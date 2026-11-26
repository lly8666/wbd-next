"""Real Windows client and Winsock application. WSL transports test routing only."""
import os,sys,time,json,pathlib,subprocess,socket,threading,hashlib
from m0_h2442_tcp import sink
from m0_h2455_segments import collect,windows_readers
H2455=os.environ.get("WBD_H2455_SEGMENTS")=="windows"
from m0_wl_native_resource_sampler import sample_windows_original_process
ROOT=pathlib.Path.cwd();OUT=ROOT/"h2476-out/client";OUT.mkdir(parents=True,exist_ok=True)
PEER=os.environ["WBD_PLAN024_NATIVE_VERIFIED_GUEST_IP4"]
HOST=os.environ["WBD_PLAN024_NATIVE_VERIFIED_HOST_IP4"]
NETEM=OUT/"netem";NETEM.mkdir(exist_ok=True)
SERVER=ROOT/"h2476-out/server"
BIN=ROOT/"result/wl-public"
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

from m0_h2475_fixture import wpath,wsl,snapshot,shape as guest_shape
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def save(p,d):p.write_text(json.dumps(d,indent=2)+"\n")
def control(role,path,body=None):
    if role!="server":raise ValueError(role)
    code="import json,sys,http.client; c=http.client.HTTPConnection('127.0.0.1',18727,timeout=75); c.request('POST',sys.argv[1],sys.argv[2],{'X-H2228-Token':sys.argv[3]+'-local','Content-Type':'application/json'}); s=c.getresponse(); b=s.read(); assert s.status==200,(s.status,b[:500]);print(b.decode())"
    return json.loads(wsl("python3","-c",code,path,json.dumps(body or {}),os.environ["GITHUB_RUN_ID"],timeout=85))
def shape(loss,delay):
    assert loss==0 and delay in (0,200)
    return guest_shape(NETEM,delay)
def ps(code):
    p=subprocess.run(["pwsh","-NoProfile","-NonInteractive","-Command","$ErrorActionPreference='Stop'; "+code],capture_output=True,text=True,timeout=15)
    if p.returncode:raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()
def route_for(host):
    return json.loads(ps("Find-NetRoute -RemoteIPAddress '"+host+"' | Where-Object {$_.DestinationPrefix} | Select-Object -First 1 InterfaceIndex,InterfaceAlias,DestinationPrefix,NextHop,RouteMetric | ConvertTo-Json -Compress"))
def direct_peers():
    import ipaddress
    roles={role:read(ROOT/"h2228-peer"/(role+".json"))["tail_ip"] for role in ("relay","server")}
    for role,peer in roles.items():
        wsl("tailscale","ping","--c=5","--timeout=3s",peer,timeout=22)
    st=json.loads(wsl("tailscale","status","--json",timeout=8))
    out=[]
    for role,peer in roles.items():
        p=next(x for x in st["Peer"].values() if peer in x.get("TailscaleIPs",[]))
        endpoint=p.get("CurAddr","")
        if not endpoint:raise RuntimeError("no direct Tailscale endpoint for "+role)
        host=str(ipaddress.IPv4Address(endpoint.rsplit(":",1)[0]))
        out.append({"role":role,"endpoint":endpoint,"host":host,"route":route_for(host),"rx_bytes":p.get("RxBytes"),"tx_bytes":p.get("TxBytes")})
    return out
def pin_underlay(d,owned):
    r=route_for(PEER);save(d/"underlay-before.json",r)
    if r["InterfaceIndex"]!=int(os.environ["WBD_PLAN024_NATIVE_VERIFIED_IFINDEX"]):raise RuntimeError("WSL peer route mismatch")
    return r["InterfaceIndex"]
def check_underlay(d,expected):
    r=route_for(PEER);save(d/"underlay-after-apply.json",r)
    if r["InterfaceIndex"]!=expected:raise RuntimeError("WSL peer route changed")
def unpin_underlay(owned):
    for prefix,idx,hop in reversed(owned):
        ps(f"Remove-NetRoute -DestinationPrefix '{prefix}' -InterfaceIndex {idx} -NextHop '{hop}' -PolicyStore ActiveStore -Confirm:$false")
def add_fixture_route(prefix,idx,hop,owned):
    ps(f"New-NetRoute -DestinationPrefix '{prefix}' -InterfaceIndex {idx} -NextHop '{hop}' -RouteMetric 1 -PolicyStore ActiveStore | Out-Null")
    owned.append((prefix,idx,hop))
