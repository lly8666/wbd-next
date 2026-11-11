#!/usr/bin/env python3
"""PLAN028 H1548: genuine two-way app between ONE Wintun and FOUR Linux TUN
clients and their ONE original shared TLS443 Go/Rust TUN server.

This is deliberately neither an echo-only loop nor a fake data-plane owner:
each OS binds its own original inner /32, sends independent numbered UDP
application data, verifies first unique delivery and runs framed TCP both
directions concurrently. Kernel outer bytes, not these logical offers, are
the bandwidth qualification. One 600s common barrier, 200ms/0 or 30% loss.
"""
import argparse,ipaddress,json,os,pathlib,select,socket,struct,threading,time
NAMES=("alice","bob","carol","dave","erin")
IPS=("10.66.0.2","10.66.0.3","10.66.0.4","10.66.0.5","10.66.0.6")
MAGIC=b"WBD1548A"
HEADER=struct.Struct("!8sBQ")
TCP_HEAD=struct.Struct("!5sBBQ")
BASES={0:(8,14,11,6,9),30:(10,22,18,10,14)}
L1_BASES=(6,6,3,3,6) # inner Mbps per direction, actual Linux/Windows sockets
PHASES=(("warmup",10,.30),("first_wave",90,.60),
        ("sustained",180,1.),("overload",90,1.10),("recovery",230,1.))
assert sum(x[1] for x in PHASES)==600
MAX_SEQ=3600000

def phase(t,duration=600):
    if duration==150:
        if t<10:return "warmup",.30
        if t<120:return "sustained",1.
        if t<150:return "recovery",.80
        return "drain",0
    elapsed=0
    for label,sec,mult in PHASES:
        elapsed+=sec
        if t<elapsed:return label,mult
    return "drain",0

def bind_udp(ip,port):
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4*1024*1024)
    s.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,2*1024*1024)
    until=time.monotonic()+90
    while True:
        try:s.bind((ip,port));break
        except OSError:
            if time.monotonic()>until:raise
            time.sleep(.15)
    s.setblocking(False)
    return s

