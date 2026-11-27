"""Real Windows client and Winsock application. WSL transports test routing only."""
import os,sys,time,json,pathlib,subprocess,socket,threading,hashlib
from m0_winxdp_pressure_tcp import client as pressure_client
from m0_winxdp_pressure_profile import CASES as PRESSURE_CASES,SECONDS as PRESSURE_SECONDS
from m0_h2455_segments import collect,windows_readers
H2455=os.environ.get("WBD_H2455_SEGMENTS")=="windows"
from m0_wl_native_resource_sampler import sample_windows_original_process
ROOT=pathlib.Path.cwd();OUT=ROOT/"h2476-out/client";OUT.mkdir(parents=True,exist_ok=True)
PEER=os.environ["WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4"]
HOST=os.environ["WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4"]
NETEM=OUT/"netem";NETEM.mkdir(exist_ok=True)
SERVER=ROOT/"h2476-out/server"
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
    if not delay:return guest_shape(NETEM,0)
    c=CASES[CURRENT]
    guest_shape(NETEM,200)
    for dev,handle in (("eth0","20:"),("ifbwlm0","10:")):
        args=["tc","qdisc","change","dev",dev,"root","handle",handle,"netem","delay",str(c["delay"])+"ms","loss",str(loss)+"%"]
        if c.get("correlation"):args.append(str(c["correlation"])+"%")
        wsl(*args,"limit","32768")
    row={d:wsl("tc","-s","qdisc","show","dev",d) for d in ("eth0","ifbwlm0")}
    save(NETEM/"pressure-qdisc.json",row)
    return {"loss_pct":loss,"delay_ms":c["delay"],"actual":row}
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
def exact_flows(a,b):
    try:
        return len(a["flows"])==len(b["flows"]) and all(x["sent"]==y["received"] and x["received"]==y["sent"] and x["tx_sha256"]==y["rx_sha256"] and x["rx_sha256"]==y["tx_sha256"] for x,y in zip(a["flows"],b["flows"]))
    except (KeyError,TypeError):return False
