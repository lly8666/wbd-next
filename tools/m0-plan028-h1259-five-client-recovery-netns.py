#!/usr/bin/env python3
"""H1259: 5 original-Go TLS + Rust raw/TUN clients, recovery after overload.

One runner, six network namespaces, real two-way per-client tc netem,
ten real application workers share one monotonic start and run 430s + 10s
drain. The workload uses the repository's original traffic.py; no mock
packets, no synthetic "success" results, no app-level retries.
"""
import json
import os
import pathlib
import re
import shlex
import signal
import subprocess
import sys
import threading
import time

NAMES = ("alice", "bob", "carol", "dave", "erin")
MODES = ("normal", "fec-auto", "game2", "game4", "fec-fixed")
LOSS = (0, 1, 5, 15, 30)
DELAY = (0, 15, 50, 100, 125)
RATE = (22, 22, 18, 18, 16)
EXTRA = (
    ("--record-cipher", "aes-128-gcm"),
    ("--record-cipher", "chacha20-poly1305"),
    ("--record-cipher", "aes-256-gcm"),
    ("--game-fec", "fixed6", "--record-cipher", "chacha20-poly1305"),
    ("--fec-profile", "6", "--outer-mtu", "1280", "--record-cipher", "aes-128-gcm"),
)


# The original H1259 430-second default remains unchanged. An opt-in
# SOURCE-qualified H1274 scene extends this very same real Go TLS/Rust harness.
LONG_SCENE=os.environ.get("WBD_PLAN028_30M_SCENE","")
LONG_SCENES={
    "baseline":((0,0,1,1,5),(0,0,15,20,50),(8,8,6,6,6),(67,73,83,97,109)),
    "heterogeneous":((0,1,5,15,30),(0,15,50,100,125),(12,12,10,9,8),(79,89,101,107,113)),
    "pressure":((0,1,5,15,30),(0,15,50,100,125),(22,22,18,18,16),(73,83,97,109,127)),
}
FAST_SCENE=os.environ.get("WBD_PLAN028_FAST_SCENE","")
if FAST_SCENE and LONG_SCENE:
    raise SystemExit("rapid and long scenes cannot run together")
FAST_PHASES=(("first_wave",20,.6),("sustained",40,1.0),
             ("overload",40,1.3),("recovery",70,1.0))
ROTATION_SECONDS=(0,0,0,0,0)
if FAST_SCENE:
    if FAST_SCENE not in LONG_SCENES:
        raise SystemExit("unknown rapid native scene")
    LOSS,DELAY,RATE,_=LONG_SCENES[FAST_SCENE]
    # Source-locked app start is about 55s after initial Go/Rust Ready.
    # Never rotate before the first actual UDP/TCP business packet: the
    # previous 29..47s rapid schedule caused artificial 11..39s early
    # gaps and cold retries BEFORE the coordinated stress start.
    ROTATION_SECONDS=(97,101,103,89,107)
if LONG_SCENE:
    if LONG_SCENE not in LONG_SCENES:
        raise SystemExit("invalid PLAN028 30m profile")
    LOSS,DELAY,RATE,ROTATION_SECONDS=LONG_SCENES[LONG_SCENE]
LONG_PHASES=(
    ("first_wave",240,.6),("sustained",600,1.0),
    ("overload",300,1.3),("recovery",650,1.0),
)

def run(*args, capture=False, check=True):
    result = subprocess.run(args, text=True, capture_output=capture, check=check)
    return result.stdout if capture else ""


def ready(path, marker, seconds=60):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if path.exists() and marker in path.read_text(errors="replace"):
            return
        time.sleep(.2)
    raise RuntimeError(f"not ready: {path} marker={marker}")


def write_json(path, item):
    path.write_text(json.dumps(item, indent=2) + "\n")


