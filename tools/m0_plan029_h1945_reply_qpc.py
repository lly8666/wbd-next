#!/usr/bin/env python3
"""Source-locked Win32 QPC split: Rust inner TCP write -> app first recv.

Only signed test's original Windows product + Python application.
No Linux/WSL2 clock synchronization, payload, packet capture or CPU claim.
"""
import math
import re
import statistics

MARK="PLAN029_H1945_REPLY_QPC_FINAL "
LIMIT=1024
def need(ok,why):
    if not ok:raise ValueError("H1945 "+why)
def dist(values):
    need(bool(values),"empty timing samples")
    s=sorted(values);p=lambda n:round(s[min(len(s)-1,math.ceil(len(s)*n)-1)],3)
    return {"n":len(s),"p50_ms":round(statistics.median(s),3),
            "p95_ms":p(.95),"p99_ms":p(.99),"max_ms":p(1),
            "ge8_ms":sum(v>=8 for v in s),"ge16_ms":sum(v>=16 for v in s)}
def read_native_qpc(log):
    lines=[line.split(MARK,1)[1].strip() for line in log.splitlines()
           if MARK in line]
    need(len(lines)==1,"original Rust final record absent/duplicated")
    m=re.fullmatch(r"frequency=([1-9]\d*) count=(\d+) rows=([0-9:,]*) "
                   r"source=original_rust_direct_test_only",lines[0])
    need(m is not None,"invalid native signed QPC record")
    freq=int(m[1]);count=int(m[2])
    need(0<count<=LIMIT,"native QPC count missing/overflow")
    rows=[]
    for pair in m[3].split(","):
        parts=pair.split(":")
        need(len(parts)==2,"invalid original Rust QPC row")
        port,tick=map(int,parts)
        need(1024<=port<=65535 and tick>0,"invalid source port/QPC")
        rows.append((port,tick))
    need(len(rows)==count,"native QPC count mismatch")
    need(all(x[1]<=y[1] for x,y in zip(rows,rows[1:])),
         "native QPC time order corrupt")
    return freq,rows

