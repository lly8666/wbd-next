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
# Same exact accepted product artifact, two occurrences per arm.
ORDER=("A","E","E","A")
CASES=tuple(range(len(ORDER)))
PROFILES={"A":"dual-rust-bbr3-immediate","E":"dual-rust-bbr3-earned-edt"}
PRODUCT_SOURCE="9677716be3e3f46e7918e3225ad46cbb54e37563"
SOURCES={k:PRODUCT_SOURCE for k in ORDER}
def dual(i):return i>=0 and ORDER[i]!="S"
def splice(i):return i>=0 and ORDER[i]=="S"
def loss_for(i):return 0.0
def cc_for(i):return "cubic" if i<0 or ORDER[i]=="R" else "bbr"
def rust_cc(i):return "bbr" if dual(i) else None
def ack_for(k):return "2"
def profile(i,k):return PROFILES[k]
def compress(k):return "1"
def offer(i):return None
def target_bytes(i):return None
def profile_env(k,server):
    return ["WBD_M0_MIDDLE_CC=bbr3","WBD_M0_BBR3_INITIAL_600M=1",
            "WBD_M0_NATIVE_EDT="+("1" if k=="E" else "0")]+(["WBD_M0_NATIVE_FEEDBACK=service"] if server else [])
def app_args(i,role):
    return [sys.executable,str(ROOT/"tools/m0_dual_tcp_long_app.py"),role,
            str(PORT if i>=0 else 5202),TARGET if i>=0 else "10.248.82.2","180"]
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
def fq_reset():
    h.ns(N,"tc","qdisc","replace","dev","wan0","root","fq")
    return fq_state()
def fq_state():
    rows=json.loads(h.ns(N,"tc","-s","-j","qdisc","show","dev","wan0").stdout)
    return next(x for x in rows if x["kind"]=="fq" and x.get("root"))
def edt_receipt(log,k,role):
    rows=[x for x in log.splitlines() if "WBD_M0_TCP_EDT " in x]
    if k=="A":return {"valid":not rows,"enabled":False}
    values=[dict(re.findall(r"(\w+)=(\d+)",x)) for x in rows]
    if not values:return {"valid":False,"enabled":True}
    timed=sum(int(x["timed_copied"]) for x in values)
    maximum=max(int(x["max_delay_ns"]) for x in values)
    return {"valid":maximum<=1_000_000 and (role!="server" or timed>0),
            "enabled":True,"timed_copied":timed,"max_delay_ns":maximum}
def common():
    return ["--server-name","wbd-h2228.example.test","--route-key-hex-file",fixture.TMP/"route-key.hex",
            "--mode","normal","--outer-repair","on","--outer-mtu","1160","--tun-fq-maxrate-mbps","0"]
