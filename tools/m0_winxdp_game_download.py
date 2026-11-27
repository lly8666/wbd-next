"""Real Game download diagnostics: four TCP sockets or one UDP receiver."""
import concurrent.futures,json,os,pathlib,re,shutil,socket,subprocess,sys,time
from m0_wl_perf_v2_config import read_scenario
SECONDS=30
STREAMS=4
PORT=5202
TARGET="198.18.77.2"
NS="h2441-origin"
ROOT=pathlib.Path.cwd()
OUT=ROOT/"result/wl-public"
E=ROOT/"result/winxdp-game-download"
MODES=("game2","game2-fec","game4","game4-fec")

def tcp_flow(sock,side,start):
    sock.settimeout(.25)
    bins=[0]*SECONDS
    drain=0;waits=0;error=None;last=None;gap=0.
    data=bytes(range(256))*256
    buf=bytearray(262144)
    try:
        while time.monotonic()<start+SECONDS+(5 if side=="windows" else 0):
            try:n=sock.recv_into(buf) if side=="windows" else sock.send(data)
            except socket.timeout:waits+=1;continue
            now=time.monotonic()
            if not n:break
            if side=="windows" and last is not None:gap=max(gap,now-last)
            last=now
            i=int(now-start)
            if 0<=i<SECONDS:bins[i]+=n
            elif i>=SECONDS:drain+=n
        if side=="linux":
            try:sock.shutdown(socket.SHUT_WR)
            except OSError:pass
    except OSError as e:error=repr(e)
    finally:sock.close()
    return {"bytes_1s":bins,"window_bytes":sum(bins),"drain_bytes":drain,
            "socket_timeouts":waits,"error":error,"max_interdelivery_s":gap}

def tcp_app(side,flag,directory):
    flag=pathlib.Path(flag);out=pathlib.Path(directory)
    sockets=[];errors=[]
    if side=="linux":
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((TARGET,PORT));listener.listen(STREAMS);listener.settimeout(.25)
            print("GAME_TCP_LISTEN",flush=True)
            limit=time.monotonic()+28
            while len(sockets)<STREAMS and time.monotonic()<limit and not flag.exists():
                try:
                    c,_=listener.accept()
                    c.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4*1024*1024)
                    c.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,b"cubic")
                    import struct
                    c.setsockopt(socket.SOL_SOCKET,47,struct.pack("=Q",int(250*125000/STREAMS)))
                    sockets.append(c)
                except socket.timeout:continue
    else:
        def connect(i):
            c=socket.socket()
            try:
                c.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,16*1024*1024)
                c.bind(("10.66.0.2",0));c.settimeout(20);c.connect((TARGET,PORT))
                return c,None
            except OSError as e:c.close();return None,repr(e)
        with concurrent.futures.ThreadPoolExecutor(max_workers=STREAMS) as pool:
            for c,err in pool.map(connect,range(STREAMS)):
                if c is not None:sockets.append(c)
                else:errors.append(err)
        print("GAME_TCP_CONNECTED "+str(len(sockets)),flush=True)
    limit=time.monotonic()+30
    while not flag.exists() and time.monotonic()<limit:time.sleep(.015)
    if not flag.exists():
        for c in sockets:c.close()
        raise RuntimeError("TCP business start barrier missing")
    start=time.monotonic()
    if sockets:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sockets)) as pool:
            flows=list(pool.map(lambda s:tcp_flow(s,side,start),sockets))
    else:time.sleep(SECONDS);flows=[]
    bins=[sum(f["bytes_1s"][i] for f in flows) for i in range(SECONDS)]
    row={"side":side,"measurement_start_monotonic_s":start,"measurement_end_monotonic_s":start+SECONDS,
         "measurement_duration_s":SECONDS,"connected_streams":len(sockets),"connect_errors":errors,
         "flows":flows,"bytes_1s":bins,"window_bytes":sum(bins),"window_mbps":sum(bins)*8/SECONDS/1e6,
         "drain_bytes":sum(f["drain_bytes"] for f in flows)}
    (out/("game-tcp-"+side+".json")).write_text(json.dumps(row,indent=2))
    print("GAME_TCP_RESULT "+json.dumps(row),flush=True)

