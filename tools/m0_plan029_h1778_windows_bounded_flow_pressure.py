#!/usr/bin/env python3
"""16 Wintun-bound Direct tuples under hard8; Tunnel and existing Direct must advance."""
import json,socket,sys,time
lease,fake,tun=sys.argv[1:4]
tag=b"PLAN029-H1778/"
direct=(fake,46118)
held=[];success=[]
def echo(sock,data,remote):
 sock.sendto(data,remote)
 try:wire,peer=sock.recvfrom(512)
 except socket.timeout:return False
 if (wire,peer)!=(data+b"-ECHO",remote):
  raise RuntimeError("wrong original Windows Wintun UDP reverse tuple")
 return True
try:
 for i in range(16):
  s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  s.bind((lease,0));s.settimeout(.8);held.append(s)
  if echo(s,tag+b"FIRST/"+str(i).encode("ascii"),direct):success.append(s)
 if not(1<=len(success)<=8):
  raise RuntimeError("configured Direct hard8 did not bound new physical UDP tuples")
 # The new Tunnel flow must be delivered when Direct new-flow is full.
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as tun_sock:
  tun_sock.bind((lease,0));tun_sock.settimeout(1.3)
  tunnel_ok=any(echo(tun_sock,tag+b"TUNNEL",(tun,46119)) for _ in range(5))
 if not tunnel_ok:raise RuntimeError("new Tunnel starved behind Direct hard cap")
 # Do not refresh the other 15 sockets. Rust DirectUDP idle TTL is 120s,
 # so keep exactly one established Direct alive across that expiry window.
 old=success[0];old.settimeout(1.4)
 started=time.monotonic();heartbeats=0
 while time.monotonic()-started<127:
  if not echo(old,tag+b"KEEP",direct):
   raise RuntimeError("already admitted Direct failed under cap")
  heartbeats+=1
  time.sleep(12)
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as fresh:
  fresh.bind((lease,0));fresh.settimeout(1.2)
  recovered=False
  for _ in range(8):
   if echo(fresh,tag+b"RECOVER",direct):
    recovered=True;break
   time.sleep(.25)
 if not recovered:raise RuntimeError("no new Direct admitted after 120s idle reclaim")
 if not echo(old,tag+b"FINISH",direct):
  raise RuntimeError("old Direct lost after the pool recovered")
 print("PLAN029_H1778_WINDOWS_DIRECT8_TUNNEL_PRESSURE "+json.dumps({
  "hard_configured":8,"new_direct_attempts":16,
  "new_direct_real_echo":len(success),"unanswered_new_direct":16-len(success),
  "new_tunnel_while_full":tunnel_ok,"old_direct_heartbeat":heartbeats,
  "new_direct_after_expiry":recovered,"old_direct_final":True,
  "wait_seconds":round(time.monotonic()-started,1),
  "app_source":"ORIGINAL_WINDOWS_WINTUN_BOUND_LEASE",
  "no_typed_drop_reason":"UNANSWERED_NOT_ASSUMED_CAPACITY_CAUSE"
 },sort_keys=True),flush=True)
finally:
 for sock in held:sock.close()
