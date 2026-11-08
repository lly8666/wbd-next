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
CAPACITY_STEPS=os.environ.get("WBD_PLAN028_FAST_CAPACITY_STEPS","")
if CAPACITY_STEPS not in ("","1","2"):
    raise SystemExit("invalid L2 capacity calibration flag")
if CAPACITY_STEPS and (FAST_SCENE!="pressure" or LONG_SCENE):
    raise SystemExit("L2 capacity calibration is short pressure only")
# H1309 opt-in, external 500ms Linux NUD + veth counters ONLY.
# The read-only observer creates no underlay packet or product control.
NEIGH_CLOCK_DIAG=os.environ.get("WBD_PLAN028_ERIN_NEIGH_CLOCK_DIAG","")
if NEIGH_CLOCK_DIAG not in ("","1"):
    raise SystemExit("invalid Erin physical neighbour observer")
if NEIGH_CLOCK_DIAG and (FAST_SCENE!="pressure" or CAPACITY_STEPS!="2" or LONG_SCENE):
    raise SystemExit("Erin NUD observer only in bounded 180s headroom pressure scene")
# Test-only veth underlay L2 control-plane deconfounding: netem at the
# physical veth egress drops ARP broadcasts as well as protected DATA.
# Previous native W19→W21 established ARP NUD INCOMPLETE as a 2-3s
# synthetic blackout; install each peer's ACTUAL ephemeral veth MAC on
# both ends to retain unmodified true 30% DATA loss and 125ms delay.
# This is NEVER product configuration or physical deployment. Old dynamic
# ARP failures remain separate. L3 may opt in to the verified veth L2
# control without altering the original DATA netem damage.
# Explicit L1 application-direction scene, separate from all legacy
# two-way H1259/H1314 tests. No user UDP/TCP/probes in the silent
# direction, but original Go TLS + Rust Health stays real and intact.
ONEWAY_APP=os.environ.get("WBD_PLAN028_APP_ONEWAY","")
ONEWAY_HEALTH_BLACKHOLE=os.environ.get("WBD_PLAN028_ONEWAY_HEALTH_BLACKHOLE","")
if ONEWAY_HEALTH_BLACKHOLE not in ("","1"):
    raise SystemExit("invalid source-scoped one-way native Health blackout")
if ONEWAY_APP not in ("","1"):
    raise SystemExit("invalid L1 directional business switch")
if ONEWAY_APP and not (FAST_SCENE=="pressure" and CAPACITY_STEPS=="2"
                      and not LONG_SCENE):
    raise SystemExit("L1 one-way only in 180s bounded capacity scene")
STATIC_NEIGH=os.environ.get("WBD_PLAN028_STATIC_OWNED_NEIGH","")
if STATIC_NEIGH not in ("","1"):
    raise SystemExit("invalid test-only static veth neighbour switch")
if STATIC_NEIGH and not (
        (FAST_SCENE=="pressure" and CAPACITY_STEPS=="2" and not LONG_SCENE)
        or (LONG_SCENE in LONG_SCENES and not FAST_SCENE)):
    raise SystemExit("test-only veth neighbour control requires calibrated short or L3 scene")
if ONEWAY_APP and STATIC_NEIGH!="1":
    raise SystemExit("one-way L1 requires test-controlled original veth ARP")
if ONEWAY_HEALTH_BLACKHOLE and not ONEWAY_APP:
    raise SystemExit("native Health preterminal test requires genuine one-way application")
# Opt-in H1353: one common Game4 physical underlay, both directions, 100% loss.
# Default and all prior scenarios remain byte-for-byte behavior compatible.
CORRELATED_GAME4_BLACKHOLE=os.environ.get("WBD_PLAN028_GAME4_CORRELATED_BLACKHOLE","")
if CORRELATED_GAME4_BLACKHOLE not in ("","1"):
    raise SystemExit("invalid physical Game4 blackout flag")
