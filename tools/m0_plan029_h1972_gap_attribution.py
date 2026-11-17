#!/usr/bin/env python3
"""PLAN029 H1972: source-joined ordinary steady TCP Windows QPC *gaps*.

No new traffic and no Linux/Windows clock subtraction. Audit only the
2048 genuine original single-connection application QPC windows, one
1024B Wintun ingress plus 1024B on each actual WinSock relay leg.
"""
import math
from m0_plan029_h1966_steady_qpc import (
    read_chunks,ING,LEG,MIN_COUNT,SIZE,need
)

def dist_us(rows,frequency):
    need(len(rows)==MIN_COUNT and all(isinstance(v,int) and v>=0 for v in rows),
         "H1972 exact nonnegative 2048 QPC gaps missing")
    values=sorted(rows)
    return {"n":len(values),
            **{k:round(values[math.ceil(p*len(values))-1]*1_000_000/frequency,3)
               for k,p in (("p50_us",.5),("p95_us",.95),("p99_us",.99),
                           ("max_us",1.0))}}

def analyze(log,steady,source):
    need(steady["source_sha"]==source,"H1972 source differs")
    report=steady["same_source_steady_windows_qpc"]
    need(report["status"]==
         "PASS_SCOPED_ORIGINAL_WINDOWS_QPC_2048_MESSAGES_SAME_ONE_STREAM" and
         report["source_sha"]==source and report["messages"]==MIN_COUNT,
         "H1972 first exact source/bytes Stop join absent")
    f,ing=read_chunks(log,ING,6,"original_rust_wintun_tx_test_only")
    f2,legs=read_chunks(log,LEG,12,"original_rust_tcp_test_only")
    direct=steady["direct"]
    port=direct["source_port"]
    need(f==f2==direct["qpc_frequency"]==report["same_windows_qpc_frequency"],
         "H1972 QPC shared frequency mismatch")
    ing=[r for r in ing if r[0]==port]
    legs=[r for r in legs if r[0]==port]
    rows={name:[] for name in (
      "app_start_to_on_packet","on_packet_to_nat_complete",
      "nat_complete_to_kernel_inner_read","kernel_inner_read_to_physical_write",
      "physical_write_to_physical_read","physical_read_to_kernel_inner_write",
      "kernel_inner_write_to_app_recv","complete_app_rtt")}
    for a,b,c in direct["app_qpc"]:
        ir=[r for r in ing if a<=r[3]<=c]
        lr=[r for r in legs if a<=r[1]<=c]
        need(sum(x[2] for x in ir)==SIZE and
             all(sum(x[idx] for x in lr)==SIZE for idx in (7,8,9,10)),
             "H1972 1024B ingress / 4 kernel leg exact byte join failed")
        entry=min(x[3] for x in ir)
        nat=max(x[5] for x in ir)
        inner_read=min(x[2] for x in lr if x[7]>0)
        physical_write=max(x[3] for x in lr if x[8]>0)
        physical_read=min(x[4] for x in lr if x[9]>0)
        inner_write=max(x[5] for x in lr if x[10]>0)
        need(a<=entry<=nat<=inner_read<=physical_write<=
             physical_read<=inner_write<=c,
             "H1972 cross-owner QPC chronology cannot join without overlap")
        row_values=(entry-a,nat-entry,inner_read-nat,
                    physical_write-inner_read,physical_read-physical_write,
                    inner_write-physical_read,c-inner_write,c-a)
        for k,v in zip(rows,row_values):rows[k].append(v)
    need(all(len(v)==MIN_COUNT for v in rows.values()),
         "H1972 missing exact continuous 2048 requests")
    return {"source_sha":source,"status":"PASS_SCOPED_REAL_ORIGINAL_WINDOWS_2048_QPC_GAPS",
            "mode":"ONE_NORMAL_ALREADY_ESTABLISHED_DIRECT_KERNEL_TCP_1KIB",
            "windows_qpc_frequency":f,"matched_source_port":port,
            "gaps_us":{k:dist_us(v,f) for k,v in rows.items()},
            "observability":"on_packet starts AFTER Wintun ReadPacket; no RX SendPacket timestamps",
            "large_gap_priority":"nat_to_kernel_inner_read and inner_write_to_app_recv",
            "cross_run_causality":"NOT_ESTABLISHED_BY_DIFFERENT_VM_RUNS",
            "terminal":"REQUIRES_PRIOR_FULL_ORIGINAL_OWNED_STOP"}
