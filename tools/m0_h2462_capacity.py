"""H2462 single TCP flow, zero injected loss, WSL2 Tailscale capacity A/B/A."""
import http.server,ipaddress,json,os,pathlib,re,subprocess,sys,threading,time
import m0_h2228_three_runner_relay as h

ROOT=pathlib.Path.cwd()
PEER=ROOT/"h2228-peer"
OUT=ROOT/"h2228-out"
SPECS=[(-10,"baseline-0ms",0,600,"baseline","baseline"),
       (-11,"baseline-400ms",200,600,"baseline","baseline"),
       (-12,"wsl-gro-400ms",200,600,"gro","baseline"),
       (-13,"baseline-repeat-400ms",200,600,"baseline","baseline"),
       (-14,"all-linux-gro-400ms",200,600,"gro","gro"),
       (-15,"all-linux-gro-300m",200,300,"gro","gro"),
       (-16,"baseline-final-400ms",200,600,"baseline","baseline")]
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
    p=out/f"h2462-{role}-original-offload.json"
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
    s.DIRECT={case:(delay,67108864) for case,_,delay,rate,_,_ in SPECS}
    s.DIRECT_RATES={case:rate for case,_,delay,rate,_,_ in SPECS}
    s.DIRECT_SECONDS=60
    # Only configure the existing bare TCP endpoint, no WBD, origin, or TLS setup.
    for k,v in (("net.ipv4.tcp_rmem","4096 87380 67108864"),("net.ipv4.tcp_wmem","4096 65536 67108864"),
                ("net.core.rmem_max","67108864"),("net.core.wmem_max","67108864")):
        h.ns(h.NODE,"sysctl","-qw",k+"="+v)
    h.ns(h.NODE,"tc","qdisc","replace","dev","wan0","root","fq")
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
            save(OUT/"server-ready.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"scope":"bare TCP only"})
            svc.serve_forever()
    finally:
        for key in list(s.procs):s.stop(key)

def client():
    import m0_h2442_windows_client as c
    c.DIRECT={case:(delay,67108864) for case,_,delay,rate,_,_ in SPECS}
    c.DIRECT_RATES={case:rate for case,_,delay,rate,_,_ in SPECS}
    c.DIRECT_SECONDS=60
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
    def summary():
        save(out/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
             "real_three_runner_l3_relay":True,"all_three_distinct_native_machines":True,"streams":1,
             "scope":"bare TCP, zero injected loss, no WBD","rows":rows})
    try:
        # Require the existing direct peers before measuring. No change to routes.
        save(out/"initial-direct-peers.json",c.direct_peers())
        save(out/"windows-offload-inventory.json",json.loads(c.ps("Get-NetAdapter | Select-Object Name,InterfaceIndex,LinkSpeed,Status | ConvertTo-Json -Compress")))
        for case,label,delay,rate,wsl_mode,arm_mode in SPECS:
            clock.clear()
            record={"case":case,"label":label,"rate_mbps":rate,"added_rtt_ms":delay*2,"status":"INCOMPLETE"}
            try:
                record["offload"]=apply(wsl_mode,arm_mode)
                record["effective_candidate"]=any(x["diff_from_baseline"] for x in record["offload"].values())
                record.update(c.case(case));record.update(clock)
            except Exception as e:record["error"]=repr(e);record.update(clock)
            rows.append(record);summary()
            print("H2462_CASE "+json.dumps({k:v for k,v in record.items() if k!="offload"}),flush=True)
        if not all(r["status"]=="MEASURED_EXACT" for r in rows):raise SystemExit(2)
    finally:
        summary()
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
        rows.append({"case":r["case"],"label":r["label"],"rx_mbps":r.get("rx_mbps"),"receipt":r["status"],
                     "candidate_changed":r.get("effective_candidate"),"path":checks,
                     "qualified":r["status"]=="MEASURED_EXACT" and all(v["direct"] for v in checks.values())})
    result={"source_sha":s["source_sha"],"run_id":s["run_id"],"rows":rows,
            "all_cases_qualified":len(rows)==len(SPECS) and all(r["qualified"] for r in rows)}
    save("h2462-qualification.json",result);print("H2462_QUALIFICATION "+json.dumps(result),flush=True)
    if not result["all_cases_qualified"]:raise SystemExit(2)

if __name__=="__main__":
    action=sys.argv[1]
    if action=="profile":print(json.dumps(profile(*sys.argv[2:])))
    elif action=="monitor":monitor(*sys.argv[2:])
    elif action=="server":server()
    elif action=="client":client()
    elif action=="qualify":qualify(sys.argv[2])
    else:raise ValueError(action)
