#!/usr/bin/env python3
"""Actual packaged Windows native owner to one WSL shared server. No new wire."""
import json, os, pathlib, re, secrets, subprocess, sys, time
from m0_plan028_h1415_windows_linux_independent_clients import marker, stopwin, linux_kill, guestpath, wsl
ROOT=pathlib.Path.cwd()
OUT=ROOT/"result/wl-public"
source=os.environ["WBD_MIXED_BINARY_SOURCE"]
peer=sys.argv[1]
app=ROOT/"tools/m0_mixed_mode_route_native.py"
guest_app=guestpath(app)
ldir=ROOT/"linux-product"
guest=guestpath(ldir)
assert json.loads((ldir/"manifest.json").read_text())["source_sha"]==source
procs=[]
private=[]
rows=[]
server=None
win=None
pidfile=OUT/"mixed-server.pid"
serverlog=OUT/"mixed-server.log"
def spawn(label,argv,stdin=False):
    pth=OUT/(label+".log")
    with pth.open("w") as f:
        p=subprocess.Popen(list(map(str,argv)),stdin=subprocess.PIPE if stdin else None,
                           stdout=f,stderr=subprocess.STDOUT,text=stdin,cwd=OUT)
    procs.append(p)
    return p,pth
def count(pattern):
    return len(re.findall(pattern,serverlog.read_text(errors="replace")))