def server_start(i):
    global CURRENT,FOLDER
    assert CURRENT is None and i in CASES
    CURRENT=fixture.current=i
    FOLDER=OUT/("case-"+str(i));FOLDER.mkdir()
    set_cc(N,i);set_cc(ORIGIN,i)
    save(FOLDER/"fq-initial.json",fq_reset())
    if i<0:
        source=spawn("origin",N,FOLDER/"origin.log",*app_args(i,"origin"))
        where=N;port=5202
    else:
        k=ORDER[i];b=bundle(k)
        flags=["--tcp-proxy-cc","bbr","--tcp-proxy-port","46180"] if splice(i) else ["--dual-rust-tcp"]
        p=spawn("server",N,FOLDER/"server.log","env","WBD_M0_ACK_PROBE=2","WBD_M0_RX_PACKET_STATS=1",*profile_env(k,True),"LD_LIBRARY_PATH="+str(b),b/"wbd-v4-server",
                "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
                "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--users-file",fixture.TMP/"users.json",
                "--lease-pool","10.66.0.128/25","--tls-cert",OUT/"cert.pem","--tls-key",fixture.TMP/"key.pem",
                *common(),*flags)
        waitmark(p,FOLDER/"server.log","V4_PUBLIC_MULTI_SERVER_READY role=server port=443")
        if splice(i):waitmark(p,FOLDER/"server.log","WBD_TCP_SPLICE_READY")
        source=spawn("origin",ORIGIN,FOLDER/"origin.log",*app_args(i,"origin"))
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
    if dual(i):
        end=time.monotonic()+15
        while time.monotonic()<end and "WBD_M0_TCP_FLOW_FINAL " not in (d/"server.log").read_text(errors="replace"):
            time.sleep(.1)
    rc={key:stop(key) for key in list(PROCS)}
    result={"case":i,"rc":rc,"final_sample":sample,"final_sample_error":sample_error}
    try:result["origin_app"]=load(d/"origin.log")
    except Exception as e:result["origin_app_error"]=repr(e)
    if i>=0:
        log=(d/"server.log").read_text(errors="replace")
        result["joined_stop"]=rc.get("server")==0 and "V4_PUBLIC_SHARED_TUN_STOP" in log and "reader_joined=1" in log and "V4_PUBLIC_SERVER_MASQUERADE_STOP_DRAINED" in log and (("WBD_DUAL_RUST_TCP_OWNER_STOP" in log) if dual(i) else ("WBD_TCP_SPLICE_STOP error=<nil>" in log))
        if splice(i):
            result["splice_socket_close"]=[s for s in log.splitlines() if "WBD_M0_SPLICE_TCP_INFO " in s]
            result["splice_actual_cc"]=[s for s in log.splitlines() if "WBD_TCP_SPLICE_ACCEPT " in s]
        result["wire"]=[s for s in log.splitlines() if "WBD_DUAL_TCP_WIRE role=" in s]
        result["probe"]=probe_receipt(log,"server-middle",ORDER[i],i) if dual(i) else {"valid":bool(result["splice_socket_close"]) and any(" cc=bbr" in x for x in result["splice_actual_cc"])}
        result["bulk_tcp_sample"]=bulk_tcp_sample(log,"server-middle")
        bulk=result["bulk_tcp_sample"]
        result["bulk_retired"]=bool(bulk and any("WBD_M0_TCP_FLOW_FINAL " in s and (" id="+str(bulk["flow_id"])+" ") in s and "leg=server-middle" in s for s in log.splitlines()))
        result["bulk_stop_sample"]=bool(bulk and any("WBD_M0_TCP_FLOW_STOP " in s and (" id="+str(bulk["flow_id"])+" ") in s and "leg=server-middle" in s for s in log.splitlines()))
        result["experiment"]=profile(i,ORDER[i])
        result["edt"]=edt_receipt(log,ORDER[i],"server")
        result["fq_initial"]=load(d/"fq-initial.json")
        result["fq_after_stop"]=fq_state()
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
    rows=[x for x in log.splitlines() if "WBD_M0_TCP_INFO " in x and "leg="+leg+" " in x]
    marker="WBD_M0_BBR "
    bbr=[x for x in log.splitlines() if marker in x and "leg="+leg+" " in x]
    mode=2 if leg=="server-middle" else 0
    cc=rust_cc(i)
    valid=bool(rows) and all(('congestion: "'+cc+'"') in x and (" native_feedback_mode="+str(mode)+" ") in x and " ack3=false " in x and " native_pace_ceiling_bytes_s=0 " in x for x in rows)
    valid=valid and bool(bbr) and all(" initial_pacing_rate=75000000" in x for x in bbr)
    return {"valid":valid,"cc":cc,"native_feedback_mode":mode,"initial_pacing_rate":75000000,"tcp_info_rows":len(rows),"bbr_rows":len(bbr)}
