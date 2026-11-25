"""H2460 native ZeroTier capacity decomposition, bare TCP only."""
import http.client,http.server,json,os,pathlib,subprocess,sys,threading,time
import m0_h2459_zt as z
import m0_h2228_three_runner_relay as h
from m0_h2442_tcp import sink

OUT=z.OUT
APP=pathlib.Path(__file__).with_name("m0_h2442_tcp.py").resolve()
PORT=5202
SECONDS=60
RATE=600
BUF=67108864
ROLE=None
CURRENT=None

def save(p,obj):z.save(p,obj)
def tune():
    h.root("modprobe","tcp_bbr",allow_fail=True)
    for k,v in (("net.ipv4.tcp_congestion_control","bbr"),
                ("net.ipv4.tcp_rmem","4096 87380 67108864"),
                ("net.ipv4.tcp_wmem","4096 65536 67108864"),
                ("net.core.rmem_max","67108864"),("net.core.wmem_max","67108864")):
        h.root("sysctl","-qw",k+"="+v)

def cpu_sample():
    if os.name=="nt":
        cmd=["pwsh","-NoProfile","-NonInteractive","-Command",
             "$p=Get-Process | Where-Object {$_.ProcessName -like 'zerotier*'}; @($p | ForEach-Object { @{pid=$_.Id; name=$_.ProcessName; cpu_s=$_.CPU; threads=@($_.Threads | ForEach-Object {@{id=$_.Id; cpu_s=$_.TotalProcessorTime.TotalSeconds}})} }) | ConvertTo-Json -Depth 6 -Compress"]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=12)
        return {"processes":json.loads(p.stdout or "[]"),"rc":p.returncode}
    p=subprocess.run(["pidof","zerotier-one"],capture_output=True,text=True,timeout=5)
    rows=[]
    for pid in p.stdout.split():
        tasks=[]
        for path in pathlib.Path("/proc",pid,"task").glob("*/stat"):
            try:
                s=path.read_text();pos=s.rindex(")");v=s[pos+2:].split()
                tasks.append({"tid":int(path.parent.name),"name":s[s.index("(")+1:pos],"ticks":int(v[11])+int(v[12])})
            except (OSError,ValueError,IndexError):continue
        rows.append({"pid":int(pid),"tasks":tasks})
    return {"ticks_per_second":os.sysconf("SC_CLK_TCK"),"processes":rows}

def cpu_monitor(folder,stop):
    with (folder/"zt-cpu.jsonl").open("w",encoding="utf-8",buffering=1) as f:
        while not stop.exists():
            t=time.time();row={"wall_unix":t}
            try:row.update(cpu_sample())
            except Exception as e:row["error"]=repr(e)
            f.write(json.dumps(row)+"\n")
            time.sleep(max(0,5-(time.time()-t)))

def start_monitors(role,folder):
    stop=folder/"monitor-stop"
    threads=[threading.Thread(target=z.monitor,args=(role,folder/"zt-paths.jsonl",stop),daemon=True),
             threading.Thread(target=cpu_monitor,args=(folder,stop),daemon=True)]
    for t in threads:t.start()
    return stop,threads

def stop_monitors(stop,threads):
    stop.touch()
    for t in threads:t.join(8)

def local_source(case):
    global CURRENT
    assert CURRENT is None
    assert case in (0,1,2,3,4) and (ROLE=="relay")== (case in (1,4))
    folder=OUT/("case-"+str(case));folder.mkdir(exist_ok=True)
    path=folder/"source.log";f=path.open("w")
    host=z.GW["client"] if ROLE=="relay" else z.LAN["server"]
    p=subprocess.Popen([sys.executable,str(APP),"source",host,str(PORT),str(RATE),"bbr",str(SECONDS)],stdout=f,stderr=subprocess.STDOUT)
    CURRENT=(p,f,path,case)
    end=time.monotonic()+15
    while "SOURCE_READY" not in path.read_text(errors="replace"):
        if p.poll() is not None or time.monotonic()>end:raise RuntimeError("source not ready: "+path.read_text(errors="replace")[-300:])
        time.sleep(.1)
    return {"case":case,"ready":True,"source":host}

