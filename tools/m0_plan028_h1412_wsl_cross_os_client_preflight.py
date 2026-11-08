#!/usr/bin/env python3
"""H1412 ONLY: real Windows host <-> bridged WSL2 eth0, plus independent
Linux network namespace underlay capability. NO VPN product or PASS claims.
All changes are owned on this ephemeral CI VM and restored in finally.
"""
import json,os,pathlib,socket,subprocess,sys,time,traceback
NAME="wbdp1412"; NS="wbdn1412"; HOST="wbdv1412"; CHILD="wbdc1412"
PORT=46098; ALIAS="10.26.250.1"; PEER="10.26.250.2"
OUT=pathlib.Path("result/wl-public");OUT.mkdir(parents=True,exist_ok=True)
REPORT=OUT/"h1412-wsl-bridge-feasibility.json"
def wsl(*argv,timeout=30,check=True):
    p=subprocess.run(["wsl.exe","-d","Ubuntu","-u","root","--",*argv],
        text=True,capture_output=True,timeout=timeout)
    if check and p.returncode:
        raise RuntimeError("guest command failed "+repr(argv[:6])+" rc="+str(p.returncode)+
            " stderr="+p.stderr[-480:]+" out="+p.stdout[-350:])
    return p
def ip(*argv,check=True):
    return wsl("ip",*argv,check=check).stdout.strip()
def shell(command,check=True):
    return wsl("sh","-c",command,check=check).stdout.strip()
def guestpath(local):
    p=pathlib.Path(local).resolve()
    return "/mnt/"+p.drive[0].lower()+"/"+"/".join(p.relative_to(p.anchor).parts)
def witness():
    return json.loads(ip("-j","-4","addr","show","dev","eth0"))[0]
def serve_guest():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.bind(("0.0.0.0",PORT));s.settimeout(.5)
    print("H1412_GUEST_BIND",flush=True)
    start=time.monotonic()
    while time.monotonic()-start<25:
        try:data,addr=s.recvfrom(512)
        except socket.timeout:continue
        if not data.startswith(b"H1412_REAL_"):continue
        print("H1412_GUEST_RX source="+addr[0]+" bytes="+str(len(data)),flush=True)
        s.sendto(data,addr)
    s.close()
def probe_guest():
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(.4)
    p=b"H1412_REAL_INDEPENDENT_LINUX_NAMESPACE"
    for _ in range(28):
        s.sendto(p,(ALIAS,PORT))
        try:
            data,addr=s.recvfrom(256)
            if data==p and addr[0]==ALIAS:
                print("H1412_LINUX_VETH_BRIDGE_REAL_KERNEL_UDP_ECHO_PASS",flush=True)
                return
        except socket.timeout:pass
    raise RuntimeError("Linux independent namespace physical veth UDP echo not received")
def probe_windows(addr):
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(.5)
    p=b"H1412_REAL_WINDOWS_VSWITCH_BRIDGED_WSL"
    for _ in range(25):
        s.sendto(p,(addr,PORT))
        try:
            data,peer=s.recvfrom(256)
            if data==p and peer[0]==addr:return {"real_windows_udp":True,"peer_ipv4":peer[0]}
        except socket.timeout:pass
    raise RuntimeError("actual Windows host UDP to original WSL2 guest IPv4 stopped at bridged eth0")
