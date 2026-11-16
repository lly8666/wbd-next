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


# H1953 signed-only first original Windows kernel listener/physical connect/
# local app inner receive -> first physical write; never Linux clock arithmetic.
PREWRITE_MARK="PLAN029_H1953_PREWRITE_QPC_FINAL "
def read_native_prewrite_qpc(log):
    lines=[line.split(PREWRITE_MARK,1)[1].strip()
           for line in log.splitlines() if PREWRITE_MARK in line]
    need(len(lines)==1,"H1953 original prewrite QPC absent/duplicated")
    m=re.fullmatch(r"frequency=([1-9]\d*) count=(\d+) rows=([0-9:,]*) "
                   r"source=original_rust_direct_test_only",lines[0])
    need(m is not None,"H1953 original prewrite QPC format invalid")
    freq=int(m[1]);count=int(m[2])
    need(0<count<=LIMIT,"H1953 original prewrite row count invalid")
    rows=[]
    for entry in m[3].split(","):
        fields=entry.split(":")
        need(len(fields)==7,"H1953 prewrite tuple incomplete")
        port,accepted,connected,inner_recv,phys_write,phys_recv,inner_write=map(int,fields)
        need(1024<=port<=65535 and
             0<accepted<=connected<=inner_recv<=phys_write<=phys_recv<=inner_write,
             "H1953 missing/nonmonotonic original prephysical event")
        rows.append((port,accepted,connected,inner_recv,phys_write,phys_recv,inner_write))
    need(len(rows)==count,"H1953 prewrite row count mismatch")
    need(all(a[-1]<=b[-1] for a,b in zip(rows,rows[1:])),
         "H1953 original inner write chronology invalid")
    return freq,rows

