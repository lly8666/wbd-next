"""Real Windows client and Winsock application. WSL transports test routing only."""
import os,sys,time,json,pathlib,subprocess,socket,threading,hashlib
from m0_h2442_tcp import sink
from m0_h2455_segments import collect,windows_readers
H2455=os.environ.get("WBD_H2455_SEGMENTS")=="windows"
from m0_wl_native_resource_sampler import sample_windows_original_process
ROOT=pathlib.Path.cwd();OUT=ROOT/"h2475-out/client";OUT.mkdir(parents=True,exist_ok=True)
PEER=os.environ["WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4"]
HOST=os.environ["WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4"]
NETEM=OUT/"netem";NETEM.mkdir(exist_ok=True)
SERVER=ROOT/"h2475-out/server"
BIN=ROOT/"result/wl-public"
CASES=json.loads((ROOT/"tools/m0_h2442_matrix.json").read_text())
DIAG=os.environ.get("WBD_H2450_RX_DIAG")=="1"
if DIAG:
    CASES=[dict(CASES[0],isolate=iso,rcvbuf=buf) for iso,buf in [(False,0),(True,0),(True,16777216),(True,0),(False,0)]]
H2452=os.environ.get("WBD_H2452_RATE")
if H2452:
    target=int(H2452)
    assert target in (400,600)
    CASES=[dict(CASES[0],budget=target,rate=target,isolate=False,rcvbuf=b) for b in (0,67108864,67108864,0)]
DIRECT={-5:(0,0),-4:(200,0),-3:(200,67108864),-2:(200,67108864),-1:(200,0)} if H2452 else {-2:(0,0),-1:(200,0)}
SECONDS=60 if H2452 else 35
DIRECT_SECONDS=60 if H2452 else 25
H2453=os.environ.get("WBD_H2453_PACING")=="1"
DIRECT_RATES={}
if H2453:
    assert H2452
    rates=(250,400,600,250)
    CASES=[dict(CASES[0],budget=rate,rate=rate,isolate=False,rcvbuf=67108864) for rate in rates]
    DIRECT={-5:(0,0),**{i:(200,67108864) for i in (-4,-3,-2,-1)}}
    DIRECT_RATES=dict(zip((-4,-3,-2,-1),rates))
if os.environ.get("WBD_H2458_TARGETED")=="1":
    CASES=[dict(CASES[0],budget=rate,rate=rate,isolate=False,rcvbuf=67108864) for rate in (250,600,250)]
    DIRECT={-5:(0,0),-2:(200,67108864)}
    DIRECT_RATES={-2:600}

from m0_h2475_fixture import wpath,wsl,snapshot,shape as guest_shape
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def save(p,d):p.write_text(json.dumps(d,indent=2)+"\n")
def control(role,path,body=None):
    if role!="server":raise ValueError(role)
    code="import json,sys,http.client; c=http.client.HTTPConnection('127.0.0.1',18727,timeout=75); c.request('POST',sys.argv[1],sys.argv[2],{'X-H2228-Token':sys.argv[3]+'-local','Content-Type':'application/json'}); s=c.getresponse(); b=s.read(); assert s.status==200,(s.status,b[:500]);print(b.decode())"
    return json.loads(wsl("python3","-c",code,path,json.dumps(body or {}),os.environ["GITHUB_RUN_ID"],timeout=85))
def shape(loss,delay):
    assert loss==0 and delay in (0,200)
    return guest_shape(NETEM,delay)
def ps(code):
    p=subprocess.run(["pwsh","-NoProfile","-NonInteractive","-Command","$ErrorActionPreference='Stop'; "+code],capture_output=True,text=True,timeout=15)
    if p.returncode:raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()
def route_for(host):
    return json.loads(ps("Find-NetRoute -RemoteIPAddress '"+host+"' | Where-Object {$_.DestinationPrefix} | Select-Object -First 1 InterfaceIndex,InterfaceAlias,DestinationPrefix,NextHop,RouteMetric | ConvertTo-Json -Compress"))
