"""H2461: same Windows ingress, TCP MSS and independent-flow capacity discrimination."""
import concurrent.futures,http.client,http.server,json,os,pathlib,socket,struct,subprocess,sys,threading,time
import m0_h2459_zt as z
import m0_h2228_three_runner_relay as h
from m0_h2442_tcp import sink

OUT=z.OUT
APP=pathlib.Path(__file__).resolve()
PORT=5202
SECONDS=60
RATE=600
BUF=67108864
ROLE=None
CURRENT=None
SPECS={0:(1,0),1:(1,0),2:(1,560),3:(1,0),4:(4,0)}

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
        row={"processes":json.loads(p.stdout or "[]"),"rc":p.returncode}
        perf=subprocess.run(["pwsh","-NoProfile","-NonInteractive","-Command",
            "@(Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Select-Object Name,PercentProcessorTime,PercentDPCTime,PercentInterruptTime,PercentPrivilegedTime) | ConvertTo-Json -Compress"],capture_output=True,text=True,timeout=12)
        if perf.returncode==0:row["processor_perf"]=json.loads(perf.stdout or "[]")
        return row
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
    ss=subprocess.run(["ss","-tinm","sport",">=","5202","and","sport","<=","5205"],capture_output=True,text=True,timeout=5)
    return {"ticks_per_second":os.sysconf("SC_CLK_TCK"),"processes":rows,"ss":ss.stdout}

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

def tcp_source(host,port,rate,mss):
    with socket.socket() as l:
        l.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        if mss:l.setsockopt(socket.IPPROTO_TCP,socket.TCP_MAXSEG,mss)
        l.bind((host,port));l.listen(1);l.settimeout(90)
        print("SOURCE_READY",flush=True)
        c,_=l.accept()
        with c:
            c.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,b"bbr")
            cc=c.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,32).split(b"\0")[0].decode()
            assert cc=="bbr"
            c.setsockopt(socket.SOL_SOCKET,47,struct.pack("=Q",rate*125000))
            actual=struct.unpack("=Q",c.getsockopt(socket.SOL_SOCKET,47,8))[0]
            assert actual==rate*125000
            effective_mss=c.getsockopt(socket.IPPROTO_TCP,socket.TCP_MAXSEG)
            c.settimeout(15);assert c.recv(1)==b"R"
            c.settimeout(.5);b=bytes(256*1024);n=0;t=time.monotonic();end="deadline"
            while time.monotonic()-t<SECONDS:
                try:q=c.send(b)
                except socket.timeout:continue
                except OSError as e:end=repr(e);break
                if not q:end="zero";break
                n+=q
            try:c.shutdown(socket.SHUT_WR)
            except OSError as e:end=repr(e)
            print(json.dumps({"bytes":n,"end":end,"actual_cc":cc,"pacing_bytes_per_s":actual,"actual_mss":effective_mss,"requested_mss":mss,"port":port}),flush=True)