def analyze_prewrite(log,scene,source):
    prior=analyze_path(log,scene,source)
    freq,rows=read_native_prewrite_qpc(log)
    need(freq==prior["frequency_hz"],"H1953 QPC frequencies mismatch")
    _,existing=read_native_path_qpc(log)
    prior_path={}
    for port,w,r,i in existing:prior_path.setdefault(port,[]).append((w,r,i))
    by_port={}
    for j,row in enumerate(rows):by_port.setdefault(row[0],[]).append((j,row))
    used=set();reported={}
    for policy,app in (("fin_first",scene["windows"]),
                       ("payload_first",scene["echo_before_fin_control"]["windows"])):
        samples=[x for x in app["qpc_records"] if x.get("role")=="direct"]
        need(len(samples)==192,"H1953 original Direct application rows missing")
        to_accept=[];connect=[];await_inner=[];forward=[];to_outer=[]
        accepted_before_fin=0
        for x in samples:
            port=x["source_port"];fin=x["half_close_qpc"];first=x["first_echo_qpc"]
            found=[(j,row) for j,row in by_port.get(port,[])
                   if j not in used and fin-freq//100<=row[-1]<=first+freq//100]
            need(len(found)==1,"H1953 missing/ambiguous original Direct port QPC")
            j,row=found[0]
            _,a,c,r,w,o,i=row
            need(any((w,o,i)==prior for prior in prior_path.get(port,[])),
                 "H1953 events disagree with H1948 physical first-events")
            used.add(j)
            v=(a-fin)*1000/freq
            to_accept.append(v)
            accepted_before_fin+=int(v<0)
            connect.append((c-a)*1000/freq)
            await_inner.append((r-c)*1000/freq)
            forward.append((w-r)*1000/freq)
            to_outer.append((w-fin)*1000/freq)
        reported[policy]={
            "client_FIN_to_Rust_listener_accept_signed":dist(to_accept),
            "Rust_listener_accept_to_physical_connected":dist(connect),
            "physical_connected_to_first_inner_recv":dist(await_inner),
            "first_inner_recv_to_first_physical_write":dist(forward),
            "client_FIN_to_first_physical_write_signed":dist(to_outer),
            "listener_accept_precedes_client_FIN":accepted_before_fin}
    need(len(used)==384,"H1953 384 original Direct joined events required")
    return {"source_sha":source,"frequency_hz":freq,
            "status":"PASS_SCOPED_SAME_WINDOWS_PREPHYSICAL_QPC",
            "matched_direct_events":len(used),"rust_first_event_rows":len(rows),
            "policies":reported,
            "limitations":["WIN2025_SOURCE_LOCKED_NO_LINUX_ONEWAY_CLOCK",
                "ACCEPT_CONNECT_TIMESTAMPS_AFTER_SUCCESSFUL_SYSCALL",
                "INNER_RECV_AFTER_REAL_NONBLOCKING_KERNEL_READ",
                "PHYSICAL_WRITE_AFTER_SUCCESSFUL_KERNEL_SEND",
                "OBSERVATION_NOT_CAUSAL_P99_FIX_OR_CPU_AB"]}


# H1955 only: exact same-source, same-Windows, interleaved Direct SYN
# early physical connect vs original accept-time physical connect.
PRECON_MARK="PLAN029_H1955_PRECONNECT_AB_QPC_FINAL "
def read_native_preconnect_qpc(log):
    lines=[x.split(PRECON_MARK,1)[1].strip()
        for x in log.splitlines() if PRECON_MARK in x]
    need(len(lines)==1,"H1955 original preconnect receipt missing/duplicated")
    m=re.fullmatch(r"frequency=([1-9]\d*) count=(\d+) "
                   r"early_started=(\d+) early_failed=(\d+) "
                   r"rows=([0-9:,]*) source=original_rust_direct_test_only",
                   lines[0])
    need(m is not None,"H1955 invalid original preconnect receipt")
    freq=int(m[1]);count=int(m[2])
    started=int(m[3]);failed=int(m[4])
    need(0<count<=LIMIT and started>=0 and failed==0,
         "H1955 preconnect overflow/physical eager socket failed")
    rows=[]
    for entry in m[5].split(","):
        items=entry.split(":")
        need(len(items)==4,"H1955 original preconnect first-event row incomplete")
        port,enabled,start,accepted=map(int,items)
        need(1024<=port<=65535 and enabled in (0,1) and
             0<start<=accepted,"H1955 original preconnect time/mode malformed")
        need(enabled==1 or start==accepted,
             "H1955 off arm must not begin before listener accept")
        rows.append((port,enabled,start,accepted))
    need(len(rows)==count,"H1955 source first-event row count invalid")
    need(sum(int(x[1]) for x in rows)==started,
         "H1955 eager socket start count not matching first replies")
    return freq,rows

def analyze_preconnect(log,scene,source):
    proof=analyze_prewrite(log,scene,source)
    freq,rows=read_native_preconnect_qpc(log)
    need(freq==proof["frequency_hz"],"H1955 original Windows QPC freq changed")
    _,prewrites=read_native_prewrite_qpc(log)
    by_key={}
    for i,row in enumerate(rows):
        by_key.setdefault((row[0],row[3]),[]).append((i,row))
    qpc_by_port={}
    for port,accepted,connected,inner_recv,phys_write,phys_recv,reply_write in prewrites:
        qpc_by_port.setdefault(port,[]).append((
            accepted,connected,inner_recv,phys_write,phys_recv,reply_write))
    consumed=set();joined_pre=set();report={}
    for policy,app in (("fin_first",scene["windows"]),
                       ("payload_first",scene["echo_before_fin_control"]["windows"])):
        arm=[v for v in app["qpc_records"] if v.get("role")=="direct"]
        need(len(arm)==192,"H1955 missing original Direct application receipts")
        observations={"on":[],"off":[]}
        lead={"on":[],"off":[]}
        accepts={"on":[],"off":[]}
        for x in arm:
            port=x["source_port"];fin=x["half_close_qpc"];first=x["first_echo_qpc"]
            pre=[row for row in qpc_by_port.get(port,[])
                 if (port,row[0]) not in joined_pre and
                    fin-freq//100<=row[-1]<=first+freq//100]
            need(len(pre)==1,"H1955 actual physical prewrite QPC ambiguous")
            accepted,connected,inner_recv,write,recv,reply=pre[0]
            linked=by_key.get((port,accepted),[])
            need(len(linked)==1,"H1955 physical SYN start not matched by accept")
            i,row=linked[0]
            need(i not in consumed,"H1955 reused source-port preconnect event")
            consumed.add(i);joined_pre.add((port,accepted))
            _,mode,started,_=row
            arm_name="on" if mode==1 else "off"
            # Actual client half-close clock remains the same Windows QPC;
            # a negative FIN->write is a valid early payload response, not
            # a latency correction or an imaginary cross-OS timestamp.
            observations[arm_name].append((write-fin)*1000/freq)
            lead[arm_name].append((accepted-started)*1000/freq)
            accepts[arm_name].append((connected-accepted)*1000/freq)
        need(all(len(observations[k])==96 for k in ("on","off")),
             "H1955 within-policy 96-on/96-off interleaving missing")
        report[policy]={arm_name:{
            "n":len(observations[arm_name]),
            "client_FIN_to_first_physical_write_signed":dist(observations[arm_name]),
            "first_physical_connect_start_to_listener_accept":dist(lead[arm_name]),
            "listener_accept_to_physical_connected":dist(accepts[arm_name])
        } for arm_name in ("on","off")}
    need(len(consumed)==384,"H1955 all 384 original Direct off/on rows required")
    return {"source_sha":source,
        "status":"PASS_SCOPED_SAME_SOURCE_INTERLEAVED_PRECONNECT_P2",
        "matched_direct_events":384,"original_windows_frequency_hz":freq,
        "native_qpc_rows":len(rows),"policies":report,
        "preconnect_enabled_only_signed_original_CI":True,
        "limitations":["TRUE_SAME_SOURCE_WIN2025_INTERLEAVED_NOT_INDEPENDENT_VM",
                       "NOT_REMOTE_LINUX_ONEWAY_CLOCK",
                       "LOW_N_WITHIN_POLICY_P99_CANNOT_PROVE_CAUSAL_FIX",
                       "PHYSICAL_SOCKET_START_BEFORE_LISTENER_ACCEPT_NOT_EARLY_ACK",
                       "NORMAL_PRODUCT_EAGER_CONNECT_REMAINS_DISABLED"]}
