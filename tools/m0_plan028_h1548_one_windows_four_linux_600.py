#!/usr/bin/env python3
"""PLAN028 H1548: 1 genuine signed Windows Wintun + 4 native Linux netns
client accounts, 1 original Go/Rust TLS443 shared Linux TUN server, 600s.

Windows hosted VM contains ONE Wintun (not the superseded Windows5 case).
Four Linux clients use independent WSL2 network namespaces and real TUNs.
Full physical outer bytes include WSL eth0 IFB+egress and eight Linux
veth qdiscs, never calculated from application target or FEC copies.
All setup must be owned, source-locked, finally-restored. No mock network.
"""
import argparse,hashlib,json,os,pathlib,re,secrets,shlex,subprocess,sys,time
from m0_plan028_h1415_windows_linux_independent_clients import (
    l2_setup,l2_restore,marker,stopwin,linux_kill,guestpath,ip,wsl,
    NAME,NS,HOST,CHILD,ALIAS,PEER,witness)
from m0_plan028_h1506_windows_five_native_600 import (
    netem,write_rate_control)
from m0_plan028_h1430_windows_linux_l3 import vm_budget_tick
ROOT=pathlib.Path.cwd();OUT=ROOT/"result"/"wl-public"
OUT.mkdir(parents=True,exist_ok=True)
NAMES=("alice","bob","carol","dave","erin")
MODES=("normal","fec-auto","game2","game4","fec-fixed")
IPS=("10.66.0.2","10.66.0.3","10.66.0.4","10.66.0.5","10.66.0.6")
NS4=(NS,"wbm1548c","wbm1548d","wbm1548e")
HOST4=(HOST,"wbh1548c","wbh1548d","wbh1548e")
CHILD4=(CHILD,"wbc1548c","wbc1548d","wbc1548e")
OUTER4=(PEER,"10.26.250.3","10.26.250.4","10.26.250.5")
BAND=(250,300)
EXTRAS={
 "bob":("--record-cipher","chacha20-poly1305"),
 "carol":("--record-cipher","aes-256-gcm"),
 "dave":("--game-fec","fixed6","--record-cipher","chacha20-poly1305"),
 "erin":("--fec-profile","6","--outer-mtu","1280","--record-cipher","aes-128-gcm"),
}

def need(cond,reason):
    if not cond:raise RuntimeError(reason)

