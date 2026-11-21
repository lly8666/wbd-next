#!/usr/bin/env python3
"""H2276 dual independent Windows -> Linux relay -> ARM Linux real TCP capacity.

The relay performs kernel DNAT/SNAT and only shapes forwarded TCP; it does
not terminate TCP. Each group has its own three GitHub VMs and ephemeral tail
IDs. This is a topology/capacity diagnostic, NOT a WBD Wintun/NPF product run.
Reuse H2271's real Winsock/Linux socket 4-bulk + 160-echo application.
"""
import argparse
import contextlib
import io
import ipaddress
import json
import os
import pathlib
import platform
import re
import secrets
import subprocess
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import m0_wl_loss_tcp_probe as tcp

PORT = tcp.PORT
CONTROL_PORT = 18727
TIERS = (-1, 0, 1, 5)  # -1 = no-loss/no-added-delay infrastructure capacity reference
ARM = "aarch64"
ROLES = ("client", "relay", "server")
TAIL = ipaddress.ip_network("100.64.0.0/10")
ROOT = pathlib.Path("h2276-out")


def require(ok, msg):
    if not ok:
        raise RuntimeError("H2276_" + msg)


def run(*args, timeout=40, tolerate=False):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True,
                       timeout=timeout)
    if p.returncode and not tolerate:
        raise RuntimeError("H2276_COMMAND_FAIL " + repr(args) + " " +
                           (p.stderr or p.stdout)[-750:])
    return p


def save(path, row):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def meta(group, role):
    require(group in ("a", "b") and role in ROLES, "ROLE_OR_GROUP")
    arch = platform.machine().lower()
    require((role == "server" and arch in ("aarch64", "arm64")) or
            (role == "client" and os.name == "nt" and arch in ("amd64", "x86_64")) or
            (role == "relay" and os.name == "posix" and arch == "x86_64"),
            "ACTUAL_OS_ARCH_ROLE")
    ip = run("tailscale", "ip", "-4").stdout.strip()
    addr = ipaddress.ip_address(ip)
    require(addr in TAIL, "ACTUAL_TAIL_IPV4")
    source = os.environ["GITHUB_SHA"]
    runid = os.environ["GITHUB_RUN_ID"]
    require(bool(re.fullmatch("[0-9a-f]{40}", source)) and
            bool(re.fullmatch("[1-9][0-9]{4,19}", runid)),
            "SOURCE_RUN_ID")
    result = dict(group=group, role=role, source_sha=source, run_id=runid,
                  os=platform.system(), arch=arch, tail_ip=ip,
                  topology="TWO_INDEPENDENT_THREE_RUNNER_WIN_RELAY_ARM",
                  product_source="NOT_RUN_WIN_WINTUN_NPF")
    if role == "relay":
        result["control_token"] = secrets.token_hex(24)
    save(ROOT / (role + "-peer.json"), result)
    return result


def verify(own, peer, role):
    require(peer.get("role") == role and peer.get("group") == own["group"] and
            peer.get("source_sha") == own["source_sha"] and
            peer.get("run_id") == own["run_id"] and
            peer.get("topology") == own["topology"], "CROSS_GROUP_OR_SOURCE")
    require(ipaddress.ip_address(peer["tail_ip"]) in TAIL and
            peer["tail_ip"] != own["tail_ip"], "INVALID_OR_SAME_PEER")
    return peer["tail_ip"]



