"""Plan029: scoped same-VM, same-Rust-V3 split-policy ABBA CPU comparison.

A=Rust V3 route-mode all; B=Rust V3 bypass-lan-cn, but BOTH send
all matched original two-OS application load over the SAME Tunnel.
Never conflate this with old V4-vs-V3 or physical-TCP-vs-Direct CPU.
"""
from math import isfinite
from statistics import mean

ORDER=("A1_all","B1_cn","B2_cn","A2_all")
MODES=("all","bypass-lan-cn","bypass-lan-cn","all")
SUCCESS="PASS_SCOPED_P1_SAME_RUST_V3_POLICY_ABBA_MEASURED"

def score(legs,source):
    if not (isinstance(source,str) and len(source)==40 and len(legs)==4 and
            [x["name"] for x in legs]==list(ORDER) and
            [x["route_mode"] for x in legs]==list(MODES)):
        raise ValueError("not source-locked four-leg A-B-B-A")
    if not all(x.get("source_sha")==source and x.get("result")=="PASS" and
               x.get("split_trial") is True and
               x.get("owned_stop")=="PASS_BOTH_OWNED" and
               x.get("app_target")=="203.0.113.77" and
               x.get("linux_alias_os_owned") is True for x in legs):
        raise ValueError("SOURCE, owner, route or actual Tunnel alias mismatch")
    for key in ("windows_cli_sha256","linux_server_sha256"):
        values={x.get(key) for x in legs}
        if len(values)!=1 or None in values or "" in values:
            raise ValueError("same original binary SHA not proven")
    ratios=[];deliveries=[];tcp=[];rtt=[]
    for leg in legs:
        used=leg["windows_cpu"]["cpu_total_s"]
        received=leg["actual_delivered_gib"]
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or
               not isfinite(x) or x<=0 for x in (used,received)):
            raise ValueError("bad measured CPU or delivery")
        for side in ("windows","linux"):
            app=leg["applications"][side]
            if (app["actual_delivered_mbps"]<47.5 or
                app["rtt_probe_replies"]<200 or
                not isfinite(app["udp_rtt_p99_ms"])):
                raise ValueError("not matched two-OS 50Mbps/UDP p99")
        if (leg.get("rust_thread_cpu",{}).get("rust_combined_cpu_s_lower_bound",0)<=0 or
            leg.get("rust_thread_cpu",{}).get("samples",0)<45):
            raise ValueError("missing original Rust TX/RX Win32 TID CPU")
        ratios.append(used/received)
        deliveries.append(received)
        rtt.append(leg["applications"]["windows"]["udp_rtt_p99_ms"])
    a=mean((ratios[0],ratios[3]))
    b=mean((ratios[1],ratios[2]))
    drift_a=100*abs(ratios[3]-ratios[0])/a
    drift_b=100*abs(ratios[2]-ratios[1])/b
    difference=100*(b/a-1)
    spread=100*(max(deliveries)/min(deliveries)-1)
    noise=max(5.0,drift_a,drift_b)
    return {
        "source_sha":source,"order":list(ORDER),"route_modes":list(MODES),
        "scope":"ONE_WIN_VM_ORIGINAL_RUST_V3_POLICY_ABBA_SAME_TUNNEL_NO_DIRECT_FLOW",
        "per_leg_cpu_s_per_delivered_gib":[round(x,5) for x in ratios],
        "A_all_mean_cpu_s_per_gib":round(a,5),
        "B_cn_mean_cpu_s_per_gib":round(b,5),
        "B_minus_A_cpu_s_per_gib":round(b-a,5),
        "B_over_A_cpu_pct":round(difference,3),
        "A_drift_pct":round(drift_a,3),
        "B_repeat_spread_pct":round(drift_b,3),
        "delivered_gib_spread_pct":round(spread,3),
        "per_leg_windows_udp_p99_ms":rtt,
        "traffic_comparable":spread<=3,
        "cpu_interpretation":("INCONCLUSIVE_UNMATCHED_GOODPUT" if spread>3
            else "POTENTIAL_REGRESSION_NEEDS_REPLICATION" if difference>noise
            else "NO_PROVEN_REGRESSION_WITHIN_ABBA_NOISE"),
        "excluded_claims":[
          "A_STILL_HAS_ORIGINAL_RUST_TUNNEL_TX_RX",
          "B_INCLUDE_RULESET_STATE_AND_CLASSIFIER_NOT_PURE_INSTRUCTION_COST",
          "THIS_IS_NOT_WINDOWS_PHYSICAL_TCP_VS_DIRECT_KERNEL_BRIDGE_COST",
          "NO_DRIVER_ISR_DPC_OR_WSL_CPU_ACCOUNTED",
          "NOT_A_STATISTICALLY_SIGNIFICANT_CAUSAL_CPU_CLAIM_WITH_ONLY_FOUR_LEGS",
          "P99_NOT_PAIRWISE_SUBTRACTABLE",
        ],
    }
