#!/usr/bin/env python3
"""Native RAW scatter EDT capability; isolated synthetic UDP, no product session."""
import hashlib,json,os,pathlib,re,socket,struct,subprocess,sys,time,statistics,resource
O=pathlib.Path(os.environ.get("FQ_OUT","fq-out")).resolve()
COUNT=4096
def run(*args):
    return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True)
def save(p,x):
    p.write_text(json.dumps(x,indent=2)+"\n")
def recv(path):
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,8<<20)
    sock.setsockopt(socket.SOL_SOCKET,35,1) # SO_TIMESTAMPNS, 64-bit native
    sock.bind(("192.0.2.2",5202));sock.settimeout(3)
    pathlib.Path(str(path)+".ready").touch()
    rows=[]
    try:
        while len(rows)<COUNT:
            data,anc,flags,addr=sock.recvmsg(2048,128)
            if len(data)!=1132:raise ValueError("unexpected datagram length")
            stamps=[struct.unpack("=qq",v[:16]) for level,kind,v in anc if level==socket.SOL_SOCKET and kind==35]
            assert len(stamps)==1 and not flags
            sec,ns=stamps[0]
            rows.append([int.from_bytes(data[12:20],"big"),sec*10**9+ns])
    except socket.timeout:pass
    save(path,rows)
def ns(n,*args):return run("ip","netns","exec",n,*args)
def quant(xs):
    if not xs:return {}
    a=sorted(xs)
    return {str(p):a[min(len(a)-1,int(p*(len(a)-1)))] for p in (.0,.5,.95,.99,1.)}
def main():
    O.mkdir(parents=True,exist_ok=True)
    binary=pathlib.Path(sys.argv[1]).resolve()
    order=os.environ["FQ_ORDER"];assert order in ("ABBA","BAAB")
    a,b="wbd-fq-tx","wbd-fq-rx"
    save(O/"host.json",{"source":os.environ["GITHUB_SHA"],"run":os.environ["GITHUB_RUN_ID"],"order":order,
        "test_binary_sha256":hashlib.sha256(binary.read_bytes()).hexdigest(),"cpu":run("lscpu"),"kernel":run("uname","-a")})
    rows=[]
    try:
        run("ip","netns","add",a);run("ip","netns","add",b)
        run("ip","link","add","fq-tx","type","veth","peer","name","fq-rx")
        run("ip","link","set","fq-tx","netns",a);run("ip","link","set","fq-rx","netns",b)
        for space,dev,addr in ((a,"fq-tx","192.0.2.1"),(b,"fq-rx","192.0.2.2")):
            ns(space,"ip","addr","add",addr+"/24","dev",dev)
            ns(space,"ip","link","set",dev,"up")
            ns(space,"ip","link","set","lo","up")
            ns(space,"ethtool","-K",dev,"gro","off","gso","off","tso","off")
        ns(b,"sysctl","-qw","net.core.rmem_max=8388608")
        ns(a,"ping","-c","1","-W","2","192.0.2.2") # warm neighbor, not part of measurement
        for i,k in enumerate(order):
            d=O/f"{i}-{k}";d.mkdir()
            ns(a,"tc","qdisc","replace","dev","fq-tx","root","fq")
            before=json.loads(ns(a,"tc","-s","-j","qdisc","show","dev","fq-tx"))
            assert any(x["kind"]=="fq" for x in before)
            save(d/"qdisc-before.json",before)
            path=d/"received.json"
            with (d/"receiver.log").open("w") as out:
                rx=subprocess.Popen(["ip","netns","exec",b,sys.executable,str(pathlib.Path(__file__).resolve()),"recv",str(path)],stdout=out,stderr=subprocess.STDOUT)
                try:
                    for _ in range(100):
                        if pathlib.Path(str(path)+".ready").exists():break
                        if rx.poll() is not None:raise RuntimeError("receiver exited")
                        time.sleep(.02)
                    else:raise RuntimeError("receiver readiness timeout")
                    begin=resource.getrusage(resource.RUSAGE_CHILDREN)
                    t=time.monotonic_ns()
                    p=subprocess.run(["ip","netns","exec",a,"env","WBD_FQ_FIXTURE_MODE="+("timed" if k=="B" else "immediate"),str(binary),"--ignored","--exact","linux_batch::tests::native_raw_txtime_fq_scatter_receipt","--nocapture"],capture_output=True,text=True,timeout=30)
                    end=resource.getrusage(resource.RUSAGE_CHILDREN)
                    (d/"sender.log").write_text(p.stdout+p.stderr)
                    assert p.returncode==0 and "1 passed" in p.stdout,p.stdout[-2000:]+p.stderr[-1000:]
                    tx_wall=(time.monotonic_ns()-t)/1e9
                    assert rx.wait(10)==0
                finally:
                    if rx.poll() is None:rx.terminate();rx.wait(5)
            q=json.loads(ns(a,"tc","-s","-j","qdisc","show","dev","fq-tx"))
            save(d/"qdisc-after.json",q)
            received=json.loads(path.read_text())
            batches=[]
            for line in p.stdout.splitlines():
                if line.startswith("FQ_BATCH "):
                    fields=dict(re.findall(r"(\w+)=([^\s]+)",line))
                    batches.append({x:int(v) if re.fullmatch(r"-?\d+",v) else v for x,v in fields.items()})
            assert len(batches)==128 and all(x["accepted"]==32 for x in batches)
            by_id={i:t for i,t in received}
            spacing=[];span=[];edt_error=[];early=0
            for j,x in enumerate(batches):
                ids=range(j*32,j*32+32)
                if not all(z in by_id for z in ids):continue
                ts=[by_id[z] for z in ids]
                spacing.extend((v-u)/1000 for u,v in zip(ts,ts[1:]))
                span.append((ts[-1]-ts[0])/1000)
                if k=="B":
                    for n,z in enumerate(ids):
                        expected=x["wall_ns"]+(x["first_edt_ns"]-x["mono_ns"])+n*15467
                        e=(by_id[z]-expected)/1000
                        edt_error.append(e);early+=e < -20
            row={"leg":k,"mode":"edt" if k=="B" else "immediate","accepted":sum(x["accepted"] for x in batches),
                "received":len(received),"unique":len(by_id),"missing":COUNT-len(set(range(COUNT))&by_id.keys()),
                "duplicates":len(received)-len(by_id),"adjacent_inversions":sum(v[0]<u[0] for u,v in zip(received,received[1:])),
                "within_batch_gap_us":quant(spacing),"batch_span_us":quant(span),"edt_error_us":quant(edt_error),
                "early_over_20us":early,"submit_duration_us":quant([(x["returned_ns"]-x["mono_ns"])/1000 for x in batches]),
                "outq_before":quant([x["outq_before"] for x in batches]),"outq_after":quant([x["outq_after"] for x in batches]),
                "drain":next((l for l in p.stdout.splitlines() if l.startswith("FQ_DRAIN ")),None),
                "sender_cpu_s":end.ru_utime+end.ru_stime-begin.ru_utime-begin.ru_stime,"sender_wall_s":tx_wall,
                "qdisc":q,"scope":"software receiver timestamps; local veth, not wire departure or product goodput"}
            save(d/"result.json",row);rows.append(row);save(O/"summary.json",{"order":order,"rows":rows})
        assert all(x["missing"]==x["duplicates"]==0 and x["unique"]==COUNT for x in rows), "datagram identity qualification failed"
    finally:
        for n in (a,b):subprocess.run(["ip","netns","del",n],check=False)
if __name__=="__main__":
    if sys.argv[1]=="recv":recv(pathlib.Path(sys.argv[2]))
    else:main()
