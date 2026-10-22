"""One Actions job, one scenario, sequential pinned binaries A or AB/BA.

Linux namespaces are the adapter; the actual Go CLI owns TLS and Rust raw/TUN.
This file never synthesizes transport packets, ACKs, FEC or product readiness.
"""
import argparse
import json
import os
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from .artifacts import fetch, sha, verify
from .config import Unsupported, netem_args, validate
from .report import markdown, summarize, network_accounting

ROOT = Path(__file__).resolve().parents[2]
TRAFFIC = Path(__file__).with_name("traffic.py")


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def command(args, check=True):
    p = subprocess.run([str(x) for x in args], text=True, capture_output=True, timeout=20)
    if check and p.returncode:
        # No credential-bearing commands use this function.
        raise RuntimeError(f'{args[0]} exit={p.returncode}: {p.stderr[-1000:]}')
    return p.stdout


def read(path):
    try:
        return Path(path).read_text()
    except OSError:
        return "UNAVAILABLE"


def process(pid):
    try:
        fields = read(f"/proc/{pid}/stat").rsplit(")", 1)[1].split()
        rss = int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
        cpu = (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
        return {"cpu_s": cpu, "rss_bytes": rss, "threads": int(fields[17])}
    except (ValueError, IndexError):
        return None


class Monitor:
    def __init__(self, products, output):
        self.products, self.output = products, output
        self.samples, self.stop = [], threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            fields = read("/proc/stat").splitlines()[0].split()[1:]
            self.samples.append({"ns": time.monotonic_ns(), "cpu": list(map(int, fields)),
                "psi_cpu": read("/proc/pressure/cpu"),
                "psi_memory": read("/proc/pressure/memory"),
                "processes": {name: process(p.pid) for name, p in self.products.items()}})
            self.stop.wait(1)

    def finish(self, window=None):
        self.stop.set()
        self.thread.join(3)
        dump(self.output / "host-samples.json", self.samples)
        peak_psi = peak_steal = 0.0
        samples = [s for s in self.samples if window is None or window[0] <= s["ns"] <= window[1]]
        psi = []
        for s in samples:
            m = re.search(r"some avg10=([\d.]+)", s["psi_cpu"])
            if m:
                psi.append(float(m[1]))
            peak_psi = max(peak_psi, float(m[1]) if m else 0)
        for a, b in zip(samples, samples[1:]):
            # guest/guest_nice already included in user/nice; exclude the double-count.
            total = sum(b["cpu"][:8]) - sum(a["cpu"][:8])
            if total > 0:
                peak_steal = max(peak_steal, (b["cpu"][7] - a["cpu"][7]) * 100 / total)
        costs = {}
        for name in self.products:
            points = [s["processes"][name] for s in self.samples if s["processes"][name]]
            if points:
                costs[name] = {"cpu_s_observed_including_warmup_setup_drain": points[-1]["cpu_s"]-points[0]["cpu_s"],
                               "rss_peak_bytes": max(p["rss_bytes"] for p in points)}
        return {"cpu_psi_some_peak": peak_psi, "cpu_psi_some_mean": sum(psi)/len(psi) if psi else None,
                "cpu_psi_over20_fraction": sum(v > 20 for v in psi)/len(psi) if psi else None,
                "samples_in_measurement": len(samples), "steal_pct_peak": peak_steal, "processes": costs}


def startup_diagnostic(log_text):
    """Never persist CLI stdout/stderr or secret-bearing argv: fixed labels only."""
    tokens = {
        "CLI_UNKNOWN_FLAG": "flag provided but not defined",
        "CLI_BAD_ARGUMENTS": "missing/invalid real original v4 tls/raw/tun settings",
        "CLI_BAD_ROUTE_KEY": "invalid tls route key",
        "CLI_BAD_TUNNEL_ID": "invalid tunnel-id",
        "RUNTIME_MISSING_SHARED_LIBRARY": "error while loading shared libraries",
        "RUNTIME_MISSING_SYMBOL": "undefined symbol",
        "KERNEL_NO_DEVICE": "no such device",
        "KERNEL_TUN_UNAVAILABLE": "/dev/net/tun",
        "KERNEL_PERMISSION": "operation not permitted",
        "KERNEL_DENIED": "permission denied",
        "KERNEL_ADDRESS_BUSY": "address already in use",
        "KERNEL_INVALID_ARGUMENT": "invalid argument",
        "KERNEL_NO_SUCH_FILE": "no such file or directory",
        "NETWORK_CONNECT_REFUSED": "connection refused",
        "NETWORK_TIMED_OUT": "i/o timeout",
        "GO_PANIC": "panic:",
    }
    text = log_text.lower()
    reasons = [label for label, token in tokens.items() if token in text]
    return {"safe_failure_classes": reasons or ["UNCLASSIFIED_NO_RAW_LOG_PERSISTED"],
            "log_lines_present": min(len(log_text.splitlines()), 100000)}

class LinuxExperiment:
    def __init__(self, config, bundle_dir, out, label):
        self.config, self.bundle = config, Path(bundle_dir) / "fixed-build"
        self.out, self.label = Path(out), label
        self.out.mkdir(parents=True, exist_ok=False)
        self.temp = tempfile.TemporaryDirectory(prefix="wbd-net-", dir=os.environ.get("RUNNER_TEMP"))
        self.private = Path(self.temp.name)
        suffix = secrets.token_hex(4)
        self.ns = {"client": "wbnc-" + suffix, "server": "wbns-" + suffix}
        self.iface = {"client": "wbnc0", "server": "wbns0"}
        self.ip = {"client": "10.25.0.2", "server": "10.25.0.1"}
        self.inner = {"client": "10.66.0.2", "server": "10.66.0.1"}
        self.products, self.workers, self.handles = {}, {}, []
        self.created = []
        self.monitor = None
        self.lanes = {"game2": 2, "game4": 4}.get(config["product"]["mode"], 1)
        self.config_events, self.snapshots = [], []
        self.child_env = {k: v for k, v in os.environ.items() if k not in ["GH_TOKEN", "GITHUB_TOKEN"]}

    def nscommand(self, role, args, check=True):
        return command(["ip", "netns", "exec", self.ns[role], *args], check)

    def spawn(self, role, args, log):
        f = open(self.private / log, "w")
        self.handles.append(f)
        return subprocess.Popen(["ip", "netns", "exec", self.ns[role], *map(str, args)],
                                stdout=f, stderr=subprocess.STDOUT, env=self.child_env)

    def setup(self):
        for ns in self.ns.values():
            command(["ip", "netns", "add", ns])
            self.created.append(ns)
        # Create veth inside the owned namespace, never touch host routes/firewall.
        self.nscommand("client", ["ip", "link", "add", "wbnc0", "type", "veth", "peer", "name", "wbns0"])
        self.nscommand("client", ["ip", "link", "set", "wbns0", "netns", self.ns["server"]])
        for role in self.ns:
            dev = self.iface[role]
            self.nscommand(role, ["ip", "link", "set", "lo", "up"])
            self.nscommand(role, ["ip", "addr", "add", self.ip[role] + "/24", "dev", dev])
            self.nscommand(role, ["ip", "link", "set", dev, "mtu", str(self.config["network"]["outer_mtu"]), "up"])
            self.nscommand(role, ["ethtool", "-K", dev, "gro", "off", "gso", "off", "tso", "off"])
            self.nscommand(role, ["iptables", "-A", "OUTPUT", "-p", "tcp", "--tcp-flags", "RST", "RST", "-j", "DROP"])
            self.nscommand(role, ["iptables", "-N", "WBN_LOSS"])
            self.nscommand(role, ["iptables", "-I", "OUTPUT", "1", "-j", "WBN_LOSS"])
        command(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-days", "1", "-nodes",
                 "-keyout", self.private / "key.pem", "-out", self.private / "cert.pem",
                 "-subj", "/CN=wbd-v4.example.test", "-addext", "subjectAltName=DNS:wbd-v4.example.test"])
        (self.private / "key.pem").chmod(0o600)
        route, password, tunnel = secrets.token_hex(32), secrets.token_hex(16), secrets.token_hex(16)
        for role in ["server", "client"]:
            args = ["env", "LD_LIBRARY_PATH=" + str(self.bundle), str(self.bundle / ("wbd-v4-" + role)),
                "--raw-interface", self.iface[role], "--local-ip", self.ip[role],
                "--local-port", "443" if role == "server" else "41031",
                "--tun-name", "wbntun0", "--tun-ipv4", self.inner[role] + "/24",
                "--server-name", "wbd-v4.example.test", "--route-key-hex", route,
                "--username", "ephemeral-harness", "--password", password, "--tunnel-id", tunnel,
                "--mode", self.config["product"]["mode"], "--fec-profile", str(self.config["product"]["fec_profile"])]
            if role == "server":
                args += ["--tls-cert", str(self.private / "cert.pem"), "--tls-key", str(self.private / "key.pem")]
            else:
                args += ["--peer-ip", self.ip["server"], "--peer-port", "443"]
            self.products[role] = self.spawn(role, args, role + ".log")
            if role == "server":
                time.sleep(.5)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if any(p.poll() is not None for p in self.products.values()):
                raise RuntimeError("public CLI exited before readiness: " + repr({r:p.poll() for r,p in self.products.items()}))
            if self.lanes > 1:
                ready = all(f"V4_ORIGINAL_GO_GAME_NATIVE_READY role={r} lanes={self.lanes}" in read(self.private / (r + ".log")) for r in self.ns)
            else:
                ready = all(f"V4_ORIGINAL_GO_{r.upper()}_NATIVE_READY" in read(self.private / (r + ".log")) for r in self.ns)
            if ready:
                break
            time.sleep(.1)
        else:
            raise RuntimeError("real native READY timeout")
        self.effective = {"mode": self.config["product"]["mode"], "lanes": self.lanes,
                          "game_fec": "off (public CLI explicitly sets off)", "inner_links": {}}
        for role in self.ns:
            links = json.loads(self.nscommand(role, ["ip", "-j", "link", "show", "wbntun0"]))
            self.effective["inner_links"][role] = links
            if (not self.config["traffic"]["allow_fragmentation"] and self.config["traffic"]["udp_share"]
                    and max(s for s, _ in self.config["traffic"]["sizes"]) + 28 > links[0]["mtu"]):
                raise Unsupported("UDP payload+28 exceeds actual TUN MTU; explicitly allow_fragmentation or use a separate rejection case")
        dump(self.out / "effective-config.json", self.effective)

    def configure(self, phase, index, initial=False):
        event = {"phase": phase["name"], "scheduled_index": index, "begin_ns": time.monotonic_ns(), "commands": []}
        for role, direction in [("client", "c2s"), ("server", "s2c")]:
            dev, d = self.iface[role], phase[direction]
            self.nscommand(role, ["iptables", "-F", "WBN_LOSS"])
            for lane in d["blackhole_lanes"]:
                self.nscommand(role, ["iptables", "-A", "WBN_LOSS", "-p", "tcp",
                    "--dport" if role == "client" else "--sport", str(442 + lane), "-j", "DROP"])
            independent = self.config["network"]["lane_loss"] == "independent" and self.lanes > 1
            if initial and independent:
                self.nscommand(role, ["tc", "qdisc", "add", "dev", dev, "root", "handle", "1:",
                                      "prio", "bands", str(self.lanes), "priomap", *("0" for _ in range(16))])
            for lane in range(self.lanes if independent else 1):
                args = ["tc", "qdisc", "add" if initial else "change", "dev", dev]
                if independent:
                    args += ["parent", f"1:{lane+1}", "handle", f"{100+lane}:"]
                else:
                    args += ["root", "handle", "100:"]
                seed = self.config["seed"] + index * 100 + lane + (10000 if role == "server" else 0)
                if self.config["network"]["netem_rng"] == "unseeded_recorded":
                    seed = None  # Explicit request mode, never silently fall back.
                args += ["netem", *netem_args(d, seed, self.config["network"]["queue_packets"])]
                self.nscommand(role, args)
                event["commands"].append({"direction": direction, "lane": lane+1 if independent else "all", "argv": args,
                                           "kernel_rng": self.config["network"]["netem_rng"]})
                if initial and independent:
                    self.nscommand(role, ["tc", "filter", "add", "dev", dev, "parent", "1:", "protocol", "ip",
                        "pref", str(10+lane), "flower", "ip_proto", "tcp", "dst_port" if role == "client" else "src_port",
                        str(443+lane), "classid", f"1:{lane+1}"])
        event["end_ns"] = time.monotonic_ns()
        self.config_events.append(event)

    def snapshot(self, name):
        row = {"name": name, "ns": time.monotonic_ns(), "processes": {r: process(p.pid) for r, p in self.products.items()}, "network": {}}
        for role in self.ns:
            row["network"][role] = {
                "qdisc": json.loads(self.nscommand(role, ["tc", "-s", "-j", "qdisc", "show", "dev", self.iface[role]])),
                "links": json.loads(self.nscommand(role, ["ip", "-s", "-j", "link", "show"])),
                "snmp": self.nscommand(role, ["cat", "/proc/net/snmp"]),
                "udp_sockets": self.nscommand(role, ["ss", "-uanm"], False),
                "packet_sockets": self.nscommand(role, ["ss", "-0", "-am"], False),
                "blackhole_counters": self.nscommand(role, ["iptables", "-nvxL", "WBN_LOSS"])}
        self.snapshots.append(row)

    def wait_until(self, ns):
        while time.monotonic_ns() < ns:
            if any(p.poll() is not None for p in self.products.values()):
                raise RuntimeError("product exited during real traffic")
            time.sleep(min(.05, max(0, (ns-time.monotonic_ns())/1e9)))

    def markers(self):
        # Persist whitelist-only numeric/product-state messages, never TLS keys or arguments.
        logs = {}
        for role in self.ns:
            lines = [line for line in read(self.private / (role + ".log")).splitlines()
                     if re.search(r"V4_(PUBLIC_(M2_OUTER |FEC2_READBACK |GAME_KERNEL |NATIVE_STOP_DRAINED|GAME_NATIVE_STOP_DRAINED)|ORIGINAL_GO_\w+_NATIVE_READY)", line)]
            logs[role] = "\n".join(lines[-40:])
            (self.out / (role + "-product-markers.log")).write_text(logs[role] + "\n")
        return logs

    def telemetry(self):
        logs = self.markers()
        mode = self.config["product"]["mode"]
        applied = {}
        for role, log in logs.items():
            matches = re.findall(r"V4_PUBLIC_FEC2_READBACK role=\w+ mode=(\w+) requested=(\d+) applied=(\d+) profile=(\d+) pending=(\w+)", log)
            if matches:
                applied[role] = matches[-1]
        verified = True
        if mode in ["fec-fixed", "fec-auto"]:
            verified = len(applied) == 2 and all(v[0] == ("fixed" if mode == "fec-fixed" else "auto") and v[1] == v[2]
                and int(v[2]) > 0 and v[4] == "false" and (mode != "fec-fixed" or int(v[3]) == self.config["product"]["fec_profile"])
                for v in applied.values())
        counters = {}
        for role, log in logs.items():
            lines = [s for s in log.splitlines() if "V4_PUBLIC_M2_OUTER " in s or "V4_PUBLIC_GAME_KERNEL " in s]
            counters[role] = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", lines[-1])} if lines else {}
        repair = sum(v["original_frozen_retransmitted"] for v in counters.values()) if all("original_frozen_retransmitted" in v for v in counters.values()) else None
        return {"stop_drained_both": all(("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED" if self.lanes > 1 else "V4_PUBLIC_NATIVE_STOP_DRAINED") in s for s in logs.values()),
                "effective_config_verified": verified, "fec_final_readback": applied, "counters": counters,
                "repair_packets": repair, "repair_wire_bytes_and_10pct_budget": "NOT_OBSERVED",
                "repair_useful_spurious_and_latency": "NOT_OBSERVED",
                "FEC_k_r_parity_queue_decode": "NOT_OBSERVED",
                "owner_queue_age_lock_wait_raw_socket_drops": "NOT_EXPOSED_BY_CURRENT_PUBLIC_CLI",
                "auto_runtime_curve": "NOT_OBSERVED_FINAL_READBACK_ONLY"}

    def run(self):
        result = None
        host = {}
        started = time.monotonic_ns()
        try:
            self.setup()
            self.configure({**self.config["phases"][0], "name": "warmup"}, 0, True)
            config_path = self.private / "effective-request.json"
            dump(config_path, self.config)
            start_ns = time.monotonic_ns() + 20_000_000_000
            for role in ["server", "client"]:
                peer = "server" if role == "client" else "client"
                self.workers[role] = self.spawn(role, [sys.executable, str(TRAFFIC), "--config", str(config_path),
                    "--role", role, "--local", self.inner[role], "--peer", self.inner[peer],
                    "--output", str(self.out / (role + "-traffic.json")), "--start-ns", str(start_ns)], role + "-traffic.log")
            self.monitor = Monitor({**self.products, **{r + "-injector": p for r, p in self.workers.items()}}, self.out)
            self.monitor.thread.start()
            deadline = time.monotonic() + 18
            while time.monotonic() < deadline:
                if all((self.out / (r + "-traffic.ready")).exists() for r in self.ns):
                    break
                if any(p.poll() is not None for p in self.workers.values()):
                    raise RuntimeError("traffic worker setup failed")
                time.sleep(.1)
            else:
                raise RuntimeError("traffic worker not ready before scheduled start")
            self.wait_until(start_ns)
            self.snapshot("warmup-start")
            boundary = start_ns + int(self.config["warmup_s"] * 1e9)
            for i, phase in enumerate(self.config["phases"], 1):
                self.wait_until(boundary)
                self.snapshot("before-" + phase["name"])
                self.configure(phase, i)
                self.config_events[-1]["scheduled_start_ns"] = boundary
                boundary += int(phase["seconds"] * 1e9)
            self.wait_until(boundary)
            self.snapshot("measurement-end")
            for p in self.workers.values():
                p.wait(timeout=self.config["drain_s"] + 10)
                if p.returncode:
                    raise RuntimeError("traffic worker exited with failure")
            self.snapshot("drain-end")
            host = self.monitor.finish((start_ns + int(self.config["warmup_s"] * 1e9), boundary))
            self.monitor = None
            for p in self.products.values():
                p.terminate()
            for p in self.products.values():
                p.wait(timeout=10)
                if p.returncode:
                    raise RuntimeError("product nonzero exit on Stop")
            result = summarize(self.config, json.loads((self.out / "client-traffic.json").read_text()),
                               json.loads((self.out / "server-traffic.json").read_text()), self.telemetry(), host)
            result["network_accounting"] = network_accounting(self.snapshots)
            # Source cohort includes late packets; CPU/wire window excludes warmup/drain.
            begin = next(s for s in self.snapshots if s["name"] == "before-" + self.config["phases"][0]["name"])
            end = next(s for s in self.snapshots if s["name"] == "measurement-end")
            result["measurement_cost"] = {}
            for role, direction in [("client", "s2c"), ("server", "c2s")]:
                cpu = end["processes"][role]["cpu_s"] - begin["processes"][role]["cpu_s"]
                rows = [x for x in result["observed"] if x["direction"] == direction]
                delivered_packets = sum(x["delivered"] for x in rows)
                delivered_bytes = sum(x["cohort_delivered_app_mbps"] * 1e6 / 8 * next(p["seconds"] for p in self.config["phases"] if p["name"] == x["phase"]) for x in rows)
                def link_bytes(s):
                    v = next(x for x in s["network"][role]["links"] if x["ifname"] == self.iface[role])
                    return v.get("stats64", v.get("stats"))["tx"]["bytes"]
                result["measurement_cost"][role] = {"cpu_s": cpu,
                    "cpu_s_per_delivered_GiB": cpu / (delivered_bytes / 2**30) if delivered_bytes else None,
                    "cpu_s_per_delivered_Mrecords": cpu / (delivered_packets / 1e6) if delivered_packets else None,
                    "outer_interface_tx_bytes": link_bytes(end)-link_bytes(begin),
                    "note": "process handles both directions; normalization uses its received business; veth bytes are interface accounting, not physical L1"}
            late_events = [e for e in self.config_events if "scheduled_start_ns" in e and
                e["end_ns"] - e["scheduled_start_ns"] > max(100_000_000, int(self.config["phases"][e["scheduled_index"]-1]["seconds"] * 1e8))]
            if late_events:
                result["limits"].append("INVALID_IMPAIRMENT_TIMING: stage transition late; inspect events")
                if result["result"] != "FAIL":
                    result["result"] = "INCONCLUSIVE"
        except Unsupported as e:
            result = {"result": "UNSUPPORTED", "reason": str(e)}
        except Exception as e:
            diagnostics = {role: {**startup_diagnostic(read(self.private / (role + ".log"))),
                                  "exit_before_cleanup": p.poll(),
                                  "tun_present": bool(self.nscommand(role, ["ip", "link", "show", "wbntun0"], False))}
                           for role, p in self.products.items()}
            result = {"result": "FAIL", "reason": str(e), "failures": [str(e)],
                      "safe_startup_diagnostics": diagnostics}
        finally:
            if self.monitor:
                host = self.monitor.finish()
            self.cleanup()
            self.markers()
            for role in self.ns:
                text = read(self.private / (role + "-traffic.log"))
                if text != "UNAVAILABLE":
                    (self.out / (role + "-traffic.log")).write_text(text[-12000:])
            dump(self.out / "network-snapshots.json", self.snapshots)
            dump(self.out / "impairment-events.json", self.config_events)
            result.update(label=self.label, monotonic_start_ns=started, monotonic_end_ns=time.monotonic_ns(),
                          host=host, source=self.config["bundles"][self.label]["source"],
                          request_id=self.config["id"], cleanup=self.cleanup_result)
            if not self.cleanup_result["owned_namespaces_absent"]:
                result["result"] = "FAIL"
                result.setdefault("failures", []).append("owned namespace cleanup incomplete")
            dump(self.out / "result.json", result)
            (self.out / "summary.md").write_text(markdown(result))
            self.temp.cleanup()
        return result

    def cleanup(self):
        for p in [*self.workers.values(), *self.products.values()]:
            if p.poll() is None:
                p.terminate()
        for p in [*self.workers.values(), *self.products.values()]:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=3)
        for ns in reversed(self.created):
            command(["ip", "netns", "del", ns], check=False)
        present = command(["ip", "netns", "list"])
        self.cleanup_result = {"owned_namespaces_absent": all(ns not in present for ns in self.created)}
        for f in self.handles:
            f.close()


