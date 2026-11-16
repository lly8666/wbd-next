#!/usr/bin/env python3
"""H1966 signed original Windows/WSL2 steady TCP echo, NOT a new packet pump.

One existing kernel TCP stream per arm, 32 warmup + 2048 x 1024-byte
stop-and-wait echoes. No FIN-first latency, preconnect, extra listener on
Windows or Linux/Windows cross-clock subtraction.
"""
import ctypes
import hashlib
import json
import math
import os
import pathlib
import socket
import subprocess
import sys

PORT=46119
WARMUP=32
COUNT=2048
SIZE=1024
MAGIC=b"P029STDY"
MARK="PLAN029_H1966_REAL_STEADY_TCP"

def payload(index):
    return index.to_bytes(4,"big")+MAGIC+bytes([index%251])*(SIZE-12)

def recv_exact(conn,amount):
    chunks=[]
    while amount:
        b=conn.recv(amount)
        if not b:raise RuntimeError("H1966 early kernel TCP EOF")
        chunks.append(b);amount-=len(b)
    return b"".join(chunks)

def qpc():
    if os.name!="nt":raise RuntimeError("H1966 QPC only on Windows")
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    freq=ctypes.c_longlong()
    if not k.QueryPerformanceFrequency(ctypes.byref(freq)) or freq.value<=0:
        raise RuntimeError("Windows QueryPerformanceFrequency unavailable")
    def tick():
        x=ctypes.c_longlong()
        if not k.QueryPerformanceCounter(ctypes.byref(x)) or x.value<=0:
            raise RuntimeError("Windows QueryPerformanceCounter unavailable")
        return x.value
    return freq.value,tick

def quant(values):
    x=sorted(values)
    def at(p):return round(x[max(0,math.ceil(len(x)*p)-1)],3)
    return dict(n=len(x),p50_ms=at(.5),p95_ms=at(.95),
                p99_ms=at(.99),max_ms=at(1))

def guest(physical,expected,source):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((physical,PORT));listener.listen(2);listener.settimeout(145)
        print("PLAN029_H1966_LINUX_STEADY_READY",flush=True)
        receipts=[]
        for arm in ("physical","direct"):
            conn,peer=listener.accept()
            if peer[0]!=expected:raise RuntimeError("Linux real physical source differs")
            with conn:
                conn.settimeout(125)
                h=hashlib.sha256()
                for i in range(WARMUP+COUNT):
                    msg=recv_exact(conn,SIZE)
                    if msg!=payload(i):raise RuntimeError("H1966 Linux TCP stream ID/bytes changed")
                    h.update(msg)
                    conn.sendall(msg)
                if conn.recv(1)!=b"":raise RuntimeError("H1966 Linux missing owned FIN")
                conn.shutdown(socket.SHUT_WR)
            receipts.append(dict(arm=arm,bytes=(WARMUP+COUNT)*SIZE,
                                 sha256=h.hexdigest(),physical_source=peer[0]))
        print("PLAN029_H1966_REAL_LINUX_STEADY "+json.dumps(
            dict(source=source,receipts=receipts,kernel_tcp=True),sort_keys=True),flush=True)

def client(role,local,remote,source,destination):
    if role not in ("physical","direct"):raise RuntimeError("unsupported role")
    if role=="direct" and (local!="10.66.0.2" or not remote.startswith("198.18.")):
        raise RuntimeError("not original Windows Wintun FakeIP path")
    freq,tick=qpc()
    samples=[]
    h=hashlib.sha256()
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as conn:
        conn.settimeout(125);conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        conn.bind((local,0));conn.connect((remote,PORT))
        source_port=conn.getsockname()[1]
        for i in range(WARMUP+COUNT):
            msg=payload(i)
            a=tick()
            conn.sendall(msg)
            b=tick()
            echo=recv_exact(conn,SIZE)
            c=tick()
            if echo!=msg:raise RuntimeError("H1966 original WinSock echoed bytes differ")
            h.update(msg)
            if i>=WARMUP:samples.append([a,b,c])
        conn.shutdown(socket.SHUT_WR)
        if conn.recv(1)!=b"":raise RuntimeError("H1966 original WinSock missing FIN")
    if len(samples)!=COUNT:raise RuntimeError("H1966 sample count wrong")
    delta=[(c-a)*1000/freq for a,b,c in samples]
    result=dict(source=source,role=role,source_ip=local,source_port=source_port,
        presented_peer=remote,physical_target=destination,
        qpc_frequency=freq,app_qpc=samples,
        rtt=quant(delta),sha256=h.hexdigest(),
        exact_bytes=(WARMUP+COUNT)*SIZE,warmup=WARMUP,measured=COUNT,
        kernel_tcp=True,half_close=True,nodelay=1)
    output=pathlib.Path(os.environ["WBD_PLAN029_H1966_RESULT_FILE"])
    output.write_text(json.dumps(result,separators=(",",":"))+"\n",encoding="utf-8")
    print(MARK+" "+json.dumps({k:v for k,v in result.items() if k!="app_qpc"},
                              sort_keys=True),flush=True)