def monitor(stop, tmp, out):
    roles = ("server",) + NAMES + tuple(p + "-" + n for p in ("s", "c") for n in NAMES)
    samples = {role: [] for role in roles}
    ticks = os.sysconf("SC_CLK_TCK")
    while not stop.is_set():
        now = time.monotonic_ns()
        for role in roles:
            try:
                pid = int((tmp / (role + ".pid")).read_text())
                stat = pathlib.Path(f"/proc/{pid}/stat").read_text()
                fields = stat[stat.rfind(")") + 2:].split()
                status = pathlib.Path(f"/proc/{pid}/status").read_text()
                rss = next(int(line.split()[1]) for line in status.splitlines()
                           if line.startswith("VmRSS:"))
                samples[role].append((now, int(fields[11]) + int(fields[12]), rss))
            except (OSError, ValueError, IndexError, StopIteration):
                pass
        stop.wait(3)
    data = {}
    for role, rows in samples.items():
        if len(rows) < 2:
            continue
        elapsed = (rows[-1][0] - rows[0][0]) / 1e9
        data[role] = {
            "sample_count": len(rows), "elapsed_seconds": round(elapsed, 3),
            "average_one_core_cpu_percent": round(
                100 * (rows[-1][1] - rows[0][1]) / ticks / max(.001, elapsed), 3),
            "peak_rss_kib": max(row[2] for row in rows),
            "start_rss_kib": rows[0][2], "end_rss_kib": rows[-1][2],
        }
    write_json(out / "h1250-cpu-rss.json", data)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: h1250-five-client-netns.py COMPILED_PRODUCT_DIR")
    build = pathlib.Path(sys.argv[1]).resolve()
    for file in ("wbd-v4-server", "wbd-v4-client", "libwbd_engine.so"):
        assert (build / file).is_file(), file
    assert pathlib.Path("/dev/net/tun").is_char_device()
    workspace = pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    out = workspace / "fixed-kernel-result"
    out.mkdir(exist_ok=True)
    source = os.environ["GITHUB_SHA"]
    runid = os.environ["GITHUB_RUN_ID"]
    tag = runid[-6:]
    tmp = pathlib.Path(os.environ["RUNNER_TEMP"]) / ("h1250-" + runid)
    tmp.mkdir(mode=0o700, exist_ok=True)
    ns_server = "sv" + tag
    server_nic = "p9" + tag
    bridge = "br" + tag
    server_tun = "t9" + tag
    namespaces = ["n" + str(i) + tag for i in range(5)]
    client_nics = ["p" + str(i) + tag for i in range(5)]
    host_nics = ["h" + str(i) + tag for i in range(5)]
    client_tuns = ["t" + str(i) + tag for i in range(5)]
    procs = {}
    opened = []
    made_ns = []
    bridge_made = False
    stop = threading.Event()
    sampler = None
    env = dict(os.environ, LD_LIBRARY_PATH=str(build) + ":" + os.environ.get("LD_LIBRARY_PATH", ""))

    def proc(role, ns, args, suffix="log"):
        logfile = tmp / (role + "." + suffix)
        handle = logfile.open("w")
        opened.append(handle)
        pidfile = tmp / (role + ".pid")
        command = "echo $$ > " + shlex.quote(str(pidfile)) + "; exec " + shlex.join(args)
        p = subprocess.Popen(
            ["sudo", "-n", "ip", "netns", "exec", ns, "bash", "-c", command],
            stdout=handle, stderr=subprocess.STDOUT, env=env)
        procs[role] = p
        return logfile

    try:
        # Six OS namespaces and six real veth peers on a dedicated bridge.
        run("sudo", "-n", "ip", "netns", "add", ns_server)
        made_ns.append(ns_server)
        for ns in namespaces:
            run("sudo", "-n", "ip", "netns", "add", ns)
            made_ns.append(ns)
        run("sudo", "-n", "ip", "link", "add", bridge, "type", "bridge")
        bridge_made = True
        run("sudo", "-n", "ip", "link", "set", bridge, "up")
        for index, ns in enumerate([ns_server] + namespaces):
            if index == 0:
                guest, host, addr = server_nic, "h9" + tag, "10.25.0.1/24"
            else:
                i = index - 1
                guest, host, addr = client_nics[i], host_nics[i], f"10.25.0.{i+2}/24"
            run("sudo", "-n", "ip", "-n", ns, "link", "set", "lo", "up")
            run("sudo", "-n", "ip", "link", "add", host, "type", "veth", "peer", "name", guest)
            run("sudo", "-n", "ip", "link", "set", host, "master", bridge)
            run("sudo", "-n", "ip", "link", "set", host, "up")
            run("sudo", "-n", "ip", "link", "set", guest, "netns", ns)
            run("sudo", "-n", "ip", "-n", ns, "addr", "add", addr, "dev", guest)
            run("sudo", "-n", "ip", "-n", ns, "link", "set", guest, "up")
            run("sudo", "-n", "ip", "netns", "exec", ns, "iptables", "-A", "OUTPUT",
                "-p", "tcp", "--tcp-flags", "RST", "RST", "-j", "DROP")
        with (tmp / "cert-create.log").open("w") as certlog:
            subprocess.run(
                ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-sha256",
                 "-days", "1", "-nodes", "-keyout", str(tmp / "key.pem"),
                 "-out", str(tmp / "cert.pem"), "-subj", "/CN=wbd-v4.example.test",
                 "-addext", "subjectAltName=DNS:wbd-v4.example.test"],
                check=True, stdout=certlog, stderr=subprocess.STDOUT)
        users = {n: "h1250-" + n + "-test" for n in NAMES}
        write_json(tmp / "users.json", users)
        os.chmod(tmp / "users.json", 0o600)
        os.chmod(tmp / "key.pem", 0o600)
        run("env", "LD_LIBRARY_PATH=" + str(build), str(build / "wbd-v4-server"),
            "--init-route-key-file",
            str(tmp / "route-key.hex"))
        assert (tmp / "route-key.hex").stat().st_mode & 0o777 == 0o600
        chosen_backend=os.environ.get("WBD_GAME_FEC_BACKEND","")
        if chosen_backend and chosen_backend not in ("scalar","native"):
            raise SystemExit("invalid native backend choice")
        diagnostic_env=["WBD_SHARED_TUN_ROUTE_DIAG=1",
                        "WBD_GAME_TX_SAMPLE=1","WBD_GAME_RX_LOCK_SAMPLE=1",
                        *(["WBD_GAME_FEC_BACKEND="+chosen_backend] if chosen_backend else [])]
        sargs = [
            "env", "LD_LIBRARY_PATH=" + str(build), *diagnostic_env,
            str(build / "wbd-v4-server"),
            "--raw-interface", server_nic, "--local-ip", "10.25.0.1",
            "--local-port", "443", "--tun-name", server_tun,
            "--tun-ipv4", "10.66.0.1/24", "--server-name", "wbd-v4.example.test",
            "--route-key-hex-file", str(tmp / "route-key.hex"),
            "--users-file", str(tmp / "users.json"), "--lease-pool", "10.66.0.128/25",
            "--tls-cert", str(tmp / "cert.pem"), "--tls-key", str(tmp / "key.pem"),
            "--mode", "shared",
        ]
        serverlog = proc("server", ns_server, sargs)
        ready(serverlog, "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443", 40)
        for i, who in enumerate(NAMES):
            args = [
                "env", "LD_LIBRARY_PATH=" + str(build), *diagnostic_env,
                str(build / "wbd-v4-client"),
                "--raw-interface", client_nics[i], "--local-ip", f"10.25.0.{i+2}",
                "--local-port", str(41031 + 1000 * i),
                "--peer-ip", "10.25.0.1", "--peer-port", "443",
                "--tun-name", client_tuns[i], "--server-name", "wbd-v4.example.test",
                "--route-key-hex-file", str(tmp / "route-key.hex"),
                "--tls-ca-pem", str(tmp / "cert.pem"),
                "--username", who, "--password", users[who],
                "--auto-ip", "--installation-id-file", str(tmp / ("install-" + who)),
                "--mode", MODES[i], *EXTRA[i],
                *(["--rotation-interval",str(ROTATION_SECONDS[i])+"s",
                   "--rotation-jitter","5s"] if (LONG_SCENE or FAST_SCENE) else []),
            ]
            proc(who, namespaces[i], args)
        leases = []
        for i, who in enumerate(NAMES):
            marker = ("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=" +
                      ("2" if MODES[i] == "game2" else "4")
                      if MODES[i].startswith("game")
                      else "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client")
            logfile = tmp / (who + ".log")
            ready(logfile, marker, 75)
            receipts = re.findall(
                r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=(10\.66\.0\.\d+)/32",
                logfile.read_text(errors="replace"))
            assert receipts, f"missing native lease readback: {who}"
            leases.append(receipts[-1])
            run("sudo", "-n", "ip", "-n", namespaces[i], "route", "replace",
                "10.66.0.1/32", "dev", client_tuns[i])
            (out / ("h1250-" + who + "-tun.json")).write_text(run(
                "sudo", "-n", "ip", "-n", namespaces[i], "-j", "link",
                "show", "dev", client_tuns[i], capture=True))
        assert len(set(leases)) == 5, leases
        (out / "h1250-server-tun.json").write_text(run(
            "sudo", "-n", "ip", "-n", ns_server, "-j", "link",
            "show", "dev", server_tun, capture=True))
        print("H1250_ORIGINAL_TLS_FIVE_AUTHENTICATED_LEASES_READY " + ",".join(leases), flush=True)

        # The original 55s absolute common start allows all ten actual
        # OS-namespace traffic endpoints to prepare, unchanged in long tests.
        if FAST_SCENE and min(ROTATION_SECONDS) <= 80:
            raise RuntimeError("rapid native rotation begins before real app start")
        start_ns = time.monotonic_ns() + 55_000_000_000
        plan = {
            "source_sha": source, "start_monotonic_ns": start_ns,
            "server_port": 443, "network_scope": "native Linux x86_64/x86_64 6-netns",
            "warmup_seconds": 10,
            "simultaneous_stress_seconds":170 if FAST_SCENE else 1790 if LONG_SCENE else 420,
            "application_load_seconds":180 if FAST_SCENE else 1800 if LONG_SCENE else 430,
            "drain_seconds":10,"long_scene":LONG_SCENE or None,
            "fast_scene":FAST_SCENE or None,
            "fec_backend_choice":chosen_backend or None,
            "rotation_seconds":{who:ROTATION_SECONDS[i] for i,who in enumerate(NAMES)}
                if (LONG_SCENE or FAST_SCENE) else {},
            "clients": [],
            "loss_model": "two physical veth egress qdiscs each client; no artificial app drops",
            "netem_qdisc_limit_packets": 10000,
        }
        for i, who in enumerate(NAMES):
            cfg = {
                "seed": "H1250-" + who, "warmup_s": 10,
                "phases": ([{"name":name,"seconds":duration,"rate_scale":scale}
                            for name,duration,scale in (FAST_PHASES if FAST_SCENE else LONG_PHASES)]
                            if (LONG_SCENE or FAST_SCENE) else [
                    {"name": "first_wave", "seconds": 60, "rate_scale": 0.6},
                    {"name": "sustained", "seconds": 240, "rate_scale": 1.0},
                    {"name": "overload", "seconds": 60, "rate_scale": 1.3},
                    {"name": "recovery", "seconds": 60, "rate_scale": 1.0},
                ]),
                "drain_s": 10, "network": {"tcp_window_profile_selected": "large"},
                "traffic": {
                    "c2s_mbps": RATE[i], "s2c_mbps": RATE[i],
                    "udp_share": 0.8 if i < 2 else 1.0,
                    "tcp_flows": 2 if i < 2 else 0, "probe_hz": 2,
                    "burst_ms": 0, "sizes": [[256, 3], [1024, 7]],
                    "max_packets": 12000000 if LONG_SCENE else 2000000, "deadline_ms": 1000,
                    "allow_fragmentation": False, "observe_size_classes": True,
                    "observe_independent_flows": i < 2,
                    "warmup_rate_scale": 0.3,
                },
            }
            write_json(tmp / ("config-" + who + ".json"), cfg)
            plan["clients"].append({
                "who": who, "mode": MODES[i], "cipher": EXTRA[i][-1],
                "lease": leases[i], "loss_pct": LOSS[i],
                "oneway_delay_ms": DELAY[i], "c2s_target_mbps": RATE[i],
                "s2c_target_mbps": RATE[i],
                "outer_mtu": 1280 if i == 4 else 1460,
                "udp_share": cfg["traffic"]["udp_share"],
                "application_port": 47001 + 10 * i,
            })
        write_json(out / "h1250-matrix-plan.json", plan)
        traffic = str(workspace / "tools/network_harness/traffic.py")
        workers = []
        for i, who in enumerate(NAMES):
            p = 47001 + i * 10
            args = ["python3", "-u", traffic, "--config",
                    str(tmp / ("config-" + who + ".json")),
                    "--role", "server", "--local", "10.66.0.1",
                    "--peer", leases[i], "--port", str(p),
                    "--start-ns", str(start_ns),
                    "--output", str(out / ("h1250-s-" + who + ".json"))]
            proc("s-" + who, ns_server, args, "traffic.log")
            workers.append("s-" + who)
        time.sleep(1)
        for i, who in enumerate(NAMES):
            p = 47001 + i * 10
            args = ["python3", "-u", traffic, "--config",
                    str(tmp / ("config-" + who + ".json")),
                    "--role", "client", "--local", leases[i],
                    "--peer", "10.66.0.1", "--port", str(p),
                    "--start-ns", str(start_ns),
                    "--output", str(out / ("h1250-c-" + who + ".json"))]
            proc("c-" + who, namespaces[i], args, "traffic.log")
            workers.append("c-" + who)
        until = time.monotonic() + 41
        while time.monotonic() < until:
            ok = sum((out / ("h1250-" + role + ".ready")).exists() for role in workers)
            if ok == 10:
                break
            time.sleep(.2)
        assert ok == 10, f"only {ok}/10 application endpoints ready"
        assert time.monotonic_ns() + 2_000_000_000 < start_ns, "coordinated start missed"

        # TLS established BEFORE netem; start all ten business streams under
        # genuine 0/1/5/15/30% network impairment at the exact same instant.
        for i in range(1, 5):
            args = ["tc", "qdisc", "replace", "dev", client_nics[i],
                    "root", "netem", "delay", str(DELAY[i]) + "ms",
                    "loss", str(LOSS[i]) + "%", "limit", "10000"]
            run("sudo", "-n", "ip", "netns", "exec", namespaces[i], *args)
            run("sudo", "-n", "tc", "qdisc", "replace", "dev", host_nics[i],
                "root", "netem", "delay", str(DELAY[i]) + "ms",
                "loss", str(LOSS[i]) + "%", "limit", "10000")
        def qdisc(stage):
            rows = []
            for i, who in enumerate(NAMES):
                rows.append(f"== {who} uplink loss={LOSS[i]}% delay={DELAY[i]}ms ==")
                rows.append(run("sudo", "-n", "ip", "netns", "exec", namespaces[i],
                                "tc", "-s", "-d", "qdisc", "show", "dev",
                                client_nics[i], capture=True))
                rows.append(f"== {who} downlink loss={LOSS[i]}% delay={DELAY[i]}ms ==")
                rows.append(run("sudo", "-n", "tc", "-s", "-d", "qdisc",
                                "show", "dev", host_nics[i], capture=True))
            (out / ("h1250-qdisc-" + stage + ".txt")).write_text("\n".join(rows))
        qdisc("before")
        sampler = threading.Thread(target=monitor, args=(stop, tmp, out), daemon=True)
        sampler.start()
        print(f"H1250_START_NS={start_ns}; 5 native clients simultaneously "
              f"{180 if FAST_SCENE else 1800 if LONG_SCENE else 430}s warmup+load, 10s drain, "
              f"scenario={FAST_SCENE or LONG_SCENE or 'h1259'}; actual two-way tc loss={LOSS}", flush=True)
        for role in workers:
            p = procs[role]
            try:
                code = p.wait(timeout=400 if FAST_SCENE else 2100 if LONG_SCENE else 530)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError("traffic worker hung: " + role) from exc
            assert code == 0, f"traffic worker failed: {role}, exit={code}"
        stop.set()
        sampler.join(timeout=8)
        qdisc("after")
        for i, who in enumerate(NAMES):
            (out / ("h1250-" + who + "-underlay.json")).write_text(run(
                "sudo", "-n", "ip", "-n", namespaces[i], "-s", "-j",
                "link", "show", "dev", client_nics[i], capture=True))
            run("sudo", "-n", "kill", "-TERM",
                (tmp / (who + ".pid")).read_text().strip(), check=False)
        run("sudo", "-n", "kill", "-TERM",
            (tmp / "server.pid").read_text().strip(), check=False)
        ready(serverlog, "V4_PUBLIC_SHARED_TUN_STOP generation=", 35)
        # Original Rust Game/FEC Stop is per-client. The previous 430s
        # Action finished real traffic but copied Dave's log BEFORE his
        # native backend readback was flushed; the report then failed.
        # Wait for each product's OWN final shared-TUN Stop, which follows
        # its FEC backend Stop receipts, before copying this leg's logs.
        for who in NAMES:
            ready(tmp / (who + ".log"),
                  "V4_PUBLIC_SHARED_TUN_STOP generation=", 35)
        ready(tmp / "dave.log", "M0_GAME_M4_FEC_BACKEND_READBACK", 10)
        if LONG_SCENE or FAST_SCENE:
            # Each of five client processes must terminate/flush its actual final
            # generation before final Stop and repeat counters are copied.
            for who in NAMES:
                procs[who].wait(timeout=35)
            procs["server"].wait(timeout=35)
        # Product Stop counters are owned by each original Go/Rust process.
        # Copy now, before the report, to expose per-client TUN queue drops.
        for who in ("server",) + NAMES:
            log = tmp / (who + ".log")
            (out / ("h1250-product-" + who + ".log")).write_bytes(log.read_bytes()[-1500000:])
        if FAST_SCENE:
            run("python3", str(workspace / "tools/m0-plan028-h1286-rapid-report.py"),
                "--art", str(out), "--product-log", str(serverlog),
                "--output", str(out / "h1286-rapid-report.json"))
        elif LONG_SCENE:
            run("python3", str(workspace / "tools/m0-plan028-h1274-30min-report.py"),
                "--art", str(out), "--product-log", str(serverlog),
                "--output", str(out / "h1274-thirty-minute-report.json"))
        else:
            run("python3", str(workspace / "tools/m0-plan028-h1259-five-client-recovery-report.py"),
                "--art", str(out), "--product-log", str(serverlog),
                "--output", str(out / "h1250-five-client-report.json"))
        print(("M0_H1286_NATIVE_ARM64_FIVE_CLIENT_180S_DIAGNOSTIC_COMPLETE "+FAST_SCENE)
              if FAST_SCENE else ("M0_H1274_NATIVE_ARM64_FIVE_CLIENT_1800S_DIAGNOSTIC_COMPLETE "+LONG_SCENE)
              if LONG_SCENE else "M0_H1259_NATIVE_ORIGINAL_TLS_RUST_FIVE_CLIENT_RECOVERY_430S_DIAGNOSTIC_COMPLETE",
              flush=True)
    finally:
        stop.set()
        if sampler is not None:
            sampler.join(timeout=6)
        for role in list(procs)[::-1]:
            p = procs[role]
            if p.poll() is None:
                pidfile = tmp / (role + ".pid")
                if pidfile.exists():
                    run("sudo", "-n", "kill", "-TERM", pidfile.read_text().strip(), check=False)
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        for ns in reversed(made_ns):
            run("sudo", "-n", "ip", "netns", "del", ns, check=False)
        if bridge_made:
            run("sudo", "-n", "ip", "link", "del", bridge, check=False)
        for handle in opened:
            handle.close()
        for role in ("server",) + NAMES:
            log = tmp / (role + ".log")
            if log.exists():
                (out / ("h1250-product-" + role + ".log")).write_bytes(
                    log.read_bytes()[-1500000:])
        for role in ("s-" + n for n in NAMES):
            log = tmp / (role + ".traffic.log")
            if log.exists():
                (out / ("h1250-traffic-" + role + ".log")).write_bytes(log.read_bytes()[-40000:])
        for role in ("c-" + n for n in NAMES):
            log = tmp / (role + ".traffic.log")
            if log.exists():
                (out / ("h1250-traffic-" + role + ".log")).write_bytes(log.read_bytes()[-40000:])


if __name__ == "__main__":
    main()