def case(i):
    d=OUT/("case-"+str(i));d.mkdir(exist_ok=False)
    shape(0,0);control("server","/start",{"case":i})
    p=None;worker=None;event=threading.Event();f=None;owned=[];isolated=[];samples=[]
    result={"case":i,"status":"INCOMPLETE",**CASES[i]}
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
            args=[str(BIN/"wbd-client-embedded.exe"),"--native-v4-product","--control-stdin","--server-ip",PEER,"--server-port","443","--source-port",str(41031+2*i),"--server-name","wbd-h2228.example.test","--route-key-hex-file",str(route),"--tls-ca-pem",str(SERVER/"cert.pem"),"--username","bench","--password","H2442-ONLY","--tunnel-id","102030405060708090a0b0c0d0e0f001","--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDH2442","--state-path",str(d/"owned-wal.json"),"--mtu",str(c["mtu"]),"--lanes","1","--fec-mode","fixed" if prof>=0 else "off","--fec-parity","4" if prof>=0 else "0","--fec.mode","fixed" if prof>=0 else "off","--fec.profile",["light","mild","medium","balanced","high","strong","maximum"][max(0,prof)],"--route-mode","all","--outer-repair","on"]
            physical=route_for("192.0.2.2") if c["isolate"] else None
            expected=pin_underlay(d,owned)
            f=(d/"client.log").open("w");p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=f,stderr=subprocess.STDOUT,text=True,cwd=BIN)
            worker=threading.Thread(target=sample_windows_original_process,args=(p,d/"windows-cpu.jsonl",event),daemon=True);worker.start()
            t=time.monotonic()+30
            while "WBD_WINDOWS_CLIENT_READY" not in (d/"client.log").read_text(errors="replace"):
                if p.poll() is not None or time.monotonic()>t:raise RuntimeError("actual Windows native READY absent")
                time.sleep(.2)
            check_underlay(d,expected)
            if c['isolate']:isolate_background(d,physical,isolated)
            probe()
            print("H2448_NATIVE_COLD_PROBE_PASS case="+str(i),flush=True)
            save(d/"shape.json",shape(c["loss"],c["delay"]));time.sleep(1)
            origin_route=route_for("192.0.2.2")
            save(d/"origin-route.json",origin_route)
            print("H2449_ORIGIN_ROUTE "+json.dumps(origin_route),flush=True)
            before=snapshot()
            business={}
            def connected():
                business["start"]=time.monotonic()
                def observe():
                    time.sleep(20)
                    try:save(d/"origin-tcp-steady.json",{"ss":wsl("ip","netns","exec","h2442origin","ss","-tinm","( sport = :5400 )")})
                    except Exception as e:save(d/"origin-tcp-steady.json",{"error":repr(e)})
                t=threading.Thread(target=observe,daemon=True);samples.append(t);t.start()
            result.update(pressure_client("192.0.2.2",5400,"10.66.0.2",SECONDS,c,connected))
            result["business_start_mono"]=business.get("start")
            print("WINXDP_TCP_BUSINESS_END case="+str(i)+" end="+str(result.get("end")),flush=True)
            after=snapshot()
            result["netem_packets"]={k:after["netem_packets"][k]-before["netem_packets"][k] for k in ("eth0","ifbwlm0")}
            result["kernel_counter_delta"]={k:v-before["counters"].get(k,v) for k,v in after["counters"].items()}
            save(d/"business-boundaries.json",{"before":before,"after":after})
            result.update(c)
        result["status"]="RECEIVED" if result["end"]=="eof" else "INCOMPLETE"
    except Exception as e:result["error"]=repr(e)
    finally:
        try:
            save(d/"local-path-before-clear.json",{"links":json.loads(wsl("ip","-s","-j","link","show")),"qdisc":json.loads(wsl("tc","-s","-j","qdisc","show")),"ss":wsl("ss","-tinm","( sport = :5400 or dport = :5400 or sport = :5202 or dport = :5202 )")})
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
        # Keep physical /2s through native Stop: do not reopen background routes.
        try:unpin_underlay([r for r in isolated if r[0].endswith('/32')])
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
        try:unpin_underlay([r for r in isolated if r[0].endswith("/2")])
        except Exception as e:result["isolation_cleanup_error"]=repr(e)
        try:result["server"]=control("server","/stop")
        except Exception as e:result["server_error"]=repr(e)
        try:unpin_underlay(owned)
        except Exception as e:result["underlay_cleanup_error"]=repr(e)
        src=result.get("server",{}).get("source") or {}
        if not result.get("underlay_cleanup_error") and not result.get("isolation_cleanup_error") and result["status"]=="RECEIVED" and result.get("bytes")==src.get("bytes") and src.get("end")=="deadline" and exact_flows(result,src) and (i<0 or (result.get("client_stop") and result.get("client_ready") and not result.get("client_panic") and result["server"].get("path_ok") and result["server"].get("pacing_ok") and result["server"].get("stop") and not result["server"].get("panic"))):result["status"]="MEASURED_EXACT"
        else:result["status"]="INCOMPLETE"
        save(d/"result.json",result)
    return result

