#!/usr/bin/env python3
"""029B B4: one original WSL2 host, three REAL Windows GUI generations.

Physical CN DNS remains one endpoint; ordinary/all use real A. A test-owned
/32 on eth0 exists only for advanced Direct generation, then is removed.
The same 203.0.113.77 stays on the original server TUN for subsequent
Tunnel generations. AF_PACKET witnesses cannot stand in for Win32 or Rust.
"""
import json
import select
import socket
import struct
import sys
import time

physical, host, lease, tunnel, overseas = sys.argv[1:6]
if lease != "10.66.0.2" or tunnel != "10.66.0.1" or overseas != "203.0.113.77":
    raise RuntimeError("B4 requires the original exact Wintun/TUN identities")
qname = b"\x03www\x02cn\x07example\x00"
question = qname + b"\x00\x01\x00\x01"
edge = b"\x04edge\x03cdn\x07example\x00"
dns_ids = {b"\x29\x61": ("advanced", physical, host),
           b"\x29\x62": ("ordinary", physical, host),
           b"\x29\x63": ("all", tunnel, lease)}
business = {b"P29B4-G1": ("advanced", host),
            b"P29B4-G2": ("ordinary", lease),
            b"P29B4-G3": ("all", lease)}
stale = (b"P29B4-STALE-G2", b"P29B4-STALE-G3")
observed = {}
attempts = {}
unrelated = 0
raw_fake = 0
start = time.monotonic()
deadline = start + 155
done_at = None

def raw_socket(interface):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800))
    s.bind((interface, 0))
    return s

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as direct, \
     socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as tunneled, \
     socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as app, \
     raw_socket("eth0") as physical_wire, raw_socket("wbdwl4") as tunnel_wire:
    direct.bind((physical, 53))
    tunneled.bind((tunnel, 53))
    app.bind((overseas, 46119))
    print("PLAN029B_B4_LINUX_DNS_AND_BUSINESS_READY", flush=True)
    while time.monotonic() < deadline:
        if len(observed) == 6 and done_at is None:
            done_at = time.monotonic()
        if done_at is not None and time.monotonic() - done_at > 3:
            break
        ready, _, _ = select.select(
            [direct, tunneled, app, physical_wire, tunnel_wire], [], [], .3)
        for sock in ready:
            data, peer = sock.recvfrom(4096)
            if sock in (physical_wire, tunnel_wire):
                # AF_PACKET only: count actual IPv4 egress towards any
                # previous-generation FakeIP. No raw pcap retained.
                if len(data) >= 34 and data[12:14] == b"\x08\x00" and \
                   data[14] >> 4 == 4 and data[30:32] == b"\xc6\x12":
                    raw_fake += 1
                continue
            if sock is app:
                if data in stale:
                    raise RuntimeError("stale FakeIP marker reached original guest")
                if data not in business:
                    raise RuntimeError("unrecognized B4 business on physical/TUN")
                phase, expected = business[data]
                if peer[0] != expected or phase + "_data" in observed:
                    raise RuntimeError("B4 wrong or duplicate business egress " + phase)
                observed[phase + "_data"] = {
                    "source": peer[0],
                    "lane": "physical" if phase == "advanced" else "tun",
                    "bytes": len(data)}
                if sock.sendto(data + b"-ACK", peer) != len(data) + 4:
                    raise RuntimeError("B4 original guest short echo")
                continue
            if len(data) < 12 or data[4:6] != b"\x00\x01":
                raise RuntimeError("B4 invalid DNS question header")
            ticket = data[:2]
            if ticket not in dns_ids:
                # Windows NCSI can independently query the Tunnel DNS;
                # it is not a B4 transaction. Never count it as PASS.
                if sock is tunneled and unrelated < 12:
                    unrelated += 1
                    continue
                raise RuntimeError("B4 unexpected DNS ticket or physical fallback")
            phase, dst, source = dns_ids[ticket]
            selected = direct if dst == physical else tunneled
            if sock is not selected or peer[0] != source or \
               data[2:6] != b"\x01\x00\x00\x01" or data[12:] != question:
                raise RuntimeError("B4 wrong DNS upstream lane/qname/type " + phase)
            attempts[phase] = attempts.get(phase, 0) + 1
            if attempts[phase] > 2:
                raise RuntimeError("B4 excessive upstream retransmission " + phase)
            cname = b"\xc0\x0c\x00\x05\x00\x01" + struct.pack("!IH", 2, len(edge)) + edge
            arec = edge + b"\x00\x01\x00\x01" + struct.pack("!IH", 2, 4) + socket.inet_aton(overseas)
            reply = data[:2] + b"\x81\x80\x00\x01\x00\x02\x00\x00\x00\x00" + question + cname + arec
            if sock.sendto(reply, peer) != len(reply):
                raise RuntimeError("B4 DNS short kernel send")
            observed[phase + "_dns"] = {
                "physical": sock is direct, "source": peer[0],
                "real_a": overseas, "cname": True, "ttl": 2}
    expected = {p + "_" + k for p in ("advanced", "ordinary", "all")
                for k in ("dns", "data")}
    if set(observed) != expected or raw_fake:
        raise RuntimeError("B4 missing real DNS/data or stale FakeIP egress " +
                           repr((sorted(observed), raw_fake)))
    report = {"source": "ORIGINAL_LINUX_KERNEL_AND_AF_PACKET",
              "events": observed, "dns_retransmissions": attempts,
              "unrelated_os_tunnel_dns": unrelated,
              "stale_old_fake_business": 0,
              "raw_old_fake_ipv4_egress": raw_fake,
              "result": "PASS_THREE_REAL_GUI_GENERATION_EGRESS"}
    print("PLAN029B_B4_REAL_LINUX_EGRESS " +
          json.dumps(report, sort_keys=True), flush=True)
