#!/usr/bin/env python3
"""PLAN029 signed original Windows/WSL2 established-flow QPC attribution.

All phases use original Windows QPC; Linux clock is NEVER subtracted.
Wintun on_packet entry is not Wintun ReadPacket, NAT queueing is not
RX-owned SendPacket, and positive WinSock write is not Linux receipt.
Segment/event joins are checked by 1024 bytes per app QPC request window.
"""
import math
import re

ING="PLAN029_H1966_STEADY_INGRESS_QPC_FINAL "
LEG="PLAN029_H1966_STEADY_LEGS_QPC_FINAL "
PREFIX="source=original_rust_"
MIN_COUNT=2048
WARMUP=32
SIZE=1024

def need(ok,why):
    if not ok:raise RuntimeError("H1966 QPC: "+why)

def distribution(values,freq):
    need(len(values)>=MIN_COUNT,"too few steady request samples")
    seq=sorted(v*1000/freq for v in values)
    def percentile(p):return round(seq[math.ceil(p*len(seq))-1],4)
    return {"n":len(seq),"p50_ms":percentile(.5),"p95_ms":percentile(.95),
            "p99_ms":percentile(.99),"max_ms":percentile(1)}

def read_chunks(log,mark,fields,expected_source):
    chunks={}
    frequency=None
    total=None
    dropped=None
    for line in log.splitlines():
        if mark not in line:continue
        text=line.split(mark,1)[1]
        need("source="+expected_source in text,"wrong source type in "+mark)
        text=text.split(" source=",1)[0]
        tokens={}
        for word in text.split():
            if "=" not in word:continue
            k,v=word.split("=",1)
            need(k not in tokens,"duplicate field")
            tokens[k]=v
        need(all(k in tokens for k in ("frequency","total","dropped","chunk","count","rows")),
             "missing original owner Stop fields")
        f,n,d,ch,c=[int(tokens[k]) for k in
                    ("frequency","total","dropped","chunk","count")]
        need(f>1000 and 0<=n<=8192 and d==0 and 0<=ch<100 and 0<=c<=96,
             "missing native QPC, overflow, or invalid chunk")
        if frequency is None:frequency,total,dropped=f,n,d
        need((f,n,d)==(frequency,total,dropped),"mixed original owner source")
        need(ch not in chunks,"duplicate chunk")
        raw=tokens["rows"]
        rows=[] if c==0 else [item.split(":") for item in raw.split(",")]
        need(len(rows)==c,"chunk row count mismatch")
        need(all(len(row)==fields for row in rows),"row field count mismatch")
        try:values=[tuple(int(x) for x in row) for row in rows]
        except ValueError as e:raise RuntimeError("H1966 QPC: nonnumeric row") from e
        chunks[ch]=values
    need(frequency is not None,"no original Rust Stop QPC rows")
    need(set(chunks)==set(range(len(chunks))),"missing chunk")
    data=[row for i in range(len(chunks)) for row in chunks[i]]
    need(len(data)==total and total>=MIN_COUNT,"partial/truncated original QPC")
    return frequency,data

