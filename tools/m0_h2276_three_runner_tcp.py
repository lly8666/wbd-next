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
import socket

import m0_wl_loss_tcp_probe as tcp

# Historical H2228 tailnet CI routes proved TCP 18727 and VXLAN UDP 4789.
# Override the *test-only* imported H2271 socket port in this Python process;
# the actual Windows/WSL2 product test at TCP 45902 remains unchanged.
PORT = 18727
tcp.PORT = PORT
# H2281: only on explicit 2x3 native sustained-capacity workflow.
# Original Wintun/WSL product diagnostic keeps historical 24MiB/18s shape.
SUSTAINED = os.environ.get("WBD_H2281_SUSTAINED_TCP") == "1"
WINDOW_AB = os.environ.get("WBD_H2282_TCP_WINDOW_AB") == "1"
if SUSTAINED:
    tcp.BULK_MAX_BYTES = 512 * 1024 * 1024  # per flow, four independent real TCP sockets
    tcp.BULK_SEND_S = 25
    tcp.TIMEOUT_S = 150
CONTROL_PORT = 4789
TIERS = (-1, 0, 1, 5)  # -1 = no-loss/no-added-delay infrastructure capacity reference


def active_stages():
    """H2282 three 400ms zero-loss TCP socket-window AB/A-prime, else old modes."""
    if WINDOW_AB:
        return ("base", "tuned", "base_prime")
    return ("direct", -1) if os.environ.get("WBD_H2279_CAPACITY_AB")=="1" else TIERS


def actual_loss_tier(stage):
    return 0 if isinstance(stage, str) else stage


def prepare_tcp_sockbuf(stage):
    # Only the *test app* socket knobs; no WBD runtime/GoTLS changes.
    tcp.WINDOW_TEST_BYTES = 8 * 1024 * 1024 if WINDOW_AB and stage=="tuned" else 0



def server_expected_tcp_peer(stage, relay):
    return relay["client_ip"] if stage=="direct" else relay["relay_ip"]


def client_tcp_target(stage, relay, server):
    return server["tail_ip"] if stage=="direct" else relay["relay_ip"]
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
            (role == "relay" and os.name == "posix" and arch in ("aarch64", "arm64")),
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
    # Give NAT traversal its original bounded direct-discovery window.
    # Nonzero Tailscale return code can still contain genuine DERP pongs:
    # that is DERP, NOT 'no tail pong'.
    p = run("tailscale", "ping", "--c", "12", ip, timeout=50, tolerate=True)
    rows = [x.strip() for x in p.stdout.splitlines()
            if x.strip().startswith("pong from ")]
    last = rows[-1] if rows else ""
    if not last:
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
    # H2280: the old reverse filter matched src=ARM AFTER conntrack
    # reverse-SNAT, when the actual egress src is RELAY. It missed every
    # reverse ACK/data packet; prior "200ms both ways" was ONE-WAY ONLY.
    # Two isolated egress netem bands (3 & 4), verified by real counters.
    # Default band 2 carries no impairment, including OIDC/control.
    run("sudo", "-n", "tc", "qdisc", "replace", "dev", "tailscale0",
        "root", "handle", "1:", "prio", "bands", "4",
        "priomap", *(["1"] * 16))
    run("sudo", "-n", "tc", "filter", "add", "dev", "tailscale0",
        "parent", "1:", "protocol", "ip", "prio", "1", "u32",
        "match", "ip", "protocol", "6", "0xff",
        "match", "ip", "dst", arm + "/32",
        "match", "ip", "dport", str(PORT), "0xffff", "flowid", "1:3")
    run("sudo", "-n", "tc", "filter", "add", "dev", "tailscale0",
        "parent", "1:", "protocol", "ip", "prio", "2", "u32",
        "match", "ip", "protocol", "6", "0xff",
        "match", "ip", "src", relay + "/32",
        "match", "ip", "dst", win + "/32",
        "match", "ip", "sport", str(PORT), "0xffff", "flowid", "1:4")
    shaped(0)
    return dict(**own, relay_ip=relay,
                server_ip=arm, client_ip=win, tcp_port=PORT,
                control_port=CONTROL_PORT,
                forwarding="KERNEL_TCP_DNAT_SNAT_NOT_APP_TCP_PROXY",
                netem_only="CLASSIFIED_TCP_BOTH_DIRECTIONS_TAILSCALE0_BANDS3_AND4",
                other_traffic="UNSHAPED_DEFAULT_BAND2",
                endpoint_transport="REAL_WIN_WINSOCK_TO_ARM_KERNEL_TCP",
                same_source=True, direct_candidate=ping_class(arm))


