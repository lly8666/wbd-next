#!/usr/bin/env python3
"""H2421 native product in four local kernel netns; no tailnet or mocks.
Each invocation one scenario, one VM, sequential four legs. Functional is separate.
"""
import hashlib,json,os,pathlib,re,signal,subprocess,sys,time,statistics
O=pathlib.Path(os.environ.get("H2421_OUT","h2421-out")).resolve(); O.mkdir(exist_ok=True)
ROOT=pathlib.Path("linux-plan029-public-bundle").resolve()
C,R,S,T="h21client","h21router","h21server","h21origin"
N=(C,R,S,T)
ORDER=os.environ["H2421_ORDER"]; SCENE=os.environ["H2421_SCENE"]
CC={"clean":{"A":"","B":"bbr"},"loss1":{"A":"bbr","B":"cubic"},"loss5":{"A":"bbr","B":"cubic"},"congestion":{"A":"bbr","B":"cubic"},"functional":{"A":"bbr","B":"cubic"}}[SCENE]
LOSS={"clean":0,"loss1":1,"loss5":5,"congestion":0,"functional":0}[SCENE]
DELAY=0 if SCENE in ("clean","functional") else 200
RATE=100 if SCENE=="congestion" else 0
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
        if active and RATE:args+=["rate",str(RATE)+"mbit"]
        ns(R,*args)
def snap(p):
    save(p,{dev:json.loads(ns(R,"tc","-s","-j","qdisc","show","dev",dev)) for dev in ("rc0","rs0")})
def direct(label):
    shape(False)
    port=5199
    p=spawn(S,O/(label+"-origin.log"),"iperf3","-s","-1","-B","10.248.82.2","-p",port)
    try:
        until(p,lambda:f":{port} " in ns(S,"ss","-ltn"))
        raw=ns(C,"iperf3","-J","-c","10.248.82.2","-p",str(port),"-R","-P","8","-t","5","-O","2")
        (O/(label+".json")).write_text(raw)
        d=json.loads(raw);p.wait(10)
        return d["end"]["sum_received"]["bits_per_second"]/1e6
    finally:stop(p)
def appcheck(d,port):
    # Real finite bidirectional byte stream, orderly half-close, plus unchanged UDP NAT.
    app=pathlib.Path("tools/m0_h2421_splice_app.py").resolve()
    p=spawn(T,d/"app-origin.log",sys.executable,app,"origin",str(port))
    try:
        until(p,lambda:f":{port} " in ns(T,"ss","-ltn"))
        raw=ns(C,sys.executable,str(app),"client",str(port))
        (d/"app-client.json").write_text(raw)
        p.wait(30)
        assert p.returncode==0
        return json.loads(raw)
    finally:stop(p)
