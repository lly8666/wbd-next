#!/usr/bin/env python3
"""H2244 real inner UDP and TCP echoes while original Go TLS/Rust bulk runs.

Two independent application protocols travel through the genuine TUN path.
A reply must match the exact nonce+sequence. Missing is not RTT=0. Clock
timestamps are CLOCK_MONOTONIC on the same host as the native iperf case.
This is a scoped p99 SCREEN with limited samples, not physical WAN SLA.
"""
import argparse
import json
import math
import os
import pathlib
import secrets
import select
import signal
import socket
import struct
import threading
import time

MAGIC=b"WBD2244!"  # 8 bytes, application test payload, NOT WBD outer wire.
FRAME_LEN=16
UDP_PORT=53221
TCP_PORT=53222
COUNT=160
GAP_MS=80
START_DELAY_S=2.0
# Diagnostic only: original kernel TCP echo payload/wire and cadence
# never change. Same-host monotonic timestamps, no nonce or payload stored.
ECHO_SERVER_NODELAY=os.environ.get("WBD_M0_029_ECHO_SERVER_NODELAY","")
if ECHO_SERVER_NODELAY not in ("","0","1"):
    raise RuntimeError("H2272_ECHO_SERVER_NODELAY_INVALID")
TCP_TRACE=os.environ.get("WBD_M0_029_ECHO_TIMELINE")=="1"
TCP_INFO_TRACE=os.environ.get("WBD_M0_029_TCP_INFO")=="1"
if TCP_INFO_TRACE and not TCP_TRACE:
    raise RuntimeError("M029_H2260_TCP_INFO_NEEDS_APP_TRACE")
DRAIN_S=2.5

def frame(nonce,seq):
    return MAGIC+struct.pack("!II",nonce,seq)

def parse_frame(payload,nonce):
    if len(payload)!=FRAME_LEN or not payload.startswith(MAGIC):
        raise ValueError("H2244_CORRUPT_OR_UNEXPECTED_ECHO_FRAME")
    echoed,seq=struct.unpack("!II",payload[8:])
    if echoed!=nonce:raise ValueError("H2244_ECHO_NONCE_MISMATCH")
    return seq

def pct(samples, percentile):
    if not samples:
        return None
    xs=sorted(samples)
    return round(xs[max(0,math.ceil(len(xs)*percentile/100.0)-1)],4)

def _udp_server(bind, stop):
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind((bind,UDP_PORT))
    sock.settimeout(0.3)
    try:
        while not stop.is_set():
            try: data,peer=sock.recvfrom(128)
            except socket.timeout:continue
            if len(data)==FRAME_LEN and data.startswith(MAGIC):
                sock.sendto(data,peer)
    finally:
        sock.close()

def _tcp_session(conn):
    conn.settimeout(2.5)
    if ECHO_SERVER_NODELAY=="1":
        conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    if ECHO_SERVER_NODELAY:
        actual=conn.getsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY)
        print("H2272_SERVER_TCP_NODELAY_OS_READBACK val="+str(actual),flush=True)
        if actual!=int(ECHO_SERVER_NODELAY):
            raise RuntimeError("H2272_NATIVE_TCP_NODELAY_READBACK_MISMATCH")
    pending=bytearray()
    trace=[]
    try:
        while True:
            try: part=conn.recv(4096)
            except socket.timeout:continue
            if not part:break
            pending.extend(part)
            while len(pending)>=FRAME_LEN:
                f=bytes(pending[:FRAME_LEN])
                del pending[:FRAME_LEN]
                if not f.startswith(MAGIC):return
                if TCP_TRACE:
                    seq=struct.unpack("!I",f[12:16])[0]
                    received_ns=time.monotonic_ns()
                conn.sendall(f)
                if TCP_TRACE:
                    trace.append([seq,received_ns,time.monotonic_ns()])
    except (BrokenPipeError,ConnectionResetError,OSError):
        pass
    finally:
        conn.close()
        if TCP_TRACE:
            print("H2259_SERVER_TCP_TRACE "+json.dumps(trace,separators=(",",":")),flush=True)

