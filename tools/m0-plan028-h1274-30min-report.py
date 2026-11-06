#!/usr/bin/env python3
"""H1274 source-locked 1800s original TLS/Rust five-client rotation diagnostics.

A green Action means evidence collection completed, not all-client performance
qualification. Repeated frozen record bytes do NOT confer app delivery credit.
"""
import argparse
import json
import pathlib
import re

NAMES=("alice","bob","carol","dave","erin")
PHASES=(("warmup",10,.3),("first_wave",240,.6),("sustained",600,1.0),
        ("overload",300,1.3),("recovery",650,1.0))

def read(path):
    return json.loads(pathlib.Path(path).read_text())

def count(line,name):
    match=re.search(r"\b"+re.escape(name)+r"=(\d+)",line)
    return int(match.group(1)) if match else None

def mbps(bytes_count,seconds):
    return round(8*bytes_count/(seconds*1e6),5)

def outer_counts(log,mode):
    if mode=="game4":
        marker="WBD_GAME_FEC_LINUX_NORMAL_OUTER_STOP"
    elif mode=="game2":
        marker="WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP"
    else:
        marker="V4_PUBLIC_M2_OUTER role=client"
    game=mode.startswith("game")
    fields=("copied_appearance","first_record_wire_bytes","copy_record_wire_bytes") if game else (
        "first_wire_bytes","repair_accepted_wire_bytes","repair_uncertain_wire_bytes",
        "original_frozen_retransmitted")
    sums={f:0 for f in fields}
    samples=0
    per_generation=[]
    for line in log.splitlines():
        if marker not in line:
            continue
        values={f:count(line,f) for f in fields}
        if any(x is None for x in values.values()):
            continue
        for key,val in values.items():
            sums[key]+=val
        samples+=1
        per_generation.append({"retirement_ordinal":samples,
            "accepted_repeat_record_bytes":values["copy_record_wire_bytes" if game else "repair_accepted_wire_bytes"],
            "first_record_bytes":values["first_record_wire_bytes" if game else "first_wire_bytes"],
            "copied_record_count":values.get("copied_appearance",values.get("original_frozen_retransmitted"))})
    first=sums["first_record_wire_bytes" if game else "first_wire_bytes"]
    repeat=sums["copy_record_wire_bytes" if game else "repair_accepted_wire_bytes"]
    return {
        "observed_retired_generations":samples,
        "per_retired_generation_record_counters":per_generation,
        "first_record_wire_bytes":first,
        "cosmetic_accepted_repeat_record_wire_bytes":repeat,
        "uncertain_repeat_record_wire_bytes":0 if game else sums["repair_uncertain_wire_bytes"],
        "copied_original_record_count":sums.get("copied_appearance",sums.get("original_frozen_retransmitted")),
        "cosmetic_R_div_F_plus_R_pct":round(100*repeat/(first+repeat),5) if first+repeat else None,
        "cosmetic_accepted_repeat_mbps_over_1800s":mbps(repeat,1800),
        "denominator_scope":"original accepted protected record wire bytes, excludes IPv4/TCP/L2 and control C",
        "R_div_F_plus_R_plus_C":"NOT_MEASURED_CONTROL_C",
        "raw_original_counters":sums
    }

def tc_stats(path):
    txt=pathlib.Path(path).read_text(errors="replace")
    pieces=re.split(r"(?m)^== (.+?) (uplink|downlink).*? ==$",txt)
    out={}
    for index in range(1,len(pieces),3):
        name,direction,block=pieces[index:index+3]
        m=re.search(r"Sent\s+(\d+)\s+bytes\s+(\d+)\s+pkt\s+\(dropped\s+(\d+)",block)
        if m:
            actual_bytes,packets,drops=map(int,m.groups())
            out.setdefault(name,{})[direction]={
                "actual_physical_qdisc_sent_bytes":actual_bytes,
                "actual_physical_qdisc_packets":packets,
                "physical_qdisc_dropped_packets":drops,
                "observed_physical_drop_fraction":round(drops/(packets+drops),6) if packets+drops else None
            }
    return out

