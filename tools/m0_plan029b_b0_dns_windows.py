#!/usr/bin/env python3
"""029B B0 original Windows Winsock application DNS A/AAAA over UDP and TCP53.

No DNS library, mock Rust frame, raw injection or second application
packet pump. Must use the real leased Wintun IPv4 address and original
kernel UDP/TCP sockets; AAAA is local NOERROR/NODATA, A from Linux TUN.
"""
import json
import socket
import struct
import sys
import time

lease, upstream = sys.argv[1:3]
if lease != "10.66.0.2" or upstream != "10.66.0.1":
    raise RuntimeError("unexpected original signed Windows/WSL2 TUN addresses")
QNAME = b"\x03www\x07globalx\x07example\x00"
ANSWER4 = socket.inet_aton("203.0.113.77")
results = {}

def question(qtype, tid):
    tail = QNAME + struct.pack("!HH", qtype, 1)
    return struct.pack("!HHHHHH", tid, 0x0100, 1, 0, 0, 0) + tail

def check(raw, tid, qtype, proto, address):
    if len(raw) < 12 or raw[:2] != struct.pack("!H", tid):
        raise RuntimeError("wrong original app DNS transaction ID")
    flags, qd, an, ns, ar = struct.unpack("!5H", raw[2:12])
    if flags != 0x8180 or qd != 1 or ns or ar or raw[12:12+len(QNAME)] != QNAME:
        raise RuntimeError("DNS QR/RD/RA/AD/NOERROR/question/extra altered")
    expected_question = QNAME + struct.pack("!HH", qtype, 1)
    if raw[12:12+len(expected_question)] != expected_question:
        raise RuntimeError("original app DNS type/class not preserved")
    if qtype == 28:
        if an != 0 or raw[12:] != expected_question:
            raise RuntimeError("managed AAAA is not exact local NODATA")
        name = "AAAA"
        result = "NOERROR_NODATA_LOCAL"
    else:
        # Upstream socket returns a real compressed A record TTL2.
        rr = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x02\x00\x04" + ANSWER4
        if an != 1 or raw[12:] != expected_question + rr:
            raise RuntimeError("original upstream real A/TTL2 was not preserved")
        name = "A"
        result = "REAL_A_TTL2_NOT_FAKEIP"
    if address != (upstream, 53):
        raise RuntimeError("DNS app reply did not originate from requested server")
    return {"protocol": proto, "qtype": qtype, "qname": "www.globalx.example",
            "original_id": "%04x" % tid, "result": result,
            "source_lease": lease, "presented_dns": upstream}

def recv_n(sock, size):
    chunks = []
    while size > 0:
        part = sock.recv(size)
        if not part:
            raise RuntimeError("original TCP53 reply truncated")
        size -= len(part)
        chunks.append(part)
    return b"".join(chunks)

def udp_query(qtype, tid):
    wire = question(qtype, tid)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(11)
        sock.bind((lease, 0))
        if sock.sendto(wire, (upstream, 53)) != len(wire):
            raise RuntimeError("real Windows UDP DNS send short")
        reply, peer = sock.recvfrom(2048)
        if sock.getsockname()[0] != lease:
            raise RuntimeError("DNS did not use leased Windows Wintun IP")
        return check(reply, tid, qtype, "udp", peer)

def tcp_query(qtype, tid):
    wire = question(qtype, tid)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(11)
        sock.bind((lease, 0))
        sock.connect((upstream, 53))
        if sock.getsockname()[0] != lease or sock.getpeername() != (upstream, 53):
            raise RuntimeError("TCP53 bypassed original Wintun DNS route")
        framed = struct.pack("!H", len(wire)) + wire
        sock.sendall(framed[:3])
        time.sleep(.012)
        sock.sendall(framed[3:])
        n = struct.unpack("!H", recv_n(sock, 2))[0]
        if not 12 <= n <= 2006:
            raise RuntimeError("unbounded TCP DNS app response")
        return check(recv_n(sock, n), tid, qtype, "tcp", (upstream, 53))

results["udp_a"] = udp_query(1, 0x3201)
results["udp_aaaa"] = udp_query(28, 0x3202)
results["tcp_aaaa"] = tcp_query(28, 0x3203)
results["tcp_a"] = tcp_query(1, 0x3204)
print("PLAN029B_B0_REAL_WINDOWS_APP_DNS_UDP_TCP_A_AAAA " +
      json.dumps({"source_lease": lease, "requested_tunnel_dns": upstream,
                  "results": results,
                  "checks": "TWO_REAL_A_UPSTREAM_TWO_LOCAL_AAAA",
                  "result": "PASS_REAL_WIN_WINTUN_UDP_TCP53_A_AAAA"},
                 sort_keys=True), flush=True)
