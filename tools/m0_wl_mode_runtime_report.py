"""Read-only exact-source per-mode runtime evidence, no product promotion.

The Windows EXE contains both original Go and its Rust DLL. Windows
GetProcessTimes/working set cannot be partitioned by implementation language.
Snapshots with fewer than two real observations are NOT_MEASURED, not zero.
"""
from __future__ import annotations
import json
import pathlib

MARKER="WBD_WINDOWS_NATIVE_PACKET_TELEMETRY "
def _last_live_owner(out:pathlib.Path)->dict:
    path=out/"client.log"
    if not path.is_file():return {"result":"NOT_MEASURED_NO_ORIGINAL_OWNER_TELEMETRY"}
    # Only parse the end of the running owner log. Do not include raw TLS
    # credentials, app packet payloads, foreign traffic or launch arguments.
    with path.open("rb") as stream:
        stream.seek(0,2)
        end=stream.tell()
        stream.seek(max(0,end-2*1024*1024))
        raw=stream.read().decode("utf-8","replace")
    for line in reversed(raw.splitlines()):
        if not line.startswith(MARKER):continue
        try:
            row=json.loads(line[len(MARKER):])
        except (ValueError,TypeError):continue
        if not isinstance(row,dict):continue
        # Keep only safe measured fields; no credentials/opaque diagnostic
        # payloads can be returned by the parser.
        approved=("mode","actual_rust_m2_effective","npcap_ingress_local_drops",
                  "tx_records","rx_first_delivered_ipv4",
                  "rejected_or_invalid_carriers","oversize_rejects",
                  "original_source_batch_counts_0_to_4",
                  "original_source_stage_failures",
                  "original_m2_firstsend_batch_peak",
                  "pending_original_rust_frozen_or_unacked_legacy_carrier_records",
                  "oldest_unacked_carrier_ms","max_observed_interdelivery_ms",
                  "effective_payload_mtu","effective_mtu_updates","local_mtu_drops",
                  "failed_lanes","auto_requested_revision","auto_applied_revision",
                  "go_runtime_heap_alloc_bytes_1hz",
                  "go_runtime_heap_objects_1hz",
                  "go_runtime_mallocs_total_1hz","go_runtime_num_gc_1hz")
        return {"result":"OBSERVED_NATIVE_OWNER_1HZ",
                "fields":{k:row[k] for k in approved if k in row}}
    return {"result":"NOT_MEASURED_NO_ORIGINAL_OWNER_TELEMETRY"}

def summarize_original_windows_process(out:pathlib.Path)->dict:
    path=out/"windows-original-go-rust-process-1hz.jsonl"
    label="WHOLE_WINDOWS_EXE_ORIGINAL_GO_PLUS_RUST_DLL_AND_KERNEL"
    if not path.is_file():
        return {"scope":label,"result":"NOT_MEASURED_NO_PROCESS_SAMPLE"}
    valid=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        try:row=json.loads(line)
        except ValueError:continue
        if not isinstance(row,dict) or row.get("scope")!=(
            "SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED"):
            continue
        try:
            vals=[float(row[key]) for key in
                  ("monotonic_s","cpu_total_s","cpu_kernel_s","cpu_user_s")]
            pid=int(row["native_pid"])
            rss=int(row["working_set_bytes"])
            private=int(row["private_bytes"])
        except (ValueError,KeyError,TypeError):continue
        if min(vals)<0 or rss<0 or private<0:continue
        if valid and (pid!=valid[0][0] or vals[0]<=valid[-1][1]):
            continue
        valid.append((pid,*vals,rss,private))
    if len(valid)<2:
        return {"scope":label,"result":"NOT_MEASURED_INSUFFICIENT_REAL_PROCESS_SAMPLES",
                "observations":len(valid)}
    a,b=valid[0],valid[-1]
    elapsed=b[1]-a[1]
    total=b[2]-a[2];kernel=b[3]-a[3];user=b[4]-a[4]
    if elapsed<=0 or min(total,kernel,user)<0:
        return {"scope":label,"result":"NOT_MEASURED_INVALID_MONOTONIC_CPU"}
    return {"scope":label,"result":"MEASURED_SAME_NATIVE_PID",
            "pid":a[0],"observations":len(valid),
            "elapsed_s":round(elapsed,3),
            "cpu_total_s":round(total,4),
            "cpu_kernel_s":round(kernel,4),"cpu_user_s":round(user,4),
            "avg_one_logical_core_pct":round(total/elapsed*100,3),
            "peak_working_set_bytes":max(v[5] for v in valid),
            "peak_private_bytes":max(v[6] for v in valid),
            "language_cpu_attribution":"UNKNOWN_NEEDS_SHORT_STACK_SAMPLE"}

def source_locked_observability(out:pathlib.Path)->dict:
    return {"windows_native_owner":_last_live_owner(out),
            "windows_original_process":summarize_original_windows_process(out),
            "business_oneway_p99":"NOT_MEASURED_UNCALIBRATED_OS_CLOCKS"}


def summarize_auto_udp_progress(path:pathlib.Path)->dict:
    """Bounded actual socket-send/first-receive witnesses; never M2 quality."""
    if not path.is_file():
        return {"result":"NOT_MEASURED_NO_REAL_AUTO_UDP_LOG"}
    with path.open("rb") as stream:
        stream.seek(0,2)
        end=stream.tell()
        stream.seek(max(0,end-256*1024))
        raw=stream.read().decode("utf-8","replace")
    rows=[]
    for line in raw.splitlines():
        if not line.startswith("{"):continue
        try:row=json.loads(line)
        except (ValueError,TypeError):continue
        if not isinstance(row,dict) or row.get("phase")!="udp_1hz":continue
        sent,received=row.get("sent"),row.get("received")
        if type(sent) is not int or type(received) is not int or sent<0 or received<0:
            return {"result":"NOT_MEASURED_INVALID_AUTO_SOURCE_COUNTER"}
        if rows and (sent<rows[-1]["socket_sent"] or received<rows[-1]["received_first"]):
            return {"result":"NOT_MEASURED_AUTO_SOURCE_COUNTER_RESET"}
        rows.append({"socket_sent":sent,"received_first":received})
    if not rows:
        return {"result":"NOT_MEASURED_NO_REAL_AUTO_1HZ_SAMPLES"}
    # 1Hz progress is not an exact 2s/8s M2 maturity window or a verified
    # Wintun ingress receipt. Do not compare these deltas to the 512 gate.
    deltas=[rows[i]["socket_sent"]-rows[i-1]["socket_sent"]
            for i in range(1,len(rows))]
    return {
        "result":"OBSERVED_REAL_APP_1HZ_SOCKET_PROGRESS",
        "observations":len(rows),"first":rows[0],"last":rows[-1],
        "min_socket_sent_per_observation":min(deltas) if deltas else None,
        "max_socket_sent_per_observation":max(deltas) if deltas else None,
        "last_four":rows[-4:],
        "owner_m2_2s8s_denominator":"NOT_MEASURED_BY_APP"}
