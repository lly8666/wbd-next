#!/usr/bin/env python3
"""Source-locked conservative readout for PLAN029 ARM same-run A64-B256-A64.

The result is a *screen*, not product PASS. Never improve reported p99 by
discarding missing echoes, never compare CPU on different runners, never use
a shorter run to claim positive throughput causality.
"""
import argparse
import json
import math
import pathlib
import re

ORDER=(("original_before",64),("inbox256_candidate",256),("original_after",64))
KINDS=("udp","tcp")
ROLES=("server","client")

def positive(value,label):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        raise ValueError("not numeric: "+label)
    if not math.isfinite(value) or value<=0:
        raise ValueError("not positive finite: "+label)
    return float(value)

def compare_scalar(a,b,after):
    a,b,after=(positive(v,"paired") for v in (a,b,after))
    center=(a+after)/2
    return {"original_before":round(a,5),"candidate":round(b,5),
            "original_after":round(after,5),
            "baseline_center":round(center,5),
            "baseline_drift_pct":round(100*(after-a)/center,3),
            "candidate_delta_to_center_pct":round(100*(b-center)/center,3),
            "candidate_vs_baselines":
              ("ABOVE_BOTH" if b>max(a,after) else
               "BELOW_BOTH" if b<min(a,after) else "INSIDE_BASELINE_RANGE")}

