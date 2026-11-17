#!/usr/bin/env python3
"""Real physical DNS responder for three CN A queries: before TTL, after TTL, after normal GUI reconnect."""
import json,select,socket,struct,sys,time
if len(sys.argv)!=3:raise RuntimeError("expected physical guest and Windows host4")
guest,host=sys.argv[1:]
dns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
dns.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
dns.bind((guest,53))
qname=b"\x03www\x02cn\x07example\x00"
question=qname+b"\x00\x01\x00\x01"
cname=b"\x04edge\x03cdn\x07example\x00"
print("PLAN029_H2063_TTL_GUEST_READY",flush=True)
received=[]
deadline=time.monotonic()+130
try:
    while len(received)<3 and time.monotonic()<deadline:
        if not select.select([dns],[],[],.3)[0]:continue
        packet,remote=dns.recvfrom(2048)
        if (remote[0]!=host or len(packet)<12 or
            packet[4:6]!=b"\x00\x01" or packet[12:]!=question):
            raise RuntimeError("foreign or invalid physical CN DNS request")
        # TTL=2s: first answer must expire before second independent socket,
        # then a third real Windows app query after normal owned Stop/reconnect.
        response=packet[:2]+b"\x81\x80\x00\x01\x00\x02\x00\x00\x00\x00"+question
        response+=b"\xc0\x0c\x00\x05\x00\x01"+struct.pack("!I",2)+struct.pack("!H",len(cname))+cname
        response+=cname+b"\x00\x01\x00\x01"+struct.pack("!I",2)+b"\x00\x04"+socket.inet_aton(guest)
        if dns.sendto(response,remote)!=len(response):
            raise RuntimeError("short physical DNS reply")
        identity=packet[:2].hex()
        if identity not in [q["id"] for q in received]:
            expected="29%02x"%(0x61+len(received))
            if identity!=expected:
                raise RuntimeError("unexpected new DNS transaction during TTL/reconnect")
            received.append({"ordinal":len(received)+1,"id":identity,
                             "physical_source":remote[0],"resolver":guest,"ttl":2})
            print("PLAN029_H2063_TTL_GUEST_PHYSICAL_RX "+
                  json.dumps(received[-1],sort_keys=True),flush=True)
    if len(received)!=3:raise RuntimeError("three physical TTL/reconnect DNS requests not observed")
finally:
    dns.close()
print("PLAN029_H2063_TTL_GUEST_RECEIPT "+
      json.dumps({"count":len(received),"queries":received,"ttl_s":2},sort_keys=True),flush=True)
