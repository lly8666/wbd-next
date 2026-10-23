"""One Actions job, one scenario, sequential pinned binaries A or AB/BA.

Linux namespaces are the adapter; the actual Go CLI owns TLS and Rust raw/TUN.
This file never synthesizes transport packets, ACKs, FEC or product readiness.
"""
import argparse
import copy
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
from .envelope import request_envelope

ROOT = Path(__file__).resolve().parents[2]
TRAFFIC = Path(__file__).with_name("traffic.py")

def verify_outer_recovery_policy(expected, observed):
    """Only single-repair sources can prove the v2 readback.

    Historical legacy bundles lack this native marker: never certify them as
    v2, but do not invalidate an otherwise useful same-VM AB control.
    """
    if expected != "outer-single-repair-v2":
        return None
    return len(observed) == 2 and all(
        v.get("policy") == expected
        and v.get("repair_attempt_limit") == 1
        and v.get("shadow_limit") == 131072
        and v.get("retain_cap_us") == 1500000
        for v in observed.values())


def product_marker_line(line):
    """Only documented public numeric/status marker families enter artifacts."""
    return bool(re.search(
        r"V4_(PUBLIC_(MTU |M2_OUTER |FEC2_TX |FEC2_FAILURE |FEC2_M2_PROOF |FEC2_RX_PROOF |FEC2_RX_IP_CLASS |FEC2_M1_INGRESS |FEC2_M1_STAGE |FEC2_READBACK |RX_CHAIN |TX_CHAIN |M1_POOL |GAME_KERNEL |NATIVE_STOP_DRAINED|GAME_NATIVE_STOP_DRAINED)|ORIGINAL_GO_\w+_NATIVE_READY)",
        line))




