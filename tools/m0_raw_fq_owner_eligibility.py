#!/usr/bin/env python3
"""Native FQ socket-key/throttle and pending-SKB lifetime diagnostic.
Synthetic IP_HDRINCL UDP over owned veth. Not product or wire performance.
"""
import array
import fcntl
import json
import os
import pathlib
import socket
import statistics
import struct
import subprocess
import sys
import time

OUT = pathlib.Path("fq-owner-out").resolve()
SRC, DST = "192.0.2.1", "192.0.2.2"
TX, RX = "wbd-fq-owner-tx", "wbd-fq-owner-rx"
SO_TXTIME, SO_TIMESTAMPNS, SIOCOUTQ = 61, 35, 0x5411
HORIZONS = (1_000_000, 20_000_000)
ORDER = "ABBA" * 4

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")

def cmd(*argv):
    return subprocess.check_output(argv, stderr=subprocess.STDOUT, text=True)

def ns(name, *argv):
    return cmd("ip", "netns", "exec", name, *argv)

def outq(sock):
    value = array.array("i", [0])
    fcntl.ioctl(sock.fileno(), SIOCOUTQ, value, True)
    return value[0]

def raw():
    s = socket.socket(socket.AF_INET, socket.SOCK_RAW | socket.SOCK_NONBLOCK, socket.IPPROTO_RAW)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"fq-owner-tx\0")
    s.setsockopt(socket.SOL_SOCKET, SO_TXTIME, struct.pack("=iI", time.CLOCK_MONOTONIC, 0))
    return s

def send(sock, ident, edt=None):
    payload = struct.pack("!Q", ident) + bytes(56)
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + 8 + len(payload), 43, 0, 64, 17, 0,
                     socket.inet_aton(SRC), socket.inet_aton(DST))
    udp = struct.pack("!HHHH", 42000, 5202, 8 + len(payload), 0)
    ancillary = [] if edt is None else [(socket.SOL_SOCKET, SO_TXTIME, struct.pack("=Q", edt))]
    wall = time.time_ns()
    mono = time.monotonic_ns()
    n = sock.sendmsg([ip, udp, payload], ancillary, 0, (DST, 0))
    returned = time.monotonic_ns()
    assert n == len(ip) + len(udp) + len(payload), n
    return {"id": ident, "wall_ns": wall, "mono_ns": mono, "returned_ns": returned,
            "edt_ns": edt, "accepted_bytes": n}

def receiver():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, SO_TIMESTAMPNS, 1)
    s.bind((DST, 5202))
    s.settimeout(3)
    (OUT / "receiver-ready").touch()
    rows = []
    try:
        while True:
            data, ancillary, flags, _ = s.recvmsg(256, 128)
            stamps = [struct.unpack("=qq", v[:16]) for level, kind, v in ancillary
                      if level == socket.SOL_SOCKET and kind == SO_TIMESTAMPNS]
            assert len(data) == 64 and len(stamps) == 1 and not flags
            sec, nano = stamps[0]
            rows.append([struct.unpack("!Q", data[:8])[0], sec * 10**9 + nano])
    except socket.timeout:
        pass
    save(OUT / "received.json", rows)

def sender():
    rows = []
    ident = 1
    # A: earlier immediate packet uses the very same raw socket as the
    # future packet. B: identical outer header, another raw socket.
    # Both sockets are created before measurement; no per-trial setup cost.
    with raw() as paced, raw() as independent:
        for horizon in HORIZONS:
            for arm in ORDER:
                future_at = time.monotonic_ns() + horizon
                later = send(paced, ident, future_at)
                queued = outq(paced)
                # Allow qdisc to observe the future packet and throttle.
                # This delay belongs only to the fixture.
                time.sleep(horizon / 10 / 1e9)
                earlier = send(paced if arm == "A" else independent, ident + 1)
                after = outq(paced)
                time.sleep(horizon / 1e9 + .004)
                rows.append({"kind": "mixed", "arm": arm, "horizon_ns": horizon,
                             "future": later, "immediate": earlier, "outq_after_future": queued,
                             "outq_after_immediate": after, "outq_after_wait": outq(paced),
                             "immediate_lead_ns": future_at - earlier["mono_ns"]})
                ident += 2
    # Closing the fd may not cancel kernel-owned queued data. Observe,
    # rather than assume, whether the accepted future packet survives close.
    for horizon in HORIZONS:
        for _ in range(8):
            s = raw()
            future_at = time.monotonic_ns() + horizon
            later = send(s, ident, future_at)
            queued = outq(s)
            s.close()
            closed_mono, closed_wall = time.monotonic_ns(), time.time_ns()
            time.sleep(horizon / 1e9 + .004)
            rows.append({"kind": "close", "horizon_ns": horizon, "future": later,
                         "outq_before_close": queued, "close_mono_ns": closed_mono,
                         "close_wall_ns": closed_wall})
            ident += 1
    save(OUT / "sent.json", rows)