def tcp_exchange(index,is_server,local,remote,barrier,done,duration,counters,errors):
    sock=None;listener=None
    try:
        if is_server:
            listener=socket.socket()
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((local,46000+index));listener.listen(2)
            listener.settimeout(1)
            until=time.monotonic()+120
            while not done.is_set() and time.monotonic()<until:
                try:sock,_=listener.accept();break
                except socket.timeout:pass
            if sock is None:raise RuntimeError("real TCP peer not accepted "+str(index))
        else:
            until=time.monotonic()+120
            while not done.is_set() and time.monotonic()<until:
                candidate=socket.socket()
                candidate.settimeout(1)
                candidate.bind((local,0))
                try:candidate.connect((remote,46000+index));sock=candidate;break
                except OSError:
                    candidate.close();time.sleep(.2)
            if sock is None:raise RuntimeError("real client TCP not established "+str(index))
        sock.settimeout(.15)
        while not barrier.exists():
            if done.is_set():return
            time.sleep(.05)
        start=time.monotonic();next_send=start
        received=bytearray();seq=0
        while not done.is_set() and time.monotonic()-start<duration+5:
            now=time.monotonic()
            if now>=next_send and now-start<duration:
                # Source-separated TCP frames; real Windows or WSL sockets.
                frame=TCP_HEAD.pack(b"W15TC",index,1 if is_server else 0,seq)
                try:
                    sock.sendall(frame)
                    counters["sent"]+=1;seq+=1
                except (BlockingIOError,TimeoutError):pass
                next_send=now+1
            ready,_,_=select.select([sock],[],[],.1)
            if ready:
                part=sock.recv(16384)
                if not part:break
                received.extend(part)
                while len(received)>=TCP_HEAD.size:
                    magic,idx,direction,number=TCP_HEAD.unpack_from(received)
                    del received[:TCP_HEAD.size]
                    if magic!=b"W15TC" or idx!=index or direction==(1 if is_server else 0):
                        counters["invalid"]+=1
                    else:counters["received"]+=1
        if counters["sent"]==0 or counters["received"]==0:
            errors.append("TCP actual bilateral progress missing "+str(index))
    except BaseException as e:errors.append("TCP actor "+str(index)+" "+repr(e))
    finally:
        if sock:sock.close()
        if listener:listener.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--role",choices=("windows","linux-client","server"),required=True)
    ap.add_argument("--index",type=int,default=-1)
    ap.add_argument("--scene",choices=("loss0","loss30"),required=True)
    ap.add_argument("--barrier",type=pathlib.Path,required=True)
    ap.add_argument("--control",type=pathlib.Path,required=True)
    ap.add_argument("--out",type=pathlib.Path,required=True)
    ap.add_argument("--duration",type=int,default=600)
    ap.add_argument("--inner-ips",default="")
    ap.add_argument("--windows-auto-ip",action="store_true",
                    help="H1581: allow server-authenticated Windows auto /32")
    a=ap.parse_args()
    assert a.duration in (150,600) and len(os.environ["GITHUB_SHA"])==40
    # Real account-scoped OS /32, never the stale manual fixture addresses,
    # must reach UDP/TCP sockets for both 150s and 600s.
    assert a.inner_ips and (a.duration!=150 or a.scene=="loss0")
    actual=a.inner_ips.split(",")
    assert len(actual)==5 and len(set(actual))==5
    pool=ipaddress.ip_network("10.66.0.128/25")
    if a.windows_auto_ip:
        assert a.duration==150 and a.scene=="loss0"
        assert ipaddress.ip_address(actual[0]) in pool and actual[0]!="10.66.0.2"
    else:
        assert actual[0]=="10.66.0.2"
    assert all(ipaddress.ip_address(x) in pool for x in actual[1:])
    global IPS
    IPS=tuple(actual)
    loss=0 if a.scene=="loss0" else 30
    assert (a.role=="windows" and a.index==0 or
            a.role=="linux-client" and 1<=a.index<=4 or
            a.role=="server" and a.index==-1)
    indices=range(5) if a.role=="server" else (a.index,)
    ip="10.66.0.1" if a.role=="server" else IPS[a.index]
    peer=lambda i:IPS[i] if a.role=="server" else "10.66.0.1"
    a.out.parent.mkdir(parents=True,exist_ok=True)
    sockets={i:bind_udp(ip,45910+i) for i in indices}
    print("H1548_REAL_INNER_OS_APP_BOUND "+json.dumps({"role":a.role,"index":a.index,
       "local":ip,"outer_source":os.environ["GITHUB_SHA"],"scene":a.scene}),flush=True)
    done=threading.Event();errors=[]
    tcp={i:{"sent":0,"received":0,"invalid":0} for i in indices}
    threads=[threading.Thread(target=tcp_exchange,args=(
       i,a.role=="server",ip,peer(i),a.barrier,done,a.duration,tcp[i],errors),daemon=True)
       for i in indices]
    for thread in threads:thread.start()
    until=time.monotonic()+120
    while not a.barrier.exists():
        if time.monotonic()>until:raise RuntimeError("owned original app start barrier missing")
        time.sleep(.04)
    start=time.monotonic()
    seq={i:0 for i in indices};sent={i:0 for i in indices}
    got={i:0 for i in indices};duplicates={i:0 for i in indices}
    invalid={i:0 for i in indices};send_errors={i:0 for i in indices}
    seen={i:bytearray((MAX_SEQ+7)//8) for i in indices}
    last_rx={i:None for i in indices};maxgap={i:0 for i in indices}
    txbins={i:[0]*60010 for i in indices}
    rxbins={i:[0]*60020 for i in indices}
    credit={i:0 for i in indices};last_credit=start
    last_print=start;state="NOT_RUN";last_control=start-10;scale=1.0
    try:
        while time.monotonic()-start<a.duration+4:
            now=time.monotonic();elapsed=now-start
            label,mult=phase(elapsed,a.duration)
            if now-last_control>=5:
                rate_cfg=json.loads(a.control.read_text())
                scale=float(rate_cfg["scale"])
                if not .65<=scale<=1.35:raise RuntimeError("unsafe or foreign original stress rate")
                last_control=now
            if elapsed<a.duration:
                dt=min(.10,max(0,now-last_credit))
                last_credit=now
                for i in indices:
                    rate=(L1_BASES if a.duration==150 else BASES[loss])[i]*1e6/8*mult*scale
                    credit[i]=min(rate*.055,credit[i]+dt*rate)
                    batch=0
                    while credit[i]>=256 and batch<48:
                        length=256 if seq[i]%4==0 else 1120
                        if credit[i]<length:break
                        if seq[i]>=MAX_SEQ:raise RuntimeError("unique UDP sequence capacity")
                        payload=HEADER.pack(MAGIC,i,seq[i])+bytes(length-HEADER.size)
                        try:n=sockets[i].sendto(payload,(peer(i),45910+i))
                        except OSError:
                            send_errors[i]+=1
                            if send_errors[i]>=100:raise
                            break
                        if n!=length:raise RuntimeError("partial accepted native UDP")
                        bucket=min(int(elapsed*100),len(txbins[i])-1)
                        txbins[i][bucket]+=1;sent[i]+=1;seq[i]+=1
                        credit[i]-=length;batch+=1
            readable,_,_=select.select(list(sockets.values()),[],[],.0015)
            for so in readable:
                i=next(k for k,v in sockets.items() if v is so)
                for _ in range(125):
                    try:payload,origin=so.recvfrom(1400)
                    except BlockingIOError:break
                    if len(payload) not in (256,1120) or payload[:8]!=MAGIC or origin[0]!=peer(i):
                        invalid[i]+=1;continue
                    _,who,num=HEADER.unpack_from(payload)
                    if who!=i or num>=MAX_SEQ:
                        invalid[i]+=1;continue
                    q,bit=divmod(num,8)
                    if seen[i][q]&(1<<bit):duplicates[i]+=1;continue
                    seen[i][q]|=1<<bit;got[i]+=1
                    t=time.monotonic()
                    if last_rx[i] is not None:maxgap[i]=max(maxgap[i],t-last_rx[i])
                    last_rx[i]=t
                    bucket=min(max(0,int((t-start)*100)),len(rxbins[i])-1)
                    rxbins[i][bucket]+=1
            if now-last_print>=10:
                print("H1548_REAL_APP_TICK "+json.dumps({
                   "scene":a.scene,"role":a.role,"seconds":round(elapsed,1),
                   "phase":label,"scale":scale,"sent":sent,"unique_rx":got,
                   "tcp":tcp},separators=(",",":")),flush=True)
                last_print=now
        state=("COMPLETE_TRUE_150S_ORIGINAL_GO_RUST_INNER_APPLICATION" if a.duration==150
               else "COMPLETE_TRUE_600S_ORIGINAL_GO_RUST_INNER_APPLICATION")
    except BaseException as e:
        state="FAIL_OR_CAPACITY_LIMITED"
        errors.append(repr(e))
        raise
    finally:
        done.set()
        for t in threads:t.join(timeout=3)
        for so in sockets.values():so.close()
        result={"schema_version":1,"source_sha":os.environ.get("GITHUB_SHA"),
          "role":a.role,"index":a.index,"scene":a.scene,
          "real_native_os_inner_bind":ip,"duration_required_s":a.duration,
          "elapsed_s":round(time.monotonic()-start,3),"last_pace_scale":scale,
          "status":state,"base_mbps_per_direction":L1_BASES if a.duration==150 else BASES[loss],
          "actual_udp_kernel_send":{NAMES[i]:sent[i] for i in indices},
          "actual_udp_unique_received":{NAMES[i]:got[i] for i in indices},
          "duplicates":{NAMES[i]:duplicates[i] for i in indices},
          "invalid":{NAMES[i]:invalid[i] for i in indices},
          "send_errors":{NAMES[i]:send_errors[i] for i in indices},
          "max_active_udp_interarrival_ms":{NAMES[i]:round(maxgap[i]*1000,2) for i in indices},
          "tcp_real_frames":{NAMES[i]:tcp[i] for i in indices},
          "udp_sender_10ms_bins":{NAMES[i]:txbins[i] for i in indices},
          "udp_receiver_10ms_bins":{NAMES[i]:rxbins[i] for i in indices},
          "error":errors}
        a.out.write_text(json.dumps(result,separators=(",",":"))+"\n")
        print("H1548_REAL_OS_APP_FINAL "+json.dumps({k:v for k,v in result.items()
            if k not in ("udp_sender_10ms_bins","udp_receiver_10ms_bins")},separators=(",",":")),flush=True)
if __name__=="__main__":main()
