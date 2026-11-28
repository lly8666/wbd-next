#!/usr/bin/env python3
"""One ARM client / ARM routed impairment VM / ARM server, matched sustained finite application across three hosts.
Reuse H2228 real two L2 networks and the existing H2442 preset HTTP control.
"""
import hashlib,http.client,http.server,json,os,pathlib,re,signal,subprocess,sys,time,statistics
import m0_h2228_three_runner_relay as h
import m0_h2442_server as fixture

ROOT=pathlib.Path.cwd()
OUT=ROOT/"h2228-out";OUT.mkdir(exist_ok=True)
N=h.NODE;ORIGIN=fixture.ORIGIN
# One native binary, independently selected feedback candidates, mirrored order.
ARM=os.environ["WBD_M0_FEEDBACK_ARM"]
ORDER=(ARM,"A","A",ARM) if os.environ["WBD_M0_FEEDBACK_ORDER"]=="reverse" else ("A",ARM,ARM,"A")
CASES=(-1,*range(len(ORDER)),-2)
PROFILES={"A":"service-epoch-with-paired-receive-measurement",ARM:{"H":"paired-receive-with-stall-observation"}[ARM]}
SOURCES={k:os.environ["GITHUB_SHA"] for k in PROFILES}
def loss_for(i):return 0.0
def cc_for(i):return "bbr"
def rust_cc(i):return "bbr1"
def ack_for(k):return "2"
def profile(i,k):return PROFILES[k]
def compress(k):return "1"
def offer(i):return 600_000_000
def target_bytes(i):return 1024*1024*1024
def profile_env(k,server):
    return ["WBD_M0_NATIVE_FEEDBACK=service"] if server else ["WBD_M0_NATIVE_FEEDBACK="+("receive-stall" if k=="H" else "receive-pair")]
def app_args(i,role):
    return [sys.executable,str(ROOT/"tools/m0_dual_rust_tcp_app.py"),role,
            str(PORT if i>=0 else 5202),TARGET if i>=0 else "10.248.82.2",
            str(target_bytes(i)),str(offer(i))]
