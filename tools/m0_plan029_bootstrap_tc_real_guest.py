#!/usr/bin/env python3
"""Real WSL2 physical UDP TC=1 -> SAME endpoint TCP53, once or twice after GUI Stop."""
import json,socket,select,struct,sys,time
if len(sys.argv) not in (3,4) or (len(sys.argv)==4 and sys.argv[3]!="reconnect"):
    raise RuntimeError("expected guest host [reconnect]")
guest,host=sys.argv[1:3]
target=2 if len(sys.argv)==4 else 1
qname=b"\x03vpn\x04edge\x02cn\x07example\x00"
question=qname+b"\x00\x01\x00\x01"
udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
tcp=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
for s in (udp,tcp):s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,0)
udp.bind((guest,53));tcp.bind((guest,53));tcp.listen(2)
print("PLAN029_BOOTSTRAP_TC_GUEST_READY",flush=True)
receipts=[]
active=None
deadline=time.monotonic()+(120 if target==2 else 50)
def exact(c,n):
    data=b""
    while len(data)<n:
        d=c.recv(n-len(data))
        if not d:raise RuntimeError("physical TCP DNS short response")
        data+=d
    return data
try:
    while time.monotonic()<deadline and len(receipts)<target:
        for s in select.select([udp,tcp],[],[],.3)[0]:
            if s is udp:
                wire,addr=udp.recvfrom(2048)
                if addr[0]!=host or wire[4:6]!=b"\x00\x01" or wire[12:]!=question or active is not None:
                    raise RuntimeError("unexpected physical UDP bootstrap identity")
                active={"udp_tc":1,"tcp_a":0,"guest":guest,"physical_host":host,"id":wire[:2].hex(),
                        "ordinal":len(receipts)+1}
                print("PLAN029_BOOTSTRAP_TC_GUEST_PHYSICAL_UDP_RX source="+host+
                      " resolver="+guest+" dns_id="+active["id"],flush=True)
                response=wire[:2]+b"\x83\x80\x00\x01\x00\x00\x00\x00\x00\x00"+question
                if udp.sendto(response,addr)!=len(response):raise RuntimeError("short UDP TC")
            else:
                if active is None:raise RuntimeError("unprompted TCP connection")
                conn,addr=tcp.accept()
                with conn:
                    conn.settimeout(6)
                    if addr[0]!=host:raise RuntimeError("TCP physical source differs")
                    n=struct.unpack("!H",exact(conn,2))[0]
                    if n<12 or n>1000:raise RuntimeError("unexpected DNS frame length")
                    wire=exact(conn,n)
                    if wire[:2].hex()!=active["id"] or wire[4:6]!=b"\x00\x01" or wire[12:]!=question:
                        raise RuntimeError("TC fallback not same transaction")
                    response=wire[:2]+b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"+question
                    response+=b"\xc0\x0c\x00\x01\x00\x01"+struct.pack("!I",30)+b"\x00\x04"+socket.inet_aton(guest)
                    conn.sendall(struct.pack("!H",len(response))+response)
                    active["tcp_a"]=1
                    print("PLAN029_BOOTSTRAP_TC_GUEST_SAME_ENDPOINT_TCP_A source="+host+
                          " resolver="+guest+" id="+active["id"],flush=True)
                print("PLAN029_BOOTSTRAP_TC_GUEST_RECEIPT "+json.dumps(active,sort_keys=True),flush=True)
                receipts.append(active)
                active=None
    if len(receipts)!=target:raise RuntimeError("physical TC/TCP bootstrap generations incomplete")
finally:
    udp.close();tcp.close()
print("PLAN029_BOOTSTRAP_TC_GUEST_ALL_RECEIPTS "+
      json.dumps({"count":len(receipts),"expected":target,"same_endpoint":guest},sort_keys=True),flush=True)