def client_case(i):
    k=ORDER[i] if i>=0 else "bare"
    d=OUT/("case-"+str(i));d.mkdir()
    started=False;pre=post=before=after=None
    row={"case":i,"leg":k,"source_sha":SOURCES.get(k),"loss_pct":loss_for(i),"ack_ratio":int(ack_for(k)) if i>=0 else None,"kernel_cc":cc_for(i),"rust_middle_cc":rust_cc(i) if i>=0 else None,"server_ingress_first":i>=0,"client_local_gso":i>=0,"inbox_slots":1024 if i>=0 else None,"server_middle_pace_quantum_mss":32 if i>=0 else None,"offered_bps":offer(i),"target_bytes":target_bytes(i),"experiment":profile(i,k) if i>=0 else "bare","sack_compress":compress(k) if i>=0 else None,"added_rtt_ms":400,"status":"INCOMPLETE"}
    try:
        shape(0,0)
        set_cc(N,i)
        row["fq_initial"]=fq_reset()
        started=True
        control("/start",{"case":i})
        if i>=0:
            b=bundle(k);flags=["--dual-rust-tcp"] if dual(i) else []
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
        cmd=["ip","netns","exec",N,*app_args(i,"client")]
        save(d/"app-argv.json",cmd)
        with (d/"app-client.json").open("w") as f,(d/"app-client.err").open("w") as err:
            p=subprocess.Popen(cmd,stdout=f,stderr=err)
            t=time.monotonic()
            try:
                for at in (5,15,30,45,60,90,120,150,180,210,240):
                    try:
                        p.wait(timeout=max(0.01,t+at-time.monotonic()))
                        break
                    except subprocess.TimeoutExpired:pass
                    sample={"wall_ns":time.time_ns()}
                    for name,read in (("client",lambda:snapshot("client")),("server",lambda:control("/sample")),("relay",lambda:relay("snapshot"))):
                        try:sample[name]=read()
                        except Exception as e:sample[name+"_error"]=repr(e)
                    save(d/("live-"+str(at)+".json"),sample)
                p.wait(timeout=max(1,270-(time.monotonic()-t)))
            finally:
                if p.poll() is None:p.kill();p.wait()
        row["end_wall_ns"]=time.time_ns()
        row["app_rc"]=p.returncode
        if p.returncode:raise RuntimeError("finite app rc="+str(p.returncode))
        r=load(d/"app-client.json")
        assert r["received_bytes"]>0 and r["eof"]
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
            row["client_stop"]=rc==0 and "V4_PUBLIC_SHARED_TUN_STOP" in log and "reader_joined=1" in log and log.count("V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client")==1 and (not dual(i) or "WBD_DUAL_RUST_TCP_OWNER_STOP" in log)
            row["wire"]=[s for s in log.splitlines() if "WBD_DUAL_TCP_WIRE role=" in s]
            row["edt"]=edt_receipt(log,k,"client")
            row["fq_after_stop"]=fq_state()
            row["probe"]=probe_receipt(log,"client-middle",k,i) if dual(i) else {"valid":True}
            row["native_counters"]=[s for s in log.splitlines() if "M0_PLAN029_NATIVE_INBOX_BOUND" in s or "WBD_M0_TCP_INGRESS" in s or "WBD_M0_TCP_PUBLISH" in s or "WBD_M0_RAW_RX_PACKET_STATS" in s or "WBD_M0_TCP_M4_CLOCK" in s or "WBD_M0_LOCAL_TUN_GSO" in s or "V4_PUBLIC_SHARED_TUN_STOP" in s]
        if started:
            try:row["server_receipt"]=control("/stop")
            except Exception as e:row["server_stop_error"]=repr(e)
        if row.get("application_result"):
            origin=row.get("server_receipt",{}).get("origin_app",{})
            app=row.get("application_result",{})
            row["hash_match"]=origin.get("sha256")==app.get("sha256") and origin.get("sent_bytes")==app.get("received_bytes") and app.get("received_bytes",0)>0 and origin.get("seconds",0)>=180 and row.get("server_receipt",{}).get("rc",{}).get("origin")==0
            if row["status"]=="MEASURED" and not row["hash_match"]:row["status"]="INCOMPLETE_APP_HASH"
        if row["status"]=="MEASURED" and i>=0 and (not row.get("client_stop") or not row.get("server_receipt",{}).get("joined_stop")):row["status"]="INCOMPLETE_STOP"
        if row["status"]=="MEASURED" and i>=0 and not (row.get("probe",{}).get("valid") and row.get("server_receipt",{}).get("probe",{}).get("valid")):row["status"]="INCOMPLETE_PROBE"
        if row["status"]=="MEASURED" and (not row.get("endpoint_direct_snapshots") or row.get("server_receipt",{}).get("final_sample_error")):row["status"]="INCOMPLETE_PATH_OR_SAMPLE"
        if row["status"]=="MEASURED" and dual(i) and not row.get("server_receipt",{}).get("bulk_retired"):row["status"]="INCOMPLETE_RECOVERY_SAMPLE"
        if row["status"]=="MEASURED":
            sr=row["server_receipt"]
            if not (row["edt"]["valid"] and sr["edt"]["valid"]):row["status"]="INCOMPLETE_EDT_RECEIPT"
            elif not all(x.get("qlen")==0 and x.get("backlog")==0 for x in (row["fq_after_stop"],sr["fq_after_stop"])):row["status"]="INCOMPLETE_FQ_DRAIN"
            elif not all(x["fq_initial"]["options"]==x["fq_after_stop"]["options"] for x in (row,sr)):row["status"]="INCOMPLETE_FQ_CHANGE"
        if row["status"]=="MEASURED" and i<0 and not row.get("server_receipt",{}).get("origin_app",{}).get("kernel_final_valid"):row["status"]="INCOMPLETE_KERNEL_FINAL"
        save(d/"result.json",row)
        print("ARM_LONGFLOW_RESULT "+json.dumps({k:v for k,v in row.items() if k not in ("server_receipt","wire")}),flush=True)
    return row
def client():
    manifests()
    peers={role:peer(role) for role in ("client","relay","server")}
    for role in ("relay","server"):h.validate_pair(peers["client"],peers[role],role)
    distinct=len({m["tail_ip"] for m in peers.values()})==3
    assert distinct
    fixture.TMP.mkdir(exist_ok=True)
    (fixture.TMP/"route-key.hex").write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n")
    (fixture.TMP/"route-key.hex").chmod(0o600)
    rows=[]
    complete=False
    try:
        for i in CASES:
            rows.append(client_case(i));save(OUT/"rows.json",rows)
        complete=len(rows)==len(CASES) and all(x["status"]=="MEASURED" for x in rows)
        summary={"source_sha":os.environ["GITHUB_SHA"],"product_sources":SOURCES,"run_id":os.environ["GITHUB_RUN_ID"],
            "real_three_runner_l3_relay":True,"all_three_distinct_native_machines":distinct,"architecture":"aarch64","added_rtt_ms":400,
            "planned_source_seconds":180,"application_offer":"saturated","outer_mtu":1160,"product_tun_fq_maxrate_mbps":0,
            "initial_rust_bbr_pacing_bytes_s":75000000,"kernel_cc":"bbr","server_native_feedback_mode":2,"client_native_feedback_mode":0,
            "edt_product_enabled_by_arm":{"A":False,"E":True},"endpoint_wan_qdisc":"fq both arms","order":list(ORDER),"profiles":PROFILES,
            "status":"MEASURED_ABBA_EDT_DIAGNOSTIC" if complete else "INCOMPLETE","rows":rows}
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
