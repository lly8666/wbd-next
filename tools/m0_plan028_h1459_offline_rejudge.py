#!/usr/bin/env python3
"""Rejudge immutable SOURCE548/6c5 original native stress artifacts OFFLINE."""
import argparse,json,pathlib

SOURCE="548a47cc708d82d45e1722540b6677342f3c8c5b"
HISTORIC="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
ROLES=("server","alice","bob","carol","dave","erin")
STOP="V4_PUBLIC_SHARED_TUN_STOP generation="

def read(p):
    return json.loads(p.read_text())

def classify_zero_loss(missing,overflow,original,stable):
    if missing or overflow:
        return "FAIL_SCOPED_ZEROLOSS_UDP_MISSING_OR_SERVER_LEASE_QUEUE_OVERFLOW"
    if not stable or original.startswith("FAIL"):
        return "FAIL_OR_INCONCLUSIVE_BUSINESS_STABILITY"
    if original.startswith(("PASS_SCOPED","CAPACITY_LIMITED","HOST_NEAR_LIMIT")):
        return original
    return "NOT_QUALIFIED_UNKNOWN_VERDICT"

def inspect(root,scene,source,historic=False):
    plan=read(root/"h1250-matrix-plan.json")
    rapid=read(root/"h1286-rapid-report.json")
    assert plan["source_sha"]==rapid["source_sha"]==source
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert plan["application_load_seconds"]==180 and len(plan["clients"])==5
    assert set(rapid["clients"])==set(ROLES)-{"server"}
    for role in ROLES:
        p=root/("h1250-product-"+role+".log")
        assert p.exists() and STOP in p.read_text(errors="replace"),role
    lease=rapid["server_per_authenticated_lease_tun"]
    overflow=sum(int(v.get("pending_overflow",0)) for v in lease.values())
    queue_short=sum(v["offered"]-v["direct_delivered"] for v in lease.values())
    missing={}
    for who in ROLES[1:]:
        for direction in ("uplink","downlink"):
            bins=rapid["clients"][who]["directions"][direction]["phases"]
            missing[who+"_"+direction]=sum(int(p["actual_udp_sent"])-int(p["unique_udp_delivered"]) for p in bins)
    total=sum(missing.values())
    if scene=="weaknet30":
        assert [p["loss_pct"] for p in plan["clients"]]==[0,1,5,15,30]
        assert (root/"h1312-static-neighbour-installed.json").exists()
        assert (root/"h1312-static-neighbour-after.json").exists()
        q=rapid["actual_physical_qdisc"]["erin"]
        loss={d:q[d]["observed_physical_drop_fraction"] for d in ("uplink","downlink")}
        assert all(.25 < x < .35 for x in loss.values())
        original="h1286_weaknet_diagnostic"
        verdict=("PASS_SCOPED_180S_MIXED_0_TO30PCT_REAL_NETEM" if rapid["alert_count"]==0
                 else "INCONCLUSIVE_WEAKNET_ALERTS")
        phases=[]
    else:
        name=("h1360-l2-zero-loss.json" if scene=="normal75" else "h1349-l2-game4-zero-loss.json") if historic else "h1458-capacity-audit.json"
        a=read(root/name)
        assert a["original_product_source_sha"]==source
        assert a["measurement_complete"] and a["auth_user_count"]==5
        assert a["server_exact_final_stop"] and a["all_five_exact_final_client_stop"]
        original=a["classification"]
        verdict=classify_zero_loss(total,overflow,original,a["real_business_stability_pass"])
        loss=None
        focus="dave" if scene=="game4fec20" else "alice"
        phases=[{"stage":r["phase"],"host_busy_pct":r["host_busy_mean_pct"],
                 "max_core_busy_pct":max(r["host_per_core_busy_mean_pct"].values()),
                 "measured_focused_client_Mbps":r["clients"][focus]["uplink"]["actual_total_app_offered_mbps"],
                 "measured_focused_delivered_Mbps":r["clients"][focus]["uplink"]["actual_total_app_delivered_mbps"]}
                for r in a["phases"]]
    return {"source_sha":source,"scene":scene,
            "original_capacity_verdict":original,"strict_scoped_verdict":verdict,
            "udp_missing_by_client_direction":missing,"udp_missing_total":total,
            "server_lease_queue_overflow":overflow,"server_offered_minus_direct_delivered":queue_short,
            "all_six_original_owned_Stops":True,"measured_load_phases":phases,
            "erin_actual_physical_loss_fraction":loss,"rapid_alerts":rapid["alerts"],
            "scope":"original Go TLS443 Rust TUN five clients Linux x86_64 180s, not Windows"}