def public_fec_m1_stage(log_text):
    """Original Fixed M1 handoff after successful TUN loan, numeric only.

    A missing or malformed native readback remains NOT_OBSERVED, never zero.
    Staging worker owns one 32-packet turn, so individual atomic readbacks
    permit at most 32 in-flight count differences.
    """
    fields=("attempted","queued","not_ready","error","oversize","mode_skipped")
    rows=[line for line in log_text.splitlines()
          if "V4_PUBLIC_FEC2_M1_STAGE role=" in line]
    if not rows:
        return None
    d={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",rows[-1])}
    if any(k not in d for k in fields):
        return None
    actual=d["queued"]+d["not_ready"]+d["error"]
    if abs(d["attempted"]-actual)>32 or d["oversize"]>d["error"]+32:
        return None
    return {k:d[k] for k in fields}


def public_fec_m1_ingress(log_text):
    """True native pre-stage TUN receipt counts, never imply source delivery."""
    fields=("read_ipv4","small_loaned","small_arena_fail","jumbo","rejected")
    rows=[line for line in log_text.splitlines()
          if "V4_PUBLIC_FEC2_M1_INGRESS role=" in line]
    if not rows:
        return None
    values={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",rows[-1])}
    if any(k not in values for k in fields):
        return None
    # Worker atomics are observed concurrently (not a transaction);
    # bounded one-turn in-flight counts may differ by <=32.
    done=(values["small_loaned"]+values["small_arena_fail"]+values["jumbo"])
    if abs(values["read_ipv4"]-done)>32:
        return None
    return {k:values[k] for k in fields}


def public_fec_rx_ip_class(log_text):
    """Original after-M4-write protocol/ACK type counts, never inferred."""
    fields=("sys_udp","rec_udp","sys_tcp","rec_tcp","other_ip",
            "tcp_ack_only","tcp_data","tcp_other")
    rows=[line for line in log_text.splitlines()
          if "V4_PUBLIC_FEC2_RX_IP_CLASS role=" in line]
    if not rows:
        return None
    d={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)", rows[-1])}
    if any(k not in d for k in fields):
        return None
    if (d["tcp_ack_only"]+d["tcp_data"]+d["tcp_other"] !=
        d["sys_tcp"]+d["rec_tcp"]):
        return None
    return {k:d[k] for k in fields}


def public_fec_rx_proof(log_text):
    """Strict numeric original AEAD/Pn→FEC decoder→M4 TUN, never default zero."""
    fields=("source_seen","source_accepted","parity_seen","parity_accepted",
            "systematic_candidate","recovered_candidate","systematic_tun",
            "recovered_tun","tun_failed","decoder_rejected",
            "admission_disabled")
    rows=[line for line in log_text.splitlines()
          if "V4_PUBLIC_FEC2_RX_PROOF role=" in line]
    if not rows:
        return None
    values={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",rows[-1])}
    if any(k not in values for k in fields):
        return None
    if (values["source_accepted"]>values["source_seen"] or
        values["parity_accepted"]>values["parity_seen"] or
        values["systematic_tun"]>values["systematic_candidate"] or
        values["recovered_tun"]>values["recovered_candidate"] or
        values["tun_failed"]>
            values["systematic_candidate"]+values["recovered_candidate"] or
        values["admission_disabled"]>
            values["source_seen"]+values["parity_seen"] or
        values["decoder_rejected"]>
            values["source_seen"]+values["parity_seen"]):
        return None
    return {k:values[k] for k in fields}


def public_fec_m2_proof(log_text):
    """Only true original Go/Rust M2 counters once pre-Stop, never infer zero."""
    fields=("accepted","not_sent","uncertain","unknown_2s","unknown_8s",
            "covered_2s","covered_8s","reverse_reports","first_censored",
            "cover_censored")
    rows=[line for line in log_text.splitlines()
          if "V4_PUBLIC_FEC2_M2_PROOF role=" in line]
    if not rows:
        return None
    values={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",rows[-1])}
    if any(k not in values for k in fields):
        return None
    if values["first_censored"] not in (0,1) or values["cover_censored"] not in (0,1):
        return None
    return {k:values[k] for k in fields}


def public_fec_failure_reasons(log_text):
    """Read only the genuine pre-Stop counters, never infer missing as zero."""
    fields=("source_payload","source_arena","source_seal","parity_policy",
            "parity_arena","parity_seal","parity_m4_noncopy","source_m4_noncopy")
    rows=[line for line in log_text.splitlines() if "V4_PUBLIC_FEC2_FAILURE role=" in line]
    if not rows:
        return None
    values={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)", rows[-1])}
    if not all(k in values for k in fields):
        return None
    return {k:values[k] for k in fields}


def public_fec_tx_snapshot(log_text):
    """Parse complete original-Go pre-Stop owner marker or mark unknown."""
    fields = ("accepted","notready","full","partial","k1","k2_4",
              "k5_12","k13_16","rplanned","rsent","expired",
              "pressure_jobs","pressure_sources","unknown_capacity")
    rows = [line for line in log_text.splitlines()
            if "V4_PUBLIC_FEC2_TX role=" in line]
    if not rows:
        return None
    values = {k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",rows[-1])}
    if not all(k in values for k in fields):
        return None
    if values["full"]+values["partial"] != sum(values[k] for k in ("k1","k2_4","k5_12","k13_16")):
        return None
    if values["rsent"]>values["rplanned"]:
        return None
    return {k:values[k] for k in fields}





def tcp_socket_state_counts(output):
    """Only count TCP states, never persist inner addresses/ports or payload."""
    allowed={"LISTEN","SYN-SENT","SYN-RECV","ESTAB","FIN-WAIT-1",
             "FIN-WAIT-2","CLOSE-WAIT","CLOSING","LAST-ACK","TIME-WAIT","CLOSED"}
    result={}
    for line in output.splitlines():
        cols=line.split()
        if cols and cols[0].upper() in allowed:
            state=cols[0].upper()
            result[state]=result.get(state,0)+1
    return result


def tcp_kernel_progress_counts(raw):
    """From ss -H -tin: aggregate kernel TCP_INFO numbers; NEVER retain peers.

    A field absent from the kernel output is NOT_OBSERVED, not numeric zero.
    Per-socket endpoint lines are read only in memory and immediately dropped.
    """
    fields=("bytes_sent","bytes_acked","bytes_received","notsent",
            "unacked","cwnd","snd_wnd","rto","mss","advmss","pmtu",
            "rcvmss","ssthresh","reordering","rcv_space","dsack_dups")
    blocks=[]
    current=None
    for line in raw.splitlines():
        if line.startswith("ESTAB ") or line.startswith("ESTAB\t"):
            if current is not None:
                blocks.append(current)
            current=[]
        elif current is not None and line[:1].isspace():
            current.append(line)
        else:
            if current is not None:
                blocks.append(current)
            current=None
    if current is not None:
        blocks.append(current)
    out={"established":len(blocks)}
    values={k:[] for k in fields}
    retrans=[]
    rtts=[]
    cc_counts={}
    for block in blocks:
        details=" ".join(block)
        cc=re.match(r"\s*(cubic|reno|bbr|bbr2|vegas|westwood|htcp)\b",details)
        if cc: cc_counts[cc.group(1)]=cc_counts.get(cc.group(1),0)+1
        matched_rtt=re.search(r"(?<![a-zA-Z0-9_])rtt:(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)",details)
        if matched_rtt: rtts.append(float(matched_rtt.group(1)))
        for name in fields:
            found=re.search(r"(?<![a-zA-Z0-9_])"+name+r":(\d+)(?![0-9])",details)
            if found:
                values[name].append(int(found.group(1)))
        match=re.search(r"(?<![a-zA-Z0-9_])retrans:(\d+)/(\d+)",details)
        if match:
            retrans.append((int(match.group(1)),int(match.group(2))))
    for name in fields:
        v=values[name]
        out[name]={"sampled_sockets":len(v),"sum":sum(v),"max":max(v)} if v else "NOT_OBSERVED"
    out["retrans"]={"sampled_sockets":len(retrans),
                    "in_flight_sum":sum(a for a,_ in retrans),
                    "total_sum":sum(b for _,b in retrans)} if retrans else "NOT_OBSERVED"
    out["rtt_ms"]={"sampled_sockets":len(rtts),
                   "max":max(rtts),"mean":sum(rtts)/len(rtts)} if rtts else "NOT_OBSERVED"
    out["congestion_algorithm_counts"]=cc_counts if cc_counts else "NOT_OBSERVED"
    return out


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
    def __init__(self, products, output, tcp_namespaces=None):
        self.products, self.output = products, output
        self.tcp_namespaces=tcp_namespaces or {}
        self.samples, self.stop = [], threading.Event()
        self.last_tcp_poll_ns=0
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            fields = read("/proc/stat").splitlines()[0].split()[1:]
            now=time.monotonic_ns()
            sample={"ns":now,"cpu":list(map(int,fields)),
                    "psi_cpu":read("/proc/pressure/cpu"),
                    "psi_memory":read("/proc/pressure/memory"),
                    "processes":{name:process(p.pid) for name,p in self.products.items()}}
            # Numeric TCP_INFO every 2s. Never persist raw addresses, ports,
            # payloads or secret-bearing socket output.
            if self.tcp_namespaces and now-self.last_tcp_poll_ns>=2_000_000_000:
                self.last_tcp_poll_ns=now
                sample["tcp"]={}
                for role,ns in self.tcp_namespaces.items():
                    try:
                        raw=command(["ip","netns","exec",ns,"ss","-H","-tin"],False)
                        sample["tcp"][role]=tcp_kernel_progress_counts(raw)
                    except (OSError,subprocess.SubprocessError):
                        sample["tcp"][role]="NOT_OBSERVED"
            self.samples.append(sample)
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
        tcp_summary={}
        for role in self.tcp_namespaces:
            rows=[p["tcp"][role] for p in samples
                  if isinstance(p.get("tcp",{}).get(role),dict)
                  and p["tcp"][role].get("established",0)>0]
            v={"samples":len(rows)}
            for key in ("cwnd","snd_wnd","notsent","mss","advmss","pmtu",
                        "ssthresh","unacked","rto","reordering"):
                vals=[p[key]["sum"] for p in rows if isinstance(p.get(key),dict)]
                if vals:
                    sorted_vals=sorted(vals)
                    v[key]={"min":sorted_vals[0],
                            "median":sorted_vals[len(sorted_vals)//2],
                            "max":sorted_vals[-1]}
                else: v[key]="NOT_OBSERVED"
            rtt=[p["rtt_ms"]["mean"] for p in rows if isinstance(p.get("rtt_ms"),dict)]
            v["rtt_ms"]={"min":min(rtt),"max":max(rtt)} if rtt else "NOT_OBSERVED"
            cc={}
            for p in rows:
                d=p.get("congestion_algorithm_counts")
                if isinstance(d,dict):
                    for name,n in d.items(): cc[name]=cc.get(name,0)+n
            v["congestion_algorithm_counts"]=cc if cc else "NOT_OBSERVED"
            tcp_summary[role]=v
        return {"cpu_psi_some_peak": peak_psi, "cpu_psi_some_mean": sum(psi)/len(psi) if psi else None,
                "cpu_psi_over20_fraction": sum(v > 20 for v in psi)/len(psi) if psi else None,
                "samples_in_measurement": len(samples), "steal_pct_peak": peak_steal,
                "processes": costs, "tcp_window_summary": tcp_summary or "NOT_OBSERVED"}


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
        self.config=copy.deepcopy(config)
        self.tcp_profile=config["network"].get("tcp_window_profiles",{}).get(label,"baseline")
        self.tcp_reorder_profile=config["network"].get("tcp_reordering_profiles",{}).get(label,"baseline")
        self.config["network"]["tcp_window_profile_selected"]=self.tcp_profile
        self.config["network"]["tcp_reordering_profile_selected"]=self.tcp_reorder_profile
        self.bundle = Path(bundle_dir) / "fixed-build"
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
        if self.tcp_profile=="large":
            # Restrict writes to per-netns IPv4 TCP autotuning limits.
            # Do NOT attempt net.core *mem_max writes: the ARM runner failed
            # that readback before business; user socket SO_*BUF is clamped,
            # so report actual getsockopt bytes instead of claiming 8MiB.
            settings=(("net.ipv4.tcp_rmem","4096 4194304 16777216"),
                      ("net.ipv4.tcp_wmem","4096 4194304 16777216"))
            for role in self.ns:
                for k,value in settings:
                    self.nscommand(role,["sysctl","-w",k+"="+value])
                    actual=self.nscommand(role,["sysctl","-n",k]).strip()
                    if actual.split()!=value.split():
                        raise RuntimeError("namespaced TCP window readback mismatch "+k)
        if self.tcp_reorder_profile=="outer_repair_tolerant":
            # Experimental per-netns Linux TCP threshold. Not product default.
            # At 10Mbps/MSS1277, 192 in-flight segments span ~196ms,
            # comparable to the extra forward path of one outer repair.
            for role in self.ns:
                key="net.ipv4.tcp_reordering"
                self.nscommand(role,["sysctl","-w",key+"=192"])
                if self.nscommand(role,["sysctl","-n",key]).strip()!="192":
                    raise RuntimeError("namespaced TCP reordering readback mismatch")
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
        self.effective["tcp_window_profile"]=self.tcp_profile
        self.effective["tcp_reordering_profile"]=self.tcp_reorder_profile
        self.effective["tcp_window_override"]="namespaced tcp_[rw]mem 16MiB max; socket requested 8MiB but SO_*BUF may be kernel-clamped (read back)" if self.tcp_profile=="large" else "untouched baseline"
        dump(self.out / "effective-config.json", self.effective)
        inner = min(links[0]["mtu"] for links in self.effective["inner_links"].values())
        dump(self.out / "capacity-envelope-observed-mtu.json", request_envelope(self.config, inner))

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
                "tcp_states": tcp_socket_state_counts(self.nscommand(role, ["ss", "-H", "-tan"], False)),
                "tcp_kernel_progress": tcp_kernel_progress_counts(self.nscommand(role, ["ss", "-H", "-tin"], False)),
                "blackhole_counters": self.nscommand(role, ["iptables", "-nvxL", "WBN_LOSS"])}
        if name.startswith("before-"):
            settings=("tcp_congestion_control","tcp_available_congestion_control",
                      "tcp_mtu_probing","tcp_sack","tcp_timestamps",
                      "tcp_window_scaling","tcp_rmem","tcp_wmem",
                      "tcp_reordering","tcp_max_reordering","tcp_recovery")
            row["tcp_kernel_settings"]={
                role:{**{k:self.nscommand(role,["sysctl","-n","net.ipv4."+k],False).strip()
                      or "NOT_OBSERVED" for k in settings},
                      **{k:self.nscommand(role,["sysctl","-n","net.core."+k],False).strip()
                      or "NOT_OBSERVED" for k in ("rmem_max","wmem_max")}}
                for role in self.ns}
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
                     if product_marker_line(line)]
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
        recovery_policy = {}
        for role, log in logs.items():
            lines = [s for s in log.splitlines() if "V4_PUBLIC_M2_OUTER " in s or "V4_PUBLIC_GAME_KERNEL " in s]
            counters[role] = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", lines[-1])} if lines else {}
            outer = [s for s in log.splitlines() if "V4_PUBLIC_M2_OUTER " in s]
            if outer:
                m = re.search(r"policy=([A-Za-z0-9_.-]+)", outer[-1])
                if m:
                    recovery_policy[role] = {
                        "policy": m.group(1),
                        **{k: int(v) for k, v in re.findall(
                            r"(repair_attempt_limit|shadow_limit|retain_cap_us)=(\d+)", outer[-1])},
                    }
        rx_chain={}
        required_rx=("raw_observed","raw_tuple","data_unique","data_lagged32",
                     "link_completed","tun_delivered","link_pending",
                     "link_malformed","link_discarded","tun_failed",
                     "replay_duplicate","replay_retired","open_invalid",
                     "feedback_retained_pages","feedback_dropped",
                     "tun_udp","tun_tcp","tun_other")
        for role,log in logs.items():
            chain=[line for line in log.splitlines() if "V4_PUBLIC_RX_CHAIN " in line]
            if chain:
                row={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",chain[-1])}
                if all(k in row for k in required_rx):
                    rx_chain[role]=row
        tx_chain={}
        tx_fields=("tun_udp","tun_tcp","tun_other","tun_rejected",
                   "arena_failed","staged_udp","staged_tcp")
        for role,log in logs.items():
            lines=[line for line in log.splitlines() if "V4_PUBLIC_TX_CHAIN " in line]
            if lines:
                row={k:int(v) for k,v in re.findall(r"([a-z0-9_]+)=(\d+)",lines[-1])}
                if all(k in row for k in tx_fields): tx_chain[role]=row
        m1_pool={}
        for role,log in logs.items():
            rows=[line for line in log.splitlines() if "V4_PUBLIC_M1_POOL " in line]
            if rows:
                v={k:int(n) for k,n in re.findall(r"([a-z0-9_]+)=(\d+)",rows[-1])}
                if all(k in v for k in ("slots","peak_loaned","charged_bytes",
                                        "normal_control_reserve")):
                    m1_pool[role]=v
        requested_policy = self.config["bundles"][self.label].get(
            "recovery_policy", self.config.get("policy"))
        policy_verified = verify_outer_recovery_policy(
            requested_policy, recovery_policy)
        if policy_verified is False:
            verified = False
        repair = sum(v["original_frozen_retransmitted"] for v in counters.values()) if all("original_frozen_retransmitted" in v for v in counters.values()) else None
        fec_tx = {role:public_fec_tx_snapshot(log) for role,log in logs.items()}
        tx_available = all(v is not None for v in fec_tx.values())
        fec_failures = {role:public_fec_failure_reasons(log) for role,log in logs.items()}
        fec_m2 = {role:public_fec_m2_proof(log) for role,log in logs.items()}
        fec_rx = {role:public_fec_rx_proof(log) for role,log in logs.items()}
        fec_ip = {role:public_fec_rx_ip_class(log) for role,log in logs.items()}
        fec_m1 = {role:public_fec_m1_ingress(log) for role,log in logs.items()}
        fec_stage = {role:public_fec_m1_stage(log) for role,log in logs.items()}
        fec_class_valid = all(fec_ip[role] is not None and fec_rx[role] is not None and
            (sum(fec_ip[role][k] for k in ("sys_udp","rec_udp","sys_tcp","rec_tcp","other_ip")) ==
             fec_rx[role]["systematic_tun"]+fec_rx[role]["recovered_tun"])
            for role in logs)
        return {"stop_drained_both": all(("V4_PUBLIC_GAME_NATIVE_STOP_DRAINED" if self.lanes > 1 else "V4_PUBLIC_NATIVE_STOP_DRAINED") in s for s in logs.values()),
                "effective_config_verified": verified, "fec_final_readback": applied, "counters": counters,
                "recovery_policy_readback": recovery_policy,
                "original_rx_chain": rx_chain if len(rx_chain)==2 else "NOT_OBSERVED",
                "original_tx_chain": tx_chain if len(tx_chain)==2 else "NOT_OBSERVED",
                "original_m1_pool": m1_pool if len(m1_pool)==2 else "NOT_OBSERVED",
                "recovery_policy_verified": policy_verified,
                "recovery_policy_expected": requested_policy or "NOT_DECLARED",
                "repair_packets": repair,
                "original_m2_authenticated_coverage": fec_m2 if all(v is not None for v in fec_m2.values()) else "NOT_OBSERVED",
                "original_fec_rx_m3_m4_proof": fec_rx if all(v is not None for v in fec_rx.values()) else "NOT_OBSERVED",
                "original_fec_rx_ipv4_classes": fec_ip if fec_class_valid else "NOT_OBSERVED",
                "original_fec_m1_tun_ingress": fec_m1 if all(v is not None for v in fec_m1.values()) else "NOT_OBSERVED",
                "original_fec_m1_postloan_stage": fec_stage if all(v is not None for v in fec_stage.values()) else "NOT_OBSERVED",
                "repair_wire_bytes_and_10pct_budget": "NOT_OBSERVED",
                "repair_useful_spurious_and_latency": "NOT_OBSERVED",
                "FEC_k_r_parity_queue_decode": {
                    "real_tx_owner_end_snapshot": fec_tx,
                    "real_tx_fail_reasons": fec_failures,
                    "real_rx_decode_and_parity_age": "NOT_OBSERVED"
                } if tx_available else "NOT_OBSERVED",
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
            self.monitor = Monitor({**self.products, **{r + "-injector": p for r, p in self.workers.items()}}, self.out, self.ns)
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
            steady_start=next((p for p in self.snapshots if
                p["name"]=="before-"+self.config["phases"][0]["name"]),None)
            steady_end=next((p for p in self.snapshots if
                p["name"]=="measurement-end"),None)
            if steady_start is not None and steady_end is not None:
                drops=source_tun_tx_drops_by_role(steady_start,steady_end)
                result["source_tun_tx_drops_steady"]=drops
                if any(isinstance(n,int) and n>0 for n in drops.values()):
                    result["limits"].append("SOURCE_TUN_TX_DROPS: kernel upstream loss before product")
                    if result["result"]=="PASS_SCOPED_OBSERVATION":
                        result["result"]="INCONCLUSIVE"
            result["tcp_window_profile"]=self.tcp_profile
            result["tcp_reordering_profile"]=self.tcp_reorder_profile
            result["socket_effective_buffers"]={
                role:json.loads((self.out/(role+"-traffic.json")).read_text()).get("effective_buffers",{})
                for role in ("client","server")}
            before=[v for v in self.snapshots if v["name"]=="before-"+self.config["phases"][0]["name"]]
            result["tcp_kernel_settings"]=before[0].get("tcp_kernel_settings","NOT_OBSERVED") if before else "NOT_OBSERVED"
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


def source_tun_tx_drops_by_role(before,after):
    """Exact steady kernel source TUN TX loss, before product can read it."""
    result={}
    for role in ("client","server"):
        def count(snapshot):
            links=snapshot.get("network",{}).get(role,{}).get("links",[])
            dev=next((p for p in links if p.get("ifname")=="wbntun0"),None)
            if not dev: return None
            stats=dev.get("stats64",dev.get("stats",{}))
            return stats.get("tx",{}).get("dropped")
        x,y=count(before),count(after)
        result[role]=y-x if isinstance(x,int) and isinstance(y,int) and y>=x else "NOT_OBSERVED"
    return result


def capacity_action_digest(leg):
    """Small source-bounded numeric evidence in the Actions log, in addition
    to the ordinary artifact. No packet payloads, addresses or credentials.
    The log must distinguish host, injector and product capacity even when
    a result is INCONCLUSIVE and artifact retrieval is unavailable.
    """
    host = leg.get("host", {})
    proc = host.get("processes", {})
    costs = leg.get("measurement_cost", {})
    telemetry = leg.get("telemetry", {})
    rows = []
    for row in leg.get("observed", []):
        rows.append({
            "direction": row.get("direction"), "protocol": row.get("protocol"),
            "phase": row.get("phase"),
            "target_mbps": row.get("target_app_mbps"),
            "injected_mbps": row.get("injected_app_mbps"),
            "delivered_mbps": row.get("cohort_delivered_app_mbps"),
            "missing": row.get("missing_after_drain"),
            "arrival_p99_ms": row.get("first_arrival_ms", {}).get("p99_ms"),
            "send_lag_p99_ms": row.get("send_lag_ms", {}).get("p99_ms"),
            "tcp_backpressure": row.get("tcp_backpressure_slots"),
            "app_send_errors": row.get("send_errors"),
        })
    netem = []
    for item in leg.get("network_accounting", []):
        for q in item.get("netem", []):
            netem.append({"role": item.get("role"),
                "phase": item.get("phase"), "netem_drop_pct": q.get("approx_loss_pct"),
                "backlog_packets": q.get("end_qlen"),
                "backlog_bytes": q.get("end_backlog_bytes"),
                "kernel_delta": item.get("kernel_delta", {})})
    return {
        "label": leg.get("label"), "result": leg.get("result"),
        "limits": leg.get("limits", [])[:16],
        "failures": leg.get("failures", [])[:16],
        "warnings": leg.get("warnings", [])[:8],
        "stop_heavier_resource_cases": leg.get("stop_heavier_resource_cases"),
        "observed": rows, "netem": netem,
        "measurement_cpu": {
            role: {"cpu_s": costs.get(role, {}).get("cpu_s"),
                   "cpu_s_per_delivered_GiB":
                        costs.get(role, {}).get("cpu_s_per_delivered_GiB"),
                   "outer_tx_bytes":
                        costs.get(role, {}).get("outer_interface_tx_bytes")}
            for role in ("client", "server")},
        "source_tun_tx_drops_steady":leg.get("source_tun_tx_drops_steady","NOT_OBSERVED"),
        "tcp_window_profile":leg.get("tcp_window_profile","NOT_OBSERVED"),
        "tcp_reordering_profile":leg.get("tcp_reordering_profile","NOT_OBSERVED"),
        "socket_effective_buffers":leg.get("socket_effective_buffers","NOT_OBSERVED"),
        "tcp_kernel_settings":leg.get("tcp_kernel_settings","NOT_OBSERVED"),
        "host": {"tcp_window_summary":host.get("tcp_window_summary","NOT_OBSERVED"),
                 "cpu_psi_peak": host.get("cpu_psi_some_peak"),
                 "cpu_psi_over20_fraction": host.get("cpu_psi_over20_fraction"),
                 "steal_pct_peak": host.get("steal_pct_peak"),
                 "processes": {
                     name: {"cpu_s_including_setup":
                                proc.get(name, {}).get("cpu_s_observed_including_warmup_setup_drain"),
                            "peak_rss_bytes": proc.get(name, {}).get("rss_peak_bytes")}
                     for name in ("client", "server", "client-injector", "server-injector")}},
        "original_tx_chain": telemetry.get("original_tx_chain", "NOT_OBSERVED"),
        "original_m1_pool": telemetry.get("original_m1_pool", "NOT_OBSERVED"),
        "original_rx_chain": telemetry.get("original_rx_chain", "NOT_OBSERVED"),
        "repair_packets": telemetry.get("repair_packets"),
        "stop_drained_both": telemetry.get("stop_drained_both"),
        "policy_verified": telemetry.get("recovery_policy_verified"),
        "owned_cleanup": leg.get("cleanup", {}).get("owned_namespaces_absent"),
    }


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
        dump(directory / "capacity-envelope.json", request_envelope(config))
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
    # The bounded digest survives in the job log when an artifact retrieval
    # backend fails; do not make a different Action just to fetch raw results.
    for leg in results:
        print("NETWORK_CAPACITY_LEG " +
              json.dumps(capacity_action_digest(leg), sort_keys=True), flush=True)
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