def leg(i,k):
    d=O/f"{i}-{k}";d.mkdir()
    cc=CC[k];port=5300+i;server=client=app=None
    shape(False)
    cmd=["env","LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-server",
      "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
      "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--server-name","wbd-h2228.example.test",
      "--route-key-hex-file",O/"route-key.hex","--users-file",O/"users.json","--lease-pool","10.66.0.128/25",
      "--tls-cert",O/"cert.pem","--tls-key",O/"key.pem","--outer-mtu","1460","--mode","shared","--outer-repair","on"]
    if cc:cmd+=["--tcp-proxy-cc",cc,"--tcp-proxy-port","46180"]
    try:
        server=spawn(S,d/"server.log",*cmd)
        until(server,lambda:"V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in (d/"server.log").read_text())
        if cc:assert f"WBD_TCP_SPLICE_READY tun=wbds0 port=46180 cc={cc}" in (d/"server.log").read_text()
        client=spawn(C,d/"client.log","env","LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-client",
          "--raw-interface","wan0","--local-ip","10.248.81.2","--local-port",44100+i*2,
          "--peer-ip","10.248.82.2","--peer-port","443","--tun-name","wbdc0",
          "--server-name","wbd-h2228.example.test","--route-key-hex-file",O/"route-key.hex",
          "--username","bench","--password","H2421-ONLY","--auto-ip","--installation-id-file",d/"install",
          "--mode","normal","--outer-repair","on","--outer-mtu","1460")
        until(client,lambda:"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" in (d/"client.log").read_text())
        ns(C,"ip","route","replace","198.18.77.2/32","dev","wbdc0")
        (d/"client-route.txt").write_text(ns(C,"ip","route","get","198.18.77.2"))
        (d/"server-tun-qdisc.txt").write_text(ns(S,"tc","-s","qdisc","show","dev","wbds0"))
        shape(True);time.sleep(1)
        snap(d/"before-netem.json")
        if SCENE=="functional":
            row=appcheck(d,port)
        else:
            app=spawn(T,d/"origin.log","iperf3","-s","-1","-B","198.18.77.2","-p",port)
            until(app,lambda:f":{port} " in ns(T,"ss","-ltn"))
            pre=[stats(server),stats(client)];h0=host();tick=os.sysconf("SC_CLK_TCK");t=time.monotonic()
            with (d/"iperf.json").open("w") as out,(d/"iperf.err").open("w") as err:
                p=subprocess.Popen(["ip","netns","exec",C,"iperf3","-J","-c","198.18.77.2","-p",str(port),"-C","bbr","-P","1","-R","-t","25","-O","8"],stdout=out,stderr=err)
            with (d/"socket-samples.txt").open("w") as samples:
                while p.poll() is None:
                    if time.monotonic()-t>100:p.kill();p.wait();break
                    samples.write(f"\nTIME {time.time()} SERVER_PID_TICKS {stats(server)} CLIENT_PID_TICKS {stats(client)}\n")
                    for n in (S,T,C):
                        samples.write(n+"\n"+ns(n,"ss","-tinm"))
                    samples.write(pathlib.Path("/proc/stat").read_text().splitlines()[0]+"\n"+pathlib.Path("/proc/pressure/cpu").read_text())
                    samples.flush();time.sleep(1)
            h1=host();post=[stats(server),stats(client)]
            raw=(d/"iperf.json").read_text()
            try:
                data=json.loads(raw); received=data["end"]["sum_received"];sent=data["end"]["sum_sent"]
                assert p.returncode==0 and not data.get("error") and received["bytes"]>0 and received["seconds"]>=20
                gib=received["bytes"]/2**30
                row={"status":"MEASURED","mbps":received["bits_per_second"]/1e6,"received_bytes":received["bytes"],"sender_retransmits":sent.get("retransmits"),"seconds":received["seconds"],"wall_seconds":time.monotonic()-t,"server_cpu_s_per_measured_gib":(post[0]-pre[0])/tick/gib,"client_cpu_s_per_measured_gib":(post[1]-pre[1])/tick/gib,"host_cpu_s_per_measured_gib":sum(h1[j]-h0[j] for j in (0,1,2,5,6))/tick/gib,"host_steal_ticks":h1[7]-h0[7]}
            except (ValueError,KeyError,AssertionError) as ex:
                row={"status":"TCP_INCOMPLETE","mbps":None,"rc":p.returncode,"error":str(ex),"raw_tail":raw[-500:]}
            stop(app)
        snap(d/"after-netem.json");shape(False)
        stop(client);stop(server)
        sl=(d/"server.log").read_text();cl=(d/"client.log").read_text()
        assert "V4_PUBLIC_SHARED_TUN_STOP" in sl and "reader_joined=1" in sl
        assert "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED" in sl
        (d/"after-stop-mangle.txt").write_text(ns(S,"iptables","-t","mangle","-S"))
        (d/"after-stop-routes.txt").write_text(ns(S,"ip","rule","show"))
        assert "TPROXY" not in (d/"after-stop-mangle.txt").read_text()
        assert "V4_PUBLIC_SHARED_TUN_STOP" in cl or "V4_PUBLIC_NATIVE_STOP_DRAINED" in cl
        copies=[int(x) for x in re.findall(r"WBD_TCP_SPLICE_DONE .*?down=(\d+)",sl)]
        if cc:
            assert "WBD_TCP_SPLICE_STOP error=<nil>" in sl
            if row["status"]=="MEASURED" or SCENE=="functional":
                assert f"target=198.18.77.2:{port} cc={cc}" in sl and max(copies,default=0)>=row["received_bytes"]
        else:assert not copies
        row.update(leg=k,index=i,cc=cc or "origin-bbr-nat",source_sha=os.environ["GITHUB_SHA"],run_id=os.environ["GITHUB_RUN_ID"],splice_down_bytes=copies,server_shared_tun_stop=[x for x in sl.splitlines() if "V4_PUBLIC_SHARED_TUN_STOP" in x],client_shared_tun_stop=[x for x in cl.splitlines() if "V4_PUBLIC_SHARED_TUN_STOP" in x],server_exit=server.returncode,client_exit=client.returncode)
        save(d/"result.json",row);print(json.dumps(row),flush=True)
        return row
    finally:
        shape(False)
        for p in (app,client,server):
            if p and p.poll() is None:stop(p)
try:
    make()
    # Fixture-only credential; not a user secret, omit from uploaded evidence.
    (O/"route-key.hex").write_text(hashlib.sha256(("H2421"+os.environ["GITHUB_RUN_ID"]).encode()).hexdigest()+"\n")
    (O/"users.json").write_text(json.dumps({"bench":"H2421-ONLY"}))
    for name in ("route-key.hex","users.json"):(O/name).chmod(0o600)
    run("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",str(O/"key.pem"),"-out",str(O/"cert.pem"),"-subj","/CN=wbd-h2228.example.test","-addext","subjectAltName=DNS:wbd-h2228.example.test")
    (O/"key.pem").chmod(0o600)
    baseline=None if SCENE=="functional" else direct("pre-direct")
    rows=[leg(i,k) for i,k in enumerate(ORDER)]
    after=None if SCENE=="functional" else direct("post-direct")
    summary={"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"scope":"one VM four native kernel netns, actual original WBD Go TLS Rust RAW/TUN, NOT independent three runners or physical WAN","scene":SCENE,"order":ORDER,"loss_pct":LOSS,"added_rtt_ms":DELAY*2,"router_rate_mbps":RATE,"outer_mtu":1460,"mode":"normal/off","outer_repair":"on","origin_cc":"bbr","pre_direct_mbps":baseline,"post_direct_mbps":after,"rows":rows,"manifest":json.loads((ROOT/"manifest.json").read_text())}
    if SCENE!="functional" and all(r["status"]=="MEASURED" for r in rows):
        a=[r["mbps"] for r in rows if r["leg"]=="A"];b=[r["mbps"] for r in rows if r["leg"]=="B"]
        summary.update(a_mean_mbps=statistics.mean(a),b_mean_mbps=statistics.mean(b),b_over_a_pct=100*(statistics.mean(b)/statistics.mean(a)-1),a_spread_pct=100*(max(a)-min(a))/statistics.mean(a),b_spread_pct=100*(max(b)-min(b))/statistics.mean(b))
    save(O/"summary.json",summary)
    assert all(r["status"]=="MEASURED" for r in rows)
finally:
    for name in ("route-key.hex","users.json","key.pem","cert.pem"):
        (O/name).unlink(missing_ok=True)
    for n in reversed(N):subprocess.run(["ip","netns","del",n],check=False)
