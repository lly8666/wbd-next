#!/usr/bin/env python3
"""H2429 real finite duplex/half-close/8 flows/UDP, scaled 1/16 for CHR free license."""
import socket,sys,hashlib,json,threading,time
role,port=sys.argv[1],int(sys.argv[2])
host="198.18.77.2"
up=hashlib.shake_256(b"upload-h2421").digest(128*1024)
down=hashlib.shake_256(b"download-h2421").digest(192*1024)
udp=b"actual-udp-nat-h2421"
def read_all(s):
    chunks=[]
    while True:
        b=s.recv(65536)
        if not b:return b"".join(chunks)
        chunks.append(b)
if role=="origin":
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as u,socket.socket() as listener:
        u.bind((host,port));u.settimeout(30)
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind((host,port));listener.listen(1);listener.settimeout(30)
        c,_=listener.accept()
        with c:
            c.settimeout(30);data=read_all(c);assert data==up
            c.sendall(down);c.shutdown(socket.SHUT_WR)
        errors=[]
        def extra(c):
            try:
                with c:
                    c.settimeout(30);assert read_all(c)==up[:16384]
                    c.sendall(down[:65536]);c.shutdown(socket.SHUT_WR)
            except BaseException as e:errors.append(repr(e))
        workers=[]
        for _ in range(8):
            c,_=listener.accept();t=threading.Thread(target=extra,args=(c,));t.start();workers.append(t)
        for t in workers:t.join(35);assert not t.is_alive()
        assert not errors,errors
        packet,addr=u.recvfrom(2048);assert packet==udp;u.sendto(packet,addr)
        print(json.dumps({"upload_sha256":hashlib.sha256(data).hexdigest(),"udp":True}),flush=True)
else:
    with socket.create_connection((host,port),timeout=30) as c:
        c.sendall(up);c.shutdown(socket.SHUT_WR);data=read_all(c);assert data==down
    errors=[]
    def extra(i):
        try:
            with socket.socket() as c:
                c.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,32768)
                c.settimeout(30);c.connect((host,port));c.sendall(up[:16384]);c.shutdown(socket.SHUT_WR)
                if i==0:time.sleep(1)
                assert read_all(c)==down[:65536]
        except BaseException as e:errors.append(repr(e))
    workers=[threading.Thread(target=extra,args=(i,)) for i in range(8)]
    for t in workers:t.start()
    for t in workers:t.join(35);assert not t.is_alive()
    assert not errors,errors
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as u:
        u.settimeout(5);u.sendto(udp,(host,port));assert u.recvfrom(2048)[0]==udp
    print(json.dumps({"status":"MEASURED","received_bytes":len(data),"upload_bytes":len(up),"download_sha256":hashlib.sha256(data).hexdigest(),"tcp_halfclose":True,"udp_nat_echo":True,"concurrent_connections":8,"concurrent_upload_bytes":8*16384,"concurrent_download_bytes":8*65536,"one_delayed_receiver_seconds":1}))
