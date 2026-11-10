#!/usr/bin/env python3
"""PLAN028: ONE real signed Windows VPN client + ONE independent native
Linux netns VPN client authenticated to the SAME original Go TLS443/Rust
shared-TUN server. Actual kernel UDP/TCP both, A Stop B survives, all owned.
No second Windows Wintun, fabricated handshake, synthetic DATA, or new wire.
"""
import json,hashlib,os,pathlib,re,secrets,socket,subprocess,sys,time
from m0_plan028_h1412_wsl_cross_os_client_preflight import (
    wsl,ip,witness,guestpath,NAME,NS,HOST,CHILD,ALIAS,PEER)
root=pathlib.Path.cwd();out=root/"result"/"wl-public";out.mkdir(parents=True,exist_ok=True)
L3_DURATION=(600 if os.environ.get("WBD_PLAN028_WIN_LINUX_600")=="1" else 1800) if os.environ.get("WBD_PLAN028_WIN_LINUX_L3")=="1" else 0
source=os.environ["GITHUB_SHA"]
report={"schema_version":1,"source_sha":source,
 "scene":"ONE_WINDOWS_SIGNED_CLIENT_AND_INDEPENDENT_LINUX_NETNS_CLIENT_ONE_SHARED_SERVER",
 "status":"NOT_RUN","mode":"normal","mode_public":"NOT_RUN",
 "windows_client_instances":1,"linux_client_instances":1,
 "shared_server":"NOT_RUN","two_independent_credentials":"NOT_RUN",
 "app_duplex":"NOT_RUN","tcp_duplex":"NOT_RUN","stop":"NOT_RUN",
 "windows_stop_linux_survives":"NOT_RUN","owned_l2_restored":False,
 "WL_N0":"NOT_RUN","WL_P200":"NOT_RUN","WL_V2":"NOT_RUN"}
def need(cond,what):
    if not cond:raise RuntimeError(what)
def marker(p,part,proc=None,timeout=60):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        t=p.read_text(errors="replace") if p.exists() else ""
        if part in t:return t
        if proc is not None and proc.poll() is not None:
            raise RuntimeError("original "+part+" process exited "+str(proc.returncode)+" "+t[-600:])
        time.sleep(.2)
    raise RuntimeError("original "+part+" not observed: "+(p.read_text(errors="replace") if p.exists() else "")[-650:])
def udp_stats(p):
    result={"sent":0,"received":0,"reverse_received":0,
            "echo_age_ms":None,"reverse_age_ms":None,
            "max_echo_gap_ms":0.,"max_reverse_gap_ms":0.}
    if p.exists():
        with p.open("rb") as fd:
            fd.seek(max(0,p.stat().st_size-16384))
            lines=fd.read().decode("utf-8","replace").splitlines()
        for line in lines:
            try:
                item=json.loads(line)
                if item.get("phase") in ("udp","final"):
                    for key in ("sent","received","reverse_received"):
                        result[key]=int(item.get(key,0))
                    for key in ("echo_age_ms","reverse_age_ms","max_echo_gap_ms","max_reverse_gap_ms"):
                        result[key]=item.get(key,0.)
            except (ValueError,TypeError):pass
    return result
def count(p):
    return udp_stats(p)["received"]
def stopwin(p):
    if p is None or p.poll() is not None:return
    try:
        if p.stdin:p.stdin.write("stop\n");p.stdin.flush()
        p.wait(timeout=22)
    except Exception:
        p.terminate()
        try:p.wait(timeout=6)
        except subprocess.TimeoutExpired:p.kill()
def linux_kill(pidfile):
    if not pidfile.exists():return
    v=pidfile.read_text().strip()
    if v.isdigit():wsl("kill","-TERM",v,check=False)
def guest_script(name,text):
    p=out/name;p.write_bytes(text.encode("utf-8"));return guestpath(p)
