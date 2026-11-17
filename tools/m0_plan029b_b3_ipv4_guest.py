#!/usr/bin/env python3
"""PLAN029B B3 Linux guest: only genuine original IPv4 TUN echoes."""
import json
import select
import socket
import sys
import time

ip,src=sys.argv[1:3]
seen=set()
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
    s.bind((ip,46114))
    print("PLAN029B_B3_LINUX_TUN_IPV4_READY",flush=True)
    end=time.monotonic()+53
    while time.monotonic()<end and len(seen)<12:
        r,_,_=select.select([s],[],[],.3)
        if not r:continue
        wire,peer=s.recvfrom(300)
        if peer[0]!=src or not wire.startswith(b"P29B-B3-V4-"):
            raise RuntimeError("B3 original Linux TUN source/marker wrong")
        try:n=int(wire[len(b"P29B-B3-V4-"):])
        except ValueError as exc:raise RuntimeError("B3 invalid ordinal") from exc
        if not 0<=n<12:raise RuntimeError("B3 invalid original sequence")
        seen.add(n)
        s.sendto(wire+b"-ECHO",peer)
    if seen!=set(range(12)):
        raise RuntimeError("B3 original Linux TUN IPv4 missing sequence "+repr(sorted(seen)))
    print("PLAN029B_B3_ORIGINAL_LINUX_TUN_IPV4 "+
          json.dumps({"result":"PASS_REAL_LINUX_IPV4_TUN_MIX",
                      "source":src,"destination":ip,"unique_echo":12,
                      "ipv6_guest_echo":"NOT_APPLICABLE_PACKET_DROPPED_AT_CLIENT"},
                     sort_keys=True),flush=True)