def isolate_background(d,physical,owned):
    # Diagnostic only: the two actual benchmark destinations still use the
    # original native Wintun. More-specific physical routes keep unrelated
    # hosted-runner traffic out of this isolated experiment.
    for host in ("192.0.2.2","10.66.0.1"):
        r=route_for(host)
        if r["InterfaceAlias"]!="WBDH2442":raise RuntimeError("benchmark destination not on Wintun before isolation")
        if r["DestinationPrefix"]!=host+"/32":
            add_fixture_route(host+"/32",int(r["InterfaceIndex"]),r["NextHop"],owned)
    for prefix in ("0.0.0.0/2","64.0.0.0/2","128.0.0.0/2","192.0.0.0/2"):
        add_fixture_route(prefix,int(physical["InterfaceIndex"]),physical["NextHop"],owned)
    check={h:route_for(h) for h in ("192.0.2.2","10.66.0.1","8.8.8.8")}
    save(d/"isolated-route-check.json",check)
    if any(check[h]["InterfaceAlias"]!="WBDH2442" for h in ("192.0.2.2","10.66.0.1")) or check["8.8.8.8"]["InterfaceIndex"]!=physical["InterfaceIndex"]:
        raise RuntimeError("fixture isolation route selection mismatch")
def sample_connected(d,workers):
    def sample_worker():
        t=time.monotonic()
        for delay in ((2,12,30,45) if os.environ.get("WBD_H2458_TARGETED")=="1" else (12,30,45) if H2452 else (12,22)):
            time.sleep(max(0,t+delay-time.monotonic()))
            try:
                if H2455:
                    row=collect(d,str(delay),windows_readers(ROOT,wsl,wpath,ps,control))
                    data=row["server"]["value"]
                else:data=control("server","/sample")
                save(d/("active-server-"+str(delay)+".json"),data)
                print("H2450_ACTIVE_SS "+json.dumps({"delay":delay,"ss":data.get("ss","")}),flush=True)
            except Exception as e:save(d/("active-server-"+str(delay)+".json"),{"error":repr(e)})
    worker=threading.Thread(target=sample_worker,daemon=True);workers.append(worker);worker.start()
def probe():
    t=time.monotonic()+55
    while time.monotonic()<t:
        try:c=socket.create_connection(("10.66.0.1",45901),timeout=2,source_address=("10.66.0.2",0));break
        except OSError:time.sleep(.2)
    else:raise RuntimeError("Windows TCP cold probe not connected")
    with c:
        c.settimeout(10);c.sendall(b"R");assert c.recv(1)==b"S";c.sendall(b"T");assert c.recv(1)==b"U"
