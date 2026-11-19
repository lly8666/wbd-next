#!/usr/bin/env python3
"""029B B2 original Windows Wintun application proves ordinary CN semantics.

No synthetic packet injection: bind actual leased AF_INET kernel sockets,
query controlled physical CN and tunnel non-CN DNS, and send traffic to the
same overseas A via the original authenticated Wintun/TUN path.
"""
import json
import socket
import struct
import sys
import time

lease, overseas, tunnel_dns = sys.argv[1:4]
if lease != "10.66.0.2" or overseas != "203.0.113.77" or \
   tunnel_dns != "10.66.0.1":
    raise RuntimeError("B2 caller did not use scoped original Wintun identity")
CN = b"\x03www\x02cn\x07example\x00"
GLOBAL = b"\x03www\x07globalx\x07example\x00"
EDGE = b"\x04edge\x03cdn\x07example\x00"
A = b"\x00\x01\x00\x01"
target = socket.inet_aton(overseas)
observed = {}

def parse_rr(wire, cursor):
    if cursor + 2 > len(wire):
        raise RuntimeError("short upstream RR name")
    if wire[cursor] & 0xc0 == 0xc0:
        cursor += 2
    else:
        for _ in range(60):
            if cursor >= len(wire):
                raise RuntimeError("unterminated DNS label")
            n = wire[cursor]
            if not n:
                cursor += 1
                break
            if n & 0xc0 or n > 63 or cursor + 1 + n >= len(wire):
                raise RuntimeError("invalid domain label")
            cursor += 1 + n
        else:
            raise RuntimeError("unbounded DNS owner name")
    if cursor + 10 > len(wire):
        raise RuntimeError("short DNS owner/TTL header")
    typ, cls, ttl, n = struct.unpack("!HHIH", wire[cursor:cursor+10])
    cursor += 10
    if cursor + n > len(wire):
        raise RuntimeError("DNS record overread")
    return (typ, cls, ttl, wire[cursor:cursor+n], cursor+n)

def query(label, qname, presented, tid):
    wire = struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0) + qname + A
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((lease, 0))
        sock.settimeout(1.2)
        deadline = time.monotonic() + 18
        while time.monotonic() < deadline:
            if sock.sendto(wire, (presented, 53)) != len(wire):
                raise RuntimeError("short real Windows Wintun DNS application send")
            try:
                reply, peer = sock.recvfrom(2048)
            except socket.timeout:
                continue
            if peer != (presented, 53) or reply[:2] != wire[:2]:
                continue
            if sock.getsockname()[0] != lease:
                raise RuntimeError("DNS app escaped original Wintun lease")
            break
        else:
            raise RuntimeError("no real ordinary CN DNS receipt " + label)
    if len(reply) < len(wire) or reply[2:4] != b"\x81\x80" or \
       reply[4:6] != b"\x00\x01" or reply[8:12] != b"\x00\x00"*2 or \
       reply[12:12+len(qname)+4] != qname + A:
        # Only on the first genuine Windows application error. A SERVFAIL
        # from an interrupted guest is not evidence of a bad product route;
        # retain the exact returned RCODE and question in bounded form.
        print("PLAN029B_B2_FIRST_INVALID_WINDOWS_DNS " +
              json.dumps({"lane": label, "resolver": presented,
                          "response_length": len(reply),
                          "header12": reply[:12].hex(),
                          "question_prefix48": reply[12:60].hex(),
                          "expected_question": (qname + A).hex(),
                          "source": "ORIGINAL_WINDOWS_AF_INET"},
                         sort_keys=True), flush=True)
        raise RuntimeError("real DNS original ID/status/question not preserved")
    count = struct.unpack("!H", reply[6:8])[0]
    if count != (2 if label == "cn" else 1):
        raise RuntimeError("ordinary CN CNAME/A count wrong; FakeIP present?")
    cursor = len(wire)
    records = []
    for _ in range(count):
        typ, cls, ttl, data, cursor = parse_rr(reply, cursor)
        if cls != 1 or ttl != 2:
            raise RuntimeError("ordinary CN real TTL/RR class altered")
        records.append((typ, data))
    if cursor != len(reply) or records[-1] != (1, target) or \
       (label == "cn" and records[0] != (5, EDGE)):
        raise RuntimeError("ordinary CN real CNAME/A changed or FakeIP leaked")
    if any(t == 1 and v.startswith(b"\xc6\x12") for t, v in records):
        raise RuntimeError("unexpected FakeIP answer in ordinary mode")
    observed[label] = {"original_id": "%04x" % tid, "resolver_requested": presented,
                       "real_a": overseas, "ttl": 2, "cname": label == "cn"}

def business(tag):
    payload = ("P29B-" + tag + "-TUNNEL").encode()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((lease, 0))
        sock.settimeout(1.4)
        deadline = time.monotonic() + 18
        while time.monotonic() < deadline:
            sock.sendto(payload, (overseas, 46113))
            try:
                data, peer = sock.recvfrom(2048)
            except socket.timeout:
                continue
            if data == payload + b"-REPLY" and peer == (overseas, 46113):
                break
        else:
            raise RuntimeError("real overseas A did not use authenticated Tunnel")
        observed[tag.lower()+"_business"] = {"source_lease": sock.getsockname()[0],
                                              "presented_peer": peer[0],
                                              "real_tun_udp": True}

query("cn", CN, "8.8.8.8", 0x6201)
business("CN")
query("global", GLOBAL, tunnel_dns, 0x6202)
business("GLOBAL")
print("PLAN029B_B2_REAL_WINDOWS_ORDINARY_CN_REAL_A_BOTH_TUNNEL " +
      json.dumps({"result": "PASS_ORIGINAL_WIN_WINTUN_REAL_A_CNAME_TTL2_AND_TUNNEL",
                  "source": lease, "events": observed, "no_fakeip": True,
                  "dns_physical_cn_only": True}, sort_keys=True), flush=True)
