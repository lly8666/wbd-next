#!/usr/bin/env python3
"""Native original-product same-VM A/B benchmark; one clean download scene."""
import hashlib,json,os,pathlib,re,signal,subprocess,sys,time,statistics
O=pathlib.Path("dual-tcp-perf-out").resolve(); O.mkdir(exist_ok=True)
ROOTS={k:pathlib.Path("bundles",k).resolve() for k in ("A","B")}
SOURCES={"A":"26b11e2da236e909b73f461964c52d5a86d42dca","B":"86e3ec30010a59cbb60539b902cb96dc21e04d6a"}
COMPARE=os.environ.get("DUAL_TCP_COMPARE","splice")
ARCH=os.environ.get("DUAL_TCP_ARCH","x86_64")
if COMPARE=="toolchain":
    SOURCES={k:os.environ["GITHUB_SHA"] for k in ROOTS}
elif COMPARE=="profile":
    ROOTS={"B":ROOTS["B"]}; SOURCES={"B":SOURCES["B"]}
C,R,S,T="h21client","h21router","h21server","h21origin"
N=(C,R,S,T)
ORDER="B" if COMPARE=="profile" else "ABBA"
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
def stats(p):
    s=pathlib.Path(f"/proc/{p.pid}/stat").read_text().rsplit(")",1)[1].split()
    return int(s[11])+int(s[12])
