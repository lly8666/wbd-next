#!/usr/bin/env python3
"""One bounded H1778 two-egress Linux socket fixture; no network mutations."""
import json,select,socket,sys,time
physical,tun,host,lease=sys.argv[1:5]
tag=b"PLAN029-H1778/"
p=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
t=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
first=set();keep=recover=tunnel=finish=0
try:
 p.bind((physical,46118));t.bind((tun,46119))
 print("PLAN029_H1778_LINUX_TWO_OS_SOCKETS_READY",flush=True)
 deadline=time.monotonic()+230
 while time.monotonic()<deadline and not(finish and recover and tunnel and keep>=8):
  ready,_,_=select.select([p,t],[],[],.7)
  for s in ready:
   wire,peer=s.recvfrom(512)
   if not wire.startswith(tag):raise RuntimeError("foreign H1778 datagram")
   if s is p:
    if peer[0]!=host:raise RuntimeError("Direct was not physically sourced")
    if wire.startswith(tag+b"FIRST/"):first.add(peer[1])
    elif wire==tag+b"KEEP":keep+=1
    elif wire==tag+b"RECOVER":recover+=1
    elif wire==tag+b"FINISH":finish+=1
    else:raise RuntimeError("bad Direct pressure marker")
   elif peer[0]!=lease or wire!=tag+b"TUNNEL":
    raise RuntimeError("Tunnel destination/source were not original Linux TUN")
   else:tunnel+=1
   if s.sendto(wire+b"-ECHO",peer)!=len(wire)+5:
    raise RuntimeError("short independent Linux real UDP echo")
 if not(first and keep>=8 and recover and tunnel and finish):
  raise RuntimeError("physical Direct old/new or simultaneous Tunnel missing")
 print("PLAN029_H1778_LINUX_BOUNDED_TWO_EGRESS "+json.dumps({
  "direct_source_physical":host,"direct_real_dst":physical,
  "first_unique":len(first),"old_direct_keep":keep,
  "new_direct_after_idle":recover,"old_direct_final":finish,
  "tunnel_lease":lease,"tunnel_dst":tun,"new_tunnel_echo":tunnel,
  "real_sockets":"LINUX_ETH0_46118_AND_ORIGINAL_TUN_46119"
 },sort_keys=True),flush=True)
finally:
 p.close();t.close()
