"""H2455 native x86 Linux client with H2442 ARM server and relay."""
import hashlib,http.client,json,os,pathlib,subprocess,sys,time
import m0_h2228_three_runner_relay as h
from m0_h2442_tcp import sink
from m0_h2455_segments import collect,linux_snapshot
ROOT=pathlib.Path.cwd()
OUT=ROOT/"h2442-out"
BIN=ROOT/"linux-plan029-public-bundle"
NODE=h.NODE
RATES=(250,400,600,250)
SECONDS=60
def read(p):return json.loads(p.read_text())
def save(p,d):h.save(p,d)
def control(path,body=None):
    peer=read(ROOT/"h2228-peer/server.json")
    relay=read(ROOT/"h2228-peer/relay.json")
    c=http.client.HTTPConnection(peer["tail_ip"],18727,timeout=75)
    try:
        c.request("POST",path,json.dumps(body or {}),{"X-H2228-Token":relay["control_token"],"Content-Type":"application/json"})
        r=c.getresponse();raw=r.read()
        if r.status!=200:raise RuntimeError((r.status,raw[:300]))
        return json.loads(raw)
    finally:c.close()
def shape(delay):
    return h.remote(read(ROOT/"h2228-peer/relay.json"),"impair",loss=0,delay=delay,model="iid")
def readers():
    return {"server":lambda:control("/sample"),"relay":lambda:h.remote(read(ROOT/"h2228-peer/relay.json"),"snapshot"),"client_node":lambda:linux_snapshot(NODE),"client_host":lambda:linux_snapshot()}
