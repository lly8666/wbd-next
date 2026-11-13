#!/usr/bin/env python3
"""Original Windows Wintun app: DNS timeout must not fall back to Direct DNS."""
import json,socket,sys,time
lease,presented=sys.argv[1:3]
name=b"\x09no-backup\x07globalx\x07example\x00"
question=name+b"\x00\x01\x00\x01"
txid=b"\x17\x67"
query=txid+b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"+question
sent=0
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as app:
 app.bind((lease,0))
 app.settimeout(.55)
 for _ in range(3):
  written=app.sendto(query,(presented,53))
  if written!=len(query):raise RuntimeError("Wintun kernel socket incomplete DNS query send")
  sent+=1
  try:
   reply,from_peer=app.recvfrom(2048)
  except socket.timeout:continue
  if reply[:2]==txid:
   raise RuntimeError("DNS blackhole unexpectedly returned a response from "+repr(from_peer))
 if sent!=3:raise RuntimeError("DNS blackhole app failed to send real queries")
print("PLAN029_H1767_REAL_WINDOWS_DNS_BLACKHOLE "+json.dumps({
  "source_lease":lease,"presented_dns":presented,"qname":"no-backup.globalx.example",
  "query_count":sent,"unexpected_response":False,
  "socket":"REAL_WINDOWS_WINTUN_KERNEL_UDP53"},sort_keys=True),flush=True)