def source_result():
    global CURRENT
    p,f,path,case=CURRENT
    p.wait(25);f.close();CURRENT=None
    row=json.loads(path.read_text().splitlines()[-1]);row["rc"]=p.returncode;row["case"]=case
    save(path.parent/"source-result.json",row)
    return row

def measured_sink(host,local):
    start=time.time()
    result=sink(host,PORT,local,SECONDS,rcvbuf=BUF)
    result.update(measure_start_unix=start,measure_end_unix=time.time())
    return result

class Control(h.Control):
    def do_POST(self):
        if self.path=="/impair" and ROLE=="relay":return super().do_POST()
        if not self.authorized():self.send_error(403);return
        try:
            body=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path=="/source":result=local_source(int(body["case"]))
            elif self.path=="/source-result":result=source_result()
            elif self.path=="/sink" and ROLE=="relay":
                assert body=={"case":0}
                result=measured_sink(z.LAN["server"],z.GW["server"])
                save(OUT/"case-0-sink.json",result)
            else:raise ValueError("path")
            self.result(result)
        except Exception as e:
            self.send_error(500,repr(e)[:350])
    def do_GET(self):
        if not self.authorized():self.send_error(403);return
        if self.path=="/health":self.result({"role":ROLE,"ready":True})
        elif self.path=="/snapshot":
            value={"links":z.linux_snapshot(),"ss":h.root("ss","-tinm").stdout}
            if ROLE=="relay":value["relay"]=h.local_relay_snapshot("capacity")
            self.result(value)
        else:self.send_error(404)

