#!/usr/bin/env python3
"""True Game 2/4 LAN Direct: Win Wintun IPv4 UDP to Linux physical UDP."""
import json
import socket
import sys
import time
if len(sys.argv)!=5 or sys.argv[1] not in ("guest","windows"):
    raise SystemExit("signed original Game LAN requires role, local, remote, source tag")
role,local,remote,tag=sys.argv[1:]
if not tag.isalnum() or len(tag)!=16:
    raise SystemExit("source tag must be 16 ASCII hex characters")
body=("P29B-GAME-LAN-"+tag).encode("ascii")
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.settimeout(1.0)
try:
    if role=="guest":
        sock.bind((local,46117))
        print("PLAN029B_GAME_REAL_LINUX_PHYSICAL_LAN_READY",flush=True)
        deadline=time.monotonic()+37
        while time.monotonic()<deadline:
            try:data,peer=sock.recvfrom(2048)
            except socket.timeout:continue
            if data!=body or peer[0]!=remote:
                raise SystemExit("LAN egress did not use original physical Windows IPv4")
            sock.sendto(body+b"-ECHO",peer)
            print("PLAN029B_GAME_REAL_LINUX_LAN_DIRECT_UDP "+json.dumps(
              {"result":"PASS_ORIGINAL_LINUX_KERNEL_PHYSICAL_LAN_UDP",
               "original_windows_physical":peer[0],"guest":local,
               "bytes":len(data)},sort_keys=True),flush=True)
            break
        else:
            raise SystemExit("no physical LAN UDP from original Windows")
    else:
        sock.bind((local,0))
        deadline=time.monotonic()+29
        while time.monotonic()<deadline:
            sock.sendto(body,(remote,46117))
            try:data,peer=sock.recvfrom(2048)
            except socket.timeout:continue
            if data!=body+b"-ECHO" or peer[0]!=remote:
                raise SystemExit("physical LAN echo did not return from real Linux UDP socket")
            print("PLAN029B_GAME_REAL_WINDOWS_LAN_DIRECT_UDP "+json.dumps(
              {"result":"PASS_ORIGINAL_WINTUN_PHYSICAL_LAN_UDP",
               "src":local,"physical_guest":peer[0],"bytes":len(body)},
               sort_keys=True),flush=True)
            break
        else:
            raise SystemExit("Windows Wintun LAN Direct UDP reply missing")
finally:
    sock.close()