def direct_peers():
    import ipaddress
    roles={role:read(ROOT/"h2228-peer"/(role+".json"))["tail_ip"] for role in ("relay","server")}
    for role,peer in roles.items():
        wsl("tailscale","ping","--c=5","--timeout=3s",peer,timeout=22)
    st=json.loads(wsl("tailscale","status","--json",timeout=8))
    out=[]
    for role,peer in roles.items():
        p=next(x for x in st["Peer"].values() if peer in x.get("TailscaleIPs",[]))
        endpoint=p.get("CurAddr","")
        if not endpoint:raise RuntimeError("no direct Tailscale endpoint for "+role)
        host=str(ipaddress.IPv4Address(endpoint.rsplit(":",1)[0]))
        out.append({"role":role,"endpoint":endpoint,"host":host,"route":route_for(host),"rx_bytes":p.get("RxBytes"),"tx_bytes":p.get("TxBytes")})
    return out
def pin_underlay(d,owned):
    r=route_for(PEER);save(d/"underlay-before.json",r)
    if r["InterfaceIndex"]!=int(os.environ["WBD_PLAN024_NATIVE_VERIFIED_IFINDEX"]):raise RuntimeError("WSL peer route mismatch")
    return r["InterfaceIndex"]
def check_underlay(d,expected):
    r=route_for(PEER);save(d/"underlay-after-apply.json",r)
    if r["InterfaceIndex"]!=expected:raise RuntimeError("WSL peer route changed")
def unpin_underlay(owned):
    for prefix,idx,hop in reversed(owned):
        ps(f"Remove-NetRoute -DestinationPrefix '{prefix}' -InterfaceIndex {idx} -NextHop '{hop}' -PolicyStore ActiveStore -Confirm:$false")
def add_fixture_route(prefix,idx,hop,owned):
    ps(f"New-NetRoute -DestinationPrefix '{prefix}' -InterfaceIndex {idx} -NextHop '{hop}' -RouteMetric 1 -PolicyStore ActiveStore | Out-Null")
    owned.append((prefix,idx,hop))
def isolate_background(d,physical,owned):
    # Diagnostic only: the two actual benchmark destinations still use the
    # original native Wintun. More-specific physical routes keep unrelated
    # hosted-runner traffic out of this isolated experiment.
    for host in ("192.0.2.2","10.66.0.1"):
        r=route_for(host)
        if r["InterfaceAlias"]!="WBDH2442":raise RuntimeError("benchmark destination not on Wintun before isolation")
        if r["DestinationPrefix"]!=host+"/32":
            add_fixture_route(host+"/32",int(r["InterfaceIndex"]),r["NextHop"],owned)
    for prefix in ("0.0.0.0/2","64.0.0.0/2","128.0.0.0/2","192.0.0.0/2"):
        add_fixture_route(prefix,int(physical["InterfaceIndex"]),physical["NextHop"],owned)
    check={h:route_for(h) for h in ("192.0.2.2","10.66.0.1","8.8.8.8")}
    save(d/"isolated-route-check.json",check)
    if any(check[h]["InterfaceAlias"]!="WBDH2442" for h in ("192.0.2.2","10.66.0.1")) or check["8.8.8.8"]["InterfaceIndex"]!=physical["InterfaceIndex"]:
        raise RuntimeError("fixture isolation route selection mismatch")
def sample_connected(d,workers):
    def sample_worker():
        t=time.monotonic()
        for delay in ((2,12,30,45) if os.environ.get("WBD_H2458_TARGETED")=="1" else (12,30,45) if H2452 else (12,22)):
            time.sleep(max(0,t+delay-time.monotonic()))
            try:
                if H2455:
                    row=collect(d,str(delay),windows_readers(ROOT,wsl,wpath,ps,control))
                    data=row["server"]["value"]
                else:data=control("server","/sample")
                save(d/("active-server-"+str(delay)+".json"),data)
                print("H2450_ACTIVE_SS "+json.dumps({"delay":delay,"ss":data.get("ss","")}),flush=True)
            except Exception as e:save(d/("active-server-"+str(delay)+".json"),{"error":repr(e)})
    worker=threading.Thread(target=sample_worker,daemon=True);workers.append(worker);worker.start()