def os_host_cpu():
    """Actual host all-core busy/idle, separate from Python/process CPU."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class FileTime(ctypes.Structure):
            _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]
        idle, kernel, user = FileTime(), FileTime(), FileTime()
        fn = ctypes.WinDLL("kernel32", use_last_error=True).GetSystemTimes
        fn.argtypes = [ctypes.POINTER(FileTime)] * 3
        fn.restype = wintypes.BOOL
        require(bool(fn(ctypes.byref(idle), ctypes.byref(kernel),
                        ctypes.byref(user))), "WINDOWS_GET_SYSTEM_TIMES")
        def scalar(ft):
            return (int(ft.high) << 32) + int(ft.low)
        i, k, u = scalar(idle), scalar(kernel), scalar(user)
        return (i, (k - i) + u)
    row = pathlib.Path("/proc/stat").read_text().splitlines()[0].split()
    require(row[0] == "cpu" and len(row) >= 6, "LINUX_PROC_CPU")
    values = [int(v) for v in row[1:]]
    idle = values[3] + values[4]
    return (idle, sum(values) - idle)


def cpu_busy_percent(before, after):
    idle = after[0] - before[0]
    busy = after[1] - before[1]
    total = idle + busy
    require(idle >= 0 and busy >= 0 and total > 0, "HOST_CPU_TIME_NONMONOTONIC")
    return round(busy * 100 / total, 3)

def ping_class(ip):
    p = run("tailscale", "ping", "--c", "4", ip, timeout=25, tolerate=True)
    rows = [x.strip() for x in p.stdout.splitlines()
            if x.strip().startswith("pong from ")]
    last = rows[-1] if rows else ""
    if p.returncode or not last:
        status = "UNKNOWN_NO_TAIL_PONG"
    elif "via DERP" in last:
        status = "DERP_OR_RELAY_LIMIT"
    elif re.search(r"via (?:\d{1,3}\.){3}\d{1,3}:\d+", last):
        status = "DIRECT_CANDIDATE"
    else:
        status = "UNKNOWN_TAIL_PATH"
    return {"status": status, "last_reply": last[-200:],
            "run_returncode": p.returncode}


def tc_read():
    r = run("sudo", "-n", "tc", "-s", "-j", "qdisc", "show",
            "dev", "tailscale0")
    return json.loads(r.stdout)


def command_plan(arm, win, relay):
    """Do not change tailscale physical underlay, only this service's TCP."""
    require(len({arm, win, relay}) == 3, "THREE_IDENTITIES")
    for val in (arm, win, relay):
        require(ipaddress.ip_address(val) in TAIL, "TAIL_IP_SCOPE")
    nat = [
        ("-t", "nat", "-I", "PREROUTING", "1", "-i", "tailscale0",
         "-s", win + "/32", "-d", relay + "/32", "-p", "tcp",
         "--dport", str(PORT), "-j", "DNAT",
         "--to-destination", arm + ":" + str(PORT)),
        ("-t", "nat", "-I", "POSTROUTING", "1", "-o", "tailscale0",
         "-d", arm + "/32", "-p", "tcp", "--dport", str(PORT),
         "-j", "SNAT", "--to-source", relay),
        ("-I", "FORWARD", "1", "-i", "tailscale0", "-o", "tailscale0",
         "-s", win + "/32", "-d", arm + "/32", "-p", "tcp",
         "--dport", str(PORT), "-j", "ACCEPT"),
        ("-I", "FORWARD", "1", "-i", "tailscale0", "-o", "tailscale0",
         "-s", arm + "/32", "-d", win + "/32", "-p", "tcp",
         "--sport", str(PORT), "-j", "ACCEPT"),
    ]
    return nat


def configure_relay(own, server, client):
    arm = verify(own, server, "server")
    win = verify(own, client, "client")
    relay = own["tail_ip"]
    require(os.name == "posix", "LINUX_RELAY_REQUIRED")
    run("sudo", "-n", "sysctl", "-w", "net.ipv4.ip_forward=1")
    for row in command_plan(arm, win, relay):
        run("sudo", "-n", "iptables", *row)
    # The default band is unshaped. Only the original forwarded TCP data
    # and its reverse ACK are directed into band 3, not management/OIDC.
    run("sudo", "-n", "tc", "qdisc", "replace", "dev", "tailscale0",
        "root", "handle", "1:", "prio", "bands", "3",
        "priomap", *(["1"] * 16))
    run("sudo", "-n", "tc", "filter", "add", "dev", "tailscale0",
        "parent", "1:", "protocol", "ip", "prio", "1", "u32",
        "match", "ip", "protocol", "6", "0xff",
        "match", "ip", "dst", arm + "/32",
        "match", "ip", "dport", str(PORT), "0xffff", "flowid", "1:3")
    run("sudo", "-n", "tc", "filter", "add", "dev", "tailscale0",
        "parent", "1:", "protocol", "ip", "prio", "2", "u32",
        "match", "ip", "protocol", "6", "0xff",
        "match", "ip", "src", arm + "/32",
        "match", "ip", "sport", str(PORT), "0xffff", "flowid", "1:3")
    shaped(0)
    return dict(**own, relay_ip=relay,
                server_ip=arm, client_ip=win, tcp_port=PORT,
                control_port=CONTROL_PORT, control_token=own["control_token"],
                forwarding="KERNEL_TCP_DNAT_SNAT_NOT_APP_TCP_PROXY",
                netem_only="CLASSIFIED_FORWARDED_TCP_TAILSCALE0_BAND3",
                other_traffic="UNSHAPED_DEFAULT_BAND2",
                endpoint_transport="REAL_WIN_WINSOCK_TO_ARM_KERNEL_TCP",
                same_source=True, direct_candidate=ping_class(arm))


def shaped(loss):
    require(loss in TIERS, "LOSS_TIER_NOT_ALLOWED")
    delay = 0 if loss == -1 else 200
    pct = max(0, loss)
    run("sudo", "-n", "tc", "qdisc", "replace", "dev", "tailscale0",
        "parent", "1:3", "handle", "30:", "netem",
        "delay", str(delay) + "ms", "loss", str(pct) + "%",
        "limit", "65536")
    return dict(loss_pct=pct, stage_id=loss, one_way_delay_ms=delay,
                qdisc=tc_read(), ts=time.monotonic())


