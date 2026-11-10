#!/usr/bin/env python3
"""H1524 offline-only first-fault replay from immutable native H1520 result ZIPs.

No packet generation, no network rerun and no product readiness inference from
a reporter check. Preserve original Action status separately.
"""
import argparse,json,pathlib,re

NAMES=("alice","bob","carol","dave","erin")
def read(p):return json.loads(p.read_text())
def num(text,needle):return text.count(needle)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",type=pathlib.Path,required=True)
    p.add_argument("--scene",choices=("loss0","loss30"),required=True)
    p.add_argument("--original-product-source",required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    art=a.art
    plan=read(art/"h1250-matrix-plan.json")
    original=read(art/"h1461-six-hundred-report.json")
    observer=read(art/"h1520-outer-observer.json")
    full=read(art/"h1520-verdict.json")
    samples=[json.loads(x) for x in (art/"h1520-outer-10s.jsonl").read_text().splitlines() if x.strip()]
    assert plan["source_sha"]==original["source_sha"]==a.original_product_source
    assert full["frozen_original_product_source"]==a.original_product_source
    assert plan["H1520_outer_600_profile"]=="outer100to150-"+a.scene
    assert original["duration_seconds"]==600
    server=(art/"h1250-product-server.log").read_text(errors="replace")
    roles={}
    for n in NAMES:
        log=(art/("h1250-product-"+n+".log")).read_text(errors="replace")
        o=original["clients"][n]
        detailed={}
        for marker in ("V4_PUBLIC_TIMER_ROTATION_DUE role=client",
                        "V4_PUBLIC_PATH_NEW_GENERATION_READY role=client",
                        "V4_PUBLIC_PATH_OLD_EXACT_STOP role=client",
                        "V4_PUBLIC_PATH_CANDIDATE_FAILED role=client",
                        "V4_PUBLIC_SHARED_TUN_STOP generation=",
                        "V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client",
                        "V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_READY role=client",
                        "V4_PUBLIC_LEASE_APPLIED role=client"):
            detailed[marker]=num(log,marker)
        path_events=[line.strip()[:400] for line in log.splitlines() if
            any(s in line for s in (
                "V4_PUBLIC_PATH_NEW_GENERATION_READY",
                "V4_PUBLIC_PATH_CANDIDATE_FAILED",
                "V4_PUBLIC_PATH_OLD_EXACT_STOP",
                "V4_PUBLIC_TIMER_ROTATION_DUE",
                "V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_READY"))]
        roles[n]={
          "mode":o["mode"],
          "rotation_report":o["rotation"],
          "original_lease":o["lease"],
          "counts":detailed,
          "last_12_path_events":path_events[-12:],
          "directions":{side:{
             "udp_offered":sum(int(s["actual_udp_sent"]) for s in leg["phases"]),
             "udp_first_received":sum(int(s["unique_udp_delivered"]) for s in leg["phases"]),
             "tcp_frames_sent":leg["true_tcp"]["framed_app_sent"],
             "tcp_frames_received":leg["true_tcp"]["framed_app_received"],
             "max_active_tx_no_rx_gap_ms":leg["largest_10ms_bucket_no_receive_while_sender_active_ms"],
             "phase_details":leg["phases"],
            } for side,leg in o["directions"].items()},
        }
    normal_server=[line.strip()[:500] for line in server.splitlines() if any(s in line for s in (
      "V4_PUBLIC_MIXED_NORMAL_READY role=server",
      "V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server",
      "V4_PUBLIC_MIXED_NORMAL_B_UNPROVEN",
      "V4_PUBLIC_MIXED_ADMISSION_REJECT",
      "V4_PUBLIC_GAME_GROUP_LANE_READY role=server",
      "V4_PUBLIC_GAME_SINGLE_LANE_READY role=server",
      "V4_PUBLIC_GAME_SERVER_B_UNPROVEN"
    ))]
    no_noise=[]; signals=("panic:","fatal error:","M0_SHARED_TUN_LEASE_QUEUE_DIAG","V4_PUBLIC_SHARED_TUN_STOP generation=")
    for line in server.splitlines():
        if any(s in line for s in signals):no_noise.append(line.strip()[:450])
    stable=[x for x in samples if x["phase"] in ("sustained","recovery") and x["sample_seconds"]>=8]
    result={
      "source_sha":a.original_product_source,"scene":a.scene,
      "original_report_result":original.get("result"),
      "original_report_rotations":original.get("rotation_verdict"),
      "original_report_alert_count":original.get("alert_count"),
      "original_report_alerts":original.get("alerts"),
      "h1520_original_hard_errors":full.get("hard_errors"),
      "business_and_rotations":roles,
      "server_m4_events_count":len(normal_server),
      "server_m4_first_12":normal_server[:12],
      "server_m4_last_40":normal_server[-40:],
      "server_stop_queue_crash_tail":no_noise[-25:],
      "original_stops":full["original_all_six_owned_stops"],
      "actual_kernel_outer_steady_mean":round(sum(x["total_outer_mbps"] for x in stable)/len(stable),4) if stable else None,
      "actual_kernel_outer_steady_windows":len(stable),
      "original_capacity_guard":(art/"h1520-host-10s-budget.jsonl").read_text().splitlines()[-5:],
      "classification":"OFFLINE_RAW_DIAGNOSTIC_ONLY_NO_NETWORK_NEW_PASS",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("H1524_OFFLINE_REAL_RAW_"+a.scene.upper()+" "+json.dumps({
       "outer_mbps":result["actual_kernel_outer_steady_mean"],
       "alerts":result["original_report_alerts"],
       "normal_m4_server_log_events":len(normal_server),
       "rotation_per_client":{n:{
         "result":row["rotation_report"].get("result"),
         "READY":row["counts"]["V4_PUBLIC_PATH_NEW_GENERATION_READY role=client"],
         "DUE":row["counts"]["V4_PUBLIC_TIMER_ROTATION_DUE role=client"],
         "OLD_STOP":row["counts"]["V4_PUBLIC_PATH_OLD_EXACT_STOP role=client"],
         "candidate_failed":row["counts"]["V4_PUBLIC_PATH_CANDIDATE_FAILED role=client"],
         "owned_final_stop":row["counts"]["V4_PUBLIC_SHARED_TUN_STOP generation="],
         "udp_received":sum(x["udp_first_received"] for x in row["directions"].values()),
         "tcp_received":sum(x["tcp_frames_received"] for x in row["directions"].values()),
         "gaps_ms":[x["max_active_tx_no_rx_gap_ms"] for x in row["directions"].values()],
       } for n,row in roles.items()}
    },sort_keys=True),flush=True)
if __name__=="__main__":main()