def local_source(case):
    global CURRENT
    assert CURRENT is None
    assert case in SPECS and (ROLE=="relay")== (case!=0)
    count,mss=SPECS[case]
    folder=OUT/("case-"+str(case));folder.mkdir(exist_ok=True)
    host=z.GW["client"] if ROLE=="relay" else z.LAN["server"]
    procs=[]
    CURRENT=(case,procs)
    for i in range(count):
        path=folder/("source-"+str(i)+".log");f=path.open("w")
        p=subprocess.Popen([sys.executable,str(APP),"source",host,str(PORT+i),str(RATE//count),str(mss)],stdout=f,stderr=subprocess.STDOUT)
        procs.append((p,f,path))
    end=time.monotonic()+15
    for p,f,path in procs:
        while "SOURCE_READY" not in path.read_text(errors="replace"):
            if p.poll() is not None or time.monotonic()>end:raise RuntimeError("source not ready: "+path.read_text(errors="replace")[-300:])
            time.sleep(.1)
    return {"case":case,"ready":True,"source":host,"streams":count,"requested_mss":mss}

def source_result():
    global CURRENT
    case,procs=CURRENT
    rows=[]
    for p,f,path in procs:
        p.wait(25);f.close()
        row=json.loads(path.read_text().splitlines()[-1]);row["rc"]=p.returncode;rows.append(row)
    CURRENT=None
    result={"case":case,"bytes":sum(x["bytes"] for x in rows),"end":"deadline" if all(x["end"]=="deadline" and x["rc"]==0 for x in rows) else "incomplete","flows":rows}
    save(OUT/("case-"+str(case))/"source-result.json",result)
    return result

def measured_sink(host,local,count=1):
    start=time.time()
    def flow(i):
        row=sink(host,PORT+i,local,SECONDS,rcvbuf=BUF)
        row["port"]=PORT+i
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
        rows=list(pool.map(flow,range(count)))
    return {"measure_start_unix":start,"measure_end_unix":time.time(),
            "bytes":sum(x["bytes"] for x in rows),"rx_mbps":sum(x["rx_mbps"] for x in rows),
            "end":"eof" if all(x["end"]=="eof" for x in rows) else "incomplete","flows":rows}

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
    # Fixed MTU 1200 throughout; MSS is per test socket only.
    specs=[(0,"server-to-relay-reference",0,"server"),(1,"windows-default-mss",0,"relay"),
           (2,"windows-mss560",0,"relay"),(3,"windows-default-mss-repeat",0,"relay"),
           (4,"windows-four-flows",0,"relay")]
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
                else:row.update(measured_sink(z.GW["client"],z.LAN["client"],SPECS[case][0]))
                row["source"]=request(source,"/source-result",{});started=False
                row["after"]={role:request(role,"/snapshot") for role in ("relay","server")}
                rxf={x["port"]:x for x in row.get("flows",[])}
                txf={x["port"]:x for x in row["source"].get("flows",[])}
                if row.get("end")=="eof" and row["source"].get("end")=="deadline" and len(rxf)==len(txf)==SPECS[case][0] and set(rxf)==set(txf) and all(rxf[k]["bytes"]==txf[k]["bytes"] for k in txf):
                    row["status"]="MEASURED_EXACT"
            except Exception as e:row["error"]=repr(e)
            finally:
                if started:
                    try:row["source"]=request(source,"/source-result",{})
                    except Exception as e:row["source_error"]=repr(e)
                try:request("relay","/impair",{"loss_pct":0,"delay_ms":0,"model":"iid"})
                except Exception as e:row["clear_error"]=repr(e)
                rows.append(row);save(folder/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"rows":rows})
                print("H2461_CASE "+json.dumps({k:v for k,v in row.items() if k not in ("before","after")}),flush=True)
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
        required={"server":["relay"],"relay":["server"]} if row["case"]==0 else {"client":["relay"],"relay":["client"]}
        verdict={}
        for role,peers in required.items():
            log=[x for x in pathlogs[role] if a is not None and b is not None and a-3<=x["wall_unix"]<=b+3]
            t=[x["wall_unix"] for x in log]
            verdict[role]={"samples":len(log),"direct":bool(t and t[0]<=a+2 and t[-1]>=b-2 and all(y-x<=4 for x,y in zip(t,t[1:])) and all(
                x.get("source_sha")==summary["source_sha"] and x.get("run_id")==summary["run_id"] and x.get("role")==role and
                all(x.get("public_direct",{}).get(peer) for peer in peers) for x in log))}
        results.append({"case":row["case"],"label":row["label"],"receipt":row["status"],"rx_mbps":row.get("rx_mbps"),"actual_mss":[f.get("actual_mss") for f in row.get("source",{}).get("flows",[])],"streams":SPECS[row["case"]][0],"paths":verdict,"qualified":row["status"]=="MEASURED_EXACT" and all(x["direct"] for x in verdict.values())})
    report={"source_sha":summary["source_sha"],"run_id":summary["run_id"],"rows":results,
            "all_cases_qualified":len(results)==5 and all(x["qualified"] for x in results),
            "scope":"bare TCP segment capacity, no product throughput claim; sampled direct paths only"}
    save("h2461-qualification.json",report);print(json.dumps(report),flush=True)
    if not report["all_cases_qualified"]:raise SystemExit(2)

def join(role):
    try:z.join(role)
    except Exception as e:
        status={"error":repr(e),"role":role}
        try:
            row=z.read(z.PEER/(role+".json"));n=z.z.api("/network/"+row["network_id"])
            status["network"]={k:n.get(k) for k in ("status","assignedAddresses","portDeviceName","mtu","id")}
        except Exception as nested:status["network_error"]=repr(nested)
        save(OUT/"join-failure.json",status)
        raise

if __name__=="__main__":
    if sys.argv[1]=="source":tcp_source(sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]))
    elif sys.argv[1]=="join":join(sys.argv[2])
    elif sys.argv[1]=="controller":controller(sys.argv[2])
    elif sys.argv[1]=="client":client()
    elif sys.argv[1]=="qualify":qualify(sys.argv[2])
    else:raise ValueError(sys.argv[1])