def analyze(log,steady,source):
    need(steady["source_sha"]==source,"different original product SOURCE")
    direct=steady["direct"];physical=steady["physical"]
    need(all(d["source"]==source and d["measured"]==MIN_COUNT and
             d["warmup"]==WARMUP and d["exact_bytes"]==(MIN_COUNT+WARMUP)*SIZE and
             len(d["app_qpc"])==MIN_COUNT and d["half_close"] and
             d["nodelay"]==1 for d in (direct,physical)),
         "missing original Windows kernel application receipts")
    need(direct["role"]=="direct" and physical["role"]=="physical" and
         direct["source_port"]!=physical["source_port"] and
         direct["source_ip"]=="10.66.0.2","wrong physical/Direct socket identity")
    f,ing=read_chunks(log,ING,6,"original_rust_wintun_tx_test_only")
    f2,legs=read_chunks(log,LEG,12,"original_rust_tcp_test_only")
    need(f==f2==direct["qpc_frequency"]==physical["qpc_frequency"],
         "different Win32 QPC clock frequency")
    port=direct["source_port"]
    ing=[r for r in ing if r[0]==port]
    legs=[r for r in legs if r[0]==port]
    need(len(ing)>=MIN_COUNT and len(legs)>=MIN_COUNT,
         "original port missing ingress or two-leg progress")
    need(all(0<r[2]<=SIZE and 0<r[3]<=r[4]<=r[5] for r in ing),
         "invalid original Wintun TCP segment/phase order")
    need(all(0<r[1]<r[6] and r[7]+r[8]+r[9]+r[10]>0 for r in legs),
         "invalid original relay service span")
    need(all(r[1]<=t<=r[6] for r in legs for t in r[2:6] if t) and
         all((r[2]==0 or r[3]==0 or r[2]<=r[3]) and
             (r[4]==0 or r[5]==0 or r[4]<=r[5]) for r in legs),
         "positive WinSock event QPC outside its owner service turn")
    # Original app stops before each next send until the full prior echo.
    # Therefore a TCP segment belongs to exactly one (send, recv) interval,
    # irrespective of packet splits/merges. Sum bytes, not packet counts.
    app=direct["app_qpc"]
    need(all(len(r)==3 and 0<r[0]<=r[1]<=r[2] for r in app),
         "nonmonotonic original application QPC")
    need(all(app[i][2]<app[i+1][0] for i in range(len(app)-1)),
         "app pipelined or overlapped packets: cannot join")
    ingress_latency=[];nat_latency=[];inner_outer=[];outer_inner=[]
    ready_ms=[];window_missing=0;event_pairs=0
    for a,b,c in app:
        ir=[r for r in ing if a<=r[3]<=c]
        lr=[r for r in legs if a<=r[1]<=c]
        if sum(r[2] for r in ir)!=SIZE:
            window_missing+=1;continue
        ingress_latency.append(sum(r[4]-r[3] for r in ir))
        nat_latency.append(sum(r[5]-r[4] for r in ir))
        # A TCP relay can split, coalesce or queue; only attribute a
        # request when it has exact byte receipts on BOTH WinSock legs.
        if not (sum(r[7] for r in lr)==SIZE and
                sum(r[8] for r in lr)==SIZE and
                sum(r[9] for r in lr)==SIZE and
                sum(r[10] for r in lr)==SIZE):
            window_missing+=1;continue
        first_inner=min(r[2] for r in lr if r[2]>0 and r[7]>0)
        last_outer=max(r[3] for r in lr if r[3]>0 and r[8]>0)
        first_reply=min(r[4] for r in lr if r[4]>0 and r[9]>0)
        last_inner=max(r[5] for r in lr if r[5]>0 and r[10]>0)
        if not (first_inner<=last_outer<=first_reply<=last_inner<=c):
            window_missing+=1;continue
        inner_outer.append(last_outer-first_inner)
        outer_inner.append(last_inner-first_reply)
        ready_ms.extend(r[11] for r in lr)
        event_pairs+=1
    need(window_missing==0 and event_pairs==MIN_COUNT and
         len(ingress_latency)==MIN_COUNT,"missing or ambiguous request-to-owner QPC joins")
    app_physical=[r[2]-r[0] for r in physical["app_qpc"]]
    app_direct=[r[2]-r[0] for r in direct["app_qpc"]]
    p=distribution(app_physical,f)
    d=distribution(app_direct,f)
    return {
      "status":"PASS_SCOPED_ORIGINAL_WINDOWS_QPC_2048_MESSAGES_SAME_ONE_STREAM",
      "source_sha":source,"same_windows_qpc_frequency":f,
      "port":port,"messages":MIN_COUNT,
      "sequence_policy":"per stop-and-wait app QPC windows / exact 1024B on each kernel leg; no TCP packet count equality",
      "app_physical_rtt":p,"app_direct_rtt":d,
      "direct_minus_physical_rtt_ms":{k:round(d[k]-p[k],4)
                                    for k in ("p50_ms","p95_ms","p99_ms")},
      "wintun_on_packet_to_classification":distribution(ingress_latency,f),
      "classification_to_NAT_queued":distribution(nat_latency,f),
      "kernel_inner_read_to_physical_write":distribution(inner_outer,f),
      "physical_read_to_kernel_inner_write":distribution(outer_inner,f),
      "relay_ticket_age_ms":{"n":len(ready_ms),"max":max(ready_ms),
           "ge8":sum(t>=8 for t in ready_ms),"ge16":sum(t>=16 for t in ready_ms),
           "resolution":"coarse owner milliseconds, not QPC"},
      "unobserved":["Wintun ReadPacket before on_packet","owner RX mailbox age and SendPacket",
          "Windows TCP kernel consume/ACK","Linux guest execution (different clock)",
          "driver/kernel CPU attribution"],
      "causality":"APP_RTT_EXTRA_INCLUDES_WINDOWS_TCP_KERNEL_AND_SCHEDULING_NOT_ALL_RUST",
      "owned_stop":"JOIN_ONLY_AFTER_PASS_BOTH_OWNED"
    }
