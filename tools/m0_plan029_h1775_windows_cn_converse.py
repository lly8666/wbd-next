#!/usr/bin/env python3
"""Actual Windows Wintun app Tunnel DNS result then physical CN-IP Direct UDP."""
import json,socket,struct,subprocess,sys,time
lease,cn4=sys.argv[1:3]
q=b"\x05cn-ip\x07globalx\x07example\x00\x00\x01\x00\x01"
txid=b"\x17\x75"
query=txid+b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"+q
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as dns:
 dns.bind((lease,0));dns.settimeout(.8)
 answer=None
 until=time.monotonic()+17
 while time.monotonic()<until:
  dns.sendto(query,("8.8.8.8",53))
  try:wire,source=dns.recvfrom(2048)
  except socket.timeout:continue
  if wire[:2]==txid and source==("8.8.8.8",53):answer=wire;break
 if answer is None:raise RuntimeError("Wintun app nonCN Tunnel DNS answer missing")
 if (answer[2:4]!=b"\x81\x80" or answer[4:8]!=b"\x00\x01\x00\x01" or
     answer[12:12+len(q)]!=q or len(answer)!=12+len(q)+16 or
     answer[-4:]!=socket.inet_aton(cn4)):
  raise RuntimeError("nonCN real CN-IP answer missing/false FakeIP")
 resolved=socket.inet_ntoa(answer[-4:])
a=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",
 "(Get-NetAdapter -Name 'WBDWLMAIN' -ErrorAction Stop).ifIndex"],
 capture_output=True,text=True,timeout=9,check=True)
ifidx=int(a.stdout.strip())
if ifidx<=0:raise RuntimeError("signed Wintun ifindex absent")
marker=b"PLAN029-H1775-NONCN-CNIP-DIRECT-UDP"
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as app:
 # This on-link fixture explicitly selects actual Wintun via Winsock;
 # ordinary physical-bound/on-link application interception is NOT claimed.
 app.setsockopt(socket.IPPROTO_IP,getattr(socket,"IP_UNICAST_IF",31),struct.pack("!I",ifidx))
 app.bind((lease,0));app.settimeout(.8)
 until=time.monotonic()+18
 echoed=None
 while time.monotonic()<until:
  app.sendto(marker,(resolved,46111))
  try:wire,source=app.recvfrom(2048)
  except socket.timeout:continue
  if source==(resolved,46111) and wire==marker+b"-ECHO":
   echoed=wire;break
 if echoed is None:raise RuntimeError("physical Direct reverse never delivered to original app Wintun")
 print("PLAN029_H1775_REAL_WINDOWS_D2_CNIP_DIRECT "+json.dumps({
  "dns_query_name":"cn-ip.globalx.example","dns_display":"8.8.8.8",
  "dns_real_a":resolved,"fakeip":False,"app_bound_lease":lease,
  "app_forced_wintun_ifindex":ifidx,"business_dst":resolved,"echo_bytes":len(echoed)
 },sort_keys=True),flush=True)
