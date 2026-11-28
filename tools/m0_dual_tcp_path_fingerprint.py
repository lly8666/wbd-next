#!/usr/bin/env python3
"""Fixture-only full bidirectional header trace on four owned VXLAN interfaces.
No payload retained. Nanosecond software timestamps are not synchronized clocks.
Compare repeated identities in capture order, flag offload aggregation and capture loss.
"""
import collections,gzip,json,os,pathlib,re,signal,struct,subprocess,sys,time
OUT=pathlib.Path("h2228-out")
READY=OUT/"path-sample-ready.json"
RESULT=OUT/"path-sample-result.json"
# Full synthetic business tuples only, in both directions. No management traffic.
FILTER="ip and tcp and ((src host 10.248.82.2 and dst host 10.248.81.2 and (src port 443 or src port 5202)) or (src host 10.248.81.2 and dst host 10.248.82.2 and (dst port 443 or dst port 5202)))"
DEV={"server":[(None,"h228vs","server_vx")],
     "client":[(None,"h228vc","client_vx")],
     "relay":[(None,"h228vs","relay_server_vx"),(None,"h228vc","relay_client_vx")]}
def host_sample():
    return {"wall_ns":time.time_ns(),"monotonic_ns":time.monotonic_ns(),**{name:pathlib.Path("/proc",name).read_text() for name in ("stat","softirqs","net/softnet_stat")}}
def save(p,v):
    # The stop process waits for RESULT to exist; publish only complete JSON.
    tmp=p.with_suffix(".tmp")
    tmp.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
    tmp.replace(p)
def decode(p,trace):
    counts=collections.Counter();records=0;ignored=0;aggregated=0;nonstandard=0
    first=None;last=None
    with p.open("rb") as f,gzip.open(trace,"wt",compresslevel=3) as out:
        hdr=f.read(24)
        if len(hdr)!=24:raise ValueError("short pcap header")
        order={b"\xd4\xc3\xb2\xa1":"<",b"\x4d\x3c\xb2\xa1":"<",b"\xa1\xb2\xc3\xd4":">",b"\xa1\xb2\x3c\x4d":">"}.get(hdr[:4])
        if order is None or struct.unpack_from(order+"I",hdr,20)[0]!=1:raise ValueError("expected Ethernet pcap")
        nanos=hdr[:4] in (b"\x4d\x3c\xb2\xa1",b"\xa1\xb2\x3c\x4d")
        out.write("wall_ns,sport,dport,seq,ack,ip_len,ipid,flags,window,tcp_header_bytes,wire_len\n")
        while True:
            h=f.read(16)
            if not h:break
            if len(h)!=16:raise ValueError("short pcap record")
            sec,frac,n,wire=struct.unpack(order+"IIII",h)
            if n>54:raise ValueError("unexpected snaplen")
            data=f.read(n)
            if len(data)!=n:raise ValueError("truncated pcap")
            records+=1
            if n<54 or data[12:14]!=b"\x08\x00" or data[14]!=0x45 or data[23]!=6:
                ignored+=1;continue
            ip_len=struct.unpack_from("!H",data,16)[0]
            sport,dport,seq,ack=struct.unpack_from("!HHII",data,34)
            th=(data[46]>>4)*4;payload=ip_len-20-th
            if th<20 or payload<0:nonstandard+=1;continue
            stamp=sec*1_000_000_000+(frac if nanos else frac*1000)
            first=stamp if first is None else first;last=stamp
            ipid=struct.unpack_from("!H",data,18)[0]
            flags=data[47];window=struct.unpack_from("!H",data,48)[0]
            out.write(f"{stamp},{sport},{dport},{seq},{ack},{ip_len},{ipid},{flags},{window},{th},{wire}\n")
            port=443 if 443 in (sport,dport) else 5202
            direction="forward" if sport==port else "reverse"
            counts[f"{port}:{direction}:"+("data" if payload else "control")]+=1
            if ip_len>(1160 if port==443 else 1500):aggregated+=1
    return {"records":records,"ignored_nonstandard":ignored+nonstandard,"decoded":sum(counts.values()),"counts":dict(counts),
            "aggregated_records":aggregated,"nanosecond_pcap":nanos,"first_wall_ns":first,"last_wall_ns":last,"trace":trace.name}
def start(role):
    OUT.mkdir(exist_ok=True)
    ps=[];stopping=False
    def request_stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,request_stop)
    signal.signal(signal.SIGINT,request_stop)
    rows={};err=None
    before=host_sample();cpu_start=os.times()
    try:
        for ns,dev,label in DEV[role]:
            pcap=OUT/(label+".pcap");log=OUT/(label+".capture.log")
            argv=(["ip","netns","exec",ns] if ns else [])+["tcpdump","-n","--time-stamp-precision=nano","-i",dev,"-s","54","-B","16384","-w",str(pcap),FILTER]
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
        after=host_sample();capture_end=os.times()
        for label,p,pcap,log,argv in ps:
            try:p.wait(10)
            except subprocess.TimeoutExpired:p.kill();p.wait()
            raw=log.read_text(errors="replace")
            m=re.search(r"(\d+) packets dropped by kernel",raw)
            rec={"argv":argv,"rc":p.returncode,"kernel_drops":int(m[1]) if m else None}
            try:rec.update(decode(pcap,OUT/(label+'.headers.csv.gz')))
            except Exception as e:rec["error"]=repr(e)
            rec["valid"]=p.returncode==0 and rec["kernel_drops"]==0 and rec.get("decoded",0)>0 and rec.get("nanosecond_pcap") and rec.get("ignored_nonstandard")==0
            rows[label]=rec
            # Retain numeric identities only, never the raw pcap.
            pcap.unlink(missing_ok=True)
        save(RESULT,{"role":role,"filter":FILTER,"error":err,"rows":rows,
                     "host_before":before,"host_after":after,"capture_parent_cpu_times":dict(zip(("user","system","children_user","children_system","elapsed"),(b-a for a,b in zip(cpu_start,capture_end)))),"capture_and_decode_cpu_times":dict(zip(("user","system","children_user","children_system","elapsed"),(b-a for a,b in zip(cpu_start,os.times())))),"valid":err is None and len(rows)==len(DEV[role]) and all(v["valid"] for v in rows.values())})
def stop():
    if not READY.exists():raise RuntimeError("capture readiness missing")
    if not RESULT.exists():
        os.kill(json.loads(READY.read_text())["pid"],signal.SIGTERM)
        end=time.monotonic()+300
        while not RESULT.exists() and time.monotonic()<end:time.sleep(.2)
    r=json.loads(RESULT.read_text())
    print(json.dumps({"role":r["role"],"valid":r["valid"],"rows":{k:{a:b for a,b in v.items() if a not in ("identity_counts","timestamps_us")} for k,v in r["rows"].items()}}))
    if not r["valid"]:raise SystemExit(2)
if __name__=="__main__":
    if sys.argv[1]=="start":start(sys.argv[2])
    elif sys.argv[1]=="stop":stop()
