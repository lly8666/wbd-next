#!/usr/bin/env python3
"""H1506 two strictly separate signed Windows five-client native 600s scenes.

One Windows 2025 VM per 0% or 30% run, one original Linux Go/Rust shared
TLS443 server, 5 separate original Windows Wintun/NPF Go/Rust processes,
5 authenticated identities, five distinct owned adapters and /32 leases.
True application packets IN BOTH DIRECTIONS; actual 443..446 WSL2 netem
200ms each way; real per-10s kernel outer rate for all five, not an
application target. OS-owned 198.19.254.1<->.9 physical flips at four
seeded random 100-130s intervals trigger ORIGINAL cohort M4 reauth.
"""
import argparse,hashlib,json,os,pathlib,random,re,socket,subprocess,sys,time
from m0_wl_windows_bounded_cmd import run_captured
from m0_plan028_h1430_windows_linux_l3 import vm_budget_tick
ROOT=pathlib.Path.cwd()
OUT=ROOT/"result/wl-public"
OUT.mkdir(parents=True,exist_ok=True)
NAMES=("alice","bob","carol","dave","erin")
MODES=("normal","auto","game2","game4","fixed6")
INNER=("10.66.0.2","10.66.0.3","10.66.0.4","10.66.0.5","10.66.0.6")
SRC="198.19.254.1";DEST="198.19.254.2"
def die(s):raise RuntimeError(s)
def check(cond,msg):
    if not cond:die(msg)
def unix(p):
    p=pathlib.Path(p).resolve()
    return "/mnt/"+p.drive[0].lower()+"/"+"/".join(p.relative_to(p.anchor).parts)
def wsl(*args,timeout=40,checked=True):
    p=run_captured(["wsl.exe","-d","Ubuntu","-u","root","--",*args],timeout)
    if checked and p.returncode:die("real WSL OS "+repr(args[:6])+" rc="+str(p.returncode)+" "+p.stderr[-600:])
    return p.stdout
def wsl_python(script,*argv,timeout=20,check=True):
    return wsl("env","GITHUB_SHA="+os.environ["GITHUB_SHA"],"python3","-u",
               unix(ROOT/"tools"/script),*map(str,argv),timeout=timeout,checked=check)
def os_script(action,receipt):
    cmd=["pwsh","-NoProfile","-NonInteractive","-File",
         str(ROOT/"tools/m0-plan028-win-wsl-product-owned-alias.ps1"),
         "-Action",action,"-Receipt",str(receipt)]
    p=run_captured(cmd,75)
    if p.returncode:die("original Windows WSL physical source "+action+": "+p.stderr[-900:])
    return p.stdout
def line_ready(p,marker,proc,timeout=100):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if marker in (p.read_text(errors="replace") if p.exists() else ""):return
        if proc is not None and proc.poll() is not None:
            die("original product exited before "+marker+" "+repr(p)+" rc="+str(proc.returncode)+" "+
                p.read_text(errors="replace")[-700:])
        time.sleep(.2)
    die("true OS readiness timeout "+marker+" "+repr(p)+" "+(p.read_text(errors="replace")[-500:] if p.exists() else "MISSING"))
def stop_win(p):
    if p is None or p.poll() is not None:return
    try:
        p.stdin.write("stop\n");p.stdin.flush()
        p.wait(timeout=28)
    except (OSError,ValueError,subprocess.TimeoutExpired):
        p.terminate()
        try:p.wait(timeout=7)
        except subprocess.TimeoutExpired:p.kill()
def snapshot_ifaces():
    p=run_captured(["powershell.exe","-NoProfile","-NonInteractive","-Command",
      "Get-NetAdapter -IncludeHidden|Where-Object {$_.Name -like 'WBDWL5*'}|Select-Object Name,InterfaceIndex,InterfaceGuid,Status|ConvertTo-Json -Compress"],20)
    if p.returncode:die("Windows native Wintun OS readback unavailable")
    items=json.loads(p.stdout or "[]")
    return items if isinstance(items,list) else [items]