def netem_by_direction(qdiscs):
    """One actual kernel netem per NAT-adjusted egress direction."""
    require(isinstance(qdiscs, list), "KERNEL_QDISC_NOT_JSON_ARRAY")
    expected = {"win_to_arm": ("1:3", "30:"),
                "arm_to_win": ("1:4", "40:")}
    result = {}
    for direction, (parent, handle) in expected.items():
        hits = [q for q in qdiscs if q.get("kind") == "netem" and
                q.get("parent") == parent and q.get("handle") == handle]
        if len(hits) == 1:
            result[direction] = hits[0]
    return result


def netem_phase_receipt(before, after, stage):
    """Fail closed if either REAL TCP direction bypassed qdisc.

    These are Linux egress packet counts and netem losses, not distinct
    app messages or an estimate of WBD internal packet loss.
    """
    a = netem_by_direction(before)
    b = netem_by_direction(after)
    require(set(a) == set(b) == {"win_to_arm", "arm_to_win"},
            "NETEM_TWO_DIRECTION_READBACK_ABSENT")
    result = {}
    for direction in ("win_to_arm", "arm_to_win"):
        old, new = a[direction], b[direction]
        packets = new.get("packets", 0) - old.get("packets", 0)
        drops = new.get("drops", 0) - old.get("drops", 0)
        require(isinstance(packets, int) and isinstance(drops, int) and
                packets > 0 and drops >= 0,
                "NETEM_" + direction.upper() + "_NO_REAL_TRAFFIC")
        # netem "packets" counts emitted packets; drops are separately tracked.
        result[direction] = {"egress_packets": packets,
                             "intentional_netem_drops": drops,
                             "drop_percent_observed": round(
                                 100 * drops / (packets + drops), 4)}
        if stage in (1, 5):
            require(drops > 0,
                    "NETEM_" + direction.upper() + "_LOSS_NO_ACTUAL_DROPS")
    return {"status": "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",
            "stage_id": stage, "per_direction": result,
            "scope": "ACTUAL_RELAY_KERNEL_EGRESS_NOT_WBD_OR_APP_DROP"}


def shaped(loss):
    require(loss in TIERS, "LOSS_TIER_NOT_ALLOWED")
    delay = 0 if loss == -1 else 200
    pct = max(0, loss)
    for band, handle in (("1:3", "30:"), ("1:4", "40:")):
        run("sudo", "-n", "tc", "qdisc", "replace", "dev", "tailscale0",
            "parent", band, "handle", handle, "netem",
            "delay", str(delay) + "ms", "loss", str(pct) + "%",
            "limit", "65536")
    readback = tc_read()
    require(set(netem_by_direction(readback)) == {"win_to_arm", "arm_to_win"},
            "NETEM_TWO_INDEPENDENT_KERNEL_DIRECTIONS_NOT_INSTALLED")
    return dict(loss_pct=pct, stage_id=loss, one_way_delay_ms=delay,
                real_bidir_kernel_netem=True,
                qdisc=readback, ts=time.monotonic())


def observed_relay_counters(own):
    """Read scoped local kernel counters after actual attempted TCP traffic."""
    rows = {}
    for table, chain in (("nat", "PREROUTING"),
                         ("nat", "POSTROUTING"),
                         ("filter", "FORWARD")):
        proc = run("sudo", "-n", "iptables", "-t", table, "-L", chain,
                   "-v", "-n", "-x", timeout=8, tolerate=True)
        selected = []
        for line in proc.stdout.splitlines():
            words = line.split()
            if (len(words) >= 8 and words[0].isdigit() and
                    words[1].isdigit() and
                    str(PORT) in line and
                    (own["tail_ip"] in line or
                     own["tail_ip"] not in line and "dpt:" in line)):
                selected.append({"packets": int(words[0]),
                                 "bytes": int(words[1]),
                                 "port": PORT})
        rows[table + "_" + chain] = {
            "read_rc": proc.returncode, "matched_rules": selected}
    return {"kernel_tc": tc_read(),
            "owned_tcp_forward_rule_counters": rows,
            "qdisc_permitted_counters_only": True}


