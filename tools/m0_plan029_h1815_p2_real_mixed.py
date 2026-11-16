#!/usr/bin/env python3
"""PLAN029 H1815: two genuine OS kernel paths, moderate 1MiB TCP plus
concurrent small Tunnel UDP. A test fixture, not another product packet pump.
"""
import hashlib,json,math,os,pathlib,socket,subprocess,sys,time

# Private, same-run A-B-B-A source-locked fixture. The extra argv
# explicitly propagates selection through WSL (Windows env is NOT shared).
ABBA=(os.environ.get("WBD_PLAN029_P2_ABBA_SCENE")=="1" or
      (len(sys.argv)>5 and sys.argv[5]=="p2abba"))
# H1956: four original 4MiB kernel Direct sessions, signed-only.
# WSL carries this finite workload through explicit argv, not Windows env.
PRECON_BULK=(os.environ.get("WBD_PLAN029_P2_PRECONNECT_BULK_ABBA_SCENE")=="1" or
             (len(sys.argv)>5 and sys.argv[5]=="p2preconnect4"))
PORT=46116 if ABBA else 46112
SMALL_PORT=46114
# Windows environment is NOT automatically imported by wsl.exe; the Linux
# guest gets the same load selection as a fourth explicit argv value.
BULK=(os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" or
      (len(sys.argv)>4 and sys.argv[4]=="p2bulk"))
SIZE=4*1024*1024 if BULK else 1024*1024
SEND_PAUSE=0.0 if BULK else .004
if ABBA and not BULK:raise RuntimeError("P2 A-B-B-A requires 4MiB unpaced")
ABBA_MODES=("copy","bypass","bypass","copy")
TCP128=os.environ.get("WBD_PLAN029_TCP128_SCENE")=="1"
TCP128_CONTROL=os.environ.get("WBD_PLAN029_TCP128_CONTROL_SCENE")=="1"
SUSTAIN=os.environ.get("WBD_PLAN029_P2_SUSTAIN_SCENE")=="1"
HIGH_RATE=os.environ.get("WBD_PLAN029_P2_HIGH_RATE_SCENE")=="1"
SMALL_TCP=os.environ.get("WBD_PLAN029_P2_SMALL_TCP_SCENE")=="1"
LONG_RATE=os.environ.get("WBD_PLAN029_P2_LONG_RATE_SCENE")=="1"
STEADY_QPC=os.environ.get("WBD_PLAN029_P2_STEADY_QPC_SCENE")=="1"
if STEADY_QPC and (BULK or ABBA or PRECON_BULK or SMALL_TCP or
                  SUSTAIN or HIGH_RATE or TCP128):
    raise RuntimeError("H1966 ordinary 1KiB established-TCP QPC cannot mix bulk/stress/first-SYN")
if LONG_RATE and not HIGH_RATE:
    raise RuntimeError("H1903 extended 2GiB/1.5GiB requires explicit high-rate signed source")
# H1931 one source-locked original product does both diagnostics: small
# kernel A-B-B-A first, then the 10GiB physical/Direct CPU control.
# Ordinary short rate, 128, sustained and old four-flow ABBA remain exclusive.
if HIGH_RATE and (SUSTAIN or ABBA or TCP128 or
                  (SMALL_TCP and not LONG_RATE) or not BULK):
    raise RuntimeError("H1931 rate/small combination only with signed long P2")
if SMALL_TCP and (SUSTAIN or ABBA or TCP128 or
                  (HIGH_RATE and not LONG_RATE) or not BULK):
    raise RuntimeError("H1931 small TCP only signed ordinary bulk or long P2")
if PRECON_BULK and (ABBA or not BULK or SUSTAIN or HIGH_RATE or TCP128 or
                    (os.name=="nt" and not SMALL_TCP)):
    raise RuntimeError("H1956 preconnect bulk requires exactly one original signed 4MiB plus small-TCP P2")
if SUSTAIN and (ABBA or TCP128 or not BULK):
    raise RuntimeError("H1896 sustained TCP separate from 128/ABBA and requires 4MiB CN")
if TCP128_CONTROL and not TCP128:
    raise RuntimeError("H1894 matched CPU control requires actual H1892 128 TCP")
if TCP128 and (ABBA or not BULK):
    raise RuntimeError("H1892 signed 128 Wintun sockets requires ordinary unpaced 4MiB P2")