def l2_setup(ipv4,prefix,mac,gw):
    ip("link","add",NAME,"type","bridge")
    ip("link","set","dev",NAME,"address",mac)
    ip("link","set","dev",NAME,"up")
    ip("addr","add",ipv4+"/"+str(prefix),"dev",NAME)
    ip("link","set","dev","eth0","master",NAME)
    ip("addr","del",ipv4+"/"+str(prefix),"dev","eth0")
    ip("route","replace","default","via",gw,"dev",NAME)
    ip("addr","add",ALIAS+"/24","dev",NAME)
    ip("netns","add",NS)
    ip("link","add",HOST,"type","veth","peer","name",CHILD,"netns",NS)
    ip("link","set",HOST,"master",NAME)
    ip("link","set",HOST,"up")
    ip("-n",NS,"link","set","lo","up")
    ip("-n",NS,"addr","add",PEER+"/24","dev",CHILD)
    ip("-n",NS,"link","set",CHILD,"up")
    ip("-n",NS,"route","add","default","via",ALIAS,"dev",CHILD)
    # Only namespace client fakeTCP local port, never a process-wide BPF.
    wsl("ip","netns","exec",NS,"iptables","-I","OUTPUT","-p","tcp",
        "--tcp-flags","RST","RST","-j","DROP")
    links=json.loads(ip("-j","link","show","dev",NAME))
    need(len(links)==1 and links[0]["address"].lower()==mac.lower(),
         "actual WSL bridge not bound to original Windows-neighbor MAC")
def l2_restore(ipv4,prefix,gw):
    ip("netns","del",NS,check=False)
    ip("link","del",HOST,check=False)
    ip("link","set","dev","eth0","nomaster",check=False)
    link=json.loads(ip("-j","link","show","dev","eth0"))
    need(len(link)==1,"original WSL2 eth0 link missing at rollback")
    addr=json.loads(ip("-j","-4","addr","show","dev","eth0"))
    cur=[a["local"]+"/"+str(a["prefixlen"]) for row in addr
         for a in row.get("addr_info",[]) if a["family"]=="inet"]
    original=ipv4+"/"+str(prefix)
    if original not in cur:ip("addr","add",original,"dev","eth0")
    ip("route","replace","default","via",gw,"dev","eth0")
    ip("link","del",NAME,check=False)
    fresh=witness()
    values=[a["local"]+"/"+str(a["prefixlen"]) for a in fresh["addr_info"] if a["family"]=="inet"]
    routes=json.loads(ip("-j","-4","route","show","default"))
    return (original in values and any(x.get("dev")=="eth0" and x.get("gateway")==gw for x in routes)
        and wsl("ip","link","show","dev",NAME,check=False).returncode!=0
        and wsl("ip","netns","exec",NS,"true",check=False).returncode!=0)
def tcp_windows(local):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(8)
    try:
        s.bind((local,0));s.connect(("10.66.0.1",45902))
        v=b"WBD_H1415_REAL_TCP_WINDOWS"
        s.sendall(v);received=b""
        while len(received)<len(v):
            part=s.recv(1024)
            if not part:break
            received+=part
        need(received==v,"Windows genuine TCP kernel echo mismatch")
    finally:s.close()
