#!/usr/bin/env python3
"""PLAN029 H1794 true Linux eth0 and original Tunnel DNS TCP/53 receivers."""
import json,select,socket,struct,sys,time
physical,tunnel,host,lease=sys.argv[1:5]
cnq=b"\x03www\x02cn\x07example\x00\x00\x01\x00\x01"
nonq=b"\x03www\x07globalx\x07example\x00\x00\x01\x00\x01"
names={cnq:("direct",physical,host,"198.51.100.77"),
       nonq:("tunnel",tunnel,lease,"203.0.113.77")}
def read_n(conn,n):
 data=b""
 while len(data)<n:
  piece=conn.recv(n-len(data))
  if not piece:raise RuntimeError("short real TCP DNS framed question")
  data+=piece
 return data
ports={}
receipts={}
for lane,addr in (("direct",physical),("tunnel",tunnel)):
 s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
 s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
 s.bind((addr,53));s.listen(4);s.setblocking(False)
 ports[s]=lane
print("PLAN029_H1794_REAL_TWO_LINUX_TCP53_ENDPOINTS_READY",flush=True)
try:
 deadline=time.monotonic()+48
 unrelated=0
 while time.monotonic()<deadline and len(receipts)<2:
  rd,_,_=select.select(list(ports),[],[],.4)
  for sock in rd:
   conn,peer=sock.accept()
   with conn:
    conn.settimeout(7)
    length=struct.unpack("!H",read_n(conn,2))[0]
    if not 17<=length<=2006:raise RuntimeError("invalid real DNS/TCP message length")
    wire=read_n(conn,length)
    if len(wire)<12 or wire[4:6]!=b"\x00\x01":
     raise RuntimeError("real DNS TCP QDCOUNT/length invalid")
    q=wire[12:]
    expected=names.get(q)
    if expected is None:
     unrelated+=1
     if unrelated>32:raise RuntimeError("too many unrelated TCP DNS control queries")
     continue
    lane,local,source,answer=expected
    if ports[sock]!=lane or sock.getsockname()[0]!=local or peer[0]!=source:
     raise RuntimeError("actual DNS TCP upstream entered wrong interface/source")
    if lane in receipts:raise RuntimeError("duplicate same QNAME physical/Tunnel query")
    response=(wire[:2]+b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"
      +q+b"\xc0\x0c\x00\x01\x00\x01"+(60).to_bytes(4,"big")
      +b"\x00\x04"+socket.inet_aton(answer))
    framed=struct.pack("!H",len(response))+response
    conn.sendall(framed)
    receipts[lane]=dict(lane=lane,real_socket_local=local,
       original_client_source=peer[0],real_a=answer,
       wire_id=wire[:2].hex(),reply_bytes=len(response),qname=
       "www.cn.example" if lane=="direct" else "www.globalx.example")
 if set(receipts)!={"direct","tunnel"}:
  raise RuntimeError("original Linux two real interface DNS TCP streams not both delivered")
 print("PLAN029_H1794_LINUX_REAL_DIRECT_AND_TUNNEL_TCP53 "+json.dumps({
  "direct":receipts["direct"],"tunnel":receipts["tunnel"],
  "unrelated_ignored":unrelated,
  "no_other_dns_endpoint":True
 },sort_keys=True),flush=True)
finally:
 for sock in ports:sock.close()
