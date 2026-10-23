#!/usr/bin/env python3
"""Actions-only direct-IP TCP control for V3-C: same host, RTT, MTU, BDP.

This does NOT exercise WBD Next and can never qualify product throughput.
Runs one 200Mbps unidirectional TCP/400ms RTT scenario on one native ARM VM.
No global sysctls, no product deployment; netns names have unique run suffix.
"""
import argparse
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time

RATE = 200_000_000
WARM_S = 15
STEADY_S = 60
DRAIN_S = 5
CHUNK = 32768
DEV_MTU = 1429
NS_PREFIX = "v3direct"


def call(*args, check=True):
    return subprocess.run(args, text=True, capture_output=True, check=check)


def worker(args):
    target = float(args.start)
    end = target + WARM_S + STEADY_S
    result = {"role": args.worker, "app_mtu": DEV_MTU, "requested_mbps": 200}
    if args.worker == "server":
        listen = socket.socket()
        listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen.bind(("10.233.42.2", 42119))
        listen.listen(1)
        Path(args.ready).write_text("ready")
        listen.settimeout(10)
        conn, _ = listen.accept()
        listen.close()
    else:
        conn = socket.socket()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.settimeout(9)
        conn.connect(("10.233.42.2", 42119))
    result["actual_sndbuf"] = conn.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
    result["actual_rcvbuf"] = conn.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    conn.setblocking(False)
    during = 0
    warm = 0
    blocked = 0
    accepted_chunks = 0
    if args.worker == "server":
        buf = bytearray(1 << 20)
        while time.monotonic() < end + DRAIN_S:
            readable, _, _ = select.select([conn], [], [], .25)
            if not readable:
                continue
            try:
                count = conn.recv_into(buf)
            except BlockingIOError:
                continue
            if not count:
                break
            when = time.monotonic()
            if target + WARM_S <= when < end:
                during += count
            elif target <= when < target + WARM_S:
                warm += count
    else:
        data = memoryview(bytes(CHUNK))
        next_due = target
        offset = 0
        while time.monotonic() < end:
            now = time.monotonic()
            if now < next_due:
                select.select([], [], [], min(.003, next_due - now))
                continue
            if now < target:
                next_due = target
                continue
            _, writable, _ = select.select([], [conn], [], .002)
            if not writable:
                blocked += 1
                continue
            try:
                n = conn.send(data[offset:])
            except BlockingIOError:
                blocked += 1
                continue
            if n == 0:
                blocked += 1
                continue
            offset += n
            if offset == CHUNK:
                if target + WARM_S <= now < end:
                    during += CHUNK
                elif target <= now < target + WARM_S:
                    warm += CHUNK
                accepted_chunks += 1
                offset = 0
                # Time-based, bounded sending: do not aggregate a huge burst
                # after socket backpressure. Count missing pace as an input limit.
                next_due = max(next_due + CHUNK * 8 / RATE, now - .025)
        try:
            conn.shutdown(socket.SHUT_WR)
        except OSError:
            pass
    result.update(steady_payload_bytes=during, warmup_payload_bytes=warm,
                  measured_mbps=during * 8 / (STEADY_S * 1e6),
                  blocked_writes=blocked, accepted_chunks=accepted_chunks,
                  rtt_ms=400, one_way_ms=200)
    conn.close()
    Path(args.out).write_text(json.dumps(result, indent=2))
    return 0


