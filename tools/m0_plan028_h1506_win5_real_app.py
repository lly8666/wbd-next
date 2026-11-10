#!/usr/bin/env python3
"""H1506 true 5x Windows Wintun <-> Linux shared TUN UDP app, 600 s.

All sent/received datagrams traverse original signed Windows Npcap/Wintun,
Go TLS443, Rust AEAD/FEC and Linux original Go/Rust TUN. No UDP echo shim,
no product modification and no simulated ready/packet delivery. Both
directions send INDEPENDENT numbered business datagrams at per-mode rates.
"""
import argparse,json,os,pathlib,select,socket,struct,time
NAMES=("alice","bob","carol","dave","erin")
# Each direction. 46Mbps combined *before* actual per-mode outer inflation.
BASE=(8.0,5.0,4.0,2.0,4.0)
MAGIC=b"WBD1506A"
HDR=struct.Struct("!8sBQ")   # source real lease id + per-side unique seq
PAYLOAD=1120                 # Fits Fixed6 true 1280 outer MTU
LIMIT=1800000
PORT=45903
INNER=("10.66.0.2","10.66.0.3","10.66.0.4","10.66.0.5","10.66.0.6")
def read_control(p):
    if not p.exists():return 1.0
    data=json.loads(p.read_text())
    scale=float(data["scale"])
    if not .35<=scale<=1.70:raise RuntimeError("foreign/invalid bounded rate scale")
    return scale
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--side",choices=("windows","linux"),required=True)
    p.add_argument("--scene",choices=("loss0","loss30"),required=True)
    p.add_argument("--barrier",type=pathlib.Path,required=True)
    p.add_argument("--control",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    p.add_argument("--duration",type=int,required=True)
    a=p.parse_args()
    assert a.duration==600 and os.environ.get("GITHUB_SHA")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    local=INNER if a.side=="windows" else ("10.66.0.1",)
    socks=[]
    for ip in local:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4*1024*1024)
        s.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,2*1024*1024)
        deadline=time.monotonic()+60
        while True:
            try:s.bind((ip,PORT));break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.1)
        s.setblocking(False);socks.append(s)
    print("H1506_REAL_"+a.side.upper()+"_FIVE_CLIENT_APP_BOUND "+
          json.dumps({"scene":a.scene,"local":local,"port":PORT,"source":os.environ["GITHUB_SHA"]}),flush=True)
    until=time.monotonic()+90
    while not a.barrier.exists():
        if time.monotonic()>until:raise RuntimeError("real cross-OS app barrier missing")
        time.sleep(.025)
    start=time.monotonic()
    sent=[0]*5;got=[0]*5;dups=[0]*5;invalid=[0]*5
    last_rx=[None]*5;gap=[0.0]*5
    bits=[bytearray((LIMIT+7)//8) for _ in range(5)]
    buffers=[bytearray(PAYLOAD) for _ in range(5)]
    for i,b in enumerate(buffers):HDR.pack_into(b,0,MAGIC,i,0)
    credit=[0.0]*5;last_credit=start
    last_sample=start;last_control=start-10
    scale=1.0;send_error=None;heartbeat=0
    tx_bins=[[0]*60000 for _ in range(5)]
    rx_bins=[[0]*60800 for _ in range(5)]
    try:
        while time.monotonic()-start<a.duration+8:
            now=time.monotonic();elapsed=now-start
            if now-last_control>=5:
                scale=read_control(a.control);last_control=now
            if elapsed<a.duration:
                dt=min(.12,max(0,now-last_credit))
                for i in range(5):
                    credit[i]=min(BASE[i]*1e6/8*.10*scale,
                                  credit[i]+dt*BASE[i]*1e6/8*scale)
                last_credit=now
                for i in range(5):
                    batch=0
                    src=socks[i] if a.side=="windows" else socks[0]
                    dest=("10.66.0.1",PORT) if a.side=="windows" else (INNER[i],PORT)
                    while credit[i]>=PAYLOAD and batch<48:
                        if sent[i]>=LIMIT:
                            raise RuntimeError("actual app sequence capacity bounded")
                        HDR.pack_into(buffers[i],0,MAGIC,i,sent[i])
                        try:n=src.sendto(buffers[i],dest)
                        except OSError as e:
                            send_error={"who":NAMES[i],"errno":getattr(e,"errno",None),
                                        "at_s":round(elapsed,3),"message":str(e)}
                            break
                        if n!=PAYLOAD:raise RuntimeError("partial actual socket kernel send")
                        k=int(elapsed*100)
                        if k<len(tx_bins[i]):tx_bins[i][k]+=1
                        sent[i]+=1;credit[i]-=PAYLOAD;batch+=1
                    if send_error:break
            if send_error:break
            readable,_,_=select.select(socks,[],[],.0015)
            for s in readable:
                for _ in range(160):
                    try:data,src=s.recvfrom(1600)
                    except BlockingIOError:break
                    if len(data)!=PAYLOAD or data[:8]!=MAGIC:
                        continue
                    _,i,seq=HDR.unpack_from(data)
                    if not i<5 or seq>=LIMIT or (
                        a.side=="windows" and (socks[i] is not s or src[0]!="10.66.0.1")
                    ) or (a.side=="linux" and src[0]!=INNER[i]):
                        if i<5:invalid[i]+=1
                        continue
                    idx=seq//8;mask=1<<(seq%8)
                    if bits[i][idx]&mask:
                        dups[i]+=1;continue
                    bits[i][idx]|=mask
                    got[i]+=1
                    t=time.monotonic()
                    if last_rx[i] is not None:gap[i]=max(gap[i],t-last_rx[i])
                    last_rx[i]=t
                    b=int((t-start)*100)
                    if b<len(rx_bins[i]):rx_bins[i][b]+=1
            if now-last_sample>=1:
                heartbeat+=1
                print(json.dumps({"phase":"real_native_app_1s","scene":a.scene,
                    "side":a.side,"elapsed_s":round(elapsed,2),
                    "scale":scale,"sent":dict(zip(NAMES,sent)),
                    "received_first":dict(zip(NAMES,got))},separators=(",",":")),flush=True)
                last_sample=now
        outcome="COMPLETE_TRUE_600S_REAL_NATIVE_APP"
    except BaseException as e:
        outcome="FAIL_OR_CAPACITY_INTERRUPTED"
        send_error=send_error or {"exception":repr(e)}
        raise
    finally:
        elapsed=time.monotonic()-start
        for s in socks:s.close()
        result={"schema_version":1,"scene":a.scene,"source_sha":os.environ.get("GITHUB_SHA"),
                "side":a.side,"original_os_socket":True,"duration_requested_s":a.duration,
                "elapsed_s":round(elapsed,3),"classification":outcome,
                "base_inner_mbps_per_client_per_direction":dict(zip(NAMES,BASE)),
                "udp_payload_bytes":PAYLOAD,
                "actual_kernel_send_accepted":dict(zip(NAMES,sent)),
                "actual_unique_received":dict(zip(NAMES,got)),
                "duplicate":dict(zip(NAMES,dups)),
                "invalid":dict(zip(NAMES,invalid)),
                "max_interdelivery_ms":{n:round(v*1000,2) for n,v in zip(NAMES,gap)},
                "actual_sender_10ms_bins":dict(zip(NAMES,tx_bins)),
                "real_receiver_10ms_bins":dict(zip(NAMES,rx_bins)),
                "error":send_error}
        a.out.write_text(json.dumps(result,separators=(",",":"))+"\n")
        print("H1506_REAL_FIVE_APP_ORIGINAL_FINAL "+json.dumps(
            {k:v for k,v in result.items() if k not in
             ("actual_sender_10ms_bins","real_receiver_10ms_bins")},separators=(",",":")),flush=True)
if __name__=="__main__":main()