def product_app():
    script=r"""import json,pathlib,select,socket,sys,time
mode=sys.argv[1]
if mode=="echo":
    dst=pathlib.Path(sys.argv[2])
    while True:
        try:
            u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            u.bind(("10.66.0.1",45901))
            t=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            t.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            t.bind(("10.66.0.1",45902));t.listen(4)
            break
        except OSError:
            time.sleep(.1)
    targets={"A":"10.66.0.2","B":"10.66.0.3"}
    count={"A":0,"B":0};next_send=time.monotonic()
    while True:
        now=time.monotonic()
        if now>=next_send:
            for label,ip in targets.items():
                if (dst/("h1415-"+label+"-start.flag")).exists():
                    try:
                        u.sendto(("WBD_H1415_REVERSE_%s_%d"%(label,count[label])).encode(),(ip,45901))
                        count[label]+=1
                    except OSError:pass
            next_send=now+.1
        readable,_,_=select.select([u,t],[],[],.06)
        for sock in readable:
            if sock is u:
                data,addr=u.recvfrom(4096)
                if data.startswith(b"WBD_H1415_"):u.sendto(data,addr)
            else:
                conn,addr=t.accept()
                try:
                    conn.settimeout(3);data=conn.recv(4096)
                    if data.startswith(b"WBD_H1415_REAL_TCP_"):conn.sendall(data)
                finally:conn.close()
elif mode=="udp":
    local,label,stop=sys.argv[2:5]
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    deadline=time.monotonic()+65
    while True:
        try:s.bind((local,45901));break
        except OSError:
            if time.monotonic()>=deadline:raise
            time.sleep(.1)
    start=time.monotonic();n=0;rx=0;reverse_rx=0;last=start
    echo_last=None;reverse_last=None;max_echo_gap=0.;max_reverse_gap=0.
    app_limit=int(sys.argv[5]) if len(sys.argv)>5 else 150
    seen=set();reverse_seen=set();last_send_error=-10.
    echo_prefix=("WBD_H1415_REAL_UDP_%s_"%label).encode()
    reverse_prefix=("WBD_H1415_REVERSE_%s_"%label).encode()
    budgeted=(len(sys.argv)>6 and sys.argv[6]=="h1504budget")
    old_phase=None
    while not pathlib.Path(stop).exists() and time.monotonic()-start<app_limit:
        elapsed=time.monotonic()-start
        # H1504 genuine application data in four bounded stages. No
        # new control kind, custom VPN retransmission, or server loop.
        if budgeted:
            if elapsed<450:phase="warm";recv_window=.045;sleep_s=.060;body_size=128
            elif elapsed<1050:phase="mixed";recv_window=.025;sleep_s=.030;body_size=256
            elif elapsed<1350:phase="higher";recv_window=.020;sleep_s=.020;body_size=1024
            else:phase="recovery";recv_window=.030;sleep_s=.035;body_size=512
            if old_phase!=phase:
                old_phase=phase
                print(json.dumps({"phase":"budget_switch","label":label,
                    "stage":phase,"elapsed_s":round(elapsed,3),
                    "sent_packets_at_start":n,"received_packets_at_start":rx,
                    "reverse_packets_at_start":reverse_rx,
                    "payload_bytes":body_size,"recv_window_ms":round(recv_window*1000),
                    "sleep_ms":round(sleep_s*1000)}),flush=True)
            header=echo_prefix+str(n).encode()+b"|"
            data=header+b"Q"*max(0,body_size-len(header))
        else:
            recv_window=.045;sleep_s=.060
            data=echo_prefix+str(n).encode()
        try:s.sendto(data,("10.66.0.1",45901));n+=1
        except OSError as exc:
            if time.monotonic()-last_send_error>2:
                print(json.dumps({"phase":"send_error","label":label,
                     "errno":getattr(exc,"errno",None)}),flush=True)
                last_send_error=time.monotonic()
        # Server reverse UDP and delayed echoes interleave on the same socket.
        # Correlate actual IDs rather than only this iteration's payload;
        # drain at most 32 datagrams/45ms from the true kernel socket.
        end=time.monotonic()+recv_window
        for _ in range(32):
            remaining=end-time.monotonic()
            if remaining<=0:break
            ready,_,_=select.select([s],[],[],remaining)
            if not ready:break
            got,addr=s.recvfrom(4096)
            if addr[0]!="10.66.0.1":continue
            if got.startswith(echo_prefix):
                try:seq=int(got[len(echo_prefix):].split(b"|",1)[0])
                except ValueError:continue
                if 0<=seq<n and seq not in seen:
                    seen.add(seq);rx+=1
                    received_at=time.monotonic()
                    if echo_last is not None:max_echo_gap=max(max_echo_gap,received_at-echo_last)
                    echo_last=received_at
            elif got.startswith(reverse_prefix):
                try:seq=int(got[len(reverse_prefix):])
                except ValueError:continue
                if seq>=0 and seq not in reverse_seen:
                    reverse_seen.add(seq);reverse_rx+=1
                    received_at=time.monotonic()
                    if reverse_last is not None:max_reverse_gap=max(max_reverse_gap,received_at-reverse_last)
                    reverse_last=received_at
        if time.monotonic()-last>.5:
            now=time.monotonic()
            print(json.dumps({"phase":"udp","label":label,"sent":n,
                "received":rx,"reverse_received":reverse_rx,
                "echo_age_ms":None if echo_last is None else round((now-echo_last)*1000,2),
                "reverse_age_ms":None if reverse_last is None else round((now-reverse_last)*1000,2),
                "max_echo_gap_ms":round(max_echo_gap*1000,2),
                "max_reverse_gap_ms":round(max_reverse_gap*1000,2)}),flush=True)
            last=now
        time.sleep(sleep_s)
    now=time.monotonic()
    print(json.dumps({"phase":"final","label":label,"sent":n,
        "received":rx,"reverse_received":reverse_rx,
        "echo_age_ms":None if echo_last is None else round((now-echo_last)*1000,2),
        "reverse_age_ms":None if reverse_last is None else round((now-reverse_last)*1000,2),
        "max_echo_gap_ms":round(max_echo_gap*1000,2),
        "max_reverse_gap_ms":round(max_reverse_gap*1000,2)}),flush=True)
elif mode=="tcp":
    local=sys.argv[2]
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.settimeout(7)
    s.bind((local,0));s.connect(("10.66.0.1",45902))
    data=b"WBD_H1415_REAL_TCP_LINUX"
    s.sendall(data);got=b""
    while len(got)<len(data):
        piece=s.recv(1024)
        if not piece:break
        got+=piece
    assert got==data,(got,data)
    print("H1415_LINUX_NATIVE_KERNEL_TCP_ECHO_PASS",flush=True)
else:raise SystemExit("unknown native product application stage")
"""
    p=out/"h1415-real-kernel-app.py";p.write_text(script,encoding="utf-8");return p,guestpath(p)
