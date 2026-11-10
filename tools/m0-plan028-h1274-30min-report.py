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
MID600_PHASES=(("warmup",10,.3),("first_wave",90,1/3),
               ("sustained",180,2/3),("overload",90,1.),
               ("recovery",230,2/3))
H1520_OUTER_PHASES=(("warmup",10,.3),("first_wave",90,.6),
                    ("sustained",180,1.0),("overload",90,1.10),
                    ("recovery",230,1.0))

def read(path):
    return json.loads(pathlib.Path(path).read_text())

def count(line,name):
    match=re.search(r"\b"+re.escape(name)+r"=(\d+)",line)
    return int(match.group(1)) if match else None

def mbps(bytes_count,seconds):
    return round(8*bytes_count/(seconds*1e6),5)

def outer_counts(log,mode,duration=1800):
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
        "cosmetic_accepted_repeat_mbps_over_1800s":mbps(repeat,duration),
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
    for minute in range(len(tx)//6000):
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

def normal_m4_server_proof(server_text):
    # Only exact original protected Rust M4 Ready counts, not ordinary TLS
    # completion, local client Ready, or a guessed source port.
    commits=set((ip,int(port)) for ip,port in re.findall(
        r"V4_PUBLIC_MIXED_NORMAL_READY role=server port=443 client_ipv4=([\d.]+) client_port=(\d+)",
        server_text))
    rejects={(ip,int(port)):(stage,int(rc)) for stage,rc,ip,port in re.findall(
        r"V4_PUBLIC_MIXED_ADMISSION_REJECT stage=normal_rust_owner m4_stage=([a-z_]+) native_rc=(-?\d+) class=[^\s]+ client_ipv4=([\d.]+) client_port=(\d+)",
        server_text)}
    return commits,rejects


def normal_m4_client_proof(client_text):
    return [(int(gen),ip,int(port)) for gen,ip,port in re.findall(
        r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+).*?client_ipv4=([\d.]+) client_port=(\d+)",
        client_text)]


