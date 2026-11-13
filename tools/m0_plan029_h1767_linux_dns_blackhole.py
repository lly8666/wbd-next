#!/usr/bin/env python3
"""Scoped D1 true TUN DNS outage, with simultaneously armed physical DNS leak sentinel."""
import json,selectors,socket,sys,time
tun,physical,lease=sys.argv[1:4]
name=b"\x09no-backup\x07globalx\x07example\x00"
expected=name+b"\x00\x01\x00\x01"
sel=selectors.DefaultSelector()
sockets=[]
try:
 for kind,ip in (("tunnel",tun),("physical",physical)):
  s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
  s.bind((ip,53));s.setblocking(False)
  sel.register(s,selectors.EVENT_READ,kind);sockets.append(s)
 print("PLAN029_H1767_LINUX_TUN_DNS_BLACKHOLE_AND_PHYSICAL_SENTINEL_READY",flush=True)
 receipts={"tunnel":0,"physical":0};sources=set()
 end=time.monotonic()+7.0 # cover the complete native 5s DNS budget plus observation margin
 while time.monotonic()<end:
  for key,_ in sel.select(timeout=min(0.15,max(0,end-time.monotonic()))):
   query,peer=key.fileobj.recvfrom(2048)
   if len(query)<12 or query[12:]!=expected or query[4:6]!=b"\x00\x01":
    raise RuntimeError("blackhole fixture received unexpected query ID/QNAME/shape")
   receipts[key.data]+=1
   sources.add(peer[0])
   if peer[0]!=lease:raise RuntimeError("DNS blackhole original lease mismatch")
   # Do not send any DNS response. A physical query here is forbidden.
 if receipts["tunnel"]<2 or receipts["physical"]!=0:
  raise RuntimeError("DNS tunnel receipt missing or direct fallback leakage "+repr(receipts))
 print("PLAN029_H1767_REAL_LINUX_DNS_BLACKHOLE "+json.dumps({
    "tunnel_ip":tun,"physical_ip":physical,"client_source":list(sources),
    "tunnel_query_count":receipts["tunnel"],"physical_query_count":receipts["physical"],
    "replied":False},sort_keys=True),flush=True)
finally:
 sel.close()
 for s in sockets:s.close()
