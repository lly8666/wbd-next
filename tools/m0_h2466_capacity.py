"""H2466 stable-load bare TCP and frozen native WBD comparisons."""
import http.server,ipaddress,json,os,pathlib,re,subprocess,sys,threading,time
import m0_h2228_three_runner_relay as h

ROOT=pathlib.Path.cwd()
PEER=ROOT/"h2228-peer"
OUT=ROOT/"h2228-out"
SPECS=[(-10,"bare250-before",200,250,"gro","gro"),
       (0,"wbd100",200,100,"gro","gro"),
       (1,"wbd150",200,150,"gro","gro"),
       (2,"wbd200",200,200,"gro","gro"),
       (3,"wbd250",200,250,"gro","gro"),
       (4,"wbd150-repeat",200,150,"gro","gro"),
       (-11,"bare250-after",200,250,"gro","gro")]
def configure(module):
    module.DIRECT={case:(delay,67108864) for case,_,delay,rate,_,_ in SPECS if case<0}
    module.DIRECT_RATES={case:rate for case,_,delay,rate,_,_ in SPECS if case<0}
    module.CASES=[{"budget":rate,"rate":rate,"loss":0,"profile":-1,"isolate":False,"rcvbuf":67108864}
                  for case,_,delay,rate,_,_ in SPECS if case>=0]
    module.DIRECT_SECONDS=module.SECONDS=60
FEATURES={"rx-udp-gro-forwarding":"on","rx-gro-list":"off"}

def save(path,obj):
    p=pathlib.Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2)+"\n")
