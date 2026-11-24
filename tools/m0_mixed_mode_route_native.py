#!/usr/bin/env python3
"""Real original Go TLS/Rust RAW/TUN, one shared server, same /32 mode changes."""
import contextlib
import json
import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import time

def app():
    role, local, peer, port, tag = sys.argv[2:]
    port = int(port)
    marker = ("MIXED-SWITCH/" + tag).encode()
    def receive(sock, expected):
        out = b""
        while len(out) < len(expected):
            part = sock.recv(len(expected)-len(out))
            if not part:
                break
            out += part
        assert out == expected, (tag, out)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp, socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
        udp.settimeout(8); tcp.settimeout(8)
        if role == "listen":
            udp.bind((local, port)); tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp.bind((local, port)); tcp.listen(1)
            print("APP_LISTENING", flush=True)
            data, addr = udp.recvfrom(2048)
            assert data == marker and addr[0] == peer, (data, addr)
            udp.sendto(b"ACK/"+data, addr)
            conn, addr = tcp.accept()
            with conn:
                conn.settimeout(8)
                assert addr[0] == peer, addr
                receive(conn, marker)
                conn.sendall(b"ACK/"+marker)
        else:
            udp.bind((local, 0)); udp.settimeout(.3)
            for _ in range(25):
                udp.sendto(marker,(peer,port))
                try:
                    data,addr=udp.recvfrom(2048)
                    if data==b"ACK/"+marker and addr[0]==peer: break
                except socket.timeout: pass
            else: raise RuntimeError("reverse or forward UDP missing "+tag)
            tcp.bind((local,0)); tcp.connect((peer,port)); tcp.sendall(marker)
            receive(tcp,b"ACK/"+marker)
    print("REAL_TCP_UDP_PASS "+tag, flush=True)

if len(sys.argv)>1 and sys.argv[1]=="app":
    app()
    sys.exit(0)

root=pathlib.Path(sys.argv[1]).resolve()
out=pathlib.Path(sys.argv[2]).resolve()
out.mkdir(parents=True,exist_ok=True)
source=json.loads((root/"manifest.json").read_text())["source_sha"]
assert source==os.environ["GITHUB_SHA"]
script=pathlib.Path(__file__).resolve()
env=dict(os.environ,LD_LIBRARY_PATH=str(root))
server_log=out/"server.log"
ns_s,ns_a,ns_b="wbdms","wbdma","wbdmb"
bridge="wbdmbr"
procs=[]
proofs=[]
def cmd(*args, **kw):
    return subprocess.run(list(map(str,args)),check=True,**kw)
def ip(*args):
    return cmd("ip",*args)
def spawn(ns, argv, log):
    with log.open("w") as f:
        p=subprocess.Popen(["ip","netns","exec",ns,*map(str,argv)],env=env,stdout=f,stderr=subprocess.STDOUT)
    procs.append(p)
    return p
def content(path):
    return path.read_text(errors="replace") if path.exists() else ""
def wait_for(p, log, predicate, seconds=25):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        s=content(log)
        if predicate(s): return s
        if p.poll() is not None: raise RuntimeError("process exited "+str(log)+" "+s[-4000:])
        time.sleep(.05)
    raise RuntimeError("marker timeout "+str(log)+" "+content(log)[-4000:])
def stop(p,log,marker):
    if p.poll() is None: p.send_signal(signal.SIGTERM)
    rc=p.wait(timeout=20)
    assert rc==0 and marker in content(log), (rc,marker,content(log)[-4000:])
def count_promotion():
    return len(re.findall(r"V4_PUBLIC_(?:NORMAL|GAME)_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX",content(server_log)))
