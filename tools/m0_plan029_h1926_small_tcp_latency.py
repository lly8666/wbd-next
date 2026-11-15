#!/usr/bin/env python3
"""H1926: source-locked Windows/WSL2 real TCP small-request A-B-B-A latency.

Same original owner, genuine Linux kernel listener on the existing owned
46112 grant. All samples are application-level phases, NEVER one-way
network latency or isolated splitter-only CPU. No product runtime code.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import statistics
import struct
import subprocess
import sys
import time

PORT=46112
SIZES=(64,1024,16384)
REPEATS=32
ORDER=("physical","direct","direct","physical")
MARK="PLAN029_H1926_SMALL_TCP_WINDOWS"
GUEST_MARK="PLAN029_H1926_SMALL_TCP_LINUX"
READY="PLAN029_H1926_LINUX_TCP_READY"
SOURCE=os.environ.get("GITHUB_SHA","")
TOTAL=REPEATS*len(SIZES)*len(ORDER)


def payload(seq,size):
    prefix=(b"PLAN029-H1926-REAL-KERNEL-TCP/"+
            seq.to_bytes(4,"big"))
    return (prefix*((size+len(prefix)-1)//len(prefix)))[:size]


def scenario():
    seq=0
    for repeat in range(REPEATS):
        for size in SIZES:
            for path in ORDER:
                yield seq,path,size
                seq+=1


def read_exact(sock,count):
    data=bytearray()
    while len(data)<count:
        chunk=sock.recv(min(16384,count-len(data)))
        if not chunk:
            raise RuntimeError("H1926 early TCP EOF instead of complete echo")
        data.extend(chunk)
    return bytes(data)


def emit(mark,data):
    print(mark+" "+json.dumps(data,sort_keys=True,separators=(",",":")),
          flush=True)


def send_guest_echo(conn,data,reply_policy):
    if reply_policy not in ("fin_first","payload_first"):
        raise RuntimeError("H1942 invalid original source-locked echo policy")
    if reply_policy=="payload_first":
        conn.sendall(data)
        conn.shutdown(socket.SHUT_WR)
    # Both policies MUST still receive the real Linux kernel TCP FIN.
    if conn.recv(1)!=b"":
        raise RuntimeError("H1942 Linux original TCP FIN missing")
    if reply_policy=="fin_first":
        conn.sendall(data)
        conn.shutdown(socket.SHUT_WR)


def guest(physical,host_source,expected_source,reply_policy="fin_first"):
    if not expected_source or len(expected_source)!=40:
        raise RuntimeError("H1926 real Linux SOURCE absent")
    dig=hashlib.sha256()
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((physical,PORT))
        listener.listen(32)
        listener.settimeout(50)
        print(READY,flush=True)
        for seq,_role,size in scenario():
            conn,peer=listener.accept()
            if peer[0]!=host_source:
                raise RuntimeError("H1926 Linux did not observe physical underlay source")
            with conn:
                conn.settimeout(20)
                header=read_exact(conn,8)
                received_seq,received_size=struct.unpack("!II",header)
                if (received_seq,received_size)!=(seq,size):
                    raise RuntimeError("H1926 Linux connection order/size mismatch")
                data=read_exact(conn,size)
                if data!=payload(seq,size):
                    raise RuntimeError("H1926 Linux source-locked TCP bytes mismatch")
                dig.update(data)
                send_guest_echo(conn,data,reply_policy)
    emit(GUEST_MARK,{"source_sha":expected_source,
        "received_connections":TOTAL,"real_kernel_tcp":True,
        "underlay_source":host_source,"port":PORT,
        "sha256_all_received":dig.hexdigest(),"reply_policy":reply_policy})


def percentile(values,pct):
    items=sorted(values)
    return round(items[min(len(items)-1,math.ceil(len(items)*pct)-1)],3)


def distribution(values):
    return {"n":len(values),
            "min_ms":round(min(values),3),
            "p50_ms":round(statistics.median(values),3),
            "p95_ms":percentile(values,.95),
            "p99_ms":percentile(values,.99),
            "max_ms":round(max(values),3)}


def windows(physical,host_source,fake,expected_source,reply_policy="fin_first"):
    if not expected_source or SOURCE!=expected_source:
        raise RuntimeError("H1926 Windows original SOURCE SHA mismatch")
    if not fake.startswith("198.18."):
        raise RuntimeError("H1926 requires announced CN FakeIP, no proxy")
    if reply_policy not in ("fin_first","payload_first"):
        raise RuntimeError("H1942 unknown original echo policy")
    records={str(size):{"physical":[],"direct":[]} for size in SIZES}
    dig=hashlib.sha256()
    begin=time.perf_counter()
    for seq,role,size in scenario():
        ip=host_source if role=="physical" else "10.66.0.2"
        target=physical if role=="physical" else fake
        data=payload(seq,size)
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
            sock.settimeout(20)
            sock.bind((ip,0))
            start=time.perf_counter_ns()
            sock.connect((target,PORT))
            connected=time.perf_counter_ns()
            if sock.getsockname()[0]!=ip:
                raise RuntimeError("H1926 Windows true source changed")
            # Keep application's TCP_NODELAY unchanged for both paths.
            app_nodelay=sock.getsockopt(socket.IPPROTO_TCP,
                                        socket.TCP_NODELAY)
            sock.sendall(struct.pack("!II",seq,size)+data)
            sent=time.perf_counter_ns()
            sock.shutdown(socket.SHUT_WR)
            half=time.perf_counter_ns()
            first=sock.recv(min(16384,size))
            first_at=time.perf_counter_ns()
            if not first:
                raise RuntimeError("H1926 no first echo byte")
            echoed=first+read_exact(sock,size-len(first))
            full=time.perf_counter_ns()
            if echoed!=data or sock.recv(1)!=b"":
                raise RuntimeError("H1926 Windows echo content or TCP FIN missing")
            finished=time.perf_counter_ns()
        dig.update(data)
        ms=lambda a,b: (b-a)/1e6
        records[str(size)][role].append({
            "connect":ms(start,connected),
            "upload":ms(connected,sent),
            "half_close":ms(sent,half),
            "first_echo_after_half_close":ms(half,first_at),
            "download_after_first":ms(first_at,full),
            "fin_after_full":ms(full,finished),
            "total":ms(start,finished),
            "app_nodelay":int(app_nodelay),
        })
    summary={}
    phases=("connect","upload","half_close","first_echo_after_half_close",
            "download_after_first","fin_after_full","total")
    for size in SIZES:
        by=records[str(size)]
        for role in ORDER:
            if len(by[role])!=2*REPEATS:
                raise RuntimeError("H1926 missing one signed path's TCP samples")
        phys=by["physical"];direct=by["direct"]
        if {x["app_nodelay"] for x in phys}!={0} or (
                {x["app_nodelay"] for x in direct}!={0}):
            raise RuntimeError("H1926 comparison changed application socket options")
        summary[str(size)]={}
        for role,series in (("physical",phys),("direct",direct)):
            summary[str(size)][role]={
                phase:distribution([x[phase] for x in series])
                for phase in phases}
        summary[str(size)]["direct_minus_physical_ms"]={
            phase:{"p50_delta":round(
                summary[str(size)]["direct"][phase]["p50_ms"]-
                summary[str(size)]["physical"][phase]["p50_ms"],3),
                "p99_delta":round(
                summary[str(size)]["direct"][phase]["p99_ms"]-
                summary[str(size)]["physical"][phase]["p99_ms"],3)}
            for phase in phases}
    elapsed=round(time.perf_counter()-begin,4)
    emit(MARK,{"source_sha":SOURCE,"reply_policy":reply_policy,
        "physical_underlay":host_source,
        "wintun_lease":"10.66.0.2","fakeip":fake,
        "order":list(ORDER),"sizes":list(SIZES),
        "repetitions_per_path_per_size":REPEATS*2,
        "total_connections":TOTAL,"payload_sha256":dig.hexdigest(),
        "elapsed_s":elapsed,"same_vm_original_process":True,
        "no_cross_os_oneway_clock_claim":True,
        "no_cpu_causality_claim":True,"stats":summary,
        "scope":"TRUE_SAME_VM_NATIVE_WINDOWS_PHYSICAL_VS_WINTUN_FAKEIP_SMALL_TCP"})


def proof(path,marker):
    lines=[line.split(marker+" ",1)[1] for line in
           Path(path).read_text(encoding="utf-8").splitlines()
           if line.startswith(marker+" ")]
    if len(lines)!=1:
        raise RuntimeError("H1926 exact receipt absent "+str(path))
    return json.loads(lines[0])


def run_small_tcp_latency(root,out,physical,host_source,fake,unix,ready):
    if not (os.environ.get("GITHUB_ACTIONS")=="true" and
            os.environ.get("WBD_PLAN029_P2_SMALL_TCP_SCENE")=="1" and
            os.environ.get("WBD_PLAN029_P2_BULK_SCENE")=="1" and
            os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")=="1"):
        raise RuntimeError("H1926 only original source-locked signed P2")
    source=os.environ["GITHUB_SHA"]
    script=Path(root)/"tools"/"m0_plan029_h1926_small_tcp_latency.py"
    glog=Path(out)/"plan029-h1926-latency-linux.log"
    wlog=Path(out)/"plan029-h1926-latency-windows.log"
    children=[]
    try:
        with glog.open("w") as gf:
            guest_args=["wsl.exe","-d","Ubuntu","-u","root","--",
                "python3","-u",unix(script),"guest",physical,host_source,source]
            guest_proc=subprocess.Popen(guest_args,stdout=gf,
                       stderr=subprocess.STDOUT)
            children.append(guest_proc)
            ready(glog,READY,guest_proc,12)
            with wlog.open("w") as wf:
                win_proc=subprocess.Popen([sys.executable,"-u",str(script),
                    "windows",physical,host_source,fake,source],
                    stdout=wf,stderr=subprocess.STDOUT)
                children.append(win_proc)
                if win_proc.wait(timeout=95)!=0:
                    raise RuntimeError("H1926 real Windows small TCP failed "+
                                       wlog.read_text(errors="replace")[-1700:])
            if guest_proc.wait(timeout=15)!=0:
                raise RuntimeError("H1926 Linux small TCP failed "+
                                   glog.read_text(errors="replace")[-1700:])
        w=proof(wlog,MARK);g=proof(glog,GUEST_MARK)
        if (w["source_sha"]!=source or g["source_sha"]!=source or
            w["total_connections"]!=TOTAL or g["received_connections"]!=TOTAL or
            w["payload_sha256"]!=g["sha256_all_received"] or
            g["underlay_source"]!=host_source or
            w["wintun_lease"]!="10.66.0.2" or
            w["fakeip"]!=fake or
            w["physical_underlay"]!=host_source or
            w["order"]!=list(ORDER) or w["sizes"]!=list(SIZES) or
            w["repetitions_per_path_per_size"]!=2*REPEATS):
            raise RuntimeError("H1926 real original two-OS A-B-B-A SHA/count/source failed")
        for size in SIZES:
            for role in ("physical","direct"):
                for phase in ("connect","first_echo_after_half_close","total"):
                    item=w["stats"][str(size)][role][phase]
                    if item["n"]!=2*REPEATS or not (
                        0<=item["p50_ms"]<=item["p99_ms"]<=item["max_ms"]):
                        raise RuntimeError("H1926 invalid measured TCP phase tail")
        echo_control=None
        if os.environ.get("WBD_PLAN029_P2_ECHO_EARLY_CONTROL")=="1":
            # SAME native Windows owner, exact second Linux kernel
            # listener port and 384 application sockets. The legacy
            # FIN-first proof above is unchanged, and both still own FIN.
            log_g=Path(out)/"plan029-h1942-echo-first-guest.log"
            log_w=Path(out)/"plan029-h1942-echo-first-windows.log"
            with log_g.open("w") as gp:
                guest2=subprocess.Popen(
                    ["wsl.exe","-d","Ubuntu","-u","root","--",
                     "python3","-u",unix(script),"guest",
                     physical,host_source,source,"payload_first"],
                    stdout=gp,stderr=subprocess.STDOUT)
                children.append(guest2)
                ready(log_g,READY,guest2,12)
                with log_w.open("w") as wp:
                    client2=subprocess.Popen(
                        [sys.executable,"-u",str(script),"windows",
                         physical,host_source,fake,source,"payload_first"],
                        stdout=wp,stderr=subprocess.STDOUT)
                    children.append(client2)
                    if client2.wait(timeout=95)!=0:
                        raise RuntimeError("H1942 true Windows echo-first failed "+
                                           log_w.read_text(errors="replace")[-1500:])
                if guest2.wait(timeout=15)!=0:
                    raise RuntimeError("H1942 true Linux echo-first failed "+
                                       log_g.read_text(errors="replace")[-1500:])
            e_win=proof(log_w,MARK)
            e_linux=proof(log_g,GUEST_MARK)
            if (w["reply_policy"]!="fin_first" or
                g["reply_policy"]!="fin_first" or
                e_win["reply_policy"]!="payload_first" or
                e_linux["reply_policy"]!="payload_first" or
                e_win["source_sha"]!=source or e_linux["source_sha"]!=source or
                e_win["total_connections"]!=TOTAL or
                e_linux["received_connections"]!=TOTAL or
                e_win["payload_sha256"]!=e_linux["sha256_all_received"] or
                e_win["payload_sha256"]!=w["payload_sha256"] or
                e_win["order"]!=list(ORDER) or e_win["sizes"]!=list(SIZES) or
                e_win["repetitions_per_path_per_size"]!=2*REPEATS or
                e_win["fakeip"]!=fake or
                e_win["wintun_lease"]!="10.66.0.2" or
                e_win["physical_underlay"]!=host_source or
                e_linux["underlay_source"]!=host_source):
                raise RuntimeError("H1942 true two-OS 384+384 source/SHA/FIN failure")
            for size in SIZES:
                for path in ("physical","direct"):
                    for phase in ("connect","first_echo_after_half_close","total"):
                        item=e_win["stats"][str(size)][path][phase]
                        if item["n"]!=2*REPEATS or not (
                            0<=item["p50_ms"]<=item["p99_ms"]<=item["max_ms"]):
                            raise RuntimeError("H1942 invalid echo-first tail receipt")
            echo_control={
                "source_sha":source,
                "status":"PASS_SCOPED_ORIGINAL_TWO_OS_ECHO_BEFORE_FIN",
                "windows":e_win,"linux":e_linux,
                "limitations":"sequential application-protocol intervention; no old/new product CPU claim"}
        return {"source_sha":source,
                "status":"PASS_SCOPED_SMALL_TCP_A_B_B_A_SHA_FIN",
                "windows":w,"linux":g,
                "echo_before_fin_control":echo_control,
                "original_go_rust_owner":"SAME_AS_4M_P2",
                "tunnel_udp":"SAME_P2_LIFETIME_BOUNDARY",
                "owned_stop":"PENDING_ORIGINAL_OWNER_STOP"}
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill()


if __name__=="__main__":
    if len(sys.argv) in (5,6) and sys.argv[1]=="guest":
        guest(*sys.argv[2:])
    elif len(sys.argv) in (6,7) and sys.argv[1]=="windows":
        windows(*sys.argv[2:])
    else:
        raise SystemExit("H1926 only exact Linux guest / Windows original roles")