def host():
    return [int(x) for x in pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
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
def snap(p):
    save(p,{dev:json.loads(ns(R,"tc","-s","-j","qdisc","show","dev",dev)) for dev in ("rc0","rs0")})

def manifest(k):
    root=ROOTS[k]
    m=json.loads((root/"manifest.json").read_text())
    assert m["source_sha"]==SOURCES[k] and m["architecture"]==ARCH
    if COMPARE=="toolchain":assert m["rust"]=={"A":"1.85.1","B":"1.100.0"}[k]
    for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==m["sha256"][name]
    return {"manifest":m,"manifest_sha256":hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest()}

def leg(i,k):
    d=O/f"{i}-{k}";d.mkdir()
    root=ROOTS[k];port=5300+i;server=client=app=profile=None
    splice=(k=="A" and COMPARE=="splice")
    common=["--server-name","wbd-h2228.example.test","--route-key-hex-file",O/"route-key.hex",
            "--mode","normal","--outer-repair","on","--outer-mtu","1460"]
    server_flags=["--tcp-proxy-cc","bbr","--tcp-proxy-port","46180"] if splice else ["--dual-rust-tcp"]
    client_flags=[] if splice else ["--dual-rust-tcp"]
    begin=time.monotonic_ns()
    try:
        server=spawn(S,d/"server.log","env","LD_LIBRARY_PATH="+str(root),root/"wbd-v4-server",
            "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
            "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--users-file",O/"users.json",
            "--lease-pool","10.66.0.128/25","--tls-cert",O/"cert.pem","--tls-key",O/"key.pem",*common,*server_flags)
        until(server,lambda:"V4_PUBLIC_MULTI_SERVER_READY role=server port=443" in (d/"server.log").read_text())
        client=spawn(C,d/"client.log","env","LD_LIBRARY_PATH="+str(root),root/"wbd-v4-client",
            "--raw-interface","wan0","--local-ip","10.248.81.2","--local-port",str(44100+i*2),
            "--peer-ip","10.248.82.2","--peer-port","443","--tun-name","wbdc0",
            "--username","bench","--password","DUAL-TCP-PERF","--auto-ip","--installation-id-file",d/"install",*common,*client_flags)
        until(client,lambda:"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" in (d/"client.log").read_text())
        if splice:
            assert "WBD_TCP_SPLICE_READY tun=wbds0 port=46180 cc=bbr" in (d/"server.log").read_text()
        else:
            until(server,lambda:"WBD_DUAL_RUST_TCP_OWNER_START" in (d/"server.log").read_text())
            assert "WBD_DUAL_RUST_TCP_OWNER_START" in (d/"client.log").read_text()
        ns(C,"ip","route","replace","198.18.77.2/32","dev","wbdc0")
        route=ns(C,"ip","route","get","198.18.77.2");assert "dev wbdc0" in route
        (d/"client-route.txt").write_text(route)
        (d/"server-tun-qdisc.txt").write_text(ns(S,"tc","-s","qdisc","show","dev","wbds0"))
        snap(d/"before-netem.json")
        app=spawn(T,d/"origin.log","iperf3","-s","-1","-B","198.18.77.2","-p",str(port))
        until(app,lambda:f":{port} " in ns(T,"ss","-ltn"))
        if COMPARE=="profile":
            with (d/"perf-record.log").open("w") as log:
                profile=subprocess.Popen([os.environ["DUAL_TCP_PERF_BIN"],"record","-e","cpu-clock","-F","99","--call-graph","dwarf,8192","-p",str(client.pid),"-o",str(d/"perf.data")],stdout=log,stderr=subprocess.STDOUT)
            time.sleep(.25)
        pre=[stats(server),stats(client)];h0=host();tick=os.sysconf("SC_CLK_TCK");t=time.monotonic_ns()
        with (d/"iperf.json").open("w") as out,(d/"iperf.err").open("w") as err:
            p=subprocess.run(["ip","netns","exec",C,"iperf3","-J","-c","198.18.77.2","-p",str(port),"-C","bbr","-P","1","-R","-t","25"],stdout=out,stderr=err,timeout=90)
        end=time.monotonic_ns();h1=host();post=[stats(server),stats(client)]
        if profile:
            if profile.poll() is None:profile.send_signal(signal.SIGINT)
            profile.wait(15)
            with (d/"perf-report.txt").open("w") as log:
                report=subprocess.run([os.environ["DUAL_TCP_PERF_BIN"],"report","--stdio","--no-children","--sort","comm,dso,symbol","--percent-limit","0.3","-i",str(d/"perf.data")],stdout=log,stderr=subprocess.STDOUT)
            save(d/"profile-status.json",{"record_rc":profile.returncode,"report_rc":report.returncode,"scope":"DIAGNOSTIC_ONLY"})
        data=json.loads((d/"iperf.json").read_text());assert p.returncode==0 and not data.get("error"),data.get("error")
        received=data["end"]["sum_received"];sent=data["end"]["sum_sent"]
        assert received["bytes"]>0 and received["seconds"]>=24
        app.wait(15);assert app.returncode==0
        gib=received["bytes"]/2**30
        row={"status":"MEASURED","leg":k,"index":i,"source_sha":SOURCES[k],"build_manifest_sha256":MANIFESTS[k]["manifest_sha256"],"start_monotonic_ns":begin,"measurement_start_ns":t,"measurement_end_ns":end,"mbps":received["bits_per_second"]/1e6,"received_bytes":received["bytes"],"seconds":received["seconds"],"wall_seconds":(end-t)/1e9,"origin_sender_retransmits":sent.get("retransmits"),"server_cpu_s_per_gib":(post[0]-pre[0])/tick/gib,"client_cpu_s_per_gib":(post[1]-pre[1])/tick/gib,"host_cpu_s_per_gib":sum(h1[j]-h0[j] for j in (0,1,2,5,6))/tick/gib,"host_steal_ticks":h1[7]-h0[7]}
        snap(d/"after-netem.json")
        stop(client);stop(server)
        sl=(d/"server.log").read_text();cl=(d/"client.log").read_text()
        for log in (sl,cl):
            assert "V4_PUBLIC_SHARED_TUN_STOP" in log and "reader_joined=1" in log
        assert "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED" in sl
        assert server.returncode==0 and client.returncode==0
        if splice:
            assert "WBD_TCP_SPLICE_STOP error=<nil>" in sl
            assert f"target=198.18.77.2:{port} cc=bbr" in sl
            copies=[int(x) for x in re.findall(r"WBD_TCP_SPLICE_DONE .*?down=(\d+)",sl)]
            assert max(copies,default=0)>=received["bytes"]
            row["splice_down_bytes"]=copies
        else:
            assert "WBD_TCP_SPLICE_READY" not in sl
            assert all("WBD_DUAL_RUST_TCP_OWNER_STOP" in log for log in (sl,cl))
        assert "TPROXY" not in ns(S,"iptables","-t","mangle","-S")
        row.update(end_monotonic_ns=time.monotonic_ns(),server_exit=server.returncode,client_exit=client.returncode)
        save(d/"result.json",row);print(json.dumps(row),flush=True)
        return row
    finally:
        if profile and profile.poll() is None:
            profile.send_signal(signal.SIGINT);profile.wait(15)
        for p in (app,client,server):
            if p and p.poll() is None:stop(p)
        (d/"install").unlink(missing_ok=True)

MANIFESTS={k:manifest(k) for k in ROOTS}
try:
    save(O/"builds.json",MANIFESTS)
    save(O/"runner.json",{"run_id":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"harness_sha":os.environ["GITHUB_SHA"],"runner_name":os.environ["RUNNER_NAME"],"job":os.environ["GITHUB_JOB"],"boot_id":pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip(),"uname":run("uname","-a"),"lscpu":run("lscpu"),"iperf":run("iperf3","--version")})
    make();shape(False)
    (O/"route-key.hex").write_text(hashlib.sha256(("DUAL-TCP-PERF"+os.environ["GITHUB_RUN_ID"]).encode()).hexdigest()+"\n")
    (O/"users.json").write_text(json.dumps({"bench":"DUAL-TCP-PERF"}))
    for name in ("route-key.hex","users.json"):(O/name).chmod(0o600)
    run("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",str(O/"key.pem"),"-out",str(O/"cert.pem"),"-subj","/CN=wbd-h2228.example.test","-addext","subjectAltName=DNS:wbd-h2228.example.test")
    (O/"key.pem").chmod(0o600)
    rows=[]
    for i,k in enumerate(ORDER):
        rows.append(leg(i,k));save(O/"rows.json",rows)
    assert all(a["end_monotonic_ns"]<=b["start_monotonic_ns"] for a,b in zip(rows,rows[1:]))
    fields=("mbps","server_cpu_s_per_gib","client_cpu_s_per_gib","host_cpu_s_per_gib")
    means={k:{f:statistics.mean(r[f] for r in rows if r["leg"]==k) for f in fields} for k in ROOTS}
    save(O/"summary.json",{"status":"DIAGNOSTIC_ONLY" if COMPARE=="profile" else "MEASURED_NOT_PROMOTED","comparison":COMPARE,"scenario":"clean-1stream-download-25s","order":ORDER,"loss_pct":0,"added_rtt_ms":0,"outer_mtu":1460,"outer_repair":"on","seed":0,"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"rows":rows,"means":means,"builds":MANIFESTS})
finally:
    for name in ("route-key.hex","users.json","key.pem","cert.pem"):(O/name).unlink(missing_ok=True)
    for n in reversed(N):subprocess.run(["ip","netns","del",n],check=False)