def set_cc(ns,i):
    cc=cc_for(i)
    h.ns(ns,"sysctl","-qw","net.ipv4.tcp_congestion_control="+cc)
    assert h.ns(ns,"sysctl","-n","net.ipv4.tcp_congestion_control").stdout.strip()==cc
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
def bundle(k):return ROOT/"bundles"/"A"
def manifests():
    rows={}
    for k,source in SOURCES.items():
        b=bundle(k);m=load(b/"manifest.json")
        assert m["source_sha"]==source and m["architecture"]=="aarch64" and m["rust"]=="1.85.1"
        for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
            assert hashlib.sha256((b/name).read_bytes()).hexdigest()==m["sha256"][name]
        rows[k]={"manifest":m,"manifest_sha256":hashlib.sha256((b/"manifest.json").read_bytes()).hexdigest()}
    assert len({v["manifest_sha256"] for v in rows.values()})==1
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
def qualify_direct(role):
    # Warm the already authorized fixture peer path before measurement,
    # not during the measured application window. A cold or unreachable
    # peer still fails the existing direct-path requirement.
    until=time.monotonic()+35
    attempts=[]
    while True:
        d=direct(role)
        attempts.append({"wall_ns":time.time_ns(),"paths":d})
        if d and all(x["direct"] for x in d.values()):return attempts
        if time.monotonic()>=until:return attempts
        p=h.cmd("tailscale","ping","--c=1",peer("relay")["tail_ip"],timeout=8,allow_fail=True)
        attempts[-1]["ping_rc"]=p.returncode
        attempts[-1]["ping_output"]=p.stdout[-1200:]
        time.sleep(.5)

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
    assert CURRENT is None and i in CASES
    CURRENT=fixture.current=i
    FOLDER=OUT/("case-"+str(i));FOLDER.mkdir()
    set_cc(N,i);set_cc(ORIGIN,i)
    if i<0:
        source=spawn("origin",N,FOLDER/"origin.log",*app_args(i,"recovery-origin"))
        where=N;port=5202
    else:
        k=ORDER[i];b=bundle(k)
        flags=["--dual-rust-tcp"]
        p=spawn("server",N,FOLDER/"server.log","env","WBD_M0_ACK_PROBE=2","WBD_M0_RX_PACKET_STATS=1",*profile_env(k,True),"LD_LIBRARY_PATH="+str(b),b/"wbd-v4-server",
                "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
                "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--users-file",fixture.TMP/"users.json",
                "--lease-pool","10.66.0.128/25","--tls-cert",OUT/"cert.pem","--tls-key",fixture.TMP/"key.pem",
                *common(),*flags)
        waitmark(p,FOLDER/"server.log","V4_PUBLIC_MULTI_SERVER_READY role=server port=443")
        source=spawn("origin",ORIGIN,FOLDER/"origin.log",*app_args(i,"recovery-origin"))
        where=ORIGIN;port=PORT
    until=time.monotonic()+15
    while f":{port} " not in h.ns(where,"ss","-ltn").stdout:
        if source.poll() is not None or time.monotonic()>until:raise RuntimeError("origin listener failed")
        time.sleep(.2)
    readiness=qualify_direct("server")
    save(FOLDER/"direct-before-ready.json",readiness)
    if not all(x["direct"] for x in readiness[-1]["paths"].values()):
        raise RuntimeError("server direct path not ready before measurement")
    return {"case":i,"ready":True,"direct_readiness":readiness[-1]}
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
    sample=None;sample_error=None
    try:sample=server_sample();save(d/"after.json",sample)
    except Exception as e:sample_error=repr(e)
    p=PROCS.get("origin")
    if p and p.poll() is None:
        try:p.wait(20)
        except subprocess.TimeoutExpired:pass
    rc={key:stop(key) for key in list(PROCS)}
    result={"case":i,"rc":rc,"final_sample":sample,"final_sample_error":sample_error}
    try:result["origin_app"]=load(d/"origin.log")
    except Exception as e:result["origin_app_error"]=repr(e)
    if i>=0:
        log=(d/"server.log").read_text(errors="replace")
        result["joined_stop"]=rc.get("server")==0 and "V4_PUBLIC_SHARED_TUN_STOP" in log and "reader_joined=1" in log and "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED" in log and "WBD_DUAL_RUST_TCP_OWNER_STOP" in log
        result["wire"]=[s for s in log.splitlines() if "WBD_DUAL_TCP_WIRE role=" in s]
        result["probe"]=probe_receipt(log,"server-middle",ORDER[i],i)
        result["bulk_tcp_sample"]=bulk_tcp_sample(log,"server-middle")
        bulk=result["bulk_tcp_sample"]
        result["bulk_retired"]=bool(bulk and any("WBD_M0_TCP_FLOW_FINAL " in s and (" id="+str(bulk["flow_id"])+" ") in s and "leg=server-middle" in s for s in log.splitlines()))
        result["bulk_stop_sample"]=bool(bulk and any("WBD_M0_TCP_FLOW_STOP " in s and (" id="+str(bulk["flow_id"])+" ") in s and "leg=server-middle" in s for s in log.splitlines()))
        result["experiment"]=profile(i,ORDER[i])
        result["native_counters"]=[s for s in log.splitlines() if "V4_PUBLIC_RX_CHAIN role=" in s or "V4_PUBLIC_TX_CHAIN role=" in s or "V4_PUBLIC_SHARED_TUN_STOP" in s or "M0_PLAN029_NATIVE_INBOX_BOUND" in s or "WBD_M0_TCP_INGRESS" in s or "WBD_M0_TCP_PUBLISH" in s or "WBD_M0_RAW_RX_PACKET_STATS" in s or "WBD_M0_TCP_M4_CLOCK" in s]
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
def bulk_tcp_sample(log,leg):
    # Use the latest retained sample of the flow with the largest observed
    # sent byte count. These are live snapshots, not final packet receipts.
    latest={}
    for line in log.splitlines():
        if "WBD_M0_TCP_INFO " not in line or "leg="+leg+" " not in line:continue
        ident=re.search(r"\bid=(\d+)",line)
        if not ident:continue
        fields={}
        for key in ("bytes_sent","bytes_retrans","dsack_dups","reord_seen","timeouts"):
            match=re.search(r"\b"+key+r": (\d+)\b",line)
            if match:fields[key]=int(match.group(1))
        if "bytes_sent" not in fields or "bytes_retrans" not in fields:continue
        latest[ident.group(1)]={"flow_id":int(ident.group(1)),**fields,"sample_line":line}
    if not latest:return None
    sample=max(latest.values(),key=lambda x:x["bytes_sent"])
    sample["retrans_byte_ratio"]=sample["bytes_retrans"]/sample["bytes_sent"] if sample["bytes_sent"] else None
    return sample