def analyze(original_log,scene,source):
    need(re.fullmatch(r"[0-9a-f]{40}",source) is not None,
         "invalid exact SOURCE")
    need(scene.get("source_sha")==source and
         scene.get("status")=="PASS_SCOPED_SMALL_TCP_A_B_B_A_SHA_FIN",
         "original FIN/SHA source not passed")
    follow=scene.get("echo_before_fin_control")
    need(isinstance(follow,dict) and follow.get("source_sha")==source and
         follow.get("status")=="PASS_SCOPED_ORIGINAL_TWO_OS_ECHO_BEFORE_FIN",
         "second original echo policy not passed")
    freq,rows=read_native_qpc(original_log)
    by_port={}
    for i,(port,tick) in enumerate(rows):by_port.setdefault(port,[]).append((i,tick))
    used=set();report={}
    for policy,app in (("fin_first",scene["windows"]),
                       ("payload_first",follow["windows"])):
        need(app.get("source_sha")==source and
             app.get("reply_policy")==policy and
             app.get("total_connections")==384 and
             app.get("qpc_frequency")==freq,
             "Windows client SOURCE/QPC frequency invalid")
        samples=app.get("qpc_records")
        need(isinstance(samples,list) and len(samples)==384,
             "missing QPC for both physical and Direct arms")
        arm=[x for x in samples if x.get("role")=="direct"]
        need(len(arm)==192,"missing 192 genuine Direct app sockets")
        before=[];after=[];total=[]
        for x in arm:
            port=x["source_port"];half=x["half_close_qpc"];first=x["first_echo_qpc"]
            need(type(port)==int and type(half)==int and type(first)==int
                 and 1024<=port<=65535 and 0<half<=first,
                 "invalid Windows application QPC")
            # 10ms tolerance allows Rust after-write timestamp and app
            # first recv to race on separate Windows threads, not a 10ms
            # artificial latency compensation. Reused ports match by QPC.
            candidates=[(i,t) for i,t in by_port.get(port,[])
                if i not in used and half-freq//100<=t<=first+freq//100]
            need(len(candidates)==1,"missing or ambiguous Rust reply QPC")
            idx,t=candidates[0];used.add(idx)
            before.append((t-half)*1000/freq)
            after.append((first-t)*1000/freq)
            total.append((first-half)*1000/freq)
        report[policy]={
            "client_FIN_to_Rust_first_inner_write":dist(before),
            "Rust_first_inner_write_to_client_first_recv":dist(after),
            "client_FIN_to_first_recv":dist(total),
            "negative_post_write_interleaving":sum(x<0 for x in after)}
    need(len(used)==384,"not all 384 native first reply events linked")
    return {"source_sha":source,
        "status":"PASS_SCOPED_OBSERVATIONAL_SAME_WINDOWS_QPC",
        "scope":"RUST_INNER_WINSOCK_WRITE_TO_WINDOWS_APP_FIRST_RECV",
        "frequency_hz":freq,"rust_logged_events":len(rows),
        "matched_direct_events":len(used),"policies":report,
        "limitations":["QPC_SAME_WINDOWS_VM_ONLY_NOT_LINUX_ONEWAY",
          "RUST_TIMESTAMP_AFTER_INNER_WRITE_SYSTEM_CALL_RETURN",
          "RUST_WRITE_TO_APP_RECV_INCLUDES_WINDOWS_TCP_WINTUN_AND_SCHEDULING",
          "CLIENT_FIN_TO_RUST_WRITE_INCLUDES_LINUX_AND_OUTER_TCP",
          "NOT_CPU_AB_OR_CAUSAL_P99_FIX"]}


# H1948: first REAL physical Winsock write -> first physical recv ->
# first inner Winsock write. No cross-OS absolute timestamp arithmetic:
# physical RTT includes Linux/WSL2 and actual physical TCP kernels.
PATH_MARK="PLAN029_H1948_REPLY_PATH_QPC_FINAL "
def read_native_path_qpc(log):
    lines=[line.split(PATH_MARK,1)[1].strip() for line in log.splitlines()
           if PATH_MARK in line]
    need(len(lines)==1,"H1948 original path QPC record absent/duplicated")
    m=re.fullmatch(r"frequency=([1-9]\d*) count=(\d+) rows=([0-9:,]*) "
                   r"source=original_rust_direct_test_only",lines[0])
    need(m is not None,"H1948 native path format invalid")
    freq=int(m[1]);count=int(m[2])
    need(0<count<=LIMIT,"H1948 native path count invalid")
    rows=[]
    for entry in m[3].split(","):
        fields=entry.split(":")
        need(len(fields)==4,"H1948 incomplete first-event row")
        port,w,r,i=map(int,fields)
        need(1024<=port<=65535 and 0<w<=r<=i,
             "H1948 first events missing or out of order")
        rows.append((port,w,r,i))
    need(len(rows)==count,"H1948 native row count mismatch")
    need(all(a[3]<=b[3] for a,b in zip(rows,rows[1:])),
         "H1948 inner QPC sequence not monotonic")
    return freq,rows

def analyze_path(original_log,scene,source):
    prior=analyze(original_log,scene,source)
    freq,paths=read_native_path_qpc(original_log)
    need(freq==prior["frequency_hz"],"H1948 QPC frequency differs")
    _,inners=read_native_qpc(original_log)
    by_port={}
    for j,(port,w,r,i) in enumerate(paths):
        by_port.setdefault(port,[]).append((j,w,r,i))
    inner_port={}
    for port,i in inners:inner_port.setdefault(port,[]).append(i)
    used=set();result={}
    for policy,app in (("fin_first",scene["windows"]),
                       ("payload_first",scene["echo_before_fin_control"]["windows"])):
        rows=[x for x in app["qpc_records"] if x.get("role")=="direct"]
        need(len(rows)==192,"H1948 direct app rows absent")
        from_fin=[];rtt=[];to_inner=[];to_app=[];total=[]
        for app_row in rows:
            port=app_row["source_port"]
            fin=app_row["half_close_qpc"];recv=app_row["first_echo_qpc"]
            # The inner write joins H1945's already-proven app window.
            # A port may be reused; require one unclaimed event per window.
            candidates=[(j,w,r,i) for j,w,r,i in by_port.get(port,[])
                if j not in used and fin-freq//100<=i<=recv+freq//100]
            need(len(candidates)==1,"H1948 native path missing or ambiguous")
            j,w,r,i=candidates[0]
            need(any(abs(i-old)<=freq//1000 for old in inner_port.get(port,[])),
                 "H1948 inner write does not match original H1945")
            used.add(j)
            from_fin.append((w-fin)*1000/freq)
            rtt.append((r-w)*1000/freq)
            to_inner.append((i-r)*1000/freq)
            to_app.append((recv-i)*1000/freq)
            total.append((recv-fin)*1000/freq)
        result[policy]={
            "client_FIN_to_first_physical_write_signed":dist(from_fin),
            "Rust_first_physical_write_to_first_physical_read":dist(rtt),
            "Rust_first_physical_read_to_first_inner_write":dist(to_inner),
            "Rust_first_inner_write_to_app_first_recv":dist(to_app),
            "client_FIN_to_app_first_recv":dist(total),
            "physical_write_precedes_FIN":sum(v<0 for v in from_fin)}
    need(len(used)==384,"H1948 384 source-locked Direct first-event joins not proven")
    return {"source_sha":source,"frequency_hz":freq,
        "status":"PASS_SCOPED_OBSERVATIONAL_SAME_WINDOWS_QPC_PATH",
        "matched_direct_events":len(used),"rust_path_rows":len(paths),
        "policies":result,
        "limitations":["NO_CROSS_WINDOWS_LINUX_ABSOLUTE_CLOCK",
          "PHYSICAL_WRITE_TO_READ_INCLUDES_LINUX_AND_NETWORK",
          "WIN32_QPC_NOT_CAUSAL_CPU_OR_LATENCY_FIX",
          "FIRST_OUTER_READ_IS_AFTER_NONBLOCKING_RECV_SUCCESS",
          "SIGNED_TEST_ONLY_NO_PRODUCTION_POLLING"]}