def control_service(own):
    """Single source-locked relay; control interface never enters netem band."""
    token = own["control_token"]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_POST(self):
            if self.path != "/loss" or self.headers.get("X-Run-Token") != token:
                self.send_error(403)
                return
            try:
                body = self.rfile.read(min(1024, int(
                    self.headers.get("Content-Length", "0"))))
                tier = json.loads(body)["loss"]
                require(type(tier) is int and tier in TIERS, "BAD_LOSS_REQUEST")
                output = shaped(tier)
                save(ROOT / ("relay-loss" + str(tier) + ".json"), output)
                raw = json.dumps({"loss": tier, "configured": True,
                                  "netem": output}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            except Exception as error:
                self.send_error(422, type(error).__name__)

    srv = ThreadingHTTPServer((own["tail_ip"], CONTROL_PORT), Handler)
    srv.daemon_threads = True
    print("H2276_RELAY_CONTROL_READY", flush=True)
    srv.serve_forever(poll_interval=0.2)


def remote_shape(relay, tier):
    request = urllib.request.Request(
        "http://" + relay["relay_ip"] + ":" + str(CONTROL_PORT) + "/loss",
        data=json.dumps({"loss": tier}).encode(),
        headers={"X-Run-Token": relay["control_token"],
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=25) as response:
        body = json.loads(response.read(20000))
    require(body["configured"] and body["loss"] == tier,
            "KERNEL_IMPAIRMENT_NO_READBACK")
    return body


def run_server(own, relay):
    peer = verify(own, relay, "relay")
    result = []
    for tier in TIERS:
        print("H2276_SERVER_STAGE_START " + str(tier), flush=True)
        before = time.process_time()
        host_before = os_host_cpu()
        t = time.monotonic()
        tcp.server(own["tail_ip"], peer, own["source_sha"])
        result.append(dict(loss_pct=tier,
                           service_wall_s=round(time.monotonic() - t, 4),
                           python_service_cpu_s=round(time.process_time() - before, 4),
                           arm_host_allcore_busy_pct=cpu_busy_percent(
                               host_before, os_host_cpu())))
    save(ROOT / "server-result.json", dict(
        source_sha=own["source_sha"], run_id=own["run_id"],
        group=own["group"], stages=result, real_native_arm=True,
        no_product_go_rust_claim=True))
    print("H2276_SERVER_ALL_TCP_STAGES_PASS", flush=True)


def run_client(own, relay, server):
    win = own["tail_ip"]
    endpoint = verify(own, relay, "relay")
    verify(own, server, "server")
    require(relay["relay_ip"] == endpoint and
            relay["client_ip"] == win and
            relay["server_ip"] == server["tail_ip"] and
            relay["source_sha"] == own["source_sha"] and
            relay["group"] == own["group"], "RELAY_TOPOLOGY_MISMATCH")
    observation = dict(source_sha=own["source_sha"], run_id=own["run_id"],
                       group=own["group"],
                       client_os="NATIVE_WINDOWS_2025_WINSOCK",
                       server_os="NATIVE_ARM64_LINUX_KERNEL_TCP",
                       relay_os="INDEPENDENT_LINUX_KERNEL_NAT_AND_TC",
                       first_delivery_scope="TCP_APPLICATION_BYTES_AND_160_ECHO",
                       product_go_tls_rust="NOT_RUN_THIS_PREFLIGHT",
                       network_tailscale_client_relay=ping_class(endpoint),
                       network_tailscale_client_server=ping_class(server["tail_ip"]),
                       stages=[])
    save(ROOT / "client-result.json", observation)
    for tier in TIERS:
        shape = remote_shape(relay, tier)
        time.sleep(2.0)
        buffer = io.StringIO()
        begin = time.monotonic()
        cpu0 = time.process_time()
        host_before = os_host_cpu()
        with contextlib.redirect_stdout(buffer):
            tcp.client(win, endpoint, own["source_sha"])
        evidence = buffer.getvalue()
        rows = [json.loads(s.split(tcp.MARK + "CLIENT_DONE ", 1)[1])
                for s in evidence.splitlines()
                if tcp.MARK + "CLIENT_DONE " in s]
        require(len(rows) == 1 and rows[0]["sparse_echo_received"] == 160 and
                rows[0]["bind"] == win and rows[0]["peer"] == endpoint,
                "MISSING_REAL_TCP_CLIENT_RESULT")
        row = dict(loss_pct=tier, delivered=rows[0],
                   client_python_cpu_s=round(time.process_time()-cpu0, 4),
                   windows_host_allcore_busy_pct=cpu_busy_percent(
                       host_before, os_host_cpu()),
                   stage_wall_s=round(time.monotonic()-begin, 4),
                   actual_kernel_shape=shape["netem"]["qdisc"])
        observation["stages"].append(row)
        save(ROOT / "client-result.json", observation)
        print("H2276_NATIVE_WINDOWS_TCP_RECEIVER_RESULT " +
              json.dumps({"group": own["group"], "loss": tier,
                          "mbps": rows[0]["bulk_receiver_goodput_mbps"],
                          "tcp_p99_ms": rows[0]["sparse_tcp_rtt_p99_ms"],
                          "late_over_1s": rows[0]["sparse_tcp_late_1000ms"],
                          "client_app_cpu_seconds": row["client_python_cpu_s"]},
                         sort_keys=True), flush=True)
    require([r["loss_pct"] for r in observation["stages"]] == list(TIERS),
            "NOT_ALL_THREE_RELAY_LOSS_STAGES")
    observation["status"] = "PASS_THREE_RUNNER_TCP_INFRA_SCOPED"
    observation["capacity_qualification"] = (
        "INFRA_CAPACITY_BELOW_800MBPS_NOT_PRODUCT_FAIL"
        if observation["stages"][0]["delivered"]["bulk_receiver_goodput_mbps"] < 800
        else "ROUTED_ZERO_LOSS_TCP_REFERENCE_AT_LEAST_800MBPS")
    save(ROOT / "client-result.json", observation)
    print("H2276_COMPLETE_ONE_REAL_WIN_RELAY_ARM_TRIPLET " +
          own["group"], flush=True)


def await_artifact(name, dest):
    """Wait only the artifact of this SAME workflow run, no cross-run reuse."""
    require(bool(re.fullmatch(r"h2276-[ab]-(?:client|relay|server)-(?:peer|ready|result)", name)),
            "ARTIFACT_NAME")
    dest = pathlib.Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for _ in range(130):
        p = run("gh", "run", "download", os.environ["GITHUB_RUN_ID"],
                "-R", os.environ["GITHUB_REPOSITORY"], "-n", name,
                "-D", str(dest), timeout=40, tolerate=True)
        if p.returncode == 0 and any(dest.glob("*.json")):
            print("H2276_SAME_RUN_ARTIFACT_RECEIVED " + name, flush=True)
            return
        time.sleep(4)
    raise RuntimeError("H2276_MISSING_SAME_RUN_ARTIFACT " + name)


def cleanup_relay(own, server, client):
    arm = verify(own, server, "server")
    win = verify(own, client, "client")
    rows = command_plan(arm, win, own["tail_ip"])
    for row in reversed(rows):
        # Do not delete a foreign chain; delete only exact installed rules.
        r = list(row)
        ix = r.index("-I")
        r[ix] = "-D"
        del r[ix + 2]
        run("sudo", "-n", "iptables", *r, tolerate=True)
    run("sudo", "-n", "tc", "qdisc", "del", "dev", "tailscale0",
        "root", tolerate=True)
    print("H2276_RELAY_OWNED_NETWORK_RULES_CLEANED", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("meta", "relay", "serve",
                                             "server", "client", "await", "cleanup"))
    parser.add_argument("group", choices=("a", "b"))
    parser.add_argument("role", choices=ROLES)
    parser.add_argument("peers", nargs="*")
    a = parser.parse_args()
    if a.command == "await":
        require(len(a.peers) == 2, "AWAIT_ARGS")
        await_artifact(*a.peers)
        return
    if a.command == "meta":
        require(not a.peers, "META_ARGS")
        meta(a.group, a.role)
        return
    own = load(ROOT / (a.role + "-peer.json"))
    require(own["group"] == a.group and own["role"] == a.role,
            "ACTUAL_ROLE_GROUP")
    if a.command == "cleanup":
        require(a.role == "relay" and len(a.peers) == 2, "CLEANUP_ARGS")
        cleanup_relay(own, load(a.peers[0]), load(a.peers[1]))
    elif a.command == "relay":
        require(a.role == "relay" and len(a.peers) == 2,
                "RELAY_ARGS")
        ready = configure_relay(own, load(a.peers[0]), load(a.peers[1]))
        save(ROOT / "relay-ready.json", ready)
        print("H2276_RELAY_SOURCE_LOCKED_READY", flush=True)
    elif a.command == "serve":
        require(a.role == "relay" and not a.peers, "SERVE_ARGS")
        control_service(own)
    elif a.command == "server":
        require(a.role == "server" and len(a.peers) == 1, "SERVER_ARGS")
        run_server(own, load(a.peers[0]))
    elif a.command == "client":
        require(a.role == "client" and len(a.peers) == 2, "CLIENT_ARGS")
        run_client(own, load(a.peers[0]), load(a.peers[1]))


if __name__ == "__main__":
    main()
