#!/usr/bin/env python3
"""H2305 external GPL upstream kernel module, *interface-only* smoke.

No upstream code inside this file/repository. Only documented Linux
TCP_CONGESTION / TCP_BRUTAL_PARAMS / TCP_BRUTAL_VERSION socket interface.
This is a disposable GitHub runner root+module test, not WBD deployment.
"""
import json
import os
import socket
import struct
import sys

TCP_BRUTAL_PARAMS=23301
TCP_BRUTAL_VERSION=23302
RATE_BYTES_S=1_250_000  # one isolated socket, 10Mbps target
GAIN_TENTHS=15
GROUP_ID=467

def main():
    if sys.platform!="linux" or os.environ.get("GITHUB_ACTIONS")!="true":
        raise RuntimeError("H2305_DISPOSABLE_NATIVE_GITHUB_LINUX_ONLY")
    if "brutal" not in open("/proc/modules",encoding="ascii").read().split():
        # /proc/modules format name etc. Only a real loaded module counts.
        mods={l.split()[0] for l in open("/proc/modules",encoding="ascii")}
        if "brutal" not in mods:
            raise RuntimeError("H2305_UPSTREAM_LINUX_BRUTAL_KO_NOT_LOADED")
    default=open("/proc/sys/net/ipv4/tcp_congestion_control",
                 encoding="ascii").read().strip()
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as server:
        server.settimeout(5)
        server.bind(("127.0.0.1",0))
        server.listen(1)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as client:
            client.settimeout(5)
            client.connect(server.getsockname())
            conn,peer=server.accept()
            with conn:
                conn.settimeout(5)
                prior=conn.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,64)
                conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,b"brutal")
                actual=conn.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,64)
                actual=actual.split(b"\0",1)[0].decode("ascii")
                if actual!="brutal":
                    raise RuntimeError("H2305_BRUTAL_ALGO_NOT_SOCKET_SELECTED")
                desired=struct.pack("<QIQ",RATE_BYTES_S,GAIN_TENTHS,GROUP_ID)
                conn.setsockopt(socket.IPPROTO_TCP,TCP_BRUTAL_PARAMS,desired)
                packed=conn.getsockopt(socket.IPPROTO_TCP,TCP_BRUTAL_PARAMS,20)
                values=struct.unpack("<QIQ",packed)
                if values!=(RATE_BYTES_S,GAIN_TENTHS,GROUP_ID):
                    raise RuntimeError("H2305_REAL_BRUTAL_PARAMS_READBACK_MISMATCH")
                version=struct.unpack("<I",conn.getsockopt(
                    socket.IPPROTO_TCP,TCP_BRUTAL_VERSION,4))[0]
                if version<0x020000:
                    raise RuntimeError("H2305_BRUTAL_VERSION2_NOT_ACTUAL")
                payload=b"H2305_"*512
                conn.sendall(payload)
                got=bytearray()
                while len(got)<len(payload):
                    chunk=client.recv(len(payload)-len(got))
                    if not chunk: break
                    got.extend(chunk)
                if bytes(got)!=payload:
                    raise RuntimeError("H2305_REAL_TCP_BRUTAL_SOCKET_BYTES_NOT_RECEIVED")
    restored=open("/proc/sys/net/ipv4/tcp_congestion_control",
                  encoding="ascii").read().strip()
    if restored!=default:
        raise RuntimeError("H2305_GLOBAL_LINUX_CC_CHANGED")
    print("H2305_REAL_LINUX_GPL_BRUTAL_SOCKET_PARAMS_AND_TCP_BYTES_PASS "+
          json.dumps({"original_socket_cc":prior.split(b"\0",1)[0].decode(),
                     "actual_socket_cc":actual,"rate_bytes_s":RATE_BYTES_S,
                     "gain_tenths":GAIN_TENTHS,"group_id":GROUP_ID,
                     "module_version":version,"real_tcp_received":len(payload),
                     "global_congestion":restored,
                     "wbd_product":"NOT_RUN","outer_fake_tcp":"NOT_RUN"},
                     sort_keys=True),flush=True)
if __name__=="__main__":
    main()
