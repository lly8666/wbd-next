#!/usr/bin/env python3
"""H2243: true TUN global token-bucket fair-burst scheduling with native M4 batches.

Only a cold, deliberately reversible local TUN reader capacity-feedback
candidate changes source admission; TLS/FEC/PN/opportunistic outer repair
and DATA ordering remain unchanged. True 4flow baseline/candidate/baseline,
new original TLS/Rust client generation + owned Stop per phase. Existing
M4 observer and TUN 200ms counters use the same CLOCK_MONOTONIC clock.
No Go per-packet callback, packet contents, new owner or new delivery path.
"""
import json
import os
import pathlib
import re
import shutil
import sys

REPO=pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:sys.path.insert(0,str(REPO))
from tools import m0_h2234_local_netns as L

PHASES=(("original_before",4),
        ("tbf16kb_fq_codel",4),
        ("tbf48kb_fq_codel",4),
        ("original_after",4))
TBF_RATE_MBIT=450
BURST_KIB=(16,48)
GATE_MARKER="V4_PUBLIC_H2241_TUN_GATE_STOP "
TUN_MARKER="V4_PUBLIC_H2240_TUN_WINDOW "
TX_MARKER="V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG "

def numeric_receipts(log,marker,required):
    values=[]
    for line in log.splitlines():
        if marker not in line:continue
        found=dict((key,int(val)) for key,val in re.findall(r"(\w+)=(\d+)",line))
        if any(k not in found for k in required):
            raise RuntimeError("H2240_INCOMPLETE_REAL_NATIVE_RECEIPT_"+marker.split()[0])
        values.append({k:found[k] for k in required})
    times=[x["mono_ns"] for x in values]
    if any(x<=0 for x in times) or any(b<=a for a,b in zip(times,times[1:])):
        raise RuntimeError("H2240_NONMONOTONIC_KERNEL_TIMESTAMP")
    if len(values)>240:raise RuntimeError("H2240_OUT_OF_BOUNDED_TRACE_SCOPE")
    return values

