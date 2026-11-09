#!/usr/bin/env python3
"""H1461 exact SOURCE genuine five-client 600s/1800s original native verdict.

Only original Go TLS443/Rust M4, kernel TUN/UDP/TCP and owned Stop count.
Configured offered Mbps and green CI are never substituted for actual delivery.
"""
import argparse,json,pathlib,re

NAMES=("alice","bob","carol","dave","erin")
STOP="V4_PUBLIC_SHARED_TUN_STOP generation="

def read(p):
    return json.loads(p.read_text())

def report(art,duration,source,wrapper):
    assert duration in (600,1800) and len(source)==40 and len(wrapper)==40
    assert source==wrapper
    plan=read(art/"h1250-matrix-plan.json")
    path=art/("h1461-six-hundred-report.json" if duration==600 else "h1274-thirty-minute-report.json")
    full=read(path)
    assert plan["source_sha"]==full["source_sha"]==source
    assert plan["application_load_seconds"]==full["duration_seconds"]==duration
    assert plan["simultaneous_stress_seconds"]==duration-10
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert len(plan["clients"])==5 and set(full["clients"])==set(NAMES)
    assert plan["server_port"]==full["server_single_port"]==443
    if duration==600:
        assert plan["H1461_600s_capacity75_profile"]=="EXACT_600S_FIVE_CLIENT_ZEROLOSS_25_50_75_50_NO_ROTATION"
        assert plan["physical_l2_arp_control"]=="test_only_permanent_actual_peer_mac"
        assert [p["c2s_target_mbps"] for p in plan["clients"]]==[75,2,2,2,2]
        assert [p["loss_pct"] for p in plan["clients"]]==[0]*5
    else:
        assert plan["long_scene"]=="heterogeneous"
        assert [p["loss_pct"] for p in plan["clients"]]==[0,1,5,15,30]
    owned={}
    for role in ("server",)+NAMES:
        p=art/("h1250-product-"+role+".log")
        owned[role]=p.is_file() and STOP in p.read_text(errors="replace")
    errors=[]
    if not all(owned.values()):
        errors.append("MISSING_ORIGINAL_GO_RUST_SHARED_TUN_FINAL_STOP")
    server=(art/"h1250-product-server.log").read_text(errors="replace")
    overflow=[int(x) for x in re.findall(r"M0_SHARED_TUN_LEASE_QUEUE_DIAG [^\n]*?\bpending_overflow=(\d+)",server)]
    if len(overflow)!=5:
        errors.append("MISSING_PER_LEASE_TRUE_SERVER_QUEUE_DIAGNOSTIC")
    total_overflow=sum(overflow)
    if duration==600 and total_overflow:
        errors.append("ORIGINAL_SERVER_8_SLOT_QUEUE_OVERFLOW_"+str(total_overflow))
    actual=[]
    for who in NAMES:
        client=full["clients"][who]
        if client["rotation"]["result"]!="PASS_SCOPED":
            errors.append(who+"_M4_HANDOFF_OR_STABLE_AUTH_OR_STOP_UNQUALIFIED")
        cp=read(art/("h1250-c-"+who+".json"))
        sp=read(art/("h1250-s-"+who+".json"))
        if cp["role"]!="client" or sp["role"]!="server":
            errors.append(who+"_BAD_REAL_ORIGINAL_APP_ROLE")
        if cp["end_ns"]-cp["start_ns"]!=duration*1_000_000_000 or sp["end_ns"]-sp["start_ns"]!=duration*1_000_000_000:
            errors.append(who+"_REAL_APPLICATION_CLOCK_NOT_"+str(duration))
        for direction in ("uplink","downlink"):
            leg=client["directions"][direction]
            stages=leg["phases"]
            sent=sum(x["actual_udp_sent"] for x in stages)
            recv=sum(x["unique_udp_delivered"] for x in stages)
            if not sent or not recv:errors.append(who+"_"+direction+"_NO_GENUINE_UDP")
            if leg["largest_10ms_bucket_no_receive_while_sender_active_ms"]>=750:
                errors.append(who+"_"+direction+"_ACTIVE_GAP_GE750MS")
            if duration==600 and recv!=sent:
                errors.append(who+"_"+direction+"_ZERO_LOSS_MISSING_"+str(sent-recv))
            if duration==1800 and stages[-1]["actual_delivery_fraction"] is not None and stages[-1]["actual_delivery_fraction"]<.95:
                errors.append(who+"_"+direction+"_RECOVERY_BELOW95PCT")
            actual.append({"client":who,"direction":direction,
                           "actual_original_udp_sent":sent,"unique_udp_received":recv,
                           "missing":sent-recv,"maximum_active_gap_ms":leg["largest_10ms_bucket_no_receive_while_sender_active_ms"],
                           "phase_unique_udp_delivery":stages})
    alice=read(art/"h1250-c-alice.json")
    if duration==600:
        expected=[("warmup",10),("first_wave",90),("sustained",180),("overload",90),("recovery",230)]
        phases=alice["stats"]["udp"]
        tcp=alice["stats"]["tcp"]
        assert len(phases)==len(tcp)==len(expected)
        target=[25,50,75,50]
        observed=[]
        for i,(name,length) in enumerate(expected):
            if i==0:continue
            actual_mbps=(phases[i]["tx_bytes"]+tcp[i]["tx_bytes"])*8/(length*1e6)
            observed.append({"stage":name,"target_mbps":target[i-1],
                             "actual_offered_mbps":round(actual_mbps,4),
                             "delivery_source":"actual original traffic worker UDP+framed TCP bytes"})
        if any(x["actual_offered_mbps"]<.95*x["target_mbps"] for x in observed):
            errors.append("GENERATOR_OR_HOST_FAILED_TO_OFFER_95PCT")
    else:
        observed=None
    if errors:
        status="FAIL_SCOPED_OR_ENVIRONMENT_LIMITED_OR_INCOMPLETE"
    elif full["alert_count"] and duration==1800:
        status="INCONCLUSIVE_1800S_NATIVE_ALERTS_PRESENT"
    elif duration==600:
        status="PASS_SCOPED_ORIGINAL_5CLIENT_600S_75MBPS_ZEROLOSS_AND_STOP"
    else:
        status="PASS_SCOPED_ORIGINAL_5CLIENT_1800S_HETEROGENEOUS_AND_STOP"
    result={
        "schema_version":1,"source_sha":source,"wrapper_sha":wrapper,
        "duration_s":duration,"status":status,"original_five_clients":5,
        "single_original_TLS443_Rust_native_TUN":True,
        "windows_Wintun_L3_1800s":"NOT_QUALIFIED",
        "original_six_owned_final_stop":owned,
        "genuine_server_per_lease_overflow":overflow,
        "total_true_queue_overflow":total_overflow,
        "all_clients_original_application":actual,
        "alice_600_25_50_75_50_actual_offered_vs_targets":observed,
        "original_native_rotation_verdict":full["rotation_verdict"],
        "original_report_alert_count":full["alert_count"],
        "original_report_alerts":full["alerts"],
        "hard_faults":errors,
        "no_false_qualification":["green runner != product pass","configured speed != actual business",
                                 "600s capacity no L1 rotations", "Linux 1800s != Windows L3"]
    }
    (art/"h1461-native-verdict.json").write_text(json.dumps(result,indent=2)+"\n")
    print("H1461_FIVE_CLIENT_NATIVE_TRUE_DURATION_RESULT",json.dumps({
        "source_sha":source,"duration_s":duration,"status":status,
        "queue_overflow":total_overflow,"app_fault_count":len(errors),
        "report_alerts":full["alert_count"],
        "alice_offered":observed},sort_keys=True),flush=True)
    if errors:raise RuntimeError("H1461 original product or host capacity not qualified: "+repr(errors))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",type=pathlib.Path,required=True)
    p.add_argument("--duration",type=int,choices=(600,1800),required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--wrapper",required=True)
    a=p.parse_args()
    report(a.art,a.duration,a.source,a.wrapper)

if __name__=="__main__":
    main()