def start_client(ns, iface, outer, tun, port, name, mode, extra=()):
    log=out/(name+".log")
    inst="other" if ns==ns_b else "switch"
    args=[root/"wbd-v4-client","--raw-interface",iface,"--local-ip",outer,"--local-port",port,
          "--peer-ip","10.25.0.1","--peer-port","443","--tun-name",tun,
          "--server-name","wbd-v4.example.test","--route-key-hex-file",out/"route-key.hex",
          "--tls-ca-pem",out/"cert.pem","--username","alice","--password","mixed-route-fixture",
          "--auto-ip","--installation-id-file",out/("install-"+inst),"--mode",mode,*extra]
    p=spawn(ns,args,log)
    marker="V4_ORIGINAL_GO_GAME_NATIVE_READY role=client" if mode.startswith("game") else "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client"
    s=wait_for(p,log,lambda s: marker in s and "V4_PUBLIC_LEASE_APPLIED role=client" in s)
    lease=re.findall(r"os_readback=([0-9.]+)/32",s)[-1]
    ip("-n",ns,"route","replace","10.66.0.1/32","dev",tun)
    return p,log,lease
port=47000
def probe(ns,lease,tag):
    global port
    # Server-originated application delivery comes FIRST, independently of
    # client uplink payload; an echo-only uplink could mask a stale TX owner.
    for direction,sns,dns,src,dst in [
        ("s2c",ns_s,ns,"10.66.0.1",lease),
        ("c2s",ns,ns_s,lease,"10.66.0.1")]:
        port+=1
        label=tag+"-"+direction
        llog=out/(label+"-listener.log")
        slog=out/(label+"-sender.log")
        listener=spawn(dns,[sys.executable,"-u",script,"app","listen",dst,src,port,label],llog)
        wait_for(listener,llog,lambda s:"APP_LISTENING" in s,5)
        sender=spawn(sns,[sys.executable,"-u",script,"app","send",src,dst,port,label],slog)
        assert sender.wait(timeout=18)==0,(label,content(slog))
        assert listener.wait(timeout=10)==0,(label,content(llog))
        assert "REAL_TCP_UDP_PASS" in content(slog) and "REAL_TCP_UDP_PASS" in content(llog)
        proofs.append(label)
    print("REAL_BIDIRECTIONAL_TCP_UDP "+tag,flush=True)
