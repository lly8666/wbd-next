#!/usr/bin/env python3
"""H2430: actual application-paced native WBD capacity staircase; no mid-path rate cap."""
import hashlib,json,os,pathlib,re,signal,subprocess,sys,time,statistics
from m0_h2435_cpu import sample_cpu, summarize_cpu, cpu_environment
O=pathlib.Path(os.environ.get("H2421_OUT","h2421-out")).resolve(); O.mkdir(exist_ok=True)
ROOT=pathlib.Path("linux-plan029-public-bundle").resolve()
C,R,S,T="h21client","h21router","h21server","h21origin"
N=(C,R,S,T)
LOSS=float(os.environ["H2434_LOSS"])
PROFILE=int(os.environ["H2434_PROFILE"])
PAIR=os.environ["H2434_PAIR"]
SCENE=os.environ["H2439_SCENE"]
WEAK_CAP=int(os.environ["H2439_WEAK_CAP"])
FINITE=os.environ.get("H2437_FINITE","0")=="1"
ORIGIN_CC=os.environ.get("H2434_ORIGIN_CC","cubic")
INBOX=os.environ.get("H2434_INBOX","1024")
EXIT="nat"
DIRECTION="download"
ORDER=os.environ["H2432_ORDER"]
ARM="A"
PACED=os.environ.get("H2433_PACED","1")=="1"
RATE=int(os.environ["H2432_RATE"])
TOOL=pathlib.Path("tools/m0_h2437_tcp_source.py").resolve()
PRODUCT_SOURCE=os.environ["H2439_PRODUCT_SOURCE"]
SMOKE=os.environ.get("H2431_SMOKE","0")=="1"
RHO={-1:0,0:.125,1:.25,2:.375,3:.5,4:.75,5:1,6:1.25}[PROFILE]
RESERVE=.90
DELAY=int(os.environ["H2434_RTT"])//2
RATES=(RATE,)
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
        for key in ("net.ipv4.conf.all.rp_filter=0","net.ipv4.conf.default.rp_filter=0","net.ipv4.tcp_congestion_control="+ORIGIN_CC,"net.ipv4.tcp_rmem=4096 87380 67108864","net.ipv4.tcp_wmem=4096 65536 67108864","net.core.rmem_max=67108864","net.core.wmem_max=67108864"):
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
    ns(T,"tc","qdisc","replace","dev","app0","root","fq","flow_limit","256")
    save(O/"topology.json",{n:{"routes":ns(n,"ip","route"),"links":json.loads(ns(n,"ip","-j","link")),"cc":ns(n,"sysctl","-n","net.ipv4.tcp_congestion_control")} for n in N})
