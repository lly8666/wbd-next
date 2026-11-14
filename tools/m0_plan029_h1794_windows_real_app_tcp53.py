#!/usr/bin/env python3
"""H1794 original Windows Wintun-bound kernel app TCP/53, not a parser mock."""
import json,socket,struct,sys,time
lease,presented=sys.argv[1:3]
if lease!="10.66.0.2":raise RuntimeError("unexpected signed Windows Wintun lease")
def read_n(conn,n):
 data=b""
 while len(data)<n:
  chunk=conn.recv(n-len(data))
  if not chunk:raise RuntimeError("original Windows TCP/53 short DNS response")
  data+=chunk
 return data
def query(lane,qname,qwire,tid,real):
 question=qwire+b"\x00\x01\x00\x01"
 req=tid+b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"+question
 message=struct.pack("!H",len(req))+req
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as app:
  app.settimeout(11)
  app.bind((lease,0))
  begin=time.monotonic()
  app.connect((presented,53))
  if app.getsockname()[0]!=lease or app.getpeername()!=(presented,53):
   raise RuntimeError("Windows app TCP53 did not use original lease/presented DNS")
  app.sendall(message[:3])
  time.sleep(.014)
  app.sendall(message[3:])
  size=struct.unpack("!H",read_n(app,2))[0]
  if not 17<=size<=2006:raise RuntimeError("invalid DNS/TCP return length")
  answer=read_n(app,size)
 # The REAL CN FakeIP answer re-encodes the RR owner uncompressed, while
 # the guest's ordinary nonCN resolver uses RFC1035 c0 0c compression.
 # Validate the common type/class/RDLENGTH tail, not a forged encoding
 # shape; do not accidentally require CN FakeIP to be c0 0c.
 if(answer[:2]!=tid or answer[2:4]!=b"\x81\x80" or
    answer[4:8]!=b"\x00\x01\x00\x01" or
    answer[12:12+len(question)]!=question or len(answer)<len(question)+26 or
    answer[-14:-12]!=b"\x00\x01" or answer[-12:-10]!=b"\x00\x01" or
    answer[-6:-4]!=b"\x00\x04"):
  raise RuntimeError("original Windows TCP DNS wire id/rcode/question/RR changed")
 actual=socket.inet_ntoa(answer[-4:])
 if lane=="direct":
  if not actual.startswith("198.18.") or actual==real:
   raise RuntimeError("CN DNS TCP did not return durable FakeIP rather than overseas CDN")
 else:
  if actual!=real:raise RuntimeError("nonCN DNS TCP was synthesized or wrong resolver answer")
 return dict(lane=lane,original_dns_presented=presented,original_lease=lease,
     qname=qname,wire_id=tid.hex(),dns_answer_a=actual,
     real_upstream_a=real,was_fake=(lane=="direct"),
     elapsed_ms=round((time.monotonic()-begin)*1000,2),
     fragmented_original_app_writes=True)
if __name__=="__main__":
 direct=query("direct","www.cn.example",b"\x03www\x02cn\x07example\x00",
   b"\x17\x94","198.51.100.77")
 tunnel=query("tunnel","www.globalx.example",b"\x03www\x07globalx\x07example\x00",
   b"\x17\x95","203.0.113.77")
 print("PLAN029_H1794_WINDOWS_REAL_ORIGINAL_APP_TCP53 "+json.dumps({
   "direct":direct,"tunnel":tunnel,
   "two_original_kernel_tcp_app_connections":True
 },sort_keys=True),flush=True)