def case(i):
    d=OUT/("case-"+str(i));d.mkdir(exist_ok=False)
    shape(0,0);control("server","/start",{"case":i})
    p=None;worker=None;event=threading.Event();f=None;owned=[];isolated=[];samples=[]
    result={"case":i,"status":"INCOMPLETE"}
    try:
        if i<0:
            delay,buf=DIRECT[i]
            if delay:shape(0,delay)
            access=HOST
            result.update(sink(PEER,5202,access,DIRECT_SECONDS,rcvbuf=buf,connected=(lambda:sample_connected(d,samples)) if H2452 else None))
            if H2452:result["added_rtt_ms"]=delay*2
            if H2453:result["direct_requested_pacing_mbps"]=DIRECT_RATES.get(i,0)
        else:
            c=CASES[i];prof=c["profile"]
            route=d/"route-key.hex";route.write_text(hashlib.sha256(("H2442-TEST-ONLY/"+os.environ["GITHUB_RUN_ID"]+"/"+os.environ["GITHUB_SHA"]).encode()).hexdigest()+"\n")
            args=[str(BIN/"wbd-client-embedded.exe"),"--native-v4-product","--control-stdin","--server-ip",PEER,"--server-port","443","--source-port",str(41031+2*i),"--server-name","wbd-h2228.example.test","--route-key-hex-file",str(route),"--tls-ca-pem",str(SERVER/"cert.pem"),"--username","bench","--password","H2442-ONLY","--tunnel-id","102030405060708090a0b0c0d0e0f001","--installation-id","445566778899aabbccddeeff00112233","--lease4","10.66.0.2/32","--adapter","WBDH2442","--state-path",str(d/"owned-wal.json"),"--mtu","1160","--lanes","1","--fec-mode","fixed" if prof>=0 else "off","--fec-parity","4" if prof>=0 else "0","--fec.mode","fixed" if prof>=0 else "off","--fec.profile",["light","mild","medium","balanced","high","strong","maximum"][max(0,prof)],"--route-mode","all","--outer-repair","on"]
            physical=route_for("192.0.2.2") if c["isolate"] else None
            expected=pin_underlay(d,owned)
            f=(d/"client.log").open("w");p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=f,stderr=subprocess.STDOUT,text=True,cwd=BIN)
            worker=threading.Thread(target=sample_windows_original_process,args=(p,d/"windows-cpu.jsonl",event),daemon=True);worker.start()
            t=time.monotonic()+30
            while "WBD_WINDOWS_CLIENT_READY" not in (d/"client.log").read_text(errors="replace"):
                if p.poll() is not None or time.monotonic()>t:raise RuntimeError("actual Windows native READY absent")
                time.sleep(.2)
            check_underlay(d,expected)
            if c['isolate']:isolate_background(d,physical,isolated)
            probe()
            print("H2448_NATIVE_COLD_PROBE_PASS case="+str(i),flush=True)
            save(d/"shape.json",shape(c["loss"],200));time.sleep(1)
            origin_route=route_for("192.0.2.2")
            save(d/"origin-route.json",origin_route)
            print("H2449_ORIGIN_ROUTE "+json.dumps(origin_route),flush=True)
            result.update(sink("192.0.2.2",5400,"10.66.0.2",SECONDS,rcvbuf=c.get("rcvbuf",0),connected=(lambda:sample_connected(d,samples)) if DIAG or H2452 else None))
            result.update(c)
        result["status"]="RECEIVED" if result["end"]=="eof" else "INCOMPLETE"
    except Exception as e:result["error"]=repr(e)
    finally:
        try:
            save(d/"local-path-before-clear.json",{"links":json.loads(wsl("ip","-s","-j","link","show")),"qdisc":json.loads(wsl("tc","-s","-j","qdisc","show")),"ss":wsl("ss","-tinm","( sport = :5400 or dport = :5400 or sport = :5202 or dport = :5202 )")})
        except Exception as e:result["local_snapshot_error"]=repr(e)
        # Clean link before owned Stop, never kill as success.
        try:
            shape(0,0)
            for name in ("wl-n0-netem-before.json","wl-n0-netem-after.json","actual-netem-readback.json"):
                src=NETEM/name
                if src.exists():
                    (d/name).write_bytes(src.read_bytes());src.unlink()
        except Exception as e:result["shape_clear_error"]=repr(e)
        for sample in samples:sample.join(3)
        # Keep physical /2s through native Stop: do not reopen background routes.
        try:unpin_underlay([r for r in isolated if r[0].endswith('/32')])
        except Exception as e:result['isolation_cleanup_error']=repr(e)
        if p:
            if p.poll() is None:
                try:p.stdin.write("stop\n");p.stdin.flush();p.wait(25)
                except Exception:p.terminate();p.wait(8)
            event.set()
            if worker:worker.join(5)
            if f:f.close()
            cl=(d/"client.log").read_text(errors="replace")
            result.update(client_stop=p.returncode==0 and "WBD_WINDOWS_NATIVE_DISCONNECTED_V1" in cl,client_ready="WBD_WINDOWS_CLIENT_READY" in cl,client_panic="panicked at" in cl)
            (d/"route-key.hex").unlink(missing_ok=True)
        try:unpin_underlay([r for r in isolated if r[0].endswith("/2")])
        except Exception as e:result["isolation_cleanup_error"]=repr(e)
        try:result["server"]=control("server","/stop")
        except Exception as e:result["server_error"]=repr(e)
        try:unpin_underlay(owned)
        except Exception as e:result["underlay_cleanup_error"]=repr(e)
        src=result.get("server",{}).get("source") or {}
        if not result.get("underlay_cleanup_error") and not result.get("isolation_cleanup_error") and result["status"]=="RECEIVED" and result.get("bytes")==src.get("bytes") and src.get("end")=="deadline" and (i<0 or (result.get("client_stop") and result.get("client_ready") and not result.get("client_panic") and result["server"].get("proxy_accept") and result["server"].get("proxy_pacing") and result["server"].get("stop") and not result["server"].get("panic"))):result["status"]="MEASURED_EXACT"
        else:result["status"]="INCOMPLETE"
        save(d/"result.json",result);print("H2442_CASE "+json.dumps(result),flush=True)
    return result
