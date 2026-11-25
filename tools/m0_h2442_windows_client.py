"""Real Windows client and Winsock application. WSL transports test routing only."""
import os,sys,time,json,pathlib,subprocess,socket,threading,hashlib
from m0_h2442_tcp import sink
from m0_wl_native_resource_sampler import sample_windows_original_process
ROOT=pathlib.Path.cwd();OUT=ROOT/"h2442-out";OUT.mkdir(exist_ok=True)
BIN=ROOT/"result/wl-public"
CASES=json.loads((ROOT/"tools/m0_h2442_matrix.json").read_text())
def wpath(p):
    p=p.resolve();return "/mnt/"+p.drive[0].lower()+"/"+"/".join(p.relative_to(p.anchor).parts)
def wsl(*a,timeout=30):
    p=subprocess.run(["wsl.exe","-d","Ubuntu","-u","root","--",*map(str,a)],capture_output=True,text=True,timeout=timeout)
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
    p=None;worker=None;event=threading.Event();f=None
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
            f=(d/"client.log").open("w");p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=f,stderr=subprocess.STDOUT,text=True,cwd=BIN)
            worker=threading.Thread(target=sample_windows_original_process,args=(p,d/"windows-cpu.jsonl",event),daemon=True);worker.start()
            probe()
            t=time.monotonic()+30
            while "WBD_WINDOWS_CLIENT_READY" not in (d/"client.log").read_text(errors="replace"):
                if p.poll() is not None or time.monotonic()>t:raise RuntimeError("actual Windows native READY absent")
                time.sleep(.2)
            save(d/"shape.json",shape(c["loss"],200));time.sleep(1)
            result.update(sink("198.18.77.2",5400,"10.66.0.2",35))
            result.update(c)
        result["status"]="RECEIVED" if result["end"]=="eof" else "INCOMPLETE"
    except Exception as e:result["error"]=repr(e)
    finally:
        # Clean link before owned Stop, never kill as success.
        try:shape(0,0)
        except Exception as e:result["shape_clear_error"]=repr(e)
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
        src=result.get("server",{}).get("source") or {}
        if result["status"]=="RECEIVED" and result.get("bytes")==src.get("bytes") and src.get("end")=="deadline" and (i<0 or (result.get("client_stop") and result.get("client_ready") and not result.get("client_panic") and result["server"].get("proxy_accept") and result["server"].get("proxy_pacing") and result["server"].get("stop") and not result["server"].get("panic"))):result["status"]="MEASURED_EXACT"
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
            finish(base,"INFRA_CAPACITY_UNQUALIFIED");raise SystemExit("direct routed capacity <285Mbps or incomplete")
        x=case(0);save(OUT/"smoke.json",x)
        if x["status"]!="MEASURED_EXACT":
            finish(base+[x],"NATIVE_SMOKE_FAILED");raise SystemExit(2)
    elif action=="matrix":
        base=read(OUT/"baseline.json");rows=[read(OUT/"smoke.json")]
        for i,c in enumerate(CASES[1:],1):
            if c["budget"]==600 and base[0].get("rx_mbps",0)<570:continue
            rows.append(case(i));save(OUT/"matrix-progress.json",rows)
        finish(base+rows,"MEASURED_ALL" if len(rows)==len(CASES) and all(r["status"]=="MEASURED_EXACT" for r in rows) else "PARTIAL_OR_CAPACITY_LIMITED")