def probe():
    t=time.monotonic()+55
    while time.monotonic()<t:
        try:c=socket.create_connection(("10.66.0.1",45901),timeout=2,source_address=("10.66.0.2",0));break
        except OSError:time.sleep(.2)
    else:raise RuntimeError("Windows TCP cold probe not connected")
    with c:
        c.settimeout(10);c.sendall(b"R");assert c.recv(1)==b"S";c.sendall(b"T");assert c.recv(1)==b"U"
def case(i):
    d=OUT/("case-"+str(i));d.mkdir(exist_ok=False)
    shape(0,0);control("server","/start",{"case":i})
    p=None;worker=None;event=threading.Event();f=None;owned=[];isolated=[];samples=[]
    result={"case":i,"status":"INCOMPLETE"}
    try:
        if i<0:
            delay,buf=DIRECT[i]
            if delay:shape(0,delay)
            access=HOST
            result.update(sink(PEER,5202,access,DIRECT_SECONDS,rcvbuf=buf,connected=(lambda:sample_connected(d,samples)) if H2452 else None))
            if H2452:result["added_rtt_ms"]=delay*2
            if H2453:result["direct_requested_pacing_mbps"]=DIRECT_RATES.get(i,0)
        else:
            c=CASES[i];prof=c["profile"]
            route=d/"route-key.hex";route.write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n")
            args=[str(BIN/"wbd-client-embedded.exe"),"--native-v4-product","--control-stdin","--server-ip",PEER,"--server-port","443","--source-port",str(41031+2*i),"--server-name","wbd-h2228.example.test","--route-key-hex-file",str(route),"--tls-ca-pem",str(SERVER/"cert.pem"),"--username","bench","--password","H2442-ONLY","--tunnel-id","102030405060708090a0b0c0d0e0f001","--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDH2442","--state-path",str(d/"owned-wal.json"),"--mtu","1160","--lanes","1","--fec-mode","fixed" if prof>=0 else "off","--fec-parity","4" if prof>=0 else "0","--fec.mode","fixed" if prof>=0 else "off","--fec.profile",["light","mild","medium","balanced","high","strong","maximum"][max(0,prof)],"--route-mode","all","--outer-repair","on"]
            physical=route_for("192.0.2.2") if DIAG else None
            expected=pin_underlay(d,owned)
            f=(d/"client.log").open("w");p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=f,stderr=subprocess.STDOUT,text=True,cwd=BIN)
            worker=threading.Thread(target=sample_windows_original_process,args=(p,d/"windows-cpu.jsonl",event),daemon=True);worker.start()
            t=time.monotonic()+30
            while "WBD_WINDOWS_CLIENT_READY" not in (d/"client.log").read_text(errors="replace"):
                if p.poll() is not None or time.monotonic()>t:raise RuntimeError("actual Windows native READY absent")
                time.sleep(.2)
            check_underlay(d,expected)
            if DIAG and c['isolate']:isolate_background(d,physical,isolated)
            probe()
            print("H2448_NATIVE_COLD_PROBE_PASS case="+str(i),flush=True)
            save(d/"shape.json",shape(c["loss"],200));time.sleep(1)
            origin_route=route_for("192.0.2.2")
            save(d/"origin-route.json",origin_route)
            print("H2449_ORIGIN_ROUTE "+json.dumps(origin_route),flush=True)
            result.update(sink("192.0.2.2",5400,"10.66.0.2",SECONDS,rcvbuf=c.get("rcvbuf",0),connected=(lambda:sample_connected(d,samples)) if DIAG or H2452 else None))
            result.update(c)
        result["status"]="RECEIVED" if result["end"]=="eof" else "INCOMPLETE"
    except Exception as e:result["error"]=repr(e)
    finally:
        try:
            save(d/"local-path-before-clear.json",{"links":json.loads(wsl("ip","-s","-j","link","show")),"qdisc":json.loads(wsl("tc","-s","-j","qdisc","show")),"ss":wsl("ss","-tinm")})
        except Exception as e:result["local_snapshot_error"]=repr(e)
        # Clean link before owned Stop, never kill as success.
        try:
            shape(0,0)
            for name in ("wl-n0-netem-before.json","wl-n0-netem-after.json","actual-netem-readback.json"):
                src=NETEM/name
                if src.exists():
                    (d/name).write_bytes(src.read_bytes());src.unlink()
        except Exception as e:result["shape_clear_error"]=repr(e)
        for sample in samples:sample.join(3)
        try:unpin_underlay(isolated)
        except Exception as e:result['isolation_cleanup_error']=repr(e)
        if p:
            if p.poll() is None:
                try:p.stdin.write("stop\n");p.stdin.flush();p.wait(25)
                except Exception:p.terminate();p.wait(8)
            event.set()
            if worker:worker.join(5)
            if f:f.close()
            cl=(d/"client.log").read_text(errors="replace")
            result.update(client_stop=p.returncode==0 and "WBD_WINDOWS_NATIVE_DISCONNECTED_V1" in cl,client_ready="WBD_WINDOWS_CLIENT_READY" in cl,client_panic="panicked at" in cl)
            (d/"route-key.hex").unlink(missing_ok=True)
        try:result["server"]=control("server","/stop")
        except Exception as e:result["server_error"]=repr(e)
        try:unpin_underlay(owned)
        except Exception as e:result["underlay_cleanup_error"]=repr(e)
        src=result.get("server",{}).get("source") or {}
        if not result.get("underlay_cleanup_error") and not result.get("isolation_cleanup_error") and result["status"]=="RECEIVED" and result.get("bytes")==src.get("bytes") and src.get("end")=="deadline" and (i<0 or (result.get("client_stop") and result.get("client_ready") and not result.get("client_panic") and result["server"].get("proxy_accept") and result["server"].get("proxy_pacing") and result["server"].get("stop") and not result["server"].get("panic"))):result["status"]="MEASURED_EXACT"
        else:result["status"]="INCOMPLETE"
        save(d/"result.json",result);print("H2442_CASE "+json.dumps(result),flush=True)
    return result
