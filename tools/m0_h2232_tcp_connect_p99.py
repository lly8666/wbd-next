#!/usr/bin/env python3
"""H2232: real kernel TCP connect() P50/P95/P99 alongside H2231 iperf3.

No WBD product/wire edits: isolated original Linux netns WBD TUN or direct
underlay. This measures actual socket handshake completion on the live path,
not iperf's sender RTT, UDP app RTT, or exact one-way SYN->SYNACK wire time.
A 3-second workload has too few observed independent connections for P99.
Incomplete/failed connects count as failures and cannot become zero latency.
"""
import argparse
import errno
import json
import os
import pathlib
import selectors
import socket
import sys
import time

try:
    from tools.m0_h2231_three_runner_metrics import distribution, APP_P99_MIN_SAMPLES
except ImportError:
    from m0_h2231_three_runner_metrics import distribution, APP_P99_MIN_SAMPLES

DEST={"direct":("10.248.82.2",45912),"wbd":("10.66.0.1",45911)}
SCHEMA="H2232_REAL_TCP_CONNECT_P99_V1"
MAX_INFLIGHT=32
CONNECT_TIMEOUT_NS=3_000_000_000
IN_PROGRESS={errno.EINPROGRESS,errno.EALREADY,errno.EWOULDBLOCK,errno.EINTR}

def need(value,message):
    if not value:raise ValueError("H2232_TCP_CONNECT_FAIL_CLOSED_"+message)

def write(path,record):
    p=pathlib.Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")

def server(kind):
    need(kind in DEST,"SERVER_KIND")
    address,port=DEST[kind]
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((address,port))
        listener.listen(256)
        listener.settimeout(1)
        print("H2232_ORIGINAL_KERNEL_TCP_CONNECT_SERVER_READY kind="+kind,flush=True)
        while True:
            try:conn,_=listener.accept()
            except socket.timeout:continue
            # connect() completion is proved by kernel SYN/SYNACK/ACK.
            # No user-space application payload to fake business iperf.
            conn.close()

def validate(kind,count,interval_ms,deadline_s):
    need(kind in DEST,"TARGET_NOT_ALLOWLISTED")
    need(type(count) is int and 1<=count<=160,"INVALID_REQUEST_COUNT")
    need(interval_ms==100,"BAD_CONNECTION_CADENCE")
    need(2.0<=deadline_s<=20.0,"DEADLINE_OUT_OF_BOUNDS")
    need((count-1)*interval_ms/1000+0.6<deadline_s,
         "NOT_ENOUGH_TIME_TO_EMIT_REQUESTS")

