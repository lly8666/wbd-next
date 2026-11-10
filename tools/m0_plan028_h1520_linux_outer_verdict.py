#!/usr/bin/env python3
"""H1520 native Linux six-netns 600s high outer throughput evidence verdict.

One real TCP443 server, five real Go TLS/Rust/TUN owners, UDP and TCP.
100-150 Mbps means actual kernel outer bytes BOTH directions combined,
never logical business target, planned FEC or loopback UDP.
"""
import argparse,json,pathlib
NAMES=("alice","bob","carol","dave","erin")
def read(p):return json.loads(p.read_text())
def verdict(art,scene,source,wrapper):
    assert scene in ("loss0","loss30") and len(source)==len(wrapper)==40 and source!=wrapper
    plan=read(art/"h1250-matrix-plan.json")
    full=read(art/"h1461-six-hundred-report.json")
    observer=read(art/"h1520-outer-observer.json")
    samples=[json.loads(x) for x in (art/"h1520-outer-10s.jsonl").read_text().splitlines() if x.strip()]
    loss=0 if scene=="loss0" else 30
    assert plan["source_sha"]==full["source_sha"]==observer["original_product_source_sha"]==source
    assert plan["H1520_outer_600_profile"]=="outer100to150-"+scene
    assert plan["application_load_seconds"]==full["duration_seconds"]==600
    assert [v["c2s_target_mbps"] for v in plan["clients"]]==[12,8,6,3,6]
    assert [v["s2c_target_mbps"] for v in plan["clients"]]==[12,8,6,3,6]
    assert [v["oneway_delay_ms"] for v in plan["clients"]]==[200]*5
    assert [v["loss_pct"] for v in plan["clients"]]==[loss]*5
    assert plan["server_port"]==full["server_single_port"]==443
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    errors=[]
    if observer["status"]!="MEASURED_REAL_KERNEL" or len(samples)<48:
        errors.append("INSUFFICIENT_ACTUAL_KERNEL_OUTER_10S_MEASUREMENT")
    stable=[x for x in samples if x["phase"] in ("sustained","recovery")
            and x["sample_seconds"]>=8]
    within=[x for x in stable if 100<=x["total_outer_mbps"]<=150]
    mean=round(sum(x["total_outer_mbps"] for x in stable)/len(stable),3) if stable else None
    qualify=(len(stable)>=28 and len(within)>=int(.7*len(stable)) and
             mean is not None and 100<=mean<=150)
    if not qualify:errors.append("KERNEL_OUTER_100_150_MBPS_NOT_PROVEN")
    if not any(x["up_mbps"]>20 and x["down_mbps"]>20 for x in stable):
        errors.append("REAL_OUTER_BOTH_DIRECTIONS_NOT_PROVEN")
    total_drops={"up":[0]*5,"down":[0]*5}
    for x in samples:
        for side in ("up","down"):
            for i,v in enumerate(x["qdisc_drops_delta"][side]):total_drops[side][i]+=v
    if loss==30 and any(v<=0 for side in total_drops.values() for v in side):
        errors.append("30PCT_PHYSICAL_KERNEL_DROPS_NOT_TRIGGERED_ALL_TEN_LEGS")
    if loss==0 and any(v>0 for side in total_drops.values() for v in side):
        errors.append("ZERO_CONFIGURED_LOSS_KERNEL_QDISC_DROP")
    stop={}
    for role in ("server",)+NAMES:
        p=art/("h1250-product-"+role+".log")
        stop[role]=p.is_file() and "V4_PUBLIC_SHARED_TUN_STOP generation=" in p.read_text(errors="replace")
    if not all(stop.values()):errors.append("ORIGINAL_PER_OWNER_STOP_INCOMPLETE")
    if full.get("rotation_verdict")!="PASS_ALL_FIVE_SCOPED":
        errors.append("BOTH_SIDES_ACTUAL_M4_ROTATION_NOT_PROVEN")
    queue=full.get("server_per_authenticated_lease_tun",{})
    pending=sum(int(v.get("pending_overflow") or 0) for v in queue.values())
    if len(queue)!=5:errors.append("FIVE_SERVER_OWNED_LEASE_QUEUE_RECEIPTS_MISSING")
    if loss==0 and pending:errors.append("ZERO_LOSS_SERVER_QUEUE_OVERFLOW_"+str(pending))
    progress=[]
    for who in NAMES:
        client=full["clients"][who]
        if client["rotation"]["result"]!="PASS_SCOPED":
            errors.append(who+"_GENERATION_M4_OR_OWNED_STOP_FAIL")
        for direction in ("uplink","downlink"):
            leg=client["directions"][direction]
            sent=sum(int(p["actual_udp_sent"]) for p in leg["phases"])
            got=sum(int(p["unique_udp_delivered"]) for p in leg["phases"])
            gap=leg["largest_10ms_bucket_no_receive_while_sender_active_ms"]
            tcp=leg["true_tcp"]
            progress.append({"name":who,"direction":direction,"udp_sent":sent,
                "udp_unique_received":got,"udp_delivery_ratio":round(got/sent,4) if sent else None,
                "max_active_udp_gap_ms":gap,
                "real_framed_tcp_sent":tcp["framed_app_sent"],
                "real_framed_tcp_received":tcp["framed_app_received"]})
            if sent==0 or got==0:errors.append(who+"_"+direction+"_NO_NATIVE_UDP")
            if loss==0 and got!=sent:errors.append(who+"_"+direction+"_ZEROLOSS_BUSINESS_MISSING")
            if loss==30 and sent and got/sent<.4:errors.append(who+"_"+direction+"_30PCT_BUSINESS_COLLAPSE")
            if gap>=(1200 if loss==0 else 3000):
                errors.append(who+"_"+direction+"_ACTIVE_SECOND_SCALE_BLACKOUT_"+str(gap))
            if who in ("alice","bob") and (tcp["framed_app_sent"]==0 or tcp["framed_app_received"]==0):
                errors.append(who+"_"+direction+"_REAL_TCP_NOT_DELIVERED")
    severe=[a for a in full.get("alerts",[]) if a.get("kind") in (
       "CLIENT_NORMAL_READY_WITHOUT_SERVER_NATIVE_M4",
       "CLIENT_GAME2_READY_WITHOUT_SERVER_NATIVE_COHORT",
       "APP_RX_GAP_WITH_ACTIVE_TX_GE750MS",
       "MINUTE_LEVEL_APP_RX_STARVATION",
       "NO_ORIGINAL_TLS_SERVER_PORT_READY")]
    if severe:errors.append("ORIGINAL_REPORT_SEVERE_EVIDENCE_ALERTS_"+str(len(severe)))
    status=("PASS_SCOPED_NATIVE_LINUX_FIVE_600S_100_150_OUTER_200MS_"+scene.upper()
            if not errors else
            "CAPACITY_OR_PRODUCT_OR_MEASUREMENT_LIMITED_NOT_PASS")
    result={"schema_version":1,"plan":"PLAN028","scene":scene,
      "status":status,"frozen_original_product_source":source,"wrapper_source":wrapper,
      "architecture":"native Linux x86_64 both ends, six netns, same VM",
      "actual_kernel_full_outer_total_both_direction_mbps":{
       "target_min":100,"target_max":150,"steady_mean_mbps":mean,
       "steady_window_count":len(stable),"within_target_window_count":len(within),
       "within_target_fraction":round(len(within)/len(stable),4) if stable else None,
       "lowest":min((x["total_outer_mbps"] for x in stable),default=None),
       "highest":max((x["total_outer_mbps"] for x in stable),default=None)},
      "real_physical_oneway_delay_ms":200,"loss_pct_both_egress_directions":loss,
      "actual_qdisc_drop_counts":total_drops,"actual_unique_business":progress,
      "original_all_six_owned_stops":stop,"server_per_lease_pending_overflow":pending,
      "original_rotation_verdict":full.get("rotation_verdict"),
      "original_report_alerts":full.get("alerts",[]),
      "hard_errors":errors,"claims_not_made":["Windows Wintun","physical WAN",
        "true OS physical source-IP flip on Linux (timed TLS rotations instead)",
        "FEC appearance copy as business recovery","Android","cross-VM latency"]}
    (art/"h1520-verdict.json").write_text(json.dumps(result,indent=2)+"\n")
    print("H1520_LINUX_ACTUAL_OUTER_VERDICT "+json.dumps(
        {"status":status,"mean_mbps":mean,"stable_windows":len(stable),
         "within":len(within),"faults":errors}),flush=True)
    if errors:raise RuntimeError("H1520 real native Linux scoped not qualified; inspect original artifacts")
    return result
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",type=pathlib.Path,required=True)
    p.add_argument("--scene",choices=("loss0","loss30"),required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--wrapper",required=True)
    a=p.parse_args();verdict(a.art,a.scene,a.source,a.wrapper)
if __name__=="__main__":main()
