#!/usr/bin/env python3
"""Actual dual Rust TCP Normal product over four native Linux namespaces; functional only."""
import hashlib,json,os,pathlib,signal,subprocess,sys,time
O=pathlib.Path(os.environ.get("DUAL_TCP_OUT","dual-tcp-out")).resolve(); O.mkdir(exist_ok=True)
ROOT=pathlib.Path("linux-plan029-public-bundle").resolve()
C,R,S,T="h21client","h21router","h21server","h21origin"
N=(C,R,S,T)
LOSS=0
DELAY=0
RATE=0
def run(*args):
    try:return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True)
    except subprocess.CalledProcessError as e:
        print(f"COMMAND_FAILED {args[0]} rc={e.returncode}: {e.output}",file=sys.stderr,flush=True)
        raise
def ns(n,*args):return run("ip","netns","exec",n,*args)
def save(p,d):p.write_text(json.dumps(d,indent=2)+"\n")
def spawn(n,path,*args):
    with path.open("w") as f:
        p=subprocess.Popen(["ip","netns","exec",n,*map(str,args)],stdout=f,stderr=subprocess.STDOUT)
    p.fixture_log=path
    return p
def until(p,pred):
    for i in range(240):
        if p.poll() is not None:
            raise RuntimeError(f"early exit {p.returncode}: {p.fixture_log}\n{p.fixture_log.read_text()[-3500:]}")
        if pred():return
        time.sleep(.25)
    raise RuntimeError(f"readiness timeout: {p.fixture_log}\n{p.fixture_log.read_text()[-3500:]}")
def stop(p):
    if p and p.poll() is None:
        p.send_signal(signal.SIGTERM)
        try:p.wait(20)
        except subprocess.TimeoutExpired:p.kill();p.wait();raise RuntimeError("Stop timeout")
def make():
    run("modprobe","tcp_bbr")
    for n in N:
        run("ip","netns","add",n);ns(n,"ip","link","set","lo","up")
        for key in ("net.ipv4.conf.all.rp_filter=0","net.ipv4.conf.default.rp_filter=0","net.ipv4.tcp_congestion_control=bbr","net.ipv4.tcp_rmem=4096 87380 67108864","net.ipv4.tcp_wmem=4096 65536 67108864","net.core.rmem_max=67108864","net.core.wmem_max=67108864"):
            ns(n,"sysctl","-qw",key)
    for n,a,ip,m,b,jp in [(C,"wan0","10.248.81.2/24",R,"rc0","10.248.81.1/24"),(S,"wan0","10.248.82.2/24",R,"rs0","10.248.82.1/24"),(S,"exit0","198.18.77.1/24",T,"app0","198.18.77.2/24")]:
        run("ip","link","add","h21v1","type","veth","peer","name","h21v2")
        for dev,name,space,addr in (("h21v1",a,n,ip),("h21v2",b,m,jp)):
            run("ip","link","set",dev,"netns",space)
            ns(space,"ip","link","set",dev,"name",name)
            ns(space,"ip","addr","add",addr,"dev",name)
            ns(space,"ip","link","set",name,"mtu","1500","up")
            ns(space,"sysctl","-qw","net.ipv4.conf."+name+".rp_filter=0")
            # One netem event per actual L3 datagram, not a GSO train.
            ns(space,"ethtool","-K",name,"gro","off","gso","off","tso","off")
    ns(C,"ip","route","add","10.248.82.0/24","via","10.248.81.1")
    ns(S,"ip","route","add","10.248.81.0/24","via","10.248.82.1")
    ns(T,"ip","route","add","10.66.0.0/24","via","198.18.77.1")
    for n in (R,S):ns(n,"sysctl","-qw","net.ipv4.ip_forward=1")
    for n,flag in ((C,"--dport"),(S,"--sport")):
        ns(n,"iptables","-A","OUTPUT","-o","wan0","-p","tcp",flag,"443","--tcp-flags","RST","RST","-j","DROP")
    ns(S,"iptables","-t","nat","-A","POSTROUTING","-o","exit0","-s","10.66.0.0/24","-j","MASQUERADE")
    ns(T,"tc","qdisc","replace","dev","app0","root","fq","maxrate","600mbit")
    save(O/"topology.json",{n:{"routes":ns(n,"ip","route"),"links":json.loads(ns(n,"ip","-j","link")),"cc":ns(n,"sysctl","-n","net.ipv4.tcp_congestion_control")} for n in N})