from m0_winxdp_ab_profile import cases,DIRECT,DIRECT_RATES,DIRECT_MSS,SECONDS,DIRECT_SECONDS,GUEST_PATH,clean,midpoint,drops,netem_active
CASES=cases(ROOT)
H2452=H2453=DIAG=False


def rsc_state():
    queries={
        "global":"(Get-NetOffloadGlobalSetting).ReceiveSegmentCoalescing.ToString() | ConvertTo-Json -Compress",
        "switch":"@(Get-VMSwitch | Where-Object {$_.Name -match '^WSL( |$)'} | Select-Object Name,SoftwareRscEnabled) | ConvertTo-Json -Compress",
        "adapter":"@(Get-NetAdapter -IncludeHidden | Where-Object {$_.InterfaceIndex -eq "+os.environ["WBD_PLAN024_NATIVE_VERIFIED_IFINDEX"]+" -or $_.Name -eq 'WBDH2442'} | Select-Object Name,InterfaceIndex,Status,InterfaceDescription) | ConvertTo-Json -Compress",
        "rsc":"@(Get-NetAdapterRsc -IncludeHidden | Where-Object {$_.Name -match '^vEthernet \(WSL' -or $_.Name -eq 'WBDH2442'} | Select-Object Name,IPv4Enabled,IPv4Operational,IPv4FailureReason,IPv6Enabled,IPv6Operational) | ConvertTo-Json -Compress",
        "stats":"@(Get-NetAdapterStatistics -IncludeHidden | Where-Object {$_.Name -match '^vEthernet \(WSL' -or $_.Name -eq 'WBDH2442'} | Select-Object Name,ReceivedUnicastPackets,ReceivedBytes,RscStatistics) | ConvertTo-Json -Depth 5 -Compress",
        "tcp":"@(Get-NetTCPSetting | Select-Object SettingName,DelayedAckFrequency,DelayedAckTimeoutMs,CongestionProvider) | ConvertTo-Json -Compress",
        "connection":"@(Get-NetTCPConnection -State Established | Where-Object {$_.RemotePort -in @(5202,5400) -and $_.RemoteAddress -in @('"+PEER+"','192.0.2.2')} | Select-Object LocalAddress,RemoteAddress,RemotePort,AppliedSetting) | ConvertTo-Json -Compress"
    }
    out={}
    for k,q in queries.items():
        try:out[k]=json.loads(ps(q) or "null")
        except Exception as e:out[k]={"unavailable":repr(e)}
    return out

def offload_state():
    import re
    raw=wsl("ethtool","-k","eth0")
    features={}
    for line in raw.splitlines():
        m=re.match(r"\s*([\w-]+):\s+(on|off)(?:\s+(\[fixed\]))?",line)
        if m:features[m[1]]={"value":m[2],"fixed":bool(m[3])}
    return {"features":features,"raw":raw}
def set_segmentation(original,off):
    names=("generic-segmentation-offload","tcp-segmentation-offload")
    f=original["features"]
    if not all(n in f for n in names):raise RuntimeError("missing TSO/GSO feature identity")
    target={n:("off" if off else f[n]["value"]) for n in names}
    cur=offload_state()["features"]
    for n in names:
        if cur[n]["value"]!=target[n]:
            wsl("ethtool","-K","eth0",n,target[n])
    if not off:
        cur=offload_state()["features"]
        for n,x in f.items():
            if n.startswith("tx-tcp") and n in cur and cur[n]["value"]!=x["value"] and not x["fixed"]:
                wsl("ethtool","-K","eth0",n,x["value"])
    actual=offload_state()
    if any(actual["features"][n]["value"]!=target[n] for n in names):raise RuntimeError("TSO/GSO readback mismatch")
    if not off:
        diff={n:[x["value"],actual["features"].get(n,{}).get("value")] for n,x in f.items() if actual["features"].get(n,{}).get("value")!=x["value"]}
        if diff:raise RuntimeError("offload restore mismatch "+repr(diff))
    return actual