def measure_tcp(root,out,wsl,unix,win_product,linux_product,scenario):
    # Use the same isolated forwarded origin topology as H2441. A
    # connection to 10.66.0.1 is LOCAL and never enters TCP TPROXY.
    wsl("ip","netns","add",NS)
    try:
        wsl("ip","link","add","h2441host","type","veth","peer","name","h2441peer")
        wsl("ip","link","set","h2441peer","netns",NS)
        wsl("ip","addr","add","198.18.77.1/24","dev","h2441host")
        wsl("ip","link","set","h2441host","up")
        for args in (("link","set","lo","up"),("addr","add",TARGET+"/24","dev","h2441peer"),("link","set","h2441peer","up"),("route","add","default","via","198.18.77.1")):
            wsl("ip","netns","exec",NS,"ip",*args)
        (out/"game-tcp-origin-route.json").write_text(wsl("ip","-j","route","get",TARGET))
        return _measure_tcp(root,out,unix,win_product,linux_product,scenario)
    finally:
        wsl("ip","netns","del",NS)

def _measure_tcp(root,out,unix,win_product,linux_product,scenario):
    flag=out/"game-tcp-start.flag";flag.unlink(missing_ok=True)
    script=root/"tools/m0_winxdp_game_download.py";processes=[]
    def wait_marker(p,path,marker,seconds):
        end=time.monotonic()+seconds
        while marker not in path.read_text(errors="replace"):
            if p.poll() is not None or time.monotonic()>=end:raise RuntimeError("TCP startup "+marker)
            time.sleep(.1)
    with (out/"game-tcp-linux.log").open("w") as ll,(out/"game-tcp-windows.log").open("w") as wl:
        try:
            l=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","ip","netns","exec",NS,"python3","-u",unix(script),"tcp-app","linux",unix(flag),unix(out)],stdout=ll,stderr=subprocess.STDOUT);processes.append(l)
            wait_marker(l,out/"game-tcp-linux.log","GAME_TCP_LISTEN",10)
            w=subprocess.Popen([sys.executable,"-u",str(script),"tcp-app","windows",str(flag),str(out)],stdout=wl,stderr=subprocess.STDOUT);processes.append(w)
            wait_marker(w,out/"game-tcp-windows.log","GAME_TCP_CONNECTED",25)
            flag.write_text("REAL_TCP_SOCKETS_CONNECTED\n")
            end=time.monotonic()+42
            while any(p.poll() is None for p in processes):
                if win_product.poll() is not None or linux_product.poll() is not None:raise RuntimeError("native owner exited during TCP")
                if time.monotonic()>=end:raise RuntimeError("TCP diagnostic deadline")
                time.sleep(.2)
            rows={side:json.loads((out/("game-tcp-"+side+".json")).read_text()) for side in ("windows","linux")}
            accepts=(out/"server.log").read_text(errors="replace").count("WBD_TCP_SPLICE_ACCEPT target="+TARGET+":"+str(PORT)+" cc=bbr")
            status=("MEASURED_TCP_DOWNLOAD" if rows["windows"]["connected_streams"]==rows["linux"]["connected_streams"]==STREAMS and accepts>=STREAMS
                    else "TCP_PARTIAL_OR_BBR_NOT_PROVED")
            return {"status":status,"bbr_accepts":accepts,"windows":rows["windows"],"linux":rows["linux"],"sender_scope":"SOCKET_ACCEPTED_BYTES_NOT_DELIVERED","receiver_scope":"FIRST_TCP_STREAM_BYTES_IN_30S"}
        finally:
            for p in processes:
                if p.poll() is None:p.terminate()
            for p in processes:
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill()

def kernel_sample(flag,output):
    flag=pathlib.Path(flag);end=time.monotonic()+150
    while not flag.exists() and time.monotonic()<end:time.sleep(.1)
    if not flag.exists():return
    start=time.monotonic()
    with pathlib.Path(output).open("w") as f:
        while time.monotonic()-start<SECONDS+2:
            row={"elapsed_s":time.monotonic()-start}
            for key,args in (("eth0",["tc","-s","-j","qdisc","show","dev","eth0"]),
                             ("ifb",["tc","-s","-j","qdisc","show","dev","ifbwlm0"]),
                             ("ss",["ss","-tin","( sport = :5202 or dport = :5202 or sport = :46180 )"]),
                             ("origin_ss",["ip","netns","exec",NS,"ss","-tin","sport",":5202"])):
                try:
                    p=subprocess.run(args,text=True,capture_output=True,timeout=3)
                    row[key]=json.loads(p.stdout) if key in ("eth0","ifb") and p.returncode==0 else p.stdout
                except Exception as e:row[key+"_error"]=repr(e)
            f.write(json.dumps(row)+"\n");f.flush()
            time.sleep(max(0,2-(time.monotonic()-start)%2))

def read_json(p):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError,ValueError):return {}

