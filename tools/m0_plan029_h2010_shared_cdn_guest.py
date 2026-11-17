#!/usr/bin/env python3
"""Signed H2010: same overseas CDN IPv4, independent physical/Tunnel kernel receipts."""
import json,select,socket,struct,sys,time
physical,resolver,cdn,host,lease=sys.argv[1:6]
cn=b"\x03cdn\x02cn\x07example\0\0\x01\0\x01"
non=b"\x04edge\x07globalx\x07example\0\0\x01\0\x01"
cm=b"PLAN029-H2010-CN-CDN-DIRECT"
nm=b"PLAN029-H2010-NONCN-CDN-TUNNEL"
sockets=[]
def bound(ip,port,pkt=False):
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 s.bind((ip,port))
 if pkt:s.setsockopt(socket.IPPROTO_IP,8,1) # Linux IP_PKTINFO
 sockets.append(s)
 return s
try:
 dphys=bound(physical,53)
 dtun=bound(resolver,53)
 bphys=bound(cdn,46131,True)
 btun=bound(cdn,46132,True)
 ifphys=socket.if_nametoindex("eth0")
 iftun=socket.if_nametoindex("wbdwl4")
 if not ifphys or not iftun or ifphys==iftun:raise RuntimeError("not independent real Linux interfaces")
 counts={"cn_dns_physical":0,"noncn_dns_tunnel":0,
         "cn_business_physical":0,"noncn_business_tunnel":0,
         "unrelated_queries":0}
 print("PLAN029_H2010_SHARED_CDN_FOUR_KERNEL_SOCKETS_READY",flush=True)
 until=time.monotonic()+65
 while time.monotonic()<until and not all(counts[x] for x in (
      "cn_dns_physical","noncn_dns_tunnel",
      "cn_business_physical","noncn_business_tunnel")):
  ready,_,_=select.select(sockets,[],[],.4)
  for s in ready:
   if s in (dphys,dtun):
    wire,peer=s.recvfrom(2048)
    q=cn if s is dphys else non
    name="cn_dns_physical" if s is dphys else "noncn_dns_tunnel"
    expected=host if s is dphys else lease
    if peer[0]!=expected or len(wire)<12 or wire[4:6]!=b"\0\x01" or wire[12:]!=q:
     counts["unrelated_queries"]+=1
     if counts["unrelated_queries"]>64:raise RuntimeError("unrelated DNS cap exceeded")
     continue
    if counts[name]>=3:raise RuntimeError("repeated DNS tickets")
    answer=(wire[:2]+b"\x81\x80\0\x01\0\x01\0\0\0\0"+
            q+b"\xc0\x0c\0\x01\0\x01"+(45).to_bytes(4,"big")+
            b"\0\x04"+socket.inet_aton(cdn))
    if s.sendto(answer,peer)!=len(answer):raise RuntimeError("short real DNS")
    counts[name]+=1
   else:
    wire,anc,flags,peer=s.recvmsg(2048,128)
    physical_arm=s is bphys
    expected_if=ifphys if physical_arm else iftun
    expected_source=host if physical_arm else lease
    marker=cm if physical_arm else nm
    key="cn_business_physical" if physical_arm else "noncn_business_tunnel"
    indices=[struct.unpack_from("=I",v)[0] for level,kind,v in anc
             if level==socket.IPPROTO_IP and kind==8 and len(v)>=4]
    if len(indices)!=1 or indices[0]!=expected_if:
     raise RuntimeError("CDN wrong actual Linux IP_PKTINFO interface "+repr((key,indices,expected_if)))
    if wire!=marker or peer[0]!=expected_source or counts[key]:
     raise RuntimeError("CDN wrong real egress source/payload/unique "+key)
    if s.sendto(marker+b"-ECHO",peer)!=len(marker)+5:
     raise RuntimeError("short real business reply")
    counts[key]+=1
 if any(counts[x]==0 for x in (
      "cn_dns_physical","noncn_dns_tunnel",
      "cn_business_physical","noncn_business_tunnel")):
  raise RuntimeError("missing shared CDN true two-egress receipt "+repr(counts))
 print("PLAN029_H2010_LINUX_REAL_SHARED_CDN "+json.dumps({
  "real_a":cdn,"physical_resolver":physical,"tunnel_resolver":resolver,
  "physical_src":host,"tunnel_src":lease,
  "physical_ifindex":ifphys,"tunnel_ifindex":iftun,
  "kernel_eth0_and_tun_distinct":True,"counts":counts},sort_keys=True),flush=True)
finally:
 for s in sockets:s.close()