import re
from m0_winxdp_ab_profile import GUEST_PATH
CASES=PRESSURE_CASES
SECONDS=PRESSURE_SECONDS
H2452=H2453=DIAG=False
CURRENT=0
def main():
    global CURRENT
    rows=[]
    log=(OUT/"server-control.log").open("w")
    p=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--cd",wpath(ROOT),"--exec","env","GITHUB_SHA="+os.environ["GITHUB_SHA"],"GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],"RUNNER_TEMP=/tmp","PATH="+GUEST_PATH,"WBD_H2476_PEER="+PEER,"WBD_XDP_PRESSURE_LAB="+os.environ.get("WBD_XDP_PRESSURE_LAB","0"),"WBD_XDP_PRESSURE_PATH="+os.environ.get("WBD_XDP_PRESSURE_PATH","bbr"),"WBD_XDP_STRESS_PHASE="+os.environ.get("WBD_XDP_STRESS_PHASE",""),"H2478_REPLICA="+os.environ["H2478_REPLICA"],"python3",wpath(ROOT/"tools/m0_winxdp_pressure_server.py")],stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+60
        while "H2442_SERVER_CONTROL_READY" not in (OUT/"server-control.log").read_text(errors="replace"):
            if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError("local server control not ready")
            time.sleep(.2)
        order=list(range(len(CASES)))
        if os.environ["H2478_REPLICA"] in "BDFHJL":order.reverse()
        if os.environ["H2478_REPLICA"]=="S":order=[0,1,4] if os.environ.get("WBD_XDP_STRESS_PHASE")=="upload" else [0,5] if os.environ.get("WBD_XDP_PRESSURE_LAB")=="1" else [0,2]
        abba=os.environ.get("WBD_XDP_STRESS_PHASE")=="carrier-abba"
        if abba:
            order=list(range(len(CASES)))
            if os.environ["H2478_REPLICA"] in "BDFHJL":
                order=[i for g in reversed(range(len(CASES)//4)) for i in range(4*g,4*g+4)]
            # S reproduces the previous duplex tail failure, even off 9V45.
            # Other replicas run only the H2480-style clean quartets.
            order=[i for i in order if (CASES[i]["group"]=="lossy-duplex")== (os.environ["H2478_REPLICA"]=="S")]
        for i in order:
            CURRENT=i
            if abba:
                import shutil
                arm=CASES[i]["arm"]
                base=ROOT/"carrier-ab"/arm
                m=read(base/"identity.json")
                for filename,key in (("wbd-client-embedded.exe","exe"),("wbd_engine.dll","dll")):
                    src=base/filename
                    assert hashlib.sha256(src.read_bytes()).hexdigest()==m[key]
                    shutil.copyfile(src,BIN/filename)
                    assert hashlib.sha256((BIN/filename).read_bytes()).hexdigest()==m[key]
                print("WINXDP_ABBA_IDENTITY "+json.dumps(dict(m,arm=arm,case=i)),flush=True)
            if os.environ.get("WBD_XDP_PRESSURE_LAB")=="1":
                c=CASES[i]
                for key,value in (("RX",c["rx_slots"]),("TX",c["tx_slots"]),("QUANTUM",c["quantum"]),("POLICY",c["policy"])):
                    os.environ["WBD_XDP_LAB_"+key]=str(value)
            print("WINXDP_PRESSURE_BEGIN "+json.dumps(CASES[i]),flush=True)
            r=case(i)
            d=OUT/("case-"+str(i))
            s=(d/"client.log").read_text(errors="replace") if (d/"client.log").exists() else ""
            def receipt(marker):
                ls=[l for l in s.splitlines() if marker in l]
                return {k:int(v) for k,v in re.findall(r"(\w+)=(\d+)",ls[-1])} if ls else {}
            r["tx"]=receipt("WBD_XDP_TX_STOP ")
            r["rx"]=receipt("WBD_XDP_RX_STOP ")
            r["rx_queues"]=[l for l in s.splitlines() if "WBD_XDP_RX_QUEUE_STOP " in l]
            r["server_rc"]=r.get("server",{}).get("rc")
            r["server_stop"]=r.get("server",{}).get("stop")
            r["server_path_ok"]=r.get("server",{}).get("path_ok")
            r["server_rx_mbps"]=((r.get("server",{}).get("source") or {}).get("rx_mbps"))
            r["flow_gaps_s"]=[f.get("max_rx_gap_s") for f in r.get("flows",[])]
            r["flow_tail"]={side:[{k:x.get(k) for k in ("sent","received","tx_end","rx_end","last_rx_elapsed_s","rx_eof_elapsed_s","tx_shutdown_elapsed_s","rx_after_business_bytes","errors")} for x in flows] for side,flows in (("windows",r.get("flows",[])),("linux",(r.get("server",{}).get("source") or {}).get("flows",[])))}
            r["socket_sendbufs"]=[f.get("socket_sndbuf") for f in r.get("flows",[])]
            r["socket_send_timeouts"]=[f.get("send_timeouts") for f in r.get("flows",[])]
            r["steady_process_cpu_cores"]=None
            if r.get("business_start_mono") and (d/"windows-cpu.jsonl").exists():
                try:
                    start=r["business_start_mono"]
                    cpu=[json.loads(l) for l in (d/"windows-cpu.jsonl").read_text().splitlines() if l.strip()]
                    cpu=[v for v in cpu if start+10<=v["monotonic_s"]<=start+SECONDS-5]
                    if len(cpu)>=2:
                        dt=cpu[-1]["monotonic_s"]-cpu[0]["monotonic_s"]
                        if dt>0:r["steady_process_cpu_cores"]=(cpu[-1]["cpu_total_s"]-cpu[0]["cpu_total_s"])/dt
                except Exception as e:r["cpu_sample_error"]=repr(e)
            r["tx_lab"]=receipt("WBD_XDP_TX_LAB ")
            r["rx_lab"]=[{k:int(v) for k,v in re.findall(r"(\w+)=(\d+)",l)} for l in s.splitlines() if "WBD_XDP_RX_LAB " in l]
            r["fec_receipts"]=[l for l in s.splitlines() if "WBD_WINDOWS_FEC2_INSTALLED" in l]
            r["fec_ok"]=r["profile"]<0 or any("mode=fec-fixed" in l and f"profile={r['profile']} " in l for l in r["fec_receipts"])
            r["loss_observed"]=sum(v for k,v in r.get("kernel_counter_delta",{}).items() if k.startswith("qdisc.") and "|netem|" in k)
            r["traffic_ok"]=(r["direction"]=="down" or r.get("sent",0)>0) and (r["direction"]=="up" or r.get("received",0)>0)
            r["lab_ok"]=os.environ.get("WBD_XDP_PRESSURE_LAB")!="1" or (r["tx_lab"].get("slots")==r["tx_slots"] and any(q.get("slots")==r["rx_slots"] and q.get("quantum")==r["quantum"] for q in r["rx_lab"]))
            r["fatal"]=[l[:300] for l in s.splitlines() if "WBD_XDP_TX_RING_FULL" in l or "worker rc=" in l or "WBD_XDP_TX_COMPLETION_NOTIFY_FAILED" in l]
            r["exact_hash"]=exact_flows(r,r.get("server",{}).get("source") or {})
            r["pressure_valid"]=r["status"]=="MEASURED_EXACT" and r["exact_hash"] and all(v>0 for v in r.get("netem_packets",{}).values()) and len(r.get("netem_packets",{}))==2 and r["tx"].get("invalid")==0 and r["rx"].get("truncated")==0 and not r["fatal"] and r["fec_ok"] and r["traffic_ok"] and r["lab_ok"] and (r["loss"]==0 or r["loss_observed"]>0)
            if abba:
                r["binary_identity"]=m
                if r["arm"]=="A":
                    r["carrier_ok"]=not any(marker in s for marker in ("WBD_XDP_TX_READY","WBD_XDP_RX_READY","WBD_XDP_TX_STOP","WBD_XDP_RX_STOP"))
                    r["pressure_valid"]=r["status"]=="MEASURED_EXACT" and r["exact_hash"] and r["carrier_ok"] and r["fec_ok"] and r["traffic_ok"] and len(r.get("netem_packets",{}))==2 and all(v>0 for v in r.get("netem_packets",{}).values()) and (r["loss"]==0 or r["loss_observed"]>0) and not r["fatal"]
                else:
                    r["carrier_ok"]="WBD_XDP_TX_READY" in s and "WBD_XDP_RX_READY" in s and r["tx"].get("published",0)>0 and r["tx"].get("published")==r["tx"].get("completed_before_close") and r["rx"].get("received",0)>0
                    r["pressure_valid"]=r["pressure_valid"] and r["carrier_ok"]
                goodput=(r.get("rx_mbps") or 0)+(r.get("server_rx_mbps") or 0)
                r["cpu_s_per_gib"]=r["steady_process_cpu_cores"]*8589.934592/goodput if goodput>0 and r["steady_process_cpu_cores"] is not None else None
            rows.append(r);save(d/"measurement.json",r)
            if abba:
                import statistics
                group=[v for v in rows if v["group"]==r["group"]]
                if len(group)==4:
                    pair={"group":r["group"],"sequence":"".join(v["arm"] for v in group),"valid":all(v["pressure_valid"] and v["cpu_s_per_gib"] is not None for v in group)}
                    for k in ("rx_mbps","server_rx_mbps","cpu_s_per_gib"):
                        for a in ("A","B"):
                            v=[x.get(k) for x in group if x["arm"]==a]
                            pair[a+"_"+k]=statistics.mean(v) if len(v)==2 and all(x is not None for x in v) else None
                        av,bv=pair["A_"+k],pair["B_"+k]
                        pair[k+"_delta_pct"]=100*(bv/av-1) if av and bv is not None else None
                    print("WINXDP_CARRIER_ABBA_PAIR "+json.dumps(pair),flush=True)
                    save(OUT/("pair-"+r["group"]+".json"),pair)
            save(OUT/"summary.json",{"tested_release":os.environ.get("WBD_XDP_TESTED_DLL_SHA","bceefcd096c9a4b0301db46184210834f75775db"),"fixture_sha":os.environ["GITHUB_SHA"],"replica":os.environ["H2478_REPLICA"],"rows":rows})
            print("WINXDP_PRESSURE_CASE "+json.dumps({k:r[k] for k in ("case","name","arm","group","carrier_ok","cpu_s_per_gib","binary_identity","direction","streams","rate","loss","profile","status","sent","received","rx_mbps","server_rx_mbps","flow_gaps_s","flow_tail","socket_sendbufs","socket_send_timeouts","steady_process_cpu_cores","server_rc","server_stop","server_path_ok","tx","rx","rx_queues","tx_lab","rx_lab","policy","fec_ok","traffic_ok","lab_ok","loss_observed","fatal","exact_hash","pressure_valid","kernel_counter_delta","error") if k in r}),flush=True)
            if r.get("shape_clear_error") or not r.get("client_stop") or not r.get("server_stop") or r.get("underlay_cleanup_error") or r.get("isolation_cleanup_error"):
                for pth in (SERVER/("case-"+str(i))/"server.log",SERVER/("case-"+str(i))/"source.log",d/"client.log"):
                    if pth.exists():
                        print("PRESSURE_FAILURE_TAIL "+str(pth),flush=True)
                        print("\n".join(l[:650] for l in pth.read_text(errors="replace").splitlines()[-12:]),flush=True)
                raise RuntimeError("owned cleanup failed; no next case")
        control("server","/finish")
        if p.wait(30)!=0:raise RuntimeError("local control exit")
        if len(rows)!=len(order) or not all(r["pressure_valid"] and (not abba or r["cpu_s_per_gib"] is not None) for r in rows):raise SystemExit(2)
    finally:
        try:shape(0,0)
        except Exception as e:print("PRESSURE_CLEANUP_ERROR",repr(e),flush=True)
        if p.poll() is None:
            try:control("server","/stop")
            except Exception:pass
            try:control("server","/finish");p.wait(30)
            except Exception:p.terminate();p.wait(10)
        log.close()
if __name__=="__main__":main()
