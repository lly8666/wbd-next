"""Real Windows client and Winsock application. WSL transports test routing only."""
import os,sys,time,json,pathlib,subprocess,socket,threading,hashlib
from m0_h2442_tcp import sink
from m0_wl_native_resource_sampler import sample_windows_original_process
ROOT=pathlib.Path.cwd();OUT=ROOT/"h2442-out";OUT.mkdir(exist_ok=True)
BIN=ROOT/"result/wl-public"
CASES=json.loads((ROOT/"tools/m0_h2442_matrix.json").read_text())
DIAG=os.environ.get("WBD_H2450_RX_DIAG")=="1"
if DIAG:
    CASES=[dict(CASES[0],isolate=iso,rcvbuf=buf) for iso,buf in [(False,0),(True,0),(True,16777216),(True,0),(False,0)]]
def wpath(p):
    p=p.resolve();return "/mnt/"+p.drive[0].lower()+"/"+"/".join(p.relative_to(p.anchor).parts)
def wsl(*a,timeout=30):
    p=subprocess.run(["wsl.exe","-d","Ubuntu","-u","root","--exec",*map(str,a)],capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError((p.stderr+p.stdout)[-600:])
    return p.stdout.strip()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def save(p,d):p.write_text(json.dumps(d,indent=2)+"\n")
def control(role,path,body=None):
    p=ROOT/"h2228-peer"/(role+".json")
    relay=ROOT/"h2228-peer/relay.json"
    # Reuse same authorized private control transport from the gateway.
    code="import json,sys,http.client; p=json.load(open(sys.argv[1])); r=json.load(open(sys.argv[2])); c=http.client.HTTPConnection(p['tail_ip'],18727,timeout=75); c.request('POST',sys.argv[3],sys.argv[4],{'X-H2228-Token':r['control_token'],'Content-Type':'application/json'}); s=c.getresponse(); b=s.read(); assert s.status==200,(s.status,b[:500]);print(b.decode())"
    return json.loads(wsl("python3","-c",code,wpath(p),wpath(relay),path,json.dumps(body or {}),timeout=85))
def shape(loss,delay):
    return control("relay","/impair",{"loss_pct":loss,"delay_ms":delay,"model":"iid"})
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
    rows=direct_peers()
    save(d/"underlay-before.json",rows)
    for row in rows:
        host=row["host"];r=row["route"];prefix=host+"/32"
        if r["DestinationPrefix"]==prefix:continue
        if r["InterfaceAlias"]=="WBDH2442":raise RuntimeError("underlay already captured before Apply")
        idx=int(r["InterfaceIndex"]);hop=r["NextHop"]
        ps(f"New-NetRoute -DestinationPrefix '{prefix}' -InterfaceIndex {idx} -NextHop '{hop}' -RouteMetric 1 -PolicyStore ActiveStore | Out-Null")
        owned.append((prefix,idx,hop))
    save(d/"underlay-pins.json",owned)
    rows=direct_peers()
    save(d/"underlay-pinned.json",rows)
    if any(r["route"]["DestinationPrefix"]!=r["host"]+"/32" for r in rows):raise RuntimeError("direct endpoint changed before Apply")
    return {r["role"]:r["route"]["InterfaceIndex"] for r in rows}
def check_underlay(d,expected):
    rows=direct_peers()
    save(d/"underlay-after-apply.json",rows)
    if any(r["route"]["InterfaceIndex"]!=expected[r["role"]] or r["route"]["DestinationPrefix"]!=r["host"]+"/32" for r in rows):
        raise RuntimeError("Tailscale direct endpoint not on pinned physical path after Apply")
    print("H2448_UNDERLAY_AFTER_APPLY "+json.dumps(rows),flush=True)
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
    def collect():
        t=time.monotonic()
        for delay in (12,22):
            time.sleep(max(0,t+delay-time.monotonic()))
            try:
                data=control("server","/sample")
                save(d/("active-server-"+str(delay)+".json"),data)
                print("H2450_ACTIVE_SS "+json.dumps({"delay":delay,"ss":data.get("ss","")}),flush=True)
            except Exception as e:save(d/("active-server-"+str(delay)+".json"),{"error":repr(e)})
    worker=threading.Thread(target=collect,daemon=True);workers.append(worker);worker.start()
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
            if i==-1:shape(0,200)
            access=read(ROOT/"h2228-peer/client.json")["windows_access_ip"]
            result.update(sink("10.248.82.2",5202,access,25))
        else:
            c=CASES[i];prof=c["profile"]
            route=d/"route-key.hex";route.write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n")
            args=[str(BIN/"wbd-client-embedded.exe"),"--native-v4-product","--control-stdin","--server-ip","10.248.82.2","--server-port","443","--source-port",str(41031+2*i),"--server-name","wbd-h2228.example.test","--route-key-hex-file",str(route),"--tls-ca-pem",str(ROOT/"h2228-server-ready/cert.pem"),"--username","bench","--password","H2442-ONLY","--tunnel-id","102030405060708090a0b0c0d0e0f001","--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDH2442","--state-path",str(d/"owned-wal.json"),"--mtu","1160","--lanes","1","--fec-mode","fixed" if prof>=0 else "off","--fec-parity","4" if prof>=0 else "0","--fec.mode","fixed" if prof>=0 else "off","--fec.profile",["light","mild","medium","balanced","high","strong","maximum"][max(0,prof)],"--route-mode","all","--outer-repair","on"]
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
            result.update(sink("192.0.2.2",5400,"10.66.0.2",35,rcvbuf=c.get("rcvbuf",0),connected=(lambda:sample_connected(d,samples)) if DIAG else None))
            result.update(c)
        result["status"]="RECEIVED" if result["end"]=="eof" else "INCOMPLETE"
    except Exception as e:result["error"]=repr(e)
    finally:
        # Clean link before owned Stop, never kill as success.
        try:shape(0,0)
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
def finish(rows,status):
    save(OUT/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"real_three_runner_l3_relay":True,"all_three_distinct_native_machines":True,"windows_native_client":True,"streams":1,"status":status,"rows":rows})
    control("server","/finish")
if __name__=="__main__":
    action=sys.argv[1]
    if action=="baseline":
        a=case(-2);b=case(-1);save(OUT/"baseline.json",[a,b])
    elif action=="smoke":
        base=read(OUT/"baseline.json")
        if base[0]["status"]!="MEASURED_EXACT" or base[0].get("rx_mbps",0)<285:
            # Still perform the clean native probe; do not interpret unqualified capacity as performance.
            x=case(0);save(OUT/"smoke.json",x)
            finish(base+[x],"INFRA_CAPACITY_UNQUALIFIED");raise SystemExit("direct routed capacity <285Mbps or incomplete")
        x=case(0);save(OUT/"smoke.json",x)
        if x["status"]!="MEASURED_EXACT":
            finish(base+[x],"NATIVE_SMOKE_FAILED");raise SystemExit(2)
    elif action=="matrix":
        base=read(OUT/"baseline.json");rows=[read(OUT/"smoke.json")]
        for i,c in enumerate(CASES[1:],1):
            if c["budget"]==600 and base[0].get("rx_mbps",0)<570:continue
            rows.append(case(i));save(OUT/"matrix-progress.json",rows)
        finish(base+rows,"MEASURED_ALL" if len(rows)==len(CASES) and all(r["status"]=="MEASURED_EXACT" for r in rows) else "PARTIAL_OR_CAPACITY_LIMITED")
