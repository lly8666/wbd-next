#!/usr/bin/env python3
"""Actual socket sender with explicit CC and optional pacing. Fixed steady-window
wall-clock measurement includes stalls; no invented delivery or early EOF pass."""
import socket,struct,sys,time,json
role,host,port,rate,cc=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),sys.argv[5]
opt=getattr(socket,"SO_MAX_PACING_RATE",47)
buf=bytearray(256*1024)
def sample(sock,source):
    start=time.monotonic();count=total=0;end="deadline";sock.settimeout(.5)
    while time.monotonic()-start<(50 if source else 65):
        try:n=sock.send(buf) if source else sock.recv_into(buf)
        except socket.timeout:continue
        except OSError as e:end=repr(e);break
        elapsed=time.monotonic()-start
        if not n:end="eof";break
        total+=n
        if 15<=elapsed<45:count+=n
    return {"bytes":count,"seconds":30,"bits_per_second":count*8/30,"total_bytes":total,"elapsed_seconds":time.monotonic()-start,"end":end}
if role=="source":
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((host,port));listener.listen(1);listener.settimeout(60)
        c,_=listener.accept()
        with c:
            c.settimeout(30)
            c.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,cc.encode())
            actual_cc=c.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,32).split(b"\0")[0].decode()
            assert actual_cc==cc
            if rate:c.setsockopt(socket.SOL_SOCKET,opt,struct.pack("=Q",rate*125000))
            actual=struct.unpack("=Q",c.getsockopt(socket.SOL_SOCKET,opt,8))[0]
            assert not rate or actual==rate*125000
            assert c.recv(1)==b"R"
            row=sample(c,True);row.update(congestion_control=actual_cc,socket_pacing_bytes_per_s=actual)
            try:c.shutdown(socket.SHUT_WR)
            except OSError as e:row["shutdown_error"]=repr(e)
            print(json.dumps(row),flush=True)
else:
    with socket.create_connection((host,port),timeout=60) as c:
        c.settimeout(30);c.sendall(b"R")
        print(json.dumps(sample(c,False)),flush=True)
