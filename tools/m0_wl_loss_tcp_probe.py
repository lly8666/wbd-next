#!/usr/bin/env python3
"""H2271: actual Windows Wintun <-> Linux TUN kernel TCP under owned netem.

Test application only. Four real sustained TCP sockets and a distinct 160-echo
TCP stream share the original Go TLS/Rust owner. No synthetic packet/ACK path.
Each client measures its own monotonic RTT; no cross-OS clock subtraction.
"""
import json
import math
import os
import pathlib
import socket
import struct
import subprocess
import sys
import threading
import time

PORT = 45902
BULK_FLOWS = 4
BULK_BLOCK = b"Z" * 16384
BULK_MAX_BYTES = 24 * 1024 * 1024
BULK_SEND_S = 18
ECHO_COUNT = 160
ECHO_PERIOD_S = 0.08
TIMEOUT_S = 100
# H2282 test-only per-stage override from independent 2x3 network wrapper.
# Never changes original signed Wintun/WSL2 product diagnostic by default.
WINDOW_TEST_BYTES = 0
# A full original remote Win-GoTLS-to-ARM-Rust start may need more setup than
# the old same-VM case; this timeout is test LISTEN only, not product code.
LISTENER_ACCEPT_TIMEOUT_S = 120 if os.environ.get("WBD_H2286_PRODUCT_FULL_WIN_ARM") == "1" else 35
# H2286 test-only SAME 4x25s REAL Windows Wintun <-> remote ARM TUN capacity.
# Not a WBD product knob. Explicitly isolate all historical H2273 smoke tests.
if os.environ.get("WBD_H2286_PRODUCT_FULL_WIN_ARM") == "1":
    BULK_MAX_BYTES = 512 * 1024 * 1024
    BULK_SEND_S = 25
    TIMEOUT_S = 180
    WINDOW_TEST_BYTES = 2 * 1024 * 1024
    if os.environ.get("WBD_H2302_WINDOW_ABA") == "1":
        chosen = int(os.environ.get("WBD_H2302_INNER_TCP_TEST_BYTES", "2097152"))
        if chosen not in (2*1024*1024, 8*1024*1024, 16*1024*1024):
            raise RuntimeError("H2302_UNSUPPORTED_TEST_WINDOW")
        WINDOW_TEST_BYTES = chosen


def _read_socket_buffers(sock):
    return {"requested_bytes": WINDOW_TEST_BYTES,
            "sndbuf_os": sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
            "rcvbuf_os": sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)}


def _maybe_set_buffers(sock):
    if WINDOW_TEST_BYTES:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, WINDOW_TEST_BYTES)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, WINDOW_TEST_BYTES)
    return _read_socket_buffers(sock)


MARK = "M029_H2271_NATIVE_TCP_"
TOKEN = 0x4D3032395F544350


def exact(sock, count):
    parts = []
    left = count
    while left:
        part = sock.recv(left)
        if not part:
            raise RuntimeError("H2271_KERNEL_TCP_EARLY_EOF")
        parts.append(part)
        left -= len(part)
    return b"".join(parts)


def quant(values, p):
    if not values:
        return None
    seq = sorted(values)
    return round(seq[max(0, math.ceil(len(seq) * p) - 1)], 3)


