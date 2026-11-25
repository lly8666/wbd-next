"""ARM server: source-locked preset case control, no arbitrary command endpoint."""
import os,sys,json,pathlib,subprocess,time,signal,http.server,threading,hashlib
import m0_h2228_three_runner_relay as h
ROOT=pathlib.Path.cwd();OUT=ROOT/"h2228-out";OUT.mkdir(exist_ok=True)
TMP=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2442-"+os.environ["GITHUB_RUN_ID"]);TMP.mkdir(exist_ok=True)
BUNDLE=ROOT/"linux-plan029-public-bundle";APP=ROOT/"tools/m0_h2442_tcp.py"
CASES=[{"rate":30,"proxy":False},{"rate":30,"proxy":True}]
NODE=h.NODE;ORIGIN="h2442origin";procs={};logs={};current=None;folder=None
def spawn(key,ns,args,folder):
    f=(folder/(key+".log")).open("w");logs[key]=f
    p=subprocess.Popen(["sudo","-n","ip","netns","exec",ns,*map(str,args)],stdout=f,stderr=subprocess.STDOUT,start_new_session=True);procs[key]=p;return p
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
    h.root("ip","link","set","h2442exit","netns",NODE);h.root("ip","link","set","h2442app","netns",ORIGIN)
    h.ns(NODE,"ip","addr","add","198.18.77.1/24","dev","h2442exit");h.ns(NODE,"ip","link","set","h2442exit","up")
    for a in (("link","set","lo","up"),("addr","add","198.18.77.2/24","dev","h2442app"),("link","set","h2442app","up"),("route","add","default","via","198.18.77.1")):h.ns(ORIGIN,"ip",*a)
    h.ns(NODE,"sysctl","-qw","net.ipv4.ip_forward=1")
    for ns in (NODE,ORIGIN):
        for k,v in (("net.ipv4.tcp_rmem","4096 87380 67108864"),("net.ipv4.tcp_wmem","4096 65536 67108864"),("net.core.rmem_max","67108864"),("net.core.wmem_max","67108864")):h.ns(ns,"sysctl","-qw",k+"="+v)
    h.ns(ORIGIN,"sysctl","-qw","net.ipv4.tcp_congestion_control=cubic")
    h.ns(ORIGIN,"tc","qdisc","replace","dev","h2442app","root","fq")
    h.ns(NODE,"tc","qdisc","replace","dev","wan0","root","fq")
    subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",str(TMP/"key.pem"),"-out",str(OUT/"cert.pem"),"-subj","/CN=wbd-h2228.example.test","-addext","subjectAltName=DNS:wbd-h2228.example.test"],check=True,capture_output=True)
    (TMP/"route-key.hex").write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n")
    (TMP/"users.json").write_text(json.dumps({"bench":"H2442-ONLY"}));(TMP/"leases.json").write_text(json.dumps({"bench":"10.66.0.2/32"}))
    for p in (TMP/"key.pem",TMP/"route-key.hex",TMP/"users.json",TMP/"leases.json"):p.chmod(0o600)
def sample():
    return {"host_stat":pathlib.Path("/proc/stat").read_text(),"psi":pathlib.Path("/proc/pressure/cpu").read_text(),"wan":json.loads(h.ns(NODE,"ip","-s","-j","link","show","dev","wan0").stdout),"ss":h.ns(NODE,"ss","-tinm").stdout}
def start(i):
    global current,folder
    assert current is None and -2<=i<len(CASES)
    current=i;folder=OUT/("case-"+str(i));folder.mkdir(exist_ok=False)
    if i<0:
        spawn("source",NODE,[sys.executable,APP,"source","10.248.82.2",5202,0,"bbr",25],folder);waitmark("source","SOURCE_READY")
    else:
        c=CASES[i];cap=c["rate"]*125000
        spawn("wan-capture",NODE,["timeout","100","tcpdump","-n","-tt","-l","-i","wan0","-c","2500","tcp port 443"],folder)
        time.sleep(.4)
        spawn("server",NODE,["env","LD_LIBRARY_PATH="+str(BUNDLE),"WBD_SHARED_TUN_ROUTE_DIAG=1","WBD_M0_SPLICE_PACING_AB="+str(cap),BUNDLE/"wbd-v4-server","--raw-interface","wan0","--local-ip","10.248.82.2","--local-port","443","--tun-name","wbds0","--tun-ipv4","10.66.0.1/24","--server-name","wbd-h2228.example.test","--route-key-hex-file",TMP/"route-key.hex","--users-file",TMP/"users.json","--lease-pool","10.66.0.128/25","--manual-client-leases-file",TMP/"leases.json","--tls-cert",OUT/"cert.pem","--tls-key",TMP/"key.pem","--mode","shared","--peer-persona","windows11","--outer-repair","on","--outer-mtu","1160","--tun-fq-maxrate-mbps","0"]+(["--tcp-proxy-cc","bbr","--tcp-proxy-port","46180"] if c["proxy"] else []),folder)
        waitmark("server","V4_PUBLIC_MIXED_MULTI_SERVER_READY")
        if c["proxy"]:waitmark("server","WBD_TCP_SPLICE_READY")
        spawn("tun-capture",NODE,["timeout","100","tcpdump","-n","-tt","-l","-i","wbds0","-c","2000","tcp"],folder)
        h.ns(NODE,"tc","qdisc","replace","dev","wbds0","root","fq","flow_limit","256")
        spawn("probe",NODE,[sys.executable,APP,"probe","10.66.0.1",45901],folder);waitmark("probe","PROBE_READY")
        spawn("source",ORIGIN,[sys.executable,APP,"source","198.18.77.2",5400,c["rate"],"cubic",20],folder);waitmark("source","SOURCE_READY")
    h.save(folder/"before.json",sample());return {"case":i,"ready":True}
def close():
    global current
    assert current is not None
    h.save(folder/"after.json",sample())
    p=procs.get("source")
    if p:
        try:p.wait(3)
        except subprocess.TimeoutExpired:pass
    rc={k:stop(k) for k in list(procs)}
    result={"case":current,"rc":rc}
    try:result["source"]=json.loads((folder/"source.log").read_text().splitlines()[-1])
    except Exception:result["source"]=None
    if current>=0:
        s=(folder/"server.log").read_text(errors="replace")
        result.update(proxy_configured=CASES[current]["proxy"],proxy_accept="WBD_TCP_SPLICE_ACCEPT target=198.18.77.2:5400 cc=bbr" in s,proxy_pacing="bytes_per_s="+str(CASES[current]["rate"]*125000) in s,stop="V4_PUBLIC_NATIVE_STOP_DRAINED" in s or "V4_PUBLIC_SHARED_TUN_STOP" in s,panic="panicked at" in s,inbox1024="slots=1024 " in s)
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
    peer=json.load(open("h2228-peer/client.json"));relay=json.load(open("h2228-peer/relay.json"))
    try:
        setup()
        with http.server.ThreadingHTTPServer((h.tailscale_ip(),18727),Handler) as s:
            h.save(OUT/"server-ready.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"real_wbd_server_ready":True,"scope":"control_bound_before_native_case"})
            print("H2442_SERVER_CONTROL_READY",flush=True);s.serve_forever()
    finally:
        for k in list(procs):stop(k)
        h.root("ip","netns","del",ORIGIN,allow_fail=True)