def summary(case,mode,transport,rc):
    report=read_json(case/"report.json");v=report.get("WL_V2",{})
    log=(case/"client.log").read_text(errors="replace") if (case/"client.log").exists() else ""
    server=(case/"server.log").read_text(errors="replace") if (case/"server.log").exists() else ""
    def receipts(marker):return [{k:int(v) for k,v in re.findall(r"(\w+)=(\d+)",l)} for l in log.splitlines() if marker in l]
    def lines(marker):return [l[-800:] for l in log.splitlines() if marker in l][-12:]
    app=read_json(case/("game-tcp-windows.json" if transport=="tcp" else "wl-n0-windows-app.json"))
    lapp=read_json(case/("game-tcp-linux.json" if transport=="tcp" else "wl-n0-linux-app.json"))
    cpu=[];f=case/"windows-original-go-rust-process-1hz.jsonl"
    if f.exists():
        for l in f.read_text(errors="replace").splitlines():
            try:
                x=json.loads(l)
                if app.get("measurement_start_monotonic_s",1e99)<=x["monotonic_s"]<=app.get("measurement_end_monotonic_s",-1):cpu.append(x)
            except (ValueError,KeyError):pass
    resource={}
    if len(cpu)>=2:
        t=cpu[-1]["monotonic_s"]-cpu[0]["monotonic_s"]
        if t>0:
            for k in ("cpu_total_s","cpu_user_s","cpu_kernel_s"):
                if k in cpu[-1] and k in cpu[0]:resource[k+"_per_s"]=(cpu[-1][k]-cpu[0][k])/t
            named=[x for x in cpu[1:] if x.get("thread_cpu",{}).get("named_rust_workers",0)==2]
            resource["named_rust_worker_samples"]=len(named)
            for k in ("rust_tx_cpu_delta_s","rust_rx_cpu_delta_s","rust_tx_kernel_delta_s","rust_rx_kernel_delta_s"):
                resource[k+"_per_s"]=sum(x["thread_cpu"][k] for x in named)/t if len(named)==len(cpu)-1 else None
            for k in ("working_set_bytes","private_bytes"):
                vals=[x[k] for x in cpu if k in x]
                if vals:resource["peak_"+k]=max(vals)
    samples=[];f=case/"kernel-samples.jsonl"
    if f.exists():
        for l in f.read_text(errors="replace").splitlines():
            try:samples.append(json.loads(l))
            except ValueError:pass
    wire={}
    if len(samples)>=2:
        for dev in ("eth0","ifb"):
            try:
                a=next(q for q in samples[0][dev] if q["kind"]=="netem")
                b=next(q for q in samples[-1][dev] if q["kind"]=="netem")
                t=samples[-1]["elapsed_s"]-samples[0]["elapsed_s"]
                wire[dev]={"interval_s":t,"post_netem_mbps":(b["bytes"]-a["bytes"])*8/t/1e6,
                           "post_netem_pps":(b["packets"]-a["packets"])/t,"drops":b["drops"]-a["drops"]}
            except (StopIteration,KeyError,TypeError,ZeroDivisionError):pass
    telemetry=[]
    for l in log.splitlines():
        if "WBD_WINDOWS_NATIVE_PACKET_TELEMETRY " in l:
            try:telemetry.append(json.loads(l.split("WBD_WINDOWS_NATIVE_PACKET_TELEMETRY ",1)[1]))
            except ValueError:pass
    row={"mode":mode,"transport":transport,"rc":rc,"status":v.get("status"),"stop":report.get("stop"),
         "error":report.get("error"),"source":report.get("product_binary_source"),
         "windows_app":{k:app.get(k) for k in ("window_mbps","connected_streams","bytes_1s","received_payload_mbps","received_first_packets","max_interdelivery_ms","business_udp_rtt","udp_socket_probe_deltas")},
         "linux_app":{k:lapp.get(k) for k in ("window_mbps","connected_streams","bytes_1s","sent_payload_mbps","sent_packets","sender_error")},
         "windows_cpu":resource,"wire":wire,"tx":receipts("WBD_XDP_TX_STOP "),"rx":receipts("WBD_XDP_RX_STOP "),
         "tx_lab":receipts("WBD_XDP_TX_LAB "),"rx_lab":receipts("WBD_XDP_RX_LAB "),
         "wintun_backpressure":receipts("WBD_XDP_GAME_DOWNLOAD_STOP "),
         "rss_default":receipts("WBD_XDP_SINGLE_RSS_READY "),"rss_ready":receipts("WBD_XDP_RX_READY "),
         "bbr":report.get("game_download_bbr"),"bbr_accepts":v.get("tcp_download",{}).get("bbr_accepts"),
         "fec_backend":lines("M0_WINDOWS_GAME_M4_FEC_BACKEND_READBACK"),"outer_stop":lines("WBD_GAME_FEC_NORMAL_OUTER_STOP"),
         "fec_applied":[l[-600:] for l in server.splitlines() if "V4_PUBLIC_GAME_FEC_APPLIED role=server" in l][-4:],
         "native_telemetry_last":telemetry[-3:],"linux_tun_link":report.get("linux_tun_link_kernel"),"linux_tun_fq":report.get("linux_tun_fq_kernel")}
    (case/"measurement.json").write_text(json.dumps(row,indent=2))
    print("WINXDP_GAME_DOWNLOAD_CASE "+json.dumps(row),flush=True)
    return row