def server(bind_ip, client_ip, source):
    received = {"B": [], "E": []}
    errors = []
    lock = threading.Lock()
    accepted_buffers = []

    def handle(conn, peer):
        try:
            with conn:
                conn.settimeout(TIMEOUT_S)
                if peer[0] != client_ip:
                    raise RuntimeError("H2271_WRONG_REAL_TUNNEL_PEER")
                kind = exact(conn, 1)
                if kind == b"B":
                    with lock:
                        accepted_buffers.append(_read_socket_buffers(conn))
                    size = 0
                    while True:
                        data = conn.recv(65536)
                        if not data:
                            break
                        if data.count(90) != len(data):
                            raise RuntimeError("H2271_REAL_TCP_BULK_DATA_MISMATCH")
                        size += len(data)
                    conn.sendall(struct.pack("!Q", size))
                    with lock:
                        received["B"].append(size)
                elif kind == b"E":
                    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    for index in range(ECHO_COUNT):
                        frame = exact(conn, 16)
                        seq, token = struct.unpack("!QQ", frame)
                        if seq != index or token != TOKEN:
                            raise RuntimeError("H2271_REAL_TCP_ECHO_SEQUENCE_MISMATCH")
                        conn.sendall(frame)
                    with lock:
                        received["E"].append(ECHO_COUNT)
                else:
                    raise RuntimeError("H2271_UNKNOWN_REAL_TCP_APPLICATION")
        except Exception as exc:
            with lock:
                errors.append(type(exc).__name__ + ":" + str(exc))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener_buffers = _maybe_set_buffers(listener)
        listener.bind((bind_ip, PORT))
        listener.listen(max(16, BULK_FLOWS + 4))
        listener.settimeout(LISTENER_ACCEPT_TIMEOUT_S)
        print(MARK + "SERVER_READY " + json.dumps({
            "source_sha": source, "bind": bind_ip, "peer": client_ip,
            "real_kernel_tcp": True}), flush=True)
        workers = []
        for _ in range(BULK_FLOWS + 1):
            conn, peer = listener.accept()
            worker = threading.Thread(target=handle, args=(conn, peer))
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join(timeout=TIMEOUT_S)
        if any(worker.is_alive() for worker in workers):
            raise RuntimeError("H2271_REAL_TCP_SERVER_DRAIN_TIMEOUT")
    if errors or len(received["B"]) != BULK_FLOWS or received["E"] != [ECHO_COUNT]:
        raise RuntimeError("H2271_REAL_TCP_SERVER_INCOMPLETE " + repr(errors))
    print(MARK + "SERVER_DONE " + json.dumps({
        "source_sha": source, "bind": bind_ip, "peer": client_ip,
        "bulk_received_bytes": sum(received["B"]),
        "bulk_flows": BULK_FLOWS, "echo_received": ECHO_COUNT,
        "listener_buffers_os": listener_buffers,
        "accepted_bulk_buffers_os": accepted_buffers,
        "real_kernel_tcp": True}, sort_keys=True), flush=True)


