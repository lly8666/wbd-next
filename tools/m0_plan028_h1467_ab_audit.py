#!/usr/bin/env python3
"""H1467: read exact original source66fb per-host sequential short A/B products."""
import argparse,json,pathlib,re
SRC="66fb6b4454b1ce4297ab04efa20c7f931ff12383"
NAMES=("alice","bob","carol","dave","erin")
def load(p):return json.loads(p.read_text())
def inspect(root,case):
    p=load(root/"h1250-matrix-plan.json")
    assert p["source_sha"]==SRC and p["h1467_short_ab_case"]==case
    assert p["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert p["application_load_seconds"]==180 and p["simultaneous_stress_seconds"]==170
    assert p["physical_l2_arp_control"]=="test_only_permanent_actual_peer_mac"
    assert len(p["clients"])==5 and [v["who"] for v in p["clients"]]==list(NAMES)
    assert all(v["loss_pct"]==v["oneway_delay_ms"]==0 for v in p["clients"])
    assert [v["s2c_target_mbps"] for v in p["clients"]]==[75 if case.startswith("capacity") else 12,2,2,2,2]
    assert p["rotation_seconds"]["alice"]==(97 if case=="rotating12" else 3600)
    assert p["h1467_normal_alice_packet_mix"]==([[1024,1]] if case=="capacity_large" else [[256,3],[1024,7]])
    log={who:(root/("h1250-product-"+who+".log")).read_text(errors="replace") for who in ("server",)+NAMES}
    assert all("V4_PUBLIC_SHARED_TUN_STOP generation=" in x for x in log.values())
    rx=re.findall(r"M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=(\d+\.\d+\.\d+\.\d+) offered=(\d+) direct_delivered=(\d+) downstream_full=(\d+) pending_overflow=(\d+) pending_byte_limit=(\d+) pending_peak_packets=(\d+) pending_peak_bytes=(\d+)",log["server"])
    assert len(rx)==5
    q={a:{"offered":int(b),"direct":int(c),"full":int(d),"overflow":int(e),"byte_limit":int(f),"peak":int(g),"bytes":int(h)} for a,b,c,d,e,f,g,h in rx}
    assert all(v["peak"]<=8 and v["bytes"]<=65536 for v in q.values())
    users={}
    for spec in p["clients"]:
        who=spec["who"]
        cl=load(root/("h1250-c-"+who+".json"));sv=load(root/("h1250-s-"+who+".json"))
        assert cl["role"]=="client" and sv["role"]=="server"
        assert cl["end_ns"]-cl["start_ns"]==sv["end_ns"]-sv["start_ns"]==180000000000
        ds={}
        for direction in ("uplink","downlink"):
            tx,rr=(cl,sv) if direction=="uplink" else (sv,cl)
            assert len(tx["stats"]["udp"])==len(rr["stats"]["udp"])==5
            stages=[{"phase":a["phase"],"sent":a["tx_packets"],"recv":b["rx_packets"],"missing":a["tx_packets"]-b["rx_packets"],"tx_bytes":a["tx_bytes"]} for a,b in zip(tx["stats"]["udp"],rr["stats"]["udp"])]
            ds[direction]={"phases":stages,"total_missing":sum(x["missing"] for x in stages)}
        users[who]={"lease":spec["lease"],"mode":spec["mode"],"queue":q[spec["lease"]],"directions":ds}
    cpu=load(root/"h1250-cpu-rss.json");r=load(root/"h1286-rapid-report.json")
    assert r["source_sha"]==SRC
    return {"case":case,"source_sha":SRC,"users":users,
      "original_six_Stop":True,"all_five_original_clocks_180s":True,
      "process_cpu_rss":{n:cpu[n] for n in ("server",)+NAMES},
      "rapid_original_alerts":r["alerts"],"original_rotation_verdict":r["rotation_verdict"],
      "alice_zero_loss_down_missing":users["alice"]["directions"]["downlink"]["total_missing"],
      "alice_original_queue_overflow":users["alice"]["queue"]["overflow"],
      "alice_gen_ready":log["alice"].count("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client"),
      "alice_old_Stop":log["alice"].count("V4_PUBLIC_PATH_OLD_EXACT_STOP role=client"),
      "client_raw_diag_500ms":log["alice"].count("V4_PUBLIC_FEC2_EGRESS_DIAG"),
      "server_original_m4_diag_500ms":log["server"].count("V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG"),
      "all_zero_loss_complete":all(x["total_missing"]==0 for u in users.values() for x in u["directions"].values()),
      "Windows_L3_1800":"NOT_QUALIFIED"}
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--root",type=pathlib.Path,required=True)
    a.add_argument("--pair",choices=("capacity","generation"),required=True)
    a.add_argument("--out",type=pathlib.Path,required=True)
    args=a.parse_args()
    cases=("capacity_mixed","capacity_large") if args.pair=="capacity" else ("static12","rotating12")
    outcomes={k:inspect(args.root/k/"fixed-kernel-result",k) for k in cases}
    result={"schema_version":1,"source_sha":SRC,"paired_control":args.pair,"same_runner_sequential_original_binary":True,
            "order":list(cases),"observations":outcomes,"classification":{
                k:("PASS_SCOPED_180S" if v["all_zero_loss_complete"] and v["alice_original_queue_overflow"]==0 else "FAIL_SCOPED_180S")
                for k,v in outcomes.items()},"restriction":"Not a causal proof until reverse order/CPU state replicated. No 600/1800 source qualification."}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+"\n")
    print("H1467_SOURCE66FB_TRUE_NATIVE_180S_SAME_HOST_AB",json.dumps(
      {k:{"alice_DL_missing":v["alice_zero_loss_down_missing"],"server_queue_overflow":v["alice_original_queue_overflow"]}
       for k,v in outcomes.items()},sort_keys=True),flush=True)
if __name__=="__main__":main()