def minute_windows(tx,rx):
    assert len(tx)==len(rx)
    result=[]
    for minute in range(30):
        a,b=minute*6000,(minute+1)*6000
        first=sum(tx[a:b]); received=sum(rx[a:b])
        result.append({"minute":minute+1,"offered_mbps":mbps(first,60),
                       "delivered_mbps":mbps(received,60),
                       "delivery_fraction":round(received/first,5) if first else None})
    return result

def longest_active_tx_no_rx_gap_ms(tx,rx):
    """Real synchronized 10ms app bins; no native kernel-causality inference."""
    assert len(tx)==len(rx)
    current=maximum=0
    for a,b in zip(tx,rx):
        current=current+1 if a>0 and b==0 else 0
        if current>maximum:
            maximum=current
    return maximum*10

def per_lease_tun_stop_counters(server_text):
    result={}
    for line in server_text.splitlines():
        if "M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=" not in line:
            continue
        m=re.search(r"\bip=(\d+\.\d+\.\d+\.\d+)",line)
        if m:
            result[m.group(1)]={field:count(line,field) for field in (
                "offered","direct_delivered","pending_overflow",
                "pending_peak_bytes","pending_peak_packets")}
    return result

def analyze(art,server_log):
    plan=read(art/"h1250-matrix-plan.json")
    assert plan["long_scene"] in ("baseline","heterogeneous","pressure")
    assert plan["application_load_seconds"]==1800
    assert plan["simultaneous_stress_seconds"]==1790
    assert sum(p[1] for p in PHASES)==1800
    assert len(plan["clients"])==5
    assert {p["who"] for p in plan["clients"]}==set(NAMES)
    cpu=read(art/"h1250-cpu-rss.json")
    qdisc=tc_stats(art/"h1250-qdisc-after.txt")
    server_text=pathlib.Path(server_log).read_text(errors="replace")
    per_lease=per_lease_tun_stop_counters(server_text)
    result={
        "schema_version":1,"checkpoint":"H1274",
        "source_sha":plan["source_sha"],"scene":plan["long_scene"],
        "result":"DIAGNOSTIC_COMPLETE","architecture":"native_ARM64_client_and_server",
        "duration_seconds":1800,"clients":{},"alerts":[],
        "actual_physical_qdisc":qdisc,
        "server_per_authenticated_lease_tun":per_lease,
        "server_cpu_rss":cpu.get("server"),
        "server_single_port":plan["server_port"],
        "limitations":[
            "Source-locked hosted same-runner ARM64 netns, not physical WAN or Android/Windows",
            "No app retransmission or synthetic receipt; original Go TLS/NativeRust RAW/TUN",
            "Game appearance-only repeat packets preserve frozen PN/Seq/record bytes",
            "R/(F+R) is comparable record-byte scope only; control C and outer IP/TCP/L2 unavailable",
            "Native FEC/Game redundancy is not the appearance-only retransmission numerator",
            "Actual qdisc loss includes configured loss and potential qdisc overflow",
            "CPU/RSS are original process samples, not a causal before/after optimization"
        ]
    }
    repeat_all=0
    first_all=0
    rotation_ok=True
    for spec in plan["clients"]:
        who=spec["who"]
        source=read(art/("h1250-c-"+who+".json"))
        peer=read(art/("h1250-s-"+who+".json"))
        assert source["role"]=="client" and peer["role"]=="server"
        assert source["start_ns"]==peer["start_ns"]==plan["start_monotonic_ns"]
        assert source["end_ns"]-source["start_ns"]==1800_000_000_000
        assert peer["end_ns"]-peer["start_ns"]==1800_000_000_000
        if source["capacity_exceeded"] or peer["capacity_exceeded"]:
            result["alerts"].append({"who":who,"kind":"GENERATOR_PACKET_CAP_REACHED"})
        text=(art/("h1250-product-"+who+".log")).read_text(errors="replace")
        ready=[int(v) for v in re.findall(
            r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+)",text)]
        old=[int(v) for v in re.findall(
            r"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)",text)]
        timer=[l for l in text.splitlines() if "V4_PUBLIC_TIMER_ROTATION_DUE role=client" in l]
        leases=re.findall(
            r"V4_PUBLIC_LEASE_APPLIED role=client.*?os_readback=(10\.66\.0\.\d+)/32",text)
        correct_physical=bool(timer) and all(
            "same_physical_interface_ipv4=true" in l and "unchanged_path=true" in l
            for l in timer)
        sequential=bool(ready) and ready[0]==1 and all(
            b==a+1 for a,b in zip(ready,ready[1:]))
        accurate_stop=all(x in old for x in ready[:-1])
        enough=len(ready)>=11 and len(old)>=10 and len(timer)>=10
        lease_stable=bool(leases) and set(leases)=={spec["lease"]}
        native_stop="V4_PUBLIC_SHARED_TUN_STOP generation=" in text
        passed=all((correct_physical,sequential,accurate_stop,enough,lease_stable,native_stop))
        rotation_ok=rotation_ok and passed
        rotation={"result":"PASS_SCOPED" if passed else "FAIL_OR_INCOMPLETE",
                  "authenticated_generation_sequence":ready,
                  "old_generation_stop_sequence":old,"timer_events":len(timer),
                  "configured_interval_s":plan["rotation_seconds"][who],
                  "same_authenticated_lease":lease_stable,
                  "physical_ipv4_unchanged":correct_physical,
                  "native_final_stop_observed":native_stop,
                  "at_least_ten_true_successful_handoffs":enough}
        if not passed:
            result["alerts"].append({"who":who,"kind":"ROTATION_CONTINUITY_NOT_PROVEN"})
        game=("game4" if spec["mode"]=="game4" else "game2" if spec["mode"]=="game2" else "")
        repeat=outer_counts(text,game)
        if repeat["observed_retired_generations"]==0:
            result["alerts"].append({"who":who,"kind":"NO_REAL_OUTER_COUNTER"})
        repeat_all+=repeat["cosmetic_accepted_repeat_record_wire_bytes"]
        first_all+=repeat["first_record_wire_bytes"]
        details={"mode":spec["mode"],"lease":spec["lease"],
                 "server_per_lease_queue":per_lease.get(spec["lease"]),
                 "health90_events":text.count("M0_GAME_M4_HEALTH_DEAD"),
                 "outer_intent_mtu":spec["outer_mtu"],
                 "configured_loss_pct":spec["loss_pct"],
                 "one_way_delay_ms":spec["oneway_delay_ms"],
                 "rotation":rotation,"outer_cosmetic":repeat,
                 "process_cpu_rss":cpu.get(who),"directions":{}}
        for direction in ("uplink","downlink"):
            tx,rx=(source,peer) if direction=="uplink" else (peer,source)
            phases=[]
            for i,(name,duration,rate_scale) in enumerate(PHASES):
                sent=tx["stats"]["udp"][i]
                got=rx["stats"]["udp"][i]
                n=sent["tx_packets"]
                m=got["rx_packets"]
                phases.append({
                    "phase":name,"seconds":duration,
                    "actual_udp_sent":n,"unique_udp_delivered":m,
                    "actual_delivery_fraction":round(m/n,6) if n else None,
                    "actual_udp_sent_mbps":mbps(sent["tx_bytes"],duration),
                    "actual_udp_delivered_mbps":mbps(got["rx_bytes"],duration),
                    "received_only_one_way_p99_ms":got["latency"]["p99_ms"],
                    "received_only_one_way_max_ms":got["latency"]["max_ms"],
                    "generator_send_errors":sent["send_errors"],
                    "generator_backpressure":sent["backpressure"],
                    "received_duplicates":got["duplicates"],
                    "received_invalid":got["invalid"]
                })
                if n==0 or m==0:
                    result["alerts"].append({"who":who,"direction":direction,
                                             "phase":name,"kind":"NO_UDP_BUSINESS_PROGRESS"})
                elif name=="recovery" and m/n<.95:
                    result["alerts"].append({"who":who,"direction":direction,
                                             "phase":name,"kind":"RECOVERY_DELIVERY_BELOW_95PCT",
                                             "delivered_fraction":round(m/n,6)})
            tx_10ms=tx["tx_bytes_bins_10ms"]["udp"]
            rx_10ms=rx["rx_bytes_bins_10ms"]["udp"]
            no_receive_gap=longest_active_tx_no_rx_gap_ms(tx_10ms,rx_10ms)
            minute=minute_windows(tx_10ms,rx_10ms)
            no_progress=[x["minute"] for x in minute
                         if x["offered_mbps"]>.5 and x["delivered_mbps"]<.25]
            if no_progress:
                result["alerts"].append({"who":who,"direction":direction,
                                         "kind":"MINUTE_LEVEL_APP_RX_STARVATION",
                                         "minutes":no_progress})
            if no_receive_gap>=750:
                result["alerts"].append({"who":who,"direction":direction,
                                          "kind":"APP_RX_GAP_WITH_ACTIVE_TX_GE750MS",
                                          "duration_ms":no_receive_gap})
            details["directions"][direction]={
                "phases":phases,"minute_actual_business":minute,
                "largest_10ms_bucket_no_receive_while_sender_active_ms":no_receive_gap,
                "true_tcp":{"framed_app_sent":sum(x["tx_packets"] for x in tx["stats"]["tcp"]),
                            "framed_app_received":sum(x["rx_packets"] for x in rx["stats"]["tcp"]),
                            "sender_pending_at_deadline":tx["tcp_pending_at_deadline"]}}
        result["clients"][who]=details
    server=server_text
    if "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" not in server:
        result["alerts"].append({"kind":"NO_ORIGINAL_TLS_SERVER_PORT_READY"})
    for who,item in result["clients"].items():
        lease=item["lease"]
        if lease not in per_lease:
            result["alerts"].append({"who":who,"kind":"NO_SERVER_LEASE_QUEUE_RECEIPT"})
        elif per_lease[lease].get("pending_overflow",0)>0:
            result["alerts"].append({"who":who,"kind":"SERVER_PER_LEASE_QUEUE_OVERFLOW",
                                     "pending_overflow":per_lease[lease]["pending_overflow"]})
    result["rotation_verdict"]="PASS_ALL_FIVE_SCOPED" if rotation_ok else "SOME_CLIENT_ROTATION_FAILURES"
    result["total_client_outer_record"]={
        "first_record_wire_bytes":first_all,
        "cosmetic_accepted_repeat_record_wire_bytes":repeat_all,
        "cosmetic_repeat_mbps_over_1800s":mbps(repeat_all,1800),
        "cosmetic_R_div_F_plus_R_pct":round(100*repeat_all/(first_all+repeat_all),5)
                                    if first_all+repeat_all else None,
        "R_div_F_plus_R_plus_C":"NOT_MEASURED",
        "per_direction_server_cosmetic_attribution":"NOT_AVAILABLE_FROM_SERVER_COLD_LOGS"}
    result["alert_count"]=len(result["alerts"])
    result["performance_verdict"]="ALERTS_PRESENT" if result["alerts"] else "NO_CONFIGURED_ALERTS"
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True)
    p.add_argument("--product-log",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=analyze(pathlib.Path(args.art),args.product_log)
    pathlib.Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print("H1274_ARM64_30MIN_REAL_SOURCE",result["source_sha"],result["scene"],
          "rotation",result["rotation_verdict"],
          "cosmetic",result["total_client_outer_record"],
          "alerts",result["alert_count"],flush=True)

if __name__=="__main__":
    main()