def controller(role):
    global ROLE
    ROLE=role
    cfg=z.read(OUT/"zt-local.json")
    tune()
    if role=="relay":
        h.RDEV=cfg["devices"]
        def relay_ns(_name,*args,**kw):
            return h.root(*(h.RDEV["client"] if a=="rcli0" else a for a in args),**kw)
        h.ns=relay_ns
        def snapshot(tag):
            return {r:{"qdisc":json.loads(h.root("tc","-s","-j","qdisc","show","dev",d).stdout),
                       "link":json.loads(h.root("ip","-s","-j","link","show","dev",d).stdout)}
                    for r,d in h.RDEV.items()}
        h.local_relay_snapshot=snapshot
        h.impair(0,0,"iid")
        host=z.GW["client"]
    else:
        h.root("tc","qdisc","replace","dev",cfg["device"],"root","fq")
        host=z.LAN["server"]
    Control.client_ip=z.LAN["client"]
    Control.token=z.read(z.PEER/"relay.json")["control_token"]
    # Linux path monitoring is started by the existing root-owned fixture step.
    stop=OUT/"monitor-stop"
    thread=threading.Thread(target=cpu_monitor,args=(OUT,stop),daemon=True);thread.start()
    with http.server.ThreadingHTTPServer((host,18727),Control) as service:
        save(OUT/(role+"-ready.json"),{"role":role,"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"host":host})
        service.serve_forever()

def request(role,path,body=None):
    peer=z.read(z.PEER/(role+".json")); relay=z.read(z.PEER/"relay.json")
    conn=http.client.HTTPConnection(peer["control_ip"],18727,timeout=165,source_address=(z.LAN["client"],0))
    try:
        conn.request("GET" if body is None else "POST",path,None if body is None else json.dumps(body),
                     {"X-H2228-Token":relay["control_token"],"Content-Type":"application/json"})
        resp=conn.getresponse();raw=resp.read()
        assert resp.status==200,(resp.status,raw[:350])
        return json.loads(raw)
    finally:conn.close()

def client():
    folder=pathlib.Path("h2442-out");folder.mkdir(exist_ok=True)
    stop,threads=start_monitors("client",folder)
    rows=[]
    # The two single-hop tests and both routed tests use the same socket
    # options, 600M source cap, 60s duration and 1200-byte interface MTU.
    specs=[(0,"server-to-relay",0,"server"),(1,"relay-to-windows",0,"relay"),
           (2,"server-via-relay-to-windows",0,"server"),
           (3,"server-via-relay-to-windows",200,"server"),
           (4,"relay-to-windows-repeat",0,"relay")]
    try:
        request("relay","/health");request("server","/health")
        time.sleep(3)
        for case,label,delay,source in specs:
            row={"case":case,"label":label,"added_rtt_ms":delay*2,"rate_mbps":RATE,"status":"INCOMPLETE"}
            started=False
            try:
                request("relay","/impair",{"loss_pct":0,"delay_ms":delay,"model":"iid"})
                row["before"]={role:request(role,"/snapshot") for role in ("relay","server")}
                request(source,"/source",{"case":case});started=True
                if case==0:row.update(request("relay","/sink",{"case":0}))
                else:row.update(measured_sink(z.GW["client"] if source=="relay" else z.LAN["server"],z.LAN["client"]))
                row["source"]=request(source,"/source-result",{});started=False
                row["after"]={role:request(role,"/snapshot") for role in ("relay","server")}
                if row.get("end")=="eof" and row["source"].get("end")=="deadline" and row.get("bytes")==row["source"].get("bytes"):
                    row["status"]="MEASURED_EXACT"
            except Exception as e:row["error"]=repr(e)
            finally:
                if started:
                    try:row["source"]=request(source,"/source-result",{})
                    except Exception as e:row["source_error"]=repr(e)
                try:request("relay","/impair",{"loss_pct":0,"delay_ms":0,"model":"iid"})
                except Exception as e:row["clear_error"]=repr(e)
                rows.append(row);save(folder/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"rows":rows})
                print("H2460_CASE "+json.dumps({k:v for k,v in row.items() if k not in ("before","after")}),flush=True)
        if len(rows)!=5 or not all(r["status"]=="MEASURED_EXACT" for r in rows):raise SystemExit(2)
    finally:stop_monitors(stop,threads)

def qualify(folder):
    folder=pathlib.Path(folder);summary=z.read(folder/"client"/"summary.json")
    assert summary["source_sha"]==os.environ["GITHUB_SHA"] and summary["run_id"]==os.environ["GITHUB_RUN_ID"]
    pathlogs={}
    for role in z.ROLES:
        p=folder/role/"zt-paths.jsonl"
        pathlogs[role]=[json.loads(x) for x in p.read_text().splitlines()] if p.is_file() else []
    results=[]
    for row in summary["rows"]:
        a,b=row.get("measure_start_unix"),row.get("measure_end_unix")
        required={"server":["relay"],"relay":["server"]} if row["case"]==0 else {"client":["relay"],"relay":["client"]} if row["case"] in (1,4) else {"client":["relay"],"relay":["client","server"],"server":["relay"]}
        verdict={}
        for role,peers in required.items():
            log=[x for x in pathlogs[role] if a is not None and b is not None and a-3<=x["wall_unix"]<=b+3]
            t=[x["wall_unix"] for x in log]
            verdict[role]={"samples":len(log),"direct":bool(t and t[0]<=a+2 and t[-1]>=b-2 and all(y-x<=4 for x,y in zip(t,t[1:])) and all(
                x.get("source_sha")==summary["source_sha"] and x.get("run_id")==summary["run_id"] and x.get("role")==role and
                all(x.get("public_direct",{}).get(peer) for peer in peers) for x in log))}
        results.append({"case":row["case"],"label":row["label"],"receipt":row["status"],"rx_mbps":row.get("rx_mbps"),"paths":verdict,"qualified":row["status"]=="MEASURED_EXACT" and all(x["direct"] for x in verdict.values())})
    report={"source_sha":summary["source_sha"],"run_id":summary["run_id"],"rows":results,
            "all_cases_qualified":len(results)==5 and all(x["qualified"] for x in results),
            "scope":"bare TCP segment capacity, no product throughput claim; sampled direct paths only"}
    save("h2460-qualification.json",report);print(json.dumps(report),flush=True)
    if not report["all_cases_qualified"]:raise SystemExit(2)

if __name__=="__main__":
    if sys.argv[1]=="controller":controller(sys.argv[2])
    elif sys.argv[1]=="client":client()
    elif sys.argv[1]=="qualify":qualify(sys.argv[2])
    else:raise ValueError(sys.argv[1])
