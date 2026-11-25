#!/usr/bin/env python3
"""One real TCP connection. Sender socket pacing readback; measured steady interval.
No custom reliability or payload transformation."""
import socket,struct,sys,time,json
role,host,port,rate=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
cap=rate*125000
# Linux UAPI SO_MAX_PACING_RATE=47. Both supported ISAs are 64-bit.
opt=getattr(socket,"SO_MAX_PACING_RATE",47)
buf=bytearray(256*1024)
def sample(sock,source):
    start=time.monotonic();count=0;first=last=None
    while True:
        if source and time.monotonic()-start>=40:break
        n=sock.send(buf) if source else sock.recv_into(buf)
        now=time.monotonic()
        if not n:break
        elapsed=now-start
        if 10<=elapsed<=35:
            if first is None:first=now
            else:count+=n;last=now
    assert first is not None and last is not None and last-first>=24
    return {"bytes":count,"seconds":last-first,"bits_per_second":count*8/(last-first)}
if role=="source":
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((host,port));listener.listen(1);listener.settimeout(30)
        c,_=listener.accept()
        with c:
            c.settimeout(10)
            c.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,b"bbr")
            c.setsockopt(socket.SOL_SOCKET,opt,struct.pack("=Q",cap))
            actual=struct.unpack("=Q",c.getsockopt(socket.SOL_SOCKET,opt,8))[0]
            assert actual==cap,(actual,cap)
            # Receiver signals readiness; cap is configured before first data byte.
            assert c.recv(1)==b"R"
            row=sample(c,True);row["socket_pacing_bytes_per_s"]=actual
            c.shutdown(socket.SHUT_WR)
            print(json.dumps(row),flush=True)
else:
    with socket.create_connection((host,port),timeout=30) as c:
        c.settimeout(10);c.sendall(b"R")
        print(json.dumps(sample(c,False)),flush=True)
