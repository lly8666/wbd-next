#!/usr/bin/env python3
"""Signed H2010: Windows original app, two names -> SAME CDN A, opposite exits."""
import json,socket,struct,subprocess,sys,time
lease,presented,real=sys.argv[1:4]
def query_name(name):
 return b"".join(bytes([len(label)])+label.encode("ascii") for label in name.split("."))+b"\0"
def name_end(wire,pos):
 for _ in range(64):
  if pos>=len(wire):raise RuntimeError("DNS truncated")
  n=wire[pos]
  if n&0xc0==0xc0:
   if pos+2>len(wire):raise RuntimeError("bad DNS compression")
   return pos+2
  if n>63:raise RuntimeError("bad DNS label")
  if n==0:return pos+1
  pos+=1+n
 raise RuntimeError("DNS name bound")
answers=[]
for i,domain in enumerate(("cdn.cn.example","edge.globalx.example")):
 question=query_name(domain)+b"\0\x01\0\x01"
 txid=struct.pack("!H",0x2010+i)
 query=txid+b"\x01\0\0\x01\0\0\0\0\0\0"+question
 response=None
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as dns:
  dns.bind((lease,0));dns.settimeout(1.0)
  until=time.monotonic()+22
  while time.monotonic()<until:
   dns.sendto(query,(presented,53))
   try:raw,peer=dns.recvfrom(2048)
   except socket.timeout:continue
   if peer==(presented,53) and raw[:2]==txid:response=raw;break
 if response is None:raise RuntimeError("missing signed QNAME "+domain)
 if (response[2:4]!=b"\x81\x80" or response[4:8]!=b"\0\x01\0\x01"
     or response[12:12+len(question)]!=question):
  raise RuntimeError("DNS RCODE/question/answer mismatch "+domain)
 pos=12+len(question);records=[]
 for _ in range(struct.unpack("!H",response[6:8])[0]):
  pos=name_end(response,pos)
  if pos+10>len(response):raise RuntimeError("DNS RR truncated")
  typ,cls,ttl,length=struct.unpack("!HHIH",response[pos:pos+10])
  pos+=10
  if pos+length>len(response):raise RuntimeError("DNS RDATA truncated")
  if (typ,cls,length)==(1,1,4):records.append(socket.inet_ntoa(response[pos:pos+4]))
  pos+=length
 if len(records)!=1:raise RuntimeError("not exactly one A "+domain)
 answers.append(records[0])
fake,plain=answers
if not fake.startswith("198.18.") or fake==real or plain!=real:
 raise RuntimeError("shared CDN FakeIP isolation or no pollution failed "+repr(answers))
r=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",
 "(Get-NetAdapter -Name 'WBDWLMAIN' -ErrorAction Stop).ifIndex"],
 capture_output=True,text=True,timeout=9,check=True)
ifindex=int(r.stdout.strip())
if ifindex<=0:raise RuntimeError("actual Wintun ifindex absent")
receipts={}
for key,ip,port,marker in (
 ("cn_direct",fake,46131,b"PLAN029-H2010-CN-CDN-DIRECT"),
 ("noncn_tunnel",plain,46132,b"PLAN029-H2010-NONCN-CDN-TUNNEL")):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as app:
  # The owned physical /32 overrides the usual route; force entry into
  # original Wintun so Rust, not Windows OS routing, selects this egress.
  app.setsockopt(socket.IPPROTO_IP,getattr(socket,"IP_UNICAST_IF",31),
                 struct.pack("!I",ifindex))
  app.bind((lease,0));app.settimeout(.8)
  accepted=False
  until=time.monotonic()+18
  while time.monotonic()<until:
   if app.sendto(marker,(ip,port))!=len(marker):
    raise RuntimeError("short actual Windows UDP business")
   try:echo,peer=app.recvfrom(512)
   except socket.timeout:continue
   if echo==marker+b"-ECHO" and peer==(ip,port):
    accepted=True;break
  if not accepted:raise RuntimeError("shared CDN egress missing "+key)
 receipts[key]={"dst":ip,"port":port,"reply_exact":True}
print("PLAN029_H2010_WINDOWS_REAL_SHARED_CDN "+json.dumps({
 "cn_qname":"cdn.cn.example","noncn_qname":"edge.globalx.example",
 "shared_real_a":real,"cn_fakeip":fake,"noncn_real_a":plain,
 "wintun_ifindex":ifindex,"app_forced_wintun":True,
 "business":receipts},sort_keys=True),flush=True)
