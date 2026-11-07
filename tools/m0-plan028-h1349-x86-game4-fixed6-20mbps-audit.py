#!/usr/bin/env python3
"""Offline-native H1349 L2 Game4 fixed6 ledger: real app/per-VM CPU/0%-loss evidence only.

A measured throughput ceiling is useful and is NOT renamed product PASS.
Sends and deliveries are from opposite real application endpoint clocks.
TCP 'packet' counters are framed-app records, not physical TCP segments.
"""
import argparse
import json
import pathlib
import re
import statistics

NAMES=("alice","bob","carol","dave","erin")
MODES=("normal","fec-auto","game2","game4","fec-fixed")
SOURCE="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
PHASES=(("first_wave",20,.15),("sustained",30,.25),
        ("climb_10",30,.5),("overload_20",30,1.),("recovery",60,.5))

def read(p):
    return json.loads(pathlib.Path(p).read_text())

def record(root):
    plan=read(root/"h1250-matrix-plan.json")
    prior=read(root/"h1286-rapid-report.json")
    tick=read(root/"h1301-netem-clock.json")["samples"]
    assert plan["source_sha"]==prior["source_sha"]==SOURCE
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert plan["h1349_specialization"]["profile"]=="H1349_REAL_ZERO_LOSS_GAME4_FIXED6_STAGED"
    assert [(v["name"],v["seconds"],v["rate_scale"]) for v in
            plan["capacity_phase_schedule"]]==list(PHASES)
    assert [x["who"] for x in plan["clients"]]==list(NAMES)
    assert [x["mode"] for x in plan["clients"]]==list(MODES)
    assert [x["loss_pct"] for x in plan["clients"]]==[0]*5
    assert [x["oneway_delay_ms"] for x in plan["clients"]]==[0]*5
    assert [x["c2s_target_mbps"] for x in plan["clients"]]==[2,2,2,20,2]
    assert plan["application_load_seconds"]==180 and plan["warmup_seconds"]==10
    assert not plan["long_scene"] and plan["fast_scene"]=="pressure"
    server=(root/"h1250-product-server.log").read_text(errors="replace")
    assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in server
    assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in server
    streams={}
    stop={}
    generator_limits={}
    lease=set()
    for spec in plan["clients"]:
        who=spec["who"]
        c=read(root/("h1250-c-"+who+".json"))
        s=read(root/("h1250-s-"+who+".json"))
        assert c["start_ns"]==s["start_ns"]==plan["start_monotonic_ns"]
        assert c["end_ns"]-c["start_ns"]==180_000_000_000
        assert s["end_ns"]-s["start_ns"]==180_000_000_000
        generator_limits[who]={"client":bool(c["capacity_exceeded"]),"server":bool(s["capacity_exceeded"])}
        logs=(root/("h1250-product-"+who+".log")).read_text(errors="replace")
        leaseproof=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=(10\.66\.0\.\d+)/32",logs)
        assert leaseproof and set(leaseproof)=={spec["lease"]},(who,leaseproof,spec["lease"])
        lease.add(spec["lease"])
        stop[who]=("V4_PUBLIC_SHARED_TUN_STOP generation=" in logs)
        assert stop[who],who
        assert ("V4_ORIGINAL_GO_GAME_NATIVE_READY role=client" in logs
                if who in ("carol","dave") else
                "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" in logs),who
        streams[who]={"client":c,"server":s,"spec":spec}
    assert len(lease)==5
    assert len(tick)>100
    start_ns=plan["start_monotonic_ns"]
    # Two real netem qdiscs at Erin; 0 configured DATA loss must also be
    # observed as zero kernel qdisc drops (not merely copied config).
    k={}
    for direction,field in (("uplink","client_uplink_netem"),
                            ("downlink","host_downlink_netem")):
        valid=[t[field] for t in tick if t.get(field,{}).get("kind")=="netem"]
        assert len(valid)>=100,(direction,len(valid))
        delta=valid[-1]["drops"]-valid[0]["drops"]
        assert delta>=0
        k[direction]={"observed_kernel_qdisc_drops":delta,
                      "actual_packets":valid[-1]["packets"]-valid[0]["packets"]}
    phases=[]
    p=10
    all_stable=True
    targeted=[]
    for name,duration,scale in PHASES:
        a,b=p*100,(p+duration)*100
        t=[q for q in tick if p*1_000_000_000<=q["mono_ns"]-start_ns
           <(p+duration)*1_000_000_000]
        busy=[]; soft=[]; percore={}
        for first,last in zip(t,t[1:]):
            for core,left in first.get("host_core_jiffies",{}).items():
                right=last.get("host_core_jiffies",{}).get(core)
                if right is None: continue
                delta=[z-x for x,z in zip(left,right)]
                total=sum(delta)
                if total<=0: continue
                value=100*(total-delta[3]-delta[4])/total
                busy.append(value)
                soft.append(100*delta[6]/total)
                percore.setdefault(core,[]).append(value)
        assert len(busy)>=40 and len(percore)>=1,(name,len(busy),list(percore)) # VM core topology is observed, never fixed at four
        row={"phase":name,"application_seconds":[p,p+duration],
             "scale":scale,"host_busy_mean_pct":round(statistics.mean(busy),2),
             "host_softirq_mean_pct":round(statistics.mean(soft),2),
             "host_per_core_busy_mean_pct":{key:round(statistics.mean(values),2)
                                           for key,values in sorted(percore.items())},
             "host_exposed_logical_core_count":len(percore),
             "clients":{}}
        for who,dev in streams.items():
            orig=dev["spec"]["c2s_target_mbps"]*scale
            directions={}
            for direction,tx,rx in (
                ("uplink",dev["client"],dev["server"]),
                ("downlink",dev["server"],dev["client"])):
                details={}
                for proto in ("udp","tcp"):
                    offered_bytes=sum(tx["tx_bytes_bins_10ms"][proto][a:b])
                    delivered_bytes=sum(rx["rx_bytes_bins_10ms"][proto][a:b])
                    offered_records=sum(tx["tx_bins_10ms"][proto][a:b])
                    delivered_records=sum(rx["rx_bins_10ms"][proto][a:b])
                    details[proto]={
                        "offered_mbps":round(offered_bytes*8/duration/1e6,3),
                        "delivered_mbps":round(delivered_bytes*8/duration/1e6,3),
                        "offered_app_records_per_second":round(offered_records/duration,1),
                        "delivered_app_records_per_second":round(delivered_records/duration,1),
                        "delivery_fraction":round(delivered_bytes/offered_bytes,5)
                            if offered_bytes else None}
                offered=sum(details[x]["offered_mbps"] for x in ("udp","tcp"))
                delivered=sum(details[x]["delivered_mbps"] for x in ("udp","tcp"))
                directions[direction]={
                    "target_app_mbps":round(orig,3),
                    "actual_total_app_offered_mbps":round(offered,3),
                    "actual_total_app_delivered_mbps":round(delivered,3),
                    "generation_target_fill_fraction":round(offered/orig,4),
                    "udp":details["udp"],"tcp_framed":details["tcp"]}
                if details["udp"]["delivery_fraction"] is None or details["udp"]["delivery_fraction"]<.99:
                    all_stable=False
                if who=="dave":
                    targeted.append({"phase":name,"direction":direction,
                                     "target":orig,"observed":offered,
                                     "fill_fraction":round(offered/orig,5)})
            row["clients"][who]=directions
        row["total_actual_offered_mbps_one_direction"]=round(
            sum(v["uplink"]["actual_total_app_offered_mbps"]
                for v in row["clients"].values()),3)
        phases.append(row)
        p+=duration
    assert p==180
    gaps={}
    for who in NAMES:
        old=prior["clients"][who]["directions"]
        gaps[who]={direction:old[direction]["largest_10ms_bucket_no_receive_while_sender_active_ms"]
                   for direction in ("uplink","downlink")}
        if any(value>=750 for value in gaps[who].values()):
            all_stable=False
    if any(d["observed_kernel_qdisc_drops"]>0 for d in k.values()):
        all_stable=False
    near_limit=[{"phase":phase["phase"],"host_busy_pct":phase["host_busy_mean_pct"],
                 "hot_cores":{core:busy for core,busy in phase["host_per_core_busy_mean_pct"].items() if busy>=95}}
                for phase in phases if phase["host_busy_mean_pct"]>=95 or
                   any(v>=95 for v in phase["host_per_core_busy_mean_pct"].values())]
    inaccurate=[x for x in targeted if x["fill_fraction"]<.95]
    generator_limited=[who for who,record in generator_limits.items() if any(record.values())]
    # Bounded old L2 source: classify a measured ceiling, do not rebrand
    # a slow test as a full 50Mbps PASS or infer product-specific root cause.
    classification=("FAIL_REAL_APP_OR_KERNEL_0LOSS_GAP" if not all_stable else
                    "CAPACITY_LIMITED_OR_GENERATOR_LIMITED" if inaccurate or generator_limited else
                    "HOST_NEAR_LIMIT_GAME4_20MBPS_UNQUALIFIED_FOR_NEXT_STEP" if near_limit else
                    "PASS_SCOPED_0LOSS_GAME4_FIXED6_3_5_10_20_10_WITH_FIVE_SIBLINGS")
    return {
        "schema_version":1,"kind":"M0_PLAN028_H1349_NATIVE_X86_L2_ZERO_LOSS_GAME4_CALIB",
        "original_product_source_sha":SOURCE,
        "native_binaries":{"arch":"x86_64 ELF62",
                           "provenance":"original Go TLS donor a7a82; Rust native_fec_acceleration ISA-L from H1320 Action42369031512",
                           "reused_artifact_id":13572791923,
                           "validated_unchanged_product_owner_against_main":"H1331 exact source compare"},
        "traffic":"one real original TLS server443 and five separate native x86 clients with actual OS TUN and original Rust M4",
        "game4_physical_loss_percent":0,"other_four_physical_loss_percent":0,
        "auth_user_count":5,"all_five_exact_final_client_stop":all(stop.values()),
        "server_exact_final_stop":True,
        "rotation_during_test":"NONE_REQUESTED, 600s dormant timers; L1 rotation not qualified",
        "per_VM_cpu_topology":"HOST_OBSERVED_PER_PHASE_DYNAMIC_NEVER_CROSS_VM",
        "true_physical_erin_qdisc":k,
        "phases":phases,"game4_true_offered_mbps":targeted,
        "generator_capacity_exceeded":generator_limited,
        "max_app_active_tx_no_rx_gap_ms_by_client":gaps,
        "target_fill_below_95pct":inaccurate,
        "host_busy_95pct_or_more":near_limit,
        "measurement_complete":True,"real_business_stability_pass":all_stable,
        "classification":classification,
        "claim_boundaries":[
            "Host busy includes native users/generators and Linux kernel, not causal product-only CPU",
            "TCP records are framed application writes, not TCP wire PPS",
            "Native virtual-veth 0% calibration; no physical WAN/Windows/Android claim",
            "Only Game4 logical 3/5/10/20Mbps per direction, no 20Mbps or exact Game4 VM-independent ceiling if generator limited",
            "No 30% loss conclusion from this zero-loss scene",
            "No timer rotation or new exact physical source/MTU event in this scenario"
        ]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--art",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    root=pathlib.Path(args.art)
    result=record(root)
    pathlib.Path(args.out).write_text(json.dumps(result,indent=2)+"\n")
    print("M0_PLAN028_H1349_NATIVE_X86_GAME4_ZERO_LOSS_CAPACITY_OBSERVED",
          result["classification"],
          [(x["phase"],x["host_busy_mean_pct"]) for x in result["phases"]],
          flush=True)

if __name__=="__main__":
    main()
