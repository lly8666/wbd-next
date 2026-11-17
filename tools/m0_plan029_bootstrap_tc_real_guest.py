#!/usr/bin/env python3
"""Actual WSL2 UDP TC=1, same DNS endpoint TCP53 and original physical source."""
import json,socket,select,struct,sys,time
guest,host=sys.argv[1:]
qname=b"\x03vpn\x04edge\x02cn\x07example\x00"
question=qname+b"\x00\x01\x00\x01"
udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
tcp=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
for s in (udp,tcp):s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
udp.bind((guest,53));tcp.bind((guest,53));tcp.listen(1)
print("PLAN029_BOOTSTRAP_TC_GUEST_READY",flush=True)
receipt={"udp_tc":0,"tcp_a":0,"guest":guest,"physical_host":host}
deadline=time.monotonic()+50
def exact(c,n):
 data=b""
 while len(data)<n:
  d=c.recv(n-len(data))
  if not d:raise RuntimeError("physical TCP DNS short response")
  data+=d
 return data
try:
 while time.monotonic()<deadline:
  for s in select.select([udp,tcp],[],[],.3)[0]:
   if s is udp:
    wire,addr=udp.recvfrom(2048)
    if addr[0]!=host or wire[4:6]!=b"\x00\x01" or wire[12:]!=question or receipt["udp_tc"]:
     raise RuntimeError("unexpected physical UDP bootstrap identity")
    receipt["id"]=wire[:2].hex()
    response=wire[:2]+b"\x83\x80\x00\x01\x00\x00\x00\x00\x00\x00"+question
    if udp.sendto(response,addr)!=len(response):raise RuntimeError("short UDP TC")
    receipt["udp_tc"]=1
   else:
    if not receipt["udp_tc"]:raise RuntimeError("unprompted TCP connection")
    conn,addr=tcp.accept()
    with conn:
     conn.settimeout(6)
     if addr[0]!=host:raise RuntimeError("TCP physical source differs")
     n=struct.unpack("!H",exact(conn,2))[0]
     if n<12 or n>1000:raise RuntimeError("unexpected DNS frame length")
     wire=exact(conn,n)
     if wire[:2].hex()!=receipt["id"] or wire[4:6]!=b"\x00\x01" or wire[12:]!=question:
      raise RuntimeError("TC fallback not same transaction")
     response=wire[:2]+b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"+question
     response+=b"\xc0\x0c\x00\x01\x00\x01"+struct.pack("!I",30)+b"\x00\x04"+socket.inet_aton(guest)
     conn.sendall(struct.pack("!H",len(response))+response)
     receipt["tcp_a"]=1
  if receipt["tcp_a"]:break
 else:raise RuntimeError("physical TC/TCP bootstrap timeout")
finally:
 udp.close();tcp.close()
if receipt["udp_tc"]!=1 or receipt["tcp_a"]!=1:raise RuntimeError("no true TC followup")
print("PLAN029_BOOTSTRAP_TC_GUEST_RECEIPT "+json.dumps(receipt,sort_keys=True),flush=True)
