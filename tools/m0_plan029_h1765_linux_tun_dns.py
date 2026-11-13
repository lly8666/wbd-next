#!/usr/bin/env python3
"""D1 signed true guest TUN DNS/53: non-CN QNAME only, never underlay."""
import json,socket,sys
resolver,client,answer4=sys.argv[1:4]
name=b"\x03www\x07globalx\x07example\x00"
question=name+b"\x00\x01\x00\x01"
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as listener:
    listener.bind((resolver,53))
    listener.settimeout(26)
    print("PLAN029_H1765_LINUX_TUN_DNS53_READY",flush=True)
    query,peer=listener.recvfrom(2048)
    if peer[0]!=client or len(query)<12 or query[12:]!=question or query[4:6]!=b"\x00\x01":
        raise RuntimeError("foreign or unexpected real tunnel DNS QNAME/peer")
    response=query[:2]+b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"+question
    response+=b"\xc0\x0c"+b"\x00\x01\x00\x01"+(60).to_bytes(4,"big")
    response+=b"\x00\x04"+socket.inet_aton(answer4)
    if listener.sendto(response,peer)!=len(response):
        raise RuntimeError("guest TUN DNS reply not submitted")
    print("PLAN029_H1765_REAL_LINUX_TUN_DNS "+json.dumps({
        "upstream_ip":resolver,"client_ip":peer[0],"client_port":peer[1],
        "qname":"www.globalx.example","reply_a":answer4,
        "wire_id":query[:2].hex(),"reply_bytes":len(response)},sort_keys=True),flush=True)
