#!/usr/bin/env python3
"""Passive actual WSL2 AF_PACKET capture during one PUBLIC product run.

Never sends, relays, modifies, injects, or acknowledges a packet. Logs only
kernel-observed TCP 443 frame headers, no payloads or protected TLS secrets.
"""
import socket,struct,time,sys,json
dev=sys.argv[1] if len(sys.argv)>1 else "eth0"
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0800))
s.bind((dev,0));s.settimeout(1.0)
print("WL_REAL_KERNEL_UNDERLAY_CAPTURE_ARMED="+dev,flush=True)
deadline=time.monotonic()+48;seen=0;flags={}
while time.monotonic()<deadline and seen<240:
 try:frame=s.recv(4096)
 except socket.timeout:continue
 if len(frame)<54 or frame[12:14]!=b"\x08\x00":continue
 h=frame[14];ihl=(h&15)*4
 if h>>4!=4 or ihl<20 or frame[23]!=6 or len(frame)<14+ihl+20:continue
 ip=frame[14:14+ihl];t=frame[14+ihl:]
 sp,dp=struct.unpack("!HH",t[:4])
 if sp!=443 and dp!=443:continue
 name="S" if t[13]&2 else "A" if t[13]&16 else "R" if t[13]&4 else "O"
 flags[name]=flags.get(name,0)+1;seen+=1
 if seen<=64 or seen%25==0:
  addr=lambda b:".".join(map(str,b))
  print("WL_REAL_KERNEL_TCP443 "+json.dumps({"ip_src":addr(ip[12:16]),"ip_dst":addr(ip[16:20]),"sport":sp,"dport":dp,"flags":t[13],"seq":struct.unpack("!I",t[4:8])[0],"count":seen}),flush=True)
print("WL_REAL_KERNEL_TCP443_COUNTS "+json.dumps({"packet_count":seen,"flags":flags}),flush=True)
