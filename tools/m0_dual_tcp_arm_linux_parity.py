#!/usr/bin/env python3
"""One ARM client / ARM routed impairment VM / ARM server, sequential A B B A.
Reuse H2228 real two L2 networks and the existing H2442 preset HTTP control.
"""
import hashlib,http.client,http.server,json,os,pathlib,signal,subprocess,sys,time,statistics
import m0_h2228_three_runner_relay as h
import m0_h2442_server as fixture

ROOT=pathlib.Path.cwd()
OUT=ROOT/"h2228-out";OUT.mkdir(exist_ok=True)
N=h.NODE;ORIGIN=fixture.ORIGIN
SOURCES={k:os.environ["GITHUB_SHA"] for k in "AB"}
BLOCKS=(("bbr",0.0),)
ORDER="ABBA"*len(BLOCKS)
def loss_for(i):return BLOCKS[i//4][1] if i>=0 else 0.0
def cc_for(i):return BLOCKS[i//4][0] if i>=0 else "cubic"
def rust_cc(i):return "bbr1" if cc_for(i)=="bbr" else "cubic"
def ack_for(k):return "2"
def profile(i,k):return "cap64"
def compress(k):return "1"
def set_cc(ns,i):
    cc=cc_for(i)
    h.ns(ns,"sysctl","-qw","net.ipv4.tcp_congestion_control="+cc)
    assert h.ns(ns,"sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip()==cc
DURATION=45
TARGET="192.0.2.2"
PORT=5400
PEERS=ROOT/"h2228-peer"
PROCS={}
CURRENT=None
FOLDER=None
TICK=os.sysconf("SC_CLK_TCK")
def load(p):return json.loads(p.read_text())
def save(p,d):h.save(p,d)
def peer(role):return load(PEERS/(role+".json"))
def bundle(k):return ROOT/"bundles"/"B"
def manifests():
    rows={}
    for k,source in SOURCES.items():
        b=bundle(k);m=load(b/"manifest.json")
        assert m["source_sha"]==source and m["architecture"]=="aarch64" and m["rust"]=="1.85.1"
        for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
            assert hashlib.sha256((b/name).read_bytes()).hexdigest()==m["sha256"][name]
        rows[k]={"manifest":m,"manifest_sha256":hashlib.sha256((b/"manifest.json").read_bytes()).hexdigest()}
    save(OUT/"builds.json",rows)
    return rows
def spawn(key,ns,log,*args):
    with log.open("w") as f:
        p=subprocess.Popen(["ip","netns","exec",ns,*map(str,args)],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    PROCS[key]=p
    return p
def stop(key):
    p=PROCS.pop(key,None)
    if p is None:return None
    if p.poll() is None:
        p.send_signal(signal.SIGTERM)
        try:p.wait(20)
        except subprocess.TimeoutExpired:p.kill();p.wait(5)
    return p.returncode
def waitmark(p,log,mark,timeout=65):
    until=time.monotonic()+timeout
    while mark not in log.read_text(errors="replace"):
        if p.poll() is not None or time.monotonic()>until:
            raise RuntimeError("not ready "+mark+" "+log.read_text(errors="replace")[-1500:])
        time.sleep(.2)
def proc_stats(pid):
    a=pathlib.Path("/proc",str(pid),"stat").read_text().rsplit(")",1)[1].split()
    b=pathlib.Path("/proc",str(pid),"status").read_text().splitlines()
    return {"user_ticks":int(a[11]),"system_ticks":int(a[12]),"rss_kib":int(next(x for x in b if x.startswith("VmRSS:")).split()[1]),"hwm_kib":int(next(x for x in b if x.startswith("VmHWM:")).split()[1])}
def direct(role):
    required=("client","server") if role=="relay" else ("relay",)
    targets={r:peer(r)["tail_ip"] for r in required}
    ts=json.loads(h.cmd("tailscale","status","--json").stdout)
    rows={}
    for r,ip in targets.items():
        p=next((x for x in (ts.get("Peer") or {}).values() if ip in x.get("TailscaleIPs",[])),{})
        rows[r]={k:p.get(k) for k in ("CurAddr","Relay","PeerRelay","Active","RxBytes","TxBytes")}
        rows[r]["direct"]=bool(p.get("CurAddr") and not p.get("PeerRelay"))
    return rows
def watch(role):
    with (OUT/(role+"-direct.jsonl")).open("w",buffering=1) as f:
        while True:
            try:d=direct(role)
            except Exception as e:d={"error":repr(e)}
            f.write(json.dumps({"wall_ns":time.time_ns(),"peers":d})+"\n")
            time.sleep(1)
def snapshot(role):
    t=pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:9]
    tails=h.cmd("pidof","tailscaled",allow_fail=True).stdout.strip().split()
    p=PROCS.get(role)
    return {"wall_ns":time.time_ns(),"tick_hz":TICK,"host_ticks":list(map(int,t)),
            "product":proc_stats(p.pid) if p and p.poll() is None else None,
            "tailscaled":proc_stats(int(tails[0])) if tails else None,
            "paths":direct(role),
            "wan":json.loads(h.ns(N,"ip","-s","-j","link","show","dev","wan0").stdout),
            "ss":h.ns(N,"ss","-tinm").stdout,
            "tcp_cc":h.ns(N,"sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip(),
            "linux_segments":fixture.linux_snapshot(N),
            "kernel_release":os.uname().release,
            "kernel_version":os.uname().version,
            "kernel_package":h.cmd("dpkg-query","-W","-f=${Package} ${Version} ${source:Package} ${source:Version}\\n","linux-image-"+os.uname().release,allow_fail=True).stdout,
            "kernel_config_sha256":h.cmd("sha256sum","/boot/config-"+os.uname().release,allow_fail=True).stdout,
            "tcp_sysctl":[x for x in h.ns(N,"sysctl","-a",allow_fail=True).stdout.splitlines() if x.startswith(("net.ipv4.tcp_","net.core.rmem_","net.core.wmem_","net.core.default_qdisc"))],
            "bbr_module":h.cmd("modinfo","tcp_bbr",allow_fail=True).stdout,
            "qdisc":h.ns(N,"tc","-s","-j","qdisc","show").stdout,
            "offload":h.ns(N,"ethtool","-k","wan0").stdout}
def common():
    return ["--server-name","wbd-h2228.example.test","--route-key-hex-file",fixture.TMP/"route-key.hex",
            "--mode","normal","--outer-repair","on","--outer-mtu","1160"]
def server_start(i):
    global CURRENT,FOLDER
    assert CURRENT is None and -2<=i<len(ORDER)
    CURRENT=fixture.current=i
    FOLDER=OUT/("case-"+str(i));FOLDER.mkdir()
    set_cc(N,i);set_cc(ORIGIN,i)
    if i<0:
        source=spawn("origin",N,FOLDER/"origin.log","iperf3","-s","-1","-J","-B","10.248.82.2","-p","5202")
        where=N;port=5202
    else:
        k=ORDER[i];b=bundle(k)
        flags=["--dual-rust-tcp"]
        p=spawn("server",N,FOLDER/"server.log","env","WBD_M0_NATIVE_INGRESS_FIRST=1","WBD_M0_NATIVE_IPV4_HEADROOM="+("1" if k=="B" else "0"),"WBD_M0_LINUX_PARITY=1","WBD_M0_NATIVE_M4_CLOCK=1","WBD_M0_MIDDLE_CC="+rust_cc(i),"WBD_M0_SACK_COMPRESS="+compress(k),"WBD_M0_TCP_EXPERIMENT="+profile(i,k),"WBD_M0_ACK_PROBE="+ack_for(k),"LD_LIBRARY_PATH="+str(b),b/"wbd-v4-server",
                "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
                "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--users-file",fixture.TMP/"users.json",
                "--lease-pool","10.66.0.128/25","--tls-cert",OUT/"cert.pem","--tls-key",fixture.TMP/"key.pem",
                *common(),*flags)
        waitmark(p,FOLDER/"server.log","V4_PUBLIC_MULTI_SERVER_READY role=server port=443")
 
        source=spawn("origin",ORIGIN,FOLDER/"origin.log","iperf3","-s","-1","-J","-B",TARGET,"-p",str(PORT))
        where=ORIGIN;port=PORT
    until=time.monotonic()+15
    while f":{port} " not in h.ns(where,"ss","-ltn").stdout:
        if source.poll() is not None or time.monotonic()>until:raise RuntimeError("origin listener failed")
        time.sleep(.2)
    return {"case":i,"ready":True}
def server_sample():
    d=snapshot("server")
    if CURRENT is not None and CURRENT>=0:
        d["origin_ss"]=h.ns(ORIGIN,"ss","-tinm").stdout
        d["origin_segments"]=fixture.linux_snapshot(ORIGIN)
    return d
def server_close():
    global CURRENT
    assert CURRENT is not None
    i=CURRENT;d=FOLDER
    sample=server_sample();save(d/"after.json",sample)
    p=PROCS.get("origin")
    if p and p.poll() is None:
        try:p.wait(20)
        except subprocess.TimeoutExpired:pass
    rc={key:stop(key) for key in list(PROCS)}
    result={"case":i,"rc":rc,"final_sample":sample}
    try:result["iperf"]=load(d/"origin.log")
    except Exception as e:result["iperf_error"]=repr(e)
    if i>=0:
        log=(d/"server.log").read_text(errors="replace")
        result["joined_stop"]=rc.get("server")==0 and "V4_PUBLIC_SHARED_TUN_STOP" in log and "reader_joined=1" in log and "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED" in log and "WBD_DUAL_RUST_TCP_OWNER_STOP" in log
        result["wire"]=[s for s in log.splitlines() if "WBD_DUAL_TCP_WIRE role=" in s]
        result["probe"]=probe_receipt(log,"server-middle",ORDER[i],i)
        result["experiment"]=profile(i,ORDER[i])
        result["native_counters"]=[s for s in log.splitlines() if "V4_PUBLIC_RX_CHAIN role=" in s or "V4_PUBLIC_TX_CHAIN role=" in s or "V4_PUBLIC_SHARED_TUN_STOP" in s or "WBD_M0_TCP_INGRESS" in s or "WBD_M0_TCP_PUBLISH" in s or "WBD_M0_TCP_M4_CLOCK" in s]
    save(d/"result.json",result);CURRENT=fixture.current=None
    return result
def server():
    manifests()
    fixture.setup()
    h.bbr(ORIGIN)
    for ns,dev in ((ORIGIN,"h2442app"),(N,"h2442exit")):
        h.ns(ns,"ethtool","-K",dev,"gro","off","gso","off","tso","off")
    fixture.peer=peer("client");fixture.relay=peer("relay");fixture.current=None
    fixture.start=server_start;fixture.close=server_close;fixture.sample=server_sample
    try:
        with http.server.ThreadingHTTPServer((h.tailscale_ip(),18727),fixture.Handler) as s:
            save(OUT/"server-ready.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"real_wbd_server_ready":True})
            print("ARM_DUAL_SERVER_READY",flush=True)
            s.serve_forever()
    finally:
        for key in list(PROCS):stop(key)
        h.root("ip","netns","del",ORIGIN,allow_fail=True)
def control(path,body=None):
    c=http.client.HTTPConnection(peer("server")["tail_ip"],18727,timeout=95)
    try:
        c.request("POST",path,json.dumps(body or {}),{"X-H2228-Token":peer("relay")["control_token"],"Content-Type":"application/json"})
        r=c.getresponse();raw=r.read()
        if r.status!=200:raise RuntimeError((r.status,raw[:500]))
        return json.loads(raw)
    finally:c.close()
def relay(action,loss=0,delay=0):return h.remote(peer("relay"),action,loss,delay,"iid")
def shape(loss,delay):return relay("impair",loss,delay)
def delta(a,b,gib):
    result={}
    for k in ("product","tailscaled"):
        if a.get(k) and b.get(k):
            result[k]={"user_cpu_s":(b[k]["user_ticks"]-a[k]["user_ticks"])/TICK,
                       "system_cpu_s":(b[k]["system_ticks"]-a[k]["system_ticks"])/TICK,
                       "rss_kib":b[k]["rss_kib"],"hwm_kib":b[k]["hwm_kib"]}
            if gib:result[k]["cpu_s_per_gib"]=(result[k]["user_cpu_s"]+result[k]["system_cpu_s"])/gib
    ticks=sum(b["host_ticks"][i]-a["host_ticks"][i] for i in (0,1,2,5,6))
    result["host_cpu_s"]=ticks/TICK
    if gib:result["host_cpu_s_per_gib"]=ticks/TICK/gib
    return result
def probe_receipt(log,leg,k,i):
    # Both legs run the same native binary; the only intervention is
    # server ingress-first ordering. Verify actual Stop receipt and GSO.
    expected_first="true" if leg=="server-middle" else "false"
    pub=next((s for s in log.splitlines() if "WBD_M0_TCP_PUBLISH " in s),"")
    mode_ok=(" ingress_first="+expected_first+" ") in pub and (("WBD_M0_TCP_IPV4_HEADROOM enabled=1" in log)==(k=="B"))
    gso_ok=True
    if leg=="client-middle":
        receipt=next((s for s in log.splitlines() if "WBD_M0_LOCAL_TUN_GSO groups=" in s),"")
        vals=dict(w.split("=",1) for w in receipt.split() if "=" in w)
        gso_ok=int(vals.get("groups",0))>0
    rows=[s for s in log.splitlines() if "WBD_M0_TCP_INFO " in s and "leg="+leg+" " in s]
    expected='congestion: "'+rust_cc(i)+'"'
    return {"samples":len(rows),"matching":sum(expected in s and "sack_compress=true" in s and "linux_parity=true" in s and "ack3=false" in s and "nodelay=false" in s and "send_max=67108864 recv_max=67108864" in s for s in rows),
            "ingress_first_expected":expected_first,"mode_ok":mode_ok,"gso_ok":gso_ok,
            "valid":mode_ok and gso_ok and len(rows)>=10 and all(expected in s and "sack_compress=true" in s and "linux_parity=true" in s and "ack3=false" in s and "nodelay=false" in s and "send_max=67108864 recv_max=67108864" in s for s in rows)}
def client_case(i):
    k=ORDER[i] if i>=0 else "bare"
    d=OUT/("case-"+str(i));d.mkdir()
    started=False;pre=post=before=after=None
    row={"case":i,"leg":k,"source_sha":SOURCES.get(k),"loss_pct":loss_for(i),"ack_ratio":int(ack_for(k)) if i>=0 else None,"kernel_cc":cc_for(i),"rust_middle_cc":rust_cc(i) if i>=0 else None,"server_ingress_first":True,"native_ipv4_headroom":k=="B","experiment":profile(i,k) if i>=0 else "bare","sack_compress":compress(k) if i>=0 else None,"added_rtt_ms":400 if i>=0 else 0,"status":"INCOMPLETE"}
    try:
        shape(0,0)
        set_cc(N,i)
        control("/start",{"case":i});started=True
        if i>=0:
            b=bundle(k);flags=["--dual-rust-tcp"]
            p=spawn("client",N,d/"client.log","env","WBD_M0_LOCAL_TUN_GSO=1","WBD_M0_NATIVE_INGRESS_FIRST=0","WBD_M0_NATIVE_IPV4_HEADROOM="+("1" if k=="B" else "0"),"WBD_M0_LINUX_PARITY=1","WBD_M0_NATIVE_M4_CLOCK=1","WBD_M0_MIDDLE_CC="+rust_cc(i),"WBD_M0_SACK_COMPRESS="+compress(k),"WBD_M0_TCP_EXPERIMENT="+profile(i,k),"WBD_M0_ACK_PROBE="+ack_for(k),"LD_LIBRARY_PATH="+str(b),b/"wbd-v4-client",
                    "--raw-interface","wan0","--local-ip","10.248.81.2","--local-port",str(44100+2*i),
                    "--peer-ip","10.248.82.2","--peer-port","443","--tun-name","wbdc0",
                    "--username","bench","--password","H2442-ONLY","--auto-ip","--installation-id-file",fixture.TMP/("install-"+str(i)),
                    *common(),*flags)
            waitmark(p,d/"client.log","V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client")
            h.ns(N,"ip","route","replace",TARGET+"/32","dev","wbdc0")
            route=h.ns(N,"ip","route","get",TARGET).stdout
            assert "dev wbdc0" in route
            (d/"route.txt").write_text(route)
            save(d/"shape.json",shape(loss_for(i),200));time.sleep(.6)
        else:save(d/"shape.json",shape(0,0))
        save(d/"relay-before.json",relay("snapshot"))
        before=control("/sample");save(d/"server-before.json",before)
        pre=snapshot("client");save(d/"client-before.json",pre)
        row["start_wall_ns"]=time.time_ns()
        cmd=["ip","netns","exec",N,"iperf3","-J","-c",TARGET if i>=0 else "10.248.82.2","-p",str(PORT if i>=0 else 5202),"-P","1","-R","-C",cc_for(i),"-t",str(DURATION if i>=0 else 12)]
        with (d/"iperf.json").open("w") as f,(d/"iperf.err").open("w") as err:
            p=subprocess.Popen(cmd,stdout=f,stderr=err)
            t=time.monotonic()
            try:
                for at in ((4,12,24,36) if i>=0 else ()):
                    try:
                        p.wait(timeout=max(0.01,t+at-time.monotonic()))
                        break
                    except subprocess.TimeoutExpired:pass
                    sample={"wall_ns":time.time_ns()}
                    for name,read in (("client",lambda:snapshot("client")),("server",lambda:control("/sample")),("relay",lambda:relay("snapshot"))):
                        try:sample[name]=read()
                        except Exception as e:sample[name+"_error"]=repr(e)
                    save(d/("live-"+str(at)+".json"),sample)
                p.wait(timeout=max(1,155-(time.monotonic()-t)))
            finally:
                if p.poll() is None:p.kill();p.wait()
        row["end_wall_ns"]=time.time_ns()
        post=snapshot("client");save(d/"client-after.json",post)
        after=control("/sample");save(d/"server-after.json",after)
        save(d/"relay-after.json",relay("snapshot"))
        app=load(d/"iperf.json");row["iperf_rc"]=p.returncode
        if p.returncode or app.get("error"):raise RuntimeError(str(app.get("error",p.returncode)))
        a=app["end"];r=a["sum_received"];s=a["sum_sent"];gib=r["bytes"]/2**30
        row["endpoint_path_samples"]=[x["paths"] for x in (pre,post,before,after)]
        row["endpoint_direct_snapshots"]=all(all(y["direct"] for y in x.values()) for x in row["endpoint_path_samples"])
        row.update(status="MEASURED",mbps=r["bits_per_second"]/1e6,bytes=r["bytes"],seconds=r["seconds"],sender_bytes=s["bytes"],sender_retrans=s.get("retransmits"),
                   client=delta(pre,post,gib),server=delta(before,after,gib),
                   sender_cc=a.get("sender_tcp_congestion"),receiver_cc=a.get("receiver_tcp_congestion"))
    except Exception as e:row["error"]=repr(e)
    finally:
        try:shape(0,0)
        except Exception as e:row["shape_clear_error"]=repr(e)
        rc=stop("client")
        if i>=0 and (d/"client.log").exists():
            log=(d/"client.log").read_text(errors="replace")
            row["client_stop"]=rc==0 and "V4_PUBLIC_SHARED_TUN_STOP" in log and "reader_joined=1" in log and log.count("V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client")==1 and "WBD_DUAL_RUST_TCP_OWNER_STOP" in log
            row["wire"]=[s for s in log.splitlines() if "WBD_DUAL_TCP_WIRE role=" in s]
            row["probe"]=probe_receipt(log,"client-middle",k,i)
            row["native_counters"]=[s for s in log.splitlines() if "WBD_M0_TCP_INGRESS" in s or "WBD_M0_TCP_PUBLISH" in s or "WBD_M0_TCP_M4_CLOCK" in s or "WBD_M0_LOCAL_TUN_GSO" in s or "V4_PUBLIC_SHARED_TUN_STOP" in s]
        if started:
            try:row["server_receipt"]=control("/stop")
            except Exception as e:row["server_stop_error"]=repr(e)
        if row["status"]=="MEASURED" and i>=0 and (not row.get("client_stop") or not row.get("server_receipt",{}).get("joined_stop")):row["status"]="INCOMPLETE_STOP"
        if row["status"]=="MEASURED" and i>=0 and not (row.get("probe",{}).get("valid") and row.get("server_receipt",{}).get("probe",{}).get("valid")):row["status"]="INCOMPLETE_PROBE"
        save(d/"result.json",row)
        print("ARM_DUAL_RESULT "+json.dumps({k:v for k,v in row.items() if k not in ("server_receipt","wire")}),flush=True)
    return row
def client():
    manifests()
    fixture.TMP.mkdir(exist_ok=True)
    (fixture.TMP/"route-key.hex").write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n")
    (fixture.TMP/"route-key.hex").chmod(0o600)
    rows=[]
    try:
        rows.append(client_case(-1));save(OUT/"rows.json",rows)
        if rows[0]["status"]=="MEASURED" and rows[0].get("endpoint_direct_snapshots"):
            for i in range(len(ORDER)):
                rows.append(client_case(i));save(OUT/"rows.json",rows)
            rows.append(client_case(-2));save(OUT/"rows.json",rows)
        means={}
        for cc,loss in BLOCKS:
            for k in "AB":
                v=[x for x in rows if x["leg"]==k and x["kernel_cc"]==cc and x["loss_pct"]==loss and x["status"]=="MEASURED"]
                if len(v)==2:means[cc+"-"+str(loss)+"-"+k]={"mbps":statistics.mean(x["mbps"] for x in v),"client_product_cpu_s_per_gib":statistics.mean(x["client"]["product"]["cpu_s_per_gib"] for x in v),"server_product_cpu_s_per_gib":statistics.mean(x["server"]["product"]["cpu_s_per_gib"] for x in v)}
        summary={"source_sha":os.environ["GITHUB_SHA"],"product_sources":SOURCES,"intervention":"native IPv4 headroom only on both endpoints; same binary, client GSO and server ingress-first","run_id":os.environ["GITHUB_RUN_ID"],"real_three_runner_l3_relay":True,"all_three_distinct_native_machines":True,"architecture":"aarch64","blocks":BLOCKS,"added_rtt_ms":400,"streams":1,"order":ORDER,"status":"MEASURED_REQUIRES_PATH_AND_CAPACITY_REVIEW" if len(means)==2*len(BLOCKS) else "PATH_NOT_QUALIFIED" if len(rows)==1 else "INCOMPLETE","rows":rows,"means":means}
        save(OUT/"summary.json",summary)
    finally:
        control("/finish")
        (fixture.TMP/"route-key.hex").unlink(missing_ok=True)
        for p in fixture.TMP.glob("install-*"):p.unlink(missing_ok=True)
    if len(means)!=2*len(BLOCKS):raise SystemExit(2)
if __name__=="__main__":
    assert os.uname().machine=="aarch64"
    if sys.argv[1]=="server":server()
    elif sys.argv[1]=="client":client()
    elif sys.argv[1]=="watch":watch(sys.argv[2])