def client(bind_ip, target_ip, source):
    bulk = []
    errors = []
    lock = threading.Lock()
    client_bulk_buffers = []
    # H2306 test-only per-flow progress: never alters the original product.
    progress_enabled=os.environ.get("WBD_H2306_TCP_PROGRESS")=="1"
    progress=[{"flow":i,"phase":"not_started","submitted_bytes":0}
              for i in range(BULK_FLOWS)]

    def bulk_client(flow_index):
        state=progress[flow_index]
        started=time.monotonic()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(TIMEOUT_S)
                local_buffers = _maybe_set_buffers(sock)
                sock.bind((bind_ip, 0))
                state["phase"]="connecting"
                sock.connect((target_ip, PORT))
                with lock:
                    client_bulk_buffers.append(local_buffers)
                if sock.getsockname()[0] != bind_ip:
                    raise RuntimeError("H2271_NOT_ORIGINAL_WINTUN_OR_TUN_SOURCE")
                state["phase"]="send_kind"
                sock.sendall(b"B")
                first = time.monotonic()
                amount = 0
                state["phase"]="sendall_bulk"
                while amount < BULK_MAX_BYTES and time.monotonic() - first < BULK_SEND_S:
                    sock.sendall(BULK_BLOCK)
                    amount += len(BULK_BLOCK)
                    if progress_enabled:
                        state.update(submitted_bytes=amount,
                                     last_completed_send_s=round(time.monotonic()-started,3))
                state["phase"]="shutdown_write"
                sock.shutdown(socket.SHUT_WR)
                state["phase"]="await_arm_receipt"
                reported = struct.unpack("!Q", exact(sock, 8))[0]
                if amount != reported:
                    raise RuntimeError("H2271_REAL_TCP_REMOTE_BYTES_NOT_MATCHED")
                with lock:
                    bulk.append((amount, first, time.monotonic()))
                state["phase"]="complete"
                state["elapsed_s"]=round(time.monotonic()-started,3)
        except Exception as exc:
            state["error_at_phase"]=state["phase"]
            state["phase"]="error"
            state["elapsed_s"]=round(time.monotonic()-started,3)
            state["exception"]=type(exc).__name__+":"+str(exc)
            with lock:
                errors.append(type(exc).__name__ + ":" + str(exc))

    workers = [threading.Thread(target=bulk_client,args=(i,)) for i in range(BULK_FLOWS)]
    for worker in workers:
        worker.start()
    echo_times = {}
    latencies = []
    echo_error = []

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(TIMEOUT_S)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.bind((bind_ip, 0))
            sock.connect((target_ip, PORT))
            if sock.getsockname()[0] != bind_ip:
                raise RuntimeError("H2271_NOT_REAL_TUNNEL_ECHO_SOURCE")
            sock.sendall(b"E")

            def send_echo():
                try:
                    origin = time.monotonic()
                    for seq in range(ECHO_COUNT):
                        sleep = origin + ECHO_PERIOD_S * seq - time.monotonic()
                        if sleep > 0:
                            time.sleep(sleep)
                        echo_times[seq] = time.monotonic()
                        sock.sendall(struct.pack("!QQ", seq, TOKEN))
                except Exception as exc:
                    echo_error.append(type(exc).__name__ + ":" + str(exc))

            sender = threading.Thread(target=send_echo)
            sender.start()
            for seq in range(ECHO_COUNT):
                frame = exact(sock, 16)
                got, token = struct.unpack("!QQ", frame)
                if got != seq or token != TOKEN or got not in echo_times:
                    raise RuntimeError("H2271_ECHO_KERNEL_SEQ_MISMATCH")
                latencies.append((time.monotonic() - echo_times[got]) * 1000)
            sender.join(timeout=20)
            if sender.is_alive() or echo_error:
                raise RuntimeError("H2271_ECHO_SEND_INCOMPLETE " + repr(echo_error))
    except Exception as exc:
        errors.append(type(exc).__name__ + ":" + str(exc))

    for worker in workers:
        worker.join(timeout=TIMEOUT_S)
    if progress_enabled:
        print(MARK+"CLIENT_PROGRESS_DIAGNOSTIC "+json.dumps({
            "source_sha":source,"flows":progress,
            "finished_bulk_flows":len(bulk),
            "echo_received":len(latencies),"echo_errors":echo_error,
            "send_supply_s":BULK_SEND_S,"socket_timeout_s":TIMEOUT_S,
            "joined":all(not w.is_alive() for w in workers),
            "errors":errors,"diagnostic_not_goodput_or_success":True},
            sort_keys=True),flush=True)
    if errors or len(bulk) != BULK_FLOWS or any(worker.is_alive() for worker in workers):
        raise RuntimeError("H2271_REAL_TCP_CLIENT_INCOMPLETE " + repr(errors))
    total = sum(row[0] for row in bulk)
    elapsed = max(row[2] for row in bulk) - min(row[1] for row in bulk)
    if elapsed <= 0 or len(latencies) != ECHO_COUNT:
        raise RuntimeError("H2271_BAD_OR_MISSING_TCP_RECEIVER_DENOMINATOR")
    print(MARK + "CLIENT_DONE " + json.dumps({
        "source_sha": source, "bind": bind_ip, "peer": target_ip,
        "bulk_flows": BULK_FLOWS, "bulk_remote_received_bytes": total,
        "bulk_receiver_goodput_mbps": round(total * 8 / elapsed / 1e6, 3),
        "bulk_wall_s": round(elapsed, 3),
        "client_bulk_buffers_os": client_bulk_buffers,
        "sparse_echo_sent": ECHO_COUNT, "sparse_echo_received": len(latencies),
        "sparse_tcp_rtt_p50_ms": quant(latencies, .5),
        "sparse_tcp_rtt_p95_ms": quant(latencies, .95),
        "sparse_tcp_rtt_p99_ms": quant(latencies, .99),
        "sparse_tcp_late_1000ms": sum(t > 1000 for t in latencies),
        "sparse_tcp_late_2000ms": sum(t > 2000 for t in latencies),
        "real_kernel_tcp": True, "outer_loss_injected_by_owned_linux_tc": True,
        "scope": "REAL_OS_TUNNEL_TCP_NOT_GENERATOR_UDP_OR_DIRECT_FAKEIP",
    }, sort_keys=True), flush=True)