COUNT=120  # old exact receipt minimum; sustained overlap uses a separate counter
MAX_SUSTAIN=3200
if SUSTAIN:MAX_SUSTAIN=9000
if HIGH_RATE:MAX_SUSTAIN=60000 if LONG_RATE else 14000
FINISH_PACKET=b"PLAN029-P2-TUNNEL-FINISH"
PREFIX=b"PLAN029-H1815-ORIGINAL-SIGNED-COMPARATIVE-TCP/"
PAYLOAD=(PREFIX*((SIZE+len(PREFIX)-1)//len(PREFIX)))[:SIZE]
SHA=hashlib.sha256(PAYLOAD).hexdigest()
LABEL=b"PLAN029-P2-REAL-SMALL-TUNNEL-UDP"
def udp_packet(i):
    return i.to_bytes(4,"big")+LABEL+bytes(96-4-len(LABEL))
def receipt(label,data):
    print(label+" "+json.dumps(data,sort_keys=True),flush=True)

# H1993 reads ONLY the eight pre-existing 128KiB application progress
# receipts on each ordinary paced 1MiB arm. Do not add hot packet tracing,
# timers, extra connections, network workload or product changes.
def normal_tcp_128k_progress_gaps(log,role,size):
    marker="PLAN029_H1839_P2_TCP_STAGE "
    rows=[]
    for line in pathlib.Path(log).read_text(encoding="utf-8").splitlines():
        if not line.startswith(marker):continue
        item=json.loads(line[len(marker):])
        if item.get("role")!=role:
            raise RuntimeError("H1993 unrelated real TCP application role")
        rows.append(item)
    fixed={}
    progress={"upload_progress":[],"download_progress":[]}
    for item in rows:
        phase=item.get("phase")
        if phase in progress:
            progress[phase].append(item)
        elif phase in ("connected","upload_complete","half_closed","first_reply"):
            if phase in fixed:
                raise RuntimeError("H1993 duplicate original TCP stage "+phase)
            fixed[phase]=item
        else:
            raise RuntimeError("H1993 unrecognized original TCP phase "+repr(phase))
    if set(fixed)!={"connected","upload_complete","half_closed","first_reply"}:
        raise RuntimeError("H1993 incomplete actual TCP stages")
    if size!=1024*1024 or size%(128*1024):
        raise RuntimeError("H1993 only original ordinary paced 1MiB TCP")
    count=size//(128*1024)
    if any(len(progress[k])!=count for k in progress):
        raise RuntimeError("H1993 missing/duplicate 128KiB original app milestone")
    def timestamp(row):
        t=row.get("elapsed_ms")
        if type(t) not in (int,float) or not math.isfinite(t) or t<0:
            raise RuntimeError("H1993 invalid original app monotonic timestamp")
        return float(t)
    # Upload times are relative to connected, download times to the
    # original application start. Do NOT subtract the two clock origins.
    up_end=timestamp(fixed["upload_complete"])
    reply=timestamp(fixed["first_reply"])
    half=timestamp(fixed["half_closed"])
    if reply+0.002<half or up_end<0:
        raise RuntimeError("H1993 TCP timing phase order invalid")
    def gaps(kind,start):
        prev=start
        durations=[]
        for i,row in enumerate(progress[kind],1):
            if type(row.get("bytes")) is not int or row["bytes"]!=i*128*1024:
                raise RuntimeError("H1993 TCP 128KiB milestone missing or reordered")
            now=timestamp(row)
            if now+0.002<prev:
                raise RuntimeError("H1993 backwards original application progress")
            durations.append(round(max(0,now-prev),3))
            prev=now
        return durations,prev
    upload,last_up=gaps("upload_progress",0.0)
    download,last_down=gaps("download_progress",reply)
    if last_up>up_end+0.002:
        raise RuntimeError("H1993 application upload_complete precedes progress")
    # The final original actual recv() must coincide with the last bucket,
    # but the summary elapsed is a different field in the final client receipt.
    if last_down<reply:
        raise RuntimeError("H1993 missing original 1MiB download")
    return {
        "source":"ORIGINAL_WINDOWS_APP_EXISTING_128K_RECEIPT",
        "bucket_bytes":128*1024,"bucket_count":count,
        "upload_max_gap_ms":max(upload),"download_max_gap_ms":max(download),
        "upload_worst_bucket":upload.index(max(upload))+1,
        "download_worst_bucket":download.index(max(download))+1,
        "upload_bucket_gaps_ms":upload,"download_bucket_gaps_ms":download,
        "upload_includes_4ms_pacing_per_16k":True,
        "download_includes_windows_and_linux_kernel_and_scheduling":True,
        "not_app_rtt_p99_or_rust_cpu":True
    }

def tcp_guest(physical,expected_host):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        sock.bind((physical,PORT));sock.listen(5 if (ABBA or PRECON_BULK) else 2);sock.settimeout(40)
        print("PLAN029_H1815_P2_PHYSICAL_TCP_READY",flush=True)
        sources=[];sizes=[]
        for step in range(5 if (ABBA or PRECON_BULK) else 2):
            conn,peer=sock.accept()
            if peer[0]!=expected_host:
                raise RuntimeError("physical WinSock source changed under Direct")
            with conn:
                conn.settimeout(35)
                data=bytearray()
                while len(data)<SIZE:
                    chunk=conn.recv(min(16384,SIZE-len(data)))
                    if not chunk:break
                    data.extend(chunk)
                if len(data)!=SIZE or hashlib.sha256(data).hexdigest()!=SHA:
                    raise RuntimeError("P2 real Linux physical TCP 1MiB bytes mismatch")
                if conn.recv(1)!=b"":
                    raise RuntimeError("P2 kernel TCP missing half-close")
                receipt("PLAN029_H1839_GUEST_TCP_STAGE",{
                    "leg":step,"phase":"received_1m_and_eof",
                    "bytes":len(data),"sha256":SHA,
                    "source_physical":peer[0]})
                conn.sendall(data);conn.shutdown(socket.SHUT_WR)
                receipt("PLAN029_H1839_GUEST_TCP_STAGE",{
                    "leg":step,"phase":"echo_sendall_and_shutdown_complete",
                    "bytes":len(data)})
            sources.append(peer[0]);sizes.append(len(data))
        receipt("PLAN029_H1815_P2_PHYSICAL_TCP_GUEST",
          {"source_ips":sources,"received_bytes":sizes,"socket":physical,
           "kernel_socket":True})

def tcp_client(role,local,remote):
    if role=="direct" and (local!="10.66.0.2" or not remote.startswith("198.18.")):
        raise RuntimeError("P2 direct must use original Wintun /32 and announced local FakeIP")
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(35);sock.bind((local,0))
        started=time.perf_counter();sock.connect((remote,PORT))
        connected=time.perf_counter()
        # Both genuine application WinSock sockets must retain the same
        # default TCP_NODELAY state; do not change transport pacing or
        # socket tuning when comparing physical vs synthetic Direct.
        app_nodelay=sock.getsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY)
        receipt("PLAN029_H1839_P2_TCP_STAGE",{
            "role":role,"phase":"connected",
            "app_tcp_nodelay":int(app_nodelay),
            "elapsed_ms":round((connected-started)*1000,3)})
        for n in range(0,SIZE,16384):
            sock.sendall(PAYLOAD[n:n+16384])
            # Only eight bounded, independent progress checkpoints / MiB,
            # not tracing kernel packets or changing application pacing.
            if (n+16384)%(128*1024)==0:
                receipt("PLAN029_H1839_P2_TCP_STAGE",{
                    "role":role,"phase":"upload_progress",
                    "bytes":n+16384,"elapsed_ms":round((time.perf_counter()-connected)*1000,3)})
            if SEND_PAUSE:time.sleep(SEND_PAUSE) # Exact same condition on physical and Direct
        uploaded=time.perf_counter()
        receipt("PLAN029_H1839_P2_TCP_STAGE",{
            "role":role,"phase":"upload_complete","bytes":SIZE,
            "elapsed_ms":round((uploaded-connected)*1000,3)})
        sock.shutdown(socket.SHUT_WR)
        half_closed=time.perf_counter()
        receipt("PLAN029_H1839_P2_TCP_STAGE",{
            "role":role,"phase":"half_closed",
            "elapsed_ms":round((half_closed-started)*1000,3)})
        echoed=bytearray();first_reply=None;last_bucket=0
        while len(echoed)<SIZE:
            part=sock.recv(min(16384,SIZE-len(echoed)))
            if not part:
                receipt("PLAN029_H1839_P2_TCP_STAGE",{
                    "role":role,"phase":"premature_eof",
                    "bytes":len(echoed),"elapsed_ms":round((time.perf_counter()-started)*1000,3)})
                break
            if first_reply is None:
                first_reply=time.perf_counter()
                receipt("PLAN029_H1839_P2_TCP_STAGE",{
                    "role":role,"phase":"first_reply",
                    "elapsed_ms":round((first_reply-started)*1000,3)})
            echoed.extend(part)
            bucket=len(echoed)//(128*1024)
            if bucket>last_bucket:
                last_bucket=bucket
                receipt("PLAN029_H1839_P2_TCP_STAGE",{
                    "role":role,"phase":"download_progress",
                    "bytes":len(echoed),"elapsed_ms":round((time.perf_counter()-started)*1000,3)})
        ended=time.perf_counter()
        if len(echoed)!=SIZE or hashlib.sha256(echoed).hexdigest()!=SHA:
            raise RuntimeError("P2 Windows actual one-MiB kernel TCP echo wrong")
        data={"role":role,"echo_bytes":len(echoed),"payload_sha256":SHA,
              "app_tcp_nodelay":int(app_nodelay),
              "socket_source":sock.getsockname()[0],
              "socket_source_port":sock.getsockname()[1],
              "presented_peer":remote,
              "start_monotonic_s":started,"end_monotonic_s":ended,
              "elapsed_ms":round((ended-started)*1000,3),"kernel_tcp":True,
              "half_close":True,
              "connect_ms":round((connected-started)*1000,3),
              "upload_ms":round((uploaded-connected)*1000,3),
              "half_close_ms":round((half_closed-uploaded)*1000,3),
              "first_reply_wait_ms":round(((first_reply or ended)-half_closed)*1000,3),
              "download_ms":round((ended-(first_reply or ended))*1000,3),
              "nominal_send_sleep_ms":round(SIZE/16384*SEND_PAUSE*1000,3),
              "throughput_scope":"UNPACED_4M_BULK" if BULK else "PACED_FUNCTIONAL_NOT_PEAK_GOODPUT"}
    receipt("PLAN029_H1815_P2_TCP_CLIENT",data)

def udp_guest(tun_ip,lease):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind((tun_ip,SMALL_PORT));sock.settimeout(47)
        print("PLAN029_H1815_P2_LINUX_TUN_SMALL_READY",flush=True)
        total=0
        while total<MAX_SUSTAIN:
            packet,peer=sock.recvfrom(512)
            if peer[0]!=lease:
                raise RuntimeError("P2 Linux TUN small UDP source mismatch")
            if packet==FINISH_PACKET:
                sock.sendto(FINISH_PACKET,peer)
                break
            if packet!=udp_packet(total):
                raise RuntimeError("P2 Linux TUN small UDP content mismatch")
            sock.sendto(packet,peer);total+=1
        else:raise RuntimeError("P2 Linux sustained packet cap reached")
        if total<COUNT:raise RuntimeError("P2 Linux 120 minimum not covered")
    receipt("PLAN029_H1815_P2_TUNNEL_SMALL_LINUX",
      {"received":COUNT,"sustained_total":total,"source_lease":lease,
       "tunnel_local":tun_ip,"kernel_tun_socket":True})

def udp_windows(lease,tun_ip):
    if lease!="10.66.0.2":raise RuntimeError("wrong original signed Wintun lease")
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        sock.bind((lease,0));sock.settimeout(1.5)
        print("PLAN029_H1815_P2_WINDOWS_TUN_SMALL_READY",flush=True)
        started=time.perf_counter();rtts=[];gaps=[];prev=None;total=0
        tagged=[] if TCP128_CONTROL or SUSTAIN or HIGH_RATE else None
        # Test-only host completion marker: UDP must span the entire real
        # Direct TCP lifetime, not end after the old first ~2 seconds.
        done=pathlib.Path(os.environ["WBD_PLAN029_P2_TCP_DONE_MARKER"])
        for seq in range(MAX_SUSTAIN):
            begin_monotonic=time.perf_counter() if TCP128_CONTROL or HIGH_RATE else None
            if SUSTAIN and begin_monotonic is None:
                begin_monotonic=time.perf_counter()
            begin=time.perf_counter()
            sock.sendto(udp_packet(seq),(tun_ip,SMALL_PORT))
            payload,fromaddr=sock.recvfrom(512)
            end=time.perf_counter()
            if fromaddr!=(tun_ip,SMALL_PORT) or payload!=udp_packet(seq):
                raise RuntimeError("P2 small UDP echo escaped Tunnel or wrong sequence")
            rtt=(end-begin)*1000
            rtts.append(rtt)
            if tagged is not None:
                tagged.append((begin_monotonic,time.perf_counter(),rtt))
            if prev is not None:gaps.append((end-prev)*1000)
            prev=end;total+=1
            if total%128==0 and not (SUSTAIN or HIGH_RATE):
                receipt("PLAN029_H1839_P2_UDP_STAGE",{
                    "phase":"progress","delivered":total,
                    "elapsed_ms":round((end-started)*1000,3)})
            if total>=COUNT and done.exists():break
            time.sleep(.014)
        else:raise RuntimeError("P2 UDP sustained cap before TCP completion")
        sock.sendto(FINISH_PACKET,(tun_ip,SMALL_PORT))
        payload,fromaddr=sock.recvfrom(512)
        if fromaddr!=(tun_ip,SMALL_PORT) or payload!=FINISH_PACKET:
            raise RuntimeError("P2 Tunnel final controlled echo missing")
        finished=time.perf_counter()
    phase_udp=None
    if TCP128_CONTROL:
        path=pathlib.Path(os.environ["WBD_PLAN029_TCP128_WINDOWS_PHASE_PATH"])
        phase=json.loads(path.read_text(encoding="utf-8"))
        if phase.get("source_sha")!=os.environ["GITHUB_SHA"] or set(
                phase.get("windows",{}))!={"pre128","tcp128"}:
            raise RuntimeError("H1894 original signed TCP128 phase times missing")
        phase_udp={}
        previous_end=None
        for key in ("pre128","tcp128"):
            bounds=phase["windows"][key]
            start,stop=bounds["start_monotonic_s"],bounds["end_monotonic_s"]
            if not (7.5<=stop-start<=9.5 and
                    (previous_end is None or previous_end<=start)):
                raise RuntimeError("H1894 CPU/UDP idle windows overlap or are too short")
            sample=[(b,e,r) for b,e,r in tagged if start<=b and e<=stop]
            if len(sample)<25:
                raise RuntimeError("H1894 original 96B Tunnel UDP packet samples missing")
            sample.sort()
            phase_udp[key]={
                "unique_delivered":len(sample),
                "rtt_p99_ms":round(sorted(r for _,_,r in sample)[
                    math.ceil(.99*len(sample))-1],3),
                "max_interreply_gap_ms":round(max(sample[i][1]-sample[i-1][1]
                    for i in range(1,len(sample)))*1000,3),
                "scope":"ACTUAL_WINDOWS_KERNEL_TUNNEL_UDP_WITHIN_ORIGINAL_IDLE_WINDOW"
            }
            previous_end=stop
    sustained_udp=None
    if SUSTAIN:
        path=pathlib.Path(os.environ["WBD_PLAN029_P2_SUSTAIN_PHASE_FILE"])
        phase=json.loads(path.read_text(encoding="utf-8"))
        if (phase.get("source_sha")!=os.environ["GITHUB_SHA"] or
            set(phase.get("windows",{}))!={"upload","download"}):
            raise RuntimeError("H1896 actual signed Windows sustained phase file missing")
        sustained_udp={}
        last_end=None
        for name in ("upload","download"):
            stage=phase["windows"][name]
            start,stop=stage["start_monotonic_s"],stage["end_monotonic_s"]
            if (not 29.5<=stop-start<=55 or
                (last_end is not None and start<last_end)):
                raise RuntimeError("H1896 true sustained phase durations invalid")
            sample=[(b,e,r) for b,e,r in tagged if start<=b and e<=stop]
            if len(sample)<250:
                raise RuntimeError("H1896 real 96B Tunnel UDP per-phase sample absent")
            sample.sort()
            sustained_udp[name]={
                "unique_delivered":len(sample),
                "rtt_p99_ms":round(sorted(r for _,_,r in sample)[
                    math.ceil(.99*len(sample))-1],3),
                "max_interreply_gap_ms":round(max(
                    (sample[i][1]-sample[i-1][1])*1000
                    for i in range(1,len(sample))),3),
                "scope":"REAL_96B_TUNNEL_UDP_WITHIN_30S_ORIGINAL_WINDOWS_TCP_PHASE"
            }
            last_end=stop
    rate_udp=None
    if HIGH_RATE:
        path=pathlib.Path(os.environ["WBD_PLAN029_P2_HIGH_RATE_PHASE_FILE"])
        phase=json.loads(path.read_text(encoding="utf-8"))
        names=(("pre","physical_oneway_500mbps",
                "physical_duplex_700mbps_aggregate",
                "oneway_500mbps","duplex_700mbps_aggregate","post")
               if LONG_RATE else
               ("pre","oneway_500mbps","duplex_700mbps_aggregate","post"))
        if phase.get("source_sha")!=os.environ["GITHUB_SHA"] or set(
                phase.get("windows",{}))!=set(names):
            raise RuntimeError("H1898 signed 500/700Mbps QPC stage windows absent")
        rate_udp={};last_end=None
        for name in names:
            bounds=phase["windows"][name]
            start,stop=bounds["start_monotonic_s"],bounds["end_monotonic_s"]
            if (not 2<=stop-start<=(180 if LONG_RATE else 100) or
                (last_end is not None and start<last_end)):
                raise RuntimeError("H1898 overlapped/invalid TCP/UDP stage")
            samples=[(b,e,r) for b,e,r in tagged if start<=b and e<=stop]
            if len(samples)<25:
                raise RuntimeError("H1898 true Tunnel UDP absent during "+name)
            samples.sort()
            rate_udp[name]={
                "unique_delivered":len(samples),
                "rtt_p99_ms":round(sorted(r for _,_,r in samples)[
                    math.ceil(.99*len(samples))-1],3),
                "max_interreply_gap_ms":round(max(
                    (samples[i][1]-samples[i-1][1])*1000
                    for i in range(1,len(samples))),3),
                "scope":"REAL_96B_WINDOWS_KERNEL_TUNNEL_UDP_DURING_HIGH_RATE_STAGE"}
            last_end=stop
    receipt("PLAN029_H1815_P2_TUNNEL_SMALL_WINDOWS",
      {"received":COUNT,"sustained_total":total,
       "matched_phase_udp":phase_udp,
       "sustained_phase_udp":sustained_udp,
       "highrate_phase_udp":rate_udp,
       "start_monotonic_s":started,"end_monotonic_s":finished,
       "kernel_lease":lease,"tunnel_ip":tun_ip,
       "rtt_p99_ms":round(sorted(rtts)[math.ceil(.99*total)-1],3),
       "max_interreply_gap_ms":round(max(gaps),3),"kernel_udp":True})

def run_p2(root,out,physical,host_source,tunnel_ip,fake,unix,ready):
    if os.environ.get("WBD_PLAN029_P2_MIXED_SCENE")!="1":
        raise RuntimeError("H1815 true original test scene gate missing")
    source=os.environ["GITHUB_SHA"]
    exe=root/"tools"/"m0_plan029_h1815_p2_real_mixed.py"
    children=[];streams=[]
    completed=out/"plan029-h1828-direct-fully-finished.marker"
    if completed.exists():completed.unlink()
    def spawn(name,role,first,second,linux=False):
        log=out/("plan029-h1815-"+name+".log")
        f=log.open("w");streams.append(f)
        args=(["wsl.exe","-d","Ubuntu","-u","root","--","python3","-u",unix(exe)]
              if linux else [sys.executable,"-u",str(exe)])
        if linux and SUSTAIN:
            # WSL.exe does not inherit Windows process environment. Pass
            # the exact longer UDP run bound explicitly to Linux guest;
            # preserve the six-argv P2/ABBA workload contract unchanged.
            args[6:6]=["env","WBD_PLAN029_P2_SUSTAIN_SCENE=1"]
        if linux and HIGH_RATE:
            extras=["env","WBD_PLAN029_P2_HIGH_RATE_SCENE=1"]
            if LONG_RATE:extras.append("WBD_PLAN029_P2_LONG_RATE_SCENE=1")
            args[6:6]=extras
        child_env=os.environ.copy()
        child_env["WBD_PLAN029_P2_TCP_DONE_MARKER"]=str(completed)
        if TCP128_CONTROL:
            child_env["WBD_PLAN029_TCP128_WINDOWS_PHASE_PATH"]=str(
                out/"plan029-h1894-tcp128-udp-windows-phases.json")
        if SUSTAIN:
            child_env["WBD_PLAN029_P2_SUSTAIN_PHASE_FILE"]=str(
                out/"plan029-h1896-sustain-windows-phases.json")
        if HIGH_RATE:
            child_env["WBD_PLAN029_P2_HIGH_RATE_PHASE_FILE"]=str(
                out/"plan029-h1898-rate-phases.json")
        # Preserve the old original P2/ABBA argv contract as the
        # default actual runtime expression; this extra signed variant
        # changes ONLY the sixth argv of four-bulk preconnect CI.
        mode_argv=["p2abba" if ABBA else "p2ordinary"]
        if PRECON_BULK:mode_argv=["p2preconnect4"]
        p=subprocess.Popen([*args,role,first,second,
                            "p2bulk" if BULK else "p2paced",
                            *mode_argv],stdout=f,
                           stderr=subprocess.STDOUT,env=child_env)
        children.append(p)
        return p,log
    def wait(p,log,limit):
        try:code=p.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            # Preserve the last successful application phase AND genuine
            # whole-span Tunnel UDP sequence even if TCP never completes.
            # No application pacing change, second traffic source or
            # after-the-fact invented p99. This is only failed-scene evidence.
            tail=log.read_text(errors="replace")[-1600:]
            udp_log=out/"plan029-h1815-windows-tunnel-small.log"
            udp_tail=udp_log.read_text(errors="replace")[-700:] if udp_log.exists() else "NOT_RUN"
            raise RuntimeError("P2 bounded original kernel app timeout "+str(log)+
                               " LAST_APP_PHASES="+repr(tail)+
                               " CONCURRENT_TUNNEL_UDP_STAGES="+repr(udp_tail))
        if code!=0:raise RuntimeError("P2 kernel app failed "+str(log)+" "+
                 log.read_text(errors="replace")[-600:])
    def proof(log,marker):
        lines=[line.split(" ",1)[1] for line in log.read_text().splitlines()
               if line.startswith(marker+" ")]
        if len(lines)!=1:raise RuntimeError("P2 exact receipt count missing "+str(log))
        return json.loads(lines[0])
    try:
        guest,gn=spawn("linux-physical-tcp","guest_tcp",physical,host_source,True)
        ready(gn,"PLAN029_H1815_P2_PHYSICAL_TCP_READY",guest,12)
        baseline,bn=spawn("baseline-windows","baseline",host_source,physical)
        wait(baseline,bn,35)
        lin,ln=spawn("linux-tunnel-small","guest_udp",tunnel_ip,"10.66.0.2",True)
        ready(ln,"PLAN029_H1815_P2_LINUX_TUN_SMALL_READY",lin,12)
        win,wn=spawn("windows-tunnel-small","windows_udp","10.66.0.2",tunnel_ip)
        ready(wn,"PLAN029_H1815_P2_WINDOWS_TUN_SMALL_READY",win,8)
        direct_proofs=[]
        if ABBA or PRECON_BULK:
            for ordinal in range(4):
                direct,dn=spawn("direct-abba-"+str(ordinal+1),
                    "direct","10.66.0.2",fake)
                wait(direct,dn,38)
                direct_proofs.append(proof(dn,"PLAN029_H1815_P2_TCP_CLIENT"))
        else:
            direct,dn=spawn("direct-windows","direct","10.66.0.2",fake)
            wait(direct,dn,38)
            direct_proofs.append(proof(dn,"PLAN029_H1815_P2_TCP_CLIENT"))
        sustained=None
        if SUSTAIN:
            # The original two-entry P2 kernel server must finish before a
            # different physical TCP46118 listener is started. No new owner.
            wait(guest,gn,7)
            from m0_plan029_h1896_sustain_tcp import run_sustained
            original_pid=int(os.environ["WBD_PLAN029_P2_ORIGINAL_PID"])
            sustained=run_sustained(
                root,out,physical,host_source,fake,unix,ready,original_pid)
        latency=None
        if SMALL_TCP:
            # The H1815 TCP46112 Linux listener has exited; reuse exactly
            # that already-owned WSL2 grant with the same signed Windows
            # original Go/Rust, Wintun/FakeIP, and live Tunnel96B UDP.
            wait(guest,gn,7)
            from m0_plan029_h1926_small_tcp_latency import run_small_tcp_latency
            latency=run_small_tcp_latency(
                root,out,physical,host_source,fake,unix,ready)
        highrate=None
        if HIGH_RATE:
            # Reuse only the original signed WSL2 physical TCP46118
            # Hyper-V grant; SAME original product/UDP/Wintun owner.
            wait(guest,gn,7)
            from m0_plan029_h1898_highrate_tcp import run_highrate
            pid=int(os.environ["WBD_PLAN029_P2_ORIGINAL_PID"])
            highrate=run_highrate(root,out,physical,host_source,fake,unix,ready,pid)
        tcp128=None
        if TCP128:
            # Reuse original already-owned Hyper-V physical TCP46112
            # grant AFTER the ordinary Linux P2 listener exits.
            # Keep original Tunnel UDP alive across all 128 connections.
            wait(guest,gn,7)
            control=None
            if TCP128_CONTROL:
                # One genuine source-locked original Windows Go+Rust owner,
                # same ongoing 96B Tunnel UDP, with NO newly opened H1892
                # Wintun TCP sockets yet. Earlier P2 FIN grace may remain.
                begin=time.perf_counter()
                time.sleep(8)
                end=time.perf_counter()
                control={"start_monotonic_s":begin,
                         "end_monotonic_s":end,
                         "scope":"PRE128_NO_NEW_TCP_PROBE_SOCKETS_POST_P2"}
            from m0_plan029_h1892_real_tcp128 import run_tcp128
            tcp128=run_tcp128(root,out,physical,host_source,fake,unix,ready)
            if TCP128_CONTROL:
                tcp128["pre128_control"]=control
                windows=tcp128["windows"]
                owner={
                    "source_sha":source,
                    "windows":{
                        "pre128":control,
                        "tcp128":{
                            "start_monotonic_s":windows["idle_start_monotonic_s"],
                            "end_monotonic_s":windows["idle_end_monotonic_s"]
                        }
                    }
                }
                (out/"plan029-h1894-tcp128-udp-windows-phases.json").write_text(
                    json.dumps(owner,sort_keys=True),encoding="utf-8")
        completed.write_text("direct-finished\n",encoding="ascii")
        wait(win,wn,23);wait(lin,ln,7)
        if not TCP128:wait(guest,gn,7)
        steady=None
        if STEADY_QPC:
            # Do not reuse first-SYN, FIN-first or paced 1MiB phase times
            # as settled data latency. The SAME original Windows Rust Wintun
            # owner remains alive for a separate 2,048-message TCP stream.
            from m0_plan029_h1966_steady_tcp_qpc import run_steady
            steady=run_steady(root,out,physical,host_source,fake,unix,ready)
        base=proof(bn,"PLAN029_H1815_P2_TCP_CLIENT")
        # Preserve the historic P2 field, now one of the two B trials.
        # The full four-trial chain gets its OWN exact, signed receipt.
        direct_value=direct_proofs[1] if ABBA else direct_proofs[0]
        linux=proof(gn,"PLAN029_H1815_P2_PHYSICAL_TCP_GUEST")
        small_win=proof(wn,"PLAN029_H1815_P2_TUNNEL_SMALL_WINDOWS")
        small_linux=proof(ln,"PLAN029_H1815_P2_TUNNEL_SMALL_LINUX")
        # Original P2 has only one paced 1MiB physical arm and one
        # FakeIP Direct arm. Check their existing app-side progress
        # checkpoints, not an invented 2048-message microbenchmark.
        normal_gaps=None
        if not BULK:
            normal_gaps={
                "physical":normal_tcp_128k_progress_gaps(bn,"baseline",SIZE),
                "direct":normal_tcp_128k_progress_gaps(dn,"direct",SIZE),
                "scope":"SAME_VM_SEQUENTIAL_PACED_TCP_WITH_CONCURRENT_TUNNEL_UDP",
                "comparison":"DESCRIPTIVE_ONLY_NOT_CAUSAL_OR_P99",
            }
        if TCP128_CONTROL:
            if (tcp128 is None or not isinstance(
                    small_win.get("matched_phase_udp"),dict) or
                set(small_win["matched_phase_udp"])!={"pre128","tcp128"}):
                raise RuntimeError("H1894 two real same-VM Tunnel UDP phase receipts missing")
            tcp128["matched_phase_udp"]=small_win["matched_phase_udp"]
        if SUSTAIN:
            if (sustained is None or
                not isinstance(small_win.get("sustained_phase_udp"),dict) or
                set(small_win["sustained_phase_udp"])!={"upload","download"}):
                raise RuntimeError("H1896 original simultaneous UDP/TCP stage evidence absent")
            for name in ("upload","download"):
                segment=small_win["sustained_phase_udp"][name]
                if (segment["unique_delivered"]<250 or
                    segment["scope"]!=
                    "REAL_96B_TUNNEL_UDP_WITHIN_30S_ORIGINAL_WINDOWS_TCP_PHASE"):
                    raise RuntimeError("H1896 sustained phase lacked Tunnel UDP progress")
            sustained["tunnel_udp_per_phase"]=small_win["sustained_phase_udp"]
        if HIGH_RATE:
            samples=small_win.get("highrate_phase_udp")
            names={"pre","oneway_500mbps","duplex_700mbps_aggregate","post"}
            if LONG_RATE:
                names|={"physical_oneway_500mbps",
                        "physical_duplex_700mbps_aggregate"}
            if highrate is None or not isinstance(samples,dict) or set(samples)!=names:
                raise RuntimeError("H1898 original 96B Tunnel UDP QPC windows missing")
            highrate["tunnel_udp_per_stage"]=samples
            if LONG_RATE and any(samples[k]["unique_delivered"]<750
                for k in names-{"pre","post"}):
                raise RuntimeError("H1903 true 30+ second physical and Direct stages lack continuous Tunnel UDP")
            pre=highrate["phase_windows"]["windows"]["pre"]
            post=highrate["phase_windows"]["windows"]["post"]
            highrate["tunnel_udp_covers_rate"]=(
                small_win["start_monotonic_s"]<=pre["start_monotonic_s"] and
                small_win["end_monotonic_s"]>=post["end_monotonic_s"])
            if not highrate["tunnel_udp_covers_rate"]:
                raise RuntimeError("H1898 Tunnel UDP did not cover pre/load/post")
        first_direct=min(t["start_monotonic_s"] for t in direct_proofs)
        last_direct=max(t["end_monotonic_s"] for t in direct_proofs)
        overlap=(max(first_direct,small_win["start_monotonic_s"])<
                 min(last_direct,small_win["end_monotonic_s"]))
        whole_direct=(small_win["start_monotonic_s"]<=first_direct and
                      small_win["end_monotonic_s"]>=last_direct)
        whole_tcp128=(not TCP128 or (
            tcp128 is not None and
            small_win["start_monotonic_s"]<=
                tcp128["windows"]["start_monotonic_s"] and
            small_win["end_monotonic_s"]>=
                tcp128["windows"]["end_monotonic_s"]))
        if TCP128_CONTROL:
            ctl=tcp128["pre128_control"]
            if not (small_win["start_monotonic_s"]<=ctl["start_monotonic_s"]<
                    ctl["end_monotonic_s"]<=
                    tcp128["windows"]["idle_start_monotonic_s"] and
                    small_win["end_monotonic_s"]>=
                    tcp128["windows"]["idle_end_monotonic_s"]):
                raise RuntimeError("H1894 original UDP did not span both idle windows")
        if (base["role"]!="baseline" or direct_value["role"]!="direct" or
            base["app_tcp_nodelay"]!=direct_value["app_tcp_nodelay"] or
            base["echo_bytes"]!=SIZE or direct_value["echo_bytes"]!=SIZE or
            base["payload_sha256"]!=direct_value["payload_sha256"] or
            base["socket_source"]!=host_source or
            direct_value["presented_peer"]!=fake or
            linux["source_ips"]!=[host_source]*(5 if ABBA or PRECON_BULK else 2) or
            linux["received_bytes"]!=[SIZE]*(5 if ABBA or PRECON_BULK else 2) or
            small_win["received"]!=COUNT or small_linux["received"]!=COUNT or
            small_linux["source_lease"]!="10.66.0.2" or not overlap or
            not whole_direct or not whole_tcp128 or
            small_win["sustained_total"]!=small_linux["sustained_total"]):
            raise RuntimeError("P2 real baseline/Direct 1MiB + concurrent Tunnel UDP independent proof invalid")
        abba=None
        if ABBA:
            if len(direct_proofs)!=4 or any(
                    trial["role"]!="direct" or
                    trial["presented_peer"]!=fake or
                    trial["socket_source"]!="10.66.0.2" or
                    trial["echo_bytes"]!=SIZE or
                    trial["payload_sha256"]!=SHA or
                    trial["app_tcp_nodelay"]!=base["app_tcp_nodelay"] or
                    trial["half_close"] is not True
                    for trial in direct_proofs):
                raise RuntimeError("P2 A-B-B-A true Direct 4MiB SHA/FIN/source invalid")
            tests=[{"ordinal":i+1,"mode":ABBA_MODES[i],**item}
                   for i,item in enumerate(direct_proofs)]
            a_ms=(tests[0]["elapsed_ms"]+tests[3]["elapsed_ms"])/2
            b_ms=(tests[1]["elapsed_ms"]+tests[2]["elapsed_ms"])/2
            abba={
                "status":"PENDING_OWNER_STOP",
                "scope":"FOUR_REAL_FAKEIP_DIRECT_TCP_ONE_VM_ONE_BINARY_ONE_WINTUN_GENERATION",
                "test_port":PORT,"order":list(ABBA_MODES),
                "trials":tests,"copy_mean_ms":round(a_ms,3),
                "bypass_mean_ms":round(b_ms,3),
                "bypass_minus_copy_ms":round(b_ms-a_ms,3),
                "bypass_div_copy":round(b_ms/max(.001,a_ms),4),
                "rust_admission_verified":False,
                "stop":"NOT_RUN_UNTIL_OWNER_STOP",
                "cpu_user_kernel":"NOT_MEASURED_4_SHORT_TRIALS",
                "driver_cpu":"NOT_ATTRIBUTED",
                "performance_judgment":"MEASURED_ABBA_NOT_YET_REPRODUCED"
            }
        preconnect_bulk=None
        if PRECON_BULK:
            if len(direct_proofs)!=4 or any(
                trial["role"]!="direct" or trial["echo_bytes"]!=SIZE or
                trial["payload_sha256"]!=SHA or
                trial["presented_peer"]!=fake or
                trial["socket_source"]!="10.66.0.2" or
                trial["app_tcp_nodelay"]!=base["app_tcp_nodelay"] or
                trial["half_close"] is not True or
                not 1024<=trial["socket_source_port"]<=65535
                for trial in direct_proofs):
                raise RuntimeError("H1956 four real 4MiB Direct SHA/FIN/source proofs invalid")
            modes=["on","off","off","on"]
            trials=[{"ordinal":i+1,"preconnect":modes[i],**v}
                for i,v in enumerate(direct_proofs)]
            on=(trials[0]["elapsed_ms"]+trials[3]["elapsed_ms"])/2
            off=(trials[1]["elapsed_ms"]+trials[2]["elapsed_ms"])/2
            preconnect_bulk={
                "status":"PENDING_ORIGINAL_OWNED_STOP_AND_QPC",
                "source_sha":source,"scope":"ONE_WIN_VM_ORIGINAL_RUST_WINTUN_4X_UNPACED_4M_SHA_FIN_WITH_TUNNEL_UDP",
                "order":modes,"trials":trials,
                "on_mean_elapsed_ms":round(on,3),
                "off_mean_elapsed_ms":round(off,3),
                "on_div_off_elapsed":round(on/max(.001,off),4),
                "preconnect_real_QPC_join":"PENDING_ORIGINAL_OWNER_STOP",
                "linux_kernel_tcp_connections":5,
                "all_unpaced_4mib":True,
                "cpu_or_driver_causality":"NOT_MEASURED"}
        # Same-run, same-VM phase attribution, not an inferred algorithmic
        # bottleneck or a peak throughput number. Additive deltas expose the
        # first dominant wait without changing the paced 1-MiB workload.
        phases=("connect_ms","upload_ms","half_close_ms",
                "first_reply_wait_ms","download_ms")
        delta={phase:round(direct_value[phase]-base[phase],3)
               for phase in phases}
        dominant=max(phases,key=lambda phase:delta[phase])
        ratio=round(direct_value["elapsed_ms"]/max(.001,base["elapsed_ms"]),3)
        return {"source_sha":source,"binary_source_sha":os.environ.get("WBD_WL_BINARY_SOURCE",source),
                "p2_timeline":{"direct_over_physical_elapsed_ratio":ratio,
                    "normal_128k_app_progress":normal_gaps,
                    "direct_minus_physical_phase_ms":delta,
                    "dominant_added_wait_phase":dominant,
                    "same_vm_sequential_baseline":True,
                    "workload":"UNPACED_4M_16K_BLOCKS" if BULK else "PACED_16K_BLOCKS_4MS_NOT_PEAK",
                    "no_single_kernel_cause_claim":True},
                "scope":"REAL_PHYSICAL_SOCKET_BASELINE_VS_FAKEIP_RUST_DIRECT_AND_SUSTAINED_TUNNEL_UDP",
                "load_bytes":SIZE,"unpaced_bulk":BULK,
                "physical_baseline":base,"direct_windows":direct_value,"physical_guest":linux,
                "tunnel_windows":small_win,"tunnel_linux":small_linux,
                "windows_direct_fakeip":fake,"overlap":overlap,
                "covered_whole_direct_tcp":whole_direct,
                "udp_sustained_total":small_win["sustained_total"],
                "same_vm_abba":abba,
                "same_vm_preconnect_bulk":preconnect_bulk,
                "tcp128":tcp128,
                "sustained_direct_tcp":sustained,
                "highrate_direct_tcp":highrate,
                "small_tcp_latency":latency,
                "steady_tcp_qpc":steady,
                "tunnel_udp_covers_all_128":whole_tcp128,
                "cpu_attribution":"NOT_MEASURED_P2_TWO_DIFFERENT_KERNEL_SOCKET_PATHS",
                "stop":"NOT_RUN_UNTIL_OWNER_STOP"}
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill()
        for f in streams:f.close()


# H1888: strictly typed, cold final Rust kernel-socket counter receipt.
# Read after the original Go owner stops; never inspect packet payload,
# remote IP, a secret or a sampled wall-clock on the data path.
H1888_IO_FIELDS=(
    "shard_wakes","event_socket_checks","event_take_errors",
    "event_read","event_write","event_connect","event_close",
    "ticket_peak","ticket_served","ticket_wait_sum_ms","ticket_wait_max_ms",
    "relay_turns","relay_no_progress",
    "relay_progress_no_self_ticket","relay_progress_self_ticket",
    "relay_close_probe_self_ticket",
    "inner_read_calls","outer_read_calls",
    "inner_read_wouldblock","outer_read_wouldblock",
    "inner_fin_peek_calls","outer_fin_peek_calls",
    "inner_fin_peek_eof","outer_fin_peek_eof",
    "inner_write_calls","outer_write_calls",
    "inner_write_wouldblock","outer_write_wouldblock",
    "inner_write_short","outer_write_short",
    "inner_read_gated","outer_read_gated",
    "inner_read_event_suppressed","outer_read_event_suppressed",
    "direct_forwarded","queued_copy",
)
H1943_REPLY_FIELDS=(
    "reply_outer_read_turns","reply_outer_ready_wait_max_ms",
    "reply_outer_ready_wait_ge8_ms","reply_outer_ready_wait_ge16_ms",
    "reply_outer_read_inner_write_same_turn",
    "reply_outer_read_no_inner_write",
    "reply_inner_write_deferred_turns",
)
def parse_kernel_io_final(text):
    marker="PLAN029_H1888_TCP_IO_FINAL "
    records=[line.split(marker,1)[1].strip() for line in text.splitlines()
             if marker in line]
    if len(records)!=1:
        raise RuntimeError("H1888 exactly one source-locked Rust kernel I/O final missing")
    tokens={}
    for item in records[0].split():
        if "=" in item:
            key,value=item.split("=",1)
            if key in tokens:raise RuntimeError("H1888 duplicate Rust I/O counter")
            tokens[key]=value
    if tokens.get("source")!="real_kernel_two_leg":
        raise RuntimeError("H1888 forged/missing actual kernel I/O scope")
    if any(key not in tokens or not tokens[key].isascii() or
           not tokens[key].isdecimal() for key in H1888_IO_FIELDS):
        raise RuntimeError("H1888 invalid/missing nonnegative typed I/O counter")
    fields={key:int(tokens[key]) for key in H1888_IO_FIELDS}
    # Original older signed Action reports remain readable; for H1943
    # reply attribution the seven counters MUST be present as a set.
    if any(k in tokens for k in H1943_REPLY_FIELDS):
        if any(k not in tokens or not tokens[k].isascii() or
               not tokens[k].isdecimal() for k in H1943_REPLY_FIELDS):
            raise RuntimeError("H1943 partial/invalid original reply diagnostic")
        fields.update({k:int(tokens[k]) for k in H1943_REPLY_FIELDS})
        if (fields["reply_outer_ready_wait_ge16_ms"]>
              fields["reply_outer_ready_wait_ge8_ms"] or
            fields["reply_outer_ready_wait_ge8_ms"]>
              fields["reply_outer_read_turns"] or
            fields["reply_outer_read_inner_write_same_turn"]+
              fields["reply_outer_read_no_inner_write"]!=
              fields["reply_outer_read_turns"]):
            raise RuntimeError("H1943 original Rust reply timing invariant failed")
    if (fields["inner_read_calls"]<1 or fields["outer_read_calls"]<1 or
        fields["ticket_served"]<1 or
        fields["relay_no_progress"]>fields["relay_turns"] or
        fields["relay_progress_no_self_ticket"]+
          fields["relay_progress_self_ticket"]>fields["relay_turns"] or
        fields["relay_close_probe_self_ticket"]>
          fields["relay_progress_self_ticket"] or
        any(fields[f"{leg}_fin_peek_eof"]>fields[f"{leg}_fin_peek_calls"]
            for leg in ("inner","outer")) or
        any(fields[f"{leg}_{op}_wouldblock"]>fields[f"{leg}_{op}_calls"]
            for leg in ("inner","outer") for op in ("read","write"))):
        raise RuntimeError("H1888 Rust kernel readiness/call count invariant invalid")
    return {"scope":"FINAL_ONE_ORIGINAL_RUST_TX_TWO_KERNEL_TCP_LEGS",
            "attribution":"USER_KERNEL_DRIVER_CPU_NOT_MEASURED",
            "values":fields}

if __name__=="__main__":
    # An optional exact fixture-only fourth argument is carried explicitly
    # across wsl.exe, where Windows environment variables are not inherited.
    # Never silently run different payload sizes on the two kernel legs.
    if len(sys.argv) not in (4,5,6):
        raise SystemExit("P2 role, two addresses, optional workload and ABBA selection required")
    if len(sys.argv)>=5 and (
        sys.argv[4] not in ("p2bulk","p2paced") or
        BULK!=(sys.argv[4]=="p2bulk")):
        raise SystemExit("P2 physical and Wintun workload selection mismatch")
    if len(sys.argv)==6:
        if (sys.argv[5] not in ("p2abba","p2ordinary","p2preconnect4") or
                ABBA!=(sys.argv[5]=="p2abba") or
                PRECON_BULK!=(sys.argv[5]=="p2preconnect4")):
            raise SystemExit("P2 WSL explicit ABBA selection mismatch")
    elif ABBA:
        # Exact H1861 original WSL ABBA source contract; unchanged.
        raise SystemExit("P2 ABBA requires explicit WSL argv, not env-only activation")
    elif PRECON_BULK:
        raise SystemExit("H1958 signed preconnect bulk requires explicit WSL argv, not env-only activation")
    role,a,b=sys.argv[1:4]
    if role=="guest_tcp":tcp_guest(a,b)
    elif role=="guest_udp":udp_guest(a,b)
    elif role in ("baseline","direct"):tcp_client(role,a,b)
    elif role=="windows_udp":udp_windows(a,b)
    else:raise SystemExit("P2 unrecognized role")