def shape(active):
    for dev in ("rc0","rs0"):
        args=["tc","qdisc","replace","dev",dev,"root","netem","delay",str(DELAY if active else 0)+"ms","loss","random",str(LOSS if active else 0)+"%","limit","65536"]
        if active and RATE:
            args[args.index("limit")+1]="3000"
            args+=["rate",str(RATE)+"mbit"]
        ns(R,*args)
def functional():
    d=O/"normal";d.mkdir()
    server=client=app=None
    port=5300
    common=["--server-name","wbd-h2228.example.test","--route-key-hex-file",O/"route-key.hex",
        "--mode","normal","--outer-repair","on","--outer-mtu","1460","--dual-rust-tcp"]
    try:
        server=spawn(S,d/"server.log","env","LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-server",
            "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
            "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--users-file",O/"users.json",
            "--lease-pool","10.66.0.128/25","--tls-cert",O/"cert.pem","--tls-key",O/"key.pem",*common)
        until(server,lambda:"V4_PUBLIC_MULTI_SERVER_READY role=server port=443" in (d/"server.log").read_text())
        client=spawn(C,d/"client.log","env","LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-client",
            "--raw-interface","wan0","--local-ip","10.248.81.2","--local-port","44100",
            "--peer-ip","10.248.82.2","--peer-port","443","--tun-name","wbdc0",
            "--username","bench","--password","DUAL-TCP-FIXTURE","--auto-ip","--installation-id-file",d/"install",*common)
        until(client,lambda:"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" in (d/"client.log").read_text())
        until(server,lambda:"WBD_DUAL_RUST_TCP_OWNER_START" in (d/"server.log").read_text())
        assert "WBD_DUAL_RUST_TCP_OWNER_START" in (d/"client.log").read_text()
        ns(C,"ip","route","replace","198.18.77.2/32","dev","wbdc0")
        (d/"client-route.txt").write_text(ns(C,"ip","route","get","198.18.77.2"))
        assert "dev wbdc0" in (d/"client-route.txt").read_text()
        app_path=pathlib.Path("tools/m0_dual_rust_tcp_app.py").resolve()
        app=spawn(T,d/"app-origin.log",sys.executable,app_path,"origin",str(port))
        until(app,lambda:f":{port} " in ns(T,"ss","-ltn"))
        raw=ns(C,sys.executable,str(app_path),"client",str(port))
        (d/"app-client.json").write_text(raw)
        app.wait(40);assert app.returncode==0
        row=json.loads(raw);origin=json.loads((d/"app-origin.log").read_text())
        assert row["upload_sha256"]==origin["upload_sha256"]
        assert row["received_bytes"]==3*1024*1024 and row["upload_bytes"]==2*1024*1024
        assert row["tcp_halfclose"] and row["udp_nat_echo"] and origin["udp"]
        assert row["concurrent_connections"]==8
        stop(client);stop(server)
        sl=(d/"server.log").read_text();cl=(d/"client.log").read_text()
        for log in (sl,cl):
            assert "WBD_DUAL_RUST_TCP_OWNER_STOP" in log
            assert "V4_PUBLIC_SHARED_TUN_STOP" in log and "reader_joined=1" in log
        if os.environ.get("WBD_M0_LINUX_PARITY")!="0" and os.environ.get("WBD_M0_LOCAL_TUN_GSO")!="0":
            assert "WBD_M0_LOCAL_TUN_VNET" in cl and "WBD_M0_LOCAL_TUN_VNET" not in sl
            gso=next(x for x in cl.splitlines() if "WBD_M0_LOCAL_TUN_GSO groups=" in x)
            parts=dict(x.split("=",1) for x in gso.split() if "=" in x)
            assert int(parts["groups"])>0 and int(parts["segments"])>=2*int(parts["groups"]),gso
            row["local_gso"]={k:int(v) for k,v in parts.items()}
        if os.environ.get("WBD_M0_LINUX_PARITY")!="0":
            for log,expected in ((sl,"true"),(cl,"false")):
                pub=next(s for s in log.splitlines() if "WBD_M0_TCP_PUBLISH " in s)
                assert " ingress_first="+expected+" " in pub and "admission_drain_before_service=true" in pub,pub
                m4=next(s for s in log.splitlines() if "WBD_M0_TCP_M4_CLOCK " in s)
                vals=dict(x.split("=",1) for x in m4.split() if "=" in x)
                assert int(vals["copied"])>0,m4
            row["selected_default_receipts"]=True
        expected_slots=2048 if os.environ.get("WBD_M0_NATIVE_INBOX_DOUBLE")=="1" else 1024
        for log in (sl,cl):
            receipt=next(s for s in log.splitlines() if "M0_PLAN029_NATIVE_INBOX_BOUND " in s)
            assert " slots="+str(expected_slots)+" " in receipt,receipt
        row["inbox_slots"]=expected_slots
        if os.environ.get("WBD_M0_NATIVE_PACE_QUANTUM8")=="1":
            assert "WBD_M0_TCP_PACE_QUANTUM mss=8" in sl and "WBD_M0_TCP_PACE_QUANTUM mss=8" in cl
            row["native_pace_quantum_mss"]=8
        if os.environ.get("WBD_M0_RX_PACKET_STATS")=="1":
            row["packet_rx_stats"]={}
            for log,role in ((sl,"server"),(cl,"client")):
                rec=next(s for s in log.splitlines() if "WBD_M0_RAW_RX_PACKET_STATS " in s)
                row["packet_rx_stats"][role]=rec
        assert "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED" in sl
        assert "WBD_TCP_SPLICE_READY" not in sl
        assert server.returncode==0 and client.returncode==0
        assert "TPROXY" not in ns(S,"iptables","-t","mangle","-S")
        row.update(status="FUNCTIONAL_PASS",server_exit=server.returncode,client_exit=client.returncode,
            source_sha=os.environ["GITHUB_SHA"],run_id=os.environ["GITHUB_RUN_ID"],
            scope="Native original Go TLS/Rust Normal paired TCP, real four kernel netns, app bytes/hash and UDP/owned Stop; no performance or physical claim",
            manifest=json.loads((ROOT/"manifest.json").read_text()),origin=origin)
        save(O/"summary.json",row);print(json.dumps(row),flush=True)
    finally:
        for p in (app,client,server):
            if p and p.poll() is None:stop(p)
        (d/"install").unlink(missing_ok=True)

try:
    make()
    (O/"route-key.hex").write_text(hashlib.sha256(("DUAL-TCP"+os.environ["GITHUB_RUN_ID"]).encode()).hexdigest()+"\n")
    (O/"users.json").write_text(json.dumps({"bench":"DUAL-TCP-FIXTURE"}))
    for name in ("route-key.hex","users.json"):(O/name).chmod(0o600)
    run("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",str(O/"key.pem"),"-out",str(O/"cert.pem"),"-subj","/CN=wbd-h2228.example.test","-addext","subjectAltName=DNS:wbd-h2228.example.test")
    (O/"key.pem").chmod(0o600)
    shape(False)
    functional()
finally:
    for name in ("route-key.hex","users.json","key.pem","cert.pem"):
        (O/name).unlink(missing_ok=True)
    for n in reversed(N):subprocess.run(["ip","netns","del",n],check=False)
