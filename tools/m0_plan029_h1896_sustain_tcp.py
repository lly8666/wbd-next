#!/usr/bin/env python3
"""PLAN029 H1896: one original-Wintun signed 30s/30s TCP cost fixture.

This is an OS TCP APPLICATION, not a VPN data pump. One Windows socket binds
the real Wintun /32 and targets a genuine FakeIP; the WSL2 peer listens on the
physical IP. The original Go+Rust product, signed Npcap/Wintun, Linux peer,
and concurrent Tunnel UDP are owned by the existing Normal E2E job.
"""
import ctypes
import hashlib
import json
import os
import subprocess
import socket
import sys
import time
from pathlib import Path

PORT=46118
BLOCK=65536
RATE_BYTES_S=8*1024*1024
DURATION_S=30
WARMUP_S=2
MEASURE_BYTES=RATE_BYTES_S*DURATION_S
WARMUP_BYTES=RATE_BYTES_S*WARMUP_S
PREFIX=b"PLAN029-H1896-TRUE-OS-SOCKET-BULK/"
DATA=(PREFIX*((BLOCK+len(PREFIX)-1)//len(PREFIX)))[:BLOCK]
MARK_LINUX="PLAN029_H1896_SUSTAIN_LINUX"
MARK_WINDOWS="PLAN029_H1896_SUSTAIN_WINDOWS"

def emit(name,data):
    print(name+" "+json.dumps(data,sort_keys=True),flush=True)

def expected_sha(total):
    if total%BLOCK:raise RuntimeError("H1896 misaligned fixed load")
    h=hashlib.sha256()
    for _ in range(total//BLOCK):h.update(DATA)
    return h.hexdigest()

def recv_exact_data(sock,total):
    received=0;digest=hashlib.sha256()
    while received<total:
        data=sock.recv(min(BLOCK,total-received))
        if not data:raise RuntimeError("H1896 actual TCP early EOF")
        digest.update(data);received+=len(data)
    return received,digest.hexdigest()

def read_control(sock,expected):
    got=sock.recv(1)
    if got!=expected:
        raise RuntimeError("H1896 actual kernel TCP stage marker/ack mismatch")

def send_at_fixed_rate(sock,total,rate=RATE_BYTES_S):
    """Absolute QPC pacing; bounded source load, no per-segment print."""
    if total%BLOCK:raise RuntimeError("H1896 send load not block aligned")
    started=time.perf_counter()
    for sent in range(0,total,BLOCK):
        due=started+sent/rate
        while True:
            left=due-time.perf_counter()
            if left<=0:break
            time.sleep(min(.004,left))
        sock.sendall(DATA)
    end=time.perf_counter()
    # Last chunk must not finish earlier than the declared 30s interval.
    while end<started+total/rate:
        time.sleep(min(.004,started+total/rate-end))
        end=time.perf_counter()
    return round(end-started,6)

class FileTime(ctypes.Structure):
    _fields_=[("low",ctypes.c_uint32),("high",ctypes.c_uint32)]

def process_cpu_times(pid):
    """Win32 GetProcessTimes for the ORIGINAL Go+Rust process, not generator.
    Sampled only at an 8s idle-control or 30s phase boundary. User/kernel
    process time does NOT include driver ISR/DPC or Linux TUN CPU.
    """
    if os.name!="nt" or pid<=0:
        raise RuntimeError("H1896 original Win32 process-only CPU required")
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
    k.OpenProcess.restype=ctypes.c_void_p
    k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(FileTime)]*4
    k.GetProcessTimes.restype=ctypes.c_int
    k.CloseHandle.argtypes=[ctypes.c_void_p]
    k.CloseHandle.restype=ctypes.c_int
    h=k.OpenProcess(0x1000,0,pid)
    if not h:raise RuntimeError("H1896 original product OpenProcess failed")
    try:
        c,e,kt,ut=(FileTime() for _ in range(4))
        if not k.GetProcessTimes(h,ctypes.byref(c),ctypes.byref(e),
                                 ctypes.byref(kt),ctypes.byref(ut)):
            raise RuntimeError("H1896 original GetProcessTimes failed")
        def seconds(ft):
            return ((int(ft.high)<<32)|int(ft.low))*1e-7
        return {"user":seconds(ut),"kernel":seconds(kt)}
    finally:k.CloseHandle(h)

def cpu_delta(begin,end,elapsed,bytes_delivered,background=None):
    if not (elapsed>=2 and bytes_delivered>0):
        raise RuntimeError("H1896 invalid signed CPU stage interval")
    ud=end["user"]-begin["user"]
    kd=end["kernel"]-begin["kernel"]
    if ud<0 or kd<0:raise RuntimeError("H1896 non-monotonic original CPU")
    gib=bytes_delivered/(1024**3)
    result={
        "original_process_user_cpu_s":round(ud,6),
        "original_process_kernel_cpu_s":round(kd,6),
        "original_process_total_cpu_s":round(ud+kd,6),
        "original_process_user_cpu_s_per_gib":round(ud/gib,6),
        "original_process_kernel_cpu_s_per_gib":round(kd/gib,6),
        "original_process_total_cpu_s_per_gib":round((ud+kd)/gib,6),
        "original_process_cpu_pct_of_one_core":round(100*(ud+kd)/elapsed,4),
        "cpu_scope":"WIN32_ORIGINAL_GO_PLUS_RUST_PROCESS_WITH_TUNNEL_UDP_NO_DRIVER_ISR_DPC"
    }
    if background:
        # Estimate only, not a measurement of Direct-only CPU: the ongoing
        # Tunnel UDP and preceding short TCP may not have identical costs.
        u=max(0.,ud-background["user_cpu_s_per_s"]*elapsed)
        k=max(0.,kd-background["kernel_cpu_s_per_s"]*elapsed)
        result["idle_udp_background_subtracted_estimate"]={
            "user_cpu_s_per_gib":round(u/gib,6),
            "kernel_cpu_s_per_gib":round(k/gib,6),
            "method":"ONE_PRECEDING_8S_SAME_OWNER_SAME_UDP_RATE_NONCAUSAL_ESTIMATE"
        }
    return result

def idle_baseline(pid,duration=8):
    if duration!=8:raise RuntimeError("H1896 only bounded 8s same-owner control")
    b=process_cpu_times(pid)
    start=time.perf_counter()
    time.sleep(duration)
    end=time.perf_counter()
    e=process_cpu_times(pid)
    seconds=end-start
    if not 7.5<=seconds<=9.5:
        raise RuntimeError("H1896 baseline control interval invalid")
    return {"elapsed_s":round(seconds,6),
            "user_cpu_s_per_s":round((e["user"]-b["user"])/seconds,8),
            "kernel_cpu_s_per_s":round((e["kernel"]-b["kernel"])/seconds,8),
            "scope":"SAME_ORIGINAL_WINDOWS_PROCESS_WITH_96B_TUNNEL_UDP_NO_NEW_TCP"}
 
def guest(physical,host_source,source):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((physical,PORT));listener.listen(1);listener.settimeout(30)
        print("PLAN029_H1896_SUSTAIN_LINUX_READY",flush=True)
        conn,peer=listener.accept()
        if peer[0]!=host_source:
            raise RuntimeError("H1896 Linux physical TCP observed nonphysical source")
        with conn:
            conn.settimeout(90)
            warm_n,warm_hash=recv_exact_data(conn,WARMUP_BYTES)
            if warm_hash!=expected_sha(WARMUP_BYTES):
                raise RuntimeError("H1896 Windows->Linux warmup SHA wrong")
            conn.sendall(b"w")
            send_at_fixed_rate(conn,WARMUP_BYTES)
            read_control(conn,b"W")
            up_n,up_hash=recv_exact_data(conn,MEASURE_BYTES)
            if up_hash!=expected_sha(MEASURE_BYTES):
                raise RuntimeError("H1896 physical Linux received wrong sustained TCP upload")
            conn.sendall(b"u")
            read_control(conn,b"D")
            send_elapsed=send_at_fixed_rate(conn,MEASURE_BYTES)
            read_control(conn,b"d")
            conn.shutdown(socket.SHUT_WR)
            if conn.recv(1)!=b"":
                raise RuntimeError("H1896 genuine Windows TCP FIN missing")
        emit(MARK_LINUX,{
            "source_sha":source,
            "received_upload_bytes":up_n,
            "received_upload_sha256":up_hash,
            "sent_download_bytes":MEASURE_BYTES,
            "sent_download_sha256":expected_sha(MEASURE_BYTES),
            "physical_client_source":peer[0],
            "physical_listener":physical,
            "warmup_received_bytes":warm_n,
            "download_send_elapsed_s":send_elapsed,
            "half_close":True,
            "scope":"REAL_WSL2_LINUX_KERNEL_TCP_PHYSICAL_INNER_OS_RECEIVE"
        })

def windows(lease,fake,source,pid,phase_file,background_file):
    if lease!="10.66.0.2" or not fake.startswith("198.18."):
        raise RuntimeError("H1896 actual Wintun lease/FakeIP peer wrong")
    background=json.loads(Path(background_file).read_text(encoding="utf-8"))
    if (background.get("source_sha")!=source or
        background.get("scope")!=
        "SAME_ORIGINAL_WINDOWS_PROCESS_WITH_96B_TUNNEL_UDP_NO_NEW_TCP"):
        raise RuntimeError("H1896 original CPU control source mismatch")
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.settimeout(90)
        sock.bind((lease,0))
        connected_at=time.perf_counter()
        sock.connect((fake,PORT))
        connect_s=time.perf_counter()-connected_at
        nodelay=sock.getsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY)
        # Prewarm both directions on this SAME established FakeIP flow.
        send_at_fixed_rate(sock,WARMUP_BYTES)
        read_control(sock,b"w")
        sent_warm,hash_warm=recv_exact_data(sock,WARMUP_BYTES)
        if sent_warm!=WARMUP_BYTES or hash_warm!=expected_sha(WARMUP_BYTES):
            raise RuntimeError("H1896 Linux->Windows warmup bytes wrong")
        sock.sendall(b"W")
        phases={}
        u_before=process_cpu_times(pid)
        u_start=time.perf_counter()
        send_at_fixed_rate(sock,MEASURE_BYTES)
        read_control(sock,b"u")  # remote verified all 240 MiB
        u_end=time.perf_counter()
        u_after=process_cpu_times(pid)
        phases["upload"]={
            "start_monotonic_s":u_start,"end_monotonic_s":u_end,
            "elapsed_s":round(u_end-u_start,6),
            "delivered_bytes":MEASURE_BYTES,
            "receiver_sha256":expected_sha(MEASURE_BYTES),
            "throughput_mib_s":round(MEASURE_BYTES/(u_end-u_start)/1048576,4),
            "cpu":cpu_delta(u_before,u_after,u_end-u_start,MEASURE_BYTES,background)
        }
        d_before=process_cpu_times(pid)
        d_start=time.perf_counter()
        sock.sendall(b"D")
        d_n,d_hash=recv_exact_data(sock,MEASURE_BYTES)
        d_end=time.perf_counter()
        d_after=process_cpu_times(pid)
        if d_hash!=expected_sha(MEASURE_BYTES):
            raise RuntimeError("H1896 real Windows Wintun download SHA invalid")
        sock.sendall(b"d")
        phases["download"]={
            "start_monotonic_s":d_start,"end_monotonic_s":d_end,
            "elapsed_s":round(d_end-d_start,6),
            "delivered_bytes":d_n,"receiver_sha256":d_hash,
            "throughput_mib_s":round(d_n/(d_end-d_start)/1048576,4),
            "cpu":cpu_delta(d_before,d_after,d_end-d_start,d_n,background)
        }
        sock.shutdown(socket.SHUT_WR)
        if sock.recv(1)!=b"":
            raise RuntimeError("H1896 Linux kernel TCP FIN missing")
    if any(not 29.5<=phase["elapsed_s"]<=55 for phase in phases.values()):
        raise RuntimeError("H1896 target30s data phases outside bounded window")
    output={"source_sha":source,"test_port":PORT,
            "actual_client_lease":lease,"actual_fakeip_peer":fake,
            "original_pid":pid,"app_tcp_nodelay":nodelay,
            "one_persistent_socket":True,"warmup_each_direction_s":WARMUP_S,
            "warmup_each_direction_bytes":WARMUP_BYTES,
            "configured_target_mib_s":RATE_BYTES_S/1048576,
            "configured_phase_s":DURATION_S,
            "connect_ms":round(1000*connect_s,3),
            "phases":phases,"windows_half_close":True,
            "scope":"ONE_REAL_WINTUN_FAKEIP_TCP_TUNNEL_UDP_MIXED_TWO_PHASES"}
    Path(phase_file).write_text(json.dumps({"source_sha":source,"windows":{
        name:{"start_monotonic_s":phase["start_monotonic_s"],
              "end_monotonic_s":phase["end_monotonic_s"]}
        for name,phase in phases.items()}},sort_keys=True),encoding="utf-8")
    emit(MARK_WINDOWS,output)

def proof(path,marker):
    lines=[l.split(" ",1)[1] for l in Path(path).read_text(errors="replace").splitlines()
           if l.startswith(marker+" ")]
    if len(lines)!=1:raise RuntimeError("H1896 signed actual OS receipt absent/duplicated")
    return json.loads(lines[0])

def run_sustained(root,out,physical,host_source,fake,unix,ready,original_pid):
    if (os.environ.get("WBD_PLAN029_P2_SUSTAIN_SCENE")!="1" or
        os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="1" or
        os.environ.get("GITHUB_ACTIONS")!="true" or original_pid<=0):
        raise RuntimeError("H1896 restricted genuine signed original Normal owner only")
    source=os.environ["GITHUB_SHA"]
    script=Path(root)/"tools"/"m0_plan029_h1896_sustain_tcp.py"
    guestlog=Path(out)/"plan029-h1896-sustain-linux.log"
    winlog=Path(out)/"plan029-h1896-sustain-windows.log"
    phase_file=Path(out)/"plan029-h1896-sustain-windows-phases.json"
    background_file=Path(out)/"plan029-h1896-original-idle-udp-control.json"
    children=[]
    try:
        with guestlog.open("w") as f:
            guest_proc=subprocess.Popen([
                "wsl.exe","-d","Ubuntu","-u","root","--","python3","-u",unix(script),
                "guest",physical,host_source,source],
                stdout=f,stderr=subprocess.STDOUT)
            children.append(guest_proc)
            ready(guestlog,"PLAN029_H1896_SUSTAIN_LINUX_READY",guest_proc,12)
            # Baseline is taken while original Tunnel UDP continues and
            # BEFORE any new H1896 TCP application connects.
            background=idle_baseline(original_pid)
            background["source_sha"]=source
            background_file.write_text(json.dumps(background,sort_keys=True),
                                       encoding="utf-8")
            with winlog.open("w") as fw:
                win_proc=subprocess.Popen([
                    sys.executable,"-u",str(script),"windows","10.66.0.2",fake,
                    source,str(original_pid),str(phase_file),str(background_file)],
                    stdout=fw,stderr=subprocess.STDOUT)
                children.append(win_proc)
                try:rc=win_proc.wait(timeout=155)
                except subprocess.TimeoutExpired:
                    raise RuntimeError("H1896 real TCP sustained Windows timeout "+
                                       winlog.read_text(errors="replace")[-1400:])
                if rc:raise RuntimeError("H1896 signed Windows sustained app failed "+
                                         winlog.read_text(errors="replace")[-1400:])
            try:rc=guest_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                raise RuntimeError("H1896 Linux physical sustained TCP owner timeout")
            if rc:raise RuntimeError("H1896 Linux TCP sustained app failed "+
                                     guestlog.read_text(errors="replace")[-1400:])
        w=proof(winlog,MARK_WINDOWS);g=proof(guestlog,MARK_LINUX)
        phases=w.get("phases",{})
        if (w.get("source_sha")!=source or g.get("source_sha")!=source or
            w.get("original_pid")!=original_pid or
            w.get("actual_fakeip_peer")!=fake or
            w.get("actual_client_lease")!="10.66.0.2" or
            g.get("physical_client_source")!=host_source or
            not (w.get("one_persistent_socket") and w.get("windows_half_close") and
                 g.get("half_close")) or
            set(phases)!={"upload","download"} or
            g.get("received_upload_bytes")!=MEASURE_BYTES or
            g.get("sent_download_bytes")!=MEASURE_BYTES):
            raise RuntimeError("H1896 actual source-locked TCP stages not both delivered")
        for name in ("upload","download"):
            ph=phases[name]
            if (ph["delivered_bytes"]!=MEASURE_BYTES or
                ph["receiver_sha256"]!=expected_sha(MEASURE_BYTES) or
                ph["cpu"]["cpu_scope"]!=
                "WIN32_ORIGINAL_GO_PLUS_RUST_PROCESS_WITH_TUNNEL_UDP_NO_DRIVER_ISR_DPC"):
                raise RuntimeError("H1896 stage bytes, SHA, real original CPU invalid")
        if g["received_upload_sha256"]!=phases["upload"]["receiver_sha256"]:
            raise RuntimeError("H1896 Linux physical upload and Windows proof mismatch")
        if g["sent_download_sha256"]!=phases["download"]["receiver_sha256"]:
            raise RuntimeError("H1896 Linux physical download and Windows proof mismatch")
        return {"source_sha":source,"status":"PENDING_UDP_AND_OWNED_STOP",
                "scope":"REAL_WINDOWS_FAKEIP_TO_WSL2_PHYSICAL_TCP_30S_EACH_DIRECTION",
                "baseline_original_process_cpu":background,
                "windows":w,"linux":g,"owner_stop":"NOT_RUN",
                "cpu_attribution":"ORIGINAL_PROCESS_WITH_TUNNEL_UDP_NOT_DRIVER_OR_PER_FLOW_CPU"}
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:child.kill()

if __name__=="__main__":
    if len(sys.argv)==5 and sys.argv[1]=="guest":
        guest(sys.argv[2],sys.argv[3],sys.argv[4])
    elif len(sys.argv)==8 and sys.argv[1]=="windows":
        windows(sys.argv[2],sys.argv[3],sys.argv[4],int(sys.argv[5]),
                sys.argv[6],sys.argv[7])
    else:
        raise SystemExit("H1896 only signed guest or Windows source-pinned roles")