def load(path):return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
def command(*args):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=15)
    return {"rc":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
def root(*args):return command("sudo","-n",*args)
def features(dev):
    r=root("ethtool","-k",dev)
    found={}
    if r["rc"]==0:
        for line in r["stdout"].splitlines():
            m=re.match(r"\s*([\w-]+):\s+(on|off)(\s+\[fixed\])?",line)
            if m and m[1] in FEATURES:found[m[1]]={"value":m[2],"fixed":bool(m[3])}
    return found,r
def profile(role,mode):
    assert role in ("client","relay","server") and mode in ("baseline","gro")
    out=ROOT/("h2442-out" if role=="client" else "h2228-out")
    p=out/f"h2466-{role}-original-offload.json"
    if p.is_file():original=load(p)
    else:
        routes=json.loads(command("ip","-j","route","show","default")["stdout"])
        devs=sorted({r["dev"] for r in routes if "dev" in r})
        # Observe the physical/default route plus Tailscale and local VXLAN devices.
        if role=="client" and "eth0" not in devs:devs.append("eth0")
        original={"role":role,"devices":{},"kernel":command("uname","-a"),"tailscale":command("tailscale","version")}
        for dev in devs:
            f,raw=features(dev);original["devices"][dev]={"features":f,"raw":raw}
        save(p,original)
    changes=[]
    for dev,record in original["devices"].items():
        for key,v in record["features"].items():
            before,_=features(dev)
            if key not in before:continue
            target=v["value"] if mode=="baseline" else FEATURES[key]
            if before[key]["value"]==target:continue
            if before[key]["fixed"]:
                changes.append({"device":dev,"feature":key,"target":target,"status":"fixed"})
                continue
            result=root("ethtool","-K",dev,key,target)
            after,_=features(dev)
            changes.append({"device":dev,"feature":key,"before":before[key]["value"],"target":target,
                            "actual":after.get(key),"result":result})
    actual={dev:features(dev)[0] for dev in original["devices"]}
    differing=[{"device":dev,"feature":key,"value":v["value"]}
               for dev,record in original["devices"].items() for key,v in actual[dev].items()
               if key in record["features"] and v["value"]!=record["features"][key]["value"]]
    restored=not differing and all(set(actual[d])==set(r["features"]) for d,r in original["devices"].items())
    result={"role":role,"mode":mode,"changes":changes,"actual":actual,"diff_from_baseline":differing,
            "baseline_restored":restored}
    if mode=="baseline" and not restored:raise RuntimeError("offload baseline readback mismatch")
    return result

def tun_snapshot():
    def get(*args):
        result=command(*args)
        if result["rc"]:raise RuntimeError(repr(result))
        return result["stdout"]
    link=json.loads(get("ip","-s","-j","link","show","dev","tailscale0"))[0]
    counters=link.get("stats64",link.get("stats",{}))
    if "tx" not in counters:raise RuntimeError("TUN counters unavailable")
    return {"qlen":link["txqlen"],"tx":counters["tx"],"rx":counters["rx"],
            "qdisc":json.loads(get("tc","-s","-j","qdisc","show","dev","tailscale0"))}
def queue(mode):
    assert mode in ("original","snapshot")
    row=tun_snapshot()
    if row["qlen"]!=500:raise RuntimeError("unexpected fixture TUN length: "+str(row["qlen"]))
    return row
def drop_reason_inventory():
    paths=("/sys/kernel/tracing/events/skb/kfree_skb/format","/sys/kernel/debug/tracing/events/skb/kfree_skb/format")
    return {p:root("cat",p) for p in paths}
def packet_summary(text):
    sizes={}
    for line in text.splitlines():
        m=re.search(r"\btcp\s+(\d+)\s*$",line)
        if m:
            n=int(m[1]);sizes[n]=sizes.get(n,0)+1
    return {"classified":sum(sizes.values()),"zero_tcp_payload":sizes.get(0,0),
            "nonzero_tcp_payload":sum(v for k,v in sizes.items() if k>0),
            "payload_size_counts":sizes,"output_lines":len(text.splitlines())}

def packet_sample(port):
    assert port in (443,5202)
    win=load(PEER/"client.json")["windows_access_ip"]
    win=str(ipaddress.IPv4Address(win))
    expr=f"ip and tcp and src host {win} and dst host 10.248.82.2 and dst port {port}"
    start=time.time()
    p=subprocess.run(["timeout","--signal=INT","3s","tcpdump","-i","h228vc","-Q","out",
                      "-nn","-tt","-q","-l","-s","96","-c","8000",expr],
                     capture_output=True,text=True,timeout=9)
    result=packet_summary(p.stdout)
    result.update(start_unix=start,end_unix=time.time(),port=port,rc=p.returncode,stderr=p.stderr[-2500:],
                  scope="short scoped outer TCP header sample; encrypted nonzero payload not decoded; no raw packet or payload retained")
    return result

def drop_histogram():
    # Private instance on the ephemeral WSL guest, aggregate counts only.
    base=pathlib.Path("/sys/kernel/tracing/instances")
    instance=base/("h2466-"+str(os.getpid()))
    trigger=instance/"events/skb/kfree_skb/trigger"
    hist=trigger.with_name("hist")
    spec="hist:keys=location.sym,reason:sort=hitcount"
    result={"status":"UNAVAILABLE"}
    installed=False;created=False
    try:
        instance.mkdir();created=True
        trigger.write_text(spec+"\n");installed=True
        start=time.time();before=tun_snapshot();time.sleep(3);after=tun_snapshot()
        result={"status":"SAMPLED","start_unix":start,"end_unix":time.time(),
                "histogram":hist.read_text(),"tun_dropped_delta":after["tx"]["dropped"]-before["tx"]["dropped"],
                "scope":"guest-wide aggregate skb frees by call site and reason, not per-interface attribution"}
    except Exception as e:result["error"]=repr(e)
    finally:
        if installed:
            try:trigger.write_text("!"+spec+"\n")
            except OSError as e:result["remove_error"]=repr(e)
        if created:
            try:instance.rmdir()
            except OSError as e:result["cleanup_error"]=repr(e)
    return result

def process_snapshot():
    result=command("pidof","tailscaled")
    pids=result["stdout"].split()
    if len(pids)!=1:return {"pidof":result}
    pid=pids[0]
    files={}
    for name in ("stat","status","schedstat"):
        try:files[name]=pathlib.Path("/proc",pid,name).read_text()
        except OSError as e:files[name]=repr(e)
    files["threads"]={}
    for task in pathlib.Path("/proc",pid,"task").glob("*"):
        try:files["threads"][task.name]={"comm":(task/"comm").read_text().strip(),"stat":(task/"stat").read_text(),"schedstat":(task/"schedstat").read_text()}
        except OSError:continue
    host={}
    for name in ("stat","softirqs","pressure/cpu"):
        try:host[name]=pathlib.Path("/proc",name).read_text()
        except OSError as e:host[name]=repr(e)
    return {"pid":pid,"clock_ticks":os.sysconf("SC_CLK_TCK"),"files":files,"guest":host}
def monitor(role,path,stop):
    wanted=("client","server") if role=="relay" else ("relay",)
    peers={r:load(PEER/(r+".json"))["tail_ip"] for r in wanted}
    with pathlib.Path(path).open("w",encoding="utf-8",buffering=1) as f:
        while not pathlib.Path(stop).exists():
            start=time.time();row={"role":role,"wall_unix":start,"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"]}
            try:
                st=json.loads(command("tailscale","status","--json")["stdout"])
                row["peers"]={}
                for role2,ip in peers.items():
                    peer=next(x for x in st["Peer"].values() if ip in x.get("TailscaleIPs",[]))
                    endpoint=peer.get("CurAddr","")
                    public=False
                    if endpoint:
                        addr=endpoint.rsplit(":",1)[0].strip("[]")
                        public=ipaddress.ip_address(addr).is_global
                    row["peers"][role2]={"direct":bool(endpoint and not peer.get("PeerRelay")),"public":public,"rx":peer.get("RxBytes"),"tx":peer.get("TxBytes")}
            except Exception as e:row["error"]=repr(e)
            if role=="client":
                try:row["tun"]=tun_snapshot();row["process"]=process_snapshot()
                except Exception as e:row["tun_error"]=repr(e)
            f.write(json.dumps(row)+"\n");time.sleep(max(0,2-(time.time()-start)))