def host_identity():
    cpu = read("/proc/cpuinfo")
    return {"kernel": platform.release(), "machine": platform.machine(), "logical_cpus": os.cpu_count(),
            "cpu_model": next((s for s in cpu.splitlines() if s.startswith("model name")), "UNAVAILABLE"),
            "flags": next((s for s in cpu.splitlines() if s.startswith("flags")), "UNAVAILABLE"),
            "cgroup_cpu_max": read("/sys/fs/cgroup/cpu.max"), "meminfo": read("/proc/meminfo"),
            "runner": os.environ.get("RUNNER_NAME"), "job": os.environ.get("GITHUB_JOB"),
            "run": os.environ.get("GITHUB_RUN_ID"), "attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["prepare", "run"])
    ap.add_argument("--request", required=True)
    ap.add_argument("--directory", required=True)
    a = ap.parse_args()
    directory = Path(a.directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        config = validate(json.loads(Path(a.request).read_text()))
    except Exception as e:
        dump(directory / "result.json", {"result": "UNSUPPORTED" if isinstance(e, Unsupported) else "INVALID_REQUEST", "reason": str(e)})
        raise
    if os.environ.get("GITHUB_ACTIONS") != "true" or platform.system() != "Linux":
        raise RuntimeError("execution validation is GitHub Actions Linux only")
    if a.command == "prepare":
        for label, bundle in config["bundles"].items():
            receipt = fetch(bundle, directory / ("bundle-" + label))
            dump(directory / ("bundle-" + label + "-receipt.json"), receipt)
        dump(directory / "request.json", config)
        return
    if os.geteuid() != 0:
        raise RuntimeError("run needs sudo for OWNED namespaces only")
    def cancelled(signum, _frame):
        raise RuntimeError(f"cancelled by signal {signum}")
    signal.signal(signal.SIGTERM, cancelled)
    if config != json.loads((directory / "request.json").read_text()):
        raise ValueError("prepared request changed")
    dump(directory / "host.json", host_identity())
    results = []
    for label in config["order"]:
        verify(directory / ("bundle-" + label), config["bundles"][label])
        results.append(LinuxExperiment(config, directory / ("bundle-" + label), directory / label, label).run())
        if not results[-1]["cleanup"]["owned_namespaces_absent"]:
            break  # never contaminate the second measurement
    statuses = [r["result"] for r in results]
    status = "PASS_SCOPED_OBSERVATION" if all(s == "PASS_SCOPED_OBSERVATION" for s in statuses) else (
        "FAIL" if "FAIL" in statuses else "INCONCLUSIVE")
    final = {"result": status, "harness_source": os.environ["GITHUB_SHA"], "request": config,
             "host": host_identity(), "legs": results,
             "comparison": "same job, sequential, no shared namespaces; inspect background and actual delivery before claiming improvement"}
    dump(directory / "result.json", final)
    summary = "\n".join((directory / r["label"] / "summary.md").read_text() for r in results)
    (directory / "summary.md").write_text(summary)
    # Only small receipts/reports survive; no binaries/certificates/pcap in result artifact.
    for label in config["bundles"]:
        owned = directory / ("bundle-" + label)
        if owned.parent == directory and owned.exists():
            shutil.rmtree(owned)
    print(json.dumps({"result": status, "request": config["id"], "legs": statuses}))
    if status != "PASS_SCOPED_OBSERVATION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