if CORRELATED_GAME4_BLACKHOLE and not (FAST_SCENE=="pressure"
        and CAPACITY_STEPS=="2" and STATIC_NEIGH=="1" and not LONG_SCENE
        and not ONEWAY_APP and not ONEWAY_HEALTH_BLACKHOLE):
    raise SystemExit("Game4 blackout only in native 180s original duplex scene")
# One source-locked L2 max-impairment representative (30%/250ms) using
# the already proven TEST-only physical L2 ARP control, not a product knob.
ERIN_MAX_DELAY=os.environ.get("WBD_PLAN028_ERIN_MAX_DELAY","")
if ERIN_MAX_DELAY not in ("","250"):
    raise SystemExit("unsupported test-only Erin max one-way delay")
if ERIN_MAX_DELAY and not (STATIC_NEIGH=="1" and FAST_SCENE=="pressure"
                           and CAPACITY_STEPS=="2" and not LONG_SCENE):
    raise SystemExit("max-delay test requires native short, calibrated capacity and test L2 ARP control")
# Explicit short-only OS event. A new protected TLS+M4 generation must
# survive the same real NIC / same IPv4 after physical 1500 -> 1280, without
# the old PLAN027A H998 "0 of 3 small app replies" false qualification.
# This is NEVER enabled during the original 1800s/430s fixtures.
FAST_MTU_SHRINK=os.environ.get("WBD_PLAN028_FAST_MTU_SHRINK","")
if FAST_MTU_SHRINK not in ("","alice"):
    raise SystemExit("invalid short physical MTU scenario")
if FAST_MTU_SHRINK and (FAST_SCENE!="baseline" or LONG_SCENE):
    raise SystemExit("physical in-place MTU shrink is a 180s baseline-only probe")
if FAST_SCENE and LONG_SCENE:
    raise SystemExit("rapid and long scenes cannot run together")
FAST_PHASES=(("first_wave",20,.6),("sustained",40,1.0),
             ("overload",40,1.3),("recovery",70,1.0))
if CAPACITY_STEPS=="1":
    # Preserve prior H1302 0.6/0.85/1.0/0.85 historical source.
    FAST_PHASES=(("first_wave",30,.6),("sustained",60,.85),
                 ("overload",30,1.0),("recovery",50,.85))
elif CAPACITY_STEPS=="2":
    # H1303 correction: four native ARM vCPUs were already 92.5%
    # busy at 0.6x. The same 30% Erin loss must be observed WITH
    # host headroom, before treating any >750ms app gap as product.
    # Retain real 170s business and 10s drain, no new product knobs.
    FAST_PHASES=(("first_wave",30,.25),("sustained",60,.35),
                 ("overload",30,.45),("recovery",50,.35))
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
if ERIN_MAX_DELAY:
    DELAY=(*DELAY[:4],int(ERIN_MAX_DELAY))
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


def monitor_plan028_netem_qdisc(stop,out,client_ns,client_nic,host_nic):
    """Opt-in 500ms physical netem and host-core witness, never DATA path."""
    rows=[]
    while not stop.is_set():
        stamp=time.monotonic_ns()
        def read_qdisc(*cmd):
            try:
                found=json.loads(run(*cmd,capture=True))
                root=next((q for q in found
                           if q.get("root") and q.get("kind")=="netem"),None)
                if root is None:return {"kind":"NOT_NETEM"}
                return {k:root.get(k) for k in (
                    "kind","bytes","packets","drops","overlimits","requeues",
                    "backlog","qlen")}
            except (OSError,ValueError,subprocess.CalledProcessError) as exc:
                return {"kind":"NOT_MEASURED","error":type(exc).__name__}
        uplink=read_qdisc("sudo","-n","ip","netns","exec",client_ns,
                          "tc","-s","-j","qdisc","show","dev",client_nic)
        downlink=read_qdisc("sudo","-n","tc","-s","-j","qdisc",
                            "show","dev",host_nic)
        cpu={}
        try:
            for line in pathlib.Path("/proc/stat").read_text().splitlines():
                p=line.split()
                if re.fullmatch(r"cpu[0-9]+",p[0]):
                    cpu[p[0]]=[int(x) for x in p[1:9]]
                elif p[0]!="cpu":
                    break
        except (OSError,ValueError,IndexError):
            cpu={}
        rows.append({"mono_ns":stamp,"client_uplink_netem":uplink,
                     "host_downlink_netem":downlink,"host_core_jiffies":cpu})
        stop.wait(.5)
    write_json(out/"h1301-netem-clock.json",{
        "scope":"Erin veth netem uplink client netns and downlink host",
        "diagnostic":"CLOCK_MONOTONIC, tc -s -j, 500ms, no traffic modifications",
        "samples":rows})


