"""ARM server: source-locked preset case control, no arbitrary command endpoint."""
import os,sys,json,pathlib,subprocess,time,signal,http.server,threading,hashlib
import m0_h2228_three_runner_relay as h
from m0_h2455_segments import linux_snapshot
ROOT=pathlib.Path.cwd();OUT=ROOT/"h2473-out/server";OUT.mkdir(parents=True,exist_ok=True)
PEER=os.environ["WBD_H2473_PEER"]
original_ns=h.ns
def local_ns(name,*args,**kw):
    if name==h.NODE:return h.root(*args,**kw)
    return original_ns(name,*args,**kw)
h.ns=local_ns
TMP=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2442-"+os.environ["GITHUB_RUN_ID"]);TMP.mkdir(exist_ok=True)
BUNDLE=ROOT/"linux-plan029-public-bundle";APP=ROOT/"tools/m0_h2442_tcp.py"
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

CASES=[dict(CASES[0],budget=rate,rate=rate,loss=0,profile=-1,isolate=False,rcvbuf=67108864) for rate in (125,200,400,600,125)]
DIRECT={-10:(0,67108864),-11:(200,67108864),-12:(200,67108864)}
DIRECT_RATES={i:600 for i in DIRECT}
SECONDS=DIRECT_SECONDS=60
H2452=H2453=DIAG=False
NODE=h.NODE;ORIGIN="h2442origin";procs={};logs={};current=None;folder=None
def spawn(key,ns,args,folder):
    f=(folder/(key+".log")).open("w");logs[key]=f
    prefix=[] if ns==NODE else ["ip","netns","exec",ns]
    p=subprocess.Popen([*prefix,*map(str,args)],stdout=f,stderr=subprocess.STDOUT,start_new_session=True);procs[key]=p;return p
def waitmark(key,marker,sec=35):
    p=procs[key];path=pathlib.Path(logs[key].name);t=time.monotonic()+sec
    while marker not in path.read_text(errors="replace"):
        if p.poll() is not None or time.monotonic()>t:raise RuntimeError(key+" not ready: "+path.read_text(errors="replace")[-500:])
        time.sleep(.2)
def stop(key):
    p=procs.pop(key,None)
    if p and p.poll() is None:
        subprocess.run(["sudo","-n","kill","-TERM","--",str(-p.pid)],capture_output=True)
        try:p.wait(15)
        except subprocess.TimeoutExpired:subprocess.run(["sudo","-n","kill","-KILL","--",str(-p.pid)],capture_output=True);p.wait(5)
    if key in logs:logs.pop(key).close()
    return p.returncode if p else None
def setup():
    h.root("ip","netns","add",ORIGIN)
    h.root("ip","link","add","h2442exit","type","veth","peer","name","h2442app")
    h.root("ip","link","set","h2442app","netns",ORIGIN)
    h.ns(NODE,"ip","addr","add","192.0.2.1/24","dev","h2442exit");h.ns(NODE,"ip","link","set","h2442exit","up")
    for a in (("link","set","lo","up"),("addr","add","192.0.2.2/24","dev","h2442app"),("link","set","h2442app","up"),("route","add","default","via","192.0.2.1")):h.ns(ORIGIN,"ip",*a)
    h.ns(NODE,"sysctl","-qw","net.ipv4.ip_forward=1")
    for ns in (NODE,ORIGIN):
        for k,v in (("net.ipv4.tcp_rmem","4096 87380 67108864"),("net.ipv4.tcp_wmem","4096 65536 67108864"),("net.core.rmem_max","67108864"),("net.core.wmem_max","67108864")):h.ns(ns,"sysctl","-qw",k+"="+v)
    h.ns(ORIGIN,"sysctl","-qw","net.ipv4.tcp_congestion_control=cubic")
    h.ns(ORIGIN,"tc","qdisc","replace","dev","h2442app","root","fq")
    h.root("modprobe","tcp_bbr",allow_fail=True)
    if "bbr" not in h.root("sysctl","-n","net.ipv4.tcp_available_congestion_control").stdout.split():raise RuntimeError("WSL BBR unavailable; no fallback")
    subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",str(TMP/"key.pem"),"-out",str(OUT/"cert.pem"),"-subj","/CN=wbd-h2228.example.test","-addext","subjectAltName=DNS:wbd-h2228.example.test"],check=True,capture_output=True)
    (TMP/"route-key.hex").write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n")
    (TMP/"users.json").write_text(json.dumps({"bench":"H2442-ONLY"}));(TMP/"leases.json").write_text(json.dumps({"bench":"10.66.0.2/32"}))
    for p in (TMP/"key.pem",TMP/"route-key.hex",TMP/"users.json",TMP/"leases.json"):p.chmod(0o600)