def wait_count(pattern,before,p,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if count(pattern)>before:return
        if p.poll() is not None:raise RuntimeError("server exited")
        time.sleep(.1)
    raise RuntimeError("missing server promotion/retirement "+pattern)
wslbase=["wsl.exe","-d","Ubuntu","-u","root","--"]
port=47000
def probe(tag):
    global port
    for direction in ("s2c","c2s"):
        port+=1
        if direction=="s2c":
            lbase=[sys.executable,"-u",str(app)]
            sbase=wslbase+["python3","-u",guest_app]
            src,dst="10.66.0.1","10.66.0.2"
        else:
            lbase=wslbase+["python3","-u",guest_app]
            sbase=[sys.executable,"-u",str(app)]
            src,dst="10.66.0.2","10.66.0.1"
        label=tag+"-"+direction
        lp,ll=spawn("mixed-"+label+"-listen",lbase+["app","listen",dst,src,str(port),label])
        marker(ll,"APP_LISTENING",lp,8)
        sp,sl=spawn("mixed-"+label+"-send",sbase+["app","send",src,dst,str(port),label])
        assert sp.wait(timeout=18)==0,(label,sl.read_text(errors="replace"))
        assert lp.wait(timeout=10)==0,(label,ll.read_text(errors="replace"))
        assert all("REAL_TCP_UDP_PASS" in x.read_text(errors="replace") for x in (ll,sl))
def stop_client(p,log,lanes):
    stopwin(p)
    expected=("WBD_WINDOWS_GAME_NATIVE_DISCONNECTED lanes="+str(lanes) if lanes>1 else "WBD_WINDOWS_NATIVE_DISCONNECTED_V1")+" wal_restored=1 rust_stopped=1"
    assert expected in log.read_text(errors="replace"),("owned Windows Stop missing",expected)
    assert p.returncode==0,p.returncode
try:
    user="mixed-ci"
    password=secrets.token_hex(16)
    route=OUT/"mixed-route.hex";route.write_text(secrets.token_hex(32)+"\n");private.append(route)
    users=OUT/"mixed-users.json";users.write_text(json.dumps({user:password}));private.append(users)
    leases=OUT/"mixed-leases.json";leases.write_text(json.dumps({user:"10.66.0.2/32"}));private.append(leases)
    groute,gusers,gleases=("/run/wbd-mixed-"+os.environ["GITHUB_RUN_ID"]+"-"+n for n in ("route","users","leases"))
    for f,p in [(route,groute),(users,gusers),(leases,gleases)]:wsl("install","-m","600",guestpath(f),p)
    key=OUT/"mixed-key.pem";private.append(key)
    cert=OUT/"mixed-cert.pem";private.append(cert)
    wsl("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes","-keyout",guestpath(key),"-out",guestpath(cert),"-subj","/CN=wbd-v4.example.test","-addext","subjectAltName=DNS:wbd-v4.example.test",timeout=42)
    script=OUT/"mixed-server.sh";private.append(script)
    script.write_bytes(("#!/bin/sh\nset -eu\necho $$ > '"+guestpath(pidfile)+"'\nexec env LD_LIBRARY_PATH='"+guest+"' '"+guest+"/wbd-v4-server' --raw-interface eth0 --local-ip "+peer+" --local-port 443 --tun-name wbdmx4 --tun-ipv4 10.66.0.1/24 --server-name wbd-v4.example.test --route-key-hex-file "+groute+" --users-file "+gusers+" --manual-client-leases-file "+gleases+" --tls-cert '"+guestpath(cert)+"' --tls-key '"+guestpath(key)+"' --mode shared --peer-persona windows11 --outer-repair on\n").encode())
    server,serverlog=spawn("mixed-server",wslbase+["sh",guestpath(script)])
    marker(serverlog,"V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443",server,30)
    promotion=r"V4_PUBLIC_(?:NORMAL|GAME)_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX"
    retire=r"reason=same-protected-(?:normal|cohort)-grace-expired"
    prev=None
    for i,lanes in enumerate((1,2,1,4,1)):
        p0=count(promotion);r0=count(retire)
        if win is not None:stop_client(win,winlog,prev)
        t0=time.monotonic()
        args=[OUT/"wbd-client.exe","--native-v4-product","--control-stdin","--server-ip",peer,"--server-port","443","--source-port",str(41031+16*i),"--server-name","wbd-v4.example.test","--route-key-hex-file",route,"--tls-ca-pem",cert,"--username",user,"--password",password,"--tunnel-id","102030405060708090a0b0c0d0e0f001","--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDWLMAIN","--state-path",OUT/"mixed-owner.json","--mtu","1460","--lanes",str(lanes),"--fec-mode","off","--fec-parity","0","--fec.mode","off","--fec.profile","strong","--route-mode","all","--outer-repair","on"]
        win,winlog=spawn("mixed-win-"+str(i)+"-lanes-"+str(lanes),args,stdin=True)
        marker(winlog,"WBD_WINDOWS_OS_APPLIED",win,30)
        probe("switch-"+str(i))
        marker(winlog,"WBD_WINDOWS_CLIENT_READY",win,15)
        elapsed=time.monotonic()-t0
        if i:
            assert elapsed<30,("switch exceeds 30s",elapsed)
            assert count(promotion)==p0+1,("missing exact promotion",count(promotion),p0)
            wait_count(retire,r0,server,25)
            probe("after-grace-"+str(i))
        rows.append({"from_lanes":prev,"to_lanes":lanes,"seconds_to_real_duplex":elapsed,"promotion_delta":count(promotion)-p0,"tcp_udp":"PASS"})
        print("SIGNED_WINDOWS_REAL_MODE_SWITCH_PASS",rows[-1],flush=True)
        prev=lanes
    stop_client(win,winlog,prev);win=None
    linux_kill(pidfile)
    assert server.wait(timeout=30)==0
    assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in serverlog.read_text(errors="replace")
    (OUT/"mixed-pair-receipt.json").write_text(json.dumps({"qualification":"PASS_SCOPED_SIGNED_WINDOWS_WSL_SAME_SERVER_SWITCH","source_sha":source,"same_server":True,"same_authenticated_lease":"10.66.0.2/32","switches":rows,"owned_stop":"PASS"},indent=2))
finally:
    if win is not None:stopwin(win)
    if server is not None and server.poll() is None:linux_kill(pidfile)
    for p in reversed(procs):
        if p.poll() is None:
            try:p.terminate();p.wait(timeout=4)
            except Exception:p.kill()
    for f in private:f.unlink(missing_ok=True)
    for n in ("route","users","leases"):
        wsl("rm","-f","/run/wbd-mixed-"+os.environ["GITHUB_RUN_ID"]+"-"+n,check=False)
