#!/usr/bin/env python3
"""Native independent app probes during one bulk stream. No WBD private interface."""
import socket,sys,time,threading,json,statistics,math,struct
role,port=sys.argv[1],int(sys.argv[2]);host="198.18.77.2"
if role=="origin":
    def udp():
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.bind((host,port))
            while True:
                b,a=s.recvfrom(2048);s.sendto(b,a)
    def echo(c):
        with c:
            c.settimeout(2)
            try:
                b=b""
                while len(b)<16:
                    v=c.recv(16-len(b))
                    if not v:return
                    b+=v
                c.sendall(b)
            except OSError:pass
    threading.Thread(target=udp,daemon=True).start()
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        s.bind((host,port));s.listen(64)
        while True:
            c,_=s.accept();threading.Thread(target=echo,args=(c,),daemon=True).start()
else:
    rows={}
    # Start after iperf's warmup begins, measure fixed offered schedule during measured interval.
    start=time.monotonic()+9
    def worker(kind,count,period):
        data=[];miss=0;late=0
        u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM) if kind=="udp" else None
        if u:u.settimeout(.15)
        for i in range(count):
            target=start+i*period
            time.sleep(max(0,target-time.monotonic()))
            t=time.monotonic();payload=struct.pack("!QQ",i,0x2426)
            if t-target>period:late+=1
            try:
                if kind=="tcp":
                    with socket.create_connection((host,port),timeout=.25) as c:
                        c.sendall(payload);b=b""
                        while len(b)<len(payload):
                            v=c.recv(len(payload)-len(b))
                            if not v:break
                            b+=v
                else:
                    u.sendto(payload,(host,port));deadline=t+.15
                    while True:
                        u.settimeout(max(.001,deadline-time.monotonic()))
                        b=u.recv(2048)
                        if b==payload or time.monotonic()>=deadline:break
                if b==payload:data.append((time.monotonic()-t)*1000)
                else:miss+=1
            except OSError:miss+=1
        if u:u.close()
        values=sorted(data)
        rows[kind]={"offered":count,"completed":len(values),"missed":miss,"late_schedule":late,"p50_ms":statistics.median(values) if values else None,"p99_ms":values[math.ceil(.99*len(values))-1] if values else None,"all_success_ms":values}
    threads=[threading.Thread(target=worker,args=("tcp",100,.2)),threading.Thread(target=worker,args=("udp",400,.05))]
    for t in threads:t.start()
    for t in threads:t.join()
    print(json.dumps(rows),flush=True)