def scoped_diagnostic(log,case,label):
    start=case.get("iperf_start_monotonic_ns")
    end=case.get("iperf_end_monotonic_ns")
    if not isinstance(start,int) or not isinstance(end,int) or end<=start:
        raise RuntimeError("H2240_CASE_WITHOUT_REAL_MONOTONIC_INTERVAL")
    tun_keys=("mono_ns","generation","tun_batches","tun_observed",
              "delivered","backpressure","queue_full","queue_age",
              "queue_bytes","retired","pending_packets","oldest_pending_ns",
              "reader_single","no_hol")
    tx_keys=("mono_ns","generation","source_queued","m4_copied",
             "tx_err","tx_backpressure","tx_worker_cpu_ns")
    tun=numeric_receipts(log,TUN_MARKER,tun_keys)
    tx=numeric_receipts(log,TX_MARKER,tx_keys)
    def inside(data):return [x for x in data if start<=x["mono_ns"]<=end]
    tun,tx=inside(tun),inside(tx)
    if len(tun)<35 or len(tx)<8:
        raise RuntimeError("H2240_TRUE_SOURCE_TIME_BUCKETS_UNAVAILABLE")
    if not all(x["reader_single"]==1 and x["no_hol"]==1 for x in tun):
        raise RuntimeError("H2240_SOURCE_HOL_OR_READER_SEMANTICS_UNVERIFIED")
    if len({x["generation"] for x in tun})!=1 or len({x["generation"] for x in tx})!=1:
        raise RuntimeError("H2240_GENERATION_MIXED_DIAGNOSTIC")
    differences=[]
    for a,b in zip(tun,tun[1:]):
        fields=("tun_batches","tun_observed","delivered","backpressure",
                "queue_full","queue_age","queue_bytes","retired")
        entry={"end_monotonic_ns":b["mono_ns"],
               "elapsed_ns":b["mono_ns"]-a["mono_ns"],
               "pending_packets":b["pending_packets"],
               "oldest_pending_ns":b["oldest_pending_ns"]}
        for field in fields:
            if b[field]<a[field]:raise RuntimeError("H2240_MONOTONIC_COUNTER_RESET")
            entry[field+"_delta"]=b[field]-a[field]
        differences.append(entry)
    txdiff=[]
    for a,b in zip(tx,tx[1:]):
        fields=("source_queued","m4_copied","tx_err",
                "tx_backpressure","tx_worker_cpu_ns")
        diff={"end_monotonic_ns":b["mono_ns"],
              "elapsed_ns":b["mono_ns"]-a["mono_ns"]}
        for field in fields:
            if b[field]<a[field]:raise RuntimeError("H2240_TX_COUNTER_RESET")
            diff[field+"_delta"]=b[field]-a[field]
        txdiff.append(diff)
    max_drop=max(x["queue_full_delta"] for x in differences)
    max_pending=max(x["pending_packets"] for x in differences)
    stop_duration=(end-start)
    diagnostic={
        "status":"REAL_ORIGINAL_TUN200MS_AND_TX500MS_MONO_TICKS",
        "name":label,
        "iperf_interval_monotonic_ns":[start,end],
        "source":"ORIGINAL_RUST_OWNER_NANOS_NOT_PACKET_SAMPLES",
        "tun_points":len(tun),"tx_points":len(tx),
        "max_queue_full_in_one_200ms_bucket":max_drop,
        "queue_full_in_observed_case_buckets":sum(x["queue_full_delta"] for x in differences),
        "max_pending_packets":max_pending,
        "max_oldest_pending_ns_in_sample":max(x["oldest_pending_ns"] for x in differences),
        "read_packets_observed_in_case_buckets":sum(x["tun_observed_delta"] for x in differences),
        "tx_copied_in_case_buckets":sum(x["m4_copied_delta"] for x in txdiff),
        "tx_cpu_ns_in_case_buckets":sum(x["tx_worker_cpu_ns_delta"] for x in txdiff),
        "tcp_case_duration_ns":stop_duration,
        "no_packet_logging_or_ordering":True,
        "caveat":"200/500ms bins don't pinpoint first per-packet stall; only source aggregate intervals",
    }
    return diagnostic,{"tun_200ms":differences,"m4_tx_500ms":txdiff}

def gate_stop_receipt(log,expected):
    matches=[x for x in log.splitlines() if GATE_MARKER in x]
    if not expected:
        if matches:raise RuntimeError("H2241_OFF_CASE_GATE_ACTIVE")
        return {"status":"ORIGINAL_PRODUCT_NO_GATE_RECEIPT"}
    if len(matches)!=1:
        raise RuntimeError("H2241_NO_EXACT_OWNED_GATE_STOP")
    d={k:int(v) for k,v in re.findall(r"(\w+)=(\d+)",matches[0])}
    for field in ("generation","gated_turns","sleep_ns","max_sleep_ns",
                  "single_route_only","no_hol","original_owner",
                  "no_queue_or_wire_change"):
        if field not in d:raise RuntimeError("H2241_INCOMPLETE_GATE_STOP")
    if any(d[x]!=1 for x in
           ("single_route_only","no_hol","original_owner","no_queue_or_wire_change")):
        raise RuntimeError("H2241_GATE_CONTRACT_VIOLATION")
    return dict(status="REAL_GENUINE_EXCLUSIVE_ORIGINAL_READER_GATE_STOP",**d)

def tun_kernel_snapshot(node):
    # Read exactly the current original client-owned TUN, never global host.
    return {
        "tc":json.loads(L.ns(node.client,"tc","-s","-j","qdisc",
                            "show","dev","wbdc0").stdout),
        "link":json.loads(L.ns(node.client,"ip","-s","-j","link",
                              "show","dev","wbdc0").stdout)
    }