from m0_h2475_profile import cases,DIRECT,DIRECT_RATES,SECONDS,DIRECT_SECONDS,GUEST_PATH,clean,midpoint,drops,netem_active
CASES=cases(ROOT)
H2452=H2453=DIAG=False

def main():
    rows=[]
    global sink
    original_sink=sink
    clock={}
    def observed_sink(*args,**kw):
        clock["sink_before"]=snapshot()
        start=time.monotonic()
        stop=threading.Event()
        def active():
            if stop.wait(25):return
            try:
                clock["active_ss"]=wsl("ss","-tinm",timeout=10)
                clock["active_origin_ss"]=wsl("ip","netns","exec","h2442origin","ss","-tinm",timeout=10)
            except Exception as e:clock["active_sample_error"]=repr(e)
        thread=None
        prior=kw.get("connected")
        def connected():
            nonlocal thread
            clock["connect_elapsed_s"]=time.monotonic()-start
            clock["business_start_mono"]=time.monotonic()
            if prior:prior()
            thread=threading.Thread(target=active,daemon=True);thread.start()
        kw["connected"]=connected
        try:return original_sink(*args,**kw)
        finally:
            clock["business_end_mono"]=time.monotonic()
            stop.set()
            if thread:thread.join(25)
            clock["sink_after"]=snapshot()
    sink=observed_sink
    def cpu_summary(d,row):
        p=d/"windows-cpu.jsonl"
        if not p.is_file() or "business_start_mono" not in row:return None
        t=row["business_start_mono"];samples=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        samples=[x for x in samples if t+10<=x["monotonic_s"]<=t+55]
        if len(samples)<2:return None
        a,b=samples[0],samples[-1];dt=b["monotonic_s"]-a["monotonic_s"]
        if dt<=0:return None
        cpu=(b["cpu_total_s"]-a["cpu_total_s"])/dt
        return {"samples":len(samples),"core_equiv":cpu,"estimated_cpu_s_per_gib":cpu*8*2**30/(row["rx_mbps"]*1e6) if row.get("rx_mbps",0)>0 else None}

    import m0_h2470_probe as probe
    save(OUT/"cpu-probe.json",probe.run("windows"))
    save(OUT/"hardware.json",json.loads(ps("Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress")))
    save(OUT/"wsl-hardware.json",json.loads(wsl("lscpu","-J")))
    log=(OUT/"server-control.log").open("w")
    p=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--cd",wpath(ROOT),"--exec","env","GITHUB_SHA="+os.environ["GITHUB_SHA"],"GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],"RUNNER_TEMP=/tmp","PATH="+GUEST_PATH,"WBD_H2475_PEER="+PEER,"python3",wpath(ROOT/"tools/m0_h2475_local_server.py")],stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+45
        while "H2442_SERVER_CONTROL_READY" not in (OUT/"server-control.log").read_text(errors="replace"):
            if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError("local WSL server control not ready")
            time.sleep(.2)
        schedule=[-10,-11,0,1,2,3,4,5,-12]
        while schedule:
            i=schedule.pop(0)
            if i==4 and not clean(rows[-1]):
                print("H2475_SKIP_800_AFTER_NONCLEAN_600",flush=True);continue
            if i==5:
                extra=midpoint(rows)
                if extra is not None and not any(r['case']==extra for r in rows):
                    schedule.insert(0,i);i=extra
            clock.clear()
            before=json.loads(wsl("ip","-s","-j","link","show","dev","eth0"))[0]
            r=case(i)
            r.update(clock)
            r["business_drops"]=drops(clock.get("sink_before",{}),clock.get("sink_after",{}))
            r["netem_active"]=netem_active(clock.get("sink_before",{}),clock.get("sink_after",{}))
            r["steady_cpu"]=cpu_summary(OUT/("case-"+str(i)),r)
            after=json.loads(wsl("ip","-s","-j","link","show","dev","eth0"))[0]
            a,b=before.get("stats64",before.get("stats")),after.get("stats64",after.get("stats"))
            r["eth0_deltas"]={side:{k:b[side][k]-a[side][k] for k in ("dropped","errors","packets")} for side in ("rx","tx")}
            r["rate_mbps"]=DIRECT_RATES[i] if i<0 else CASES[i]["rate"]
            r["added_rtt_ms"]=2*DIRECT[i][0] if i<0 else 400
            r["kind"]="bare" if i<0 else "wbd"
            r["netem_drops"]=None
            if (OUT/("case-"+str(i))/"wl-n0-netem-after.json").is_file():
                n=read(OUT/("case-"+str(i))/"wl-n0-netem-after.json")
                r["netem_drops"]={dev:sum(q["drops"] for q in n[dev] if q.get("kind")=="netem") for dev in ("eth0","ifb")}
            r["clean_candidate"]=clean(r) if i>=0 else False
            rows.append(r)
            save(OUT/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"same_windows_runner":True,"server_os":"WSL2 Linux x86_64","native_windows_server":False,"streams":1,"rows":rows})
            print("H2475_LOCAL_CASE "+json.dumps(r),flush=True)
            if r.get("shape_clear_error") or (i>=0 and not r.get("client_stop")):raise RuntimeError("owned Stop or netem cleanup failed; no next case")
            if "sink_before" not in r or "sink_after" not in r:raise RuntimeError("business boundary missing; stop infrastructure failure")
            if i==-11 and (r.get("connect_elapsed_s",0)<.32 or not r["netem_active"]["both_used"]):
                raise RuntimeError("400ms bare TCP handshake or bidirectional netem traffic not demonstrated")
            if i>=0 and not r["netem_active"]["both_used"]:raise RuntimeError("actual bidirectional netem traffic not demonstrated")
        control("server","/finish")
        if p.wait(30)!=0:raise RuntimeError("local control exit")
        save(OUT/"h2475-windows-post-probe.json",probe.run("windows"))
        if not all(r["status"]=="MEASURED_EXACT" for r in rows):raise SystemExit(2)
    finally:
        try:shape(0,0)
        except Exception as e:print("H2475_NETEM_CLEANUP_ERROR",repr(e),flush=True)
        if p.poll() is None:
            try:control("server","/stop")
            except Exception:pass
            try:control("server","/finish");p.wait(30)
            except Exception:p.terminate();p.wait(10)
        log.close()
if __name__=="__main__":main()