def run():
    folder = Path("direct-tcp-result")
    folder.mkdir(exist_ok=True)
    unique = os.environ.get("GITHUB_RUN_ID", str(os.getpid()))[-7:]
    a, b = NS_PREFIX + "a" + unique, NS_PREFIX + "b" + unique
    devices = ("vdca" + unique[-5:], "vdcb" + unique[-5:])
    tasks = []
    def ip(*parts):
        return call("ip", *parts)
    try:
        for n in (a, b):
            ip("netns", "add", n)
        ip("link", "add", devices[0], "type", "veth", "peer", "name", devices[1])
        ip("link", "set", devices[0], "netns", a)
        ip("link", "set", devices[1], "netns", b)
        for n, dev, addr in ((a, devices[0], "10.233.42.1/30"),
                             (b, devices[1], "10.233.42.2/30")):
            ip("-n", n, "link", "set", "lo", "up")
            ip("-n", n, "addr", "add", addr, "dev", dev)
            ip("-n", n, "link", "set", "dev", dev, "mtu", str(DEV_MTU))
            ip("-n", n, "link", "set", "dev", dev, "up")
            for field in ("tcp_rmem", "tcp_wmem"):
                expected = "4096 4194304 67108864"
                actual = call("ip", "netns", "exec", n, "sysctl", "-w",
                              "net.ipv4." + field + "=" + expected)
                read = call("ip", "netns", "exec", n, "sysctl", "-n",
                            "net.ipv4." + field).stdout.strip()
                if read.split() != expected.split():
                    raise RuntimeError("TCP window readback mismatch: " + field)
            call("ip", "netns", "exec", n, "tc", "qdisc", "replace", "dev", dev,
                 "root", "netem", "delay", "200ms", "rate", "700mbit", "limit", "32768")
        start = time.monotonic() + 3.0
        ready = folder / "server.ready"
        script = str(Path(__file__).resolve())
        server = subprocess.Popen(["ip", "netns", "exec", b, sys.executable,
            script, "--worker", "server", "--start", str(start),
            "--ready", str(ready), "--out", str(folder / "server.json")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        tasks.append(server)
        deadline = time.monotonic() + 8
        while not ready.exists() and time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError("direct baseline server exited before listen")
            time.sleep(.02)
        if not ready.exists():
            raise RuntimeError("direct baseline server never listened")
        client = subprocess.Popen(["ip", "netns", "exec", a, sys.executable,
            script, "--worker", "client", "--start", str(start),
            "--ready", str(ready), "--out", str(folder / "client.json")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        tasks.append(client)
        snapshots = []
        for t in (target for target in (start + WARM_S + 5,
                                        start + WARM_S + 30,
                                        start + WARM_S + 55)):
            while time.monotonic() < t:
                time.sleep(min(.2, t - time.monotonic()))
            snapshots.append({"t_from_steady_s": round(t - start - WARM_S, 1),
                "tcp_ss": call("ip", "netns", "exec", a,
                               "ss", "-tin", "dst", "10.233.42.2").stdout,
                "netem_sender": call("ip", "netns", "exec", a, "tc", "-s",
                                     "qdisc", "show", "dev", devices[0]).stdout,
                "netem_receiver": call("ip", "netns", "exec", b, "tc", "-s",
                                       "qdisc", "show", "dev", devices[1]).stdout})
        for t in tasks:
            stdout, stderr = t.communicate(timeout=WARM_S + STEADY_S + DRAIN_S + 30)
            if t.returncode != 0:
                raise RuntimeError(f"worker exit {t.returncode}: {stderr[-2500:]}")
        sender = json.loads((folder / "client.json").read_text())
        receiver = json.loads((folder / "server.json").read_text())
        result = {"scope": "DIRECT_TCP_CONTROL_NOT_WBD_PRODUCT",
            "host_arch": os.uname().machine,
            "scenario": "200Mbps TCP app, RTT400ms, MTU1429, 700Mbps line per dir",
            "sender": sender, "receiver": receiver, "ss_and_netem": snapshots,
            "sender_target_pass": sender["measured_mbps"] >= 190,
            "receiver_target_pass": receiver["measured_mbps"] >= 190}
        (folder / "result.json").write_text(json.dumps(result, indent=2))
        print("DIRECT_TCP_BASELINE", json.dumps({
            "sender_mbps": sender["measured_mbps"],
            "receiver_mbps": receiver["measured_mbps"],
            "sender_blocked_writes": sender["blocked_writes"],
            "sender_pass": result["sender_target_pass"],
            "receiver_pass": result["receiver_target_pass"]}))
        return 0 if result["sender_target_pass"] and result["receiver_target_pass"] else 1
    finally:
        for t in tasks:
            if t.poll() is None:
                t.terminate()
                try: t.wait(timeout=2)
                except subprocess.TimeoutExpired: t.kill()
        for n in (a, b):
            call("ip", "netns", "del", n, check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=["client", "server"])
    parser.add_argument("--start")
    parser.add_argument("--ready")
    parser.add_argument("--out")
    a = parser.parse_args()
    sys.exit(worker(a) if a.worker else run())
