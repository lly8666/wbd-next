#!/usr/bin/env python3
"""029B B0 one real WSL2 kernel-TUN DNS UDP/TCP53 A-only upstream.

The Windows client must answer all managed AAAA locally. This fixture
never synthesizes AAAA and rejects any leaked target AAAA query. It only
owns the original Linux test-guest sockets, not a product DNS proxy.
"""
import json
import select
import socket
import struct
import sys
import time

tunnel, lease = sys.argv[1:3]
QNAME = b"\x03www\x07globalx\x07example\x00"
Q_A = QNAME + b"\x00\x01\x00\x01"
Q_AAAA = QNAME + b"\x00\x1c\x00\x01"
ANSWER4 = "203.0.113.77"
TTL = 2

def read_n(sock, count):
    data = b""
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise RuntimeError("physical TUN TCP53 short application query")
        data += part
    return data

def checked_query(wire, peer):
    if len(wire) < 12 or wire[4:6] != b"\x00\x01":
        raise RuntimeError("malformed or multi-question DNS forwarded to guest")
    question = wire[12:]
    if question == Q_AAAA:
        raise RuntimeError("029B managed AAAA leaked to original Linux upstream")
    if question != Q_A:
        return False
    if peer != lease:
        raise RuntimeError("foreign DNS traffic claimed as Windows Wintun lease")
    return True

def a_answer(wire):
    return (wire[:2] + b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"
            + Q_A + b"\xc0\x0c\x00\x01\x00\x01"
            + TTL.to_bytes(4, "big") + b"\x00\x04"
            + socket.inet_aton(ANSWER4))

seen = {}
unrelated = 0
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp, \
     socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
    udp.bind((tunnel, 53))
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp.bind((tunnel, 53))
    tcp.listen(3)
    print("PLAN029B_B0_REAL_LINUX_TUN_DNS_READY", flush=True)
    end = time.monotonic() + 32
    linger_until = None
    while time.monotonic() < end:
        if len(seen) == 2 and linger_until is None:
            linger_until = time.monotonic() + .7
        if linger_until is not None and time.monotonic() >= linger_until:
            break
        remaining = end - time.monotonic()
        if linger_until is not None:
            remaining = min(remaining, linger_until - time.monotonic())
        readable, _, _ = select.select([udp, tcp], [], [], min(.4, max(0, remaining)))
        for sock in readable:
            if sock is udp:
                wire, address = udp.recvfrom(2048)
                peer_ip = address[0]
                proto = "udp"
                if not checked_query(wire, peer_ip):
                    unrelated += 1
                    continue
                if proto in seen:
                    raise RuntimeError("duplicate upstream UDP A outside one ticket")
                reply = a_answer(wire)
                if udp.sendto(reply, address) != len(reply):
                    raise RuntimeError("short original Linux TUN DNS UDP reply")
            else:
                conn, addr = tcp.accept()
                proto = "tcp"
                peer_ip = addr[0]
                with conn:
                    conn.settimeout(6)
                    n = struct.unpack("!H", read_n(conn, 2))[0]
                    if not 17 <= n <= 2006:
                        raise RuntimeError("unbounded real app TCP53 upstream query")
                    wire = read_n(conn, n)
                    if not checked_query(wire, peer_ip):
                        unrelated += 1
                        continue
                    if proto in seen:
                        raise RuntimeError("duplicate upstream TCP A outside one ticket")
                    reply = a_answer(wire)
                    conn.sendall(struct.pack("!H", len(reply)) + reply)
            seen[proto] = {
                "protocol": proto, "source4": peer_ip, "upstream4": tunnel,
                "qname": "www.globalx.example", "qtype": 1,
                "upstream_id": wire[:2].hex(), "real_answer4": ANSWER4,
                "ttl": TTL, "original_kernel_socket": True
            }
            if unrelated > 16:
                raise RuntimeError("unexpected unrelated DNS flood")
    if set(seen) != {"udp", "tcp"}:
        raise RuntimeError("real DNS A not seen on both original upstream sockets")
    print("PLAN029B_B0_REAL_LINUX_TUN_DNS_RECEIPT " +
          json.dumps({"upstream_a": seen, "leaked_aaaa": 0,
                      "unrelated": unrelated, "tunnel_upstream": tunnel,
                      "source_lease": lease,
                      "result": "PASS_REAL_TUN_UDP_AND_TCP53_A_ONLY"},
                     sort_keys=True), flush=True)