def probe_receipt(log,leg,k,i):
    rows=[s for s in log.splitlines() if "WBD_M0_TCP_INFO " in s and "leg="+leg+" " in s]
    expected_first="true" if leg=="server-middle" else "false"
    pub=next((s for s in log.splitlines() if "WBD_M0_TCP_PUBLISH " in s),"")
    slots=1024
    quantum=32
    server=leg=="server-middle"
    expected_rack="false"
    expected_ack="false"
    ceiling=0
    gain="2.88671875"
    limit=131072
    first_turns=re.search(r"\bingress_first_service_turns=(\d+)",pub)
    actual_first_turns=int(first_turns.group(1)) if first_turns else -1
    first_ok=actual_first_turns>=0 and ((actual_first_turns>0)==(expected_first=="true"))
    credit_rows=rows+([s for s in log.splitlines() if "WBD_M0_TCP_INFO " in s and "leg=client-local " in s] if not server else [])
    credit=[(int(m.group(1)),int(m.group(2)),int(m.group(3))) for s in credit_rows if (m:=re.search(r" relay_pending_limit=(\d+) relay_pending_bytes=(\d+) relay_available=(\d+) ",s))]
    credit_ok=bool(credit) and len(credit)==len(credit_rows) and all(l==limit and (not l or p<=l) for l,p,a in credit)
    epochs=[int(m.group(1)) for s in log.splitlines() if "WBD_M0_TCP_DETAIL " in s and "leg="+leg+" " in s and (m:=re.search(r"\brate_epoch_preserved=(\d+)",s))]
    dry=[m.group(1) for s in log.splitlines() if "WBD_M0_TCP_DETAIL " in s and "leg="+leg+" " in s and (m:=re.search(r"\bnative_source_dry=(true|false)",s))]
    epoch_ok=bool(epochs) and bool(dry)
    bbr=[s for s in log.splitlines() if "WBD_M0_BBR1 " in s and "leg="+leg+" " in s]
    app_limited_samples=sum("delivery_rate_app_limited: true" in s for s in rows)
    bbr_phases=sorted({m.group(1) for s in bbr if (m:=re.search(r"\bphase=(\w+)",s))})
    gain_ok=bool(bbr) and all(" startup_pacing_gain="+gain+" " in s for s in bbr) and any(" phase=Startup " in s and " pacing_gain="+gain+" " in s for s in bbr)
    rates=[int(m.group(1)) for s in rows if (m:=re.search(r"\bpacing_rate: Some\((\d+)\)",s))]
    ceiling_ok=bool(rates) and all(" native_pace_ceiling_bytes_s="+str(ceiling)+" " in s for s in rows) and (not ceiling or max(rates)<=ceiling)
    origin_rows=[s for s in log.splitlines() if "WBD_M0_TCP_ORIGIN " in s]
    grants=[int(m.group(1)) for s in rows if (m:=re.search(r"\bnative_ack_grant_deferred=(\d+)",s))]
    actual_grant_max=max(grants,default=0)
    ack_ok=bool(grants) and ((actual_grant_max>0)==(expected_ack=="true")) and (not server or (bool(origin_rows) and all(" ack_drain="+expected_ack in s for s in origin_rows)))
    bound=next((s for s in log.splitlines() if "M0_PLAN029_NATIVE_INBOX_BOUND " in s),"")
    rx=next((s for s in log.splitlines() if "WBD_M0_RAW_RX_PACKET_STATS " in s),"")
    rx_drain=next((s for s in log.splitlines() if "WBD_M0_CLIENT_RX_DRAIN " in s),"")
    dv=dict(w.split("=",1) for w in rx_drain.split() if "=" in w)
    drain_expected=False
    drain_packets=int(dv.get("packets",-1))
    drain_skipped=int(dv.get("skipped_polls",-1))
    drain_ok=dv.get("enabled")==str(drain_expected).lower() and ((drain_packets>0 and drain_skipped>0) if drain_expected else drain_packets==drain_skipped==0)
    mode_ok=epoch_ok and drain_ok and (" ingress_first="+expected_first+" ") in pub and (" slots="+str(slots)+" ") in bound and " packets=" in rx and " drops=" in rx and ack_ok and ceiling_ok and gain_ok and credit_ok and first_ok and all(" pace_quantum_mss="+str(quantum)+" " in s and " rack_keep_reo_window="+expected_rack+" " in s for s in rows)
    gso_ok=True
    if leg=="client-middle":
        receipt=next((s for s in log.splitlines() if "WBD_M0_LOCAL_TUN_GSO groups=" in s),"")
        vals=dict(w.split("=",1) for w in receipt.split() if "=" in w)
        gso_ok=int(vals.get("groups",0))>0
    expected='congestion: "'+rust_cc(i)+'"'
    feedback_mode=2 if leg=="server-middle" else ((6 if k=="H" else 5) if leg=="client-middle" else 0)
    ack3_expected="false"
    feedback_ok=bool(rows) and all(f" native_feedback_mode={feedback_mode} " in s for s in rows)
    reserved=[int(m.group(1)) for s in rows if (m:=re.search(r"\bnative_reserved_bytes=(\d+)",s))]
    pair_hits=[int(m.group(1)) for s in rows if (m:=re.search(r"\bdrs_pair_hits=(\d+)",s))]
    pair_grows=[int(m.group(1)) for s in rows if (m:=re.search(r"\bdrs_pair_grows=(\d+)",s))]
    stall_epochs=[int(m.group(1)) for s in rows if (m:=re.search(r"\bdrs_stall_epochs=(\d+)",s))]
    return {"samples":len(rows),"matching":sum(expected in s and "sack_compress=true" in s and "linux_parity=true" in s and f"ack3={ack3_expected}" in s and "nodelay=false" in s and "send_max=67108864 recv_max=67108864" in s for s in rows),
            "ingress_first_expected":expected_first,"ingress_first_service_turns":actual_first_turns,"rx_drain":dv,"mode_ok":mode_ok,"gso_ok":gso_ok,"ack_grant_deferred_max_sample":actual_grant_max,"pacing_ceiling_bytes_s":ceiling,"actual_pacing_max_bytes_s":max(rates,default=0),"startup_pacing_gain":gain,"startup_gain_verified":gain_ok,"rate_epoch_preserved_max":max(epochs,default=None),"delivery_rate_app_limited_samples":app_limited_samples,"native_source_dry_samples":sum(x=="true" for x in dry) if dry else None,"native_source_observed_samples":len(dry),"bbr_phases":bbr_phases,"relay_pending_limit":limit,"relay_credit_samples":len(credit),"relay_pending_max_sample":max((p for _,p,_ in credit),default=None),"relay_credit_full_samples":sum(p==limit and a==0 for _,p,a in credit) if limit else 0,
            "native_feedback_mode":feedback_mode,"drs_pair_hits":max(pair_hits,default=None),"drs_pair_grows":max(pair_grows,default=None),"drs_stall_epochs":max(stall_epochs,default=None),"ack3_expected":ack3_expected,"native_reserved_max_sample":max(reserved,default=None),"valid":feedback_ok and mode_ok and gso_ok and len(rows)>=10 and all(expected in s and "sack_compress=true" in s and "linux_parity=true" in s and f"ack3={ack3_expected}" in s and "nodelay=false" in s and "send_max=67108864 recv_max=67108864" in s for s in rows)}