def install_owned_tun_aggregate_burst_fair(node,burst_kib):
    """Test-only owned TUN global token bucket with per-5-tuple fq_codel.

    Original fq600 is PER FLOW; four TCP streams can overwhelm one
    original M4 owner. TBF admits a *short bounded batch* at the
    aggregate rate, preserving synchronous M4 sendmmsg batch efficiency.
    Child fq_codel isolates flows and marks ECN/actively bounds queue age.
    Nothing changes the native owner, wire, TLS, FEC, queue capacities,
    original TUN ring or production cold Go policy.
    """
    if burst_kib not in BURST_KIB:
        raise RuntimeError("H2243_UNAPPROVED_TBF_BURST")
    if node.owned_pid("client") is None:
        raise RuntimeError("H2243_UNOWNED_TUN")
    before=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
    if "qdisc fq " not in before or " root " not in before or "maxrate 600Mbit" not in before:
        raise RuntimeError("H2243_ORIGINAL_FQ600_NOT_READBACK")
    link=json.loads(L.ns(node.client,"ip","-j","link","show","dev","wbdc0").stdout)
    if len(link)!=1 or link[0].get("ifname")!="wbdc0" or link[0].get("txqlen")!=2048:
        raise RuntimeError("H2243_NOT_ORIGINAL_TUN_RING_2048")
    L.ns(node.client,"tc","qdisc","replace","dev","wbdc0",
         "root","handle","1:","tbf","rate",
         str(TBF_RATE_MBIT)+"mbit","burst",str(burst_kib)+"kb","latency","15ms")
    L.ns(node.client,"tc","qdisc","replace","dev","wbdc0",
         "parent","1:1","handle","10:","fq_codel",
         "limit","256","target","5ms","interval","100ms","ecn")
    after=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
    if not ("qdisc tbf 1:" in after and " root " in after and
            "qdisc fq_codel 10:" in after and "parent 1:1" in after and
            "rate 450Mbit" in after):
        raise RuntimeError("H2243_TBF_FQCODEL_ACTUAL_KERNEL_READBACK_MISMATCH")
    return {"previous_original_fq600":before,
            "real_tbf_fq_codel_readback":after,
            "burst_kib":burst_kib,"aggregate_rate_mbps":TBF_RATE_MBIT,
            "fq_codel_packets_limit":256,"fq_codel_target_ms":5,
            "latency_tbf_max_ms":15,
            "no_original_kernel_tun_ring_capacity_change":True,
            "test_only_not_production_default":True}

def source_kernel_qdisc_receipt(before,after,expected):
    """Source-truthful per qdisc, never sum duplicated parent/child drops."""
    if len(before["link"])!=1 or len(after["link"])!=1:
        raise RuntimeError("H2243_MISSING_EXACT_OWNED_TUN_LINK")
    a=before["link"][0].get("stats64",{}).get("tx",{})
    b=after["link"][0].get("stats64",{}).get("tx",{})
    if any(not isinstance(x.get(k),int) for x in (a,b)
           for k in ("packets","dropped","bytes")):
        raise RuntimeError("H2243_REAL_TUN_LINK_COUNTS_UNKNOWN")
    result={"actual_link_tx_"+key+"_delta":b[key]-a[key]
            for key in ("packets","dropped","bytes")}
    kinds=["fq"] if expected=="original" else ["tbf","fq_codel"]
    def by_kind(s):
        seen={}
        for x in s["tc"]:
            if x.get("kind") not in kinds or x["kind"] in seen:
                raise RuntimeError("H2243_UNEXPECTED_QDISC_KIND_OR_DUPLICATE")
            seen[x["kind"]]=x
        if set(seen)!=set(kinds):
            raise RuntimeError("H2243_MISSING_OWNED_TBF_OR_FAIR_LEAF")
        if not seen[kinds[0]].get("root",False):
            raise RuntimeError("H2243_ROOT_QDISC_NOT_READBACK")
        return seen
    src,dst=by_kind(before),by_kind(after)
    for k in kinds:
        u,v=src[k],dst[k]
        for field in ("packets","drops","bytes"):
            if not isinstance(u.get(field),int) or not isinstance(v.get(field),int):
                raise RuntimeError("H2243_REAL_QDISC_COUNT_UNKNOWN_"+k)
            result[k+"_"+field+"_delta"]=v[field]-u[field]
    if any(v<0 for v in result.values()):
        raise RuntimeError("H2243_KERNEL_STATS_REGRESSION")
    result["parent_child_drops_may_overlap_not_additive"]=expected!="original"
    result["original_real_tun_ring_txqlen"]=2048
    return result