def monitor_plan028_erin_neighbor(stop,out,ns_server,server_nic,host_erin_nic):
    """External 500ms native ARM64 observer: kernel neighbour/bridge handoff,
    never a Go/Rust packet sender, ARP generator, or success oracle."""
    rows=[]
    def read_json(*cmd):
        try:return json.loads(run(*cmd,capture=True))
        except (OSError,ValueError,subprocess.CalledProcessError) as exc:
            return {"error":type(exc).__name__}
    def link_counters(rows):
        if not isinstance(rows,list) or not rows:return {"status":"NOT_MEASURED"}
        r=rows[0]
        stat=r.get("stats64",r.get("stats",{}))
        return {"ifname":r.get("ifname"),
                "rx":{k:stat.get("rx",{}).get(k) for k in ("bytes","packets","dropped","errors")},
                "tx":{k:stat.get("tx",{}).get(k) for k in ("bytes","packets","dropped","errors")}}
    while not stop.is_set():
        stamp=time.monotonic_ns()
        neigh=read_json("sudo","-n","ip","-n",ns_server,"-j","-s",
                        "neigh","show","to","10.25.0.6","dev",server_nic)
        if isinstance(neigh,list):
            neigh=[{k:v.get(k) for k in ("dst","state","used","confirmed","updated","probes")}
                   for v in neigh if v.get("dst")=="10.25.0.6"]
        server=link_counters(read_json("sudo","-n","ip","-n",ns_server,"-j","-s",
                                       "link","show","dev",server_nic))
        host=link_counters(read_json("sudo","-n","ip","-j","-s","link",
                                     "show","dev",host_erin_nic))
        rows.append({"mono_ns":stamp,"server_neighbor_erin":neigh,
                     "server_physical_veth":server,"host_erin_downlink_veth":host})
        stop.wait(.5)
    write_json(out/"h1309-erin-neigh-clock.json",{
        "scope":"server network namespace 10.25.0.6 neighbour + server veth and Erin host veth",
        "observer":"read-only ip -j -s neigh/link every500ms, no ARP query, no DATA/control writes",
        "samples":rows})


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
    qdisc_sampler = None
    neigh_sampler = None
    health_blackhole_worker = None
    game4_blackhole_worker = None
    game4_blackhole_errors = []
    mtu_worker = None
    mtu_faults = []
    env = dict(os.environ, LD_LIBRARY_PATH=str(build) + ":" + os.environ.get("LD_LIBRARY_PATH", ""))

    def snapshot_static_neighbours(stage):
        if not STATIC_NEIGH:return
        rows=[]
        for i,ns in enumerate(namespaces):
            client_ip=f"10.25.0.{i+2}"
            for side,namespace,iface,peer_ip in (
                ("client",ns,client_nics[i],"10.25.0.1"),
                ("server",ns_server,server_nic,client_ip),
            ):
                found=json.loads(run("sudo","-n","ip","-n",namespace,
                    "-j","neigh","show","to",peer_ip,"dev",iface,
                    capture=True))
                assert len(found)==1,(stage,side,peer_ip,found)
                neighbour=found[0]
                assert "PERMANENT" in neighbour.get("state",[]),(
                    stage,side,peer_ip,neighbour)
                rows.append({"role":side,"client":NAMES[i],
                    "physical_ip":peer_ip,"interface":iface,
                    "neighbor_state":"PERMANENT","lladdr_present":bool(neighbour.get("lladdr"))})
        write_json(out/("h1312-static-neighbour-"+stage+".json"),{
            "kind":"TEST_ONLY_PHYSICAL_VETH_L2_CONTROL",
            "source_sha":source,"phase":stage,"entries":rows,
            "native_owner_count":len(rows),
            "data_netem_unchanged":True,
            "product_or_route_key_modified":False})

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
        if STATIC_NEIGH:
            def real_mac(ns,dev):
                row=json.loads(run("sudo","-n","ip","-n",ns,"-j",
                    "link","show","dev",dev,capture=True))
                assert len(row)==1 and row[0].get("address")
                return row[0]["address"]
            # One validated existing bridge, one genuine physical veth
            # on each namespace. Static ARP is TEST L2 setup only.
            server_mac=real_mac(ns_server,server_nic)
            for i,ns in enumerate(namespaces):
                client_ip=f"10.25.0.{i+2}"
                run("sudo","-n","ip","-n",ns,"neigh","replace",
                    "10.25.0.1","lladdr",server_mac,"nud","permanent",
                    "dev",client_nics[i])
                run("sudo","-n","ip","-n",ns_server,"neigh","replace",
                    client_ip,"lladdr",real_mac(ns,client_nics[i]),
                    "nud","permanent","dev",server_nic)
            snapshot_static_neighbours("installed")
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
        # Opt-in read-only 500ms original M4 RX/TX snapshots. Do not turn
        # this on for default 180s or 1800s qualification (no DATA overhead),
        # and pass explicitly into both the server and client's OS namespaces.
        if os.environ.get("WBD_PLAN028_FEC_EGRESS_DIAG")=="1":
            diagnostic_env.append("WBD_FEC_EGRESS_DIAG=1")
        if os.environ.get("WBD_PLAN028_EXTERNAL_STAGE_DIAG")=="1":
            diagnostic_env.append("WBD_PLAN028_EXTERNAL_STAGE_DIAG=1")
        # Opt-in original RAW M4 Linux SO_SNDBUF/POLLOUT/SIOCOUTQ readback
        # after 64 real EAGAIN turns; max 128 queries per owned socket.
        # NO new default or per-record work and NO send retry/reseal.
        if os.environ.get("WBD_PLAN028_RAW_TX_SOCKET_DIAG")=="1":
            diagnostic_env.append("WBD_M0_RAW_TX_SOCKET_DIAG=1")
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
            "server_port": 443, "network_scope": "native Linux "+os.uname().machine+"/"+os.uname().machine+" 6-netns",
            "warmup_seconds": 10,
            "simultaneous_stress_seconds":170 if FAST_SCENE else 1790 if LONG_SCENE else 420,
            "application_load_seconds":180 if FAST_SCENE else 1800 if LONG_SCENE else 430,
            "drain_seconds":10,"long_scene":LONG_SCENE or None,
            "fast_scene":FAST_SCENE or None,
            "physical_in_place_mtu_shrink":bool(FAST_MTU_SHRINK),
            "fec_backend_choice":chosen_backend or None,
            "rotation_seconds":{who:ROTATION_SECONDS[i] for i,who in enumerate(NAMES)}
                if (LONG_SCENE or FAST_SCENE) else {},
            "clients": [],
            "loss_model": "two physical veth egress qdiscs each client; no artificial app drops",
            "physical_l2_arp_control": "test_only_permanent_actual_peer_mac" if STATIC_NEIGH else "dynamic_neighbour",
            "netem_qdisc_limit_packets": 10000,
        }
        if CAPACITY_STEPS:
            plan["capacity_phase_schedule"]=[
                {"name":name,"seconds":duration,"rate_scale":scale}
                for name,duration,scale in FAST_PHASES]
            plan["capacity_context"]=(
                "H1303 corrected native ARM64 0.6x CPU92.5%, "
                "0.85x CPU98.21%; tier2 .25/.35/.45/.35 tests "
                "true Erin 30%/125ms while host can breathe"
                if CAPACITY_STEPS=="2" else
                "H1301 four native ARM64 cores saturated near 1.0x; 1.3x not repeated")
        if ONEWAY_APP:
            # All five real original Go/Rust owners run. Application DATA
            # flows in exactly one direction; no synthetic UDP probes and
            # no implicit TCP SYNs in the reverse leg. Cold Health is NOT
            # application DATA. Verify both legs after the true Stop.
            one_way=(("uplink",1,0),("downlink",0,1),
                     ("uplink",1,0),("downlink",0,1),
                     ("uplink",1,0))
            plan["application_scene"]="strict_oneway"
            plan["application_directionality"]={
                who:one_way[i][0] for i,who in enumerate(NAMES)}
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
                    "c2s_mbps": RATE[i] * (one_way[i][1] if ONEWAY_APP else 1),
                    "s2c_mbps": RATE[i] * (one_way[i][2] if ONEWAY_APP else 1),
                    "udp_share": 1.0 if ONEWAY_APP else (0.8 if i < 2 else 1.0),
                    "tcp_flows": 0 if ONEWAY_APP else (2 if i < 2 else 0),
                    "probe_hz": 0 if ONEWAY_APP else 2,
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
                "oneway_delay_ms": DELAY[i],
                "c2s_target_mbps": RATE[i] * (one_way[i][1] if ONEWAY_APP else 1),
                "s2c_target_mbps": RATE[i] * (one_way[i][2] if ONEWAY_APP else 1),
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

        if CORRELATED_GAME4_BLACKHOLE:
            # Real Dave veth, common to all four Game4 lanes. tc replace
            # counters reset; snapshot real drops BEFORE restoring netem.
            def game4_blackhole():
                links=(("uplink",("sudo","-n","ip","netns","exec",namespaces[3]),client_nics[3]),
                       ("downlink",("sudo","-n"),host_nics[3]))
                installed=False
                try:
                    planned_start=start_ns+70_000_000_000
                    if stop.wait(max(0,(planned_start-time.monotonic_ns())/1e9)):
                        return
                    for name,prefix,nic in links:
                        run(*prefix,"tc","qdisc","replace","dev",nic,"root","netem",
                            "delay",str(DELAY[3])+"ms","loss","100%","limit","10000")
                    installed=True
                    start=time.monotonic_ns()
                    if stop.wait(max(0,(start_ns+78_000_000_000-
                                      time.monotonic_ns())/1e9)):
                        raise RuntimeError("stopped during blackhole")
                    seen={}
                    for name,prefix,nic in links:
                        records=json.loads(run(*prefix,"tc","-s","-j",
                                              "qdisc","show","dev",nic,capture=True))
                        netem=next((r for r in records if r.get("root")
                                    and r.get("kind")=="netem"),None)
                        assert netem is not None,(name,records)
                        seen[name]={"drops":int(netem.get("drops",0)),
                                    "packets":int(netem.get("packets",0))}
                    assert all(seen[n]["drops"]>100 for n in ("uplink","downlink")),seen
                    restore_start=time.monotonic_ns()
                    for name,prefix,nic in links:
                        run(*prefix,"tc","qdisc","replace","dev",nic,"root","netem",
                            "delay",str(DELAY[3])+"ms",
                            "loss",str(LOSS[3])+"%","limit","10000")
                    installed=False
                    restored=time.monotonic_ns()
                    write_json(out/"h1353-physical-game4-blackhole.json",{
                        "kind":"ONE_GAME4_FOUR_LANE_SHARED_VETH_BOTH_DIRECTIONS",
                        "app_start_ns":start_ns,"blackhole_start_ns":start,
                        "restore_start_ns":restore_start,"restored_ns":restored,
                        "planned_blackhole_start_ns":planned_start,
                        "planned_restore_ns":start_ns+78_000_000_000,
                        "physical_dave_client_namespace":namespaces[3],
                        "physical_links":{name:nic for name,_,nic in links},
                        "actual_kernel_drops_during_100pct":seen,
                        "original_delay_ms":DELAY[3],
                        "original_loss_pct":LOSS[3],
                        "other_four_links_untouched":True,
                        "no_product_source_change":True})
                    print("H1353_REAL_GAME4_TWO_DIRECTION_100PCT_BLACKHOLE_RESTORED",
                          start,restored,seen,flush=True)
                except Exception as exc:
                    game4_blackhole_errors.append(repr(exc))
                finally:
                    if installed:
                        for name,prefix,nic in links:
                            run(*prefix,"tc","qdisc","replace","dev",nic,"root","netem",
                                "delay",str(DELAY[3])+"ms",
                                "loss",str(LOSS[3])+"%","limit","10000",check=False)
            game4_blackhole_worker=threading.Thread(target=game4_blackhole,daemon=True)
            game4_blackhole_worker.start()
        if ONEWAY_HEALTH_BLACKHOLE:
            # Original true veth physical server→Erin only. Erin actual
            # uplink business and native Rust data path remain unchanged.
            # Force missing authenticated reverse Health across 60s so
            # the new cold B must start before the existing hard dead90.
            # Restore normal 30% loss at app+10s, while old A still runs.
            server_erin_egress=host_nics[4]
            down_delay=DELAY[4]
            assert LOSS[4]==30 and down_delay==125,(LOSS[4],down_delay)
            start_blackhole=time.monotonic_ns()
            run("sudo","-n","tc","qdisc","replace","dev",server_erin_egress,
                "root","netem","delay",f"{down_delay}ms",
                "loss","100%","limit","10000")
            print("H1318_REAL_OWNED_SERVER_TO_ERIN_PHYSICAL_BLACKHOLE_START",
                  start_blackhole,flush=True)
            def restore_server_erin_health():
                due_ns=start_ns+10_000_000_000
                if stop.wait(max(0,(due_ns-time.monotonic_ns())/1e9)):
                    return
                before_restore=time.monotonic_ns()
                run("sudo","-n","tc","qdisc","replace","dev",
                    server_erin_egress,"root","netem",
                    "delay",f"{down_delay}ms","loss","30%","limit","10000")
                after_restore=time.monotonic_ns()
                write_json(out/"h1318-erin-native-health-blackhole.json",{
                    "type":"ORIGINAL_SERVER_TO_CLIENT_PHYSICAL_VETH_EGRESS",
                    "host_interface":server_erin_egress,
                    "client":"erin","application_direction":"uplink",
                    "start_ns":start_blackhole,"restored_ns":after_restore,
                    "planned_restore_ns":due_ns,"restore_started_ns":before_restore,
                    "loss_during_preterminal_percent":100,
                    "loss_after_restore_percent":30,
                    "original_oneway_delay_ms":down_delay,
                    "client_uplink_damage_unchanged":True,
                    "no_user_reverse_app_or_probe":True
                })
                print("H1318_REAL_SERVER_TO_ERIN_HEALTH_BLACKHOLE_RESTORED",
                      after_restore,flush=True)
            health_blackhole_worker=threading.Thread(
                target=restore_server_erin_health,daemon=True)
            health_blackhole_worker.start()
        sampler = threading.Thread(target=monitor, args=(stop, tmp, out), daemon=True)
        sampler.start()
        if os.environ.get("WBD_PLAN028_QDISC_CLOCK_DIAG")=="1":
            qdisc_sampler=threading.Thread(target=monitor_plan028_netem_qdisc,
                args=(stop,out,namespaces[4],client_nics[4],host_nics[4]),
                daemon=True)
            qdisc_sampler.start()
        if NEIGH_CLOCK_DIAG:
            neigh_sampler=threading.Thread(
                target=monitor_plan028_erin_neighbor,
                args=(stop,out,ns_server,server_nic,host_nics[4]),daemon=True)
            neigh_sampler.start()
        if FAST_MTU_SHRINK:
            # The FIVE real apps are already started, and their coordinated
            # business packets start at start_ns; install the physical
            # bottleneck *70 seconds after active load begins*, while both
            # original Go TLS endpoints / Rust M4 owners are still running.
            # Change genuine veth kernel MTU at BOTH ends of Alice's physical
            # veth, not merely a reported/configured outer MTU.
            def physical_alice_mtu_event():
                try:
                    due_ns=start_ns+70_000_000_000
                    delay=max(0,(due_ns-time.monotonic_ns())/1e9)
                    if stop.wait(delay):
                        return
                    client=client_nics[0]
                    peer=host_nics[0]
                    ns=namespaces[0]
                    def client_mtu():
                        r=run("sudo","-n","ip","-n",ns,"-j","link",
                              "show","dev",client,capture=True)
                        return json.loads(r)[0]["mtu"]
                    def peer_mtu():
                        r=run("sudo","-n","ip","-j","link","show",
                              "dev",peer,capture=True)
                        return json.loads(r)[0]["mtu"]
                    before=(client_mtu(),peer_mtu())
                    assert before==(1500,1500),("non-1500 real NIC",before)
                    stamp=time.monotonic_ns()
                    assert stamp>start_ns+69_000_000_000,stamp
                    run("sudo","-n","ip","-n",ns,"link","set",
                        "dev",client,"mtu","1280")
                    run("sudo","-n","ip","link","set",
                        "dev",peer,"mtu","1280")
                    after=(client_mtu(),peer_mtu())
                    assert after==(1280,1280),after
                    write_json(out/"h1291-physical-mtu-shrink.json",{
                        "case":"alice_real_veth_both_ends_same_ip_no_link_down",
                        "before_actual_kernel_link_mtu":before,
                        "after_actual_kernel_link_mtu":after,
                        "app_start_monotonic_ns":start_ns,
                        "changed_monotonic_ns":stamp,
                        "changed_seconds_into_real_application":round(
                            (stamp-start_ns)/1e9,5),
                        "client_ipv4":"10.25.0.2",
                        "client_mode":"normal",
                        "source":"real_ip_link_mtu_set_under_active_auth_tls",
                    })
                    print("H1291_REAL_PHYSICAL_A_LIVE_MTU_1500_TO_1280_BOTH_VETH_READBACK",
                          stamp,flush=True)
                except Exception as exc:
                    mtu_faults.append(str(exc))
            mtu_worker=threading.Thread(target=physical_alice_mtu_event,daemon=True)
            mtu_worker.start()
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
        if mtu_worker is not None:
            mtu_worker.join(timeout=7)
            if mtu_worker.is_alive() or mtu_faults:
                raise RuntimeError("physical MTU fault: "+repr(mtu_faults))
            assert (out/"h1291-physical-mtu-shrink.json").is_file()
        if game4_blackhole_worker is not None:
            game4_blackhole_worker.join(timeout=12)
            if game4_blackhole_worker.is_alive() or game4_blackhole_errors:
                raise RuntimeError("Game4 blackhole failed: "+repr(game4_blackhole_errors))
            assert (out/"h1353-physical-game4-blackhole.json").is_file()
        stop.set()
        sampler.join(timeout=8)
        if health_blackhole_worker is not None:
            health_blackhole_worker.join(timeout=8)
            assert not health_blackhole_worker.is_alive()
            assert (out/"h1318-erin-native-health-blackhole.json").is_file(), (
                "actual server-to-Erin Health downlink impairment not restored")
        if qdisc_sampler is not None:
            qdisc_sampler.join(timeout=8)
            assert not qdisc_sampler.is_alive(), "qdisc probe did not exit"
            assert (out/"h1301-netem-clock.json").is_file()
        if neigh_sampler is not None:
            neigh_sampler.join(timeout=8)
            assert not neigh_sampler.is_alive(), "Erin neighbour observer did not exit"
            assert (out/"h1309-erin-neigh-clock.json").is_file()
        qdisc("after")
        if STATIC_NEIGH:
            snapshot_static_neighbours("after")
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
        if qdisc_sampler is not None:
            qdisc_sampler.join(timeout=6)
        if health_blackhole_worker is not None:
            health_blackhole_worker.join(timeout=6)
        if game4_blackhole_worker is not None:
            game4_blackhole_worker.join(timeout=6)
        if mtu_worker is not None:
            mtu_worker.join(timeout=3)
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
