#!/usr/bin/env python3
"""D1 signed real guest TUN DNS/53: target-only one-upstream QNAME."""
import json,socket,sys,time
resolver,client,answer4=sys.argv[1:4]
name=b"\x03www\x07globalx\x07example\x00"
question=name+b"\x00\x01\x00\x01"
def is_target_question(query):
    return (len(query)>=12 and query[4:6]==b"\x00\x01"
            and query[12:]==question)
unrelated=0
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as listener:
    listener.bind((resolver,53))
    deadline=time.monotonic()+26
    print("PLAN029_H1765_LINUX_TUN_DNS53_READY",flush=True)
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:raise RuntimeError("target Tunnel DNS question absent before 26s deadline")
        listener.settimeout(remaining)
        query,peer=listener.recvfrom(2048)
        # The *same* original Linux TUN DNS/53 listener also receives
        # unrelated on-device/system DNS QNAMEs. Ignore these silently,
        # never answer or count them as a target query, and never switch
        # the configured upstream or use the physical Direct resolver.
        if not is_target_question(query):
            unrelated+=1
            if unrelated>64:
                raise RuntimeError("H1784 unrelated TUN DNS traffic exceeded bounded 64")
            continue
        if peer[0]!=client:
            raise RuntimeError("exact target Tunnel DNS arrived from foreign lease")
        break
    response=query[:2]+b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"+question
    response+=b"\xc0\x0c"+b"\x00\x01\x00\x01"+(60).to_bytes(4,"big")
    response+=b"\x00\x04"+socket.inet_aton(answer4)
    if listener.sendto(response,peer)!=len(response):
        raise RuntimeError("guest TUN DNS reply not submitted")
    print("PLAN029_H1765_REAL_LINUX_TUN_DNS "+json.dumps({
        "upstream_ip":resolver,"client_ip":peer[0],"client_port":peer[1],
        "qname":"www.globalx.example","reply_a":answer4,
        "wire_id":query[:2].hex(),"reply_bytes":len(response),
        "unrelated_dns_ignored":unrelated,"target_queries":1
    },sort_keys=True),flush=True)