def control_service(own):
    """UDP 4789 Tailscale control, separate from ACL-proven TCP 18727 data.

    The old H2228 bridge used UDP VXLAN 4789 and TCP control18727. This
    diagnostic instead uses UDP for tiny phase/readback messages, keeping the
    WBD-free end-to-end real TCP connection in native kernel DNAT/SNAT.
    """
    token = own["control_token"]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((own["tail_ip"], CONTROL_PORT))
        server.settimeout(600)
        print("H2276_RELAY_CONTROL_READY", flush=True)
        while True:
            request, addr = server.recvfrom(1200)
            try:
                item = json.loads(request)
                require(item.get("token") == token, "UNAUTHORIZED_CONTROL")
                if item.get("op") == "loss":
                    tier = item.get("loss")
                    require(type(tier) is int and tier in TIERS,
                            "BAD_LOSS_REQUEST")
                    output = shaped(tier)
                    save(ROOT / ("relay-loss" + str(tier) + ".json"), output)
                    result = {"loss": tier, "configured": True,
                              "netem": output}
                elif item.get("op") == "diag":
                    result = observed_relay_counters(own)
                else:
                    raise RuntimeError("H2276_UNKNOWN_CONTROL_COMMAND")
                server.sendto(json.dumps(result).encode(), addr)
            except Exception as error:
                server.sendto(json.dumps(
                    {"status": "FAIL_CONTROL", "type": type(error).__name__}
                ).encode(), addr)


