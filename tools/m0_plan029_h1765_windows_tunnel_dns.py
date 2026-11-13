#!/usr/bin/env python3
"""D1 signed Windows original app UDP53: nonCN QNAME stays Tunnel DNS."""
import json,socket,sys,time
lease,presented,expected_a=sys.argv[1:4]
name=b"\x03www\x07globalx\x07example\x00"
question=name+b"\x00\x01\x00\x01"
txid=b"\x17\x65"
query=txid+b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"+question
reply=None;remote=None
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as app:
    app.bind((lease,0));app.settimeout(1.5)
    deadline=time.monotonic()+16
    while time.monotonic()<deadline:
        app.sendto(query,(presented,53))
        try:data,peer=app.recvfrom(2048)
        except socket.timeout:continue
        if data[:2]==txid:
            reply=data;remote=peer;break
if reply is None:raise RuntimeError("nonCN Tunnel DNS reply absent; no direct or fallback accepted")
if (remote!=(presented,53) or reply[2:4]!=b"\x81\x80" or
    reply[4:8]!=b"\x00\x01\x00\x01" or reply[12:12+len(question)]!=question or
    len(reply)!=12+len(question)+16 or reply[-4:]!=socket.inet_aton(expected_a)):
    raise RuntimeError("Tunnel DNS reverse source/id/question/A mismatch or FakeIP rewrite")
print("PLAN029_H1765_REAL_WINDOWS_TUN_DNS "+json.dumps({
    "query_app_dns":presented,"reply_source":remote[0],"reply_port":remote[1],
    "qname":"www.globalx.example","original_id":txid.hex(),
    "real_answer":socket.inet_ntoa(reply[-4:]),"source_lease":lease,
    "fakeip":False},sort_keys=True),flush=True)
