#!/usr/bin/env python3
"""H1359: replay only the original H1357 failed native ARM64 artifact.

No network, no forged h1286 report or missing qdisc file. The original
five-client real traffic and native exact owned Stop finished before the
H1259 generic fixture incorrectly waited for Dave Game4 OFF FEC backend
readback, which only FEC ON emits. H1357 CI FAIL remains unchanged.
"""
import argparse
import json
import pathlib
import re
import statistics

SOURCE="24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73"
WRAPPER="082a53b29916289e040e275ff588c97643686d95"
NAMES=("alice","bob","carol","dave","erin")
RATES=(4,4,3,6,3)
ROTATIONS=(97,101,103,89,107)
PHASES=(("first_wave",30,.2),("sustained",60,.35),
        ("overload",30,.5),("recovery",50,.35))

def load(p):
    return json.loads(p.read_text())

def longest_active_gap(tx,rx):
    current=peak=0
    for a,b in zip(tx,rx):
        current=current+1 if a>0 and b==0 else 0
        peak=max(peak,current)
    return peak*10

def parse_log_field(line,name):
    found=re.search(r"\b"+re.escape(name)+r"=(\d+)",line)
    assert found is not None,(name,line)
    return int(found.group(1))

def assess(root):
    plan=load(root/"h1250-matrix-plan.json")
    assert plan["source_sha"]==SOURCE
    assert plan["network_scope"]=="native Linux aarch64/aarch64 6-netns"
    assert plan["server_port"]==443 and plan["application_load_seconds"]==180
    assert [x["who"] for x in plan["clients"]]==list(NAMES)
    assert [x["mode"] for x in plan["clients"]]==[
        "normal","fec-auto","game2","game4","fec-fixed"]
    assert [x["loss_pct"] for x in plan["clients"]]==[0]*5
    assert [x["oneway_delay_ms"] for x in plan["clients"]]==[0,10,20,30,0]
    assert [x["c2s_target_mbps"] for x in plan["clients"]]==list(RATES)
    assert list(plan["rotation_seconds"].values())==list(ROTATIONS)
    assert [(x["name"],x["seconds"],x["rate_scale"])
            for x in plan["capacity_phase_schedule"]]==list(PHASES)
    assert "h1357_specialization" not in plan, "original fixture never reached postnetwork reporter"
    for stage in ("installed","after"):
        n=load(root/("h1312-static-neighbour-"+stage+".json"))
        assert n["source_sha"]==SOURCE and n["native_owner_count"]==10
        assert n["kind"]=="TEST_ONLY_PHYSICAL_VETH_L2_CONTROL"
        assert n["data_netem_unchanged"] and not n["product_or_route_key_modified"]
        assert all(x["neighbor_state"]=="PERMANENT" and x["lladdr_present"]
                   for x in n["entries"])
    server=(root/"h1250-product-server.log").read_text(errors="replace")
    assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in server
    assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in server
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=4 mode=off profile=0" in server
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=server lanes=2 mode=fixed profile=6" in server
    raw_queue={}
    for line in server.splitlines():
        if "M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=" not in line:
            continue
        m=re.search(r"\bip=(10\.66\.0\.\d+)",line)
        assert m is not None
        raw_queue[m.group(1)]={k:parse_log_field(line,k) for k in
            ("offered","direct_delivered","pending_overflow","downstream_full")}
    assert set(raw_queue)=={x["lease"] for x in plan["clients"]}
    faults=[]
    if any(v["pending_overflow"]!=0 or
           v["offered"]!=v["direct_delivered"] for v in raw_queue.values()):
        faults.append({"original_server_per_lease_queue":raw_queue})
    raw_business={}
    generations={}
    original_stop={}
    actual_caps=[]
    actual_cpu={}
    original_tcp={}
    for spec in plan["clients"]:
        who=spec["who"]
        c=load(root/("h1250-c-"+who+".json"))
        s=load(root/("h1250-s-"+who+".json"))
        assert c["role"]=="client" and s["role"]=="server"
        assert c["start_ns"]==s["start_ns"]==plan["start_monotonic_ns"]
        assert c["end_ns"]-c["start_ns"]==s["end_ns"]-s["start_ns"]==180_000_000_000
        if c["errors"] or s["errors"]:
            faults.append({"who":who,"application_error":[c["errors"],s["errors"]]})
        if c["capacity_exceeded"] or s["capacity_exceeded"]:
            actual_caps.append(who)
        log=(root/("h1250-product-"+who+".log")).read_text(errors="replace")
        lease=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=(10\.66\.0\.\d+)/32",log)
        assert lease and set(lease)=={spec["lease"]},(who,lease,spec["lease"])
        stop="V4_PUBLIC_SHARED_TUN_STOP generation=" in log
        original_stop[who]=stop
        if not stop:
            faults.append({"who":who,"missing_original_owned_stop":True})
        if who=="carol":
            assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=2 mode=fixed profile=6" in log
        if who=="dave":
            assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=off profile=0" in log
            assert "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=4" in log
            assert "M0_GAME_M4_FEC_BACKEND_READBACK" not in log, "Off must not make FEC backend claims"
        else:
            gens=list(map(int,re.findall(
                r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)",log)))
            old=list(map(int,re.findall(
                r"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)",log)))
            generations[who]={"client_authenticated_generation_sequence":gens,
                              "old_exact_stop_sequence":old}
            if gens[:3]!=[1,2,3] or old[:2]!=[1,2]:
                faults.append({"who":who,"incomplete_actual_cold_owner_handover":generations[who]})
        raw_business[who]={}
        for direction,tx,rx in (("uplink",c,s),("downlink",s,c)):
            sent=tx["tx_bytes_bins_10ms"]["udp"]
            got=rx["rx_bytes_bins_10ms"]["udp"]
            assert len(sent)==len(got)==19001,(who,len(sent),len(got))
            sent_bytes=sum(sent[:18000]); got_bytes=sum(got[:18000])
            ratio=got_bytes/sent_bytes if sent_bytes else 0
            largest_gap=longest_active_gap(sent[:18000],got[:18000])
            item={"udp_sent_bytes":sent_bytes,"udp_received_bytes":got_bytes,
                  "udp_unique_delivery_fraction":round(ratio,6),
                  "longest_active_send_without_receive_ms":largest_gap}
            raw_business[who][direction]=item
            if sent_bytes<100000 or ratio<.995 or largest_gap>=750:
                faults.append({"who":who,"direction":direction,"real_business":item})
            if who in ("alice","bob"):
                count=sum(x["tx_packets"] for x in tx["stats"]["tcp"])
                rxcount=sum(x["rx_packets"] for x in rx["stats"]["tcp"])
                pending=tx["tcp_pending_at_deadline"]
                original_tcp.setdefault(who,{})[direction]={
                    "framed_sent":count,"framed_received":rxcount,
                    "pending_at_deadline":pending}
                if count==0 or count!=rxcount or pending:
                    faults.append({"who":who,"direction":direction,
                                   "framed_tcp":original_tcp[who][direction]})
    client_log=(root/"h1250-product-dave.log").read_text(errors="replace")
    client_lanes=re.findall(
        r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=client generation=(\d+) lane=(\d+) cycle=(\d+) old_client_port=(\d+) new_client_port=(\d+) unchanged_siblings=3 original_TLS_Rust_M4=1",
        client_log)
    server_lanes=re.findall(
        r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=(\d+) rotation=(\d+) client_port=(\d+) server_port=443 same_game_adapter=1 sibling_lane_restarts=0 original_TLS=1 Rust_M4=1",
        server)
    matched=[]
    for gen,lane,cycle,old,new in client_lanes:
        if (lane,cycle,new) in server_lanes:
            matched.append({"generation":int(gen),"lane":int(lane),
                            "cycle":int(cycle),"old_port":int(old),"new_port":int(new),
                            "server_independently_confirmed":True})
    if len(matched)<2 or len({x["lane"] for x in matched})<2:
        faults.append({"game4_off_server_confirmed_hot_lane_shortfall":matched})
    sample=load(root/"h1301-netem-clock.json")["samples"]
    assert len(sample)>=200
    t0=plan["start_monotonic_ns"]
    now=10
    for name,duration,scale in PHASES:
        subset=[x for x in sample
                if now<=(x["mono_ns"]-t0)/1e9<now+duration]
        core={}
        for l,r in zip(subset,subset[1:]):
            for k,vals in l["host_core_jiffies"].items():
                other=r["host_core_jiffies"].get(k)
                if other is None:continue
                delta=[b-a for a,b in zip(vals,other)]
                total=sum(delta)
                if total>0:
                    core.setdefault(k,[]).append(
                        100*(total-delta[3]-delta[4])/total)
        assert len(core)>=1 and all(len(v)>10 for v in core.values())
        busy=[x for seq in core.values() for x in seq]
        actual_cpu[name]={"actual_guest_vcpu_count":len(core),
                          "guest_busy_mean_percent":round(statistics.mean(busy),2),
                          "highest_core_mean_percent":round(max(statistics.mean(v)
                                                                  for v in core.values()),2),
                          "offered_inner_target_mbps_per_direction":round(sum(RATES)*scale,2)}
        now+=duration
    assert now==180
    errors=(root/"h1357-native-rotating-traffic.log").read_text(errors="replace")
    assert "marker=M0_GAME_M4_FEC_BACKEND_READBACK" in errors
    assert "M0_PLAN028_H1357_NATIVE_ARM64_GAME4_OFF_REAL_ROTATION_CAPTURED" not in errors
    classification=("FAIL_REAL_ORIGINAL_GAME4_OFF_OR_SIBLING" if faults
                    else "CAPACITY_LIMITED" if actual_caps
                    else "PASS_SCOPED_OFFLINE_H1357_NATIVE_ARM64_GAME4_OFF_REAL_IO")
    return {"schema_version":1,"classification":classification,
            "original_product_source":SOURCE,"original_wrapper_source":WRAPPER,
            "original_ci_action":42439698067,"original_ci_conclusion":"failure",
            "original_ci_reporter_failure":"Go/Rust owner and app completed; shared H1259 reporter waited for Dave FEC backend readback in Game4 Off",
            "original_raw_artifact_id":13601276984,"original_raw_artifact_file_count":33,
            "network_rerun":False,"source_exact_single_port":443,
            "native_platform":"Linux native aarch64 both original Go TLS and Rust",
            "original_game4_off_server_confirmed_two_hot_lanes":matched,
            "four_other_clients_authentic_rotations":generations,
            "original_true_udp_10ms_app":raw_business,
            "original_framed_tcp":original_tcp,
            "original_native_exact_owned_stop":original_stop,
            "original_server_exact_shared_tun_stop":True,
            "original_per_lease_queue":raw_queue,
            "native_guest_capacity_by_phase":actual_cpu,
            "generator_capacity_exceeded":actual_caps,"faults":faults,
            "limitations":["Original H1357 Action CI FAIL retained, only offline raw business scope passes",
                           "FEC OFF Dave never emits FEC backend marker; no fake FEC receipts",
                           "Shared original fixture died before writing h1286-rapid-report.json and source specialization",
                           "One physical veth per Game4 client, not four physical paths; no Windows/physical/Android proof",
                           "Product ARM source24e1 not identical to x86 source6c5, no blanket L1 or L3 verdict"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--art",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    result=assess(pathlib.Path(args.art))
    pathlib.Path(args.out).write_text(json.dumps(result,indent=2)+"\n")
    print("M0_PLAN028_H1359_ORIGINAL_GAME4_OFF_33_FILE_OFFLINE_REPLAY",
          result["classification"],flush=True)

if __name__=="__main__":
    main()
