#!/usr/bin/env python3
"""PLAN028 H1390 immutable OFFLINE replay of both original H1389 ARM64 1800s workloads.
No product/network replay; the original 34-file raw artifacts are the authority.
One scene has actual Erin 3.31/3.32s app receive gaps: NEVER turn that into a full pass.
"""
import argparse,json,pathlib,re,hashlib
SOURCE="096a2d55d204c7485aa2fce7d47b3c8e31901bc4"
GO_DONOR="a7a82db31fe736ffedee330795a3234d358f1984"
ORIGINAL_RUN=42466954711
ART={
 "baseline":{"id":13612852570,"zip_sha256":"7c4cf6005ea025bf77455f5d1982b554bd3455e049fee29c6af119f24002ba7c"},
 "heterogeneous":{"id":13611954544,"zip_sha256":"58fae41aa929fe9b8234f52fab070b9fe0beabad00869ff4a0a94a23fc28c851"}
}
NAMES=["alice","bob","carol","dave","erin"]
def read(path): return json.loads(path.read_text())
def audit(root,scene):
 assert scene in ART
 expected=ART[scene]
 src=root/"fixed-kernel-result"
 files=[p for p in root.rglob("*") if p.is_file()]
 assert len(files)==34,("original raw file count",len(files))
 manifest=read(root/"fixed-build"/"manifest.json")
 report=read(src/"h1274-thirty-minute-report.json")
 plan=read(src/"h1250-matrix-plan.json")
 assert report["source_sha"]==manifest["source_sha"]==plan["source_sha"]==SOURCE
 assert manifest["original_go_sha"]==GO_DONOR
 assert manifest["architecture"]=="native_aarch64" and report["architecture"]=="native_ARM64_client_and_server"
 assert manifest["go"]=="1.23.12" and manifest["rust"]=="1.85.1"
 assert report["scene"]==plan["long_scene"]==scene
 assert report["result"]=="DIAGNOSTIC_COMPLETE"
 assert report["duration_seconds"]==plan["application_load_seconds"]==1800
 assert plan["network_scope"]=="native Linux aarch64/aarch64 6-netns"
 assert report["server_single_port"]==plan["server_port"]==443
 assert report["rotation_verdict"]=="PASS_ALL_FIVE_SCOPED"
 assert list(report["clients"])==NAMES and len(plan["clients"])==5
 serverlog=(src/"h1250-product-server.log").read_text(errors="replace")
 assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY" in serverlog
 m=re.findall(r"V4_PUBLIC_SHARED_TUN_STOP generation=(\d+) routed=(\d+) unrouted=(\d+) backpressure=(\d+) reader_joined=1",serverlog)
 assert len(m)==1,m
 server_gen,routed,unrouted,backpressure=map(int,m[0])
 assert server_gen>0 and routed>1_000_000 and unrouted==0 and backpressure==0
 queues=report["server_per_authenticated_lease_tun"]
 assert len(queues)==5
 assert sum(q["offered"] for q in queues.values())==routed
 assert all(q["offered"]==q["direct_delivered"] and q["pending_overflow"]==0 for q in queues.values())
 result_clients={}
 for who in NAMES:
  c=report["clients"][who]
  r=c["rotation"]
  assert r["result"]=="PASS_SCOPED" and r["native_final_stop_observed"] and r["same_authenticated_lease"]
  assert r["minimum_ten_true_successful_handoffs"] and c["health90_events"]==0
  if who=="dave":
   assert r["unit"]=="one_original_authenticated_Game4_lane_at_a_time"
   assert r["native_server_confirmed_hot_slots"]==r["single_lane_successful"]>=10
   assert sum(r["per_lane_success"].values())==r["single_lane_successful"]
   rotations=r["single_lane_successful"]
  else:
   generations=r["authenticated_generation_sequence"]
   stops=r["old_generation_stop_sequence"]
   assert len(generations)>=11 and generations==list(range(1,len(generations)+1))
   assert stops==generations[:-1] and r["exact_old_owner_stop"]
   assert r["failed_cold_candidates"]==0
   assert r["server_normal_m4_commits_observed"]==len(generations) if who in ("alice","bob","erin") else True
   rotations=len(stops)
  for side in ("c","s"):
   app=read(src/("h1250-"+side+"-"+who+".json"))
   assert not app["errors"] and not app["capacity_exceeded"]
   assert app["end_ns"]-app["start_ns"]==1_800_000_000_000
   assert len(app["tx_bytes_bins_10ms"]["udp"])==181001
   assert len(app["rx_bytes_bins_10ms"]["udp"])==181001
   assert sum(app["tx_bytes_bins_10ms"]["udp"])>100_000
  assert c["server_per_lease_queue"]["offered"]==queues[c["lease"]]["offered"]
  assert "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client" in (src/("h1250-product-"+who+".log")).read_text(errors="replace")
  result_clients[who]={"mode":c["mode"],"lease":c["lease"],
       "authenticated_owner_or_lane_handoffs":rotations,
       "all_original_app_errors":0,"native_final_Stop":True,
       "configured_loss_pct":c["configured_loss_pct"],
       "oneway_delay_ms":c["one_way_delay_ms"]}
 alerts=report["alerts"]
 assert report["alert_count"]==len(alerts)
 if scene=="baseline":
  assert alerts==[] and report["performance_verdict"]=="NO_CONFIGURED_ALERTS"
  perf="PASS_BASELINE_1800S_NO_CONFIGURED_ALERTS"
  classification="PASS_SCOPED_1800S_ORIGINAL_ARM64_FIVE_AUTH_CLIENTS_ROTATIONS_AND_BASELINE_PERFORMANCE"
 else:
  expected_alerts=[("erin","uplink",3310),("erin","downlink",3320)]
  assert sorted((a["who"],a["direction"],a["duration_ms"]) for a in alerts)==sorted(expected_alerts)
  assert all(a["kind"]=="APP_RX_GAP_WITH_ACTIVE_TX_GE750MS" for a in alerts)
  assert report["performance_verdict"]=="ALERTS_PRESENT"
  assert report["clients"]["erin"]["configured_loss_pct"]==30
  perf="FAIL_CONFIGURED_RX_GAP_LIMIT_ERIN_3310_3320MS_IN_30PCT_125MS"
  classification="PASS_SCOPED_1800S_ORIGINAL_ARM64_OWNER_ROTATION_AND_STOP_WITH_REAL_PERFORMANCE_FAILURE"
 return {
  "schema_version":1,"plan":"PLAN028","workstream":"M0","scene":scene,
  "original_source_sha":SOURCE,"original_go_donor_sha":GO_DONOR,
  "original_action_run":ORIGINAL_RUN,"original_action_conclusion":"success",
  "original_artifact_id":expected["id"],"original_zip_sha256":expected["zip_sha256"],
  "original_zip_crc":"PASS_34_FILES_VERIFIED_PRIOR_TO_REPLAY",
  "offline_replay_no_network_or_product_rerun":True,
  "actual_duration_seconds":1800,"original_real_authenticated_client_count":5,
  "original_go_tls443_and_rust_m4":"REAL_NATIVE_ARM64",
  "classification":classification,"rotation_verdict":report["rotation_verdict"],
  "performance_verdict":perf,"original_unfiltered_alerts":alerts,
  "original_client_receipts":result_clients,"original_server_shared_tun":{"routed":routed,"unrouted":unrouted,"backpressure":backpressure,"reader_joined":1,"queue_pending_overflows":sum(q["pending_overflow"] for q in queues.values())},
  "original_native_binary_sha256":manifest["sha256"],
  "limitations":["Original Linux hosted ARM64 real netns/veth is not physical WAN, Android or Windows",
      "Heterogeneous original Erin 30%/125ms has two authentic app receive gaps 3.31/3.32s and fails the configured 750ms gap gate; CI green only means diagnostic completed",
      "Original H1389 two 1800s run still cannot close Windows dual authenticated signed Wintun or old H998 same-socket hot MTU"]
 }
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--scene",choices=tuple(ART),required=True);p.add_argument("--out",required=True)
 a=p.parse_args();out=audit(pathlib.Path(a.root),a.scene)
 dest=pathlib.Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(out,indent=2)+"\n")
 print("M0_PLAN028_H1390_ORIGINAL_1800S_SOURCE_FROZEN_"+a.scene.upper()+"_"+out["classification"],flush=True)
if __name__=="__main__":main()
