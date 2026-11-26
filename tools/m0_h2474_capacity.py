"""H2474 stable-load bare TCP and frozen native WBD comparisons."""
import concurrent.futures,http.server,ipaddress,json,os,pathlib,re,subprocess,sys,threading,time
import m0_h2228_three_runner_relay as h

ROOT=pathlib.Path.cwd()
PEER=ROOT/"h2228-peer"
OUT=ROOT/"h2228-out"
RATES=(125,)
SPECS=[(-10,"bare250-before",200,250,"gro","gro"),
       (0,"frozen125",200,125,"gro","gro"),
       (1,"old125",200,125,"gro","gro"),
       (2,"continue125",200,125,"gro","gro"),
       (3,"old125-restored",200,125,"gro","gro"),
       (-11,"bare250-after",200,250,"gro","gro")]
MODES={0:"frozen",1:"old",2:"continue",3:"old"}
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
    p=out/f"h2474-{role}-original-offload.json"
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
WSL_DEVS=("eth0","tailscale0","h228vc","h228bc")
def fixture_snapshot():
    def get(*args):
        r=command(*args)
        if r["rc"]:raise RuntimeError(repr(r))
        return r["stdout"]
    links={}
    for link in json.loads(get("ip","-s","-j","link","show")):
        name=link["ifname"]
        if name not in WSL_DEVS:continue
        stats=link.get("stats64",link.get("stats",{}))
        links[name]={side:{k:int(stats[side][k]) for k in ("dropped","errors")} for side in ("rx","tx")}
    if set(links)!=set(WSL_DEVS):raise RuntimeError("missing WSL path interface counters")
    qdiscs={}
    for q in json.loads(get("tc","-s","-j","qdisc","show")):
        if q.get("dev") not in WSL_DEVS:continue
        key="|".join(str(q.get(k,"")) for k in ("dev","kind","handle","parent","root"))
        if key in qdiscs:raise RuntimeError("duplicate qdisc identity")
        qdiscs[key]=int(q["drops"])
    if not all(any(k.startswith(d+"|") for k in qdiscs) for d in WSL_DEVS):
        raise RuntimeError("missing WSL path qdisc counters")
    softnet=[[int(v,16) for v in line.split()[:3]] for line in get("cat","/proc/net/softnet_stat").splitlines() if line.strip()]
    if not softnet or any(len(r)!=3 for r in softnet):raise RuntimeError("missing softnet counters")
    return {"links":links,"qdisc_drops":qdiscs,"softnet_drop":sum(r[1] for r in softnet),
            "softnet_time_squeeze":sum(r[2] for r in softnet)}

def drop_deltas(before,after):
    try:
        a,b=before["fixture"],after["fixture"]
        if set(a["links"])!=set(b["links"]) or set(a["links"])!=set(WSL_DEVS) or set(a["qdisc_drops"])!=set(b["qdisc_drops"]):
            raise ValueError("path counter set changed")
        values={}
        for dev in WSL_DEVS:
            for side in ("rx","tx"):
                for k in ("dropped","errors"):
                    values[f"{dev}.{side}.{k}"]=b["links"][dev][side][k]-a["links"][dev][side][k]
        for k in a["qdisc_drops"]:values["qdisc."+k]=b["qdisc_drops"][k]-a["qdisc_drops"][k]
        values["guest_softnet_drop"]=b["softnet_drop"]-a["softnet_drop"]
        if any(v<0 for v in values.values()):raise ValueError("counter reset")
        return {"available":True,"zero":not any(values.values()),"deltas":values,
                "softnet_time_squeeze_delta":b["softnet_time_squeeze"]-a["softnet_time_squeeze"]}
    except (KeyError,TypeError,ValueError) as e:return {"available":False,"zero":False,"error":repr(e)}

def phase_drops(row):
    pairs=(("setup","tun_before","sink_before"),("business","sink_before","sink_after"),
           ("teardown","sink_after","tun_after"),("whole_case","tun_before","tun_after"))
    phases={name:drop_deltas(row.get(a,{}),row.get(b,{})) for name,a,b in pairs}
    # Snapshot reads are not atomic, so do not infer precise per-packet times.
    if all(x["available"] for x in phases.values()):
        whole=phases["whole_case"]["deltas"]
        phases["consistent"]=all(sum(phases[n]["deltas"][k] for n in ("setup","business","teardown"))==v for k,v in whole.items())
    else:phases["consistent"]=False
    return phases

