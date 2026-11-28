#!/usr/bin/env python3
"""Fixture-only sampled IPv4/TCP header identity; no payload in retained artifacts.

Eight owned synthetic WAN/VXLAN interfaces, same directional filter and tuple/seq
keys. Local capture timestamps only; no cross-host clock arithmetic.
Capture for the whole experiment to avoid clock/window mismatch.
Capture losses invalidate inference, not the application result.
"""
import collections,json,os,pathlib,re,signal,struct,subprocess,sys,time
OUT=pathlib.Path("h2228-out")
READY=OUT/"path-sample-ready.json"
RESULT=OUT/"path-sample-result.json"
# Select one 1KiB sequence interval out of each 64KiB. This is a
# deterministic sequence-stratified sample, NOT independent random sampling.
# Only reverse synthetic business tuples; no management or TLS secrets.
FILTER="ip and src host 10.248.82.2 and dst host 10.248.81.2 and tcp and (src port 443 or src port 5202) and (tcp[4:4] & 0xfc00 = 0)"
DEV={"server":[("h228node","wan0","server_tx"),(None,"h228vs","server_vx_tx")],
     "client":[(None,"h228vc","client_vx_rx"),("h228node","wan0","client_rx")],
     "relay":[(None,"h228vs","relay_server_vx_rx"),("h228rt","rsrv0","relay_rx"),
              ("h228rt","rcli0","relay_tx"),(None,"h228vc","relay_client_vx_tx")]}
def save(p,v):
    p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
def decode(p):
    counts=collections.Counter();timestamps=collections.defaultdict(list);records=0;ignored=0
    with p.open("rb") as f:
        hdr=f.read(24)
        if len(hdr)!=24:raise ValueError("short pcap header")
        order={b"\xd4\xc3\xb2\xa1":"<",b"\x4d\x3c\xb2\xa1":"<",
               b"\xa1\xb2\xc3\xd4":">",b"\xa1\xb2\x3c\x4d":">"}.get(hdr[:4])
        if order is None or struct.unpack_from(order+"I",hdr,20)[0]!=1:raise ValueError("expected Ethernet pcap")
        nanos=hdr[:4] in (b"\x4d\x3c\xb2\xa1",b"\xa1\xb2\x3c\x4d")
        while True:
            h=f.read(16)
            if not h:break
            if len(h)!=16:raise ValueError("short pcap record")
            sec,frac,n,wire=struct.unpack(order+"IIII",h)
            if n>54:raise ValueError("unexpected snaplen")
            b=f.read(n)
            if len(b)!=n:raise ValueError("truncated pcap")
            records+=1
            if n<54 or b[12:14]!=b"\x08\x00" or b[14]!=0x45 or b[23]!=6:
                ignored+=1;continue
            ip_len=struct.unpack_from("!H",b,16)[0]
            sport,dport,seq,ack=struct.unpack_from("!HHII",b,34)
            th=(b[46]>>4)*4;payload=ip_len-20-th
            if payload<=0 or th<20:continue
            # IP ID and ACK may differ for retransmissions; retain those
            # in the identity so repeated seq ranges are not collapsed.
            ident=struct.unpack_from("!H",b,18)[0]
            key=f"{sport}:{dport}:{seq}:{ack}:{ip_len}:{ident}:{b[47]}"
            counts[key]+=1
            timestamps[key].append(sec*1_000_000+(frac//1000 if nanos else frac))
    return {"records":records,"ignored_nonstandard":ignored,"data_packets":sum(counts.values()),
            "identity_counts":dict(counts),"timestamps_us":dict(timestamps)}
def start(role):
    OUT.mkdir(exist_ok=True)
    ps=[];stopping=False
    def request_stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,request_stop)
    signal.signal(signal.SIGINT,request_stop)
    rows={};err=None
    try:
        for ns,dev,label in DEV[role]:
            pcap=OUT/(label+".pcap");log=OUT/(label+".capture.log")
            argv=(["ip","netns","exec",ns] if ns else [])+["tcpdump","-n","-i",dev,"-s","54","-B","4096","-w",str(pcap),FILTER]
            with log.open("w") as f:
                proc=subprocess.Popen(argv,stdout=f,stderr=subprocess.STDOUT)
            ps.append((label,proc,pcap,log,argv))
        until=time.monotonic()+15
        while not all("listening on" in log.read_text(errors="replace") for _,_,_,log,_ in ps):
            if stopping or time.monotonic()>until or any(p.poll() is not None for _,p,_,_,_ in ps):
                raise RuntimeError("capture did not start")
            time.sleep(.1)
        save(READY,{"role":role,"pid":os.getpid(),"source_sha":os.environ.get("GITHUB_SHA"),"filter":FILTER,"wall_ns":time.time_ns()})
        while not stopping:
            if any(p.poll() is not None for _,p,_,_,_ in ps):raise RuntimeError("capture exited early")
            time.sleep(.2)
    except Exception as e:err=repr(e)
    finally:
        for label,p,pcap,log,argv in ps:
            if p.poll() is None:p.send_signal(signal.SIGINT)
        for label,p,pcap,log,argv in ps:
            try:p.wait(10)
            except subprocess.TimeoutExpired:p.kill();p.wait()
            raw=log.read_text(errors="replace")
            m=re.search(r"(\d+) packets dropped by kernel",raw)
            rec={"argv":argv,"rc":p.returncode,"kernel_drops":int(m[1]) if m else None}
            try:rec.update(decode(pcap))
            except Exception as e:rec["error"]=repr(e)
            rec["valid"]=p.returncode==0 and rec["kernel_drops"]==0 and rec.get("data_packets",0)>0 and rec.get("ignored_nonstandard")==0
            rows[label]=rec
            # Retain numeric identities only, never the raw pcap.
            pcap.unlink(missing_ok=True)
        save(RESULT,{"role":role,"filter":FILTER,"error":err,"rows":rows,
                     "valid":err is None and len(rows)==len(DEV[role]) and all(v["valid"] for v in rows.values())})
def stop():
    if not READY.exists():raise RuntimeError("capture readiness missing")
    if not RESULT.exists():
        os.kill(json.loads(READY.read_text())["pid"],signal.SIGTERM)
        end=time.monotonic()+30
        while not RESULT.exists() and time.monotonic()<end:time.sleep(.2)
    r=json.loads(RESULT.read_text())
    print(json.dumps({"role":r["role"],"valid":r["valid"],"rows":{k:{a:b for a,b in v.items() if a not in ("identity_counts","timestamps_us")} for k,v in r["rows"].items()}}))
    if not r["valid"]:raise SystemExit(2)
if __name__=="__main__":
    if sys.argv[1]=="start":start(sys.argv[2])
    elif sys.argv[1]=="stop":stop()