def probe(kind,count=120,interval_ms=100,deadline_s=15,
          socket_factory=socket.socket, selector_factory=selectors.DefaultSelector):
    validate(kind,count,interval_ms,deadline_s)
    target=DEST[kind]
    start=time.monotonic_ns()
    end=start+int(deadline_s*1e9)
    interval=interval_ms*1_000_000
    next_due=start
    pending={}
    completed={}
    errors={}
    attempted=0
    skipped_capacity=0
    max_inflight=0
    def mark_error(seq,reason):
        errors[seq]=reason
    with selector_factory() as sel:
        try:
            while time.monotonic_ns()<end:
                now=time.monotonic_ns()
                # One physical handshake attempt per scheduled 100ms slot.
                # No post-preemption unbounded burst of SYNs.
                if attempted<count and now>=next_due:
                    seq=attempted
                    attempted+=1
                    # Never catch up a scheduler pause with clustered SYNs.
                    next_due=max(start+attempted*interval,now+interval)
                    if len(pending)>=MAX_INFLIGHT:
                        skipped_capacity+=1
                        mark_error(seq,"LOCAL_INFLIGHT_CAP")
                    else:
                        sock=socket_factory(socket.AF_INET,socket.SOCK_STREAM)
                        sock.setblocking(False)
                        stamp=time.monotonic_ns()
                        try:rc=sock.connect_ex(target)
                        except OSError as exc:rc=exc.errno or errno.EIO
                        if rc==0:
                            completed[seq]=(time.monotonic_ns()-stamp)/1e6
                            sock.close()
                        elif rc in IN_PROGRESS:
                            pending[sock.fileno()]=(sock,stamp,seq)
                            try:sel.register(sock,selectors.EVENT_WRITE)
                            except (OSError,ValueError):
                                pending.pop(sock.fileno(),None)
                                mark_error(seq,"LOCAL_SELECTOR_REGISTRATION_FAILED")
                                sock.close()
                        else:
                            mark_error(seq,"KERNEL_CONNECT_ERRNO_"+str(rc))
                            sock.close()
                        max_inflight=max(max_inflight,len(pending))
                now=time.monotonic_ns()
                for fd,(sock,stamp,seq) in list(pending.items()):
                    if now-stamp>=CONNECT_TIMEOUT_NS:
                        try:sel.unregister(sock)
                        except (KeyError,ValueError):pass
                        sock.close()
                        pending.pop(fd,None)
                        mark_error(seq,"TCP_CONNECT_TIMEOUT")
                if attempted==count and not pending:break
                until_next=(next_due-now)/1e9 if attempted<count else .1
                until_end=(end-now)/1e9
                timeout=max(0,min(.1,until_next,until_end))
                if timeout==0:continue
                for key,_ in sel.select(timeout):
                    sock=key.fileobj
                    fd=sock.fileno()
                    if fd not in pending:continue
                    _,stamp,seq=pending.pop(fd)
                    try:err=sock.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR)
                    except OSError as exc:err=exc.errno or errno.EIO
                    if err==0:
                        completed[seq]=(time.monotonic_ns()-stamp)/1e6
                    else:
                        mark_error(seq,"KERNEL_CONNECT_ERRNO_"+str(err))
                    try:sel.unregister(sock)
                    except (KeyError,ValueError):pass
                    sock.close()
        finally:
            for fd,(sock,stamp,seq) in list(pending.items()):
                mark_error(seq,"PROBE_DEADLINE_WITH_TCP_PENDING")
                try:sel.unregister(sock)
                except (KeyError,ValueError):pass
                sock.close()
            pending.clear()
    latencies=[completed[i] for i in sorted(completed)]
    error_reasons={}
    for reason in errors.values():
        error_reasons[reason]=error_reasons.get(reason,0)+1
    failures=attempted-len(completed)
    result={
        "schema":SCHEMA,
        "source_sha":os.environ.get("GITHUB_SHA"),
        "run_id":os.environ.get("GITHUB_RUN_ID"),
        "kind":kind,
        "origin":"REAL_LINUX_KERNEL_TCP_CONNECT_OVER_AUTHENTICATED_WBD_TUN" if
            kind=="wbd" else "REAL_LINUX_KERNEL_TCP_CONNECT_DIRECT_ARM_RELAY",
        "target_route":"original_wbd_inner_tun" if kind=="wbd" else "direct_relay_underlay",
        "attempted_independent_connections":attempted,
        "requested_connections":count,
        "succeeded_connects":len(completed),
        "failed_or_unfinished_connects":failures,
        "unattempted_due_to_deadline":count-attempted,
        "connect_failure_pct":round(100*failures/attempted,3) if attempted else None,
        "kernel_connect_error_counts":error_reasons,
        "max_concurrent_pending_connects":max_inflight,
        "connections_skipped_inflight_capacity":skipped_capacity,
        "cadence_ms":interval_ms,"deadline_s":deadline_s,
        "kernel_tcp_connect_elapsed_ms":distribution(
             latencies,APP_P99_MIN_SAMPLES,"ms"),
        "valid_connect_p99":len(latencies)>=APP_P99_MIN_SAMPLES,
        "connect_p99_status":("OBSERVED_SAMPLE_QUANTILE" if
            len(latencies)>=APP_P99_MIN_SAMPLES else
            "UNKNOWN_INSUFFICIENT_COMPLETED_REAL_TCP_CONNECTIONS"),
        "connect_elapsed_is_not_packet_rtt":True,
        "failed_handshakes_not_hidden_by_conditional_p99":True,
        "not_physical_windows_npcap":True,
        "raw_successful_connect_ms":[round(x,3) for x in latencies]
    }
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("tcp-serve")
    a.add_argument("kind",choices=tuple(DEST))
    a=sub.add_parser("tcp-probe")
    a.add_argument("kind",choices=tuple(DEST))
    a.add_argument("output")
    a.add_argument("--count",type=int,default=120)
    a.add_argument("--interval-ms",type=int,default=100)
    a.add_argument("--deadline",type=float,default=15.0)
    a=sub.add_parser("smoke")
    a=sub.add_parser("summary-verify")
    a.add_argument("path")
    args=p.parse_args()
    if args.command=="tcp-serve":
        server(args.kind)
    elif args.command=="tcp-probe":
        result=probe(args.kind,args.count,args.interval_ms,args.deadline)
        write(args.output,result)
        print("H2232_KERNEL_TCP_CONNECT_PROBE "+json.dumps({
            k:result[k] for k in ("kind","attempted_independent_connections",
                "succeeded_connects","failed_or_unfinished_connects","connect_p99_status")}),flush=True)
    elif args.command=="summary-verify":
        d=json.loads(pathlib.Path(args.path).read_text())
        need(d.get("schema")==SCHEMA,"SCHEMA")
        need(d.get("source_sha")==os.environ["GITHUB_SHA"] and
             d.get("run_id")==os.environ["GITHUB_RUN_ID"],"SOURCE_OR_RUN_ID")
        need(d["attempted_independent_connections"]>=0,"INVALID_TCP_ATTEMPTS")
        need(d["succeeded_connects"]<=d["attempted_independent_connections"],
             "TCP_COUNT_INVARIANT")
        need(d["valid_connect_p99"] is True or
             d["kernel_tcp_connect_elapsed_ms"]["p99"] is None,
             "FORGED_UNDERSAMPLED_TCP_P99")
        print("H2232_REAL_TCP_CONNECT_SOURCE_AND_SAMPLE_COUNTS_BOUND")
    else:
        validate("wbd",16,100,2.7)
        validate("direct",120,100,15.0)
        need(DEST["direct"]!=DEST["wbd"],"SAME_PHYSICAL_AND_VIRTUAL_TARGET")
        print("H2232_TCP_CONNECT_STATIC_SMOKE_NOT_REAL_WAN")

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TimeoutError) as exc:
        print("H2232_TCP_CONNECT_FAILURE "+str(exc),file=sys.stderr)
        sys.exit(2)