def readout(document,source,run_id):
    if (document.get("status")!="PASS_SCOPED_REAL_ABA_MEASURED_NOT_PRODUCT_GAIN"
        or document.get("source_sha")!=source
        or str(document.get("run_id"))!=str(run_id)
        or document.get("architecture")!="aarch64"
        or re.fullmatch(r"[0-9a-f]{40}",source) is None):
        raise ValueError("original native A/B/A SOURCE, run or status missing")
    phases=document.get("phases")
    if not isinstance(phases,list) or len(phases)!=3:
        raise ValueError("three genuine owned phases required")
    bundle=document.get("old_and_new_same_build_manifest")
    if not isinstance(bundle,dict) or sorted(bundle)!=[
        "libwbd_engine.so","wbd-v4-client","wbd-v4-server"]:
        raise ValueError("original Go/Rust build manifest incomplete")
    # A client-only experiment must not be misclassified as a successful
    # server-only A/B. Require native cold readback of both actual endpoints.
    is_client=any("client_inbox_slots" in p for p in phases)
    changed_side="client" if is_client else "server"
    prior_end=None
    for idx,phase in enumerate(phases):
        if (phase.get("name")!=ORDER[idx][0]
            or phase.get("status")!="PASS_SCOPED_REAL_SOURCE_MEASURED_NOT_PRODUCT_GAIN"):
            raise ValueError("A/B/A source, order or phase identity mismatch")
        if is_client:
            if (phase.get("client_inbox_slots")!=ORDER[idx][1]
                or phase.get("server_inbox_slots")!=64
                or phase.get("native_cold_readback_verified") is not True
                or not isinstance(phase.get("client_generation"),int)
                or phase["client_generation"]<=0
                or not isinstance(phase.get("server_generation"),int)
                or phase["server_generation"]<=0):
                raise ValueError("client-only actual cold M1 slot / server control mismatch")
        elif phase.get("server_inbox_slots")!=ORDER[idx][1]:
            raise ValueError("server-only M1 slot identity mismatch")
        for role in ROLES:
            if positive(phase["owned_stop"][role].get("generation"),"owned stop")<1:
                raise ValueError("missing product owned Stop")
        flow=phase["measure"]["original_product_tcp"]
        if flow.get("tcp_streams")!=4:
            raise ValueError("not four real TCP streams")
        start=positive(flow.get("start_monotonic_ns"),"start")
        end=positive(flow.get("end_monotonic_ns"),"end")
        if start>=end or (prior_end is not None and start<=prior_end):
            raise ValueError("overlapping or unordered genuine A/B/A measurement clocks")
        prior_end=end
        small=phase["measure"]["smallflow"]
        if small.get("status")!="PASS_SCOPED_REAL_INNER_UDP_TCP_ECHO":
            raise ValueError("inner smallflow not genuinely delivered")
        if not (start<=positive(small.get("probe_start_monotonic_ns"),"small start")
                <positive(small.get("probe_end_monotonic_ns"),"small end")
                <=end+500000000):
            raise ValueError("inner smallflow not concurrent with bulk")
        for kind in KINDS:
            d=small[kind]
            sent=d.get("requests_sent")
            replies=d.get("unique_replies")
            missing=d.get("missing")
            if (not isinstance(sent,int) or sent<150 or
                not isinstance(replies,int) or replies<50 or
                not isinstance(missing,int) or missing!=sent-replies):
                raise ValueError("echo sent/delivered/missing counts invalid")
            if replies and not isinstance(d.get("latency_ms"),dict):
                raise ValueError("missing echo RTT quantiles")
    report={"source_sha":source,"run_id":str(run_id),
            "changed_inbox_side":changed_side,
            "status":"SAME_RUN_SCOPED_SCREEN_NOT_PRODUCT_PASS",
            "reference":"A64-B256-A64 on native ARM64; one 20s four-stream case per leg",
            "receiver_goodput_mbps":compare_scalar(*[
                p["measure"]["original_product_tcp"]["receiver_bps"]/1e6 for p in phases]),
            "sender_and_receiver_cpu_seconds_per_gib":{},
            "smallflow":{},
            "underlay_skb_counts":{},
            "qualifications":[]}
    for role in ROLES:
        report["sender_and_receiver_cpu_seconds_per_gib"][role]=compare_scalar(*[
            p["measure"]["cpu_and_rss"][role]["cpu_seconds_per_rx_gib"] for p in phases])
    for kind in KINDS:
        rows=[p["measure"]["smallflow"][kind] for p in phases]
        report["smallflow"][kind]={
            "offered":[p["requests_sent"] for p in rows],
            "unique_replies":[p["unique_replies"] for p in rows],
            "missing":[p["missing"] for p in rows],
            "survivor_only_p99_ms":[p["latency_ms"]["p99"] for p in rows],
            "missing_is_not_zero_latency":True,
            "deadline_delivery_qualification":"NOT_PROVEN_BY_THIS_SCREEN"}
    for dev in ("rcli0","rsrv0"):
        rows=[p["measure"]["router_kernel_skb"][dev] for p in phases]
        report["underlay_skb_counts"][dev]={
            "netem_skb_emitted":[r.get("netem_skb_emitted_delta") for r in rows],
            "netem_skb_drops":[r.get("netem_skb_drop_delta") for r in rows],
            "kernel_unit":"skb, may cover multiple IP segments"}
    g=report["receiver_goodput_mbps"]
    client=report["sender_and_receiver_cpu_seconds_per_gib"]["client"]
    server=report["sender_and_receiver_cpu_seconds_per_gib"]["server"]
    report["qualifications"].extend([
        "No native shared-TUN fairness benefit inferred: only one authenticated /32 in the scene",
        "Cannot call candidate useful if it only moves full drops to kernel or lowers goodput",
        "No cross-run or cross-ISA CPU causality; avoid unqualified physical WAN extrapolation",
        "No hard default promotion on one 20-second three-leg screen",
        "1000B at 1Gbps: 64 M1 slots 0.512ms, 256 slots 2.048ms; all 256 jumbo slots ~16MiB total, ~12MiB added per lease"])
    report["screen_decision"]=(
        "BETTER_GOODPUT_OUTSIDE_BASELINE_BUT_NOT_ACCEPTED" if
          g["candidate_vs_baselines"]=="ABOVE_BOTH" and
          all(x["candidate_vs_baselines"]!="ABOVE_BOTH" for x in (client,server))
        else "WORSE_GOODPUT_OUTSIDE_BASELINE" if
          g["candidate_vs_baselines"]=="BELOW_BOTH"
        else "INCONCLUSIVE_OR_COST_TRADEOFF")
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--summary",type=pathlib.Path,required=True)
    parser.add_argument("--output",type=pathlib.Path,required=True)
    parser.add_argument("--source",required=True)
    parser.add_argument("--run-id",required=True)
    args=parser.parse_args()
    src=json.loads(args.summary.read_text())
    report=readout(src,args.source,args.run_id)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("M029_ARM_ABA_CONSERVATIVE_READOUT "+report["screen_decision"],flush=True)

if __name__=="__main__":main()