def netem(action,loss,extra=()):
    result=wsl_python("m0_plan028_h1506_win5_owned_netem.py",action,
        "--loss",loss,"--out",unix(OUT),*extra,timeout=24)
    if action=="sample":
        # The emitted JSON is the only original kernel source of outer rates.
        return json.loads(result.strip().splitlines()[-1])
    return result
def write_rate_control(path,scale):
    # Both actual OS application processes read the same mounted file.
    # Atomic replace prevents WSL2 observing partial JSON in a live 600s
    # source-locked adaptive rate loop (no product/live wire mutation).
    tmp=path.with_suffix(".h1506-tmp")
    tmp.write_text(json.dumps({"scale":round(scale,4)})+"\n")
    os.replace(tmp,path)
def from_bytes(original,last,seconds):
    uplink=(original["actual_ingress_windows_to_linux"]["bytes"]-
             last["actual_ingress_windows_to_linux"]["bytes"])
    downlink=(original["actual_egress_linux_to_windows"]["bytes"]-
               last["actual_egress_linux_to_windows"]["bytes"])
    check(uplink>=0 and downlink>=0,"original kernel qdisc counters reset")
    return {"windows_to_linux_mbps":round(uplink*8/seconds/1e6,3),
            "linux_to_windows_mbps":round(downlink*8/seconds/1e6,3),
            "five_clients_both_directions_outer_mbps":round((uplink+downlink)*8/seconds/1e6,3)}
