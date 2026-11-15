#!/usr/bin/env python3
"""PLAN029 H1892: 128 ORIGINAL Wintun Direct TCP idle sockets, 2 live in one shard.

Two real OS applications (Windows lease -> signed Wintun -> Rust listener +
physical-source TCP -> Linux WSL2 eth0), not synthetic L3 packets or mock ACKs.
One event loop per test application, NO thread or socket added to the product.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time

N=128
PORT=46112  # reuse the already-owned exact signed Hyper-V TCP46112 grant
SRC_BASE=42500
ACTIVE=(15,31)  # 16 NAT proxy ports apart, verified from ORIGINAL Rust logs
SIZE=65536
MARKER="PLAN029_H1892_TCP128"
TAG=b"PLAN029-H1892/"

def emit(tag,data):
    print(tag+" "+json.dumps(data,sort_keys=True,separators=(",",":")),flush=True)

def payload(index):
    start=TAG+index.to_bytes(2,"big")
    return (start*((SIZE+len(start)-1)//len(start)))[:SIZE]

def proof(path,marker):
    entries=[line.split(" ",1)[1] for line in Path(path).read_text(
        encoding="utf-8",errors="replace").splitlines()
        if line.startswith(marker+" ")]
    if len(entries)!=1:
        raise RuntimeError("H1892 missing/duplicate genuine OS receipt "+marker)
    return json.loads(entries[0])

def guest(physical,host_source,source):
    held=[];listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    try:
        listener.bind((physical,PORT))
        listener.listen(256)
        listener.settimeout(32)
        print("PLAN029_H1892_LINUX_TCP128_LISTEN_READY",flush=True)
        remote_sources=[]
        deadline=time.monotonic()+40
        for i in range(N):
            listener.settimeout(max(.2,deadline-time.monotonic()))
            conn,peer=listener.accept()
            if peer[0]!=host_source:
                conn.close()
                raise RuntimeError("H1892 not original Windows physical-bound source")
            conn.setblocking(False)
            held.append(conn)
            remote_sources.append(peer[0])
        print("PLAN029_H1892_LINUX_ALL128_KERNEL_ACCEPTED",flush=True)
        buffers={conn:bytearray() for conn in held}
        active_seen={}
        remaining=set(held)
        deadline=time.monotonic()+18
        while len(active_seen)<len(ACTIVE):
            wait=max(0.,deadline-time.monotonic())
            if wait<=0:raise RuntimeError("H1892 two real active TCP streams starved")
            readable,_,_=select.select(list(remaining),[],[],min(wait,2.))
            for conn in readable:
                data=conn.recv(32768)
                if data:
                    buf=buffers[conn]
                    buf.extend(data)
                    if len(buf)>SIZE:
                        raise RuntimeError("H1892 illegal idle socket payload or overflow")
                else:
                    buf=bytes(buffers[conn])
                    if len(buf)!=SIZE or not buf.startswith(TAG):
                        raise RuntimeError("H1892 idle TCP prematurely closed or truncated")
                    index=int.from_bytes(buf[len(TAG):len(TAG)+2],"big")
                    if index not in ACTIVE or index in active_seen or buf!=payload(index):
                        raise RuntimeError("H1892 wrong two active OS TCP payloads")
                    conn.settimeout(6)
                    conn.sendall(buf)
                    conn.shutdown(socket.SHUT_WR)
                    remaining.remove(conn)
                    active_seen[index]=len(buf)
        emit("PLAN029_H1892_LINUX_TCP128_RECEIPT",{
            "source_sha":source,"kernel_tcp":True,
            "physical_guest":physical,"windows_physical_source":host_source,
            "accepted":len(held),"unique_physical_sources":len(set(remote_sources)),
            "idle_connections":N-len(ACTIVE),
            "active_indices":list(ACTIVE),
            "active_received_bytes":[active_seen[i] for i in ACTIVE],
            "active_sha256":[hashlib.sha256(payload(i)).hexdigest() for i in ACTIVE],
            "server_threads_for_flows":0,
        })
    finally:
        for sock in held:
            try:sock.close()
            except OSError:pass
        listener.close()

def windows(lease,fake,source):
    held=[]
    began=time.monotonic()
    try:
        for index in range(N):
            conn=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            conn.settimeout(6)
            try:
                conn.bind((lease,SRC_BASE+index))
                conn.connect((fake,PORT))
                if conn.getsockname()!=(lease,SRC_BASE+index):
                    raise RuntimeError("H1892 original Wintun source bind mutated")
                held.append(conn)
            except BaseException:
                conn.close()
                raise
            if time.monotonic()-began>35:
                raise RuntimeError("H1892 cannot establish 128 genuine TCP sockets in 35s")
        connected=time.monotonic()
        # Eight full seconds and no payload on 126 idle sockets: 1Hz
        # GetProcessTimes/Toolhelp timestamps must fall INSIDE this window.
        idle_start=time.monotonic()
        time.sleep(8)
        idle_end=time.monotonic()
        premature,_,_=select.select(held,[],[],0)
        if premature:
            raise RuntimeError("H1892 original Wintun idle socket unexpectedly signaled EOF/data")
        active_start=time.monotonic()
        for index in ACTIVE:
            sock=held[index]
            sock.sendall(payload(index))
            sock.shutdown(socket.SHUT_WR)
            sock.setblocking(False)
        buffers={i:bytearray() for i in ACTIVE}
        finished=set()
        deadline=time.monotonic()+15
        while len(finished)<len(ACTIVE):
            if time.monotonic()>=deadline:
                raise RuntimeError("H1892 same-shard two-activity starvation")
            chosen=[held[i] for i in ACTIVE if i not in finished]
            readable,_,_=select.select(chosen,[],[],min(1.,deadline-time.monotonic()))
            for sock in readable:
                index=ACTIVE[[held[i] for i in ACTIVE].index(sock)]
                data=sock.recv(32768)
                if data:
                    buffers[index].extend(data)
                    if len(buffers[index])>SIZE:
                        raise RuntimeError("H1892 extra TCP return data")
                else:
                    if bytes(buffers[index])!=payload(index):
                        raise RuntimeError("H1892 original Wintun same-shard echo SHA/FIN invalid")
                    finished.add(index)
        ended=time.monotonic()
        emit("PLAN029_H1892_WINDOWS_TCP128_RECEIPT",{
            "source_sha":source,"source_lease":lease,"fakeip":fake,"kernel_tcp":True,
            "connections":len(held),"held_idle_during_active":N-len(ACTIVE),
            "source_ports":[SRC_BASE+i for i in range(N)],
            "active_indices":list(ACTIVE),
            "active_source_ports":[SRC_BASE+i for i in ACTIVE],
            "active_sent_bytes":[SIZE]*len(ACTIVE),
            "active_echo_bytes":[len(buffers[i]) for i in ACTIVE],
            "active_sha256":[hashlib.sha256(payload(i)).hexdigest() for i in ACTIVE],
            "fin":True,"start_monotonic_s":began,
            "connected_monotonic_s":connected,
            "idle_start_monotonic_s":idle_start,
            "idle_end_monotonic_s":idle_end,
            "active_start_monotonic_s":active_start,
            "end_monotonic_s":ended,
            "single_app_thread_select":True
        })
    finally:
        for sock in held:
            try:sock.close()
            except OSError:pass

def parse_rust_128(client_log):
    """Fail closed: actual 128 SYN->NAT->kernel ACCEPT logs, not fixture labels."""
    prefix="PLAN029_H1892_WINTUN_TCP_ADMITTED "
    rows=[]
    for line in client_log.splitlines():
        if prefix not in line:continue
        pairs={}
        for item in line.split(prefix,1)[1].split():
            if "=" in item:
                name,value=item.split("=",1)
                if name in pairs:raise RuntimeError("H1892 duplicate original Rust admission key")
                pairs[name]=value
        if pairs.get("source")!="real_wintun_direct":
            raise RuntimeError("H1892 non-original Rust admission scope")
        for field in ("source_port","proxy_port","shard"):
            if not pairs.get(field,"").isascii() or not pairs.get(field,"").isdecimal():
                raise RuntimeError("H1892 missing numeric original Rust admission")
        row={k:int(pairs[k]) for k in ("source_port","proxy_port","shard")}
        if row["shard"]!=row["proxy_port"]%16:
            raise RuntimeError("H1892 Rust socket shard does not match NAT port")
        rows.append(row)
    if len(rows)!=N or {x["source_port"] for x in rows}!=set(
            range(SRC_BASE,SRC_BASE+N)) or len({x["proxy_port"] for x in rows})!=N:
        raise RuntimeError("H1892 missing one of 128 ORIGINAL Wintun accepted connections")
    by_port={x["source_port"]:x for x in rows}
    active=[by_port[SRC_BASE+i] for i in ACTIVE]
    if active[0]["shard"]!=active[1]["shard"] or (
            abs(active[0]["proxy_port"]-active[1]["proxy_port"])%16)!=0:
        raise RuntimeError("H1892 TWO active Wintun sockets not actually on same WinSock shard")
    suffix="PLAN029_H1892_TCP128_FINAL "
    finals=[line.split(suffix,1)[1] for line in client_log.splitlines()
            if suffix in line]
    if len(finals)!=1:
        raise RuntimeError("H1892 original Rust final 128 pressure counters missing")
    parts=dict(item.split("=",1) for item in finals[0].split() if "=" in item)
    if parts.get("source")!="real_wintun_direct":
        raise RuntimeError("H1892 false final kernel TCP origin")
    for k in ("admitted","active_peak","max_same_shard"):
        if not parts.get(k,"").isascii() or not parts[k].isdecimal():
            raise RuntimeError("H1892 invalid Rust final 128 counters")
    if int(parts["admitted"])!=N or int(parts["active_peak"])<N or int(
            parts["max_same_shard"])<2:
        raise RuntimeError("H1892 128 actual concurrent original Rust TCP connections NOT proved")
    return {
        "status":"ORIGINAL_RUST_TRUE_NAT_AND_KERNEL_128_ACCEPT_PASS",
        "admitted":N,"active_peak":int(parts["active_peak"]),
        "max_same_shard":int(parts["max_same_shard"]),
        "active_shared_shard":active[0]["shard"],
        "active_source_ports":[x["source_port"] for x in active],
        "no_per_flow_threads":"SINGLE_RUST_TX_EXISTING_16_SHARDS",
        "all_128_source_ports_verified":True
    }

def idle_cpu_window(path,begin,end,phase="tcp128"):
    """Same original process Win32 GetProcessTimes within a bounded phase.
    Pre-128 baseline is a post-P2 interval with no newly admitted
    TCP128 probe sockets; earlier FIN-grace metadata may still exist.
    """
    if phase not in ("tcp128","pre128"):
        raise RuntimeError("H1894 unknown original signed CPU phase")
    rows=[]
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():continue
        item=json.loads(line)
        t=item.get("monotonic_s")
        if (isinstance(t,(int,float)) and begin<=t<=end and
            item.get("scope")=="SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"):
            rows.append(item)
    if len(rows)<3 or len({r.get("native_pid") for r in rows})!=1:
        raise RuntimeError("H1892 original Windows idle 1Hz CPU process samples missing")
    rows.sort(key=lambda r:r["monotonic_s"])
    first,last=rows[0],rows[-1]
    elapsed=last["monotonic_s"]-first["monotonic_s"]
    if elapsed<2:raise RuntimeError("H1892 idle CPU samples span less than 2s")
    deltas={}
    for field in ("cpu_user_s","cpu_kernel_s","cpu_total_s"):
        v=last[field]-first[field]
        if v<0:raise RuntimeError("H1892 process CPU time not monotonic")
        deltas[field]=round(v,6)
    if abs(deltas["cpu_total_s"]-deltas["cpu_user_s"]-
           deltas["cpu_kernel_s"])>.004:
        raise RuntimeError("H1892 process kernel/user CPU sum invalid")
    return {
        "scope":("SAME_REAL_WINDOWS_PROCESS_GO_PLUS_RUST_IDLE_128_TCP" if
                 phase=="tcp128" else
                 "SAME_REAL_WINDOWS_PROCESS_GO_PLUS_RUST_PRE128_IDLE_CONTROL"),
        "native_pid":first["native_pid"],
        "observations":len(rows),"measured_elapsed_s":round(elapsed,3),
        "process_kernel_cpu_s":deltas["cpu_kernel_s"],
        "process_user_cpu_s":deltas["cpu_user_s"],
        "process_total_cpu_s":deltas["cpu_total_s"],
        "percent_one_logical_core":round(100*deltas["cpu_total_s"]/elapsed,3),
        "peak_private_bytes":max(r.get("private_bytes",0) for r in rows),
        "peak_working_set_bytes":max(r.get("working_set_bytes",0) for r in rows),
        "min_threads_sampled":min(
            (r.get("thread_cpu") or {}).get("thread_count_sampled",0) for r in rows),
        "max_threads_sampled":max(
            (r.get("thread_cpu") or {}).get("thread_count_sampled",0) for r in rows),
        "interpretation":"Original Go+Rust process CPU only; driver ISR/DPC, VM and per-function CPU NOT measured."
    }

def compare_original_cpu_idle(control,full):
    """Same Windows original process and owner, 1Hz CPU-s/second.
    Measures phase difference; neither a randomized causal A/B nor driver CPU.
    """
    if (control.get("scope")!=
        "SAME_REAL_WINDOWS_PROCESS_GO_PLUS_RUST_PRE128_IDLE_CONTROL" or
        full.get("scope")!=
        "SAME_REAL_WINDOWS_PROCESS_GO_PLUS_RUST_IDLE_128_TCP" or
        control.get("native_pid")!=full.get("native_pid") or
        control.get("observations",0)<3 or full.get("observations",0)<3):
        raise RuntimeError("H1894 matched process CPU phase provenance invalid")
    def rate(row,label):
        elapsed=row["measured_elapsed_s"]
        if elapsed<=2:raise RuntimeError("H1894 too-short original idle CPU phase")
        return row["process_"+label+"_cpu_s"]/elapsed
    user0=rate(control,"user");user128=rate(full,"user")
    kernel0=rate(control,"kernel");kernel128=rate(full,"kernel")
    return {
        "status":"SAME_ORIGINAL_WINDOWS_PROCESS_CPU_TWO_PHASES_MEASURED",
        "source":"ONE_SIGNED_WINTUN_TLS_OWNER_GETPROCESSTIMES_TWO_IDLE_WINDOWS",
        "native_pid":control["native_pid"],
        "pre128_cpu_singlecore_pct":round(100*(user0+kernel0),3),
        "tcp128_cpu_singlecore_pct":round(100*(user128+kernel128),3),
        "delta_singlecore_pct":round(100*(user128+kernel128-user0-kernel0),3),
        "delta_user_cpu_s_per_s":round(user128-user0,6),
        "delta_kernel_cpu_s_per_s":round(kernel128-kernel0,6),
        "interpretation":"Phase-associated process CPU with same UDP background, not randomized 0-vs128 causal attribution; driver ISR/DPC and OS-wide CPU NOT measured.",
        "warmup_warning":"pre128 may retain previous P2 TCP FIN-grace metadata, different chronological windows"
    }

def run_tcp128(root,out,physical,host_source,fake,unix,ready):
    if os.environ.get("WBD_PLAN029_TCP128_SCENE")!="1" or os.environ.get(
            "GITHUB_ACTIONS")!="true" or os.environ.get(
            "WBD_PLAN029_P2_MIXED_SCENE")!="1":
        raise RuntimeError("H1892 requires signed original Normal P2 scene")
    source=os.environ["GITHUB_SHA"]
    script=Path(root)/"tools"/"m0_plan029_h1892_real_tcp128.py"
    linux_log=Path(out)/"plan029-h1892-linux-tcp128.log"
    windows_log=Path(out)/"plan029-h1892-windows-tcp128.log"
    fguest=linux_log.open("w",encoding="utf-8")
    fwin=None;guest_proc=None;win_proc=None
    try:
        guest_proc=subprocess.Popen(["wsl.exe","-d","Ubuntu","-u","root","--",
            "python3","-u",unix(script),"guest",physical,host_source,source],
            stdout=fguest,stderr=subprocess.STDOUT)
        ready(linux_log,"PLAN029_H1892_LINUX_TCP128_LISTEN_READY",guest_proc,12)
        fwin=windows_log.open("w",encoding="utf-8")
        win_proc=subprocess.Popen([sys.executable,"-u",str(script),
            "windows","10.66.0.2",fake,source],
            stdout=fwin,stderr=subprocess.STDOUT)
        for proc,log,seconds in ((win_proc,windows_log,62),
                                 (guest_proc,linux_log,8)):
            try:rc=proc.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                raise RuntimeError("H1892 OS TCP128 timeout "+log.name+
                    " stage="+log.read_text(errors="replace")[-1300:])
            if rc:raise RuntimeError("H1892 true OS TCP128 failed "+log.name+
                " "+log.read_text(errors="replace")[-1500:])
        w=proof(windows_log,"PLAN029_H1892_WINDOWS_TCP128_RECEIPT")
        g=proof(linux_log,"PLAN029_H1892_LINUX_TCP128_RECEIPT")
        if (w.get("source_sha")!=source or g.get("source_sha")!=source or
            w.get("connections")!=N or g.get("accepted")!=N or
            w.get("held_idle_during_active")!=N-len(ACTIVE) or
            g.get("idle_connections")!=N-len(ACTIVE) or
            w.get("active_indices")!=list(ACTIVE) or
            g.get("active_indices")!=list(ACTIVE) or
            w.get("active_sent_bytes")!=[SIZE,SIZE] or
            w.get("active_echo_bytes")!=[SIZE,SIZE] or
            g.get("active_received_bytes")!=[SIZE,SIZE] or
            g.get("windows_physical_source")!=host_source or
            g.get("unique_physical_sources")!=1 or
            w.get("source_lease")!="10.66.0.2" or
            w.get("fakeip")!=fake or w.get("fin") is not True or
            w.get("active_sha256")!=g.get("active_sha256") or
            w.get("source_ports")!=list(range(SRC_BASE,SRC_BASE+N))):
            raise RuntimeError("H1892 genuine original Wintun 128/126idle+2live mismatch")
        return {"source_sha":source,
                "scope":"ONE_WINDOWS_WINTUN_OWNER_128_ORIGINAL_OS_TCP_SOCKETS_126_IDLE_2_ACTIVE",
                "windows":w,"linux":g,
                "rust_admission":"NOT_VERIFIED_UNTIL_ORIGINAL_STOP",
                "cpu_idle_128":"NOT_MEASURED_UNTIL_ORIGINAL_STOP",
                "stop":"NOT_RUN"}
    finally:
        for proc in (win_proc,guest_proc):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:proc.kill()
        fguest.close()
        if fwin is not None:fwin.close()

if __name__=="__main__":
    if len(sys.argv)!=5:
        raise SystemExit("H1892 requires exact guest|windows, two OS IPs and SHA")
    role,a,b,source=sys.argv[1:]
    if len(source)!=40 or any(ch not in "0123456789abcdef" for ch in source):
        raise SystemExit("H1892 invalid SOURCE")
    if role=="guest":guest(a,b,source)
    elif role=="windows":windows(a,b,source)
    else:raise SystemExit("H1892 invalid role")