def original_file(p):
    p=pathlib.Path(p)
    need(p.is_file() and p.stat().st_size>10000,"missing actual original source product "+str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()

def install_four_veth_200ms(loss,extra_owned):
    # H1415 already owns first Linux peer under an exact ephemeral L2 bridge.
    for ns,host,child,addr in zip(NS4[1:],HOST4[1:],CHILD4[1:],OUTER4[1:]):
        need(wsl("ip","netns","exec",ns,"true",check=False).returncode!=0,
             "foreign Linux netns "+ns)
        need(wsl("ip","link","show","dev",host,check=False).returncode!=0,
             "foreign Linux veth "+host)
        ip("netns","add",ns)
        extra_owned.append((ns,host))
        ip("link","add",host,"type","veth","peer","name",child,"netns",ns)
        ip("link","set",host,"master",NAME);ip("link","set",host,"up")
        ip("-n",ns,"link","set","lo","up")
        ip("-n",ns,"addr","add",addr+"/24","dev",child)
        ip("-n",ns,"link","set",child,"up")
        ip("-n",ns,"route","add","default","via",ALIAS,"dev",child)
        wsl("ip","netns","exec",ns,"iptables","-I","OUTPUT",
            "-p","tcp","--tcp-flags","RST","RST","-j","DROP")
    # Both directions of every real Linux client outer veth. The WSL
    # eth0 Windows-only physical 443..446 netem is separate, no overlap.
    br=json.loads(ip("-j","link","show","dev",NAME))[0]
    bridge_mac=br["address"]
    for ns,host,child,addr in zip(NS4,HOST4,CHILD4,OUTER4):
        nic=json.loads(ip("-n",ns,"-j","link","show","dev",child))[0]
        ip("-n",ns,"neigh","replace",ALIAS,"lladdr",bridge_mac,
           "nud","permanent","dev",child)
        ip("neigh","replace",addr,"lladdr",nic["address"],
           "nud","permanent","dev",NAME)
        wsl("tc","qdisc","add","dev",host,"root","handle","20:","netem",
            "delay","200ms","loss",str(loss)+"%","limit","32768")
        wsl("ip","netns","exec",ns,"tc","qdisc","add","dev",child,
            "root","handle","10:","netem","delay","200ms","loss",
            str(loss)+"%","limit","32768")
    return {"namespaces":list(NS4),"host_veths":list(HOST4),
            "client_veths":list(CHILD4),"physical_client_ips":list(OUTER4),
            "bridge_mac":bridge_mac,"loss":loss,"oneway_delay_ms":200}

def linux_outer_snapshot():
    # One real WSL process reads exactly eight kernel netem qdiscs.
    # Neither a configured RATE nor iperf/application bytes are counted.
    script="""import json,subprocess,sys
pairs=json.loads(sys.argv[1]);data={}
for name,argv in pairs.items():
 p=subprocess.run(argv,capture_output=True,text=True,timeout=3)
 if p.returncode:raise RuntimeError(name+" "+p.stderr[-100:])
 v=[x for x in json.loads(p.stdout) if x.get("kind")=="netem"]
 if len(v)!=1:raise RuntimeError(name+" real netem not present "+str(v))
 q=v[0];data[name]={"bytes":int(q["bytes"]),"packets":int(q["packets"]),
                    "drops":int(q.get("drops",0))}
print(json.dumps(data,sort_keys=True))
"""
    specs={}
    for ns,host,child in zip(NS4,HOST4,CHILD4):
        specs[ns+"/client_egress"]=["ip","netns","exec",ns,"tc","-s","-j","qdisc","show","dev",child]
        specs[ns+"/server_to_client"]=["tc","-s","-j","qdisc","show","dev",host]
    x=wsl("python3","-c",script,json.dumps(specs),timeout=30).stdout
    return json.loads(x.strip().splitlines()[-1])

def source_snap(loss):
    kernel=netem("sample",loss)
    native=linux_outer_snapshot()
    return {"time":time.monotonic(),
        "windows_true_outer":{
            "windows_to_server":kernel["actual_ingress_windows_to_linux"],
            "server_to_windows":kernel["actual_egress_linux_to_windows"]},
        "linux_true_outer":native}

def delta(first,second):
    dt=second["time"]-first["time"]
    need(7<=dt<=30,"invalid 10s real outer observation interval "+str(dt))
    parts={}
    def d(a,b,label):
        diff=b["bytes"]-a["bytes"]
        need(diff>=0,"kernel qdisc byte counters reset "+label)
        return diff
    for role in first["windows_true_outer"]:
        parts["windows/"+role]=d(first["windows_true_outer"][role],
                                  second["windows_true_outer"][role],role)
    for role in first["linux_true_outer"]:
        parts["linux/"+role]=d(first["linux_true_outer"][role],
                                second["linux_true_outer"][role],role)
    up=parts["windows/windows_to_server"]+sum(
        v for k,v in parts.items() if k.startswith("linux/") and k.endswith("/client_egress"))
    down=parts["windows/server_to_windows"]+sum(
        v for k,v in parts.items() if k.startswith("linux/") and k.endswith("/server_to_client"))
    return {"sample_s":round(dt,3),"up_mbps":round(up*8/dt/1e6,3),
       "down_mbps":round(down*8/dt/1e6,3),
       "both_full_outer_mbps":round((up+down)*8/dt/1e6,3),
       "source_counter_bytes_delta":parts}

def stop_guard(p):
    if p is None or p.poll() is not None:return
    try:p.terminate();p.wait(timeout=8)
    except subprocess.TimeoutExpired:p.kill()

def make_linux_script(name,body):
    local=OUT/name;local.write_bytes(body.encode("utf-8"))
    return guestpath(local)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scene",choices=("loss0","loss30"),default=os.environ.get("WBD_PLAN028_MIXED_SCENE"))
    a=ap.parse_args()
    need(a.scene in ("loss0","loss30"),"unqualified new mixed scene")
    source=os.environ["GITHUB_SHA"];need(len(source)==40,"wrong original source")
    need(os.environ.get("LINUX_BINARY_SRC")==source,"Go/Rust Windows/Linux SOURCE mismatch")
    need(os.environ.get("WBD_PLAN028_FIVE_REAL_CLIENTS")!="1",
         "no GUI singleton bypass: this case has exactly ONE Windows Wintun")
    loss=0 if a.scene=="loss0" else 30
    cli=OUT/"wbd-client-embedded.exe";ldir=ROOT/"linux-product"
    hashes={n:original_file(p) for n,p in {
        "windows_original_go":cli,"windows_original_rust":OUT/"wbd_engine.dll",
        "windows_signed_wintun":OUT/"wintun.dll",
        "linux_original_go_server":ldir/"wbd-v4-server",
        "linux_original_go_client":ldir/"wbd-v4-client",
        "linux_original_rust":ldir/"libwbd_engine.so"}.items()}
    report={"schema_version":1,"plan":"PLAN028","scope":"1_REAL_WINDOWS_WINTUN_4_LINUX_NETNS_1_SHARED_TLS443_SERVER",
       "source_sha":source,"scene":a.scene,"status":"NOT_RUN",
       "Windows_native_clients":1,"Linux_native_clients":4,"Linux_shared_server":1,
       "physical_delay_each_direction_ms":200,"physical_loss_percent":loss,
       "true_full_outer_both_directions_target_mbps":list(BAND),
       "base_inner_offer_each_direction_mbps":[8,14,11,6,9] if loss==0 else [10,22,18,10,14],
       "original_product_binary_sha256":hashes,
       "superseded_Windows5_one_host":"NOT_REQUIRED_BY_LATEST_USER",
       "physical_source_IP_switch_while_WSL_bridge_active":"NOT_TRIGGERED_IN_THIS_SCOPE"}
    before=witness()
    addresses=[x for x in before.get("addr_info",[]) if
               x["family"]=="inet" and x.get("scope")=="global"]
    need(len(addresses)==1,"real WSL2 host physical IPv4 ambiguous")
    ipv4,prefix=addresses[0]["local"],addresses[0]["prefixlen"]
    mac=json.loads(ip("-j","link","show","dev","eth0"))[0]["address"]
    routes=json.loads(ip("-j","-4","route","show","default"))
    need(len(routes)==1 and routes[0].get("gateway"),"WSL eth0 default gateway ambiguous")
    gateway=routes[0]["gateway"]
    records=[];owners={};fds=[];original_ready={}
    owns_l2=False;owns_win_netem=False;window=None;extra_owned=[]
    names=("alice","bob","carol","dave","erin")
    guest_root=guestpath(OUT);guest_build=guestpath(ldir)
    users={who:"h1548-"+secrets.token_hex(12) for who in names}
    private={
       "route":OUT/"h1548-private-route.hex",
       "users":OUT/"h1548-private-users.json",
       "leases":OUT/"h1548-private-leases.json",
       "key":OUT/"h1548-private-tls-key.pem"}
    private["route"].write_text(secrets.token_hex(32)+"\n")
    private["users"].write_text(json.dumps(users)+"\n")
    private["leases"].write_text(json.dumps({who:IPS[i]+"/32" for i,who in enumerate(names)})+"\n")
    for p in list(private.values())[:3]:os.chmod(p,0o600)
    guestsecret={name:"/run/wbd-h1548-"+os.environ["GITHUB_RUN_ID"]+"-"+name for name in ("route","users","leases")}
    barrier=OUT/"h1548-start.flag";control=OUT/"h1548-rate-control.json"
    control.write_text(json.dumps({"scale":1.0})+"\n")
    barrier.unlink(missing_ok=True)
    report_path=OUT/("h1548-"+a.scene+"-strict-native-report.json")
    app_py=guestpath(ROOT/"tools/m0_plan028_h1548_mixed_os_app.py")
    def spawn(name,command,with_input=False):
        log=OUT/(name+".log");f=log.open("w");fds.append(f)
        p=subprocess.Popen(command,stdin=subprocess.PIPE if with_input else None,
          stdout=f,stderr=subprocess.STDOUT,text=with_input)
        owners[name]=p
        return p
    try:
        for name in guestsecret:
            wsl("install","-m","600",guestpath(private[name]),guestsecret[name])
        wsl("openssl","req","-x509","-newkey","rsa:2048","-sha256",
            "-days","1","-nodes","-keyout",guestpath(private["key"]),
            "-out",guest_root+"/h1548-cert.pem",
            "-subj","/CN=wbd-v4.example.test",
            "-addext","subjectAltName=DNS:wbd-v4.example.test",timeout=42)
        need(wsl("ip","link","show","dev",NAME,check=False).returncode!=0,
             "foreign WSL owned Linux bridge name; refuse network takeover")
        owns_l2=True
        l2_setup(ipv4,prefix,mac,gateway)
        report["real_owned_linux_underlay"]=install_four_veth_200ms(loss,extra_owned)
        # Source-lock any owner to this guest bridge, never a second Wintun.
        server=make_linux_script("h1548-server.sh",
          "#!/bin/sh\nset -eu\necho $$ > '"+guest_root+"/h1548-server.pid'\n"
          "exec env LD_LIBRARY_PATH='"+guest_build+"' '"+guest_build+"/wbd-v4-server'"
          " --raw-interface "+NAME+" --local-ip "+ipv4+" --local-port 443"
          " --tun-name wbdwl48 --tun-ipv4 10.66.0.1/24"
          " --server-name wbd-v4.example.test"
          " --route-key-hex-file '"+guestsecret["route"]+"'"
          " --users-file '"+guestsecret["users"]+"'"
          " --manual-client-leases-file '"+guestsecret["leases"]+"'"
          " --tls-cert '"+guest_root+"/h1548-cert.pem'"
          " --tls-key '"+guestpath(private["key"])+"'"
          " --mode shared --peer-persona windows11 --outer-repair on\n")
        serverproc=spawn("h1548-server",["wsl.exe","-d","Ubuntu","-u","root","--","sh",server])
        marker(OUT/"h1548-server.log","V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443",serverproc,80)
        # Windows protected TCP443 must be impaired before the original SYN.
        netem("arm",loss);owns_win_netem=True
        # Windows signed original one-client native owner: no GUI singleton
        # bypass, no global route/WFP collision with a second Wintun.
        winargs=[str(cli),"--native-v4-product","--control-stdin",
            "--server-ip",ipv4,"--server-port","443","--source-port","41031",
            "--server-name","wbd-v4.example.test",
            "--route-key-hex-file",str(private["route"]),
            "--tls-ca-pem",str(OUT/"h1548-cert.pem"),
            "--username","alice","--password",users["alice"],
            "--tunnel-id","102030405060708090a0b0c0d0e0f001",
            "--installation-id","445566778899aabbccddeeff00112233",
            "--lease4","10.66.0.2/32","--adapter","WBDWLMAIN",
            "--state-path",str(OUT/"h1548-win-owner.json"),
            "--lanes","1","--fec-mode","off","--fec.mode","off",
            "--route-mode","bypass-lan","--outer-repair","on"]
        window=spawn("h1548-windows-alice",winargs,with_input=True)
        # Add all four true Linux TUNs, identities and unique source
        # ports; the same original Linux server authentically decides.
        for i,who in enumerate(names[1:],1):
            args=[
              "--raw-interface",CHILD4[i-1],"--local-ip",OUTER4[i-1],
              "--local-port",str(42031+i*1000),
              "--peer-ip",ipv4,"--peer-port","443",
              "--tun-name","wbd48"+who[0],
              "--server-name","wbd-v4.example.test",
              "--route-key-hex-file",guestsecret["route"],
              "--tls-ca-pem",guest_root+"/h1548-cert.pem",
              "--username",who,"--password",users[who],
              "--auto-ip","--installation-id-file","/run/wbd-h1548-"+os.environ["GITHUB_RUN_ID"]+"-install-"+who,
              "--mode",MODES[i],*EXTRAS[who],
              "--rotation-interval",str((97,109,103,117,127)[i])+"s",
              "--rotation-jitter","5s"]
            script=make_linux_script("h1548-linux-"+who+".sh",
              "#!/bin/sh\nset -eu\necho $$ > '"+guest_root+"/h1548-"+who+".pid'\n"
              "exec env LD_LIBRARY_PATH='"+guest_build+"' '"+guest_build+"/wbd-v4-client' "+
              shlex.join(args)+"\n")
            spawn("h1548-linux-"+who,["wsl.exe","-d","Ubuntu","-u","root","--",
                  "ip","netns","exec",NS4[i-1],"sh",script])
        marker(OUT/"h1548-windows-alice.log","WBD_WINDOWS_CLIENT_READY",window,150)
        readback=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
            "-Command","$a=Get-NetAdapter -IncludeHidden -Name 'WBDWLMAIN' -ErrorAction Stop;"+
            "$ip=Get-NetIPAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4 -ErrorAction Stop;"+
            "@{guid=[string]$a.InterfaceGuid;ip=@($ip|ForEach-Object IPAddress)}|ConvertTo-Json -Compress"],
            capture_output=True,text=True,timeout=20)
        need(readback.returncode==0 and
             "10.66.0.2" in json.loads(readback.stdout).get("ip",[]),
             "actual signed Windows Wintun Alice IPv4 /32 OS readback failed")
        original_ready["alice"]="REAL_SIGNED_WINTUN_NATIVE_TLS443_READY_OS_IP"
        for i,who in enumerate(names[1:],1):
            p=owners["h1548-linux-"+who]
            marker_name=("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes="+
              ("2" if who=="carol" else "4")) if who in ("carol","dave") else "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client"
            marker(OUT/("h1548-linux-"+who+".log"),marker_name,p,145)
            current=json.loads(ip("-n",NS4[i-1],"-j","-4","addr","show",
                                  "dev","wbd48"+who[0]))
            inner=[entry["local"] for row in current for entry in row.get("addr_info",[])
                   if entry.get("family")=="inet"]
            need(IPS[i] in inner,"Linux actual native TUN /32 OS readback missing "+who)
            ip("-n",NS4[i-1],"route","replace","10.66.0.1/32","dev","wbd48"+who[0])
            original_ready[who]="REAL_LINUX_NAMESPACE_NATIVE_TLS443_RUST_TUN_OS_IP"
        report["original_OS_ready"]=original_ready
        # Give each account its OWN direct client socket and one of five
        # independent server app sockets; 600s both real UDP and framed TCP.
        serverApp=spawn("h1548-app-server",["wsl.exe","-d","Ubuntu","-u","root","--","env",
            "GITHUB_SHA="+source,"python3","-u",app_py,
            "--role","server","--scene",a.scene,
            "--barrier",guestpath(barrier),"--control",guestpath(control),
            "--out",guest_root+"/h1548-app-server.json"])
        winApp=spawn("h1548-app-windows",[
            sys.executable,"-u",str(ROOT/"tools/m0_plan028_h1548_mixed_os_app.py"),
            "--role","windows","--index","0","--scene",a.scene,
            "--barrier",str(barrier),"--control",str(control),
            "--out",str(OUT/"h1548-app-windows.json")])
        for i,who in enumerate(names[1:],1):
            spawn("h1548-app-"+who,["wsl.exe","-d","Ubuntu","-u","root","--",
               "ip","netns","exec",NS4[i-1],"env","GITHUB_SHA="+source,
               "python3","-u",app_py,"--role","linux-client","--index",str(i),
               "--scene",a.scene,"--barrier",guestpath(barrier),
               "--control",guestpath(control),
               "--out",guest_root+"/h1548-app-"+who+".json"])
        for who in ("server","windows","bob","carol","dave","erin"):
            marker(OUT/("h1548-app-"+who+".log"),"H1548_REAL_INNER_OS_APP_BOUND",
                   owners["h1548-app-"+who],95)
        baseline=source_snap(loss)
        barrier.write_text("ORIGINAL_ONE_WINDOWS_FOUR_LINUX_REAL_600S_"+source+"\n")
        t0=time.monotonic();last=baseline;scales=[];windows=[];capacity=0
        prev_budget=vm_budget_tick()
        while time.monotonic()-t0<602:
            elapsed=time.monotonic()-t0
            for who in ("h1548-server","h1548-windows-alice",
                         "h1548-linux-bob","h1548-linux-carol",
                         "h1548-linux-dave","h1548-linux-erin"):
                need(owners[who].poll() is None,
                     "original OS-owned TLS/Rust process terminated before product Stop "+who)
            if elapsed>=600:break
            # Samples are every real 10 seconds, no planned FEC sources.
            remaining=max(0,10-(time.monotonic()-last["time"]))
            if remaining:time.sleep(min(remaining,8))
            now=source_snap(loss)
            vals=delta(last,now)
            last=now
            tick=time.monotonic()-t0
            vals.update({"elapsed_s":round(tick,2),
               "phase":"warmup" if tick<10 else "first_wave" if tick<100 else
                 "sustained" if tick<280 else "overload" if tick<370 else "recovery",
               "calibration_scale":scales[-1] if scales else 1.0})
            budget=vm_budget_tick()
            idle=budget["idle"]-prev_budget["idle"]
            tot=budget["kernel"]+budget["user"]-prev_budget["kernel"]-prev_budget["user"]
            busy=100*(1-idle/tot) if tot>0 else None
            vals.update({"windows_cpu_busy_pct":round(busy,2) if busy is not None else None,
               "windows_available_gib":budget["avail_gib"]})
            if (busy is not None and busy>98) or budget["avail_gib"]<1:
                capacity+=vals["sample_s"]
            else:capacity=0
            need(capacity<30,"CAPACITY_LIMITED Windows host 30s CPU>=98 or RAM<1GiB")
            windows.append(vals)
            if 30<=tick<320 and vals["both_full_outer_mbps"]>=1:
                current=scales[-1] if scales else 1.0
                factor=min(1.10,max(.90,275/vals["both_full_outer_mbps"]))
                scale=round(min(1.35,max(.65,current*factor)),4)
                write_rate_control(control,scale)
                scales.append(scale)
            print("H1548_REAL_ONE_WIN_FOUR_LINUX_FULL_KERNEL_OUTER_10S "+
                  json.dumps(vals,separators=(",",":")),flush=True)
        report["actual_original_kernel_outer_samples"]=windows
        report["dynamic_outer_rate_scale"]=scales
        for who in ("server","windows","bob","carol","dave","erin"):
            p=owners["h1548-app-"+who]
            p.wait(timeout=65)
            need(p.returncode==0,"original per OS app failed "+who+" "+(OUT/("h1548-app-"+who+".log")).read_text(errors="replace")[-450:])
        apps={who:json.loads((OUT/("h1548-app-"+who+".json")).read_text())
              for who in ("server","windows","bob","carol","dave","erin")}
        for who,a0 in apps.items():
            need(a0["status"]=="COMPLETE_TRUE_600S_ORIGINAL_GO_RUST_INNER_APPLICATION"
                 and a0["elapsed_s"]>=600,
                 "real 600s application missing or shortened "+who)
        server_stats=apps["server"]
        checks={}
        for i,who in enumerate(names):
            client=apps["windows" if who=="alice" else who]
            up=client["actual_udp_kernel_send"][who]
            up_rx=server_stats["actual_udp_unique_received"][who]
            down=server_stats["actual_udp_kernel_send"][who]
            down_rx=client["actual_udp_unique_received"][who]
            ct=client["tcp_real_frames"][who];st=server_stats["tcp_real_frames"][who]
            r={"up_udp_sent":up,"up_udp_unique_received":up_rx,
               "down_udp_sent":down,"down_udp_unique_received":down_rx,
               "tcp_client":ct,"tcp_server":st,
               "client_max_first_delivery_gap_ms":client["max_active_udp_interarrival_ms"][who],
               "server_max_first_delivery_gap_ms":server_stats["max_active_udp_interarrival_ms"][who]}
            checks[who]=r
            need(min(up,up_rx,down,down_rx)>100,
                 "original client/server UDP not real or missing "+who)
            need(ct["received"]>=30 and st["received"]>=30 and
                 ct["sent"]>=30 and st["sent"]>=30 and ct["invalid"]==st["invalid"]==0,
                 "original two-way framed TCP not actually received "+who)
            if loss==0:
                need(up==up_rx and down==down_rx,
                     "configured zero-loss genuine unique UDP missing "+who)
            else:
                need(up_rx/up>.40 and down_rx/down>.40,
                     "30pct loss original native data delivery collapsed "+who)
            need(r["client_max_first_delivery_gap_ms"]<3000 and
                 r["server_max_first_delivery_gap_ms"]<3000,
                 "original business seconds-scale continuous receive blackout "+who)
        report["five_original_account_kernel_application"]=checks
        steady=[x for x in windows if x["phase"] in ("sustained","recovery") and
                x["sample_s"]>=8]
        actual=sum(x["both_full_outer_mbps"] for x in steady)/len(steady) if steady else 0
        inband=sum(250<=x["both_full_outer_mbps"]<=300 for x in steady)
        report["kernel_outer_250_300_result"]={
            "measured_steady_mean_mbps":round(actual,3),"real_10s_windows":len(steady),
            "within_target_windows":inband,"target_band":[250,300],
            "up_and_down_observed":any(x["up_mbps"]>30 and x["down_mbps"]>30 for x in steady)}
        need(len(steady)>=28 and 250<=actual<=300 and
             inband>=.70*len(steady) and
             report["kernel_outer_250_300_result"]["up_and_down_observed"],
             "original true 250-300 Mbps outer both direction real kernel gate unmet")
        # Source Go native M4 and exact old/new owner log receipts are
        # independent of app data. A client READY alone is never M4 PASS.
        server_text=(OUT/"h1548-server.log").read_text(errors="replace")
        need(server_text.count("V4_PUBLIC_GAME_GROUP_LANE_READY role=server")>=2,
             "original server real Game2/4 authenticated M4 group not proven")
        need(server_text.count("V4_PUBLIC_MIXED_NORMAL_READY role=server")>=1,
             "original Windows Normal post-TLS M4 initial server not proven")
        for who in ("bob","erin"):
            log=(OUT/("h1548-linux-"+who+".log")).read_text(errors="replace")
            need("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client" in log,
                 "original Linux path authenticated B generation not shown "+who)
        report["authenticated_original_server_M4_summary"]={
            "Game2_Game4_initial_full_group_events":server_text.count("V4_PUBLIC_GAME_GROUP_LANE_READY role=server"),
            "Normal_original_M4_events":server_text.count("V4_PUBLIC_MIXED_NORMAL_READY role=server"),
            "Normal_B_after_authenticated_Health":server_text.count("V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server"),
            "Game_one_lane_hot_M4":server_text.count("V4_PUBLIC_GAME_SINGLE_LANE_READY role=server")}
        # Existing Windows stop must not destroy four independent Linux owners.
        stopwin(window)
        marker(OUT/"h1548-windows-alice.log",
               "WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1",window,35)
        need(all(owners["h1548-linux-"+who].poll() is None for who in names[1:]),
             "one Windows original owned Stop killed independent Linux sibling")
        report["windows_exact_original_Stop"]="PASS_WINTUN_WAL_RUST_DISCONNECTED"
        for who in names[1:]:linux_kill(OUT/("h1548-"+who+".pid"))
        for who in names[1:]:
            marker(OUT/("h1548-linux-"+who+".log"),
                   "V4_PUBLIC_NATIVE_STOP_DRAINED role=client",owners["h1548-linux-"+who],35)
        linux_kill(OUT/"h1548-server.pid")
        marker(OUT/"h1548-server.log","V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server",serverproc,40)
        report["all_six_original_owned_Stop"]="PASS_EXACT_SIGNED_WIN_ONE_PLUS_FOUR_LINUX_AND_SHARED_SERVER"
        report["status"]="PASS_SCOPED_REAL_WIN1_LINUX4_600S_OUTER_250_300_"+a.scene.upper()
    except BaseException as e:
        report["status"]="FAIL_OR_NOT_RUN_TRUE_ORIGINAL_OS"
        report["first_error"]=repr(e)
        print("H1548_MIXED_ONE_WINDOWS_FOUR_LINUX_FIRST_ERROR "+repr(e),flush=True)
        for name in ("h1548-server","h1548-windows-alice",
                     "h1548-linux-bob","h1548-linux-carol",
                     "h1548-linux-dave","h1548-linux-erin"):
            logfile=OUT/(name+".log")
            if logfile.exists():
                msg=logfile.read_text(errors="replace")
                print("H1548_ORIGINAL_"+name.upper().replace("-","_")+"_LAST_STAGE "+
                      json.dumps(msg.splitlines()[-10:])[-1700:],flush=True)
        raise
    finally:
        if window:stopwin(window)
        for who in names[1:]:linux_kill(OUT/("h1548-"+who+".pid"))
        linux_kill(OUT/"h1548-server.pid")
        for role,p in owners.items():
            if p.poll() is None:stop_guard(p)
        if owns_win_netem:
            try:netem("clean",loss);report["windows_eth0_original_netem_clean"]="PASS"
            except Exception as e:report["windows_eth0_original_netem_clean"]="FAIL "+repr(e)
        if owns_l2:
            try:
                # Test-only Linux veth qdiscs disappear only with our
                # owned netns/veth. Never remove the management eth0.
                for ns,host in reversed(extra_owned):
                    ip("netns","del",ns,check=False)
                    ip("link","del",host,check=False)
                report["original_WSL_bridge_restored"]=bool(l2_restore(ipv4,prefix,gateway))
                for ns,host in zip(NS4,HOST4):
                    need(wsl("ip","netns","exec",ns,"true",check=False).returncode!=0,
                         "still-live owned namespace after Stop "+ns)
                    need(wsl("ip","link","show","dev",host,check=False).returncode!=0,
                         "still-live owned Linux veth after Stop "+host)
            except Exception as e:report["original_WSL_bridge_restored"]="FAIL "+repr(e)
        for handle in fds:
            try:handle.close()
            except OSError:pass
        for name,guest in guestsecret.items():
            try:wsl("rm","-f",guest,check=False)
            except Exception:pass
        for p in private.values():p.unlink(missing_ok=True)
        for p in [OUT/"h1548-server.sh"]+[OUT/("h1548-linux-"+who+".sh") for who in names[1:]]:
            p.unlink(missing_ok=True)
        for p in (OUT/"h1548-cert.pem",barrier,control):p.unlink(missing_ok=True)
        wal=[str(p.name) for suffix in (".n4-owned-wal",".n4-owned-wal.routes")
             for p in [pathlib.Path(str(OUT/"h1548-win-owner.json")+suffix)] if p.exists()]
        report["Windows_original_WAL_leftover"]=wal
        if report["status"].startswith("PASS") and (wal or
           report.get("windows_eth0_original_netem_clean")!="PASS" or
           report.get("original_WSL_bridge_restored") is not True):
            report["status"]="FAIL_ORIGINAL_OWNED_OS_RESOURCE_NOT_RESTORED"
        report_path.write_text(json.dumps(report,indent=2)+"\n")
        print("H1548_FINAL_ORIGINAL_REAL_ONE_WIN_FOUR_LINUX "+
              json.dumps({k:v for k,v in report.items() if k in
                 ("status","source_sha","scene","first_error",
                  "kernel_outer_250_300_result","all_six_original_owned_Stop",
                  "Windows_original_WAL_leftover","original_WSL_bridge_restored",
                  "windows_eth0_original_netem_clean")},sort_keys=True),flush=True)
        if report["status"].startswith("PASS"):
            (OUT/"normal-report.json").write_text(json.dumps({
              "source_sha":source,"mode_public":"PASS_MIXED_FIVE_ORIGINAL",
              "status":report["status"],"stop":"PASS_BOTH_OWNED"},indent=2)+"\n")
if __name__=="__main__":main()