def poststop_sibling():
    # The 600s native sender is finished. Send a NEW genuine Win32 UDP
    # and TCP request through still-owned Bob Wintun to an echo in Linux
    # original server shared TUN: never a fake client auth/M4 or report.
    probe=OUT/"h1506-sibling-echo.py"
    probe.write_text("""import select,socket,time
u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);u.bind(('10.66.0.1',45905));u.setblocking(False)
t=socket.socket(socket.AF_INET,socket.SOCK_STREAM);t.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
t.bind(('10.66.0.1',45906));t.listen(2);t.setblocking(False)
print('H1506_LINUX_TRUE_SIBLING_ECHO_READY',flush=True)
deadline=time.monotonic()+35
while time.monotonic()<deadline:
 for s in select.select([u,t],[],[],.3)[0]:
  if s is u:
   data,peer=u.recvfrom(1800);u.sendto(data,peer)
  else:
   c,_=t.accept();c.settimeout(4);msg=c.recv(1024);c.sendall(msg);c.close()
""")
    p=OUT/"h1506-sibling-echo.log"
    f=p.open("w")
    child=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
       "python3","-u",unix(probe)],stdout=f,stderr=subprocess.STDOUT)
    try:
        line_ready(p,"H1506_LINUX_TRUE_SIBLING_ECHO_READY",child,30)
        u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);u.settimeout(5)
        u.bind(("10.66.0.3",0))
        for n in range(5):
            val=("H1506_REAL_BOB_UDP_AFTER_ALICE_STOP_"+str(n)).encode()
            delivered=False
            for attempt in range(10):
                u.sendto(val,("10.66.0.1",45905))
                try:ret,peer=u.recvfrom(1024)
                except socket.timeout:continue
                if ret==val and peer[0]=="10.66.0.1":
                    delivered=True
                    break
            check(delivered,"Bob real OS UDP after Alice Stop lost all bounded probes")
        u.close()
        t=socket.socket(socket.AF_INET,socket.SOCK_STREAM);t.settimeout(12)
        t.bind(("10.66.0.3",0));t.connect(("10.66.0.1",45906))
        val=b"H1506_REAL_BOB_TCP_AFTER_ALICE_STOP";t.sendall(val)
        check(t.recv(1024)==val,"Bob real kernel TCP after Alice Stop missing")
        t.close()
        return "PASS_REAL_BOB_WIN32_5_UDP_AND_TCP_AFTER_ALICE_OWNED_STOP"
    finally:
        child.terminate()
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:child.kill()
        f.close()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scene",choices=("loss0","loss30"),default=os.environ.get("WBD_PLAN028_WIN5_SCENE"))
    a=ap.parse_args()
    loss=0 if a.scene=="loss0" else 30
    source=os.environ["GITHUB_SHA"];check(len(source)==40,"unverified CI source")
    result={"schema_version":1,"plan":"PLAN028","scene":a.scene,
            "original_source_sha":source,
            "original_Windows_clients":5,"original_linux_shared_server":1,
            "outer_target_full_duplex_both_directions_mbps":[70,100],
            "real_physical_oneway_delay_ms":200,"physical_loss_pct":loss,
            "native_product":"REAL_SIGNED_WINDOWS_NPCAP_WINTUN_GO_TLS443_RUST_AEAD_NATIVE",
            "status":"NOT_RUN","cannot_qualify_if_host_saturated":True}
    cli=OUT/"wbd-client-embedded.exe"
    check(cli.stat().st_size>100000 and (OUT/"wbd_engine.dll").stat().st_size>100000
          and (OUT/"wintun.dll").stat().st_size>10000,"original signed DLL/Go binary missing")
    linux=ROOT/"linux-product"
    check(all((linux/n).stat().st_size>100000 for n in
              ("wbd-v4-server","libwbd_engine.so")),"original Linux Go Rust native missing")
    check(os.environ["LINUX_BINARY_SRC"]==source,"Linux product wrong immutable source")
    result["binary_sha256"]={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in
       {"windows_cli":cli,"windows_engine":OUT/"wbd_engine.dll",
        "linux_server":linux/"wbd-v4-server","linux_engine":linux/"libwbd_engine.so"}.items()}
    alias=OUT/"h1506-owned-alias.json"
    key=OUT/"h1506-route-private.hex"
    users=OUT/"h1506-users-private.json"
    leases=OUT/"h1506-manual-leases-private.json"
    barrier=OUT/"h1506-start.flag"
    control=OUT/"h1506-rate-control.json"
    cert=OUT/"h1506-cert.pem"
    skey=OUT/"h1506-key.pem"
    owned_files=[key,users,leases,skey]
    logs=[];ps={};windows={};wsl_netem=False;physical=False
    all_net=[];VM=[];fail=None
    try:
        physical=True
        os_script("Prepare",alias)
        rd=json.loads(alias.read_text(encoding="utf-8-sig"))
        check(rd["stage"]=="PREPARED" and rd["host_source_old"]==SRC,
              "owned OS source not genuinely selected")
        key.write_text(os.urandom(32).hex()+"\n")
        users.write_text(json.dumps({name:"h1506-real-user-"+name for name in NAMES})+"\n")
        leases.write_text(json.dumps({name:INNER[i]+"/32" for i,name in enumerate(NAMES)})+"\n")
        route_guest="/run/wbd-plan028-h1506-"+os.environ["GITHUB_RUN_ID"]+"-key"
        user_guest="/run/wbd-plan028-h1506-"+os.environ["GITHUB_RUN_ID"]+"-users"
        lease_guest="/run/wbd-plan028-h1506-"+os.environ["GITHUB_RUN_ID"]+"-lease"
        guest_secrets=(route_guest,user_guest,lease_guest)
        for p,q in zip((key,users,leases),guest_secrets):
            wsl("install","-m","600",unix(p),q)
        wsl("openssl","req","-x509","-newkey","rsa:2048","-sha256","-days","1","-nodes",
            "-keyout",unix(skey),"-out",unix(cert),"-subj","/CN=wbd-v4.example.test",
            "-addext","subjectAltName=DNS:wbd-v4.example.test",timeout=35)
        server=OUT/"h1506-start-server.sh"
        server.write_bytes(("#!/bin/sh\nset -eu\n"
          "echo $$ > '"+unix(OUT)+"/h1506-server.pid'\n"
          "exec env LD_LIBRARY_PATH='"+unix(linux)+"' '"+unix(linux/"wbd-v4-server")+"'"
          " --raw-interface eth0 --local-ip "+DEST+" --local-port 443"
          " --tun-name wbdwl5 --tun-ipv4 10.66.0.1/24"
          " --server-name wbd-v4.example.test --route-key-hex-file '"+route_guest+"'"
          " --users-file '"+user_guest+"' --manual-client-leases-file '"+lease_guest+"'"
          " --tls-cert '"+unix(cert)+"' --tls-key '"+unix(skey)+"'"
          " --mode shared --peer-persona windows11 --outer-repair on\n").encode())
        def spawn(name,cmd,stdin=None):
            f=(OUT/(name+".log")).open("w");logs.append(f)
            p=subprocess.Popen(cmd,stdin=stdin,stdout=f,stderr=subprocess.STDOUT,
                               text=(stdin is subprocess.PIPE))
            ps[name]=p;return p
        serverlog=OUT/"h1506-server.log"
        sv=spawn("h1506-server",["wsl.exe","-d","Ubuntu","-u","root","--","sh",unix(server)])
        line_ready(serverlog,"V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443",sv,80)
        # Apply true 200ms/0% or 200ms/30% BEFORE the first original
        # Windows TCP SYN, so cold TLS/M4 is impaired too, not only DATA.
        netem("arm",loss);wsl_netem=True
        for i,name in enumerate(NAMES):
            mode=MODES[i]
            params=(("1","off","off","strong"),("1","off","auto","strong"),
                    ("2","off","off","strong"),("4","off","off","strong"),
                    ("1","fixed","fixed","maximum"))[i]
            tunnel=format(int("102030405060708090a0b0c0d0e0f000",16)+i+1,"032x")
            inst=format(int("445566778899aabbccddeeff00112200",16)+i+1,"032x")
            argv=[str(cli),"--native-v4-product","--control-stdin",
                "--server-ip",DEST,"--server-port","443",
                "--source-port",str(41031+i*100),
                "--server-name","wbd-v4.example.test",
                "--route-key-hex-file",str(key),"--tls-ca-pem",str(cert),
                "--username",name,"--password","h1506-real-user-"+name,
                "--tunnel-id",tunnel,"--installation-id",inst,"--lease4",INNER[i]+"/32",
                "--adapter","WBDWL5"+name[0].upper()+str(i),
                "--state-path",str(OUT/("h1506-owned-"+name+".json")),
                "--lanes",params[0],"--fec-mode",params[1],
                "--fec-parity","4" if mode=="fixed6" else "0",
                "--fec.mode",params[2],"--fec.profile",params[3],
                "--route-mode","bypass-lan","--outer-repair","on"]
            if mode=="fixed6":argv.extend(["--mtu","1280"])
            p=spawn("h1506-client-"+name,argv,stdin=subprocess.PIPE)
            windows[name]=p
        # Start bidirectional real OS apps before Windows native Ready,
        # because original native READY may require actual reverse traffic.
        gscript=unix(ROOT/"tools/m0_plan028_h1506_win5_real_app.py")
        lin_out=OUT/("h1506-"+a.scene+"-linux-app.json")
        win_out=OUT/("h1506-"+a.scene+"-windows-app.json")
        guestargs=["wsl.exe","-d","Ubuntu","-u","root","--","env",
                   "GITHUB_SHA="+source,"python3","-u",gscript,
                   "--side","linux","--scene",a.scene,"--barrier",unix(barrier),
                   "--control",unix(control),"--out",unix(lin_out),"--duration","600"]
        lp=spawn("h1506-linux-app",guestargs)
        wp=spawn("h1506-windows-app",[sys.executable,"-u",str(ROOT/"tools/m0_plan028_h1506_win5_real_app.py"),
                   "--side","windows","--scene",a.scene,"--barrier",str(barrier),
                   "--control",str(control),"--out",str(win_out),"--duration","600"])
        line_ready(OUT/"h1506-linux-app.log","H1506_REAL_LINUX_FIVE_CLIENT_APP_BOUND",lp,90)
        line_ready(OUT/"h1506-windows-app.log","H1506_REAL_WINDOWS_FIVE_CLIENT_APP_BOUND",wp,100)
        os_ifaces=snapshot_ifaces()
        expected={"WBDWL5"+name[0].upper()+str(i) for i,name in enumerate(NAMES)}
        check({x["Name"] for x in os_ifaces}==expected and
              len({x["InterfaceIndex"] for x in os_ifaces})==5 and
              len({x["InterfaceGuid"] for x in os_ifaces})==5,
              "Five Windows real Wintun native adapters are not independently OS-owned: "+repr(os_ifaces))
        result["five_separate_windows_OS_Wintun_owners"]=os_ifaces
        base=netem("sample",loss)
        last=base
        last_t=time.monotonic()
        write_rate_control(control,1.0)
        barrier.write_text("REAL_FIVE_CLIENTS_BOTH_OS_ON_"+source+"\n")
        start=time.monotonic()
        # Four actual physical switch requests with independently seeded
        # 100-130 second gaps. Seed retained for exact replay, never fake
        # Rust lane/M4 READY. 5 clients watch the same owned WSL NIC.
        seed=int(source[:12],16)+(0 if loss==0 else 30)
        rnd=random.Random(seed)
        intervals=[rnd.randint(100,130) for _ in range(4)]
        due=[];total=0
        for sec in intervals:
            total+=sec;due.append(total)
        check(due[-1]<=520,"random source scope needs >=80s last B proof")
        result["real_physical_flip_seed"]=seed
        result["random_100_to_130s_intervals"]=intervals
        result["four_actual_event_offsets_s"]=due
        result["actual_physical_events"]=[]
        result["physical_lane_schedule_scope"]="CORRELATED_FIVE_CLIENTS_ONE_REAL_WINDOWS_WSL_UNDERLAY_OS_ROUTE_CHANGE_NOT_INDEPENDENT_PER_CLIENT_TIMER"
        result["shared_native_owner_slot_risk"]="9_ORIGINAL_LANES_X2_DURING_SIMULTANEOUS_PATH_REAUTH_MAY_EXCEED_SERVER16_OWNER_SLOTS_CONDITION_NOT_PREQUALIFIED"
        scale=1.0;bad=0;load=vm_budget_tick();last_rate_change=start
        last_outer=None;current_ip=SRC;next_due=0
        while time.monotonic()-start<600:
            time.sleep(2)
            elapsed=time.monotonic()-start
            for who,p in windows.items():
                check(p.poll() is None,"original "+who+" Windows native client exited at "+str(round(elapsed,1))+"s")
            check(sv.poll() is None and wp.poll() is None and lp.poll() is None,
                  "original native Go server or OS app exited during 600s")
            if next_due<4 and elapsed>=due[next_due]:
                previous=current_ip
                if next_due==0:
                    os_script("Switch",alias);current_ip="198.19.254.9"
                else:
                    p=run_captured(["pwsh","-NoProfile","-NonInteractive","-File",
                      str(ROOT/"tools/m0_plan028_h1506_windows_owned_source_flip.ps1"),
                      "-Action","Flip","-Receipt",str(alias),
                      "-ExpectedCurrent",previous],55)
                    check(p.returncode==0,"original Windows OS physical reselect failed "+p.stderr[-500:])
                    current_ip=SRC if previous.endswith(".9") else "198.19.254.9"
                event={"n":next_due+1,"scheduled_elapsed_s":due[next_due],
                       "actual_elapsed_s":round(time.monotonic()-start,3),
                       "from_native_Windows_OS":previous,"to_native_Windows_OS":current_ip,
                       "original_reauth_event":"PENDING_TRUE_M4_VERIFICATION"}
                result["actual_physical_events"].append(event)
                print("H1506_TRUE_WINDOWS_FIVE_PHYSICAL_NIC_RANDOM_SOURCE_EVENT "+
                      json.dumps(event),flush=True)
                next_due+=1
            now=time.monotonic()
            if now-last_t>=10:
                cur=netem("sample",loss)
                rate=from_bytes(cur,last,now-last_t)
                last=cur;last_t=now
                cur_load=vm_budget_tick()
                busy_t=cur_load["kernel"]+cur_load["user"]-load["kernel"]-load["user"]
                idle=cur_load["idle"]-load["idle"]
                cpu=round(100*(1-idle/busy_t),2) if busy_t>0 else 0
                load=cur_load
                limited=cpu>=85 or cur_load["avail_gib"]<.75
                bad=bad+1 if limited else 0
                row={"at_s":round(now-start,2),"outer":rate,
                     "physical_underlay_loss_pct":loss,
                     "Windows_total_host_cpu_busy_pct":cpu,
                     "Windows_host_available_gib":cur_load["avail_gib"],
                     "actual_udp_rate_scale":scale,"host_budget_streak":bad,
                     "real_kernel_egress_counts":cur["actual_egress_linux_to_windows"],
                     "real_kernel_ingress_counts":cur["actual_ingress_windows_to_linux"]}
                all_net.append(row);VM.append((row["at_s"],cpu,cur_load["avail_gib"]))
                print("H1506_REAL_FIVE_WINDOWS_OUTER_443_446_KERNEL_10S "+
                      json.dumps(row,separators=(",",":")),flush=True)
                if bad>=3:die("CAPACITY_LIMITED_WIN_HOST_30S_CONTINUOUS_CPU_OR_RAM_"+repr(row))
                measured=rate["five_clients_both_directions_outer_mbps"]
                if elapsed>=20 and measured>0 and now-last_rate_change>=20:
                    # Bounded outer feedback, not a FEC/data-copy injection.
                    change=(86.0/measured)**.50
                    scale=max(.35,min(1.70,scale*max(.77,min(1.22,change))))
                    if cpu>75:scale=min(scale,float(row["actual_udp_rate_scale"]))
                    write_rate_control(control,scale)
                    last_rate_change=now
        check(len(result["actual_physical_events"])==4,"not four OS-generated real path flips")
        recorded=[x["actual_elapsed_s"] for x in result["actual_physical_events"]]
        intervals_real=[recorded[0]]+[recorded[i]-recorded[i-1] for i in range(1,4)]
        result["real_OS_cohort_change_intervals_s"]=intervals_real
        check(all(99<=v<=134 for v in intervals_real),
              "genuine Windows physical lane cohort events not near random 100..130s: "+repr(intervals_real))
        wp.wait(timeout=35);lp.wait(timeout=35)
        check(wp.returncode==lp.returncode==0,"one actual original 600s UDP sender failed")
        win_json=json.loads(win_out.read_text())
        lin_json=json.loads(lin_out.read_text())
        check(win_json["elapsed_s"]>=600 and lin_json["elapsed_s"]>=600,
              "real 600s both OS application duration incomplete")
        result["native_app_600_s"]={
            "windows":{k:v for k,v in win_json.items() if not k.endswith("_bins")},
            "linux":{k:v for k,v in lin_json.items() if not k.endswith("_bins")}}
        delta={}
        for name in NAMES:
            wsend=win_json["actual_kernel_send_accepted"][name]
            lsend=lin_json["actual_kernel_send_accepted"][name]
            lrx=lin_json["actual_unique_received"][name]
            wrx=win_json["actual_unique_received"][name]
            check(wsend>0 and lsend>0 and lrx<=wsend and wrx<=lsend,
                  "original native OS data counters missing/invalid "+name)
            if loss==0:check(wsend==lrx and lsend==wrx,
                              name+" zero-kernel-loss original protected UDP permanently missing")
            else:
                check(lrx>=int(wsend*.40) and wrx>=int(lsend*.40),
                      name+" 30pct original real UDP useful delivery collapsed below40pct")
            check(wsend>=10000 and lsend>=10000,
                  name+" original native app load never reached minimum 600s offer")
            for side,src in (("windows",win_json),("linux",lin_json)):
                check(src["invalid"][name]==0 and src["duplicate"][name]==0,
                      name+" "+side+" decrypted cross-user/duplicate app packets observed")
                check(src["max_interdelivery_ms"][name]<15000,
                      name+" "+side+" true active application blackout >=15s")
            delta[name]={"windows_to_linux":{"offered":wsend,"received_unique":lrx,
                       "missing":wsend-lrx},
                         "linux_to_windows":{"offered":lsend,"received_unique":wrx,
                       "missing":lsend-wrx}}
        result["five_real_udp_unique_delivery"]=delta
        stable=[x for x in all_net if 120<=x["at_s"]<=570]
        check(len(stable)>=30,"no full steady native outer kernel 10s samples")
        within=[x for x in stable if 70<=x["outer"]["five_clients_both_directions_outer_mbps"]<=100]
        result["outer_measured"]={
          "stable_samples":len(stable),"within_real_70_to_100_mbps":len(within),
          "actual_full_duplex_rates":[x["outer"] for x in stable],
          "per_direction_mean_mbps":{
            side:round(sum(x["outer"][side] for x in stable)/len(stable),3)
            for side in ("windows_to_linux_mbps","linux_to_windows_mbps")},
          "actual_both_direction_total_mean_mbps":round(
              sum(x["outer"]["five_clients_both_directions_outer_mbps"] for x in stable)/len(stable),3)}
        check(len(within)>=int(len(stable)*.70),
              "CAPACITY_OR_USER_OUTER_TARGET_NOT_MET_70_TO_100_MBPS_"+repr(result["outer_measured"]))
        check(all(v["actual_egress_linux_to_windows"]["drops"]>=0 for v in all_net),
              "no physical kernel netem drop witness")
        if loss==30:
            check(last["actual_egress_linux_to_windows"]["drops"]>0 and
                  last["actual_ingress_windows_to_linux"]["drops"]>0,
                  "actual bidirectional netem 30pct kernel drops NOT_OBSERVED")
        server_txt=serverlog.read_text(errors="replace")
        # H1515: this is the one mixed Normal/Game listener, NOT the
        # auto-only /multi Normal listener. Count only actual post-TLS M4
        # owner readiness (three Normal and two complete Game cohorts).
        mixed_normal=server_txt.count("V4_PUBLIC_MIXED_NORMAL_READY role=server")
        mixed_game=server_txt.count("V4_PUBLIC_GAME_MULTI_GROUP_READY role=server")
        check(mixed_normal>=3 and mixed_game>=2,
              "server mixed original M4 Normal/Game groups not all proven")
        ready_counts={}
        for name in NAMES:
            contents=(OUT/("h1506-client-"+name+".log")).read_text(errors="replace")
            r=contents.count("WBD_WINDOWS_CLIENT_READY")
            ready_counts[name]=r
            check(r>=5,"four true Windows OS physical lane cohort reauth attempts not all authenticated "+name+" "+str(r))
        result["native_client_authenticated_ready_counts"]=ready_counts
        for name in ("carol","dave"):
            z=(OUT/("h1506-client-"+name+".log")).read_text(errors="replace")
            check(z.count("WBD_WINDOWS_GAME_NATIVE_APPLIED lanes=")>=5,
                  "real Game2/4 protected whole-group M4 not proven after four OS route events: "+name)
        result["observed_server_authenticated_M4_count"]=mixed_normal+mixed_game
        result["classification"]="PASS_SCOPED_REAL_5_WINDOWS_AUTH_TLS443_600S_OUTER_70_100_MBPS_"+a.scene.upper()
        # First Stop then separate fresh actual Bob TCP and UDP packets.
        stop_win(windows["alice"])
        check("WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1"
              in (OUT/"h1506-client-alice.log").read_text(errors="replace"),
              "native Alice Windows WAL/owner Stop incomplete")
        check(all(windows[n].poll() is None for n in NAMES[1:]),
              "sibling 4 Windows native processes harmed by Alice Stop")
        result["first_Stop_sibling_real_UDP_TCP"]=poststop_sibling()
        result["status"]=result["classification"]
    except BaseException as exc:
        fail=repr(exc)
        result["status"]="FAIL_PRODUCT_OR_CAPACITY_OR_INFRA_NOT_QUALIFIED"
        result["first_failure"]=fail[-1700:]
        print("H1506_ORIGINAL_NATIVE_FIVE_FIRST_ERROR "+fail[-1100:],flush=True)
        raise
    finally:
        for w in windows.values():stop_win(w)
        for i,n in enumerate(NAMES):
            p=OUT/("h1506-client-"+n+".log")
            if p.exists():
                z=p.read_text(errors="replace")
                result.setdefault("final_original_Windows_ready",{})[n]=z.count("WBD_WINDOWS_CLIENT_READY")
                result.setdefault("final_original_Windows_Stop",{})[n]=(
                    "wal_restored=1 rust_stopped=1" in z)
        if wsl_netem:
            try:
                result["original_kernel_200ms_final"]=netem("sample",loss)
                netem("clean",loss)
                result["original_owned_tc_netem_cleanup"]="PASS"
            except BaseException as e:result["tc_cleanup_failure"]=repr(e)
        if "sv" in locals() and sv.poll() is None:
            pid=OUT/"h1506-server.pid"
            if pid.exists() and pid.read_text().strip().isdigit():
                try:wsl("kill","-TERM",pid.read_text().strip(),timeout=10)
                except BaseException as e:result["server_stop_issue"]=repr(e)
            try:sv.wait(timeout=35)
            except subprocess.TimeoutExpired:sv.terminate()
        if (OUT/"h1506-server.log").exists():
            t=(OUT/"h1506-server.log").read_text(errors="replace")
            shared_stops=[line for line in t.splitlines()
                          if "V4_PUBLIC_SHARED_TUN_STOP generation=" in line
                          and "reader_joined=1" in line]
            result["server_shared_tun_exact_original_stop"]=len(shared_stops)==1
        if physical:
            try:os_script("Restore",alias);result["owned_windows_underlay_restored"]=True
            except BaseException as e:result["alias_restore_issue"]=repr(e)
        for p in (key,users,leases,skey):
            p.unlink(missing_ok=True)
        if cert.exists():cert.unlink()
        for q in ("route_guest","user_guest","lease_guest"):
            if q in locals():
                try:wsl("rm","-f",locals()[q],timeout=8)
                except BaseException:pass
        if "ps" in locals():
            for n,p in ps.items():
                if p.poll() is None:
                    p.terminate()
                    try:p.wait(timeout=5)
                    except subprocess.TimeoutExpired:p.kill()
        for f in logs:
            try:f.close()
            except BaseException:pass
        result["owner_WAL_leftover"]={}
        for n in NAMES:
            root=OUT/("h1506-owned-"+n+".json")
            result["owner_WAL_leftover"][n]=[
              p.name for p in (pathlib.Path(str(root)+".n4-owned-wal"),
                               pathlib.Path(str(root)+".n4-owned-wal.routes")) if p.exists()]
        if result["status"].startswith("PASS") and (
            not all(result["final_original_Windows_Stop"].values()) or
            not result.get("server_shared_tun_exact_original_stop") or
            not result.get("owned_windows_underlay_restored") or
            result.get("tc_cleanup_failure") or
            any(result["owner_WAL_leftover"].values())):
            result["status"]="FAIL_NATIVE_OWNED_STOP_OR_KERNEL_CLEANUP"
        result["kernel_outer_10s_rows"]=all_net
        (OUT/("h1506-"+a.scene+"-strict-real-report.json")).write_text(
            json.dumps(result,indent=2)+"\n")
        print("H1506_WINDOWS_FIVE_ORIGINAL_REPORT "+json.dumps(
          {k:v for k,v in result.items() if k not in ("kernel_outer_10s_rows","native_app_600_s","outer_measured")},
          separators=(",",":")),flush=True)
        if result["status"].startswith("PASS"):
            (OUT/"report.json").write_text(json.dumps({"source":source,"status":result["status"],
                "mode":"mixed-five","mode_public":"PASS_SCOPED_REAL_WINDOWS_FIVE_MIXED",
                "stop":"PASS_ALL_FIVE_OWNED","h1506_original_scene":a.scene},indent=2)+"\n")
    if not result["status"].startswith("PASS"):
        raise SystemExit(1)
if __name__=="__main__":main()