def main():
    state={"classification":"NOT_RUN","source":os.environ.get("GITHUB_SHA"),
           "scope":"underlay topology ONLY, NO product TLS/Go/Rust/Wintun or VPN PASS",
           "windows_client_instances":0,"linux_client_processes":0,"owned_l2_restored":False}
    before=witness()
    addresses=[a for a in before["addr_info"] if a["family"]=="inet" and a["scope"]=="global"]
    if len(addresses)!=1:raise RuntimeError("WSL eth0 has no unique global IPv4")
    ipv4=addresses[0]["local"];prefix=addresses[0]["prefixlen"]
    orig=ipv4+"/"+str(prefix)
    link=json.loads(ip("-j","link","show","dev","eth0"))[0]
    mac=link["address"]
    routes=json.loads(ip("-j","-4","route","show","default"))
    if len(routes)!=1 or not routes[0].get("gateway"):
        raise RuntimeError("WSL eth0 default gateway not uniquely owned")
    gateway=routes[0]["gateway"]
    state["orig_linux_subnet_prefix"]=prefix
    state["linux_network_namespace"]=NS
    state["guest_eth0_mac_before"]=mac
    state["bridge_mac_requested_same_as_eth0"]=True
    state["default_gateway_address_unmodified"]=True
    server=None;file=None
    try:
        ip("link","add",NAME,"type","bridge")
        ip("link","set","dev",NAME,"address",mac)
        ip("link","set","dev",NAME,"up")
        ip("addr","add",orig,"dev",NAME)
        ip("link","set","dev","eth0","master",NAME)
        ip("addr","del",orig,"dev","eth0")
        ip("route","replace","default","via",gateway,"dev",NAME)
        ip("addr","add",ALIAS+"/24","dev",NAME)
        ip("netns","add",NS)
        ip("link","add",HOST,"type","veth","peer","name",CHILD,"netns",NS)
        ip("link","set",HOST,"master",NAME)
        ip("link","set",HOST,"up")
        ip("-n",NS,"link","set","lo","up")
        ip("-n",NS,"addr","add",PEER+"/24","dev",CHILD)
        ip("-n",NS,"link","set",CHILD,"up")
        ip("-n",NS,"route","add","default","via",ALIAS,"dev",CHILD)
        bridge=json.loads(ip("-j","link","show","dev",NAME))[0]
        if bridge["address"].lower()!=mac.lower():raise RuntimeError("bridge MAC unexpectedly changed")
        state["real_linux_BRIDGE_and_NETNS_install"]="PASS"
        file=(OUT/"h1412-udp-server.log").open("w")
        guest=guestpath(pathlib.Path(__file__))
        server=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
            "python3","-u",guest,"--guest-server"],stdout=file,stderr=subprocess.STDOUT)
        start=time.monotonic()
        while time.monotonic()-start<8:
            file.flush()
            if (OUT/"h1412-udp-server.log").read_text(errors="replace").find("H1412_GUEST_BIND")>=0:break
            if server.poll() is not None:raise RuntimeError("actual Linux UDP listener exited")
            time.sleep(.15)
        else:raise RuntimeError("actual bridged WSL UDP listener unready")
        x=wsl("ip","netns","exec",NS,"python3","-u",guest,"--guest-client",timeout=25)
        if "H1412_LINUX_VETH_BRIDGE_REAL_KERNEL_UDP_ECHO_PASS" not in x.stdout:
            raise RuntimeError("independent Linux namespace UDP return not proven "+x.stdout[-300:])
        state["linux_independent_netns_real_L2_UDP"]="PASS"
        state["windows_real_vswitch_to_guest_bridge"]=probe_windows(ipv4)
        state["classification"]="PASS_SCOPED_BRIDGED_WSL2_UNDERLAY_FEASIBILITY_NOT_VPN_PRODUCT"
    except Exception as e:
        state["classification"]="ENVIRONMENT_BLOCKED_UNDERLAY_PREFLIGHT"
        state["first_failure"]=str(e)[-700:]
        raise
    finally:
        try:
            # This CI test owns only these exact names; do not alter foreign
            # guests, DHCP leases, route owners or the Windows host default.
            if server and server.poll() is None:
                server.terminate()
                try:server.wait(timeout=4)
                except subprocess.TimeoutExpired:server.kill()
            if file:file.close()
            ip("netns","del",NS,check=False)
            ip("link","del",HOST,check=False)
            # Restore eth0 original L3 before removing bridge master.
            ip("link","set","dev","eth0","nomaster",check=False)
            eth=witness()
            live=[a["local"]+"/"+str(a["prefixlen"]) for a in eth["addr_info"] if a["family"]=="inet"]
            if orig not in live:ip("addr","add",orig,"dev","eth0")
            ip("route","replace","default","via",gateway,"dev","eth0")
            ip("link","del",NAME,check=False)
            restored=witness()
            present=[a["local"]+"/"+str(a["prefixlen"]) for a in restored["addr_info"] if a["family"]=="inet"]
            live_routes=json.loads(ip("-j","-4","route","show","default"))
            state["owned_l2_restored"]=(orig in present and
                any(x.get("dev")=="eth0" and x.get("gateway")==gateway for x in live_routes) and
                wsl("ip","link","show","dev",NAME,check=False).returncode!=0 and
                wsl("ip","netns","exec",NS,"true",check=False).returncode!=0)
            if not state["owned_l2_restored"]:
                state["cleanup_failure"]="owned eth0 IPv4 / default gateway / bridge or netns mismatch"
        except Exception as e:
            state["cleanup_failure"]=type(e).__name__+":"+str(e)[-350:]
        REPORT.write_text(json.dumps(state,indent=2)+"\n")
        print("H1412_REAL_TOPOLOGY_RESULT "+json.dumps(state,sort_keys=True),flush=True)
        if not state["owned_l2_restored"]:raise RuntimeError("H1412 exact OS bridge cleanup failed")
    if state["classification"].startswith("PASS"):print("H1412_BRIDGED_WINDOWS_PLUS_LINUX_CLIENT_INFRA_PRECHECK_PASS",flush=True)
if __name__=="__main__":
    if sys.platform=="linux":
        if sys.argv[1:]==["--guest-server"]:serve_guest()
        elif sys.argv[1:]==["--guest-client"]:probe_guest()
        else:raise SystemExit("guest subcommand required")
    else:main()