def forward_sample(i):
    import re
    from collections import Counter
    dev="eth0" if i<0 else "wbds0"
    src=PEER if i<0 else "192.0.2.2"
    dst=HOST if i<0 else "10.66.0.2"
    port=5202 if i<0 else 5400
    filt=f"tcp and src host {src} and dst host {dst} and src port {port}"
    cmd="timeout 3 tcpdump -nn -tt -S -l -Q out -i "+dev+" -s 128 -c 6000 '"+filt+"' 2>&1; rc=$?; test $rc -eq 0 -o $rc -eq 124"
    raw=wsl("sh","-c",cmd,timeout=12)
    h=Counter();first=None;last=None
    for line in raw.splitlines():
        m=re.search(r"\blength (\d+)",line)
        if not m:continue
        ts=re.match(r"(\d+\.\d+)",line)
        if ts:
            last=float(ts.group(1))
            if first is None:first=last
        h[int(m[1])]+=1
    drops=re.search(r"(\d+) packets dropped by kernel",raw)
    return {"records":sum(h.values()),"tcp_payload_bytes":sum(k*v for k,v in h.items()),"payload_length_hist":dict(sorted(h.items())),"above_mss1049":sum(v for k,v in h.items() if k>1049),"above_1460":sum(v for k,v in h.items() if k>1460),"max_payload":max(h,default=0),"span_s":None if first is None else last-first,"kernel_drops":int(drops.group(1)) if drops else None,"scope":"Linux egress capture hook; may observe pre-segmentation skb, not wire or Windows NBL"}

def ack_sample(i):
    import re
    dev="eth0" if i<0 else "wbds0"
    src=HOST if i<0 else "10.66.0.2"
    dst=PEER if i<0 else "192.0.2.2"
    port=5202 if i<0 else 5400
    filt=f"tcp and src host {src} and dst host {dst} and dst port {port}"
    cmd="timeout 3 tcpdump -nn -tt -S -l -i "+dev+" -s 128 -c 6000 '"+filt+"' 2>&1; rc=$?; test $rc -eq 0 -o $rc -eq 124"
    raw=wsl("sh","-c",cmd,timeout=12)
    counts={"ack":0,"advance":0,"equal":0,"older":0,"sack":0,"payload_nonzero":0}
    last=None;first_ts=None;end_ts=None
    advance_bytes={}
    for line in raw.splitlines():
        a=re.search(r"\back (\d+)",line)
        if not a:continue
        ts=re.match(r"(\d+\.\d+)",line)
        if ts:
            end_ts=float(ts.group(1))
            if first_ts is None:first_ts=end_ts
        n=int(a.group(1));counts["ack"]+=1
        if last is not None:
            d=(n-last)&0xffffffff
            if d==0:counts["equal"]+=1
            elif d<0x80000000:
                counts["advance"]+=1
                advance_bytes[d]=advance_bytes.get(d,0)+1
            else:counts["older"]+=1
        last=n
        if re.search(r"\bsack \d",line):counts["sack"]+=1
        length=re.search(r"\blength (\d+)",line)
        if length and int(length.group(1)):counts["payload_nonzero"]+=1
    drops=re.search(r"(\d+) packets dropped by kernel",raw)
    return dict(counts,advance_bytes_hist=advance_bytes,span_s=None if first_ts is None else end_ts-first_ts,kernel_drops=int(drops.group(1)) if drops else None,interface=dev,scope="server-observed reverse inner TCP only; no raw capture persisted")

from m0_winxdp_fixture import start_observers,concise,functional

