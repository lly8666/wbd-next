#!/usr/bin/env python3
"""One synthetic continuous TCP download, 180s source window, drain/hash/EOF.
No application rate limiter. Per-second actual receiver bytes from first DATA.
"""
import socket,sys,hashlib,json,time,struct
role,port,host,duration=sys.argv[1],int(sys.argv[2]),sys.argv[3],int(sys.argv[4])
assert duration==180
request=b"m0-longflow-v1"
pattern=hashlib.shake_256(request).digest(65536)
digest=hashlib.sha256()
def info(sock):
    raw=sock.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,256)
    assert len(raw)>=216
    u32=lambda at:struct.unpack_from("=I",raw,at)[0]
    u64=lambda at:struct.unpack_from("=Q",raw,at)[0]
    return dict(state=raw[0],snd_mss=u32(16),pmtu=u32(60),unacked=u32(24),total_retrans=u32(100),
                bytes_acked=u64(120),bytes_sent=u64(200),bytes_retrans=u64(208),raw_hex=raw.hex())
if role=="origin":
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((host,port));listener.listen(1);listener.settimeout(120)
        c,_=listener.accept()
        with c:
            c.settimeout(30);req=bytearray()
            while True:
                b=c.recv(1024)
                if not b:break
                req.extend(b);assert len(req)<=len(request)
            assert req==request
            cc=c.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,32).rstrip(b"\0").decode()
            initial=info(c);n=0;start=time.monotonic();deadline=start+duration
            max_sendall=blocked_s=0.0
            while time.monotonic()<deadline:
                block=n.to_bytes(8,"big")+pattern[8:]
                t=time.monotonic();c.sendall(block);dt=time.monotonic()-t
                max_sendall=max(max_sendall,dt)
                if dt>=.25:blocked_s+=dt
                digest.update(block);n+=len(block)
            elapsed=time.monotonic()-start
            c.shutdown(socket.SHUT_WR)
            until=time.monotonic()+15
            final=info(c)
            while not(final["state"]==7 and final["unacked"]==0 and final["bytes_acked"]>=n) and time.monotonic()<until:
                time.sleep(.02);final=info(c)
            valid=final["state"]==7 and final["unacked"]==0 and final["bytes_acked"]>=n and final["bytes_sent"]>=n
            print(json.dumps({"sent_bytes":n,"sha256":digest.hexdigest(),"seconds":elapsed,"planned_send_seconds":duration,
                "application_offer":"saturated","max_sendall_seconds":max_sendall,"sendall_over_250ms_seconds":blocked_s,
                "kernel_cc":cc,"kernel_initial":initial,"kernel_tcp_final":final,"kernel_final_valid":valid}),flush=True)
elif role=="client":
    connect_start=time.monotonic()
    with socket.create_connection((host,port),timeout=30) as c:
        connected=time.monotonic();c.sendall(request);c.shutdown(socket.SHUT_WR)
        start=time.monotonic();first=None;n=0;bins=[]
        while True:
            b=c.recv(65536)
            if not b:break
            now=time.monotonic()
            if first is None:first=now
            idx=int(now-first)
            while len(bins)<=idx:bins.append(0)
            bins[idx]+=len(b);n+=len(b);digest.update(b)
        end=time.monotonic()
        assert first is not None and n>0
        elapsed=end-start
        print(json.dumps({"received_bytes":n,"sha256":digest.hexdigest(),"eof":True,"seconds":elapsed,
            "data_seconds":end-first,"first_data_seconds":first-start,"connect_seconds":connected-connect_start,
            "first_data_from_connect_seconds":first-connect_start,"mbps":n*8/elapsed/1e6,
            "receiver_second_bytes":bins,"first_180s_received_bytes":sum(bins[:180]),
            "first_180s_mbps":sum(bins[:180])*8/duration/1e6,
            "receiver_window_complete":end-first>=duration}),flush=True)
else:raise SystemExit("unknown role")