def _single(log, marker):
    rows = [json.loads(row.split(marker, 1)[1]) for row in
            log.read_text(encoding="utf-8", errors="replace").splitlines()
            if marker in row]
    if len(rows) != 1:
        raise RuntimeError("H2271_MISSING_EXACT_APP_RECEIPT " + marker)
    return rows[0]


def run_loss_tcp(root, out, unix, server_tun_ip):
    """Called with real Go TLS/Rust Windows and Linux owners still alive."""
    source = os.environ["GITHUB_SHA"]
    script = pathlib.Path(root) / "tools" / "m0_wl_loss_tcp_probe.py"
    cases = (("windows", "10.66.0.2", server_tun_ip),
             ("linux", server_tun_ip, "10.66.0.2"))
    results = {}
    for origin, local, remote in cases:
        stage = pathlib.Path(out) / ("m029-h2271-" + origin)
        stage.mkdir()
        serverlog, clientlog = stage / "server.log", stage / "client.log"
        if origin == "windows":
            server_cmd = ["wsl.exe", "-d", "Ubuntu", "-u", "root", "--",
                          "python3", "-u", unix(script),
                          "server", remote, local, source]
            client_cmd = [sys.executable, "-u", str(script),
                          "client", local, remote, source]
        else:
            server_cmd = [sys.executable, "-u", str(script),
                          "server", remote, local, source]
            client_cmd = ["wsl.exe", "-d", "Ubuntu", "-u", "root", "--",
                          "python3", "-u", unix(script),
                          "client", local, remote, source]
        with serverlog.open("w", encoding="utf-8") as fs:
            server_proc = subprocess.Popen(server_cmd, stdout=fs,
                                           stderr=subprocess.STDOUT)
            try:
                until = time.monotonic() + 20
                while (MARK + "SERVER_READY") not in serverlog.read_text(
                        encoding="utf-8", errors="replace"):
                    if server_proc.poll() is not None or time.monotonic() > until:
                        raise RuntimeError("H2271_REAL_KERNEL_TCP_LISTENER_NOT_READY " +
                                           serverlog.read_text(errors="replace")[-900:])
                    time.sleep(.1)
                with clientlog.open("w", encoding="utf-8") as fc:
                    client_proc = subprocess.Popen(client_cmd, stdout=fc,
                                                   stderr=subprocess.STDOUT)
                    try:
                        client_rc = client_proc.wait(timeout=TIMEOUT_S + 50)
                    except subprocess.TimeoutExpired:
                        client_proc.kill()
                        client_proc.wait()
                        raise RuntimeError("H2271_NATIVE_TCP_CLIENT_TIMEOUT")
                server_rc = server_proc.wait(timeout=TIMEOUT_S + 10)
                if client_rc != 0 or server_rc != 0:
                    raise RuntimeError("H2271_REAL_KERNEL_TCP_APP_FAILURE " +
                                       clientlog.read_text(errors="replace")[-900:] + " " +
                                       serverlog.read_text(errors="replace")[-900:])
            finally:
                if server_proc.poll() is None:
                    server_proc.terminate()
                    try:
                        server_proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        server_proc.kill()
                        server_proc.wait()
        c = _single(clientlog, MARK + "CLIENT_DONE ")
        s = _single(serverlog, MARK + "SERVER_DONE ")
        if (c["source_sha"] != source or s["source_sha"] != source or
                c["bind"] != local or s["bind"] != remote or
                c["bulk_remote_received_bytes"] != s["bulk_received_bytes"] or
                c["sparse_echo_received"] != s["echo_received"] or
                c["bulk_flows"] != s["bulk_flows"] or
                not c["real_kernel_tcp"] or not s["real_kernel_tcp"]):
            raise RuntimeError("H2271_NATIVE_CLIENT_SERVER_REAL_SOURCE_MISMATCH")
        results[origin] = c
        print(MARK + "SIDE_DONE " + json.dumps(
            {"origin": origin, **c}, sort_keys=True), flush=True)
    return {"source_sha": source, "status": "PASS_SCOPED_REAL_TWO_OS_KERNEL_TCP",
            "windows_client": results["windows"],
            "linux_client": results["linux"],
            "one_way_ms": 200, "loss_from_owned_scenario": "1pct_or_5pct",
            "native_owners_stop": "CHECKED_BY_EXISTING_WL_RUNNER_AFTER_THIS_STAGE",
            "not_cross_clock_latency": True, "not_a_product_perf_win": True}