def queue(mode):
    assert mode in ("original","snapshot")
    row=tun_snapshot()
    if row["qlen"]!=500:raise RuntimeError("unexpected fixture TUN length: "+str(row["qlen"]))
    row["fixture"]=fixture_snapshot()
    row["eth0_driver_stats"]=command("ethtool","-S","eth0")
    row["snapshot_unix"]=time.time()
    return row
def hardware():
    return {"cpu":command("lscpu","-J"),"kernel":command("uname","-a"),
            "cpu_count":os.cpu_count(),"affinity":sorted(os.sched_getaffinity(0)),
            "scope":"guest-visible CPU identification, not physical host capacity"}
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
    save(pathlib.Path(path).with_name("h2474-"+role+"-hardware.json"),hardware())
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
                receipt=profile("server",body["mode"])
                raw=json.dumps(receipt).encode()
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
    import m0_h2470_probe as probe
    save(out/"h2474-windows-probe.json",probe.run("windows"))
    save(out/"h2474-wsl-probe.json",json.loads(c.wsl("env","GITHUB_SHA="+os.environ["GITHUB_SHA"],"GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],"python3",c.wpath(pathlib.Path(__file__).with_name("m0_h2470_probe.py")),"wsl",timeout=40)))
    # Keep the monitoring subprocess owned by the measuring Python process.
    mon=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--exec","env","GITHUB_SHA="+os.environ["GITHUB_SHA"],
        "GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],"python3",c.wpath(pathlib.Path(__file__)),"monitor","client",
        c.wpath(out/"tailscale-paths.jsonl"),c.wpath(stop)])
    import hashlib,shutil
    orig_sink=c.sink;clock={}
    dll=c.BIN/"wbd_engine.dll";frozen=out/"frozen-wbd_engine.dll"
    experimental=ROOT/"h2474-build/wbd_engine.dll"
    manifest=load(ROOT/"h2474-build/manifest.json")
    frozen_manifest=load(out/"windows-binary-manifest.json")
    def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(dll)!=frozen_manifest["sha256"]["dll"] or digest(experimental)!=manifest["dll_sha256"]:raise RuntimeError("DLL hash mismatch")
    shutil.copyfile(dll,frozen)
    def select(case):
        mode=MODES.get(case,"frozen")
        selected=frozen if mode=="frozen" else experimental
        shutil.copyfile(selected,dll)
        if digest(dll)!=digest(selected):raise RuntimeError("DLL copy mismatch")
        os.environ["WBD_H2474_RX_CONTINUE"]="1" if mode=="continue" else "0"
        return mode,digest(dll)
    def diagnostics(case,row):
        d=out/("case-"+str(case))
        log=(d/"client.log").read_text(errors="replace") if (d/"client.log").is_file() else ""
        mode=MODES[case]
        expected=1 if mode=="continue" else 0
        markers=re.findall(r"H2474_RX_MODE continuation=(\d+)",log)
        stats=re.findall(r"H2474_RX_TURN continuation=(\d+) waits=(\d+) timeouts=(\d+) turns=(\d+) full=(\d+) bypass=(\d+) bypass_empty=(\d+)",log)
        row["rx_mode_ok"]=(not markers and not stats) if mode=="frozen" else (markers==[str(expected)] and len(stats)==1 and int(stats[0][0])==expected)
        if stats:row["rx_turns"]=dict(zip(("continuation","waits","timeouts","turns","full","bypass","bypass_empty"),map(int,stats[-1])))
        path=d/"windows-cpu.jsonl"
        if path.is_file() and row.get("business_start_mono") is not None:
            a=row["business_start_mono"]
            samples=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
            samples=[x for x in samples if a+10<=x["monotonic_s"]<=a+55]
            if len(samples)>=2:
                f,z=samples[0],samples[-1];dt=z["monotonic_s"]-f["monotonic_s"]
                if dt>0:
                    cpu=z["cpu_total_s"]-f["cpu_total_s"]
                    row["steady_cpu"]={"samples":len(samples),"seconds":dt,"cpu_s":cpu,"core_equiv":cpu/dt,
                        "estimated_cpu_s_per_gib":cpu/dt*8*2**30/(row["rx_mbps"]*1e6) if row.get("rx_mbps",0)>0 else None}
    def clean_baseline(row):
        return row.get("status")=="MEASURED_EXACT" and row.get("rx_mode_ok") is True and row.get("wsl_phase_drops",{}).get("consistent") is True and row.get("wsl_phase_drops",{}).get("business",{}).get("zero") is True and isinstance(row.get("rx_mbps"),(int,float)) and row["rx_mbps"]>=106.25 and row.get("direct_after_case") is True
    def timed_sink(*a,**kw):
        # Pre-sink: product READY and cold probe completed, netem installed.
        # Post-sink: complete EOF/deadline, before shape clear and product Stop.
        clock["sink_before"]=q("snapshot")
        clock["measure_start_unix"]=time.time()
        prior=kw.get("connected")
        def connected():
            if prior:prior()
            clock["business_start_mono"]=time.monotonic()
        kw["connected"]=connected
        try:return orig_sink(*a,**kw)
        finally:
            clock["measure_end_unix"]=time.time()
            clock["sink_after"]=q("snapshot")
    # Avoid inherited 45s async sampling spilling into short sequential cases.
    # Existing preclear segment snapshots and continuous TUN monitoring remain.
    c.sample_connected=lambda d,workers:None
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
             "scope":"9V45 Windows RX continuation same-DLL A/B/A with frozen control; single TCP, zero injected loss, FEC off","rows":rows})
    try:
        # Require the existing direct peers before measuring. No change to routes.
        save(out/"initial-direct-peers.json",c.direct_peers())
        save(out/"windows-offload-inventory.json",json.loads(c.ps("Get-NetAdapter | Select-Object Name,InterfaceIndex,LinkSpeed,Status | ConvertTo-Json -Compress")))
        save(out/"windows-hardware.json",json.loads(c.ps("Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed | ConvertTo-Json -Compress")))
        fixed_offload=apply("gro","gro")
        for case,label,delay,rate,wsl_mode,arm_mode in SPECS:
            if case in (2,3) and not (len([r for r in rows if r["case"] in (0,1) and clean_baseline(r)])==2):
                rows.append({"case":case,"label":label,"rate_mbps":rate,"status":"SKIPPED_UNCLEAN_BASELINE","kind":"wbd"})
                summary();continue
            clock.clear()
            record={"case":case,"label":label,"rate_mbps":rate,"added_rtt_ms":delay*2,"status":"INCOMPLETE"}
            try:
                record["offload"]=fixed_offload
                record["tun_before"]=q("original")
                mode,sha=select(case)
                record.update(rx_mode=mode,dll_sha256=sha,effective_candidate=mode=="continue")
                record.update(c.case(case));record.update(clock)
                if case>=0:diagnostics(case,record)
                record["kind"]="bare" if case<0 else "wbd"
                record["tun_after"]=q("snapshot")
                if record["tun_after"]["qlen"]!=record["tun_before"]["qlen"]:raise RuntimeError("TUN length drift")
                record["wsl_case_drops"]=drop_deltas(record["tun_before"],record["tun_after"])
                record["wsl_phase_drops"]=phase_drops(record)
                if case in (0,1):
                    try:c.direct_peers();record["direct_after_case"]=True
                    except Exception as e:record["direct_after_case"]=False;record["direct_after_error"]=repr(e)
            except Exception as e:
                record["status"]="INCOMPLETE"
                record["error"]=repr(e);record.update(clock)
            rows.append(record);summary()
            print("H2474_CASE "+json.dumps({k:v for k,v in record.items() if k!="offload"}),flush=True)
        # High-rate incomplete outcomes are measurements, not infrastructure errors.
        # Preserve them; the separate qualification selects only repeated clean rates.
        if not any(r["case"]>=0 and r["status"]=="MEASURED_EXACT" for r in rows):raise SystemExit(2)
    finally:
        summary()
        try:shutil.copyfile(frozen,dll);save(out/"restore-dll.json",{"sha256":digest(dll),"expected":frozen_manifest["sha256"]["dll"]});frozen.unlink()
        except Exception as e:save(out/"restore-dll.json",{"error":repr(e)})
        try:save(out/"h2474-windows-post-probe.json",probe.run("windows"))
        except Exception as e:save(out/"h2474-windows-post-probe.json",{"error":repr(e)})
        try:save(out/"h2474-wsl-post-probe.json",json.loads(c.wsl("python3",c.wpath(pathlib.Path(__file__).with_name("m0_h2470_probe.py")),"wsl",timeout=40)))
        except Exception as e:save(out/"h2474-wsl-post-probe.json",{"error":repr(e)})
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
                     "wsl_case_drops":r.get("wsl_case_drops",{"available":False,"zero":False}),
                     "rate_mbps":r["rate_mbps"],
                     "wsl_phase_drops":r.get("wsl_phase_drops",{}),
                     "duration_s":60,"steady_window_s":[10,55],
                     "goodput_to_cap":r["rx_mbps"]/r["rate_mbps"] if isinstance(r.get("rx_mbps"),(float,int)) else None,
                     "rx_mode":r.get("rx_mode"),"dll_sha256":r.get("dll_sha256"),
                     "rx_mode_ok":r.get("rx_mode_ok"),"rx_turns":r.get("rx_turns"),"steady_cpu":r.get("steady_cpu"),
                     "candidate_changed":r.get("effective_candidate"),"kind":"bare" if r["case"]<0 else "wbd","path":checks,
                     "qualified":r["status"]=="MEASURED_EXACT" and length_ok and delta is not None and all(v["direct"] for v in checks.values())})
    # Require two independent same-run cases at a rate, not merely one favorable sample.
    bare=[r for r in rows if r["kind"]=="bare"]
    valid_bare=len(bare)==2 and all(r["qualified"] and isinstance(r["rx_mbps"],(float,int)) and r["rx_mbps"]>0 for r in bare)
    drift=(max(r["rx_mbps"] for r in bare)-min(r["rx_mbps"] for r in bare))/max(r["rx_mbps"] for r in bare) if valid_bare else None
    stable=bool(valid_bare and drift<=.10)
    wbd=[r for r in rows if r["kind"]=="wbd"]
    clean=lambda r: r["qualified"] and r["wsl_phase_drops"].get("consistent") and r["wsl_phase_drops"].get("business",{}).get("zero") and r["tun_delta"] is not None and r["tun_delta"]["tx_dropped"]==0 and r["rx_mode_ok"] is True and isinstance(r["goodput_to_cap"],(int,float)) and r["goodput_to_cap"]>=.85
    variants=[r for r in wbd if r["case"] in (1,2,3)]
    same_dll=len(variants)==3 and len({r["dll_sha256"] for r in variants})==1 and variants[0]["dll_sha256"] is not None
    comparison_ready=bool(stable and len(wbd)==4 and all(clean(r) for r in wbd) and same_dll and [r["rx_mode"] for r in variants]==["old","continue","old"] and variants[1]["rx_turns"] and variants[1]["rx_turns"]["bypass"]>0 and all(r["steady_cpu"] for r in variants))
    machine={}
    for name,role,file in (("windows","client","windows-hardware.json"),("wsl","client","h2474-client-hardware.json"),
                           ("relay","relay","h2474-relay-hardware.json"),("server","server","h2474-server-hardware.json")):
        path=folder/role/file
        machine[name]={"hardware":load(path) if path.is_file() else None}
        path=folder/role/("h2474-"+name+"-probe.json")
        machine[name]["probe"]=load(path) if path.is_file() else None
    result={"schema":"m0-machine-rate-observation-v1","source_sha":s["source_sha"],"run_id":s["run_id"],
            "fixture":"wsl2-tailscale-vxlan-gro-tun500","product_source":"db8f56e0d8094c6393dbbc2c8ab92d8db7a2c141",
            "probe_only":True,"classification":"9V45_OBSERVED","machine":machine,"rows":rows,
            "cpu_gate":load(folder/"client"/"cpu-gate.json"),
            "bare250_drift":drift,"stable_bare_controls":stable,
            "comparison_ready":comparison_ready,"same_experimental_dll":same_dll,
            "screen_status":"COMPARABLE" if comparison_ready else "NOT_COMPARABLE",
            "all_cases_qualified":len(rows)==len(SPECS) and all(r["qualified"] for r in rows)}
    save("h2474-qualification.json",result);print("H2474_QUALIFICATION "+json.dumps(result),flush=True)
    if not comparison_ready:raise SystemExit(2)

if __name__=="__main__":
    action=sys.argv[1]
    if action=="queue":print(json.dumps(queue(sys.argv[2])))
    elif action=="profile":print(json.dumps(profile(*sys.argv[2:])))
    elif action=="monitor":monitor(*sys.argv[2:])
    elif action=="server":server()
    elif action=="client":client()
    elif action=="qualify":qualify(sys.argv[2])
    else:raise ValueError(action)
