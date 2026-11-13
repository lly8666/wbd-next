#!/usr/bin/env python3
"""Real D2 partial: after nonCN DNS A is delivered, only Linux original TUN gets app UDP."""
import json,socket,sys
dst,lease=sys.argv[1:3]
marker=b"PLAN029-H1770-NONCN-DNS-A-FOLLOWUP-TUNNEL-UDP"
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as peer:
 peer.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
 peer.bind((dst,46114))
 peer.settimeout(20)
 print("PLAN029_H1770_LINUX_ORIGINAL_TUN_A_BUSINESS_READY",flush=True)
 packet,source=peer.recvfrom(512)
 if source[0]!=lease or packet!=marker:
  raise RuntimeError("foreign/modified post-DNS original Tunnel UDP business")
 if peer.sendto(marker+b"-ECHO",source)!=len(marker)+5:
  raise RuntimeError("original Linux TUN UDP reply short")
 print("PLAN029_H1770_REAL_LINUX_TUN_A_BUSINESS "+json.dumps({
  "destination":dst,"source_lease":source[0],"source_port":source[1],
  "received_bytes":len(packet),"echo_bytes":len(marker)+5,
  "physical_underlay":"NOT_SELECTED_BY_THIS_TUN_SOCKET"},sort_keys=True),flush=True)
