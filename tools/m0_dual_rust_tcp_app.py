#!/usr/bin/env python3
"""Exact finite TCP duplex and UDP echo, no private WBD wire or protocol."""
import socket,sys,hashlib,json,threading,time,os,struct
role,port=sys.argv[1],int(sys.argv[2])
# Fixed-byte recovery fixture, independent of iperf3's timed control stream.
# Only the application offer is paced; the product owns all TCP behavior.
if role in ("recovery-origin","recovery-client"):
    host,target,offer=sys.argv[3],int(sys.argv[4]),int(sys.argv[5])
    pause=float(sys.argv[6]) if len(sys.argv)>6 else 0.0
    request=b"fixed-byte-recovery-v1"
    pattern=hashlib.shake_256(b"fixed-byte-recovery-v1").digest(65536)
    digest=hashlib.sha256()
    # Linux UAPI struct tcp_info through bytes_retrans, native endian.
    def kernel_info(sock):
        raw=sock.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,256)
        assert len(raw)>=216
        u32=lambda at:struct.unpack_from("=I",raw,at)[0]
        u64=lambda at:struct.unpack_from("=Q",raw,at)[0]
        return dict(state=raw[0],snd_mss=u32(16),pmtu=u32(60),unacked=u32(24),
                    total_retrans=u32(100),bytes_acked=u64(120),
                    bytes_sent=u64(200),bytes_retrans=u64(208),raw_hex=raw.hex())
    if role=="recovery-origin":
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((host,port));listener.listen(1);listener.settimeout(120) # fixture waits for cold path readiness, not a product timer
            c,_=listener.accept()
            with c:
                c.settimeout(30);req=bytearray()
                while True:
                    b=c.recv(1024)
                    if not b:break
                    req.extend(b)
                    assert len(req)<=len(request)
                assert req==request
                n=0;start=time.monotonic();due=start;max_sendall=0.0;blocked_s=0.0
                while n<target:
                    size=min(65536,target-n)
                    block=(n.to_bytes(8,"big")+pattern[8:])[:size]
                    wait=due-time.monotonic()
                    if wait>0:time.sleep(wait)
                    t=time.monotonic();c.sendall(block);elapsed=time.monotonic()-t
                    max_sendall=max(max_sendall,elapsed)
                    if elapsed>=0.25:blocked_s+=elapsed
                    digest.update(block);n+=size
                    # Never make up late app offer with an unbounded burst.
                    due=max(due+size*8/offer,time.monotonic())
                c.shutdown(socket.SHUT_WR)
                elapsed=time.monotonic()-start
                final={}
                if os.environ.get("DUAL_TCP_KERNEL_FINAL")=="1":
                    # Fixture only: keep FD until all payload and FIN are ACKed.
                    # Does not delay client EOF or change measured app duration.
                    deadline=time.monotonic()+15
                    info=kernel_info(c)
                    while not (info["state"]==7 and info["unacked"]==0 and info["bytes_acked"]>=target) and time.monotonic()<deadline:
                        time.sleep(.02)
                        info=kernel_info(c)
                    final={"kernel_tcp_final":info,"kernel_final_valid":info["state"]==7 and info["unacked"]==0 and info["bytes_acked"]>=target and info["bytes_sent"]>=target}
                print(json.dumps({"sent_bytes":n,"sha256":digest.hexdigest(),"offer_bps":offer,"seconds":elapsed,"max_sendall_seconds":max_sendall,"sendall_over_250ms_seconds":blocked_s,**final}),flush=True)
    else:
        connect_started=time.monotonic()
        with socket.create_connection((host,port),timeout=30) as c:
            connected_at=time.monotonic()
            c.sendall(request);c.shutdown(socket.SHUT_WR)
            start=time.monotonic();first=None;n=0;paused=0.0
            while True:
                b=c.recv(65536)
                if not b:break
                if first is None:first=time.monotonic()
                n+=len(b);digest.update(b)
                assert n<=target
                if pause and not paused and n>=16*1024*1024:
                    t=time.monotonic();time.sleep(pause);paused=time.monotonic()-t
            elapsed=time.monotonic()-start
            assert n==target,(n,target)
            print(json.dumps({"received_bytes":n,"sha256":digest.hexdigest(),"eof":True,"seconds":elapsed,
                "first_data_seconds":first-start if first is not None else None,
                "connect_seconds":connected_at-connect_started,"request_sent_from_connect_seconds":start-connect_started,
                "first_data_from_connect_seconds":first-connect_started if first is not None else None,"mbps":n*8/elapsed/1e6,"paused_seconds":paused}),flush=True)
    raise SystemExit(0)

host="198.18.77.2"
up=hashlib.shake_256(b"upload-h2421").digest(2*1024*1024)
down=hashlib.shake_256(b"download-h2421").digest(3*1024*1024)
udp=b"actual-udp-nat-h2421"
def read_all(s,first=None):
    chunks=[]
    while True:
        b=s.recv(65536)
        if not b:return b"".join(chunks)
        if first is not None and not first:first.append(time.monotonic_ns())
        chunks.append(b)
if role=="origin":
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as u,socket.socket() as listener:
        u.bind((host,port));u.settimeout(30)
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind((host,port));listener.listen(16);listener.settimeout(30) # eight concurrent clients, not a listen-overflow test
        c,_=listener.accept()
        with c:
            c.settimeout(30);data=read_all(c);assert data==up
            c.sendall(down);c.shutdown(socket.SHUT_WR)
        errors=[]
        def extra(c):
            try:
                with c:
                    c.settimeout(30);assert read_all(c)==up[:262144]
                    c.sendall(down[:1048576]);c.shutdown(socket.SHUT_WR)
            except BaseException as e:errors.append(repr(e))
        workers=[]
        for _ in range(8):
            c,_=listener.accept();t=threading.Thread(target=extra,args=(c,));t.start();workers.append(t)
        for t in workers:t.join(35);assert not t.is_alive()
        assert not errors,errors
        packet,addr=u.recvfrom(2048);assert packet==udp;u.sendto(packet,addr)
        print(json.dumps({"upload_sha256":hashlib.sha256(data).hexdigest(),"udp":True}),flush=True)
else:
    first=[];start=time.monotonic_ns()
    with socket.create_connection((host,port),timeout=30) as c:
        c.sendall(up);c.shutdown(socket.SHUT_WR);sent=time.monotonic_ns();data=read_all(c,first);assert data==down
    errors=[]
    def extra(i):
        try:
            with socket.socket() as c:
                c.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,32768)
                c.settimeout(30);c.connect((host,port));c.sendall(up[:262144]);c.shutdown(socket.SHUT_WR)
                if i==0:time.sleep(1)
                assert read_all(c)==down[:1048576]
        except BaseException as e:errors.append(repr(e))
    workers=[threading.Thread(target=extra,args=(i,)) for i in range(8)]
    for t in workers:t.start()
    for t in workers:t.join(35);assert not t.is_alive()
    assert not errors,errors
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as u:
        u.settimeout(5);u.sendto(udp,(host,port));assert u.recvfrom(2048)[0]==udp
    print(json.dumps({"status":"MEASURED","received_bytes":len(data),"upload_bytes":len(up),"download_sha256":hashlib.sha256(data).hexdigest(),"first_response_ns_after_request_fin":first[0]-sent,"first_response_ns_after_connect_start":first[0]-start,"upload_sha256":hashlib.sha256(up).hexdigest(),"tcp_halfclose":True,"udp_nat_echo":True,"concurrent_connections":8,"concurrent_upload_bytes":8*262144,"concurrent_download_bytes":8*1048576,"one_delayed_receiver_seconds":1}))
