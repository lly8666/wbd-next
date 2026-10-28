"""Read-only original Windows process+thread CPU audit from real 1Hz Win32 samples.

No synthetic CPU assignment: blank GetThreadDescription names stay UNKNOWN.
Process kernel time is *charged* syscall time, not kernel-wide CPU usage.
Top-6 thread table is a lower bound for a thread missing from some samples.
This module does not measure AEAD, Npcap, Wintun, Go vs Rust stack CPU.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

_WORKER=re.compile(r"WBD_WINDOWS_RUST_NATIVE_WORKER_TID role=(TX|RX) tid=(\d+)")
_WAKE=re.compile(r"WBD_WINDOWS_RUST_NATIVE_WAKE_BATCH max_verified_per_wake=(\d+) tx_wake_attempts=(\d+) rx_data_delivered=(\d+) joined=true")

def summarize_windows_cpu(path,client_log=None):
    p=Path(path)
    if not p.is_file():
        return {"status":"NOT_MEASURED_FILE_MISSING"}
    rows=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:rows.append(json.loads(line))
            except (ValueError,TypeError):
                return {"status":"INCONCLUSIVE_MALFORMED_SAMPLE"}
    if len(rows)<3:
        return {"status":"NOT_MEASURED_INSUFFICIENT_OBSERVATIONS",
                "observations":len(rows)}
    rows=[r for r in rows if r.get("scope")==
          "SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"
          and isinstance(r.get("monotonic_s"),(int,float))
          and isinstance(r.get("cpu_total_s"),(int,float))]
    if len(rows)<3 or len({r.get("native_pid") for r in rows})!=1:
        return {"status":"INCONCLUSIVE_PROCESS_SCOPE"}
    rows.sort(key=lambda r:r["monotonic_s"])
    first,last=rows[0],rows[-1]
    elapsed=last["monotonic_s"]-first["monotonic_s"]
    if elapsed<=0:return {"status":"INCONCLUSIVE_TIME_SCOPE"}
    times={}
    for source,key in (("cpu_total_s","total"),("cpu_kernel_s","kernel"),
                       ("cpu_user_s","user")):
        a=first.get(source);b=last.get(source)
        if not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or b<a:
            return {"status":"INCONCLUSIVE_PROCESS_CPU_COUNTER"}
        times[key]=round(b-a,6)
    tid_totals=defaultdict(lambda:{"cpu_s_lower_bound":0.,"kernel_s_lower_bound":0.,
                                   "user_s_lower_bound":0.,"observations_in_top6":0,
                                   "names":set(),"name_statuses":set()})
    overall_status={}
    for row in rows:
        th=row.get("thread_cpu") or {}
        for status,count in (th.get("thread_name_status_counts") or {}).items():
            overall_status[status]=overall_status.get(status,0)+count
        for x in th.get("hottest_threads",[]):
            if not isinstance(x.get("tid"),int):continue
            tid=tid_totals[x["tid"]]
            tid["cpu_s_lower_bound"]+=max(0.,x.get("cpu_delta_s",0))
            tid["kernel_s_lower_bound"]+=max(0.,x.get("cpu_kernel_delta_s",0))
            tid["user_s_lower_bound"]+=max(0.,x.get("cpu_user_delta_s",0))
            tid["observations_in_top6"]+=1
            if x.get("name"):tid["names"].add(x["name"])
            if x.get("name_status"):tid["name_statuses"].add(x["name_status"])
    top=[]
    for tid,v in tid_totals.items():
        names=sorted(v["names"])
        top.append({
            "tid":tid,
            "name":names[0] if len(names)==1 else None,
            "name_statuses":sorted(v["name_statuses"]),
            "cpu_s_lower_bound":round(v["cpu_s_lower_bound"],5),
            "kernel_s_lower_bound":round(v["kernel_s_lower_bound"],5),
            "user_s_lower_bound":round(v["user_s_lower_bound"],5),
            "observations_in_top6":v["observations_in_top6"]})
    top.sort(key=lambda x:x["cpu_s_lower_bound"],reverse=True)
    # The real Rust worker logs GetCurrentThreadId once at spawn, avoiding
    # broken GetThreadDescription HRESULT on this Windows CI runner.
    # Reject ambiguous or recycled thread IDs rather than guessing.
    native_ids={}
    wake=None
    if client_log is not None and Path(client_log).is_file():
        log=Path(client_log).read_text(encoding="utf-8",errors="replace")
        matches=_WORKER.findall(log)
        counts={role:[int(tid) for r,tid in matches if r==role]
                for role in ("TX","RX")}
        if all(len(v)==1 for v in counts.values()) and counts["TX"]!=counts["RX"]:
            native_ids={v[0]:role for role,v in counts.items()}
        found=_WAKE.findall(log)
        if len(found)==1:
            max_per,attempts,delivered=map(int,found[0])
            if max_per==32 and delivered>=0 and attempts>=0:
                wake={"max_verified_per_wake":max_per,
                      "tx_wake_attempts":attempts,
                      "rx_data_delivered":delivered,
                      "data_delivered_per_tx_wake_attempt":
                          round(delivered/attempts,4) if attempts else None,
                      "interpretation":"Wake attempts also serve CONTROL and early handoff; data-delivered / wake-attempts is not exact batching CPU or time"}
    for row in top:
        row["rust_worker_role"]=native_ids.get(row["tid"])
    named={k:round(sum((r.get("thread_cpu") or {}).get(k,0) or 0 for r in rows),5)
            for k in ("rust_tx_cpu_delta_s","rust_rx_cpu_delta_s",
                      "rust_tx_kernel_delta_s","rust_tx_user_delta_s",
                      "rust_rx_kernel_delta_s","rust_rx_user_delta_s")}
    status=("MEASURED_NAMED_TX_RX" if
        named["rust_tx_cpu_delta_s"]>0 and named["rust_rx_cpu_delta_s"]>0 else
        "MEASURED_PROCESS_AND_UNATTRIBUTED_THREADS")
    return {
        "status":status,
        "scope":"PROCESS_LIFETIME_INCLUDING_START_STOP_NOT_MEASUREMENT_ALIGNED",
        "pid":first["native_pid"],"observations":len(rows),
        "elapsed_s":round(elapsed,4),
        "process_cpu_s":times,
        "process_cpu_pct_one_core":round(100*times["total"]/elapsed,3),
        "kernel_fraction_of_process_cpu":round(times["kernel"]/times["total"],5)
            if times["total"]>0 else None,
        "peak_working_set_bytes":max(r.get("working_set_bytes",0) for r in rows),
        "peak_private_bytes":max(r.get("private_bytes",0) for r in rows),
        "named_rust_workers_cpu_s":named,
        "verified_worker_os_tids":{role:tid for tid,role in native_ids.items()},
        "native_rx_to_tx_wake_batch":wake if wake is not None else {"status":"NOT_MEASURED"},
        "thread_name_status_counts_observation_sum":overall_status,
        "top_threads_by_lower_bound_cpu":top[:8],
        "top2_threads_cpu_share_lower_bound":round(
            sum(r["cpu_s_lower_bound"] for r in top[:2])/times["total"],5)
            if times["total"]>0 else None,
        "limitations":[
            "Nameless threads are UNKNOWN, not Go; no TX/RX language attribution without OS thread ID.",
            "Per-TID aggregate includes only top six per sampled second; lower bound, not total.",
            "Process kernel time charged within EXE is not total driver/ISR/DPC CPU time.",
            "No per-function stack sample or AEAD/NPF/Wintun stage CPU split; wall timing is not CPU.",
            "Different hosted VMs must not be compared as same-VM CPU optimization proof.",
        ]}
