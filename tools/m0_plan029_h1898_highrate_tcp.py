#!/usr/bin/env python3
"""H1898: real Wintun/WSL2 TCP 500 Mb/s single-leg and 700 Mb/s aggregate full-duplex target.

A SOURCE-locked test application, NOT a Go/Rust data-plane pump or
a promise that a shared CI VM achieves these link rates. Streaming
64KiB chunks: never allocate 512MiB in the Python or product queues.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from m0_plan029_h1896_sustain_tcp import (
    BLOCK,DATA,process_cpu_times,expected_sha,recv_exact_data,read_control,
    idle_baseline,cpu_delta,FileTime,
)

PORT=46118
# H1903: an explicitly signed, source-locked long 2-GiB/1.5-GiB
# challenge. A short H1898 run preserves all previous constants and
# receipts. Linux WSL.exe does NOT inherit the Windows runner env, so
# both signed OS applications require the explicit p2long argv marker.
LONG=(os.environ.get("WBD_PLAN029_P2_LONG_RATE_SCENE")=="1" or
      (len(sys.argv)>1 and sys.argv[-1]=="p2long"))
ONE_WAY_BYTES=(2*1024*1024*1024 if LONG else 512*1024*1024)
DUPLEX_BYTES=(1536*1024*1024 if LONG else 256*1024*1024)
ONE_WAY_TARGET_BPS=500_000_000
DUPLEX_TARGET_AGG_BPS=700_000_000
MAX_STAGE_S=180 if LONG else 100
WIN_MARK="PLAN029_H1898_WINDOWS_HIGH_RATE"
GUEST_MARK="PLAN029_H1898_LINUX_HIGH_RATE"
SCOPE="ONE_REAL_WINTUN_FAKEIP_TCP_AND_WSL2_PHYSICAL_FULL_DUPLEX"
assert ONE_WAY_BYTES%BLOCK==DUPLEX_BYTES%BLOCK==0
ONE_WAY_SHA=expected_sha(ONE_WAY_BYTES)
DUPLEX_SHA=expected_sha(DUPLEX_BYTES)

def emit(marker,payload):
    print(marker+" "+json.dumps(payload,sort_keys=True,separators=(",",":")),flush=True)

def send_stream(sock,total,rate_bytes_s):
    """Bounded absolute-rate sender, zero unbounded data buffering."""
    began=time.perf_counter()
    for sent in range(0,total,BLOCK):
        deadline=began+sent/rate_bytes_s
        while True:
            left=deadline-time.perf_counter()
            if left<=0:break
            time.sleep(min(.002,left))
        sock.sendall(DATA)
    return time.perf_counter()-began

def duplex(sock,bytes_each,rate_each):
    """One test sender thread and one test receiver on SAME OS socket.
    A separate control ack only after BOTH directions SHA/byte-complete.
    No per-flow Rust thread or second TCP proxy.
    """
    errors=[]
    sent=[]
    def writer():
        try:sent.append(send_stream(sock,bytes_each,rate_each))
        except BaseException as exc:errors.append(str(exc))
    worker=threading.Thread(target=writer,name="test-only-tcp-duplex-writer")
    began=time.perf_counter()
    worker.start()
    try:received,digest=recv_exact_data(sock,bytes_each)
    except BaseException as exc:
        errors.append(str(exc));received=0;digest=""
    worker.join(timeout=MAX_STAGE_S)
    if worker.is_alive() or errors:
        raise RuntimeError("H1898 real simultaneous kernel duplex failed "+repr(errors))
    if received!=bytes_each or digest!=DUPLEX_SHA:
        raise RuntimeError("H1898 genuine bidirectional SHA mismatch")
    return {"elapsed_s":round(time.perf_counter()-began,6),
            "local_sent_bytes":bytes_each,"local_received_bytes":received,
            "local_send_elapsed_s":round(sent[0],6),
            "received_sha256":digest,"same_kernel_socket":True,
            "two_test_application_io_threads":True}

def host_cpu_snapshot():
    """Original Windows all-logical-core GetSystemTimes, not driver CPU.
    """
    if os.name!="nt":raise RuntimeError("H1898 actual Windows host required")
    import ctypes
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.GetSystemTimes.argtypes=[ctypes.POINTER(FileTime)]*3
    k.GetSystemTimes.restype=ctypes.c_int
    idle,system,user=(FileTime() for _ in range(3))
    if not k.GetSystemTimes(ctypes.byref(idle),ctypes.byref(system),
                            ctypes.byref(user)):
        raise RuntimeError("H1898 GetSystemTimes failed")
    def seconds(ft):return ((int(ft.high)<<32)|int(ft.low))*1e-7
    return (seconds(idle),seconds(system),seconds(user))

def host_cpu_delta(first,last):
    idle=max(0.,last[0]-first[0])
    kernel=max(0.,last[1]-first[1])
    user=max(0.,last[2]-first[2])
    total=kernel+user
    busy=max(0.,total-idle)
    if total<=0:raise RuntimeError("H1898 host CPU clock failed")
    return {"host_all_logical_cpu_busy_pct":round(100*busy/total,4),
            "host_cpu_time_busy_s":round(busy,6),
            "host_kernel_includes_idle_s":round(kernel,6),
            "host_user_s":round(user,6),
            "scope":"ALL_WINDOWS_LOGICAL_CPUS_INCLUDES_OTHER_RUNNER_PROCESSES_AND_DRIVERS"}

def windows_original_stage(pid,func,total):
    # Original Windows Go+Rust (not the Python load generator) plus same
    # Tunnel UDP measured at exact workload boundaries.
    p0=process_cpu_times(pid)
    g0=process_cpu_times(os.getpid())
    h0=host_cpu_snapshot()
    began=time.perf_counter()
    data=func()
    ended=time.perf_counter()
    p1=process_cpu_times(pid)
    g1=process_cpu_times(os.getpid())
    h1=host_cpu_snapshot()
    sec=ended-began
    if sec<=0:raise RuntimeError("H1898 invalid monotonic interval")
    return {"start_monotonic_s":began,"end_monotonic_s":ended,
            "elapsed_s":round(sec,6),**data,
            "original_process_cpu":cpu_delta(p0,p1,sec,total),
            "load_generator_cpu":cpu_delta(g0,g1,sec,total),
            "windows_host_cpu":host_cpu_delta(h0,h1),
            "original_process_scope":"WIN32_ORIGINAL_GO_PLUS_RUST_WITH_CONCURRENT_TUNNEL_UDP",
            "load_generator_scope":"SEPARATE_WINDOWS_PYTHON_APPLICATION_PROCESS"}

def guest(physical,expected_source,source):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((physical,PORT));listener.listen(2 if LONG else 1)
        listener.settimeout(30)
        print("PLAN029_H1898_LINUX_READY",flush=True)
        sessions=[]
        # Same Linux physical kernel listener, first ORIGINAL Windows
        # underlay control, then signed Wintun FakeIP Direct. Never an
        # artificial ACK, tunnel socket, or generated performance number.
        for ordinal in range(2 if LONG else 1):
            conn,peer=listener.accept()
            if peer[0]!=expected_source:
                raise RuntimeError("H1903 Linux saw nonphysical source")
            with conn:
                conn.settimeout(MAX_STAGE_S)
                conn.sendall(b"R")
                n,h=recv_exact_data(conn,ONE_WAY_BYTES)
                if n!=ONE_WAY_BYTES or h!=ONE_WAY_SHA:
                    raise RuntimeError("H1903 Linux physical TCP one-way SHA/bytes mismatch")
                conn.sendall(b"u")
                read_control(conn,b"D")
                conn.sendall(b"d")
                duplex_result=duplex(conn,DUPLEX_BYTES,
                                     DUPLEX_TARGET_AGG_BPS/16)
                # Each sender target = 700Mb/s aggregate /2 /8 B/s.
                conn.sendall(b"k")
                read_control(conn,b"y")
                conn.shutdown(socket.SHUT_WR)
                if conn.recv(1)!=b"":
                    raise RuntimeError("H1903 genuine Windows FIN absent")
            sessions.append({
                "path":"physical" if LONG and ordinal==0 else "direct",
                "source_ip":peer[0],"oneway_received_bytes":n,
                "oneway_sha256":h,"duplex":duplex_result,
                "half_close":True})
        last=sessions[-1]
        emit(GUEST_MARK,{"source_sha":source,"physical_source":last["source_ip"],
                         "physical_listener":physical,
                         "oneway_received_bytes":last["oneway_received_bytes"],
                         "oneway_sha256":last["oneway_sha256"],
                         "duplex":last["duplex"],"sessions":sessions,
                         "half_close":True,
                         "scope":"REAL_LINUX_KERNEL_TCP_ON_PHYSICAL_SOURCE"})

def windows(lease,fake,source,pid,phase_file,mode="direct"):
    if (mode not in ("physical","direct") or
        (mode=="physical" and not LONG) or
        (mode=="direct" and
         (lease!="10.66.0.2" or not fake.startswith("198.18.")))):
        raise RuntimeError("H1903 wrong source-bound physical/Direct selector")
    if pid<=0:raise RuntimeError("H1898 no original Go+Rust PID")
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(MAX_STAGE_S)
        sock.bind((lease,0))
        connected_start=time.perf_counter()
        sock.connect((fake,PORT))
        connect_ms=(time.perf_counter()-connected_start)*1000
        read_control(sock,b"R")
        def confirmed_upload():
            sent_s=send_stream(sock,ONE_WAY_BYTES,ONE_WAY_TARGET_BPS/8)
            read_control(sock,b"u") # Linux verified 512MiB+SHA
            return {"local_sent_bytes":ONE_WAY_BYTES,
                    "sender_elapsed_s":round(sent_s,6),
                    "receiver_sha256":ONE_WAY_SHA}
        one=windows_original_stage(pid,confirmed_upload,ONE_WAY_BYTES)
        sock.sendall(b"D")
        read_control(sock,b"d")
        def confirmed_duplex():
            result=duplex(sock,DUPLEX_BYTES,DUPLEX_TARGET_AGG_BPS/16)
            read_control(sock,b"k") # Linux verified duplex SHA
            return result
        two=windows_original_stage(pid,confirmed_duplex,2*DUPLEX_BYTES)
        sock.sendall(b"y")
        sock.shutdown(socket.SHUT_WR)
        if sock.recv(1)!=b"":
            raise RuntimeError("H1898 genuine Linux kernel FIN absent")
    stages={"oneway_500mbps":one,"duplex_700mbps_aggregate":two}
    for key,phase in stages.items():
        elapsed=phase["elapsed_s"]
        good=(ONE_WAY_BYTES if key=="oneway_500mbps" else 2*DUPLEX_BYTES)
        actual=good*8/elapsed/1e6
        phase["actual_aggregate_mbps"]=round(actual,3)
        phase["target_aggregate_mbps"]=(
            500 if key=="oneway_500mbps" else 700)
        phase["target_reached"]=actual>=phase["target_aggregate_mbps"]
        phase["wall_clock_mbps_not_driver_cpu"]=True
    # Only written after genuine kernel SHA+FIN. Different application
    # processes share Windows QPC monotonic epochs for the SAME runner.
    # Do not overwrite the earlier physical control phase timestamps.
    old={"source_sha":source,"windows":{}}
    if LONG and mode=="direct":
        old=json.loads(Path(phase_file).read_text(encoding="utf-8"))
        if (old.get("source_sha")!=source or
            set(old.get("windows",{}))!={
                "physical_oneway_500mbps",
                "physical_duplex_700mbps_aggregate"}):
            raise RuntimeError("H1903 genuine physical preflight QPC timeline absent")
    for name,value in stages.items():
        key=("physical_"+name if LONG and mode=="physical" else name)
        if key in old["windows"]:
            raise RuntimeError("H1903 duplicate physical/Direct phase")
        old["windows"][key]={
            "start_monotonic_s":value["start_monotonic_s"],
            "end_monotonic_s":value["end_monotonic_s"]}
    Path(phase_file).write_text(json.dumps(old,sort_keys=True),
                                encoding="utf-8")
    emit(WIN_MARK,{"source_sha":source,"original_pid":pid,
                   "actual_client_lease":lease,"actual_fakeip_peer":fake,
                   "path":mode,"test_port":PORT,
                   "connect_ms":round(connect_ms,3),
                   "one_real_full_duplex_tcp_socket":True,
                   "warmup":"H1815_ORIGINAL_4M_P2_PRECEDES_RATE_SCENE",
                   "stages":stages,"windows_half_close":True,
                   "scope":SCOPE if mode=="direct" else
                       "REAL_PHYSICAL_WINDOWS_TO_WSL2_TCP_SAME_OWNER_CPU_CONTROL"})

def original_cpu_increment(physical,direct):
    """Matched signed Windows PID: incremental Go+Rust process CPU per GiB.
    Not kernel-wide driver ISR/DPC time and not a separate Rust TX sample.
    Keep signed negative differences as possible CI jitter, NEVER clamp.
    """
    out={}
    for stage in ("oneway_500mbps","duplex_700mbps_aggregate"):
        a=physical["stages"][stage]
        b=direct["stages"][stage]
        if (a["local_sent_bytes"]!=b["local_sent_bytes"] or
            a["target_aggregate_mbps"]!=b["target_aggregate_mbps"] or
            a["elapsed_s"]<=0 or b["elapsed_s"]<=0):
            raise RuntimeError("H1903 CPU baseline mismatch in real same-VM stage")
        old=a["original_process_cpu"]
        new=b["original_process_cpu"]
        out[stage]={
            "physical_actual_mbps":a["actual_aggregate_mbps"],
            "direct_actual_mbps":b["actual_aggregate_mbps"],
            "physical_process_total_cpu_s_per_gib":
                old["original_process_total_cpu_s_per_gib"],
            "direct_process_total_cpu_s_per_gib":
                new["original_process_total_cpu_s_per_gib"],
            "added_process_total_cpu_s_per_gib":round(
                new["original_process_total_cpu_s_per_gib"]-
                old["original_process_total_cpu_s_per_gib"],6),
            "added_process_user_cpu_s_per_gib":round(
                new["original_process_user_cpu_s_per_gib"]-
                old["original_process_user_cpu_s_per_gib"],6),
            "added_process_kernel_cpu_s_per_gib":round(
                new["original_process_kernel_cpu_s_per_gib"]-
                old["original_process_kernel_cpu_s_per_gib"],6),
            "windows_host_busy_pct_physical":
                a["windows_host_cpu"]["host_all_logical_cpu_busy_pct"],
            "windows_host_busy_pct_direct":
                b["windows_host_cpu"]["host_all_logical_cpu_busy_pct"],
            "scope":"SAME_SOURCE_SAME_WINDOWS_PROCESS_MATCHED_DATA_VOLUME_DIFFERENT_CONSECUTIVE_TCP_SESSIONS_NOT_DRIVER_CPU"}
    return out

def proof(log,marker):
    rows=[line.split(marker+" ",1)[1] for line in Path(log).read_text(
        errors="replace").splitlines() if line.startswith(marker+" ")]
    if len(rows)!=1:raise RuntimeError("H1898 exact signed OS receipt missing")
    return json.loads(rows[0])

def run_highrate(root,out,physical,host_source,fake,unix,ready,pid):
    if (os.environ.get("WBD_PLAN029_P2_HIGH_RATE_SCENE")!="1" or
        os.environ.get("WBD_PLAN029_P2_MIXED_SCENE")!="1" or
        os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="1" or
        os.environ.get("GITHUB_ACTIONS")!="true"):
        raise RuntimeError("H1898 high-rate only original signed Normal P2")
    source=os.environ["GITHUB_SHA"]
    if LONG and not (
        os.environ.get("WBD_PLAN029_P2_LONG_RATE_SCENE")=="1" and
        os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1"):
        raise RuntimeError("H1903 long physical/direct requires signed bulk source")
    script=Path(root)/"tools"/"m0_plan029_h1898_highrate_tcp.py"
    guest_log=Path(out)/"plan029-h1898-rate-linux.log"
    win_log=Path(out)/"plan029-h1898-rate-windows.log"
    physical_log=Path(out)/"plan029-h1903-long-physical-windows.log"
    phase_file=Path(out)/"plan029-h1898-rate-phases.json"
    children=[]
    try:
        with guest_log.open("w") as gf:
            guest_args=["wsl.exe","-d","Ubuntu","-u","root","--",
                "python3","-u",unix(script),"guest",physical,host_source,source]
            if LONG:guest_args.append("p2long")
            g=subprocess.Popen(guest_args,stdout=gf,
                               stderr=subprocess.STDOUT);children.append(g)
            ready(guest_log,"PLAN029_H1898_LINUX_READY",g,12)
            # Comparable same original Windows process / same 96B UDP
            # before/after bounded controls, no actual new H1898 SYN yet.
            pre_start=time.perf_counter()
            pre=idle_baseline(pid)
            pre_end=time.perf_counter()
            if LONG:
                with physical_log.open("w") as pf:
                    physical_args=[sys.executable,"-u",str(script),"windows",
                        host_source,physical,source,str(pid),str(phase_file),
                        "physical","p2long"]
                    phys=subprocess.Popen(physical_args,stdout=pf,
                                          stderr=subprocess.STDOUT)
                    children.append(phys)
                    try:physical_rc=phys.wait(timeout=400)
                    except subprocess.TimeoutExpired:
                        raise RuntimeError("H1903 original physical TCP timeout "+
                              physical_log.read_text(errors="replace")[-1400:])
                    if physical_rc:
                        raise RuntimeError("H1903 original physical TCP failed "+
                              physical_log.read_text(errors="replace")[-1400:])
            with win_log.open("w") as wf:
                win_args=[sys.executable,"-u",str(script),"windows",
                    "10.66.0.2",fake,source,str(pid),str(phase_file)]
                if LONG:win_args.extend(["direct","p2long"])
                w=subprocess.Popen(win_args,stdout=wf,
                                   stderr=subprocess.STDOUT);children.append(w)
                try:rc=w.wait(timeout=400 if LONG else 210)
                except subprocess.TimeoutExpired:
                    raise RuntimeError("H1898 real rate client timeout "+
                                       win_log.read_text(errors="replace")[-1200:])
                if rc:raise RuntimeError("H1898 real Windows client failed "+
                                         win_log.read_text(errors="replace")[-1200:])
            try:rc=g.wait(timeout=12)
            except subprocess.TimeoutExpired:
                raise RuntimeError("H1898 real Linux kernel duplex timeout")
            if rc:raise RuntimeError("H1898 real WSL2 guest failed "+
                                     guest_log.read_text(errors="replace")[-1200:])
            post_start=time.perf_counter()
            post=idle_baseline(pid)
            post_end=time.perf_counter()
        phase_windows=json.loads(phase_file.read_text(encoding="utf-8"))
        if phase_windows.get("source_sha")!=source:
            raise RuntimeError("H1898 original Windows QPC stage source mismatch")
        phase_windows["windows"]["pre"]={
            "start_monotonic_s":pre_start,"end_monotonic_s":pre_end}
        phase_windows["windows"]["post"]={
            "start_monotonic_s":post_start,"end_monotonic_s":post_end}
        phase_file.write_text(json.dumps(phase_windows,sort_keys=True),
                              encoding="utf-8")
        w=proof(win_log,WIN_MARK);g=proof(guest_log,GUEST_MARK)
        physical_receipt=proof(physical_log,WIN_MARK) if LONG else None
        stages=w["stages"]
        if (w["source_sha"]!=source or g["source_sha"]!=source or
            w["scope"]!=SCOPE or w["original_pid"]!=pid or
            w["actual_fakeip_peer"]!=fake or
            w["actual_client_lease"]!="10.66.0.2" or
            g["physical_source"]!=host_source or
            not w["windows_half_close"] or not g["half_close"] or
            not w["one_real_full_duplex_tcp_socket"] or
            g["oneway_received_bytes"]!=ONE_WAY_BYTES or
            g["oneway_sha256"]!=expected_sha(ONE_WAY_BYTES) or
            set(stages)!={"oneway_500mbps","duplex_700mbps_aggregate"} or
            stages["oneway_500mbps"]["local_sent_bytes"]!=ONE_WAY_BYTES or
            stages["duplex_700mbps_aggregate"]["local_sent_bytes"]!=DUPLEX_BYTES or
            stages["duplex_700mbps_aggregate"]["local_received_bytes"]!=DUPLEX_BYTES or
            g["duplex"]["local_sent_bytes"]!=DUPLEX_BYTES or
            g["duplex"]["local_received_bytes"]!=DUPLEX_BYTES):
            raise RuntimeError("H1898 true original 500/700Mb/s challenge evidence mismatch")
        for stage in list(stages.values())+(
                list(physical_receipt["stages"].values()) if LONG else []):
            if not ((30.0 if LONG else 2.0)<=stage["elapsed_s"]<=MAX_STAGE_S and
                stage["actual_aggregate_mbps"]>0 and
                stage["original_process_cpu"]["original_process_total_cpu_s_per_gib"]>=0 and
                stage["load_generator_cpu"]["original_process_total_cpu_s_per_gib"]>=0):
                raise RuntimeError("H1903 signed sustained CPU/throughput stage invalid")
        incremental=None
        if LONG:
            sessions=g.get("sessions",[])
            if (len(sessions)!=2 or
                [x.get("path") for x in sessions]!=["physical","direct"] or
                physical_receipt["source_sha"]!=source or
                physical_receipt["path"]!="physical" or
                physical_receipt["actual_client_lease"]!=host_source or
                physical_receipt["actual_fakeip_peer"]!=physical or
                physical_receipt["original_pid"]!=pid or
                w.get("path")!="direct" or
                physical_receipt["windows_half_close"] is not True or
                any(x.get("oneway_sha256")!=ONE_WAY_SHA or
                    x.get("oneway_received_bytes")!=ONE_WAY_BYTES or
                    x.get("duplex",{}).get("local_received_bytes")!=DUPLEX_BYTES or
                    x.get("duplex",{}).get("local_sent_bytes")!=DUPLEX_BYTES or
                    x.get("half_close") is not True
                    for x in sessions)):
                raise RuntimeError("H1903 actual physical and Direct session SHA/FIN/source incomplete")
            incremental=original_cpu_increment(physical_receipt,w)
        return {"source_sha":source,"status":"PENDING_UDP_AND_STOP",
                "scope":("REAL_SAME_VM_PHYSICAL_AND_WINTUN_2GIB_UP_1P5GIB_EACH_DUPLEX"
                         if LONG else
                         "REAL_FAKEIP_WIN_LINUX_512M_UP_AND_256M_EACH_FULL_DUPLEX"),
                "windows":w,"linux":g,"phase_windows":phase_windows,
                "physical_control":physical_receipt,
                "same_vm_original_process_cpu_increment":incremental,
                "pre_udp_only_cpu":pre,"post_udp_only_cpu":post,
                "tunnel_udp_per_stage":"NOT_RUN",
                "owner_stop":"NOT_RUN",
                "rate_result":"TARGET_MEASURED_NOT_PREDECLARED"}
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill()

if __name__=="__main__":
    if len(sys.argv)==5 and sys.argv[1]=="guest":
        guest(*sys.argv[2:])
    elif len(sys.argv)==6 and sys.argv[1]=="guest" and sys.argv[5]=="p2long":
        guest(*sys.argv[2:5])
    elif len(sys.argv)==7 and sys.argv[1]=="windows":
        windows(*sys.argv[2:5],int(sys.argv[5]),sys.argv[6])
    elif (len(sys.argv)==9 and sys.argv[1]=="windows" and
          sys.argv[8]=="p2long" and sys.argv[7] in ("physical","direct")):
        windows(*sys.argv[2:5],int(sys.argv[5]),sys.argv[6],sys.argv[7])
    else:raise SystemExit("H1903 only source-pinned signed Windows/WSL2 roles")
