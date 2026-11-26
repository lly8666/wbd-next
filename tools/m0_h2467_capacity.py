"""H2467 stable-load bare TCP and frozen native WBD comparisons."""
import http.server,ipaddress,json,os,pathlib,re,subprocess,sys,threading,time
import m0_h2228_three_runner_relay as h

ROOT=pathlib.Path.cwd()
PEER=ROOT/"h2228-peer"
OUT=ROOT/"h2228-out"
SPECS=[(-10,"bare250-before",200,250,"gro","gro"),
       (0,"wbd150-original",200,150,"gro","gro"),
       (1,"wbd200-original",200,200,"gro","gro"),
       (2,"wbd200-priority",200,200,"gro","gro"),
       (3,"wbd150-priority",200,150,"gro","gro"),
       (4,"wbd200-restored",200,200,"gro","gro"),
       (5,"wbd150-restored",200,150,"gro","gro"),
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
    p=out/f"h2467-{role}-original-offload.json"
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

def priority_snapshot():
    pids=command("pidof","tailscaled")["stdout"].split()
    if len(pids)!=1:raise RuntimeError("expected one tailscaled")
    pid=int(pids[0]);values={}
    for entry in pathlib.Path("/proc",str(pid),"task").iterdir():
        tid=int(entry.name)
        try:values[str(tid)]=os.getpriority(os.PRIO_PROCESS,tid)
        except ProcessLookupError:continue
    if not values:raise RuntimeError("tailscaled threads unavailable")
    return {"pid":pid,"nice":values}

def priority(mode):
    assert mode in ("original","candidate","snapshot")
    before=priority_snapshot()
    if mode=="snapshot":return before
    path=ROOT/"h2442-out/h2467-priority-original.json"
    if not path.is_file():
        if set(before["nice"].values())!={0}:raise RuntimeError("original priority not uniformly zero")
        save(path,before)
    original=load(path)
    if before["pid"]!=original["pid"]:raise RuntimeError("tailscaled PID changed")
    target=-5 if mode=="candidate" else 0
    for tid,nice in before["nice"].items():
        if nice!=target:
            try:os.setpriority(os.PRIO_PROCESS,int(tid),target)
            except ProcessLookupError:continue
    after=priority_snapshot()
    if after["pid"]!=original["pid"] or set(after["nice"].values())!={target}:
        raise RuntimeError("priority readback mismatch")
    return after

def drop_reason_inventory():
    paths=("/sys/kernel/tracing/events/skb/kfree_skb/format","/sys/kernel/debug/tracing/events/skb/kfree_skb/format")
    return {p:root("cat",p) for p in paths}
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
    nice={tid:int(row["stat"].rsplit(") ",1)[1].split()[16]) for tid,row in files["threads"].items()}
    return {"pid":int(pid),"clock_ticks":os.sysconf("SC_CLK_TCK"),"files":files,"guest":host,"nice":nice}
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
    orig_sink=c.sink;clock={}
    def timed_sink(*a,**kw):
        clock["measure_start_unix"]=time.time()
        try:return orig_sink(*a,**kw)
        finally:clock["measure_end_unix"]=time.time()
    c.sink=timed_sink
    rows=[]
    def apply(wsl_mode,arm_mode):
        return {"client":json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__)),"profile","client",wsl_mode,timeout=90)),
                "relay":c.control("relay","/offload",{"mode":arm_mode}),
                "server":c.control("server","/offload",{"mode":arm_mode})}
    def q(mode):
        return json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__)),"queue",mode,timeout=30))
    def pr(mode):
        return json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__)),"priority",mode,timeout=30))
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
            clock.clear()
            record={"case":case,"label":label,"rate_mbps":rate,"added_rtt_ms":delay*2,"status":"INCOMPLETE"}
            try:
                record["offload"]=fixed_offload
                record["tun_before"]=q("original")
                record["priority_before"]=pr("candidate" if case in (2,3) else "original")
                record["effective_candidate"]=case in (2,3)
                record.update(c.case(case));record.update(clock)
                record["priority_after"]=pr("snapshot")
                if record["priority_before"]["pid"]!=record["priority_after"]["pid"] or set(record["priority_before"]["nice"].values())!=set(record["priority_after"]["nice"].values()):
                    raise RuntimeError("priority drift")
                record["kind"]="bare" if case<0 else "wbd"
                record["tun_after"]=q("snapshot")
                if record["tun_after"]["qlen"]!=record["tun_before"]["qlen"]:raise RuntimeError("TUN length drift")
            except Exception as e:
                record["status"]="INCOMPLETE"
                record["error"]=repr(e);record.update(clock)
            rows.append(record);summary()
            print("H2467_CASE "+json.dumps({k:v for k,v in record.items() if k!="offload"}),flush=True)
        if not all(r["status"]=="MEASURED_EXACT" for r in rows):raise SystemExit(2)
    finally:
        summary()
        try:save(out/"restore-priority.json",pr("original"))
        except Exception as e:save(out/"restore-priority.json",{"error":repr(e)})
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
        priority_expected=-5 if r["case"] in (2,3) else 0
        proc=[l for l in tun if l.get("process",{}).get("nice")]
        priority_ok=bool(len(proc)>=2 and all(set(l["process"]["nice"].values())=={priority_expected} for l in proc)
                         and all(set(r.get(k,{}).get("nice",{}).values())=={priority_expected} for k in ("priority_before","priority_after"))
                         and len({l["process"]["pid"] for l in proc}|{r.get(k,{}).get("pid") for k in ("priority_before","priority_after")})==1)
        # Aggregate runtime and runnable delay across threads present at both endpoints.
        schedule=None
        if len(proc)>=2:
            f,z=proc[0],proc[-1]
            dt=z["wall_unix"]-f["wall_unix"]
            ft=f["process"]["files"]["threads"];zt=z["process"]["files"]["threads"]
            runs=[];waits=[]
            for tid in ft.keys()&zt.keys():
                x=[int(v) for v in ft[tid]["schedstat"].split()];y=[int(v) for v in zt[tid]["schedstat"].split()]
                if len(x)>=2 and len(y)>=2 and y[0]>=x[0] and y[1]>=x[1]:
                    runs.append(y[0]-x[0]);waits.append(y[1]-x[1])
            if dt>0 and runs:schedule={"runtime_core_equiv":sum(runs)/1e9/dt,"runnable_wait_core_equiv":sum(waits)/1e9/dt,"matched_threads":len(runs),"seconds":dt}
        length_ok=bool(tun and all(l["tun"]["qlen"]==expected for l in tun)
                      and r.get("tun_before",{}).get("qlen")==r.get("tun_after",{}).get("qlen")==expected)
        rows.append({"case":r["case"],"label":r["label"],"rx_mbps":r.get("rx_mbps"),"receipt":r["status"],
                     "tun_delta":delta,"length_ok":length_ok,"queue_length":expected,
                     "priority_expected":priority_expected,"priority_ok":priority_ok,"schedule":schedule,"rate_mbps":r["rate_mbps"],
                     "candidate_changed":r.get("effective_candidate"),"kind":"bare" if r["case"]<0 else "wbd","path":checks,
                     "qualified":r["status"]=="MEASURED_EXACT" and length_ok and priority_ok and delta is not None and all(v["direct"] for v in checks.values())})
    result={"source_sha":s["source_sha"],"run_id":s["run_id"],"rows":rows,
            "all_cases_qualified":len(rows)==len(SPECS) and all(r["qualified"] for r in rows)}
    save("h2467-qualification.json",result);print("H2467_QUALIFICATION "+json.dumps(result),flush=True)
    if not result["all_cases_qualified"]:raise SystemExit(2)

if __name__=="__main__":
    action=sys.argv[1]
    if action=="priority":print(json.dumps(priority(sys.argv[2])))
    elif action=="queue":print(json.dumps(queue(sys.argv[2])))
    elif action=="drop-inventory":print(json.dumps(drop_reason_inventory()))
    elif action=="profile":print(json.dumps(profile(*sys.argv[2:])))
    elif action=="monitor":monitor(*sys.argv[2:])
    elif action=="server":server()
    elif action=="client":client()
    elif action=="qualify":qualify(sys.argv[2])
    else:raise ValueError(action)