def rearm_direct_capacity_listener(node):
    """Fresh unmodified iperf3 listener, no seed/parameter/result retry."""
    old=node.owned_pid("iperf-direct")
    if old is not None:
        L.root("kill","-TERM",str(old),allow_fail=True)
        p=node.procs["iperf-direct"]
        try:p.wait(timeout=5)
        except Exception: raise RuntimeError("H2243_OLD_DIRECT_IPERF_DID_NOT_EXIT")
    node.spawn("iperf-direct",node.server,["iperf3","-s","-B",L.IP_S,"-p","5202"])
    import time
    for _ in range(40):
        if ":5202 " in L.ns(node.server,"ss","-ltn").stdout:
            return {"status":"FRESH_ORIGINAL_IPERF_SERVER_KERNEL_TCP",
                    "no_product_change":True}
        time.sleep(0.2)
    raise RuntimeError("H2243_FRESH_DIRECT_IPERF_NOT_LISTENING")

def main():
    workspace=pathlib.Path(os.environ["GITHUB_WORKSPACE"])
    source=os.environ["GITHUB_SHA"];runid=os.environ["GITHUB_RUN_ID"]
    if not re.fullmatch("[0-9a-f]{40}",source):
        raise RuntimeError("H2240_SOURCE_SHA_REQUIRED")
    build=workspace/"linux-plan029-public-bundle"
    for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
        if not (build/name).is_file():raise RuntimeError("H2240_GENUINE_PRODUCT_BUILD_MISSING")
    if not pathlib.Path("/dev/net/tun").is_char_device():
        raise RuntimeError("H2240_NOT_TRUE_TUN")
    out=workspace/"h2243-burst-fair-m4"
    out.mkdir(parents=True,exist_ok=True)
    tmp=pathlib.Path(os.environ["RUNNER_TEMP"])/("h2243-"+runid)
    tmp.mkdir(parents=True,mode=0o700,exist_ok=False)
    os.environ["WBD_H2233_FOCUS"]="1"
    os.environ["WBD_H2234_TRACE"]="1"
    os.environ["WBD_H2233_MSS"]="1037"
    os.environ["WBD_H2240_NATIVE_TEST"]="1"
    node=L.OwnedLocal(build,out,tmp)
    phase_results=[]
    direct_receipts=[]
    status="NOT_RUN"
    error=None
    server_stop=False
    try:
        node.start_network();node.start_server();node.impairment(1)
        direct_receipts.append(node.iperf_case(0,1,"direct","upload",20,4))
        if direct_receipts[0]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP" or (
            direct_receipts[0].get("receiver_goodput_mbps") or 0)<250:
            status="NOT_RUN_REAL_DIRECT_CAPACITY_INSUFFICIENT"
        else:
            for i,(label,streams) in enumerate(PHASES,1):
                burst=16 if label=="tbf16kb_fq_codel" else (
                      48 if label=="tbf48kb_fq_codel" else 0)
                # NO reader gate in any phase. The source scheduler must
                # preserve true original no-HOL first arrival by itself.
                os.environ["WBD_H2241_NATIVE_GATE"]="0"
                phase={"label":label,"true_tcp_streams":streams,
                       "test_only_tbf_burst_kib":burst,
                       "original_reader_no_gate":True}
                phase_results.append(phase)
                node.start_client(1)
                try:
                    if burst:
                        phase["source_fair_kernel_setup"]=install_owned_tun_aggregate_burst_fair(node,burst)
                    else:
                        q=L.ns(node.client,"tc","-d","qdisc","show","dev","wbdc0").stdout
                        if "qdisc fq " not in q or "maxrate 600Mbit" not in q:
                            raise RuntimeError("H2243_ORIGINAL_FQ600_RESTORE_FAILED")
                    phase["owned_tun_before"]=tun_kernel_snapshot(node)
                    phase["case"]=node.iperf_case(
                        i,1,"wbd","upload",20,streams)
                    phase["owned_tun_after"]=tun_kernel_snapshot(node)
                    phase["kernel_qdisc_and_driver_delta"]=source_kernel_qdisc_receipt(
                        phase["owned_tun_before"],phase["owned_tun_after"],
                        "tbf" if burst else "original")
                    raw=node.clientlog.read_text(errors="replace")
                    diag,buckets=scoped_diagnostic(raw,phase["case"],label)
                    phase["temporal_cause_receipt"]=diag
                    L.save(out/(label+"-timeline.json"),buckets)
                finally:
                    if node.owned_pid("client") is not None:
                        phase["client_owned_stop"]=node.stop_client(1)
                        node.procs["client"].wait(timeout=15)
                    phase["gate_stop"]=gate_stop_receipt(
                        node.clientlog.read_text(errors="replace"),False)
                    prev=out/"loss1-client.log"
                    if prev.is_file():shutil.copyfile(prev,out/(label+"-client.log"))
                if phase["case"]["status"]!="PASS_REAL_KERNEL_IPERF3_TCP":
                    status="FAIL_ORIGINAL_TCP_APPLICATION";break
            if len(phase_results)==4 and status=="NOT_RUN":
                direct_receipts.append(rearm_direct_capacity_listener(node))
                direct_receipts.append(node.iperf_case(5,1,"direct","upload",20,4))
                status=("PASS_GENUINE_H2243_TBF_FAIR_BURST_ABCA_DIAGNOSTIC_ONLY"
                    if direct_receipts[-1]["status"]=="PASS_REAL_KERNEL_IPERF3_TCP"
                    else "FAIL_FINAL_REAL_DIRECT_REFERENCE")
    except Exception as e:
        error=type(e).__name__+": "+str(e)[:400]
        status="FAIL_FIRST_TRUE_SOURCE_EVENT"
    finally:
        if node.serverlog.exists() and node.owned_pid("server") is not None:
            try:server_stop=node.stop_server()
            except Exception as e:
                if not error:error="SERVER_STOP_"+type(e).__name__+": "+str(e)[:250]
        node.cleanup()
        if status.startswith("PASS") and not server_stop:
            status="FAIL_ORIGINAL_SERVER_OWNED_STOP"
        L.save(out/"summary.json",{
            "schema_version":1,"checkpoint":"H2243_TRUE_TBF_FAIR_BATCH_NATIVE_SERVICE_ABCA",
            "source_sha":source,"run_id":runid,
            "topology":"SAME_VM_THREE_GENUINE_LINUX_NETNS_ORIGINAL_GO_TLS_RUST",
            "real_independent_WAN":False,"actual_arch":os.uname().machine,
            "model":"true_kernel_GE1pct_extra_oneway_200ms_unseeded",
            "same_GE_parameters_not_identical_packet_loss":True,
            "status":status,"error":error,
            "direct_real_before_after":direct_receipts,
            "phases":phase_results,
            "server_owned_stop_verified":server_stop,
            "not_product_optimization":True,
            "candidate_only_cold_opt_in":True,
            "test_only_aggregate_cap_mbps":TBF_RATE_MBIT,
            "test_only_bursts_kib":[16,48],
            "kernel_tbf_fq_codel_fairness_with_bounded_token_burst":True,
            "product_default_original_per_flow_fq600_unchanged":True,
            "original_kernel_tun_tx_ring_2048_unchanged":True,
            "no_second_owner_or_cross_route_pause":True,
            "immutable_no_hol_out_of_order_delivery":True,
            "all_original_queue_and_outer_repair_budgets_unchanged":True
        })
    if status!="PASS_GENUINE_H2243_TBF_FAIR_BURST_ABCA_DIAGNOSTIC_ONLY":
        raise RuntimeError("H2243_"+status+" "+str(error or ""))
    print("H2243_TRUE_NATIVE_AGGREGATE_BURST_FQCODEL_BATCH_DIAGNOSTIC_ONLY")

if __name__=="__main__":main()