def sample():
    d={"host_stat":pathlib.Path("/proc/stat").read_text(),"psi":pathlib.Path("/proc/pressure/cpu").read_text(),"wan":json.loads(h.ns(NODE,"ip","-s","-j","link","show","dev","eth0").stdout),"ss":h.ns(NODE,"ss","-tinm").stdout,"wan_qdisc":h.ns(NODE,"tc","-s","qdisc","show","dev","eth0").stdout,"tun_qdisc":h.ns(NODE,"tc","-s","qdisc","show","dev","wbds0",allow_fail=True).stdout}
    if os.environ.get("WBD_H2455_SEGMENTS"):
        d["node_segments"]=linux_snapshot(NODE)
        d["host_segments"]=linux_snapshot()
        d["origin_segments"]=linux_snapshot(ORIGIN)
    return d
def start(i):
    global current,folder
    assert current is None and (i in DIRECT or 0<=i<len(CASES))
    current=i;folder=OUT/("case-"+str(i));folder.mkdir(exist_ok=False)
    if i<0:
        spawn("source",NODE,[sys.executable,APP,"source",PEER,5202,DIRECT_RATES.get(i,0),"bbr",DIRECT_SECONDS],folder);waitmark("source","SOURCE_READY")
    else:
        c=CASES[i];cap=c["rate"]*125000
        spawn("server",NODE,["env","LD_LIBRARY_PATH="+str(BUNDLE),"WBD_SHARED_TUN_ROUTE_DIAG=1","WBD_M0_SPLICE_PACING_AB="+str(cap),BUNDLE/"wbd-v4-server","--raw-interface","eth0","--local-ip",PEER,"--local-port","443","--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--server-name","wbd-h2228.example.test","--route-key-hex-file",TMP/"route-key.hex","--users-file",TMP/"users.json","--lease-pool","10.66.0.128/25","--manual-client-leases-file",TMP/"leases.json","--tls-cert",OUT/"cert.pem","--tls-key",TMP/"key.pem","--mode","shared","--peer-persona","legacy" if os.environ.get("WBD_H2455_SEGMENTS")=="linux" else "windows11","--outer-repair","on","--outer-mtu","1160","--tun-fq-maxrate-mbps","0","--tcp-proxy-cc","bbr","--tcp-proxy-port","46180"],folder)
        waitmark("server","V4_PUBLIC_MIXED_MULTI_SERVER_READY");waitmark("server","WBD_TCP_SPLICE_READY")
        h.ns(NODE,"tc","qdisc","replace","dev","wbds0","root","fq","flow_limit","256")
        h.save(folder/"origin-route.json",{"route":h.ns(NODE,"ip","route","get","192.0.2.2").stdout})
        spawn("probe",NODE,[sys.executable,APP,"probe","10.66.0.1",45901],folder);waitmark("probe","PROBE_READY")
        spawn("source",ORIGIN,[sys.executable,APP,"source","192.0.2.2",5400,c["rate"],"cubic",SECONDS],folder);waitmark("source","SOURCE_READY")
    h.save(folder/"before.json",sample());return {"case":i,"ready":True}
def close():
    global current
    assert current is not None
    h.save(folder/"after.json",sample())
    p=procs.get("source")
    if p:
        try:p.wait(20)
        except subprocess.TimeoutExpired:pass
    rc={k:stop(k) for k in list(procs)}
    result={"case":current,"rc":rc}
    try:result["source"]=json.loads((folder/"source.log").read_text().splitlines()[-1])
    except Exception:result["source"]=None
    if current>=0:
        s=(folder/"server.log").read_text(errors="replace")
        result.update(proxy_accept="WBD_TCP_SPLICE_ACCEPT target=192.0.2.2:5400 cc=bbr" in s,proxy_pacing="bytes_per_s="+str(CASES[current]["rate"]*125000) in s,stop="V4_PUBLIC_NATIVE_STOP_DRAINED" in s or "V4_PUBLIC_SHARED_TUN_STOP" in s,panic="panicked at" in s,inbox1024="slots=1024 " in s)
    h.save(folder/"result.json",result);current=None;return result
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        if self.client_address[0]!=peer["tail_ip"] or self.headers.get("X-H2228-Token")!=relay["control_token"]:self.send_error(403);return
        try:
            if self.path=="/start":
                body=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                result=start(int(body["case"]))
            elif self.path=="/sample":
                result=sample()
            elif self.path=="/stop":result=close()
            elif self.path=="/finish":
                assert current is None;result={"finished":True};threading.Thread(target=self.server.shutdown,daemon=True).start()
            else:raise ValueError("path")
            raw=json.dumps(result).encode();self.send_response(200);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        except Exception as e:
            self.send_error(500,repr(e)[:350])
if __name__=="__main__":
    peer={"tail_ip":"127.0.0.1"};relay={"control_token":os.environ["GITHUB_RUN_ID"]+"-local"}
    try:
        setup()
        with http.server.ThreadingHTTPServer(("127.0.0.1",18727),Handler) as s:
            h.save(OUT/"server-ready.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"real_wbd_server_ready":True,"scope":"control_bound_before_native_case"})
            print("H2442_SERVER_CONTROL_READY",flush=True);s.serve_forever()
    finally:
        for k in list(procs):stop(k)
        h.root("ip","netns","del",ORIGIN,allow_fail=True)
        h.root("ip","link","del","h2442exit",allow_fail=True)
        import shutil
        shutil.rmtree(TMP,ignore_errors=True)