def main():
    need(os.environ.get("WBD_PLAN028_WIN_LINUX_600")!="1" or L3_DURATION==600,
         "600s trial must enable original L3 managed route+full product setup")
    cli=out/"wbd-client-embedded.exe";win_dll=out/"wbd_engine.dll"
    serverbin=root/"linux-product"/"wbd-v4-server"
    clientbin=root/"linux-product"/"wbd-v4-client"
    linux_dll=root/"linux-product"/"libwbd_engine.so"
    for p in (cli,win_dll,serverbin,clientbin,linux_dll):
        need(p.exists() and p.stat().st_size>10000,"original product binary absent "+str(p))
    need(os.environ.get("LINUX_BINARY_SRC")==source,"Windows/Linux build SOURCE mismatch")
    for name,p in (("windows_original_client",cli),("linux_original_client",clientbin),
                   ("original_server",serverbin),("windows_rust",win_dll),("linux_rust",linux_dll)):
        report[name+"_sha256"]=hashlib.sha256(p.read_bytes()).hexdigest()
    state=witness()
    a=[x for x in state["addr_info"] if x["family"]=="inet" and x["scope"]=="global"]
    need(len(a)==1,"original guest eth0 has ambiguous source IPv4")
    ipv4=a[0]["local"];prefix=a[0]["prefixlen"]
    mac=json.loads(ip("-j","link","show","dev","eth0"))[0]["address"]
    route=json.loads(ip("-j","-4","route","show","default"))
    need(len(route)==1 and route[0].get("gateway"),"WSL2 gateway ambiguous")
    gw=route[0]["gateway"];report["outer_linux_bridged_original_IP"]=ipv4
    fds=[];secret=[];processes={};owned=False
    keys={"alice":"h1415-pass-A-private","bob":"h1415-pass-B-private"}
    local={
        "route":out/"h1415-route.hex","users":out/"h1415-users.json",
        "leases":out/"h1415-leases.json"}
    local["route"].write_text(secrets.token_hex(32)+"\n")
    local["users"].write_text(json.dumps(keys)+"\n")
    local["leases"].write_text(json.dumps({"alice":"10.66.0.2/32","bob":"10.66.0.3/32"})+"\n")
    secret=list(local.values())
    guest={}
    for kind,path in local.items():
        guest[kind]="/run/wbd-h1415-"+os.environ["GITHUB_RUN_ID"]+"-"+kind
    def start(name,command,guest_process=False):
        f=(out/(name+".log")).open("w");fds.append(f)
        p=subprocess.Popen(command,stdin=subprocess.PIPE if name=="h1415-windows" else None,
            stdout=f,stderr=subprocess.STDOUT,text=(name=="h1415-windows"))
        processes[name]=p;return p
    try:
        for kind,path in local.items():wsl("install","-m","600",guestpath(path),guest[kind])
        wsl("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes",
            "-keyout",guestpath(out)+"/h1415-key.pem",
            "-out",guestpath(out)+"/h1415-cert.pem","-subj","/CN=wbd-v4.example.test",
            "-addext","subjectAltName=DNS:wbd-v4.example.test")
        l2_setup(ipv4,prefix,mac,gw);owned=True
        report["real_win_linux_underlay"]="H1414_BRIDGE_MAC_AND_OWNED_NETNS_INSTALLED"
        pwd=guestpath(out);build=guestpath(root/"linux-product")
        servercmd=guest_script("h1415-server.sh",
            "#!/bin/sh\nset -eu\necho $$ > '"+pwd+"/h1415-server.pid'\n"
            "exec env LD_LIBRARY_PATH='"+build+"' '"+build+"/wbd-v4-server'"
            " --raw-interface "+NAME+" --local-ip "+ipv4+" --local-port 443"
            " --tun-name wbdwl4 --tun-ipv4 10.66.0.1/24"
            " --server-name wbd-v4.example.test --route-key-hex-file '"+guest["route"]+"'"
            " --users-file '"+guest["users"]+"' --manual-client-leases-file '"+guest["leases"]+"'"
            " --tls-cert '"+pwd+"/h1415-cert.pem' --tls-key '"+pwd+"/h1415-key.pem'"
            " --mode normal --peer-persona windows11 --outer-repair on\n")
        server=start("h1415-server",["wsl.exe","-d","Ubuntu","-u","root","--","sh",servercmd])
        marker(out/"h1415-server.log","V4_PUBLIC_MULTI_SERVER_READY role=server port=443",server,50)
        report["shared_server"]="REAL_GO_TLS443_SHARED_RUST_TUN_READY"
        budgeted1800=os.environ.get("WBD_PLAN028_WIN_LINUX_1800_BUDGETED")=="1"
        need(not budgeted1800 or L3_DURATION==1800,
             "H1504 mixed-length bounded pacing requires actual 1800s")
        app,guestapp=product_app()
        echo=start("h1415-echo",["wsl.exe","-d","Ubuntu","-u","root","--",
                                 "python3","-u",guestapp,"echo",pwd])
        winargs=[str(cli),"--native-v4-product","--control-stdin",
                 "--server-ip",ipv4,"--server-port","443","--source-port","41031",
                 "--server-name","wbd-v4.example.test",
                 "--route-key-hex-file",str(local["route"]),
                 "--tls-ca-pem",str(out/"h1415-cert.pem"),
                 "--username","alice","--password",keys["alice"],
                 "--tunnel-id","102030405060708090a0b0c0d0e0f001",
                 "--installation-id","445566778899aabbccddeeff00112233",
                 "--lease4","10.66.0.2/32","--adapter","WBDWLMAIN",
                 "--state-path",str(out/"h1415-win-owned.json"),
                 "--lanes","1","--fec-mode","off","--fec.mode","off",
                 "--route-mode","bypass-lan","--outer-repair","on"]
        win=start("h1415-windows",winargs)
        (out/"h1415-A-start.flag").touch()
        winapp=start("h1415-winapp",[sys.executable,"-u",str(app),"udp",
                   "10.66.0.2","A",str(out/"h1415-A-stop.flag"),
                   str(L3_DURATION+450 if L3_DURATION else 150),
                   "h1504budget" if budgeted1800 else "original"])
        marker(out/"h1415-windows.log","WBD_WINDOWS_CLIENT_READY",win,75)
        osread=subprocess.run(["powershell.exe","-NoProfile","-Command",
          "(Get-NetAdapter -IncludeHidden -Name 'WBDWLMAIN' -ErrorAction Stop | Select-Object Name,InterfaceIndex,Status) | ConvertTo-Json -Compress"],
          text=True,capture_output=True,timeout=20)
        need(osread.returncode==0 and json.loads(osread.stdout)["InterfaceIndex"]>0,
             "actual Windows signed Wintun interface not OS-installed")
        report["windows_client"]="REAL_ONE_SIGNED_NPCAP_WINTUN_AUTHENTICATED_READY"
        linuxcmd=guest_script("h1415-linux-client.sh",
             "#!/bin/sh\nset -eu\necho $$ > '"+pwd+"/h1415-linux.pid'\n"
             "exec env LD_LIBRARY_PATH='"+build+"' '"+build+"/wbd-v4-client'"
             " --raw-interface "+CHILD+" --local-ip "+PEER+" --local-port 41032"
             " --peer-ip "+ipv4+" --peer-port 443"
             " --tun-name wbdl1415 --server-name wbd-v4.example.test"
             " --route-key-hex-file '"+guest["route"]+"'"
             " --tls-ca-pem '"+pwd+"/h1415-cert.pem'"
             " --username bob --password '"+keys["bob"]+"'"
             " --tun-ipv4 10.66.0.3/32 --tunnel-id 102030405060708090a0b0c0d0e0f002"
             " --mode normal --record-cipher aes-128-gcm --outer-repair on\n")
        linux=start("h1415-linux",["wsl.exe","-d","Ubuntu","-u","root","--",
             "ip","netns","exec",NS,"sh",linuxcmd])
        (out/"h1415-B-start.flag").touch()
        linapp=start("h1415-linapp",["wsl.exe","-d","Ubuntu","-u","root","--",
             "ip","netns","exec",NS,"python3","-u",guestapp,"udp","10.66.0.3",
             "B",guestpath(out/"h1415-B-stop.flag"),
             str(L3_DURATION+450 if L3_DURATION else 150),
             "h1504budget" if budgeted1800 else "original"])
        marker(out/"h1415-linux.log","V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client",linux,75)
        both=marker(out/"h1415-server.log","V4_PUBLIC_MULTI_SESSION_READY role=server",server,15)
        need(both.count("V4_PUBLIC_MULTI_SESSION_READY role=server")>=2,
             "server did not authenticate both independent protected users")
        # Strict per-session presentation: Windows A must keep Windows11,
        # Linux Bob must keep Legacy; both are original post-TLS M4 owners.
        serverlog=(out/"h1415-server.log").read_text(errors="replace")
        need("V4_PUBLIC_MULTI_PEER_PERSONA role=server incoming=1 cold_syn_known=true actual_original_TLS_Rust_M4=1" in serverlog
             and "V4_PUBLIC_MULTI_PEER_PERSONA role=server incoming=0 cold_syn_known=true actual_original_TLS_Rust_M4=1" in serverlog,
             "original authenticated Windows/Linux session-specific peer persona not both applied")
        report["per_authenticated_peer_persona"]="PASS_WINDOWS11_A_AND_LEGACY_B_DISTINCT_NATIVE_RX"
        osaddr=json.loads(ip("-n",NS,"-j","-4","addr","show","dev","wbdl1415"))
        need(any(a.get("local")=="10.66.0.3" for row in osaddr
             for a in row.get("addr_info",[])),
             "Linux separate OS TUN lease original /32 not installed")
        # Explicit manual /32 has no connected server subnet. Install the
        # single server-inner host route only in Bob's owned namespace after
        # actual protected TLS/Rust READY and native OS TUN address readback.
        ip("-n",NS,"route","replace","10.66.0.1/32","dev","wbdl1415")
        route=json.loads(ip("-n",NS,"-j","-4","route","get","10.66.0.1",
                            "from","10.66.0.3"))
        need(any(x.get("dev")=="wbdl1415" for x in route),
             "authenticated Linux /32 route did not select own TUN")
        report["linux_manual_inner_route"]="PASS_OS_ROUTE_GET_SERVER_32_VIA_B_TUN"
        report["two_independent_credentials"]="PASS_ORIGINAL_TLS_2_ACCOUNTS_2_DISTINCT_LEASES"
        need(echo.poll() is None,"server genuine kernel echo actor not running")
        deadline=time.monotonic()+25
        while time.monotonic()<deadline and (count(out/"h1415-winapp.log")<8 or
                count(out/"h1415-linapp.log")<8):
            need(win.poll() is None and linux.poll() is None,
                 "real original VPN owner quit during two concurrent client UDP")
            time.sleep(.3)
        win_stats=udp_stats(out/"h1415-winapp.log")
        linux_stats=udp_stats(out/"h1415-linapp.log")
        report["udp_stats"]={"windows":win_stats,"linux":linux_stats}
        need(win_stats["received"]>=8 and linux_stats["received"]>=8 and
             win_stats["reverse_received"]>=5 and linux_stats["reverse_received"]>=5,
             "actual two-OS UDP echo/reverse gate failed: "+
             json.dumps(report["udp_stats"],sort_keys=True))
        report["app_duplex"]="PASS_ACTUAL_TWO_OS_KERNEL_UDP"
        tcp_windows("10.66.0.2")
        tcp=wsl("ip","netns","exec",NS,"python3","-u",guestapp,"tcp","10.66.0.3",timeout=22)
        need("H1415_LINUX_NATIVE_KERNEL_TCP_ECHO_PASS" in tcp.stdout,
             "Linux native netns TCP application not genuinely echoed")
        report["tcp_duplex"]="PASS_ACTUAL_TWO_OS_KERNEL_TCP"
        if L3_DURATION:
            from m0_plan028_h1430_windows_linux_l3 import qualify
            report["l3"]=qualify(out,L3_DURATION,
               {"windows":out/"h1415-winapp.log","linux":out/"h1415-linapp.log"},
               udp_stats,need,tcp_windows,wsl,guestapp,
               {"windows":win,"linux":linux,"server":server,"echo":echo})
        before=count(out/"h1415-linapp.log")
        (out/"h1415-A-stop.flag").touch()
        stopwin(win)
        need(win.poll() is not None and win.returncode==0 and
             "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1"
             in (out/"h1415-windows.log").read_text(errors="replace"),
             "original Windows WAL/Rust signed one-client exact Stop failed")
        need(linux.poll() is None,"independent Linux client died with Windows A Stop")
        tcp=wsl("ip","netns","exec",NS,"python3","-u",guestapp,"tcp","10.66.0.3",timeout=22)
        need("H1415_LINUX_NATIVE_KERNEL_TCP_ECHO_PASS" in tcp.stdout,
             "Linux sibling TCP did not survive Windows exact owned Stop")
        deadline=time.monotonic()+15
        while time.monotonic()<deadline and count(out/"h1415-linapp.log")-before<5:
            need(linux.poll() is None,"Linux sibling owner exited during Windows Stop")
            time.sleep(.25)
        inc=count(out/"h1415-linapp.log")-before
        need(inc>=5,"true Linux sibling app UDP stalled after Windows Stop")
        report["windows_stop_linux_survives"]={"result":"PASS_TRUE_LINUX_KERNEL_UDP_TCP_AFTER_WINDOWS_OWNED_STOP","udp_rx_increment":inc}
        (out/"h1415-B-stop.flag").touch()
        linapp.wait(timeout=9)
        linux_kill(out/"h1415-linux.pid")
        marker(out/"h1415-linux.log","V4_PUBLIC_NATIVE_STOP_DRAINED role=client",linux,32)
        linux.wait(timeout=20)
        need(linux.returncode==0,"Linux exact original Stop process exit nonzero")
        linux_kill(out/"h1415-server.pid")
        marker(out/"h1415-server.log","V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server",server,32)
        server.wait(timeout=25)
        need(server.returncode==0 and
             "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" in
             (out/"h1415-server.log").read_text(errors="replace"),
             "original multi-client Go/Rust server shared TUN Stop not drained")
        report["stop"]="PASS_BOTH_CLIENTS_EXACT_OWNED_AND_SHARED_SERVER_STOP"
        report["normal_public"]="PASS_ACTUAL_WINDOWS_LINUX_NATIVE"
        report["mode_public"]="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal"
        report["status"]="PASS_SCOPED_ONE_SIGNED_WINDOWS_PLUS_ONE_INDEPENDENT_LINUX_CLIENT_SAME_TLS443_SERVER"
    except Exception as e:
        report["status"]="FAIL_OR_NOT_RUN"
        report["first_failure"]=str(e)[-1100:]
        report["udp_stats_on_failure"]={
            "windows":udp_stats(out/"h1415-winapp.log"),
            "linux":udp_stats(out/"h1415-linapp.log")}
        print("H1420_REAL_KERNEL_UDP_COUNTS "+
              json.dumps(report["udp_stats_on_failure"],sort_keys=True),flush=True)
        for role in ("winapp","linapp","echo"):
            p=out/("h1415-"+role+".log")
            if p.exists():
                rows=p.read_text(errors="replace").splitlines()[-6:]
                print("H1420_REAL_"+role.upper()+"_APP_TAIL "+
                      json.dumps(rows,ensure_ascii=True)[-650:],flush=True)
        print("H1415_ORIGINAL_REAL_FIRST_FAILURE "+str(e)[-900:],flush=True)
        # The failed original action retained only the Linux candidate's
        # terminal class=other, not the server's actual rejection phase.
        # Copy a bounded allowlist of product-owned stage markers ONLY on
        # failure. No credentials, packet contents, or per-packet hot probes.
        stage_prefixes=(
          "V4_PUBLIC_MULTI_ADMISSION_","V4_PUBLIC_MULTI_SESSION_READY",
          "V4_PUBLIC_MULTI_PEER_PERSONA",
          "V4_PUBLIC_COLD_STAGE","V4_PUBLIC_PATH_CANDIDATE",
          "V4_PUBLIC_PATH_RECONNECT_RETRY","V4_PUBLIC_NATIVE_COLD_TLS_RESULT",
          "V4_PUBLIC_ACTUAL_PEER_SYNACK_MSS","V4_PUBLIC_NORMAL_",
          "V4_PUBLIC_GO_RX_HANDOFF","V4_PUBLIC_LEASE_APPLIED",
          "V4_ORIGINAL_GO_CLIENT_NATIVE_READY","V4_PUBLIC_M2_",
          "V4_PUBLIC_FAKETCP_CLIENT_COLD_DATA_RTO")
        excerpt={}
        for role in ("server","linux","windows"):
            p=out/("h1415-"+role+".log")
            if not p.is_file():continue
            rows=[]
            for raw in p.read_text(errors="replace").splitlines():
                # Recognize exact product stage tags, never arbitrary raw Go
                # errors or passwords from TLS/CLI output.
                at=raw.find("V4_PUBLIC_")
                if at<0:at=raw.find("V4_ORIGINAL_GO_CLIENT_NATIVE_READY")
                if at<0:continue
                item=raw[at:at+250]
                if not item.startswith(stage_prefixes):continue
                rows.append(item)
            excerpt[role]=rows[-24:]
            for item in excerpt[role]:
                print("H1417_ORIGINAL_"+role.upper()+"_COLD_STAGE "+item,flush=True)
        (out/"h1417-original-cold-stage-summary.json").write_text(
            json.dumps({"source_sha":source,"classification":"DIAGNOSTIC_NOT_PRODUCT_PASS",
             "markers":excerpt},indent=2)+"\n")
        raise
    finally:
        for name in ("A","B"):(out/("h1415-"+name+"-stop.flag")).touch()
        stopwin(processes.get("h1415-windows"))
        linux_kill(out/"h1415-linux.pid")
        linux_kill(out/"h1415-server.pid")
        for name,p in processes.items():
            if p.poll() is None:
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.terminate()
        # No product owner may survive before physical veth/netns cleanup.
        if owned:
            try:
                report["owned_l2_restored"]=bool(l2_restore(ipv4,prefix,gw))
            except Exception as e:report["owned_l2_cleanup_error"]=str(e)[-400:]
        for f in fds:
            try:f.close()
            except Exception:pass
        for kind,p in local.items():
            try:wsl("rm","-f",guest[kind],check=False)
            except Exception:pass
            p.unlink(missing_ok=True)
        for p in (out/"h1415-key.pem",out/"h1415-route.hex"):
            p.unlink(missing_ok=True)
        remaining=[]
        for suffix in (".n4-owned-wal",".n4-owned-wal.routes"):
            x=pathlib.Path(str(out/"h1415-win-owned.json")+suffix)
            if x.exists():remaining.append(x.name)
        report["windows_wal_remaining"]=remaining
        if report["status"].startswith("PASS") and (not report["owned_l2_restored"] or remaining):
            report["status"]="FAIL_OWNED_RESOURCE_NOT_RESTORED"
        (out/"h1415-mixed-client-report.json").write_text(json.dumps(report,indent=2)+"\n")
        if report["status"].startswith("PASS"):
            (out/"normal-report.json").write_text(json.dumps({
                **report,"stop":"PASS_BOTH_OWNED"},indent=2)+"\n")
        if L3_DURATION and report["status"].startswith("PASS"):
            if report.get("l3",{}).get("status")=="PASS_SCOPED_REAL_1800S_BOTH_CLIENTS":
                print("H1430_REAL_SIGNED_WINDOWS_AND_SEPARATE_LINUX_1800S_NATIVE_PASS",flush=True)
            elif report.get("l3",{}).get("status")=="PASS_SCOPED_REAL_600S_BOTH_CLIENTS":
                print("H1453_REAL_SIGNED_WINDOWS_AND_SEPARATE_LINUX_600S_NATIVE_PASS_SCOPED",flush=True)
        print("H1415_ONE_WINDOWS_ONE_LINUX_ORIGINAL_COCONCURRENT_REPORT "+
             json.dumps({k:report.get(k) for k in (
                "status","app_duplex","tcp_duplex","stop",
                "windows_stop_linux_survives","owned_l2_restored",
                "windows_wal_remaining","first_failure")},sort_keys=True),flush=True)
        if report.get("status","").startswith("PASS")==False and not report.get("first_failure"):
            raise RuntimeError("H1415 owned bridge resources or Windows WAL not restored")
if __name__=="__main__":main()