def spawn(args,log):
    with log.open("w") as f:
        return subprocess.Popen(["sudo","-n","ip","netns","exec",NODE,*map(str,args)],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
def stop(p):
    if p and p.poll() is None:
        subprocess.run(["sudo","-n","kill","-TERM","--",str(-p.pid)],capture_output=True)
        try:p.wait(20)
        except subprocess.TimeoutExpired:
            subprocess.run(["sudo","-n","kill","-KILL","--",str(-p.pid)],capture_output=True);p.wait(5)
    return p.returncode if p else None
def waitmark(p,log,marker,seconds=45):
    end=time.monotonic()+seconds
    while marker not in log.read_text(errors="replace"):
        if p.poll() is not None or time.monotonic()>end:raise RuntimeError("missing "+marker+" in "+str(log))
        time.sleep(.2)
def probe():
    import socket
    t=time.monotonic()+55
    while time.monotonic()<t:
        try:c=socket.create_connection(("10.66.0.1",45901),timeout=2,source_address=("10.66.0.2",0));break
        except OSError:time.sleep(.2)
    else:raise RuntimeError("native probe absent")
    with c:
        c.settimeout(10);c.sendall(b"R");assert c.recv(1)==b"S";c.sendall(b"T");assert c.recv(1)==b"U"
def case(i):
    folder=OUT/("case-"+str(i));folder.mkdir()
    rate=0 if i==-5 else RATES[i+4] if i<0 else RATES[i]
    row={"case":i,"status":"INCOMPLETE","rate":rate,"added_rtt_ms":0 if i==-5 else 400}
    product=app=None;started=False
    route=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2455-route-"+str(i))
    try:
        shape(0);control("/start",{"case":i});started=True
        if i>=0:
            route.write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n");route.chmod(0o600)
            cmd=["env","LD_LIBRARY_PATH="+str(BIN),BIN/"wbd-v4-client","--raw-interface","wan0","--local-ip","10.248.81.2","--local-port",str(41031+2*i),"--peer-ip","10.248.82.2","--peer-port","443","--tun-name","wbdc0","--tun-ipv4","10.66.0.2/32","--tunnel-id","102030405060708090a0b0c0d0e0f001","--server-name","wbd-h2228.example.test","--route-key-hex-file",route,"--tls-ca-pem",ROOT/"h2228-server-ready/cert.pem","--tls-verify-server","--username","bench","--password","H2442-ONLY","--mode","normal","--outer-repair","on","--outer-mtu","1160","--tun-fq-maxrate-mbps","0"]
            product=spawn(cmd,folder/"client.log")
            waitmark(product,folder/"client.log","V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client")
            for dest in ("10.66.0.1","192.0.2.2"):
                h.ns(NODE,"ip","route","replace",dest+"/32","dev","wbdc0")
            h.ns(NODE,"tc","qdisc","replace","dev","wbdc0","root","fq","flow_limit","256")
            h.ns(NODE,sys.executable,str(pathlib.Path(__file__).resolve()),"probe",timeout=70)
            save(folder/"origin-route.json",{"route":h.ns(NODE,"ip","route","get","192.0.2.2").stdout})
            host,port,local="192.0.2.2",5400,"10.66.0.2"
        else:host,port,local="10.248.82.2",5202,"10.248.81.2"
        save(folder/"shape.json",shape(0 if i==-5 else 200))
        if i>=0:time.sleep(1)
        app=spawn([sys.executable,str(pathlib.Path(__file__).resolve()),"sink",host,str(port),local,str(0 if i==-5 else 67108864)],folder/"sink.log")
        waitmark(app,folder/"sink.log","H2455_CONNECTED")
        t=time.monotonic()
        for offset in (12,30,45):
            time.sleep(max(0,t+offset-time.monotonic()))
            if app.poll() is not None:break
            collect(folder,str(offset),readers())
        app.wait(max(1,t+150-time.monotonic()))
        if app.returncode:raise RuntimeError("sink failed")
        row.update(json.loads((folder/"sink.log").read_text().splitlines()[-1]))
        if row["end"]=="eof":row["status"]="RECEIVED"
    except Exception as e:row["error"]=repr(e)
    finally:
        if started:collect(folder,"preclear",readers())
        try:shape(0)
        except Exception as e:row["shape_clear_error"]=repr(e)
        stop(app)
        if product:
            rc=stop(product)
            log=(folder/"client.log").read_text(errors="replace")
            row.update(client_stop=rc==0 and ("V4_PUBLIC_NATIVE_STOP_DRAINED role=client" in log or "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client" in log),client_ready=log.count("V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client")==1,client_panic="panicked at" in log)
        route.unlink(missing_ok=True)
        if started:
            try:row["server"]=control("/stop")
            except Exception as e:row["server_error"]=repr(e)
        server=row.get("server",{});source=server.get("source") or {}
        if row["status"]=="RECEIVED" and row.get("bytes")==source.get("bytes") and source.get("end")=="deadline" and (i<0 or (row.get("client_ready") and row.get("client_stop") and not row.get("client_panic") and server.get("proxy_accept") and server.get("proxy_pacing") and server.get("stop") and not server.get("panic"))):row["status"]="MEASURED_EXACT"
        else:row["status"]="INCOMPLETE"
        save(folder/"result.json",row);print("H2442_CASE "+json.dumps(row),flush=True)
    return row
def main():
    OUT.mkdir(exist_ok=True)
    rows=[]
    for i in range(-5,4):
        rows.append(case(i))
        save(OUT/"progress.json",rows)
    complete=all(x["status"]=="MEASURED_EXACT" for x in rows)
    save(OUT/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"real_three_runner_l3_relay":True,"all_three_distinct_native_machines":True,"linux_native_client":True,"streams":1,"status":"PACING_DIAGNOSTIC_COMPLETE" if complete else "PACING_DIAGNOSTIC_INCOMPLETE","rows":rows})
    control("/finish")
    if not complete:raise SystemExit(2)
if __name__=="__main__":
    if sys.argv[1]=="probe":probe()
    elif sys.argv[1]=="sink":
        _,_,host,port,local,buf=sys.argv
        sink(host,int(port),local,SECONDS,rcvbuf=int(buf),connected=lambda:print("H2455_CONNECTED",flush=True))
    else:main()