def matrix():
    from m0_wl_windows_bounded_cmd import run_captured
    transport=os.environ["WBD_XDP_GAME_DOWNLOAD_TRANSPORT"]
    assert transport in ("tcp","udp")
    E.mkdir(parents=True,exist_ok=True);rows=[]
    for mode in MODES:
        case=E/(transport+"-"+mode);case.mkdir()
        scenario=ROOT/"scenarios"/("xdp-game-download-"+mode+".json")
        read_scenario(scenario)
        for pat in ("report.json","*-report.json","client.log","server.log","wl-n0-*","wl-v2-linux-tun-*","game-tcp-*","mode-batch.json","windows-original-go-rust-process-1hz.jsonl","gamefec-*.txt","kernel-samples.jsonl"):
            for p in OUT.glob(pat):
                if p.is_file() and not p.name.endswith("owned.json"):p.unlink()
        env=dict(os.environ,WBD_WL_PUBLIC_MODE=mode,WBD_WL_PUBLIC_MODES=mode,
                 WBD_WL_V2_SCENARIO=str(scenario.relative_to(ROOT)).replace("\\","/"),
                 WBD_XDP_GAME_DOWNLOAD_BBR="1",
                 WBD_XDP_LAB_POLICY="",WBD_XDP_LAB_TX="2048",WBD_XDP_LAB_RX="16384",WBD_XDP_LAB_QUANTUM="32")
        shutil.copyfile(scenario,case/"scenario.json")
        flag=OUT/("game-tcp-start.flag" if transport=="tcp" else "wl-n0-start.flag")
        def guest(p):return "/mnt/"+p.drive[0].lower()+p.as_posix()[2:]
        sampler=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--","python3","-u",guest(ROOT/"tools/m0_winxdp_game_download.py"),"kernel-sample",guest(flag),guest(OUT/"kernel-samples.jsonl")],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        print("WINXDP_GAME_DOWNLOAD_BEGIN "+transport+" "+mode,flush=True)
        with (case/"fixture.log").open("w") as f:
            child=subprocess.Popen([sys.executable,"-u","tools/m0_wl_public_modes_e2e.py"],env=env,stdout=f,stderr=subprocess.STDOUT)
            try:rc=child.wait(timeout=280)
            except subprocess.TimeoutExpired:
                rc=124;run_captured(["taskkill.exe","/PID",str(child.pid),"/T","/F"],20)
                if child.poll() is None:child.kill()
        if sampler.poll() is None:sampler.terminate()
        try:sampler.wait(timeout=3)
        except subprocess.TimeoutExpired:sampler.kill()
        for pat in ("report.json","client.log","server.log","wl-n0-*.json","wl-n0-*.log","wl-v2-linux-tun-*","game-tcp-*.json","game-tcp-*.log","mode-batch.json","windows-original-go-rust-process-1hz.jsonl","gamefec-*.txt","kernel-samples.jsonl"):
            for p in OUT.glob(pat):
                if p.is_file() and not p.name.endswith("owned.json"):shutil.copyfile(p,case/p.name)
        row=summary(case,mode,transport,rc);rows.append(row)
        (E/("summary-"+transport+".json")).write_text(json.dumps(rows,indent=2))
        if rc==124 or row["stop"]!="PASS_BOTH_OWNED":
            print("WINXDP_GAME_DOWNLOAD_STOP_MISSING "+mode,flush=True);break
    return 0 if len(rows)==4 and all(r["rc"]==0 and r["stop"]=="PASS_BOTH_OWNED" and
        r["rss_default"] and r["rx"] and all(x.get("queues")==1 for x in r["rx"]) and
        (r["bbr"] or {}).get("ready") and (r["bbr"] or {}).get("stop") and
        (transport!="tcp" or (r["bbr_accepts"] or 0)>=STREAMS) for r in rows) else 2

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="tcp-app":tcp_app(*sys.argv[2:])
    elif len(sys.argv)>1 and sys.argv[1]=="kernel-sample":kernel_sample(*sys.argv[2:])
    else:raise SystemExit(matrix())