def main():
    rows=[]
    current_case=None
    original_offload=None
    offload_changed=False
    global sink
    original_sink=sink
    clock={}
    def observed_sink(*args,**kw):
        clock["rsc_before"]=rsc_state()
        clock["offload_before"]=offload_state()
        clock["sink_before"]=snapshot()
        start=time.monotonic()
        stop=threading.Event()
        observers=[]
        prior=kw.get("connected")
        def connected():
            clock["connect_elapsed_s"]=time.monotonic()-start
            clock["business_start_mono"]=time.monotonic()
            if prior:prior()
            observers.extend(start_observers(clock,stop,clock["business_start_mono"],current_case,snapshot,wsl))
        kw["connected"]=connected
        try:return original_sink(*args,**kw)
        finally:
            clock["business_end_mono"]=time.monotonic()
            stop.set()
            for observer in observers:observer.join(25)
            if any(observer.is_alive() for observer in observers):raise RuntimeError("measurement observer did not join")
            clock["sink_after"]=snapshot()
            clock["rsc_after"]=rsc_state()
            clock["offload_after"]=offload_state()
    sink=observed_sink
    def cpu_summary(d,row):
        p=d/"windows-cpu.jsonl"
        if not p.is_file() or "business_start_mono" not in row:return None
        t=row["business_start_mono"];samples=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]
        samples=[x for x in samples if t+10<=x["monotonic_s"]<=t+55]
        if len(samples)<2:return None
        a,b=samples[0],samples[-1];dt=b["monotonic_s"]-a["monotonic_s"]
        if dt<=0:return None
        cpu=(b["cpu_total_s"]-a["cpu_total_s"])/dt
        import re
        log=(d/"client.log").read_text(errors="replace")
        tids={role.lower():int(tid) for role,tid in re.findall(r"WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=(TX|RX) tid=(\d+)",log)}
        per={}
        for role,tid in tids.items():
            hits=[]
            for x in samples:
                tc=x.get("thread_cpu",{})
                # Named workers and exact TIDs are both retained by the raw sampler.
                for k,v in tc.items():
                    if isinstance(v,list):
                        hits.extend((x["monotonic_s"],z) for z in v if isinstance(z,dict) and z.get("tid")==tid)
            if len(hits)>=2:
                first,last=hits[0],hits[-1];span=last[0]-first[0]
                if span>0:per[role]={"coverage":len(hits),"core_equiv":(last[1]["cpu_total_s"]-first[1]["cpu_total_s"])/span,"kernel_core":(last[1]["cpu_kernel_s"]-first[1]["cpu_kernel_s"])/span}
        return {"samples":len(samples),"core_equiv":cpu,"workers":per,"estimated_cpu_s_per_gib":cpu*8*2**30/(row["rx_mbps"]*1e6) if row.get("rx_mbps",0)>0 else None}

    import shutil,re,statistics
    from m0_winxdp_ab_profile import MODES,comparable,SCHEDULE
    dll=BIN/"wbd_engine.dll"
    frozen=OUT/"frozen.dll"
    builds=ROOT/"xdp-build"
    manifest=read(builds/"manifest.json")
    original=read(ROOT/"h2442-out/windows-binary-manifest.json")
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    if digest(dll)!=original["sha256"]["dll"] or manifest["source_sha"]!="e5c3cc4ecc2d13c59e9ea1d930202bfd49e09017" or digest(BIN/"wbd-client-embedded.exe")!=manifest["exe"]:raise RuntimeError("source/DLL identity mismatch")
    for arm in ("A","B"):
        if digest(builds/(arm+".dll"))!=manifest[arm]:raise RuntimeError("candidate hash mismatch "+arm)
    shutil.copyfile(dll,frozen)
    reverse=os.environ["H2478_REPLICA"] in "BDFH"
    def mode_for(i):
        mode=MODES[i]
        return ("B" if mode=="A" else "A") if reverse else mode
    def select(i):
        mode=mode_for(i)
        selected=builds/(mode+".dll")
        shutil.copyfile(selected,dll)
        if digest(dll)!=digest(selected):raise RuntimeError("DLL copy identity")
        return mode,digest(dll)
    def diag(i,row):
        text=(OUT/("case-"+str(i))/"client.log").read_text(errors="replace")
        ready=[l for l in text.splitlines() if "WBD_XDP_TX_READY " in l]
        stop=[l for l in text.splitlines() if "WBD_XDP_TX_STOP " in l]
        row["xdp_ready"]=ready
        row["xdp_stop_raw"]=stop
        row["xdp_stop"]={k:int(v) for k,v in re.findall(r"(published|completed_before_close|pokes|invalid)=(\d+)",stop[-1])} if stop else None
        q=row["xdp_stop"] or {}
        row["mode_ok"]=(len(ready)==1 and len(stop)==1 and q.get("published",0)>0 and q.get("completed_before_close",0)>0 and q.get("invalid")==0 and "WBD_XDP_TX_RING_FULL" not in text and "WBD_XDP_TX_POKE_FAILED" not in text) if mode_for(i)=="B" else not ready and not stop
        rxready=[l for l in text.splitlines() if "WBD_XDP_RX_READY " in l]
        rxstop=[l for l in text.splitlines() if "WBD_XDP_RX_STOP " in l]
        row["xdp_rx_ready"]=rxready
        row["xdp_rx_stop_raw"]=rxstop
        row["xdp_rx_stop"]={k:int(v) for k,v in re.findall(r"(received|batches|waits|dropped|truncated)=(\d+)",rxstop[-1])} if rxstop else {}
        handoffs=text.count("WBD_XDP_COLD_HANDOFF same_rx_tx_umem=1")
        row["same_cold_handoff"]=handoffs==1
        row["cold_attempts"]=len(rxready)
        row["cold_first_try"]=len(rxready)==1 if mode_for(i)=="B" else None
        row["mode_ok"]=((len(ready)==len(stop)==len(rxready)==len(rxstop)>0 and handoffs==1 and q.get("published",0)>0 and q.get("completed_before_close",0)>0 and q.get("invalid")==0 and row["xdp_rx_stop"].get("received",0)>0 and row["xdp_rx_stop"].get("waits",0)>0 and row["xdp_rx_stop"].get("truncated")==0 and "WBD_XDP_TX_RING_FULL" not in text and "WBD_XDP_TX_POKE_FAILED" not in text) if mode_for(i)=="B" else not ready and not stop and not rxready and not rxstop)
        row["native_stop_receipts"]=[l for l in text.splitlines() if "WBD_WINDOWS_NATIVE_OUTER_REPAIR " in l or "WBD_WINDOWS_RUST_NATIVE_RX" in l]
    def paired(rows):
        out=[]
        for rate in (250,650):
            r=[x for x in rows if x.get("rate_mbps")==rate]
            if len(r)!=4 or not all(x.get("comparable") and x.get("steady_cpu") and x["steady_cpu"].get("estimated_cpu_s_per_gib") is not None for x in r):continue
            a=[x for x in r if x["mode"]=="A"];b=[x for x in r if x["mode"]=="B"]
            if len(a)!=2 or len(b)!=2:continue
            am=statistics.mean(x["rx_mbps"] for x in a);bm=statistics.mean(x["rx_mbps"] for x in b)
            ac=statistics.mean(x["steady_cpu"]["estimated_cpu_s_per_gib"] for x in a);bc=statistics.mean(x["steady_cpu"]["estimated_cpu_s_per_gib"] for x in b)
            out.append({"rate_mbps":rate,"sequence":"".join(x["mode"] for x in r),"A_mbps":am,"B_mbps":bm,"B_vs_A_goodput_pct":100*(bm/am-1) if am else None,"A_cpu_s_per_gib":ac,"B_cpu_s_per_gib":bc,"B_vs_A_cpu_pct":100*(bc/ac-1) if ac else None})
        return out
    import m0_h2470_probe as probe
    save(OUT/"cpu-probe.json",probe.run("windows"))
    save(OUT/"hardware.json",json.loads(ps("Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress")))
    save(OUT/"wsl-hardware.json",json.loads(wsl("lscpu","-J")))
    log=(OUT/"server-control.log").open("w")
    p=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--cd",wpath(ROOT),"--exec","env","GITHUB_SHA="+os.environ["GITHUB_SHA"],"GITHUB_RUN_ID="+os.environ["GITHUB_RUN_ID"],"RUNNER_TEMP=/tmp","PATH="+GUEST_PATH,"WBD_H2476_PEER="+PEER,"python3",wpath(ROOT/"tools/m0_winxdp_ab_server.py")],stdout=log,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+45
        while "H2442_SERVER_CONTROL_READY" not in (OUT/"server-control.log").read_text(errors="replace"):
            if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError("local WSL server control not ready")
            time.sleep(.2)
        # Opposite candidate order across replica parity; baseline brackets.
        original_offload=offload_state();save(OUT/"h2480-original-offload.json",original_offload)
        save(OUT/"h2480-original-rsc.json",rsc_state())
        # S is a separate functional check on any CPU, not a 9V45 sample.
        smoke=os.environ["H2478_REPLICA"]=="S"
        for i in ((1,0) if smoke else SCHEDULE):
            current_case=i
            mode,dll_sha=select(i)
            print("WINXDP_CASE_BEGIN "+json.dumps({"case":i,"mode":mode,"rate":CASES[i]["rate"]}),flush=True)
            clock.clear()
            before=json.loads(wsl("ip","-s","-j","link","show","dev","eth0"))[0]
            r=case(i)
            r.update(clock)
            ss_lines=(r.get("active_ss") or "").splitlines()
            tcp_lines=[line for line in ss_lines if "cwnd:" in line]
            r["ss_tcp_rows"]=len(tcp_lines)
            r["ss_backoff_rows"]=sum("backoff:" in line for line in tcp_lines)
            r["mode"]=mode;r["dll_sha256"]=dll_sha
            diag(i,r)
            r["steady_drops"]=drops(clock.get("steady_before",{}),clock.get("steady_after",{}))
            r["business_drops"]=drops(clock.get("sink_before",{}),clock.get("sink_after",{}))
            r["netem_active"]=netem_active(clock.get("sink_before",{}),clock.get("sink_after",{}))
            r["steady_cpu"]=cpu_summary(OUT/("case-"+str(i)),r)
            after=json.loads(wsl("ip","-s","-j","link","show","dev","eth0"))[0]
            a,b=before.get("stats64",before.get("stats")),after.get("stats64",after.get("stats"))
            r["eth0_deltas"]={side:{k:b[side][k]-a[side][k] for k in ("dropped","errors","packets")} for side in ("rx","tx")}
            r["rate_mbps"]=DIRECT_RATES[i] if i<0 else CASES[i]["rate"]
            r["added_rtt_ms"]=2*DIRECT[i][0] if i<0 else 400
            r["kind"]="bare" if i<0 else "wbd"
            r["requested_bare_mss"]=DIRECT_MSS.get(i)
            r["segmentation_arm"]="original"
            r["netem_drops"]=None
            if (OUT/("case-"+str(i))/"wl-n0-netem-after.json").is_file():
                n=read(OUT/("case-"+str(i))/"wl-n0-netem-after.json")
                r["netem_drops"]={dev:sum(q["drops"] for q in n[dev] if q.get("kind")=="netem") for dev in ("eth0","ifb")}
            r["functional"]=functional(r)
            r["comparable"]=comparable(r) and (i<0 or r.get("mode_ok") is True)
            r["clean_candidate"]=clean(r) if i>=0 else False
            rows.append(r)
            save(OUT/"summary.json",{"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],"same_windows_runner":True,"server_os":"WSL2 Linux x86_64","native_windows_server":False,"streams":1,"direction":"Linux_to_Windows_bulk_Windows_TX_ACK","scope":"FUNCTIONAL_FULL_CARRIER_SMOKE_ANY_CPU" if smoke else "9V45_ABBA_BAAB","build_source_sha":manifest["source_sha"],"rows":rows,"paired":paired(rows)})
            save(OUT/("case-"+str(i))/"measurement.json",r)
            print("WINXDP_FULL_AB_CASE "+json.dumps(concise(r)),flush=True)
            print("WINXDP_FULL_AB_PAIR "+json.dumps(paired(rows)),flush=True)
            if r.get("shape_clear_error") or (i>=0 and not r.get("client_stop")):raise RuntimeError("owned Stop or netem cleanup failed; no next case")
            if "sink_before" not in r or "sink_after" not in r:raise RuntimeError("business boundary missing; stop infrastructure failure")
            if i<0 and (r.get("connect_elapsed_s",0)<.32 or not r["netem_active"]["both_used"]):
                raise RuntimeError("400ms bare TCP handshake or bidirectional netem traffic not demonstrated")
            if i>=0 and (not r["netem_active"]["both_used"] or not r["mode_ok"]):raise RuntimeError("actual netem or TX mode identity not demonstrated")
        control("server","/finish")
        if p.wait(30)!=0:raise RuntimeError("local control exit")
        save(OUT/"h2476-windows-post-probe.json",probe.run("windows"))
        if smoke:
            if len(rows)!=2 or not all(r.get("functional") for r in rows):raise SystemExit(2)
            if any(r.get("cold_first_try") is False for r in rows):raise RuntimeError("full carrier real business delivered, but cold first-attempt qualification failed")
        elif len(paired(rows))!=2:raise SystemExit(2)
    finally:
        if offload_changed:save(OUT/"h2480-offload-restored-finally.json",set_segmentation(original_offload,False))
        try:shape(0,0)
        except Exception as e:print("H2476_NETEM_CLEANUP_ERROR",repr(e),flush=True)
        if p.poll() is None:
            try:control("server","/stop")
            except Exception:pass
            try:control("server","/finish");p.wait(30)
            except Exception:p.terminate();p.wait(10)
        log.close()
        shutil.copyfile(frozen,dll)
        save(OUT/"restore-dll.json",{"sha256":digest(dll),"expected":original["sha256"]["dll"]})
        frozen.unlink()
if __name__=="__main__":main()
