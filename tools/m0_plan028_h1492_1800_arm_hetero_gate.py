#!/usr/bin/env python3
"""H1492/H1493 read real ARM64 1800s baseline or heterogeneous native original owners.

Preserve actual 0/1/5/15/30% damage; no broad zero-loss requirement for
impaired users, but zero-configured-loss Alice and owned Stop are hard gates.
"""
import argparse,json,pathlib,re
SOURCE="57b0d0cded995cf26b6f8ea43a3d4588e6e61d27"
NAMES=("alice","bob","carol","dave","erin")
def load(p):return json.loads(p.read_text())
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scene",choices=("baseline","heterogeneous"),default="heterogeneous")
    ap.add_argument("--art",type=pathlib.Path,required=True)
    ap.add_argument("--out",type=pathlib.Path,required=True)
    a=ap.parse_args()
    root=a.art
    plan=load(root/"h1250-matrix-plan.json")
    assert plan["source_sha"]==SOURCE
    assert plan["application_load_seconds"]==1800
    assert plan["long_scene"]==a.scene
    assert plan["network_scope"]=="native Linux aarch64/aarch64 6-netns"
    assert plan["fec_backend_choice"]=="native"
    assert plan["physical_l2_arp_control"]=="test_only_permanent_actual_peer_mac"
    assert len(plan["clients"])==5
    assert [x["who"] for x in plan["clients"]]==list(NAMES)
    expected={"baseline":([0,0,1,1,5],[0,0,15,20,50]),
              "heterogeneous":([0,1,5,15,30],[0,15,50,100,125])}[a.scene]
    assert [x["loss_pct"] for x in plan["clients"]]==expected[0]
    assert [x["oneway_delay_ms"] for x in plan["clients"]]==expected[1]
    report=load(root/"h1274-thirty-minute-report.json")
    assert report["source_sha"]==SOURCE and report["duration_seconds"]==1800
    errors=[];users={}
    for x in plan["clients"]:
        who=x["who"]
        log=(root/f"h1250-product-{who}.log").read_text(errors="replace")
        if "V4_PUBLIC_SHARED_TUN_STOP generation=" not in log:errors.append(who+"_missing_owned_Stop")
        cl=load(root/f"h1250-c-{who}.json")
        sv=load(root/f"h1250-s-{who}.json")
        assert cl["role"]=="client" and sv["role"]=="server"
        assert cl["end_ns"]-cl["start_ns"]==sv["end_ns"]-sv["start_ns"]==1800_000_000_000
        directions={}
        for direction in ("uplink","downlink"):
            send,recv=(cl,sv) if direction=="uplink" else (sv,cl)
            aa=send["stats"]["udp"];bb=recv["stats"]["udp"]
            assert len(aa)==len(bb)==5
            sent=sum(v["tx_packets"] for v in aa)
            got=sum(v["rx_packets"] for v in bb)
            if not sent or not got:errors.append(who+"_"+direction+"_no_business_progress")
            if x["loss_pct"]==0 and got!=sent:
                errors.append(who+"_"+direction+"_zero_damage_missing_"+str(sent-got))
            directions[direction]={"sent":sent,"unique_received":got,"missing":sent-got}
        # Genuine generations may fail in high damage, but do not erase it.
        rot=report["clients"][who]["rotation"]
        if rot.get("result")!="PASS_SCOPED":
            errors.append(who+"_authenticated_rotation_"+str(rot.get("result")))
        users[who]={"loss_pct":x["loss_pct"],"oneway_delay_ms":x["oneway_delay_ms"],
                    "udp":directions,"rotation":rot}
    server=(root/"h1250-product-server.log").read_text(errors="replace")
    if "V4_PUBLIC_SHARED_TUN_STOP generation=" not in server:errors.append("server_missing_owned_Stop")
    for x in plan["clients"]:
        if "V4_PUBLIC_LEASE" not in (root/f"h1250-product-{x['who']}.log").read_text(errors="replace"):
            errors.append(x["who"]+"_lease_receipt_missing")
    queues=re.findall(
      r"M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=(\d+\.\d+\.\d+\.\d+) offered=(\d+) direct_delivered=(\d+) downstream_full=(\d+) pending_overflow=(\d+)",server)
    if len(queues)!=5:errors.append("server_per_lease_queue_receipt_not_complete")
    cpu=load(root/"h1250-cpu-rss.json") if (root/"h1250-cpu-rss.json").exists() else {}
    v={"schema_version":1,"plan":"PLAN028","source_sha":SOURCE,
       "platform":"native_ARM64_both_endpoints_with_accelerated_ISAL",
       "scene":"REAL_1800S_NATIVE_"+a.scene.upper()+"_5CLIENT",
       "actual_underlay_loss_pct":expected[0],"actual_oneway_delay_ms":expected[1],
       "actual_duration_seconds":1800,"original_tls443_Rust_TUN":True,
       "all_6_native_owners_Stop_checked":not any("owned_Stop" in e for e in errors),
       "app_original_unique_by_client_and_direction":users,
       "per_lease_exact_queue":queues,"process_cpu_rss":cpu,
       "original_report_alerts":report.get("alerts",[]),
       "hard_gate_errors":errors,
       "classification":("PASS_SCOPED_NATIVE_L3_"+a.scene.upper()) if not errors else ("FAIL_SCOPED_NATIVE_L3_"+a.scene.upper()),
       "explicit_limits":["No Windows Npcap/Wintun or external physical WAN",
                          "30%/125ms correlated high impairment is not required to have 0 residual UDP loss",
                          "Current L2 75Mbps unresolved independently: L3 cannot overrule capacity FAIL",
                          "H998 old online hot MTU FAIL and Android NOT_RUN retained"],
       "plan028":"IN_PROGRESS"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(v,indent=2)+"\n")
    print("H1492_1493_1800S_NATIVE_ARM64_L3_"+a.scene.upper()+"_REAL_VERDICT",json.dumps({
        "status":v["classification"],"errors":errors,"per_user":
        {k:{d:w["missing"] for d,w in val["udp"].items()} for k,val in users.items()}},sort_keys=True))
    if errors:raise SystemExit(1)
if __name__=="__main__":main()
