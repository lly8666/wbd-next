#!/usr/bin/env python3
"""Actual Linux TUN DNS→CN A, and independent eth0 physical Direct UDP."""
import json,select,socket,sys,time
dns4,cn4,lease,host=sys.argv[1:5]
question=b"\x05cn-ip\x07globalx\x07example\x00\x00\x01\x00\x01"
marker=b"PLAN029-H1775-NONCN-CNIP-DIRECT-UDP"
dns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
biz=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
try:
 dns.bind((dns4,53));biz.bind((cn4,46111))
 print("PLAN029_H1775_LINUX_CN_DNS_AND_PHYSICAL_DIRECT_READY",flush=True)
 seen_dns=seen_biz=0
 deadline=time.monotonic()+35
 while time.monotonic()<deadline and (not seen_dns or not seen_biz):
  rd,_,_=select.select([dns,biz],[],[],.3)
  for s in rd:
   wire,peer=s.recvfrom(2048)
   if s is dns:
    if peer[0]!=lease or len(wire)<12 or wire[4:6]!=b"\x00\x01" or wire[12:]!=question:
     raise RuntimeError("not exact original Tunnel DNS query to nonCN name")
    answer=wire[:2]+b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"+question
    answer+=b"\xc0\x0c\x00\x01\x00\x01"+(45).to_bytes(4,"big")+b"\x00\x04"+socket.inet_aton(cn4)
    if dns.sendto(answer,peer)!=len(answer):raise RuntimeError("short Tunnel DNS response")
    seen_dns+=1
   else:
    if peer[0]!=host or wire!=marker:
     raise RuntimeError("Direct business not from bound original physical socket")
    if biz.sendto(marker+b"-ECHO",peer)!=len(marker)+5:
     raise RuntimeError("short physical echo")
    seen_biz+=1
 if not seen_dns or not seen_biz:raise RuntimeError("Tunnel DNS or physical Direct UDP timed out")
 print("PLAN029_H1775_REAL_LINUX_D2_CNIP_DIRECT "+json.dumps({
  "dns_upstream":dns4,"dns_qname":"cn-ip.globalx.example",
  "dns_client_lease":lease,"dns_answers":seen_dns,"real_dns_a":cn4,
  "physical_business_dst":cn4,"physical_source":host,
  "physical_receipts":seen_biz,"echo_bytes":len(marker)+5
 },sort_keys=True),flush=True)
finally:
 dns.close();biz.close()