def remote_command(relay, op, tier=None):
    payload = {"token": relay["control_token"], "op": op}
    if tier is not None:
        payload["loss"] = tier
    target = (relay["relay_ip"], CONTROL_PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(5)
        for _ in range(3):
            client.sendto(json.dumps(payload).encode(), target)
            try:
                raw, sender = client.recvfrom(35000)
            except socket.timeout:
                continue
            require(sender[0] == relay["relay_ip"] and
                    sender[1] == CONTROL_PORT, "CONTROL_REPLY_SOURCE")
            return json.loads(raw)
    raise RuntimeError("H2276_RELAY_UDP_CONTROL_NOT_REACHABLE")


def remote_shape(relay, tier):
    body = remote_command(relay, "loss", tier)
    require(body.get("configured") and body.get("loss") == tier,
            "KERNEL_IMPAIRMENT_NO_READBACK")
    return body


def remote_diag(relay):
    return remote_command(relay, "diag")


def run_server(own, relay):
    peer = verify(own, relay, "relay")
    original_sysctls = {}
    if WINDOW_AB:
        # Ephemeral native ARM VM, but restore test-owned sysctls on Stop.
        for key in ("net.core.rmem_max", "net.core.wmem_max"):
            original_sysctls[key] = run("sysctl", "-n", key).stdout.strip()
    result = []
    try:
        if WINDOW_AB:
            for key in original_sysctls:
                run("sudo", "-n", "sysctl", "-w", key + "=16777216")
        for tier in active_stages():
            prepare_tcp_sockbuf(tier)
            expected_peer = server_expected_tcp_peer(tier,relay)
            print("H2279_SERVER_TCP_STAGE "+
                  json.dumps({"stage":tier,"actual_peer":expected_peer}),
                  flush=True)
            before = time.process_time()
            host_before = os_host_cpu()
            t = time.monotonic()
            tcp.server(own["tail_ip"], expected_peer, own["source_sha"])
            result.append(dict(stage_id=tier,
                               loss_pct=actual_loss_tier(tier),
                               server_app_sockbuf_requested=tcp.WINDOW_TEST_BYTES,
                               actual_peer=expected_peer,
                               service_wall_s=round(time.monotonic() - t, 4),
                               python_service_cpu_s=round(time.process_time() - before, 4),
                               arm_host_allcore_busy_pct=cpu_busy_percent(
                                   host_before, os_host_cpu())))
    finally:
        for key, value in original_sysctls.items():
            run("sudo", "-n", "sysctl", "-w", key+"="+value)
        if original_sysctls:
            print("H2282_TEST_OWNED_ARM_SYSCTL_RESTORED", flush=True)
    save(ROOT / "server-result.json", dict(
        source_sha=own["source_sha"], run_id=own["run_id"],
        group=own["group"], stages=result, real_native_arm=True,
        no_product_go_rust_claim=True,
        h2282_restore_owned_arm_sysctls=bool(original_sysctls)))
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
    if observation["network_tailscale_client_relay"]["status"] != "DIRECT_CANDIDATE":
        observation["status"] = "INFRA_DERP_UNQUALIFIED_SKIP_WAN_TESTS"
        observation["skip_reason"] = "WINDOWS_TO_RELAY_NOT_DIRECT_AFTER_12_DISCO_PROBES"
        save(ROOT / "client-result.json", observation)
        print("H2277_SKIP_SHARED_DERP_NOT_WBD_PERFORMANCE", flush=True)
        raise RuntimeError("H2277_INFRA_DERP_NO_VALID_3RUNNER_PERFORMANCE")
    for tier in active_stages():
        prepare_tcp_sockbuf(tier)
        target = client_tcp_target(tier,relay,server)
        loss_tier = actual_loss_tier(tier)
        shape = None if tier=="direct" else remote_shape(relay,loss_tier)
        time.sleep(0.5 if tier=="direct" else 2.0)
        buffer = io.StringIO()
        begin = time.monotonic()
        cpu0 = time.process_time()
        host_before = os_host_cpu()
        try:
            with contextlib.redirect_stdout(buffer):
                tcp.client(win, target, own["source_sha"])
        except Exception as exc:
            observation["status"] = "FAIL_REAL_TCP_FORWARDING_NOT_PRODUCT_PERF"
            observation["failed_stage"] = tier
            observation["client_exception_type"] = type(exc).__name__
            try:
                observation["relay_after_failure"] = remote_diag(relay)
            except Exception as diag_error:
                observation["relay_diag_error"] = type(diag_error).__name__
            save(ROOT / "client-result.json", observation)
            raise
        evidence = buffer.getvalue()
        rows = [json.loads(s.split(tcp.MARK + "CLIENT_DONE ", 1)[1])
                for s in evidence.splitlines()
                if tcp.MARK + "CLIENT_DONE " in s]
        require(len(rows) == 1 and rows[0]["sparse_echo_received"] == 160 and
                rows[0]["bind"] == win and rows[0]["peer"] == target,
                "MISSING_REAL_TCP_CLIENT_RESULT")
        if SUSTAINED:
            require(rows[0]["bulk_wall_s"] >= 15.0 and
                    rows[0]["bulk_remote_received_bytes"] > 0,
                    "SUSTAINED_BULK_DID_NOT_OVERLAP_160_ECHO_WINDOW")
        try:
            receipt = None if tier == "direct" else netem_phase_receipt(
                shape["netem"]["qdisc"], remote_diag(relay)["kernel_tc"], loss_tier)
            if loss_tier in (0, 1, 5):
                require(rows[0]["sparse_tcp_rtt_p50_ms"] >= 350,
                        "BOTH_200MS_EGRESS_CLASSES_NOT_REFLECTED_IN_TCP_RTT")
        except Exception as topology_exc:
            observation["status"] = "INFRA_UNQUALIFIED_KERNEL_NETEM_DIRECTION"
            observation["failed_stage"] = tier
            observation["topology_error"] = str(topology_exc)
            save(ROOT / "client-result.json", observation)
            raise
        row = dict(stage_id=tier,
                   relay_kernel_loss_receipt=receipt,
                   loss_pct=loss_tier,
                   socket_buffer_requested_bytes=tcp.WINDOW_TEST_BYTES,
                   tcp_path=("DIRECT_OS_TAILNET_ARM" if tier=="direct" else
                             "OS_KERNEL_DNAT_SNAT_RELAY"),
                   delivered=rows[0],
                   native_tcp_bulk_timed_supply_s=(tcp.BULK_SEND_S if SUSTAINED else None),
                   native_tcp_max_bytes_per_flow=tcp.BULK_MAX_BYTES,
                   sparse_echo_inside_bulk_window=(
                       rows[0]["bulk_wall_s"] >= 15.0 if SUSTAINED else None),
                   client_python_cpu_s=round(time.process_time()-cpu0, 4),
                   windows_host_allcore_busy_pct=cpu_busy_percent(
                       host_before, os_host_cpu()),
                   stage_wall_s=round(time.monotonic()-begin, 4),
                   actual_kernel_shape=(shape["netem"]["qdisc"]
                                        if shape is not None else None))
        observation["stages"].append(row)
        save(ROOT / "client-result.json", observation)
        print("H2276_NATIVE_WINDOWS_TCP_RECEIVER_RESULT " +
              json.dumps({"group": own["group"], "loss": tier,
                          "mbps": rows[0]["bulk_receiver_goodput_mbps"],
                          "tcp_p99_ms": rows[0]["sparse_tcp_rtt_p99_ms"],
                          "late_over_1s": rows[0]["sparse_tcp_late_1000ms"],
                          "client_app_cpu_seconds": row["client_python_cpu_s"]},
                         sort_keys=True), flush=True)
    require([row["stage_id"] for row in observation["stages"]] ==
            list(active_stages()), "MISSING_SOURCE_LOCKED_TCP_STAGES")
    if WINDOW_AB:
        require([x["stage_id"] for x in observation["stages"]]==
                ["base","tuned","base_prime"], "WINDOW_AB_A_PRIME_STAGES_MISSING")
        base,tuned,rebound=observation["stages"]
        for leg in (base,tuned,rebound):
            require(leg["relay_kernel_loss_receipt"]["status"] ==
                    "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED" and
                    leg["delivered"]["sparse_echo_received"]==160,
                    "WINDOW_AB_REAL_TCP_QDISC_RECEIPT_MISSING")
        require((base["socket_buffer_requested_bytes"],
                 tuned["socket_buffer_requested_bytes"],
                 rebound["socket_buffer_requested_bytes"]) ==
                (0,8*1024*1024,0),"SOCKET_BUFFER_AB_NOT_APPLIED")
        default_mean=(base["delivered"]["bulk_receiver_goodput_mbps"]+
                      rebound["delivered"]["bulk_receiver_goodput_mbps"])/2
        require(default_mean>0,"SOCKET_AB_NO_VALID_DEFAULT_GOODPUT")
        os_bufs=tuned["delivered"].get("client_bulk_buffers_os",[])
        require(len(os_bufs)==4 and all(x["requested_bytes"]==8*1024*1024
                    and x["sndbuf_os"]>0 and x["rcvbuf_os"]>0
                    for x in os_bufs), "WINDOW_AB_NO_REAL_WINSOCK_READBACK")
        observation["window_ab"] = {
            "normal_mbps":base["delivered"]["bulk_receiver_goodput_mbps"],
            "tuned_mbps":tuned["delivered"]["bulk_receiver_goodput_mbps"],
            "normal_prime_mbps":rebound["delivered"]["bulk_receiver_goodput_mbps"],
            "gain_over_default_avg_pct":round(100*(tuned["delivered"]["bulk_receiver_goodput_mbps"]/default_mean-1),3),
            "os_windows_bulk_buffers_actual":os_bufs,
            "p99_ms":[x["delivered"]["sparse_tcp_rtt_p99_ms"] for x in (base,tuned,rebound)],
            "cpu_windows_allcore_busy_pct":[x["windows_host_allcore_busy_pct"] for x in (base,tuned,rebound)],
            "no_product_default_change":True}
        observation["status"]="PASS_H2282_REAL_NATIVE_WINSOCK_ARM_SOCKET_BUFFER_AB_SCOPED"
        observation["capacity_qualification"]="WINDOW_TUNING_CANDIDATE_ONLY_NOT_WBD_PRODUCT"
    elif os.environ.get("WBD_H2279_CAPACITY_AB")=="1":
        direct = observation["stages"][0]["delivered"]["bulk_receiver_goodput_mbps"]
        relayed = observation["stages"][1]["delivered"]["bulk_receiver_goodput_mbps"]
        require(direct>0 and relayed>0, "REAL_TCP_CAPACITY_NOT_POSITIVE")
        observation["direct_vs_relay"] = {
            "direct_mbps":direct,"kernel_relay_mbps":relayed,
            "relay_over_direct":round(relayed/direct,4),
            "same_real_windows_client_and_arm_server":True,
            "same_original_four_bulk_tcp_plus_160_sparse":True,
            "same_source_and_run_id":True,
            "no_added_loss_or_delay_both_legs":True}
        observation["status"]="PASS_H2279_REAL_NATIVE_DIRECT_VS_RELAY_SCOPED"
        observation["capacity_qualification"]=(
            "BOTH_DIRECT_AND_RELAY_AT_LEAST_800MBPS" if min(direct,relayed)>=800
            else "INFRA_UNQUALIFIED_NEEDS_NETWORK_ROUTE_CAPACITY")
    else:
        require(all(row["relay_kernel_loss_receipt"]["status"] ==
                    "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED"
                    for row in observation["stages"]),
                "WBD_TWO_NETEM_DIRECTIONS_SCOPE_INCOMPLETE")
        observation["status"] = ("PASS_H2281_SUSTAINED_REAL_BIDIR_KERNEL_TCP_SCOPED"
                                 if SUSTAINED else
                                 "PASS_H2280_REAL_BIDIR_KERNEL_NETEM_TCP_SCOPED")
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
