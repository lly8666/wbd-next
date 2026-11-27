#!/usr/bin/env python3
"""Actual dual Rust TCP Normal product over four native Linux namespaces; scoped functional and controlled recovery."""
import hashlib,json,os,pathlib,re,signal,subprocess,sys,time
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

def controlled_recovery():
    # Diagnostic, not peak or CPU parity qualification. Same machine, actual
    # sockets and original carrier, no tailnet. Each case gets fresh netem.
    global DELAY,LOSS
    DELAY=200
    rows=[]
    common=["--server-name","wbd-h2228.example.test","--route-key-hex-file",O/"route-key.hex",
            "--mode","normal","--outer-repair","on","--outer-mtu","1160","--dual-rust-tcp"]
    # Test real downstream pause with the same application and both
    # paired profiles, no artificial pacing ceiling. Also verify normal
    # high-load progress without a paused consumer.
    cases=[
        ("normal-default",True,600_000_000,{},0,0,512),
        ("normal-credit",True,600_000_000,{"WBD_M0_RELAY_PENDING_CREDIT":"1"},0,0,512),
        ("pause-default",True,600_000_000,{},0,0,512),
        ("pause-credit",True,600_000_000,{"WBD_M0_RELAY_PENDING_CREDIT":"1"},0,0,512),
    ]
    for label,paired,offered,profile,jitter,loss,mib in cases:
        target_bytes=mib*1024*1024
        d=O/label;d.mkdir()
        server=client=origin=app=None
        row={"case":label,"paired":paired,"offered_bps":offered,"target_bytes":target_bytes,"added_rtt_ms":400,"injected_loss_pct":loss,"forward_jitter_ms":jitter,"profile":profile,"status":"INCOMPLETE"}
        try:
            # Establish the product/control connection on the clean
            # 400ms path, then apply the requested data-phase impairment.
            LOSS=0
            shape(True)
            if paired:
                server=spawn(S,d/"server.log","env",*[k+"="+v for k,v in profile.items()],"LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-server",
                    "--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443",
                    "--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--users-file",O/"users.json",
                    "--lease-pool","10.66.0.128/25","--tls-cert",O/"cert.pem","--tls-key",O/"key.pem",*common)
                until(server,lambda:"V4_PUBLIC_MULTI_SERVER_READY role=server port=443" in (d/"server.log").read_text())
                client=spawn(C,d/"client.log","env",*[k+"="+v for k,v in profile.items() if k in ("WBD_M0_MIDDLE_CC","WBD_M0_RELAY_PENDING_CREDIT")],"LD_LIBRARY_PATH="+str(ROOT),ROOT/"wbd-v4-client",
                    "--raw-interface","wan0","--local-ip","10.248.81.2","--local-port","44100",
                    "--peer-ip","10.248.82.2","--peer-port","443","--tun-name","wbdc0",
                    "--username","bench","--password","DUAL-TCP-FIXTURE","--auto-ip","--installation-id-file",d/"install",*common)
                until(client,lambda:"V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" in (d/"client.log").read_text())
                until(server,lambda:"WBD_DUAL_RUST_TCP_OWNER_START" in (d/"server.log").read_text())
                ns(C,"ip","route","replace","198.18.77.2/32","dev","wbdc0")
            where=T if paired else S
            host="198.18.77.2" if paired else "10.248.82.2"
            port=5400 if paired else 5202
            route=ns(C,"ip","route","get",host)
            (d/"client-route.txt").write_text(route)
            assert ("dev wbdc0" in route) if paired else ("dev wan0" in route)
            app_path=pathlib.Path("tools/m0_dual_rust_tcp_app.py").resolve()
            pause=15 if label.startswith("pause-") else 0
            args=[host,str(target_bytes),str(offered),str(pause)]
            origin_argv=[sys.executable,str(app_path),"recovery-origin",str(port),*args]
            argv=[sys.executable,str(app_path),"recovery-client",str(port),*args]
            origin=spawn(where,d/"origin.json",*origin_argv)
            until(origin,lambda:f":{port} " in ns(where,"ss","-ltn"))
            save(d/"argv.json",{"origin":origin_argv,"client":argv})
            def path_counts():
                return {dev:json.loads(ns(R,"tc","-s","-j","qdisc","show","dev",dev)) for dev in ("rc0","rs0")}
            seed_receipts={}
            for index,dev in enumerate(("rc0","rs0")):
                terms=["delay","200ms"]
                if jitter and dev=="rc0":terms+= [str(jitter)+"ms","distribution","normal"]
                args=["ip","netns","exec",R,"tc","qdisc","replace","dev",dev,"root","netem",*terms,"loss","random",str(loss)+"%","limit","65536"]
                if loss or jitter:
                    seed=20261126+index
                    trial=subprocess.run([*args,"seed",str(seed)],capture_output=True,text=True)
                    if trial.returncode:
                        # Match existing relay fixture's kernel compatibility
                        # behavior; record unavailable seed, never claim matched random outcomes.
                        seed_receipts[dev]={"seed":None,"reason":trial.stderr[-300:]}
                        run(*args)
                    else:seed_receipts[dev]={"seed":seed}
                else:
                    run(*args);seed_receipts[dev]={"seed":None,"reason":"no random impairment"}
            row["seed_receipts"]=seed_receipts
            row["qdisc_before"]=path_counts()
            save(d/"links-before.json",{n:json.loads(ns(n,"ip","-s","-j","link")) for n in N})
            def endpoint_cpu():
                result={}
                for role,p in (("client",client),("server",server),("origin",origin)):
                    if p and p.poll() is None:
                        stat=pathlib.Path("/proc",str(p.pid),"stat").read_text().rsplit(")",1)[1].split()
                        result[role]=int(stat[11])+int(stat[12])
                return result
            cpu_before=endpoint_cpu()
            app=spawn(C,d/"app-client.json",*argv)
            samples=[]
            deadline=time.monotonic()+180
            while app.poll() is None:
                try:app.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    samples.append({"wall_ns":time.time_ns(),"sender_ss":ns(where,"ss","-tinm"),"receiver_ss":ns(C,"ss","-tinm")})
                    save(d/"kernel-samples.json",samples)
                    if time.monotonic()>deadline:raise RuntimeError("controlled transfer timeout")
            origin.wait(20)
            assert app.returncode==0 and origin.returncode==0
            received=json.loads((d/"app-client.json").read_text())
            sent=json.loads((d/"origin.json").read_text())
            row.update(sender_bytes=sent["sent_bytes"],received_bytes=received["received_bytes"],mbps=received["mbps"],
                seconds=received["seconds"],first_data_seconds=received["first_data_seconds"],
                sender_sha256=sent["sha256"],receiver_sha256=received["sha256"],
                byte_match=sent["sent_bytes"]==received["received_bytes"]==target_bytes,
                hash_match=sent["sha256"]==received["sha256"],eof=received["eof"],
                paused_seconds=received["paused_seconds"],origin_max_sendall_seconds=sent["max_sendall_seconds"],origin_sendall_over_250ms_seconds=sent["sendall_over_250ms_seconds"])
            assert received["paused_seconds"]>=pause
            # CPU snapshots bracket actual app completion, not process teardown.
            cpu_after=endpoint_cpu()
            row["endpoint_product_cpu_s_per_gib"]={role:(cpu_after[role]-cpu_before[role])/os.sysconf("SC_CLK_TCK")/(target_bytes/2**30)
                for role in ("client","server") if role in cpu_before and role in cpu_after}
            save(d/"application-result.json",row)
            # Preserve both the application completion and later owner state.
            row["qdisc_after_app"]=path_counts()
            save(d/"links-after-app.json",{n:json.loads(ns(n,"ip","-s","-j","link")) for n in N})
            if paired:
                stop(client);stop(server)
                sl=(d/"server.log").read_text();cl=(d/"client.log").read_text()
                row["joined_stop"]=client.returncode==server.returncode==0 and all("WBD_DUAL_RUST_TCP_OWNER_STOP" in x and "reader_joined=1" in x for x in (sl,cl))
                row["endpoint_receipts"]={role:[line for line in log.splitlines() if any(tag in line for tag in (
                    "WBD_M0_TCP_INGRESS ","WBD_M0_RAW_RX_PACKET_STATS ","WBD_M0_TCP_M4_CLOCK ","WBD_M0_TCP_PUBLISH ","WBD_M0_LOCAL_TUN_GSO ","V4_PUBLIC_SHARED_TUN_STOP ","WBD_DUAL_TCP_WIRE role="))]
                    for role,log in (("client",cl),("server",sl))}
                row["reset_events"]={role:sum("WBD_M0_TCP_RESET_" in line for line in log.splitlines()) for role,log in (("client",cl),("server",sl))}
                latest={}
                for line in sl.splitlines():
                    if "WBD_M0_TCP_INFO " not in line or "leg=server-middle " not in line:continue
                    ident=re.search(r"\bid=(\d+)",line)
                    if not ident:continue
                    fields={key:int(m.group(1)) for key in ("bytes_sent","bytes_retrans","dsack_dups","reord_seen","timeouts")
                        if (m:=re.search(r"\b"+key+r": (\d+)\b",line))}
                    if "bytes_sent" in fields and "bytes_retrans" in fields:
                        latest[ident.group(1)]={"flow_id":int(ident.group(1)),**fields,"sample_line":line}
                if latest:
                    bulk=max(latest.values(),key=lambda x:x["bytes_sent"])
                    row["bulk_tcp_sample"]=bulk
                    row["bulk_retired"]=any("WBD_M0_TCP_FLOW_FINAL " in x and (" id="+str(bulk["flow_id"])+" ") in x and "leg=server-middle" in x for x in sl.splitlines())
                    row["bulk_stop_sample"]=any("WBD_M0_TCP_FLOW_STOP " in x and (" id="+str(bulk["flow_id"])+" ") in x and "leg=server-middle" in x for x in sl.splitlines())
                    row["bulk_snapshot_retrans_ratio"]=bulk["bytes_retrans"]/bulk["bytes_sent"] if bulk["bytes_sent"] else None
                info=[x for x in sl.splitlines() if "WBD_M0_TCP_INFO " in x and "leg=server-middle " in x]
                origin_info=[x for x in sl.splitlines() if "WBD_M0_TCP_ORIGIN " in x]
                expected_ack="true" if profile.get("WBD_M0_SERVER_ACK_DRAIN")=="1" else "false"
                expected_rack="true" if profile.get("WBD_M0_RACK_KEEP_WINDOW")=="1" else "false"
                expected_cc=profile.get("WBD_M0_MIDDLE_CC","bbr1")
                actual_grants=[int(m.group(1)) for x in info if (m:=re.search(r"\bnative_ack_grant_deferred=(\d+)",x))]
                row["ack_grant_deferred_max_sample"]=max(actual_grants,default=0)
                ceiling=int(profile.get("WBD_M0_NATIVE_PACE_MBPS","0"))*125_000
                gentle=profile.get("WBD_M0_BBR1_STARTUP15")=="1"
                bbr=[x for x in sl.splitlines() if "WBD_M0_BBR1 " in x and "leg=server-middle " in x]
                gain="1.5" if gentle else "2.88671875"
                gain_ok=bool(bbr) and all(" startup_pacing_gain="+gain+" " in x for x in bbr) and any(" phase=Startup " in x and " pacing_gain="+gain+" " in x for x in bbr)
                rates=[int(m.group(1)) for x in info if (m:=re.search(r"\bpacing_rate: Some\((\d+)\)",x))]
                row["actual_pacing_max_bytes_s"]=max(rates,default=0)
                pending_limit=131072 if profile.get("WBD_M0_RELAY_PENDING_CREDIT")=="1" else 0
                all_info=info+[x for x in cl.splitlines() if "WBD_M0_TCP_INFO " in x and ("leg=client-middle " in x or "leg=client-local " in x)]
                credit_samples=[(int(m.group(1)),int(m.group(2)),int(m.group(3))) for x in all_info if (m:=re.search(r" relay_pending_limit=(\d+) relay_pending_bytes=(\d+) relay_available=(\d+) ",x))]
                row["relay_credit_samples"]=len(credit_samples)
                row["relay_pending_max_sample"]=max((p for _,p,_ in credit_samples),default=None)
                row["relay_credit_full_samples"]=sum(p==pending_limit and a==0 for _,p,a in credit_samples) if pending_limit else 0
                credit_ok=bool(credit_samples) and len(credit_samples)==len(all_info) and all(l==pending_limit and (not l or p<=l) for l,p,a in credit_samples)
                row["profile_valid"]=credit_ok and gain_ok and bool(info and origin_info and rates) and all(" rack_keep_reo_window="+expected_rack+" " in x and 'congestion: "'+expected_cc+'"' in x and " native_pace_ceiling_bytes_s="+str(ceiling)+" " in x for x in info) and all(" ack_drain="+expected_ack in x for x in origin_info) and bool(actual_grants) and ((row["ack_grant_deferred_max_sample"]>0)==(expected_ack=="true")) and (not ceiling or row["actual_pacing_max_bytes_s"]<=ceiling)
                row["receipt_present"]=all(any("WBD_M0_RAW_RX_PACKET_STATS " in line and " drops=" in line for line in log.splitlines()) and
                    "WBD_M0_TCP_INGRESS " in log for log in (cl,sl)) and "WBD_M0_TCP_M4_CLOCK " in sl and "WBD_M0_LOCAL_TUN_GSO " in cl and bool(latest)
            row["qdisc_after_stop"]=path_counts()
            row["status"]="MEASURED" if row["byte_match"] and row["hash_match"] and row["eof"] and (not paired or (row.get("joined_stop") and row.get("receipt_present") and row.get("profile_valid"))) else "INCOMPLETE"
        except Exception as e:
            row["error"]=repr(e)
        finally:
            for p in (app,origin,client,server):
                if p and p.poll() is None:stop(p)
            (d/"install").unlink(missing_ok=True)
            save(d/"result.json",row)
            print("LOCAL_RECOVERY_RESULT "+json.dumps(row),flush=True)
            rows.append(row)
    summary={"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"scope":"One native host, fixed512MiB actual finite app at600M offer, uncapped adjacent-leg relay pending credit; ordinary and paused consumer, zero injection400ms; actual profile/rate and final-or-Stop sample; local qualification not ABBA","rows":rows,
        "status":"MEASURED_REQUIRES_RECOVERY_REVIEW" if all(x["status"]=="MEASURED" for x in rows) else "INCOMPLETE"}
    save(O/"summary.json",summary)
    if summary["status"]=="INCOMPLETE":raise SystemExit(2)

try:
    make()
    (O/"route-key.hex").write_text(hashlib.sha256(("DUAL-TCP"+os.environ["GITHUB_RUN_ID"]).encode()).hexdigest()+"\n")
    (O/"users.json").write_text(json.dumps({"bench":"DUAL-TCP-FIXTURE"}))
    for name in ("route-key.hex","users.json"):(O/name).chmod(0o600)
    run("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",str(O/"key.pem"),"-out",str(O/"cert.pem"),"-subj","/CN=wbd-h2228.example.test","-addext","subjectAltName=DNS:wbd-h2228.example.test")
    (O/"key.pem").chmod(0o600)
    shape(False)
    if os.environ.get("DUAL_TCP_RECOVERY")=="1":controlled_recovery()
    else:functional()
finally:
    for name in ("route-key.hex","users.json","key.pem","cert.pem"):
        (O/name).unlink(missing_ok=True)
    for n in reversed(N):subprocess.run(["ip","netns","del",n],check=False)