def shape(active,loss=None):
    for dev in ("rc0","rs0"):
        subprocess.run(["ip","netns","exec",R,"tc","qdisc","del","dev",dev,"root"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        args=["delay",str(DELAY if active else 0)+"ms"]
        limit=65536
        if active and SCENE=="jitter":
            args+=["20ms","25%","distribution","normal"]
        if active and SCENE=="burst":
            # Gilbert-Elliott: p(good->bad)=1%, r(bad->good)=20%,
            # all packets lost in bad state, none in good; stationary ~4.76%.
            args+=["loss","gemodel","1%","20%","100%","0%"]
        else:
            p=LOSS if active else 0
            if active and SCENE=="down-only" and dev=="rs0":p=0
            if active and SCENE=="ack-only" and dev=="rc0":p=0
            args+=["loss","random",str(p)+"%"]
        if active and SCENE=="shared":
            args+=["rate","100mbit"];limit=3000
        args+=["limit",str(limit)]
        ns(R,"tc","qdisc","add","dev",dev,"root","netem",*args)
        q=ns(R,"tc","-d","qdisc","show","dev",dev)
        assert "netem" in q and (("rate " in q)==(active and SCENE=="shared")),q

def snap(p,live=True):
    result={}
    for n in N:
        result[n]={"links":json.loads(ns(n,"ip","-s","-j","link")),"qdisc":json.loads(ns(n,"tc","-s","-j","qdisc","show")),"snmp":ns(n,"cat","/proc/net/snmp"),"netstat":ns(n,"cat","/proc/net/netstat")}
    result["host_softnet"]=pathlib.Path("/proc/net/softnet_stat").read_text()
    result["host_stat"]=pathlib.Path("/proc/stat").read_text()
    save(p,result)

def direct(label):
    shape(False)
    port=5199
    p=spawn(S,O/(label+"-origin.log"),"iperf3","-s","-1","-B","10.248.82.2","-p",port)
    try:
        until(p,lambda:f":{port} " in ns(S,"ss","-ltn"))
        cmd=["iperf3","-J","-c","10.248.82.2","-p",str(port),"-P","8","-t","5","-O","2"]
        if DIRECTION=="download":cmd+=["-R"]
        raw=ns(C,*cmd);(O/(label+".json")).write_text(raw)
        d=json.loads(raw);p.wait(10)
        return d["end"]["sum_received"]["bits_per_second"]/1e6
    finally:stop(p)

def counters(log):
    return [x for x in log.splitlines() if re.search(r"STOP|PROOF|RECEIPT|FEC2_TX|FEC2_RX|REPAIR|RAW_RX|NATIVE_INBOX|MTU",x)]

def drops(log):
    m=re.findall(r"V4_PUBLIC_SHARED_TUN_STOP generation=.*?queue_full_drops=(\d+).*?queue_byte_drops=(\d+).*?queue_age_drops=(\d+)",log)
    if not m:return None
    return sum(map(int,m[-1]))

def udp_metrics(end):
    # Modern iperf3 reports directional sum_sent and sum_received. Do not invent missing counts.
    tx=end.get("sum_sent");rx=end.get("sum_received")
    if not tx or not rx:raise KeyError("missing UDP directional sum_sent/sum_received")
    return tx,rx

def leg(i,proto,budget):
    rate=RATE
    d=O/f"{i:02}-{proto}-outer{budget}";d.mkdir()
    begin=time.monotonic_ns();port=5300+i
    server=client=app=p=competitor_server=competitor=latency=None
    profile=PROFILE
    mode="normal" if profile<0 else "fec-fixed"
    cc="bbr" if PAIR=="pacing" else {"A":"cubic","B":"bbr"}[ARM]
    pacing=WEAK_CAP*125000 if PAIR=="cubic-bbr" or ARM=="B" else None
    slots="1024"
    exit_kind="splice" if cc else "nat"
    shape(False)
    cmd=["env","LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-server",
      "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
      "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--server-name","wbd-h2228.example.test",
      "--route-key-hex-file",O/"route-key.hex","--users-file",O/"users.json","--lease-pool","10.66.0.128/25",
      "--tls-cert",O/"cert.pem","--tls-key",O/"key.pem","--outer-mtu","1460","--mode","shared","--outer-repair","on","--tun-fq-maxrate-mbps","0"]
    if cc:cmd+=["--tcp-proxy-cc",cc,"--tcp-proxy-port","46180"]
    try:
        server=spawn(S,d/"server.log","env","WBD_SHARED_TUN_ROUTE_DIAG=1",*(["WBD_M0_SPLICE_PACING_AB="+str(pacing)] if pacing else []),*cmd)
        until(server,lambda:"V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in (d/"server.log").read_text())
        client=spawn(C,d/"client.log","env","LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-client",
          "--raw-interface","wan0","--local-ip","10.248.81.2","--local-port",44100+i*2,
          "--peer-ip","10.248.82.2","--peer-port","443","--tun-name","wbdc0",
          "--server-name","wbd-h2228.example.test","--route-key-hex-file",O/"route-key.hex",
          "--username","bench","--password","H2430-ONLY","--auto-ip","--installation-id-file",d/"install",
          "--mode",mode,"--fec-profile",str(max(0,profile)),"--outer-repair","on","--outer-mtu","1460","--tun-fq-maxrate-mbps","0")
        until(client,lambda:"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" in (d/"client.log").read_text())
        until(server,lambda:re.search(r"M0_PLAN029_NATIVE_INBOX_BOUND role=server .*slots="+slots+r" ",(d/"server.log").read_text()) is not None)
        until(client,lambda:re.search(r"M0_PLAN029_NATIVE_INBOX_BOUND role=client .*slots=1024 ",(d/"client.log").read_text()) is not None)
        ns(C,"ip","route","replace","198.18.77.2/32","dev","wbdc0")
        (d/"client-route.txt").write_text(ns(C,"ip","route","get","198.18.77.2"))
        for n,dev in ((C,"wbdc0"),(S,"wbds0")):
            ns(n,"tc","qdisc","replace","dev",dev,"root","fq","flow_limit","256")
            q=ns(n,"tc","-d","qdisc","show","dev",dev)
            assert q.startswith("qdisc fq ") and "flow_limit 256" in q and "maxrate " not in q,q
            (d/(n+"-tun-config.txt")).write_text(q)
        # Only the sender paces traffic. No rate in intermediate netem or fq.
        shape(True);time.sleep(1)
        app=spawn(T,d/"origin.log",sys.executable,TOOL,"source","198.18.77.2",port,rate,ORIGIN_CC,str(int(FINITE)))
        until(app,lambda:f":{port} " in ns(T,"ss","-ltn"))
        (d/"netem-active.txt").write_text(ns(R,"tc","-s","-d","qdisc","show"))
        if SCENE=="shared":
            competitor_server=spawn(S,d/"competitor-server.log","iperf3","-s","-1","-B","10.248.82.2","-p",5600+i)
            until(competitor_server,lambda:f":{5600+i} " in ns(S,"ss","-ltn"))
        snap(d/"before.json")
        pre=[stats(server),stats(client)];h0=host();tick=os.sysconf("SC_CLK_TCK");t=time.monotonic()
        cmd=["ip","netns","exec",C,sys.executable,str(TOOL),"sink","198.18.77.2",str(port),str(rate),ORIGIN_CC,str(int(FINITE))]
        (d/"sender-command.json").write_text(json.dumps(cmd)+"\n")
        with (d/"iperf.json").open("w") as out,(d/"iperf.err").open("w") as err:
            p=subprocess.Popen(cmd,stdout=out,stderr=err)
        # The independent direct CUBIC flow crosses the SAME router egress.
        if SCENE=="shared":
            competitor=spawn(C,d/"competitor.json","iperf3","-J","-c","10.248.82.2","-p",5600+i,"-R","-P","1","-t","50","-i","1")
        latency=spawn(C,d/"wan-ping.txt","ping","-n","-i","0.2","-w","50","10.248.82.2")
        wire=[]
        cpu=[]
        with (d/"samples.txt").open("w") as samples:
            while p.poll() is None:
                if time.monotonic()-t>(240 if FINITE else 220):p.kill();p.wait();break
                record={"elapsed_s":time.monotonic()-t}
                cpu.append(sample_cpu({"server":server.pid,"client":client.pid,"origin":app.pid,"sink":p.pid},t))
                for n in (S,C):
                    iface=json.loads(ns(n,"ip","-s","-j","link","show","dev","wan0"))[0]
                    record[n]=iface.get("stats64",iface.get("stats"))
                wire.append(record)
                save(d/"wire-samples.json",wire)
                samples.write(f"\nTIME {time.time()} SERVER_TICKS {stats(server)} CLIENT_TICKS {stats(client)}\n")
                for n in (S,T,C):
                    samples.write(n+"\n"+ns(n,"ss","-tinm")+ns(n,"ss","-uinm")+ns(n,"cat","/proc/net/dev"))
                for owner in (server,client):
                    for task in pathlib.Path(f"/proc/{owner.pid}/task").glob("*/stat"):
                        try:
                            st=task.read_text();name=st.split("(",1)[1].rsplit(")",1)[0];v=st.rsplit(")",1)[1].split()
                            samples.write(f"THREAD {owner.pid} {task.parent.name} {name} {v[11]} {v[12]}\n")
                        except FileNotFoundError:pass
                samples.write(pathlib.Path("/proc/stat").read_text().splitlines()[0]+"\n"+pathlib.Path("/proc/pressure/cpu").read_text())
                samples.flush();time.sleep(2)
        save(d/"cpu-samples.json",cpu)
        if latency:
            stop(latency)
        if competitor:
            try:competitor.wait(15);competitor_server.wait(15)
            except subprocess.TimeoutExpired:stop(competitor);stop(competitor_server)
        post=[stats(server),stats(client)];h1=host()
        raw=(d/"iperf.json").read_text()
        try:
            app.wait(20)
            assert app.returncode==0
            tx=json.loads((d/"origin.log").read_text());rx=json.loads(raw)
            assert tx["congestion_control"]==ORIGIN_CC
            assert not rate or tx["socket_pacing_bytes_per_s"]==rate*125000
            assert p.returncode==0 and rx["seconds"]==30
            assert rx["bytes"]>=0
            if FINITE:
                assert tx["total_bytes"]==rx["total_bytes"]==4*2**30 and tx["sha256"]==rx["sha256"] and rx["end"]=="eof",(tx,rx)
            gib=rx["bytes"]/2**30 or 1e-12
            row={"status":"MEASURED","offered_mbps":rate,"tx_mbps":tx["bits_per_second"]/1e6,"rx_mbps":rx["bits_per_second"]/1e6,"tx_bytes":tx["bytes"],"rx_bytes":rx["bytes"],"tx_seconds":tx["seconds"],"rx_seconds":rx["seconds"],"udp_lost_packets":rx.get("lost_packets"),"udp_packets":rx.get("packets"),"udp_lost_percent":rx.get("lost_percent"),"origin_or_client_tcp_retransmits":tx.get("retransmits"),"source_total_bytes":tx["total_bytes"],"sink_total_bytes":rx["total_bytes"],"source_end":tx["end"],"sink_end":rx["end"],"source_cc_readback":tx["congestion_control"],"server_cpu_s_per_rx_gib":(post[0]-pre[0])/tick/gib,"client_cpu_s_per_rx_gib":(post[1]-pre[1])/tick/gib,"host_cpu_s_per_rx_gib":sum(h1[j]-h0[j] for j in (0,1,2,5,6))/tick/gib,"host_steal_ticks":h1[7]-h0[7]}
        except (ValueError,KeyError,AssertionError,TypeError) as ex:
            row={"status":"INCOMPLETE","offered_mbps":rate,"tx_mbps":None,"rx_mbps":None,"rc":p.returncode,"error":str(ex),"raw_tail":raw[-500:]}
        time.sleep(1)
        snap(d/"after.json")
        stop(app);stop(client);stop(server)
        sl=(d/"server.log").read_text();cl=(d/"client.log").read_text()
        assert "M0_SHARED_TUN_LEASE_QUEUE_DIAG" in sl
        assert "V4_PUBLIC_SHARED_TUN_STOP" in sl and "reader_joined=1" in sl and "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED" in sl
        assert "V4_PUBLIC_NATIVE_STOP_DRAINED" in cl
        assert "panicked at" not in sl+cl
        if pacing:assert "bytes_per_s="+str(pacing) in sl
        expected="mode=off" if profile<0 else f"mode=fixed profile={profile} "
        assert "V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY "+expected in sl,sl[-3000:]
        if cc:
            assert "WBD_TCP_SPLICE_STOP error=<nil>" in sl
            assert re.search(r"WBD_TCP_SPLICE_ACCEPT[^\n]*cc="+cc+r"(?:\s|$)",sl) or re.search(r"WBD_TCP_SPLICE[^\n]*target=[^\n]*cc="+cc+r"(?:\s|$)",sl),sl[-4000:]
        row["cpu_pressure"]=summarize_cpu(cpu)
        ping=(d/"wan-ping.txt").read_text()
        rtts=[float(x) for x in re.findall(r"time=([0-9.]+) ms",ping)]
        row["wan_ping"]={"received":len(rtts),"p50_ms":statistics.median(rtts) if rtts else None,"p95_ms":sorted(rtts)[max(0,int(.95*len(rtts))-1)] if rtts else None}
        if competitor:
            try:
                comp=json.loads((d/"competitor.json").read_text());assert competitor.returncode==0 and not comp.get("error")
                # Aligned approximately to WBD window, record actual iperf intervals.
                intervals=[x["sum"] for x in comp["intervals"] if x["sum"]["start"]>=15 and x["sum"]["end"]<=45.5]
                assert len(intervals)>=25
                row["competitor_steady_mbps"]=sum(x["bytes"] for x in intervals)*8/sum(x["seconds"] for x in intervals)/1e6
                row["competitor_window_seconds"]=sum(x["seconds"] for x in intervals)
                row["competitor_status"]="MEASURED"
            except (KeyError,ValueError,AssertionError,TypeError) as ex:
                row["competitor_status"]="INCOMPLETE";row["competitor_error"]=repr(ex)
        row["drain_verified"]=row.get("sink_end")=="eof" and row.get("source_total_bytes")==row.get("sink_total_bytes")
        if FINITE and row["status"]=="MEASURED":row["sha256"]=rx["sha256"]
        window=[x for x in wire if 15<=x["elapsed_s"]<=45]
        if len(window)>=2:
            dt=window[-1]["elapsed_s"]-window[0]["elapsed_s"]
            row["wire_sample_seconds"]=dt
            row["wan_tx_mbps_l2_counter"]={n:(window[-1][n]["tx"]["bytes"]-window[0][n]["tx"]["bytes"])*8/dt/1e6 for n in (S,C)}
            row["wan_tx_pps"]={n:(window[-1][n]["tx"]["packets"]-window[0][n]["tx"]["packets"])/dt for n in (S,C)}
        row.update(arm=ARM,scene=SCENE,proxy_pacing_bytes_per_s=pacing,finite=FINITE,client_inbox_slots=1024,server_inbox_slots=int(slots),source_pacing_bytes_per_s=rate*125000 if rate else None,outer_budget_mbps=600,proxy_cc=cc or None,origin_cc=ORIGIN_CC,added_rtt_ms=DELAY*2,nominal_fec_overhead=RHO,offered_reserve=RESERVE,harness_sha=os.environ["GITHUB_SHA"],protocol=proto,direction=DIRECTION,exit=exit_kind,fec_profile=profile,loss_pct=LOSS,server_tun_drops=drops(sl),client_tun_drops=drops(cl),server_exit=server.returncode,client_exit=client.returncode,source_sha=PRODUCT_SOURCE,start_monotonic_ns=begin,end_monotonic_ns=time.monotonic_ns())
        save(d/"native-receipts.json",{"server":counters(sl),"client":counters(cl)})
        save(d/"result.json",row);print(json.dumps(row),flush=True)
        return row
    finally:
        for process in (latency,competitor,competitor_server,p,app,client,server):
            if process and process.poll() is None:stop(process)
        shape(False)
        (d/"install").unlink(missing_ok=True)

def direct_rtt(i):
    d=O/f"{i:02}-direct-{RATE}";d.mkdir()
    port=5500+i
    shape(True)
    ns(S,"tc","qdisc","replace","dev","wan0","root","fq","flow_limit","256")
    source=spawn(S,d/"origin.log",sys.executable,TOOL,"source","10.248.82.2",port,RATE,ORIGIN_CC)
    p=None
    try:
        until(source,lambda:f":{port} " in ns(S,"ss","-ltn"))
        snap(d/"before.json")
        p=spawn(C,d/"sink.json",sys.executable,TOOL,"sink","10.248.82.2",port,RATE,ORIGIN_CC)
        with (d/"samples.txt").open("w") as f:
            while p.poll() is None:
                f.write(str(time.monotonic())+"\n"+ns(S,"ss","-tinm")+ns(C,"ss","-tinm"));f.flush();time.sleep(2)
        source.wait(10)
        tx=json.loads((d/"origin.log").read_text());rx=json.loads((d/"sink.json").read_text())
        assert p.returncode==0 and source.returncode==0 and tx["congestion_control"]==ORIGIN_CC and (not RATE or tx["socket_pacing_bytes_per_s"]==RATE*125000)
        snap(d/"after.json")
        row={"status":"MEASURED","protocol":"tcp","arm":"A","source_pacing_bytes_per_s":tx["socket_pacing_bytes_per_s"],"tx_mbps":tx["bits_per_second"]/1e6,"rx_mbps":rx["bits_per_second"]/1e6,"tx_bytes":tx["bytes"],"rx_bytes":rx["bytes"],"rx_seconds":rx["seconds"]}
        save(d/"result.json",row);print(json.dumps(row),flush=True)
        return row
    finally:
        stop(p);stop(source);shape(False)
        subprocess.run(["ip","netns","exec",S,"tc","qdisc","del","dev","wan0","root"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

try:
    save(O/"cpu-environment.json",cpu_environment())
    make()
    save(O/"cc-inventory.json",{"uname":run("uname","-a"),"registered":ns(S,"sysctl","-n","net.ipv4.tcp_available_congestion_control"),"origin_default":ns(T,"sysctl","-n","net.ipv4.tcp_congestion_control"),"bbr_module":subprocess.run(["modinfo","tcp_bbr"],capture_output=True,text=True).stdout})
    (O/"route-key.hex").write_text(hashlib.sha256(("H2430"+os.environ["GITHUB_RUN_ID"]).encode()).hexdigest()+"\n")
    (O/"users.json").write_text(json.dumps({"bench":"H2430-ONLY"}))
    for name in ("route-key.hex","users.json"):(O/name).chmod(0o600)
    run("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",str(O/"key.pem"),"-out",str(O/"cert.pem"),"-subj","/CN=wbd-h2228.example.test","-addext","subjectAltName=DNS:wbd-h2228.example.test")
    (O/"key.pem").chmod(0o600)
    pre=direct("pre-direct")
    rows=[]
    if pre>=2000:
        direct_before=direct_rtt(90) if PAIR=="capacity" else None
        for i,arm in enumerate(ORDER):
            ARM=arm
            rows.append(leg(i,"tcp",RATE))
            save(O/"partial.json",rows)
        if PAIR=="capacity":
            direct_after=direct_rtt(91)
            save(O/"direct-rtt-controls.json",[direct_before,direct_after])
    after=direct("post-direct")
    summary={"source_sha":PRODUCT_SOURCE,"harness_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"arch":os.uname().machine,"loss_pct":LOSS,"fec_profile":PROFILE,"exit":EXIT,"direction":DIRECTION,"added_rtt_ms":DELAY*2,"delay_each_direction_ms":DELAY,"outer_budget_steps_mbps":RATES,"nominal_fec_overhead":RHO,"payload_budget_reserve":RESERVE,"outer_mtu":1460,"netem_rate":None,"tun_fq_maxrate":None,"udp_payload_bytes":1200,"sender_pacing_timer_us":200,"measurement_seconds":30,"warmup_seconds":15,"pre_direct_mbps":pre,"post_direct_mbps":after,"order":ORDER,"source_rate_mbps":RATE,"pair":PAIR,"scene":SCENE,"weak_cap_mbps":WEAK_CAP,"origin_cc":ORIGIN_CC,"scope":"same VM WBD actual single TCP architecture A/B, retained Normal server 1024, no physical or three-runner qualification","rows":rows,"status":"MEASURED" if rows and min(pre,after)>=2000 else "INFRA_CAPACITY_UNQUALIFIED","manifest":json.loads((ROOT/"manifest.json").read_text())}
    save(O/"summary.json",summary)
    assert min(pre,after)>=2000,(pre,after)
    assert rows and all(x["status"]=="MEASURED" for x in rows),[(x.get("protocol"),x["status"],x.get("error")) for x in rows]
    if SCENE=="shared":assert all(x.get("competitor_status")=="MEASURED" for x in rows),[(x["arm"],x.get("competitor_status"),x.get("competitor_error")) for x in rows]
finally:
    for name in ("route-key.hex","users.json","key.pem","cert.pem"):(O/name).unlink(missing_ok=True)
    for n in reversed(N):subprocess.run(["ip","netns","del",n],check=False)
