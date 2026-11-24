#!/usr/bin/env python3
"""H2290 read-only same-PID Win32 original Go+Rust CPU in the actual TCP window.

Derive from authentic GetProcessTimes and Toolhelp GetThreadTimes 1Hz rows from
m0_wl_native_resource_sampler. Unknown unnamed threads must stay UNKNOWN;
never label residual process time "Go" or claim kernel DPC/ISR attribution.
Only diagnostic samples, no product/driver packet instrumentation or mutation.
"""
import json
import pathlib
import re
from collections import defaultdict

SCOPE="SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"
_WORKER=re.compile(r"WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=(TX|RX) tid=(\d+)")


def original_window_cpu(path,start,end,arm_received_bytes,original_log=None):
    path=pathlib.Path(path)
    if not path.is_file():raise RuntimeError("H2290_ORIGINAL_WIN32_NATIVE_CPU_SAMPLES_MISSING")
    if not end>start or arm_received_bytes<=0:
        raise RuntimeError("H2290_ACTUAL_BULK_WINDOW_OR_RECEIVED_BYTES_INVALID")
    try:
        rows=[json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    except (ValueError,TypeError) as err:
        raise RuntimeError("H2290_REAL_NATIVE_CPU_JSONL_INVALID") from err
    window=sorted((r for r in rows
                   if r.get("scope")==SCOPE
                   and isinstance(r.get("monotonic_s"),(int,float))
                   and start<=r["monotonic_s"]<=end),
                  key=lambda r:r["monotonic_s"])
    if (len(window)<14 or
        window[-1]["monotonic_s"]-window[0]["monotonic_s"]<14 or
        len({r.get("native_pid") for r in window})!=1):
        raise RuntimeError("H2290_REAL_WIN32_PROCESS_SAMPLE_WINDOW_UNQUALIFIED")
    first,last=window[0],window[-1]
    elapsed=last["monotonic_s"]-first["monotonic_s"]
    delta={}
    for attr,name in (("cpu_total_s","total"),("cpu_kernel_s","kernel"),
                      ("cpu_user_s","user")):
        x=first.get(attr);y=last.get(attr)
        if not isinstance(x,(int,float)) or not isinstance(y,(int,float)) or y<x:
            raise RuntimeError("H2290_REAL_PROCESS_CPU_COUNTER_MONOTONIC_MISSING")
        delta[name]=round(y-x,5)
    if abs(delta["total"]-delta["kernel"]-delta["user"])>0.2:
        raise RuntimeError("H2290_WIN32_PROCESS_CPU_COMPONENTS_MISMATCH")
    tids=defaultdict(lambda:{"cpu_s_lower_bound":0.0,"kernel_s_lower_bound":0.0,
                             "user_s_lower_bound":0.0,"names":set(),
                             "samples":0})
    for row in window[1:]:
        for t in (row.get("thread_cpu") or {}).get("hottest_threads",[]):
            tid=t.get("tid")
            if not isinstance(tid,int):continue
            x=tids[tid]
            x["cpu_s_lower_bound"]+=max(0.,t.get("cpu_delta_s",0) or 0)
            x["kernel_s_lower_bound"]+=max(0.,t.get("cpu_kernel_delta_s",0) or 0)
            x["user_s_lower_bound"]+=max(0.,t.get("cpu_user_delta_s",0) or 0)
            if t.get("name"):x["names"].add(t["name"])
            x["samples"]+=1
    native={}
    if original_log is not None and pathlib.Path(original_log).is_file():
        log=pathlib.Path(original_log).read_text(encoding="utf-8",errors="replace")
        matches=_WORKER.findall(log)
        for role in ("TX","RX"):
            values=[int(tid) for x,tid in matches if x==role]
            if len(values)==1:native[values[0]]=role
        if len(native)==2 and len(set(native))!=2:
            native={}
    top=[{"tid":tid,
          "name":sorted(v["names"])[0] if len(v["names"])==1 else None,
          "verified_rust_role":native.get(tid),
          "cpu_s_lower_bound":round(v["cpu_s_lower_bound"],5),
          "kernel_s_lower_bound":round(v["kernel_s_lower_bound"],5),
          "user_s_lower_bound":round(v["user_s_lower_bound"],5),
          "samples_in_top_six":v["samples"]}
          for tid,v in tids.items()]
    top.sort(key=lambda x:x["cpu_s_lower_bound"],reverse=True)
    gb=arm_received_bytes/(1024**3)
    out={"status":"MEASURED_ACTUAL_WINDOWS_ORIGINAL_PROCESS_WIN32_SAMPLED_BULK",
         "scope":"TRUE_ORIGINAL_GO_RUST_PROCESS_SAME_PID_SAMPLED_DURING_REAL_ARM_TUN_TCP_BULK",
         "native_pid":first["native_pid"],
         "samples_in_window":len(window),
         "sample_span_s":round(elapsed,3),
         "actual_bulk_start_monotonic":round(start,6),
         "actual_bulk_end_monotonic":round(end,6),
         "process_cpu_s":delta,
         "process_cpu_pct_one_core":round(delta["total"]/elapsed*100,3),
         "process_cpu_s_per_actual_arm_gib":round(delta["total"]/gb,4),
         "process_cpu_kernel_fraction":round(delta["kernel"]/delta["total"],4)
             if delta["total"]>0 else None,
         "peak_working_set_bytes":max(r.get("working_set_bytes",0) for r in window),
         "rust_worker_os_tids_if_unambiguous":{role:tid for tid,role in native.items()},
         "rust_tx_rx_top6_lower_bound_cpu_s":{
             role:round(sum(t["cpu_s_lower_bound"] for t in top
                         if t["verified_rust_role"]==role),4)
             for role in ("TX","RX")},
         "hottest_os_threads_lower_bound":top[:10],
         "limitations":[
             "1Hz samples cover a subset of the 25s app window and exclude endpoint boundary slices",
             "Go and Rust share the original Windows process; unnamed OS threads remain unattributed",
             "Only per-second top-six thread deltas are summed; worker CPU is lower bound",
             "Win32 process kernel time does not include driver, DPC, ISR or tailscaled CPU",
             "Not per-function CPU sampling, and run-to-run physical runners differ"]}
    return out