def archive_loss_tcp_stage(out, legdir):
    """Move exact original signed Windows/Linux real TCP app logs per cold leg.

    H2273's single signed Windows runner executes sequential OFF→ON in the
    same result root. Reusing the old H2271 stage directory made ON fail
    with WinError183 *after* OFF's genuine native TCP and owned Stop.
    Preserve both independent directions in this leg's evidence, and free
    the original stage path before the next cold TLS generation.
    """
    out, legdir = pathlib.Path(out), pathlib.Path(legdir)
    archived = []
    for origin in ("windows", "linux"):
        source = out / ("m029-h2271-" + origin)
        target = legdir / source.name
        if source.is_symlink() or target.exists():
            raise RuntimeError("H2278_TCP_ARCHIVE_FOREIGN_OR_STALE_PATH")
        if source.is_dir():
            if not legdir.is_dir():
                raise RuntimeError("H2278_TCP_ARCHIVE_LEG_NOT_CREATED")
            source.rename(target)  # atomic on this same Windows worktree disk
            archived.append(origin)
        elif source.exists():
            raise RuntimeError("H2278_TCP_ARCHIVE_NOT_DIRECTORY")
    return archived


if __name__ == "__main__":
    # H2273: H2271 source bb327 defined both application roles but omitted
    # the CLI entrypoint. WSL Python therefore exited silently before READY
    # in both real signed runs; it was NOT a WBD transport failure.
    if sys.argv[1:] == ["--selfcheck"]:
        if (PORT, BULK_FLOWS, ECHO_COUNT) != (45902, 4, 160):
            raise RuntimeError("H2273_NATIVE_APP_SHAPE_CHANGED")
        print("H2273_NATIVE_TCP_CLI_DISPATCH_AND_SCOPED_EXISTING_WIN_FIREWALL_PORT_READY", flush=True)
        sys.exit(0)
    if len(sys.argv) != 5 or sys.argv[1] not in ("server", "client"):
        raise SystemExit("usage: m0_wl_loss_tcp_probe.py server|client bind_ip peer_ip source_sha")
    role, bind_ip, peer_ip, source_sha = sys.argv[1:]
    if role == "server":
        server(bind_ip, peer_ip, source_sha)
    else:
        client(bind_ip, peer_ip, source_sha)