def client_case(i):
    k=ORDER[i] if i>=0 else "bare"
    d=OUT/("case-"+str(i));d.mkdir()
    started=False;pre=post=before=after=None
    row={"case":i,"leg":k,"source_sha":SOURCES.get(k),"loss_pct":loss_for(i),"ack_ratio":int(ack_for(k)) if i>=0 else None,"kernel_cc":cc_for(i),"rust_middle_cc":rust_cc(i) if i>=0 else None,"server_ingress_first":i>=0,"client_local_gso":i>=0,"inbox_slots":1024 if i>=0 else None,"server_middle_pace_quantum_mss":32 if i>=0 else None,"offered_bps":offer(i),"target_bytes":target_bytes(i),"experiment":profile(i,k) if i>=0 else "bare","sack_compress":compress(k) if i>=0 else None,"added_rtt_ms":400,"status":"INCOMPLETE"}
    try:
        shape(0,0)
        set_cc(N,i)
        started=True
        control("/start",{"case":i})
        if i>=0:
            b=bundle(k);flags=["--dual-rust-tcp"]
            p=spawn("client",N,d/"client.log","env","WBD_M0_ACK_PROBE="+ack_for(k),"WBD_M0_RX_PACKET_STATS=1",*profile_env(k,False),"LD_LIBRARY_PATH="+str(b),b/"wbd-v4-client",
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
        else:save(d/"shape.json",shape(0,200));time.sleep(.6)
        readiness=qualify_direct("client");save(d/"direct-before-app.json",readiness)
        if not all(x["direct"] for x in readiness[-1]["paths"].values()):raise RuntimeError("client direct path not ready before measurement")
        relay_before=relay("snapshot");save(d/"relay-before.json",relay_before)
        before=control("/sample");save(d/"server-before.json",before)
        pre=snapshot("client");save(d/"client-before.json",pre)
        if not all(all(y["direct"] for y in x["paths"].values()) for x in (pre,before)):
            row["status"]="PATH_NOT_QUALIFIED"
            raise RuntimeError("cold endpoint path at actual pre-app snapshot")
        row["start_wall_ns"]=time.time_ns()
        cmd=["ip","netns","exec",N,*app_args(i,"recovery-client")]
        save(d/"app-argv.json",cmd)
        with (d/"app-client.json").open("w") as f,(d/"app-client.err").open("w") as err:
            p=subprocess.Popen(cmd,stdout=f,stderr=err)
            t=time.monotonic()
            try:
                for at in (5,15,30,45,60,90,120):
                    try:
                        p.wait(timeout=max(0.01,t+at-time.monotonic()))
                        break
                    except subprocess.TimeoutExpired:pass
                    sample={"wall_ns":time.time_ns()}
                    for name,read in (("client",lambda:snapshot("client")),("server",lambda:control("/sample")),("relay",lambda:relay("snapshot"))):
                        try:sample[name]=read()
                        except Exception as e:sample[name+"_error"]=repr(e)
                    save(d/("live-"+str(at)+".json"),sample)
                p.wait(timeout=max(1,180-(time.monotonic()-t)))
            finally:
                if p.poll() is None:p.kill();p.wait()
        row["end_wall_ns"]=time.time_ns()
        row["app_rc"]=p.returncode
        if p.returncode:raise RuntimeError("finite app rc="+str(p.returncode))
        r=load(d/"app-client.json")
        assert r["received_bytes"]==target_bytes(i) and r["eof"]
        gib=r["received_bytes"]/2**30
        row["application_result"]=r
        save(d/"application-result.json",r)
        post=snapshot("client");save(d/"client-after.json",post)
        after=control("/sample");save(d/"server-after.json",after)
        relay_after=relay("snapshot");save(d/"relay-after.json",relay_after)
        observed={}
        for role in ("client","server"):
            old=next(q for q in relay_before[role]["qdisc"] if q["kind"]=="netem")
            new=next(q for q in relay_after[role]["qdisc"] if q["kind"]=="netem")
            emitted=new["packets"]-old["packets"];dropped=new["drops"]-old["drops"]
            assert old["handle"]==new["handle"] and old["options"]==new["options"] and emitted>0 and dropped>=0
            observed[role]={"emitted":emitted,"drops":dropped,"loss_ratio":dropped/(emitted+dropped)}
        row["relay_observed_loss"]=observed
        if loss_for(i):assert all(q["drops"]>0 for q in observed.values()),observed
        row["endpoint_path_samples"]=[x["paths"] for x in (pre,post,before,after)]
        row["endpoint_direct_snapshots"]=all(all(y["direct"] for y in x.values()) for x in row["endpoint_path_samples"])
        row.update(status="MEASURED",mbps=r["mbps"],bytes=r["received_bytes"],seconds=r["seconds"],
                   client=delta(pre,post,gib),server=delta(before,after,gib))
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
            row["native_counters"]=[s for s in log.splitlines() if "M0_PLAN029_NATIVE_INBOX_BOUND" in s or "WBD_M0_TCP_INGRESS" in s or "WBD_M0_TCP_PUBLISH" in s or "WBD_M0_RAW_RX_PACKET_STATS" in s or "WBD_M0_TCP_M4_CLOCK" in s or "WBD_M0_LOCAL_TUN_GSO" in s or "V4_PUBLIC_SHARED_TUN_STOP" in s]
        if started:
            try:row["server_receipt"]=control("/stop")
            except Exception as e:row["server_stop_error"]=repr(e)
        if row.get("application_result"):
            origin=row.get("server_receipt",{}).get("origin_app",{})
            app=row.get("application_result",{})
            row["hash_match"]=origin.get("sha256")==app.get("sha256") and origin.get("sent_bytes")==app.get("received_bytes")==target_bytes(i) and row.get("server_receipt",{}).get("rc",{}).get("origin")==0
            if row["status"]=="MEASURED" and not row["hash_match"]:row["status"]="INCOMPLETE_APP_HASH"
        if row["status"]=="MEASURED" and i>=0 and (not row.get("client_stop") or not row.get("server_receipt",{}).get("joined_stop")):row["status"]="INCOMPLETE_STOP"
        if row["status"]=="MEASURED" and i>=0 and not (row.get("probe",{}).get("valid") and row.get("server_receipt",{}).get("probe",{}).get("valid")):row["status"]="INCOMPLETE_PROBE"
        if row["status"]=="MEASURED" and (not row.get("endpoint_direct_snapshots") or row.get("server_receipt",{}).get("final_sample_error")):row["status"]="INCOMPLETE_PATH_OR_SAMPLE"
        if row["status"]=="MEASURED" and i>=0 and not row.get("server_receipt",{}).get("bulk_retired"):row["status"]="INCOMPLETE_RECOVERY_SAMPLE"
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
            for i in CASES[1:]:
                rows.append(client_case(i));save(OUT/"rows.json",rows)
        means={};recovery={}
        for loss in (0.0,):
            for k in PROFILES:
                key=("clean" if not loss else "loss1")+"-"+k
                v=[x for x in rows if x["leg"]==k and x["loss_pct"]==loss and x["status"]=="MEASURED"]
                if len(v)!=2:continue
                means[key]={"n":len(v),"profile":PROFILES[k],"mbps":statistics.mean(x["mbps"] for x in v),
                    "client_product_cpu_s_per_gib":statistics.mean(x["client"]["product"]["cpu_s_per_gib"] for x in v),
                    "server_product_cpu_s_per_gib":statistics.mean(x["server"]["product"]["cpu_s_per_gib"] for x in v)}
                samples=[x.get("server_receipt",{}).get("bulk_tcp_sample") for x in v]
                if all(s and s["bytes_sent"]>0 for s in samples):
                    sent=sum(s["bytes_sent"] for s in samples);retrans=sum(s["bytes_retrans"] for s in samples)
                    recovery[key]={"bulk_snapshot_sent_bytes":sent,"bulk_snapshot_retrans_bytes":retrans,"weighted_retrans_byte_ratio":retrans/sent,"samples":samples}
        complete=len(rows)==len(CASES) and all(x["status"]=="MEASURED" for x in rows) and len(recovery)==len(PROFILES)
        summary={"recovery_snapshot_scope":"retired server-middle bulk flow on identical frozen Rust build","recovery":recovery,"source_sha":os.environ["GITHUB_SHA"],"product_sources":SOURCES,"intervention":"identical qualified candidate binary, independent forward/reverse matched order, 1GiB/600M/400ms, zero injected loss, bare brackets and eight taps; separate matched comparison","run_id":os.environ["GITHUB_RUN_ID"],"real_three_runner_l3_relay":True,"all_three_distinct_native_machines":True,"architecture":"aarch64","added_rtt_ms":400,"streams":1,"order":ORDER,"profiles":PROFILES,"status":"MEASURED_REQUIRES_PATH_AND_CAPACITY_REVIEW" if complete else "PATH_NOT_QUALIFIED" if len(rows)==1 else "INCOMPLETE","rows":rows,"means":means}
        save(OUT/"summary.json",summary)
    finally:
        control("/finish")
        (fixture.TMP/"route-key.hex").unlink(missing_ok=True)
        for p in fixture.TMP.glob("install-*"):p.unlink(missing_ok=True)
    if not complete:raise SystemExit(2)
if __name__=="__main__":
    assert os.uname().machine=="aarch64"
    if sys.argv[1]=="server":server()
    elif sys.argv[1]=="client":client()
    elif sys.argv[1]=="watch":watch(sys.argv[2])