def relay():
    old=h.Control
    class Control(old):
        def do_POST(self):
            if self.path!="/offload":return super().do_POST()
            if not self.authorized():self.send_error(403);return
            try:
                body=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if set(body)!={"mode"}:raise ValueError("profile body")
                self.result(profile("relay",body["mode"]))
            except Exception as e:self.send_error(400,repr(e)[:250])
    h.Control=Control
    h.main()

def server():
    import m0_h2442_server as s
    configure(s)
    s.setup()
    s.peer=load(PEER/"client.json");s.relay=load(PEER/"relay.json")
    class Handler(s.Handler):
        def do_POST(self):
            if self.path!="/offload":return super().do_POST()
            if self.client_address[0]!=s.peer["tail_ip"] or self.headers.get("X-H2228-Token")!=s.relay["control_token"]:
                self.send_error(403);return
            try:
                body=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if set(body)!={"mode"}:raise ValueError("profile body")
                raw=json.dumps(profile("server",body["mode"])).encode()
                self.send_response(200);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
            except Exception as e:self.send_error(400,repr(e)[:250])
    try:
        with http.server.ThreadingHTTPServer((h.tailscale_ip(),18727),Handler) as svc:
            save(OUT/"server-ready.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"scope":"frozen native product and bare TCP"})
            svc.serve_forever()
    finally:
        for key in list(s.procs):s.stop(key)

def client():
    import m0_h2442_windows_client as c
    configure(c)
    out=c.OUT
    stop=out/"monitor-stop"
    # Keep the monitoring subprocess owned by the measuring Python process.
    mon=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--exec","env","GITHUB_SHA="+os.environ["GITHUB_SHA"],
        "GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],"python3",c.wpath(pathlib.Path(__file__)),"monitor","client",
        c.wpath(out/"tailscale-paths.jsonl"),c.wpath(stop)])
    orig_sink=c.sink;clock={};diagnostics={};active_case=None
    def timed_sink(*a,**kw):
        clock["measure_start_unix"]=time.time()
        finished=threading.Event()
        def sample():
            for offset,action,key,args in ((20,"packets","outer_header_sample",[str(443 if active_case>=0 else 5202)]),
                                           (35,"drop-hist","drop_histogram",[])):
                if finished.wait(max(0,clock["measure_start_unix"]+offset-time.time())):return
                try:
                    diagnostics[key]=json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__)),action,*args,timeout=20))
                except Exception as e:diagnostics[key]={"error":repr(e)}
        worker=threading.Thread(target=sample,daemon=True);worker.start()
        try:return orig_sink(*a,**kw)
        finally:
            clock["measure_end_unix"]=time.time();finished.set();worker.join(25)
    c.sink=timed_sink
    rows=[]
    def apply(wsl_mode,arm_mode):
        return {"client":json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__)),"profile","client",wsl_mode,timeout=90)),
                "relay":c.control("relay","/offload",{"mode":arm_mode}),
                "server":c.control("server","/offload",{"mode":arm_mode})}
    def q(mode):
        return json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__)),"queue",mode,timeout=30))
    def summary():
        save(out/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
             "real_three_runner_l3_relay":True,"all_three_distinct_native_machines":True,"streams":1,
             "scope":"bare and frozen WBD TCP, zero injected loss, FEC off","rows":rows})
    try:
        # Require the existing direct peers before measuring. No change to routes.
        save(out/"initial-direct-peers.json",c.direct_peers())
        save(out/"windows-offload-inventory.json",json.loads(c.ps("Get-NetAdapter | Select-Object Name,InterfaceIndex,LinkSpeed,Status | ConvertTo-Json -Compress")))
        save(out/"drop-reason-inventory.json",json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__)),"drop-inventory",timeout=40)))
        fixed_offload=apply("gro","gro")
        for case,label,delay,rate,wsl_mode,arm_mode in SPECS:
            clock.clear();diagnostics.clear();active_case=case
            record={"case":case,"label":label,"rate_mbps":rate,"added_rtt_ms":delay*2,"status":"INCOMPLETE"}
            try:
                record["offload"]=fixed_offload
                record["tun_before"]=q("original")
                record["effective_candidate"]=False
                record.update(c.case(case));record.update(clock)
                record["diagnostics"]=dict(diagnostics)
                record["kind"]="bare" if case<0 else "wbd"
                record["tun_after"]=q("snapshot")
                if record["tun_after"]["qlen"]!=record["tun_before"]["qlen"]:raise RuntimeError("TUN length drift")
            except Exception as e:
                record["status"]="INCOMPLETE"
                record["error"]=repr(e);record.update(clock)
            rows.append(record);summary()
            print("H2466_CASE "+json.dumps({k:v for k,v in record.items() if k!="offload"}),flush=True)
        if not all(r["status"]=="MEASURED_EXACT" for r in rows):raise SystemExit(2)
    finally:
        summary()
        try:save(out/"restore-tun.json",q("original"))
        except Exception as e:save(out/"restore-tun.json",{"error":repr(e)})
        try:save(out/"restore-offload.json",apply("baseline","baseline"))
        except Exception as e:save(out/"restore-offload.json",{"error":repr(e)})
        try:c.control("server","/finish")
        except Exception:pass
        stop.touch()
        try:mon.wait(10)
        except subprocess.TimeoutExpired:mon.terminate();mon.wait(10)

