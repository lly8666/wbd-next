#!/usr/bin/env python3
"""One original five-client native 180s PLAN028 stress verdict, scoped by SOURCE.

Do not infer a Mbps PASS from a target, a green job, or an alerted weaknet.
"""
import argparse
import json
from pathlib import Path

SCENES={
    "normal50":{"stages_mbps":[10,25,50,25],"kind":"normal"},
    "normal75":{"stages_mbps":[25,50,75,50],"kind":"normal"},
    "game4fec20":{"stages_mbps":[3,5,10,20,10],"kind":"game4"},
    "weaknet30":{"loss_pct":[0,1,5,15,30],"kind":"heterogeneous"}
}
ROLES=("alice","bob","carol","dave","erin")
STOP="V4_PUBLIC_SHARED_TUN_STOP generation="

def read(p):
    return json.loads(Path(p).read_text())

def verdict(scene,root,source,wrapper):
    assert scene in SCENES and len(source)==len(wrapper)==40 and source!=wrapper
    plan=read(root/"h1250-matrix-plan.json")
    rapid=read(root/"h1286-rapid-report.json")
    assert plan["source_sha"]==rapid["source_sha"]==source
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert plan["application_load_seconds"]==rapid["duration_seconds"]==180
    assert plan["simultaneous_stress_seconds"]==170
    assert plan["fast_scene"]=="pressure" and len(plan["clients"])==5
    assert set(rapid["clients"])==set(ROLES)
    stopped={}
    for role in ("server",)+ROLES:
        p=root/("h1250-product-"+role+".log")
        stopped[role]=p.exists() and STOP in p.read_text(errors="replace")
    assert all(stopped.values()),("Missing original Go/Rust owned final Stop",stopped)
    measured=[]
    hard=[]
    for who in ROLES:
        client=rapid["clients"][who]
        for direction in ("uplink","downlink"):
            leg=client["directions"][direction]
            phases=leg["phases"]
            sent=sum(int(x["actual_udp_sent"]) for x in phases)
            got=sum(int(x["unique_udp_delivered"]) for x in phases)
            measured.append({"who":who,"direction":direction,
                             "actual_sent_udp_packets":sent,"actual_received_udp_packets":got,
                             "actual_ratio":round(got/sent,5) if sent else None,
                             "max_active_tx_no_rx_gap_ms":leg["largest_10ms_bucket_no_receive_while_sender_active_ms"]})
            if sent<=0 or got<=0:hard.append(who+" "+direction+" NO_GENUINE_UDP")
    if scene=="weaknet30":
        configured=[int(v["loss_pct"]) for v in plan["clients"]]
        assert configured==SCENES[scene]["loss_pct"],configured
        assert all(int(rapid["clients"][who]["configured_loss_pct"])==configured[i]
                   for i,who in enumerate(ROLES))
        assert (root/"h1312-static-neighbour-installed.json").is_file()
        assert (root/"h1312-static-neighbour-after.json").is_file()
        classification=("FAIL_REAL_BUSINESS_OR_OWNED_STOP" if hard else
                        "INCONCLUSIVE_WEAKNET_ALERTS_PRESENT" if rapid["alert_count"] else
                        "PASS_SCOPED_X86_180S_MIXED_0_TO_30PCT_NETEM")
        capacity=None
    else:
        a=read(root/"h1458-capacity-audit.json")
        assert a["measurement_complete"] and a["auth_user_count"]==5
        assert a["original_product_source_sha"]==source
        assert a["server_exact_final_stop"] and a["all_five_exact_final_client_stop"]
        assert (a["game4_physical_loss_percent"]==0 if scene=="game4fec20"
                else a["normal_physical_loss_percent"]==0)
        assert len(a["phases"])==(5 if scene=="game4fec20" else 4)
        classification=a["classification"]
        if not a["real_business_stability_pass"]:
            hard.append("ZERO_LOSS_PRODUCT_OR_HOST_APP_GAP_NOT_CAPACITY_ATTRIBUTED")
        capacity={"classification":classification,
                  "stable":a["real_business_stability_pass"],
                  "phases":[{"name":phase["phase"],"host_busy_pct":phase["host_busy_mean_pct"],
                             "observed_actual_offered_mbps":phase.get("total_actual_offered_mbps_one_direction")}
                            for phase in a["phases"]]}
    result={
        "schema_version":1,"test":"PLAN028_H1458_TRUE_FIVE_CLIENT_LINUX_X86_STRESS",
        "immutable_product_source_sha":source,"wrapper_source_sha":wrapper,
        "scene":scene,"configured":SCENES[scene],
        "real_original_TLS443_and_Rust_TUN":True,"independent_six_linux_netns":True,
        "qualification_scope":"x86_64 Linux only, 180 seconds, no Windows Wintun 1800s",
        "duration_s":180,"actual_udp":measured,"original_six_owned_final_Stops":stopped,
        "capacity":capacity,"rapid_alert_count":rapid["alert_count"],
        "rapid_alerts":rapid["alerts"],"classification":classification,
        "hard_faults":hard,
        "cannot_claim":["Windows Wintun 1800s","physical WAN/Android",
                        "cross-VM CPU speedup","100 PPS based on target Mbps"]
    }
    (root/"h1458-verdict.json").write_text(json.dumps(result,indent=2)+"\n")
    print("H1458_ACTUAL_NATIVE_FIVE_CLIENT_SCOPED_VERDICT",scene,classification,
          "warnings="+str(len(rapid["alerts"])),flush=True)
    if hard:
        raise RuntimeError("Original native app cannot be certified; see source-locked artifacts")
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scene",choices=sorted(SCENES),required=True)
    ap.add_argument("--art",type=Path,required=True)
    ap.add_argument("--product-source",required=True)
    ap.add_argument("--wrapper-source",required=True)
    a=ap.parse_args()
    verdict(a.scene,a.art,a.product_source,a.wrapper_source)
if __name__=="__main__":
    main()