def run_steady(root,out,physical,host_source,fake,unix,ready):
    if (os.environ.get("GITHUB_ACTIONS")!="true" or
        os.environ.get("WBD_PLAN029_NATIVE_V3_TRIAL")!="1" or
        os.environ.get("WBD_PLAN029_P2_MIXED_SCENE")!="1" or
        os.environ.get("WBD_PLAN029_P2_STEADY_QPC_SCENE")!="1"):
        raise RuntimeError("H1966 unsigned original owner refused")
    source=os.environ["GITHUB_SHA"]
    exe=root/"tools"/"m0_plan029_h1966_steady_tcp_qpc.py"
    guest_log=out/"plan029-h1966-linux-steady.log"
    with guest_log.open("w") as f:
        guest=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
                                "python3","-u",unix(exe),"guest",physical,host_source,source],
                               stdout=f,stderr=subprocess.STDOUT)
        try:
            ready(guest_log,"PLAN029_H1966_LINUX_STEADY_READY",guest,12)
            arms=[]
            for role,local,remote in (("physical",host_source,physical),
                                      ("direct","10.66.0.2",fake)):
                path=out/("plan029-h1966-app-"+role+".json")
                logfile=out/("plan029-h1966-"+role+".log")
                env=os.environ.copy()
                env["WBD_PLAN029_H1966_RESULT_FILE"]=str(path)
                with logfile.open("w") as fd:
                    p=subprocess.Popen([sys.executable,"-u",str(exe),"client",
                        role,local,remote,source,physical],stdout=fd,
                        stderr=subprocess.STDOUT,env=env)
                    try:rc=p.wait(timeout=135)
                    except subprocess.TimeoutExpired:
                        p.kill();p.wait()
                        raise RuntimeError("H1966 Windows steady TCP timeout "+role)
                if rc!=0:raise RuntimeError("H1966 Windows app failure "+
                    role+" "+logfile.read_text(errors="replace")[-500:])
                val=json.loads(path.read_text(encoding="utf-8"))
                if not (val["source"]==source and val["role"]==role and
                    val["measured"]==COUNT and len(val["app_qpc"])==COUNT and
                    val["exact_bytes"]==(WARMUP+COUNT)*SIZE and
                    val["source_ip"]==local):
                    raise RuntimeError("H1966 wrong source/bytes/QPC app "+role)
                arms.append(val)
            try:guest_rc=guest.wait(timeout=15)
            except subprocess.TimeoutExpired:
                guest.kill();guest.wait()
                raise RuntimeError("H1966 Linux guest missing kernel receipt")
            if guest_rc!=0:raise RuntimeError("H1966 Linux guest failed "+
                guest_log.read_text(errors="replace")[-850:])
            lines=[line.split(" ",1)[1] for line in guest_log.read_text().splitlines()
                   if line.startswith("PLAN029_H1966_REAL_LINUX_STEADY ")]
            if len(lines)!=1:raise RuntimeError("H1966 exactly one Linux receipt required")
            proof=json.loads(lines[0])
            if proof["source"]!=source or len(proof["receipts"])!=2:
                raise RuntimeError("H1966 Linux wrong source or counts")
            for a,l in zip(arms,proof["receipts"]):
                if a["role"]!=l["arm"] or a["sha256"]!=l["sha256"] or
                   a["exact_bytes"]!=l["bytes"] or l["physical_source"]!=host_source:
                    raise RuntimeError("H1966 original two-OS byte/sha/physical path mismatch")
            return dict(source_sha=source,physical=arms[0],direct=arms[1],
                        linux=proof,stop="PENDING_ORIGINAL_OWNED_STOP",
                        scope="ORIGINAL_SAME_WINDOWS_WIN32_QPC_APPS_AND_TWO_LINUX_KERNEL_TCP_STREAMS")
        finally:
            if guest.poll() is None:
                guest.terminate()
                try:guest.wait(timeout=4)
                except subprocess.TimeoutExpired:guest.kill()

if __name__=="__main__":
    if len(sys.argv)!=5 and len(sys.argv)!=7:raise SystemExit("H1966 role argv")
    if sys.argv[1]=="guest" and len(sys.argv)==5:
        guest(*sys.argv[2:5])
    elif sys.argv[1]=="client" and len(sys.argv)==7:
        client(*sys.argv[2:7])
    else:raise SystemExit("invalid H1966 role")