def qualify(folder):
    folder=pathlib.Path(folder);s=load(folder/"client"/"summary.json")
    assert s["source_sha"]==os.environ["GITHUB_SHA"] and s["run_id"]==os.environ["GITHUB_RUN_ID"]
    logs={}
    for role in ("client","relay","server"):
        p=folder/role/"tailscale-paths.jsonl"
        logs[role]=[json.loads(l) for l in p.read_text().splitlines()] if p.is_file() else []
    rows=[]
    for r in s["rows"]:
        a,b=r.get("measure_start_unix"),r.get("measure_end_unix")
        checks={}
        for role,log in logs.items():
            x=[l for l in log if a is not None and b is not None and a-4<=l["wall_unix"]<=b+4]
            t=[l["wall_unix"] for l in x]
            checks[role]={"samples":len(x),"direct":bool(t and t[0]<=a+4 and t[-1]>=b-4 and all(v-u<=7 for u,v in zip(t,t[1:])) and all(
              l.get("source_sha")==s["source_sha"] and l.get("run_id")==s["run_id"] and l.get("role")==role
              and len(l.get("peers",{}))==(2 if role=="relay" else 1)
              and all(p["direct"] and p["public"] for p in l["peers"].values()) for l in x))}
        tun=[l for l in logs["client"] if a is not None and b is not None and a+2<=l["wall_unix"]<=b-2 and "tun" in l]
        delta=None
        if len(tun)>=2:
            f,z=tun[0],tun[-1]
            delta={"seconds":z["wall_unix"]-f["wall_unix"],"samples":len(tun),
                   "tx_packets":z["tun"]["tx"]["packets"]-f["tun"]["tx"]["packets"],
                   "tx_dropped":z["tun"]["tx"]["dropped"]-f["tun"]["tx"]["dropped"]}
        expected=500
        length_ok=bool(tun and all(l["tun"]["qlen"]==expected for l in tun)
                      and r.get("tun_before",{}).get("qlen")==r.get("tun_after",{}).get("qlen")==expected)
        rows.append({"case":r["case"],"label":r["label"],"rx_mbps":r.get("rx_mbps"),"receipt":r["status"],
                     "tun_delta":delta,"length_ok":length_ok,"queue_length":expected,
                     "rate_mbps":r["rate_mbps"],
                     "header_sample":{k:v for k,v in r.get("diagnostics",{}).get("outer_header_sample",{}).items() if k not in ("payload_size_counts","stderr")},
                     "drop_histogram_status":r.get("diagnostics",{}).get("drop_histogram",{}).get("status"),
                     "candidate_changed":r.get("effective_candidate"),"kind":"bare" if r["case"]<0 else "wbd","path":checks,
                     "qualified":r["status"]=="MEASURED_EXACT" and length_ok and delta is not None and all(v["direct"] for v in checks.values())})
    result={"source_sha":s["source_sha"],"run_id":s["run_id"],"rows":rows,
            "all_cases_qualified":len(rows)==len(SPECS) and all(r["qualified"] for r in rows)}
    save("h2466-qualification.json",result);print("H2466_QUALIFICATION "+json.dumps(result),flush=True)
    if not result["all_cases_qualified"]:raise SystemExit(2)

if __name__=="__main__":
    action=sys.argv[1]
    if action=="queue":print(json.dumps(queue(sys.argv[2])))
    elif action=="drop-inventory":print(json.dumps(drop_reason_inventory()))
    elif action=="packets":print(json.dumps(packet_sample(int(sys.argv[2]))))
    elif action=="drop-hist":print(json.dumps(drop_histogram()))
    elif action=="profile":print(json.dumps(profile(*sys.argv[2:])))
    elif action=="monitor":monitor(*sys.argv[2:])
    elif action=="server":server()
    elif action=="client":client()
    elif action=="qualify":qualify(sys.argv[2])
    else:raise ValueError(action)