def analyze(art,server_log):
    plan=read(art/"h1250-matrix-plan.json")
    assert plan["long_scene"] in ("baseline","heterogeneous","pressure")
    duration=plan["application_load_seconds"]
    assert duration in (600,1800)
    midsix=duration==600
    h1531=plan.get("H1531_outer_600_profile") in ("outer300to350-loss0","outer300to350-loss30")
    h1520=(plan.get("H1520_outer_600_profile") in (
        "outer100to150-loss0","outer100to150-loss30")) or h1531
    phase_specs=(H1520_OUTER_PHASES if h1520 else MID600_PHASES) if midsix else PHASES
    if midsix:
        assert plan["simultaneous_stress_seconds"]==590
        assert plan["long_scene"]=="baseline"
        if h1520:
            if h1531:
                assert plan["H1531_outer_target_mbps_total_both_directions"]==[300,350]
                expected=(28,20,14,6,14) if plan["H1531_outer_600_profile"].endswith("loss30") else (20,14,10,6,10)
            else:
                assert plan["H1520_outer_target_mbps_total_both_directions"]==[100,150]
                expected=(12,8,6,3,6)
            assert [round(v["c2s_target_mbps"],3) for v in plan["clients"]]==list(expected)
            loss=30 if (plan["H1531_outer_600_profile"] if h1531 else plan["H1520_outer_600_profile"]).endswith("loss30") else 0
            assert [v["loss_pct"] for v in plan["clients"]]==[loss]*5
            assert [v["oneway_delay_ms"] for v in plan["clients"]]==[200]*5
        else:
            assert plan.get("H1461_600s_capacity75_profile")=="EXACT_600S_FIVE_CLIENT_ZEROLOSS_25_50_75_50_NO_ROTATION"
            assert [round(v["c2s_target_mbps"],3) for v in plan["clients"]]==[75,2,2,2,2]
    else:
        assert plan["simultaneous_stress_seconds"]==1790
    assert sum(p[1] for p in phase_specs)==duration
    assert len(plan["clients"])==5
    assert {p["who"] for p in plan["clients"]}==set(NAMES)
    cpu=read(art/"h1250-cpu-rss.json")
    qdisc=tc_stats(art/"h1250-qdisc-after.txt")
    server_text=pathlib.Path(server_log).read_text(errors="replace")
    per_lease=per_lease_tun_stop_counters(server_text)
    # Retired original real TLS groups: server native M4 commit is a
    # separate observation from a client's local candidate READY.
    server_game2_ports=set(
        (int(lane),int(port)) for lane,port in re.findall(
            r"V4_PUBLIC_GAME_GROUP_LANE_READY role=server lanes=2 lane=(\d+) client_port=(\d+)",
            server_text))
    server_game4_hot_ports=set(
        (int(lane),int(port)) for lane,port in re.findall(
            r"V4_PUBLIC_GAME_SINGLE_LANE_READY role=server lane=(\d+) rotation=\d+ client_port=(\d+)",
            server_text))
    # A local client Ready/old Stop is not a remote M4 commit. H1279
    # pressure Alice Gen11: client Ready + exact old Stop, but the original
    # server rejected normal_rust_owner, so the entire 73.3s generation had
    # zero raw receive and no business. Match independently observed protected
    # server-native success by the exact physical IPv4+TCP source port.
    server_normal_m4,server_normal_reject=normal_m4_server_proof(server_text)
    result={
        "schema_version":1,"checkpoint":"H1461_600" if midsix else "H1274",
        "source_sha":plan["source_sha"],"scene":plan["long_scene"],
        "result":"DIAGNOSTIC_COMPLETE","architecture":plan["network_scope"],
        "duration_seconds":duration,"clients":{},"alerts":[],
        "actual_physical_qdisc":qdisc,
        "physical_l2_arp_control":plan.get("physical_l2_arp_control","historical_unspecified"),
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
        assert source["end_ns"]-source["start_ns"]==duration*1_000_000_000
        assert peer["end_ns"]-peer["start_ns"]==duration*1_000_000_000
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
        lease_stable=bool(leases) and set(leases)=={spec["lease"]}
        native_stop="V4_PUBLIC_SHARED_TUN_STOP generation=" in text
        if midsix and not h1520:
            # This 600s capacity experiment deliberately parks L1 timers
            # at 3600s. Never mistake a missing rotation for an 1800s L3
            # handoff PASS; verify the genuine initial native server M4.
            if spec["mode"]=="game2":
                committed=bool(server_game2_ports)
            elif spec["mode"]=="game4":
                # Initial authenticated 4-lane group uses the original M4
                # cohort, not the later per-lane hot-rotation witness.
                committed=("V4_PUBLIC_GAME_GROUP_LANE_READY role=server lanes=4" in server_text
                           or "V4_PUBLIC_GAME_SINGLE_LANE_READY role=server" in server_text)
            else:
                initial=normal_m4_client_proof(text)
                committed=(bool(initial) and all((ip,port) in server_normal_m4
                           for _,ip,port in initial))
            passed=(ready==[1] and not old and not timer and lease_stable
                    and native_stop and committed)
            rotation={"unit":"NO_ROTATION_BY_DESIGN_600S_ONLY",
                      "result":"PASS_SCOPED" if passed else "FAIL_OR_INCOMPLETE",
                      "native_final_stop_observed":native_stop,
                      "authenticated_initial_server_M4":committed,
                      "same_authenticated_lease":lease_stable,
                      "no_timer_events":len(timer)==0,
                      "h1461_full_1800s_handoff":"NOT_QUALIFIED"}
        elif spec["mode"]=="game4":
            # Game4 rotates one protected lane IN the same group. The
            # whole-group generation deliberately remains 1, and there is
            # no old group Stop for individual slot replacement.
            slots=[(int(lane),int(port)) for lane,port in re.findall(
                r"V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_READY role=client generation=\d+ lane=(\d+) new_client_port=(\d+)",
                text)]
            due=[line for line in text.splitlines()
                 if "V4_PUBLIC_GAME_SINGLE_LANE_DUE role=client" in line]
            deferred=text.count("V4_PUBLIC_GAME_SINGLE_LANE_COLD_DEFERRED role=client")
            matched=sum(1 for row in slots if row in server_game4_hot_ports)
            correct_physical=bool(due) and all("unchanged_path=1" in line for line in due)
            enough=(len(slots)>=(4 if h1520 else 10)
                    and {lane for lane,_ in slots}=={1,2,3,4})
            passed=(ready==[1] and not old and correct_physical and enough
                    and matched==len(slots) and len(due)==len(slots)+deferred
                    and lease_stable and native_stop)
            rotation={
                "unit":"one_original_authenticated_Game4_lane_at_a_time",
                "result":"PASS_SCOPED" if passed else "FAIL_OR_INCOMPLETE",
                "authenticated_group_generation_sequence":ready,
                "old_group_stop_sequence":old,
                "single_lane_successful":len(slots),"single_lane_attempted":len(due),
                "single_lane_deferred_cold_tls":deferred,
                "native_server_confirmed_hot_slots":matched,
                "per_lane_success":{str(lane):sum(1 for x,_ in slots if x==lane)
                                    for lane in range(1,5)},
                "same_authenticated_lease":lease_stable,
                "physical_ipv4_unchanged":correct_physical,
                "native_final_stop_observed":native_stop,
                "minimum_ten_true_successful_handoffs":enough if not h1520 else None,
                "minimum_four_true_successful_handoffs":enough if h1520 else None
            }
        else:
            # Failed candidate TLS consumes generation IDs, but only
            # successfully COMMITTED generations are required to increase
            # strictly and retire the exact former owner.
            correct_physical=bool(timer) and all(
                "same_physical_interface_ipv4=true" in line
                and "unchanged_path=true" in line for line in timer)
            increasing=bool(ready) and ready[0]==1 and all(
                b>a for a,b in zip(ready,ready[1:]))
            exact_stop=old==ready[:-1]
            minimum=4 if h1520 else 10
            enough=len(ready)>=minimum+1 and len(old)>=minimum and len(timer)>=minimum
            passed=all((correct_physical,increasing,exact_stop,enough,
                        lease_stable,native_stop))
            rotation={
                "unit":"whole_group_authenticated_TLS_Rust_replacement",
                "result":"PASS_SCOPED" if passed else "FAIL_OR_INCOMPLETE",
                "authenticated_generation_sequence":ready,
                "old_generation_stop_sequence":old,
                "timer_events":len(timer),
                "failed_cold_candidates":text.count("V4_PUBLIC_PATH_CANDIDATE_FAILED role=client"),
                "configured_interval_s":plan["rotation_seconds"][who],
                "strictly_increasing_successful_ids":increasing,
                "exact_old_owner_stop":exact_stop,
                "same_authenticated_lease":lease_stable,
                "physical_ipv4_unchanged":correct_physical,
                "native_final_stop_observed":native_stop,
                "minimum_ten_true_successful_handoffs":enough if not h1520 else None,
                "minimum_four_true_successful_handoffs":enough if h1520 else None
            }
            if spec["mode"] not in ("game2","game4"):
                # For all Normal Off / Auto / Fixed6 modes, require
                # independently observed server M4 success for every
                # client-promoted generation; never infer it from local
                # FakeTCP/TLS Ready or client-only exact old Stop.
                scoped=normal_m4_client_proof(text)
                missing=[gen for gen,ip,port in scoped
                         if (ip,port) not in server_normal_m4]
                failed=[{"generation":gen,"stage":server_normal_reject[(ip,port)][0],
                         "native_rc":server_normal_reject[(ip,port)][1]}
                        for gen,ip,port in scoped
                        if (ip,port) in server_normal_reject]
                rotation["server_normal_m4_commits_observed"]=len(scoped)-len(missing)
                rotation["client_ready_but_server_normal_m4_missing"]=missing
                rotation["server_normal_m4_rejections"]=failed
                if not scoped or len(scoped)!=len(ready) or missing or failed:
                    result["alerts"].append({
                        "who":who,"kind":"CLIENT_NORMAL_READY_WITHOUT_SERVER_NATIVE_M4",
                        "generation_ids":missing,
                        "reported_client_generations":len(ready),
                        "exact_port_proofs":len(scoped),
                        "server_rejections":failed})
                    passed=False
                    rotation["result"]="FAIL_SERVER_NORMAL_M4_COMMIT_MISSING"
            if spec["mode"]=="game2":
                # Existing authenticated Go TLS can return client READY
                # before the other endpoint commits the two-lane M4 cohort.
                # Comparing original distinct TCP ports detects that gap
                # without adding any new wire protocol or traffic probe.
                groups={}
                for gen,lane,port in re.findall(
                    r"V4_PUBLIC_GAME_GROUP_LANE_READY role=client group_generation=(\d+) lane=(\d+) local_port=(\d+)",
                    text):
                    groups.setdefault(int(gen),set()).add((int(lane),int(port)))
                missing=[gen for gen,pairs in groups.items()
                         if len(pairs)!=2 or not pairs.issubset(server_game2_ports)]
                rotation["native_server_cohort_commits_observed"]=len(groups)-len(missing)
                rotation["client_ready_but_server_cohort_not_observed"]=missing
                if missing:
                    result["alerts"].append({
                        "who":who,"kind":"CLIENT_GAME2_READY_WITHOUT_SERVER_NATIVE_COHORT",
                        "generation_ids":missing,
                        "note":"Authentic client local READY and exact old Stop are not sufficient; server never emitted both matching lane M4 commits."})
                    passed=False
                    rotation["result"]="FAIL_SERVER_COMMIT_MISSING"
        rotation_ok=rotation_ok and passed
        if not passed:
            result["alerts"].append({"who":who,"kind":"ROTATION_CONTINUITY_NOT_PROVEN"})
        game=("game4" if spec["mode"]=="game4" else "game2" if spec["mode"]=="game2" else "")
        repeat=outer_counts(text,game,duration)
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
            for i,(name,phase_seconds,rate_scale) in enumerate(phase_specs):
                sent=tx["stats"]["udp"][i]
                got=rx["stats"]["udp"][i]
                n=sent["tx_packets"]
                m=got["rx_packets"]
                phases.append({
                    "phase":name,"seconds":phase_seconds,
                    "actual_udp_sent":n,"unique_udp_delivered":m,
                    "actual_delivery_fraction":round(m/n,6) if n else None,
                    "actual_udp_sent_mbps":mbps(sent["tx_bytes"],phase_seconds),
                    "actual_udp_delivered_mbps":mbps(got["rx_bytes"],phase_seconds),
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
            assert len(phases)==len(phase_specs), "all original app phases required"
            assert sum(x["seconds"] for x in phases)==duration, "source time-varying load cannot be empty"
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
        "cosmetic_repeat_mbps_over_1800s":mbps(repeat_all,duration),
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
