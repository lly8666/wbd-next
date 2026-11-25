#!/usr/bin/env python3
"""Real local UDP/TCP DNS fixture, no external network."""
import argparse
import select
import socket
import struct

def answer(q, tcp):
    if len(q) < 17:
        raise ValueError("short query")
    i = 12
    labels = []
    while q[i]:
        n = q[i]
        labels.append(q[i+1:i+1+n])
        i += n+1
    name = b".".join(labels)
    if name not in (b"udp.wbd-b90.test", b"tc.wbd-b90.test", b"system.wbd-b91.test", b"cn.wbd-b91.test", b"target.test", b"default1.wbd-b107.test", b"default2.wbd-b107.test"):
        raise ValueError("unexpected query")
    question = q[12:i+5]
    truncated = name == b"tc.wbd-b90.test" and not tcp
    flags = 0x8380 if truncated else 0x8180
    has_a = not truncated and struct.unpack("!H", question[-4:-2])[0] == 1
    head = q[:2] + struct.pack("!HHHHH", flags, 1, int(has_a), 0, 0)
    print("B90_FIXTURE", name.decode(), "TCP" if tcp else "UDP", flush=True)
    answer_ip = "0a000202" if name == b"target.test" else "c0000237"
    return head + question + (b"" if not has_a else bytes.fromhex("c00c000100010000003c0004"+answer_ip))

def readn(c, n):
    b = b""
    while len(b) < n:
        chunk = c.recv(n-len(b))
        if not chunk:
            raise EOFError()
        b += chunk
    return b

parser=argparse.ArgumentParser()
parser.add_argument("--bind",default="127.0.0.1")
args=parser.parse_args()
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp, socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
    tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind((args.bind, 53))
    tcp.bind((args.bind, 53))
    tcp.listen(4)
    print("B90_DNS_FIXTURE_READY", flush=True)
    while True:
        ready, _, _ = select.select([udp, tcp], [], [], 10)
        for s in ready:
            try:
                if s is udp:
                    q, address = udp.recvfrom(4096)
                    udp.sendto(answer(q, False), address)
                else:
                    c, _ = tcp.accept()
                    with c:
                        c.settimeout(3)
                        q = readn(c, struct.unpack("!H", readn(c, 2))[0])
                        a = answer(q, True)
                        c.sendall(struct.pack("!H", len(a)) + a)
            except (ValueError, EOFError, OSError, IndexError):
                continue
