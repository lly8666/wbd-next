#!/usr/bin/env python3
"""PLAN029 actual two-Linux-netns TUN application UDP + kernel TCP duplex echo.

Runs inside the ORIGINAL client/server network namespaces with their real
10.188.18.x TUN addresses. The listener/initiator are ordinary Linux sockets;
no test-provided cipher, fake DATA, socket bypass, or root/global route.
"""
import json
import os
import socket
import sys
import time

if len(sys.argv) != 6:
    raise SystemExit("usage: app.py listener|sender local-ip remote-ip port label")
role, local, remote, port_text, label = sys.argv[1:]
port = int(port_text)
if (role not in ("listener", "sender")
    or (local, remote) not in (
        ("10.188.18.1", "10.188.18.2"),
        ("10.188.18.2", "10.188.18.1"))
    or not 47000 <= port <= 47999
    or not label.isalnum() or len(label) > 30):
    raise SystemExit("invalid source-locked Linux kernel app case")
marker = ("PLAN029-LINUX-TUN-" + label + "-" + local).encode()
reply = b"ORIGINAL-TUN-ACK/" + marker
# Genuine Linux kernel TCP bytes with an application-defined TLS-record
# shaped leading five octets (NOT a negotiated application TLS handshake).
# Only this test-owned payload triggers the existing bounded tls selector.
tls_shape = os.environ.get("WBD_PLAN029_LINUX_TCP_TLS_SHAPE") == "1"
def tcp_shape(body):
    if not tls_shape: return body
    return bytes((22,3,3,len(body)>>8,len(body)&255)) + body
tcp_marker = tcp_shape(marker)
tcp_reply = tcp_shape(reply)
proof = {"role": role, "source": local, "peer": remote,
         "port": port, "udp": "NOT_RUN", "tcp": "NOT_RUN"}
if role == "listener":
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp, \
         socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udp.bind((local, port)); tcp.bind((local, port))
        tcp.listen(1); udp.settimeout(15); tcp.settimeout(15)
        print("PLAN029_LINUX_APP_SOCKET_READY " + label, flush=True)
        data, peer = udp.recvfrom(2048)
        expected = ("PLAN029-LINUX-TUN-" + label + "-" + remote).encode()
        if peer[0] != remote or data != expected:
            raise RuntimeError("kernel UDP source or payload did not match original Linux TUN")
        udp.sendto(b"ORIGINAL-TUN-ACK/" + data, peer)
        proof["udp"] = "PASS_NATIVE_KERNEL_APP"
        conn, peer = tcp.accept()
        with conn:
            conn.settimeout(10)
            if peer[0] != remote:
                raise RuntimeError("kernel TCP source did not match other Linux TUN")
            chunks = bytearray()
            while len(chunks) < len(tcp_shape(expected)):
                part = conn.recv(1024)
                if not part: break
                chunks.extend(part)
            if bytes(chunks) != tcp_shape(expected):
                raise RuntimeError("real Linux TCP payload did not arrive")
            conn.sendall(tcp_shape(b"ORIGINAL-TUN-ACK/" + expected))
            conn.shutdown(socket.SHUT_WR)
            proof["tcp"] = "PASS_NATIVE_KERNEL_APP"
else:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.bind((local, 0)); udp.settimeout(2)
        for attempt in range(9):
            udp.sendto(marker, (remote, port))
            try:
                data, peer = udp.recvfrom(2048)
                if peer[0] == remote and data == reply:
                    proof["udp"] = "PASS_NATIVE_KERNEL_APP"
                    break
            except socket.timeout:
                pass
        if proof["udp"] != "PASS_NATIVE_KERNEL_APP":
            raise RuntimeError("real Linux UDP app echo missing")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
        tcp.bind((local, 0)); tcp.settimeout(12)
        tcp.connect((remote, port))
        # Verify real kernel peer while CONNECTED: Linux may clear
        # getpeername() after the remote FIN even though bytes arrived.
        if tcp.getpeername()[0] != remote:
            raise RuntimeError("unexpected real Linux TCP peer")
        tcp.sendall(tcp_marker); tcp.shutdown(socket.SHUT_WR)
        data = bytearray()
        while len(data) < len(tcp_reply):
            chunk = tcp.recv(2048)
            if not chunk: break
            data.extend(chunk)
        if bytes(data) != tcp_reply:
            raise RuntimeError("real Linux TCP app echo missing")
        proof["tcp"] = "PASS_NATIVE_KERNEL_APP"
print("PLAN029_LINUX_APP_TRUE_KERNEL_PASS " + json.dumps(proof, sort_keys=True), flush=True)