try:
    for ns in (ns_s,ns_a,ns_b):
        ip("netns","add",ns);ip("-n",ns,"link","set","lo","up")
    ip("link","add",bridge,"type","bridge");ip("link","set",bridge,"up")
    for host,iface,ns,addr in (("wmhs","wms",ns_s,"10.25.0.1"),("wmha","wma",ns_a,"10.25.0.2"),("wmhb","wmb",ns_b,"10.25.0.3")):
        ip("link","add",host,"type","veth","peer","name",iface)
        ip("link","set",host,"master",bridge);ip("link","set",host,"up")
        ip("link","set",iface,"netns",ns);ip("-n",ns,"addr","add",addr+"/24","dev",iface);ip("-n",ns,"link","set",iface,"up")
        cmd("ip","netns","exec",ns,"iptables","-A","OUTPUT","-p","tcp","--tcp-flags","RST","RST","-j","DROP")
    cmd("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes",
        "-keyout",out/"key.pem","-out",out/"cert.pem","-subj","/CN=wbd-v4.example.test",
        "-addext","subjectAltName=DNS:wbd-v4.example.test",stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (out/"users.json").write_text(json.dumps({"alice":"mixed-route-fixture"}))
    (out/"users.json").chmod(0o600)
    cmd(root/"wbd-v4-server","--init-route-key-file",out/"route-key.hex",env=env)
    server=spawn(ns_s,[root/"wbd-v4-server","--raw-interface","wms","--local-ip","10.25.0.1","--local-port","443",
        "--tun-name","wms4","--tun-ipv4","10.66.0.1/24","--server-name","wbd-v4.example.test",
        "--route-key-hex-file",out/"route-key.hex","--users-file",out/"users.json","--lease-pool","10.66.0.128/25",
        "--tls-cert",out/"cert.pem","--tls-key",out/"key.pem","--mode","shared"],server_log)
    wait_for(server,server_log,lambda s:"V4_PUBLIC_MIXED_MULTI_SERVER_READY" in s)
    other,otherlog,otherlease=start_client(ns_b,"wmb","10.25.0.3","wmb4",43031,"other-normal","normal")
    probe(ns_b,otherlease,"other-initial")
    modes=[("normal",()),("game2",()),("normal",()),("game4",("--game-fec","fixed6")),
           ("game2",("--game-fec","fixed6")),("game4",()),("fec-fixed",()),("normal",()),
           ("game4",("--rotation-interval","5s"))]
    current=None
    rows=[]
    mainlease=None
    for i,(mode,extra) in enumerate(modes):
        before=count_promotion()
        old_stop=None
        if current is not None:
            stop(current,currentlog,currentmarker)
            old_stop=time.monotonic()
        started=time.monotonic()
        current,currentlog,lease=start_client(ns_a,"wma","10.25.0.2","wma4",41031+16*i,f"switch-{i}-{mode}",mode,extra)
        currentmarker="V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client" if mode.startswith("game") else "V4_PUBLIC_NATIVE_STOP_DRAINED role=client"
        if mainlease is None: mainlease=lease
        assert lease==mainlease and lease!=otherlease,(lease,mainlease,otherlease)
        # No waiting on Health90; directly exercise actual application path.
        probe(ns_a,lease,f"switch-{i}-{mode}")
        elapsed=time.monotonic()-started
        if i:
            assert time.monotonic()-old_stop<30,"switch did not recover promptly"
            assert count_promotion()==before+1,(i,before,count_promotion(),content(server_log)[-4000:])
        probe(ns_b,otherlease,f"other-during-{i}")
        rows.append({"from":None if i==0 else modes[i-1][0],"to":mode,"lease":lease,"seconds_to_business":elapsed,
                     "promotion_delta":count_promotion()-before,"bidirectional_tcp_udp":"PASS"})
    wait_for(current,currentlog,lambda s:"V4_PUBLIC_GAME_SINGLE_LANE_READY role=client" in s,25)
    wait_for(server,server_log,lambda s:"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server" in s,25)
    probe(ns_a,mainlease,"game4-after-hot-lane")
    probe(ns_b,otherlease,"other-after-hot-lane")
    # Independent disconnected lease must still expire by original Health90,
    # without disturbing the active switched owner's real reverse traffic.
    stop(other,otherlog,"V4_PUBLIC_NATIVE_STOP_DRAINED role=client")
    deadline=time.monotonic()+105
    i=0
    while "reason=authenticated-rust-normal-health90" not in content(server_log):
        assert time.monotonic()<deadline,"original Health90 missing"
        probe(ns_a,mainlease,f"alive-during-health90-{i}")
        i+=1
        time.sleep(5)
    probe(ns_a,mainlease,"alive-after-health90")
    assert "reason=same-protected-normal-grace-expired" in content(server_log)
    assert "reason=same-protected-cohort-grace-expired" in content(server_log)
    stop(current,currentlog,currentmarker)
    stop(server,server_log,"V4_PUBLIC_SHARED_TUN_STOP generation=")
    assert "V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close" in content(server_log)
    receipt={"source_sha":source,"native_isa":os.uname().machine,"qualification":"PASS_SCOPED_REAL_MIXED_MODE_SHARED_ROUTE",
        "same_server":True,"switch_lease":mainlease,"same_account_other_lease":otherlease,"switches":rows,
        "real_tcp_udp_directions":proofs,"game4_hot_lane":"PASS","old_grace":"PASS","independent_health90":"PASS","owned_stop":"PASS"}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2),flush=True)
finally:
    for p in reversed(procs):
        if p.poll() is None:
            p.terminate()
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired: p.kill();p.wait()
    for ns in (ns_a,ns_b,ns_s):
        subprocess.run(["ip","netns","del",ns],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(["ip","link","del",bridge],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    # Do not publish test credentials, certificate keys or installation IDs.
    for name in ("key.pem","users.json","route-key.hex","install-switch","install-other"):
        with contextlib.suppress(FileNotFoundError): (out/name).unlink()
