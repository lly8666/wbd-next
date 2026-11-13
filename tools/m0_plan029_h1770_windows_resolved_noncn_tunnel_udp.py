#!/usr/bin/env python3
"""Real Windows Wintun app uses actual prior nonCN DNS A for next UDP business."""
import json,socket,sys,time
lease,resolved=sys.argv[1:3]
marker=b"PLAN029-H1770-NONCN-DNS-A-FOLLOWUP-TUNNEL-UDP"
remote=(resolved,46114)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as app:
 app.bind((lease,0));app.settimeout(.7)
 deadline=time.monotonic()+12
 reply=None;reply_from=None
 while time.monotonic()<deadline:
  if app.sendto(marker,remote)!=len(marker):
   raise RuntimeError("Windows Wintun actual app UDP incomplete write")
  try:
   wire,source=app.recvfrom(512)
  except socket.timeout:continue
  if wire==marker+b"-ECHO":
   reply=wire;reply_from=source;break
if reply is None or reply_from!=remote:
 raise RuntimeError("nonCN original DNS A follow-on Tunnel business return missing")
print("PLAN029_H1770_REAL_WINDOWS_NONCN_A_TUNNEL_BUSINESS "+json.dumps({
 "lease4":lease,"dns_real_a":resolved,"reply_ip":reply_from[0],
 "reply_port":reply_from[1],"received_bytes":len(reply),
 "fakeip":False,"kernel_socket":"ORIGINAL_WINTUN_APP"},sort_keys=True),flush=True)
