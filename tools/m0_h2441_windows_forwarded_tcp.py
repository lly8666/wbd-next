"""Actual Windows Winsock app -> original Wintun/Npcap -> Linux WBD
-> isolated Linux origin namespace; no application proxy/relay in fixture.
The existing two-OS UDP scenario is measured first; netem stays armed here."""
import sys,os,socket,time,hashlib,json,pathlib,subprocess
TARGET="198.18.77.2"
LEASE="10.66.0.2"
PORT=46191
NS="h2441-origin"
def transfer(c,source,total):
    c.settimeout(12)
    b=bytes(range(256))*1024
    view=memoryview(b)
    h=hashlib.sha256();n=0;started=time.monotonic();end="complete"
    try:
        if source:
            while n<total:
                off=n%len(b);q=c.send(view[off:min(len(b),off+total-n)])
                if not q:raise OSError("zero send")
                h.update(view[off:off+q]);n+=q
            c.shutdown(socket.SHUT_WR)
        else:
            while True:
                data=c.recv(len(b))
                if not data:break
                h.update(data);n+=len(data)
                if n>total:raise ValueError("excess bytes")
            end="eof"
    except Exception as e:end=type(e).__name__+":"+str(e)
    elapsed=max(.001,time.monotonic()-started)
    return {"bytes":n,"seconds":elapsed,"mbps":n*8/elapsed/1e6,"sha256":h.hexdigest(),"end":end}
def app(role,direction,total):
    source=(role=="origin" and direction=="download") or (role=="windows" and direction=="upload")
    if role=="origin":
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((TARGET,PORT));listener.listen(1);listener.settimeout(30)
            print("H2441_ORIGIN_READY",flush=True)
            c,_=listener.accept()
            with c:
                c.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,b"cubic")
                cc=c.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,32).split(b"\0")[0].decode()
                assert cc=="cubic"
                assert c.recv(1)==b"R"
                row=transfer(c,source,total);row["cc"]=cc;row["peer"]=c.getpeername()[0]
    else:
        with socket.create_connection((TARGET,PORT),timeout=25,source_address=(LEASE,0)) as c:
            assert c.getsockname()[0]==LEASE
            c.sendall(b"R");row=transfer(c,source,total);row["local"]=c.getsockname()[0]
    print(json.dumps(row),flush=True)
def measure(root,out,wsl,unix,win_product,linux_product,cc,scenario):
    rows=[]
    loss=max(scenario[d]["loss_pct"] for d in ("windows_to_linux","linux_to_windows"))
    total=(64 if loss==0 else 16 if loss<=5 else 4 if loss<=15 else 1)*2**20
    script=root/"tools"/"m0_h2441_windows_forwarded_tcp.py"
    # Only exact test-owned namespace/link; never replace a pre-existing name.
    if NS in wsl("ip","netns","list"):raise RuntimeError("foreign H2441 namespace")
    if "h2441host" in wsl("ip","-o","link","show"):raise RuntimeError("foreign H2441 veth")
    wsl("ip","netns","add",NS)
    try:
        wsl("ip","link","add","h2441host","type","veth","peer","name","h2441peer")
        wsl("ip","link","set","h2441peer","netns",NS)
        wsl("ip","addr","add","198.18.77.1/24","dev","h2441host")
        wsl("ip","link","set","h2441host","up")
        for args in (("link","set","lo","up"),("addr","add",TARGET+"/24","dev","h2441peer"),("link","set","h2441peer","up"),("route","add","default","via","198.18.77.1")):wsl("ip","netns","exec",NS,"ip",*args)
        wsl("ip","netns","exec",NS,"sysctl","-w","net.ipv4.tcp_congestion_control=cubic")
        (out/"h2441-origin-route.json").write_text(wsl("ip","-j","route","get",TARGET))
        for direction in ("download","upload"):
            lfile=out/("h2441-"+direction+"-origin.log");wfile=out/("h2441-"+direction+"-windows.log")
            pre=(out/"server.log").read_text(errors="replace").count("WBD_TCP_SPLICE_ACCEPT target="+TARGET+":"+str(PORT)+" cc=bbr")
            with lfile.open("w") as lo,wfile.open("w") as wo:
                l=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","ip","netns","exec",NS,"python3","-u",unix(script),"origin",direction,str(total)],stdout=lo,stderr=subprocess.STDOUT)
                w=None
                try:
                    until=time.monotonic()+15
                    while "H2441_ORIGIN_READY" not in lfile.read_text(errors="replace"):
                        if l.poll() is not None or time.monotonic()>until:raise RuntimeError("origin not ready")
                        time.sleep(.2)
                    w=subprocess.Popen([sys.executable,"-u",str(script),"windows",direction,str(total)],stdout=wo,stderr=subprocess.STDOUT)
                    deadline=time.monotonic()+100
                    samples=[]
                    while l.poll() is None or w.poll() is None:
                        if win_product.poll() is not None or linux_product.poll() is not None:raise RuntimeError("native product exited")
                        if time.monotonic()>deadline:raise RuntimeError("bounded transfer deadline")
                        samples.append({"time":time.time(),"ss":wsl("ss","-tin",timeout=5),"cpu":wsl("cat","/proc/stat","/proc/pressure/cpu",timeout=5)})
                        time.sleep(2)
                    (out/("h2441-"+direction+"-linux-samples.json")).write_text(json.dumps(samples))
                    if l.returncode or w.returncode:raise RuntimeError("application exit")
                    a=json.loads(lfile.read_text().splitlines()[-1]);b=json.loads(wfile.read_text().splitlines()[-1])
                    receiver=b if direction=="download" else a;sender=a if direction=="download" else b
                    observed=(out/"server.log").read_text(errors="replace").count("WBD_TCP_SPLICE_ACCEPT target="+TARGET+":"+str(PORT)+" cc=bbr")-pre
                    ok=sender["bytes"]==receiver["bytes"]==total and sender["sha256"]==receiver["sha256"] and receiver["end"]=="eof" and sender["end"]=="complete" and (observed>0 if cc else observed==0)
                    row={"status":"MEASURED_EXACT" if ok else "INCOMPLETE","direction":direction,"origin":a,"windows":b,"actual_receiver_mbps":receiver["mbps"],"proxy_bbr_accepts":observed,"target_bytes":total}
                except Exception as e:
                    row={"status":"INCOMPLETE","direction":direction,"error":repr(e),"target_bytes":total}
                finally:
                    for p in (w,l):
                        if p is not None and p.poll() is None:p.terminate()
                rows.append(row)
                (out/"h2441-forwarded-report.json").write_text(json.dumps(rows,indent=2))
    finally:
        # Deleting our namespace releases its exact veth peer.
        wsl("ip","netns","del",NS)
    return rows
if __name__=="__main__":app(sys.argv[1],sys.argv[2],int(sys.argv[3]))
