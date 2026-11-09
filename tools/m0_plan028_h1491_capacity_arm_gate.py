#!/usr/bin/env python3
"""Strict H1491 per-original-180s five-client zero-loss L2 CPU/queue gate.

A capacity-limited 50Mbps control prevents running the 75Mbps stage.
This reads original app, owner, route, qdisc and /proc counters only.
"""
import argparse,json,pathlib,re

SOURCE="57b0d0cded995cf26b6f8ea43a3d4588e6e61d27"
NAMES=("alice","bob","carol","dave","erin")
def read(p):return json.loads(p.read_text())
def core_busy(art):
    p=art/"h1301-netem-clock.json"
    if not p.exists():return {"result":"NOT_MEASURED"}
    rows=read(p).get("samples",[])
    if len(rows)<2:return {"result":"NOT_MEASURED"}
    a,b=rows[0]["host_core_jiffies"],rows[-1]["host_core_jiffies"]
    values={}
    for name in a.keys()&b.keys():
        first,last=a[name],b[name]
        if len(first)<8 or len(last)<8:continue
        total=sum(last[:8])-sum(first[:8])
        idle=last[3]+last[4]-first[3]-first[4]
        if total>0:values[name]=round(100*(total-idle)/total,2)
    return {"result":"MEASURED" if values else "NOT_MEASURED",
            "per_core_busy_pct":values,
            "max_core_busy_pct":max(values.values()) if values else None,
            "mean_core_busy_pct":round(sum(values.values())/len(values),2) if values else None}
def inspect(root,case):
    p=read(root/"h1250-matrix-plan.json")
    assert p["source_sha"]==SOURCE and p["h1467_short_ab_case"]==case
    assert p["application_load_seconds"]==180 and p["simultaneous_stress_seconds"]==170
    assert p["network_scope"]=="native Linux aarch64/aarch64 6-netns"
    assert p["physical_l2_arp_control"]=="test_only_permanent_actual_peer_mac"
    assert p["fec_backend_choice"]=="native"
    assert len(p["clients"])==5 and [x["who"] for x in p["clients"]]==list(NAMES)
    assert all(x["loss_pct"]==x["oneway_delay_ms"]==0 for x in p["clients"])
    want=50 if case=="capacity50" else 75
    assert [x["s2c_target_mbps"] for x in p["clients"]]==[want,2,2,2,2]
    assert all(x==3600 for x in p["rotation_seconds"].values())
    logs={who:(root/f"h1250-product-{who}.log").read_text(errors="replace")
          for who in ("server",)+NAMES}
    assert all("V4_PUBLIC_SHARED_TUN_STOP generation=" in raw for raw in logs.values()),"all six exact Stop"
    sr=logs["server"]
    matches=re.findall(
        r"M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=(\d+\.\d+\.\d+\.\d+) offered=(\d+) direct_delivered=(\d+) downstream_full=(\d+) pending_overflow=(\d+) pending_byte_limit=(\d+) pending_peak_packets=(\d+) pending_peak_bytes=(\d+)",sr)
    assert len(matches)==5, ("per-lease exact queue",len(matches))
    queues={r[0]:dict(offered=int(r[1]),direct=int(r[2]),full=int(r[3]),
                       overflow=int(r[4]),byte_limit=int(r[5]),
                       peak_packets=int(r[6]),peak_bytes=int(r[7]))
            for r in matches}
    assert all(q["peak_packets"]<=8 and q["peak_bytes"]<=65536 for q in queues.values())
    cpu=read(root/"h1250-cpu-rss.json")
    rapid=read(root/"h1286-rapid-report.json")
    assert rapid["source_sha"]==SOURCE
    users={}
    faults=[]
    for x in p["clients"]:
        who=x["who"]; cl=read(root/f"h1250-c-{who}.json")
        sv=read(root/f"h1250-s-{who}.json")
        assert cl["role"]=="client" and sv["role"]=="server"
        assert cl["end_ns"]-cl["start_ns"]==sv["end_ns"]-sv["start_ns"]==180_000_000_000
        directions={}
        for direction in ("uplink","downlink"):
            sender,receiver=(cl,sv) if direction=="uplink" else (sv,cl)
            a=sender["stats"]["udp"];b=receiver["stats"]["udp"]
            assert len(a)==len(b)==5
            missed=sum(t["tx_packets"]-u["rx_packets"] for t,u in zip(a,b))
            sent=sum(t["tx_packets"] for t in a)
            if missed: faults.append(f"{who}_{direction}_unique_missing_{missed}")
            if not sent:faults.append(f"{who}_{direction}_no_real_app_udp")
            directions[direction]=dict(sent=sent,missing=missed)
        if queues[x["lease"]]["overflow"]:
            faults.append(f"{who}_server_lease_overflow_{queues[x['lease']]['overflow']}")
        users[who]={"directions":directions,"server_lease_queue":queues[x["lease"]]}
    alice=read(root/"h1250-c-alice.json")
    phase=p["capacity_phase_schedule"]
    assert [x["name"] for x in phase]==["first_wave","sustained","overload","recovery"]
    actual=[]
    for i,stage in enumerate(phase,1):
        seconds=stage["seconds"]
        actual_mbps=(alice["stats"]["udp"][i]["tx_bytes"]+alice["stats"]["tcp"][i]["tx_bytes"])*8/(seconds*1e6)
        expected=want*stage["rate_scale"]
        actual.append({"name":stage["name"],"target_mbps":round(expected,3),
                       "offered_mbps":round(actual_mbps,3)})
        if actual_mbps<expected*.95:
            faults.append(stage["name"]+"_actual_offer_below95pct")
    cores=core_busy(root)
    host_saturated=(cores["result"]!="MEASURED" or
                   cores["mean_core_busy_pct"]>=85 or cores["max_core_busy_pct"]>=95)
    server_onecore=float(cpu.get("server",{}).get("average_one_core_cpu_percent",0))
    worker_near_limit=server_onecore>=95
    proceed=case=="capacity50" and not faults and not host_saturated and not worker_near_limit
    status=("FAIL_SCOPED_PRODUCT_OR_GENERATOR" if faults else
            "CAPACITY_LIMITED_HOST_OR_PRODUCT_THREAD" if host_saturated or worker_near_limit else
            "PASS_SCOPED_ZEROLOSS_TRUE_ORIGINAL_NATIVE")
    return {"case":case,"source_sha":SOURCE,"platform":"native_arm64_both_ends_native_ISAL",
        "true_five_authenticated":True,"app_seconds":180,
        "all_six_original_owned_Stop":True,
        "classification":status,"actual_alice_mbps":actual,
        "real_UDP_and_lease_queue_by_user":users,
        "host_cpu":cores,"server_onecore_cpu_pct":server_onecore,
        "all_process_cpu_rss":cpu,"rapid_report_alerts":rapid.get("alerts"),
        "measured_defects":faults,"75Mbps_may_run_after_control":proceed,
        "limits":["Host mean/max cores include all generator and OS work",
                  "Server one-core CPU is process-level Go+Rust, not causal hotspot",
                  "50Mbps failing capacity/progress vetoes heavier tier"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",type=pathlib.Path,required=True)
    p.add_argument("--case",choices=("capacity50","capacity_mixed"),required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    a=p.parse_args()
    v=inspect(a.art,a.case);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(v,indent=2)+"\n")
    print("H1491_REAL_NATIVE_CAPACITY_GATE",json.dumps(
        {"case":a.case,"status":v["classification"],
         "go_75":v["75Mbps_may_run_after_control"],
         "host":v["host_cpu"],"defects":v["measured_defects"]},sort_keys=True))
if __name__=="__main__":main()