def summarize(rows, received):
    by_id = dict(received)
    mixed = [r for r in rows if r["kind"] == "mixed"]
    close = [r for r in rows if r["kind"] == "close"]
    required = {r[k]["id"] for r in mixed for k in ("future", "immediate")}
    known = required | {r["future"]["id"] for r in close}
    identity = {"mixed_missing": sorted(required - by_id.keys()),
                "extras": sorted(by_id.keys() - known),
                "duplicates": len(received) - len(by_id)}
    results = []
    for r in mixed:
        f, m = r["future"], r["immediate"]
        f_rx, m_rx = by_id.get(f["id"]), by_id.get(m["id"])
        r["future_rx_wall_ns"], r["immediate_rx_wall_ns"] = f_rx, m_rx
        r["eligible"] = (r["outq_after_future"] > 0 and r["immediate_lead_ns"] > 0
                         and f_rx is not None and m_rx is not None)
        r["immediate_latency_us"] = (m_rx - m["wall_ns"]) / 1000 if m_rx is not None else None
        r["immediate_before_future"] = m_rx < f_rx if m_rx is not None and f_rx is not None else None
        r["future_lateness_us"] = ((f_rx - f["wall_ns"]) - (f["edt_ns"] - f["mono_ns"])) / 1000 if f_rx is not None else None
    for horizon in HORIZONS:
        for arm in "AB":
            sample = [r for r in mixed if r["horizon_ns"] == horizon and r["arm"] == arm and r["eligible"]]
            latencies = sorted(r["immediate_latency_us"] for r in sample)
            results.append({"horizon_ns": horizon, "arm": arm, "eligible": len(sample),
                            "immediate_before_future": sum(r["immediate_before_future"] for r in sample),
                            "immediate_latency_median_us": statistics.median(latencies) if latencies else None,
                            "immediate_latency_max_us": max(latencies) if latencies else None})
    for r in close:
        at = by_id.get(r["future"]["id"])
        r["rx_wall_ns"] = at
        r["received_after_close"] = at > r["close_wall_ns"] if at is not None else None
        r["eligible"] = r["outq_before_close"] > 0 and r["close_mono_ns"] < r["future"]["edt_ns"]
    return {"identity": identity, "mixed_summary": results,
            "close_summary": [{"horizon_ns": h,
                               "eligible": sum(r["eligible"] for r in close if r["horizon_ns"] == h),
                               "eligible_received_after_close": sum(r["eligible"] and r["received_after_close"] is True for r in close if r["horizon_ns"] == h)}
                              for h in HORIZONS], "rows": rows,
            "scope": "native RAW IP_HDRINCL with SCM_TXTIME, software receiver timestamps, no product/physical qualification"}

def main():
    OUT.mkdir(exist_ok=True)
    save(OUT / "host.json", {"source_sha": os.environ["GITHUB_SHA"], "run_id": os.environ["GITHUB_RUN_ID"],
                            "uname": cmd("uname", "-a"), "cpu": cmd("lscpu"),
                            "order": ORDER, "horizons_ns": HORIZONS})
    try:
        for space in (TX, RX):
            cmd("ip", "netns", "add", space)
        cmd("ip", "link", "add", "fq-owner-tx", "type", "veth", "peer", "name", "fq-owner-rx")
        for space, dev, addr in ((TX, "fq-owner-tx", SRC), (RX, "fq-owner-rx", DST)):
            cmd("ip", "link", "set", dev, "netns", space)
            ns(space, "ip", "addr", "add", addr + "/24", "dev", dev)
            ns(space, "ip", "link", "set", dev, "up")
            ns(space, "ip", "link", "set", "lo", "up")
            ns(space, "ethtool", "-K", dev, "gro", "off", "gso", "off", "tso", "off")
        ns(TX, "ping", "-c", "1", "-W", "2", DST)
        ns(TX, "tc", "qdisc", "replace", "dev", "fq-owner-tx", "root", "fq")
        before = json.loads(ns(TX, "tc", "-s", "-j", "qdisc", "show", "dev", "fq-owner-tx"))
        assert any(q["kind"] == "fq" for q in before)
        save(OUT / "qdisc-before.json", before)
        script = str(pathlib.Path(__file__).resolve())
        with (OUT / "receiver.log").open("w") as log:
            rx = subprocess.Popen(["ip", "netns", "exec", RX, sys.executable, script, "recv"], stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    if (OUT / "receiver-ready").exists():
                        break
                    if rx.poll() is not None:
                        raise RuntimeError("receiver exited")
                    time.sleep(.02)
                else:
                    raise RuntimeError("receiver readiness timeout")
                ns(TX, sys.executable, script, "send")
                assert rx.wait(timeout=10) == 0
            finally:
                if rx.poll() is None:
                    rx.terminate()
                    rx.wait(timeout=5)
        qdisc = json.loads(ns(TX, "tc", "-s", "-j", "qdisc", "show", "dev", "fq-owner-tx"))
        save(OUT / "qdisc-after.json", qdisc)
        result = summarize(json.loads((OUT / "sent.json").read_text()), json.loads((OUT / "received.json").read_text()))
        result["qdisc"] = qdisc
        save(OUT / "summary.json", result)
        print(json.dumps({k: v for k, v in result.items() if k != "rows"}))
        assert not any(result["identity"].values()), result["identity"]
        assert all(r["eligible"] > 0 for r in result["mixed_summary"] if r["horizon_ns"] == HORIZONS[-1])
    finally:
        for space in (TX, RX):
            subprocess.run(["ip", "netns", "del", space], check=False)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "main"
    {"main": main, "recv": receiver, "send": sender}[mode]()