def rejudge(root,repo):
    current={s:inspect(root/s,s,SOURCE) for s in ("normal50","normal75","game4fec20","weaknet30")}
    old75=inspect(root/"old-normal75","normal75",HISTORIC,True)
    oldGame=inspect(root/"old-game4","game4fec20",HISTORIC,True)
    assert current["normal75"]["udp_missing_total"]==28
    assert current["normal75"]["server_lease_queue_overflow"]==5
    assert current["normal75"]["strict_scoped_verdict"].startswith("FAIL_SCOPED")
    for case in ("normal50","game4fec20"):
        assert current[case]["udp_missing_total"]==current[case]["server_lease_queue_overflow"]==0
        assert current[case]["strict_scoped_verdict"].startswith("PASS_SCOPED")
    assert current["weaknet30"]["strict_scoped_verdict"].startswith("PASS_SCOPED")
    assert old75["udp_missing_total"]==old75["server_lease_queue_overflow"]==0
    flow=(repo/".github/workflows/m0-plan028-h1349-x86-game4-fixed6-zero-loss-capacity.yml").read_text()
    assert "PASS_SCOPED_0LOSS_GAME4_FIXED6_3_5_10_5_WITH_FIVE_SIBLINGS" in flow
    assert oldGame["original_capacity_verdict"]=="PASS_SCOPED_0LOSS_GAME4_FIXED6_3_5_10_20_10_WITH_FIVE_SIBLINGS"
    return {"schema_version":1,"plan":"PLAN028","rejudge":"H1459_SOURCE_LOCKED_OFFLINE_REAL_ARTIFACTS",
            "current_product_source":SOURCE,"wrapper_artifact_source":"e2e82a846f55b7dddd7e30c9dcbcc6b54c3c6b49",
            "current_action_id":42567898270,"current":current,
            "historical_normal75_source":HISTORIC,"historical_normal75":old75,
            "historical_game4":oldGame,"historical_game4_action_id":42567898293,
            "historical_game4_action_conclusion":"FAILURE_RETAINED",
            "historical_game4_failure":"HARNESS_STALE_10MBPS_ENUM_WHEN_ORIGINAL_APP_20MBPS_PASS_SCOPED",
            "normal75_root":"UNKNOWN_PRODUCT_QUEUE_OR_VM_CAPACITY_AT_90PCT_CPU",
            "no_cross_VM_CPU_performance_comparison":True,
            "official_windows_1800_l3":"NOT_QUALIFIED",
            "original_network_rerun":"NONE"}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--root",type=pathlib.Path,required=True)
    a.add_argument("--repo",type=pathlib.Path,default=pathlib.Path("."))
    a.add_argument("--out",type=pathlib.Path,required=True)
    v=a.parse_args()
    r=rejudge(v.root,v.repo)
    v.out.parent.mkdir(parents=True,exist_ok=True)
    v.out.write_text(json.dumps(r,indent=2)+"\n")
    for scene,data in r["current"].items():
        print("H1459_IMMUTABLE_NATIVE_STRESS_REJUDGE",scene,data["strict_scoped_verdict"],
              "missing="+str(data["udp_missing_total"]),"overflow="+str(data["server_lease_queue_overflow"]),flush=True)
    print("H1459_HISTORIC_GAME4_CI_FAIL_IS_STALE_ENUM_NOT_REAL_APP_FAIL",flush=True)
    print("H1459_OFFLINE_COMPLETE_PRESERVE_REAL_ZEROLOSS_75_FAILURE",flush=True)
if __name__=="__main__":
    main()