def run_server(bind):
    stop=threading.Event()
    def shutdown(signum,frame):
        stop.set()
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    tcp=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    tcp.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    tcp.bind((bind,TCP_PORT))
    tcp.listen(16);tcp.settimeout(0.3)
    thread=threading.Thread(target=_udp_server,args=(bind,stop),daemon=True)
    thread.start()
    print("H2244_ECHO_SERVER_READY inner_bind="+bind+" udp="+str(UDP_PORT)+" tcp="+str(TCP_PORT),flush=True)
    try:
        while not stop.is_set():
            try: conn,_=tcp.accept()
            except socket.timeout:continue
            worker=threading.Thread(target=_tcp_session,args=(conn,),daemon=True)
            worker.start()
    finally:
        tcp.close();stop.set();thread.join(timeout=2)

def run_client(address,out,count,gap_ms,start_delay_s):
    if not (1<=count<=1000 and 10<=gap_ms<=500 and 0.5<=start_delay_s<=5.0):
        raise ValueError("H2244_UNBOUNDED_SMALL_FLOW_PROBE")
    nonce=secrets.randbits(32)
    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    udp.setblocking(False)
    tcp=socket.create_connection((address,TCP_PORT),timeout=6)
    tcp.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    tcp.settimeout(0.2)
    sent={"udp":{}, "tcp":{}}
    recv={"udp":{}, "tcp":{}}
    tcp_send_done={}
    errors=[]
    duplicates={"udp":0,"tcp":0}
    start_mono=time.monotonic_ns()+int(start_delay_s*1e9)
    done=threading.Event()
    info_done=threading.Event()
    info_rows=[]
    info_errors=[]
    def monitor_original_tcp_info():
        # One already-connected original test TCP socket, never WBD
        # producer FD, setsockopt, payload or Go per-packet calls.
        for _ in range(160):
            if info_done.is_set():break
            try:
                buf=tcp.getsockopt(socket.IPPROTO_TCP,socket.TCP_INFO,104)
                if len(buf)!=104:
                    info_errors.append("TCP_INFO_PREFIX_NOT_104_BYTES");return
                word=lambda offset:struct.unpack_from("=I",buf,offset)[0]
                info_rows.append([
                    time.monotonic_ns(),
                    word(8),word(24),word(36),word(68),word(80),word(100)
                ])
            except (OSError,struct.error) as exc:
                info_errors.append("TCP_INFO_NATIVE_"+type(exc).__name__)
                return
            if info_done.wait(0.15):break
    info_thread=None
    if TCP_INFO_TRACE:
        info_thread=threading.Thread(target=monitor_original_tcp_info,daemon=True)
        info_thread.start()
    def record(kind,payload,when):
        try: seq=parse_frame(payload,nonce)
        except ValueError as exc:
            errors.append(str(exc));return
        if seq not in sent[kind]:
            errors.append("H2244_ECHO_REPLY_NOT_SENT_"+kind);return
        if seq in recv[kind]:
            duplicates[kind]+=1;return
        recv[kind][seq]=when
    def sender(kind):
        target=sock=None
        for i in range(count):
            wanted=start_mono+int(i*gap_ms*1e6)
            remaining=(wanted-time.monotonic_ns())/1e9
            if remaining>0:time.sleep(remaining)
            payload=frame(nonce,i)
            sent[kind][i]=time.monotonic_ns()
            try:
                if kind=="udp":udp.sendto(payload,(address,UDP_PORT))
                else:
                    tcp.sendall(payload)
                    if TCP_TRACE:tcp_send_done[i]=time.monotonic_ns()
            except OSError as exc:
                sent[kind].pop(i,None)
                errors.append("H2244_"+kind+"_SEND_"+type(exc).__name__)
                break
    def udp_receiver():
        until=start_mono+int((count*gap_ms/1000.0+DRAIN_S)*1e9)
        while time.monotonic_ns()<until and not done.is_set():
            ready,_,_=select.select([udp],[],[],0.1)
            if not ready:continue
            try: data,_=udp.recvfrom(512)
            except BlockingIOError:continue
            record("udp",data,time.monotonic_ns())
    def tcp_receiver():
        until=start_mono+int((count*gap_ms/1000.0+DRAIN_S)*1e9)
        pending=bytearray()
        while time.monotonic_ns()<until and not done.is_set():
            try: part=tcp.recv(2048)
            except socket.timeout:continue
            except OSError as exc:
                errors.append("H2244_TCP_RECV_"+type(exc).__name__);break
            if not part:
                errors.append("H2244_TCP_EARLY_EOF");break
            pending.extend(part)
            while len(pending)>=FRAME_LEN:
                item=bytes(pending[:FRAME_LEN]);del pending[:FRAME_LEN]
                record("tcp",item,time.monotonic_ns())
    threads=[
        threading.Thread(target=udp_receiver,daemon=True),
        threading.Thread(target=tcp_receiver,daemon=True),
        threading.Thread(target=sender,args=("udp",),daemon=True),
        threading.Thread(target=sender,args=("tcp",),daemon=True),
    ]
    for t in threads:t.start()
    for t in threads[2:]:t.join(timeout=count*gap_ms/1000.0+7.0)
    if any(t.is_alive() for t in threads[2:]):
        errors.append("H2244_PROBE_SENDER_STALLED")
    # All send threads must have completed; give each reply a bounded drain.
    for t in threads[:2]:t.join(timeout=DRAIN_S+3)
    done.set()
    for t in threads[:2]:t.join(timeout=1)
    info_done.set()
    if info_thread is not None:
        info_thread.join(timeout=2)
        if info_thread.is_alive():info_errors.append("TCP_INFO_UNJOINED")
        if info_errors:errors.extend(info_errors)
        if len(info_rows)<30:errors.append("TCP_INFO_TOO_FEW_REAL_SAMPLES")
    tcp.close();udp.close()
    end_mono=time.monotonic_ns()
    receipt={}
    for kind in ("udp","tcp"):
        samples=[(when-sent[kind][seq])/1e6 for seq,when in recv[kind].items()]
        if any(x<0 for x in samples):
            errors.append("H2244_NONMONOTONIC_ECHO_"+kind)
        receipt[kind]={
            "requests_sent":len(sent[kind]),
            "unique_replies":len(recv[kind]),
            "missing":len(sent[kind])-len(recv[kind]),
            "duplicates":duplicates[kind],
            "latency_ms":{"p50":pct(samples,50),"p95":pct(samples,95),
                          "p99":pct(samples,99),"max":pct(samples,100)},
            "echoed_seqs":sorted(recv[kind]),
            "not_delivery_proof_if_missing":True
        }
    status=("PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO"
            if not errors and all(receipt[k]["unique_replies"]>=50
                                  for k in ("udp","tcp"))
            else "FAIL_REAL_SMALL_FLOW_MEASUREMENT")
    data={
        "schema_version":1,"source_sha":os.environ.get("GITHUB_SHA"),
        "run_id":os.environ.get("GITHUB_RUN_ID"),"status":status,
        "same_host_real_monotonic_ns":True,
        "server_inner_ipv4":address,"probe_start_monotonic_ns":start_mono,
        "probe_end_monotonic_ns":end_mono,
        "count_requested":count,"gap_ms":gap_ms,"start_delay_s":start_delay_s,
        "payload_test_only_no_outer_wire_change":True,
        "udp":receipt["udp"],"tcp":receipt["tcp"],
        "errors":errors,
        "sample_scope":"160 real requests/protocol, SCREEN not product p99 SLA"
    }
    if TCP_INFO_TRACE:
        data["tcp_info_native"]={
            "abi_bytes":104,"sample_period_ms":150,
            "fields":["mono_ns","rto_us","unacked","retrans","rtt_us",
                      "snd_cwnd","total_retrans"],
            "rows":info_rows,"errors":info_errors,
            "scope":"real_original_inner_TCP_client_socket_readonly"}
    if TCP_TRACE:
        data["tcp_client_trace"]=[
            [seq,sent["tcp"][seq],tcp_send_done.get(seq),recv["tcp"].get(seq)]
            for seq in sorted(sent["tcp"])]
        data["tcp_trace_scope"]="same_host_monotonic_test_app_only_not_wire_or_kernel_path"
    pathlib.Path(out).write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print("H2244_SMALL_ECHO_RESULT "+status,flush=True)
    if status.startswith("FAIL"):
        raise RuntimeError(status)

def main():
    p=argparse.ArgumentParser()
    cmd=p.add_subparsers(dest="command",required=True)
    s=cmd.add_parser("server");s.add_argument("--bind",required=True)
    c=cmd.add_parser("client");c.add_argument("--server",required=True)
    c.add_argument("--output",required=True)
    c.add_argument("--count",type=int,default=COUNT)
    c.add_argument("--gap-ms",type=int,default=GAP_MS)
    c.add_argument("--start-delay",type=float,default=START_DELAY_S)
    args=p.parse_args()
    if args.command=="server":run_server(args.bind)
    else:run_client(args.server,args.output,args.count,args.gap_ms,args.start_delay)

if __name__=="__main__":main()
