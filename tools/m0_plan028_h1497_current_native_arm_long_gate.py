#!/usr/bin/env python3
"""PLAN028 current-source L3: real 1800s both-end ARM64 original native TUN.

Original legacy H1274 report parsed only initial server M4 banners. This
forensic gate matches exact authenticated original new-generation ports to
initial real M4 or server verified B-client kind0, with a no-collision guard.
Any B_UNPROVEN, 0%-damage missing UDP, 15s+ active user blackout, missing
owned Stop or missing Game group rekey is a hard defect, not a PASS.
"""
import argparse
import collections
import json
import pathlib
import re

NAMES=("alice","bob","carol","dave","erin")
NORMAL=("alice","bob","erin")
PHYSICAL={
 "baseline":([0,0,1,1,5],[0,0,15,20,50]),
 "heterogeneous":([0,1,5,15,30],[0,15,50,100,125]),
}
def read(p):return json.loads(p.read_text())
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--art",required=True,type=pathlib.Path)
    parser.add_argument("--source",required=True)
    parser.add_argument("--scene",choices=("baseline","heterogeneous"),required=True)
    parser.add_argument("--out",required=True,type=pathlib.Path)
    a=parser.parse_args();root=a.art
    p=read(root/"h1250-matrix-plan.json")
    assert p["source_sha"]==a.source
    assert p["long_scene"]==a.scene
    assert p["application_load_seconds"]==1800 and p["simultaneous_stress_seconds"]==1790
    assert p["network_scope"]=="native Linux aarch64/aarch64 6-netns"
    assert p["fec_backend_choice"]=="native"
    assert p["physical_l2_arp_control"]=="test_only_permanent_actual_peer_mac"
    assert [x["who"] for x in p["clients"]]==list(NAMES)
    loss,delay=PHYSICAL[a.scene]
    assert [x["loss_pct"] for x in p["clients"]]==loss
    assert [x["oneway_delay_ms"] for x in p["clients"]]==delay
    original=read(root/"h1274-thirty-minute-report.json")
    assert original["source_sha"]==a.source and original["duration_seconds"]==1800
    logs={who:(root/f"h1250-product-{who}.log").read_text(errors="replace")
          for who in ("server",)+NAMES}
    errors=[]
    for who,txt in logs.items():
        if "V4_PUBLIC_SHARED_TUN_STOP generation=" not in txt:errors.append(who+"_NATIVE_OWNER_STOP_MISSING")
    server=logs["server"]
    initial=set((ip,int(port)) for ip,port in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_READY role=server port=443 client_ipv4=([\d.]+) client_port=(\d+)",server))
    health_proven=set(int(port) for port in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server client_port=(\d+) source=authenticated_client_native_Health promoted=1",server))
    health_unproven=set(int(port) for port in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_UNPROVEN role=server client_port=(\d+)",server))
    health_pending=set(int(port) for port in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_PENDING role=server client_port=(\d+)",server))
    if health_unproven&health_proven: errors.append("SAME_B_BOTH_UNPROVEN_AND_PROMOTED")
    if health_proven-health_pending: errors.append("SERVER_B_PROMOTED_WITHOUT_PENDING")
    proofs={};ports=collections.defaultdict(list)
    for who in NORMAL:
        matched=[(int(gen),ip,int(port)) for gen,ip,port in re.findall(
           r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+).*?client_ipv4=([\d.]+) client_port=(\d+)",logs[who])]
        old=[int(v) for v in re.findall(
           r"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)",logs[who])]
        if len(matched)<11 or not matched or matched[0][0]!=1:
            errors.append(who+"_NORMAL_MIN_10_REAL_AUTH_REAUTH_NOT_PROVEN")
        if old!=[gen for gen,_,_ in matched[:-1]]:
            errors.append(who+"_NORMAL_EXACT_OLD_GENERATION_STOP_MISMATCH")
        proofs[who]=matched
        for gen,ip,port in matched:ports[port].append((who,gen,ip))
    conflicts={port:vv for port,vv in ports.items() if len(vv)!=1}
    if conflicts:errors.append("NORMAL_CLIENT_PORT_COLLISION_NO_TRUSTED_IP_IN_B_LOG")
    if health_proven-set(ports):errors.append("UNATTRIBUTED_SERVER_B_AUTH_PROOF")
    if health_unproven-set(ports):errors.append("UNATTRIBUTED_SERVER_B_AUTH_FAILURE")
    normal={}
    for who,matches in proofs.items():
        complete=[];unproven=[]
        for gen,ip,port in matches:
            if (ip,port) in initial or (port in health_proven and not conflicts):
                complete.append(gen)
            else:
                unproven.append({"generation":gen,"client_port":port,
                                 "server_explicit_B_UNPROVEN":port in health_unproven})
        normal[who]={"new_native_authenticated_generations":len(matches),
                     "server_native_proof_matched_generations":len(complete),
                     "server_native_B_unproven":unproven}
        if unproven:errors.append(who+"_NEW_NATIVE_READY_SERVER_B_UNPROVEN_"+str(len(unproven)))
    # Game2 group M4 commits and Game4 single-lane swaps are independently
    # verified in the unchanged H1274 original Rust/Go native reporter.
    game={who:original["clients"][who]["rotation"]
          for who in ("carol","dave")}
    for who,v in game.items():
        if v["result"]!="PASS_SCOPED":errors.append(who+"_GAME_REAL_M4_ROTATION_NOT_PROVEN")
    all_udp={}
    for x in p["clients"]:
        who=x["who"]
        cl=read(root/f"h1250-c-{who}.json")
        sv=read(root/f"h1250-s-{who}.json")
        if cl["end_ns"]-cl["start_ns"]!=1800_000_000_000 or sv["end_ns"]-sv["start_ns"]!=1800_000_000_000:
            errors.append(who+"_APP_NOT_REAL1800S")
        directions={}
        for d in ("uplink","downlink"):
            tx,rx=(cl,sv) if d=="uplink" else (sv,cl)
            assert len(tx["stats"]["udp"])==len(rx["stats"]["udp"])==5
            sent=sum(v["tx_packets"] for v in tx["stats"]["udp"])
            got=sum(v["rx_packets"] for v in rx["stats"]["udp"])
            invalid=sum(v["invalid"] for v in rx["stats"]["udp"])
            duplicates=sum(v["duplicates"] for v in rx["stats"]["udp"])
            if not sent or not got or got>sent:errors.append(who+"_"+d+"_BAD_REAL_UNIQUE_DELIVERY")
            if invalid or duplicates:errors.append(who+"_"+d+"_INVALID_OR_DUPLICATE_APP_PACKET")
            if x["loss_pct"]==0 and got!=sent:errors.append(who+"_"+d+"_ZERO_DAMAGE_UNIQUE_MISSING_"+str(sent-got))
            gap=original["clients"][who]["directions"][d]["largest_10ms_bucket_no_receive_while_sender_active_ms"]
            if gap>=15000:errors.append(who+"_"+d+"_ACTIVE_SENDER_NO_RECEIVER_OVER15S")
            directions[d]={"sent":sent,"unique_delivered":got,"missing":sent-got,
                 "invalid":invalid,"duplicates":duplicates,"longest_active_gap_ms":gap}
        all_udp[who]=directions
    queue={}
    for ip,offered,direct,full,overflow in re.findall(
       r"M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=([\d.]+) offered=(\d+) direct_delivered=(\d+) downstream_full=(\d+) pending_overflow=(\d+)",
       server):
        queue[ip]={"offered":int(offered),"direct":int(direct),
                   "full":int(full),"overflow":int(overflow)}
    if set(queue)!={x["lease"] for x in p["clients"]}:errors.append("MISSING_FIVE_SERVER_TUN_LEASE_QUEUE")
    if any(x["overflow"] for x in queue.values()):errors.append("SERVER_QUEUE_OVERFLOW")
    v={"schema_version":1,"plan":"PLAN028","source_sha":a.source,
       "architecture":"true_native_ARM64_two_endpoint_original_TLS_Go_Rust_ISAL",
       "scene":a.scene,"app_seconds":1800,"physical_loss_pct":loss,"physical_oneway_ms":delay,
       "native_server_initial_M4_count":len(initial),
       "native_server_B_authenticated_client_health_promotions":len(health_proven),
       "native_server_B_UNPROVEN_count":len(health_unproven),
       "normal_exact_original_port_and_authenticated_proofs":normal,
       "game2_game4_actual_native_rotations":{w:x["result"] for w,x in game.items()},
       "actual_original_app_udp_all_clients":all_udp,
       "original_server_per_lease_queue":queue,
       "original_cpu_rss":read(root/"h1250-cpu-rss.json"),
       "all_owned_native_Stop":not any("STOP" in e for e in errors),
       "hard_gate_errors":errors,
       "classification":"PASS_SCOPED_TRUE_NATIVE_1800S_"+a.scene.upper() if not errors else
                        "FAIL_SCOPED_TRUE_NATIVE_1800S_"+a.scene.upper(),
       "cautions":["No current Windows independently managed 1800s driver qualification",
                   "30%-damage FEC fixed6 residual UDP must be reported, cannot silently call zero",
                   "Capacity/CPU only from exact separate L2 original source, not a cross-run optimization claim",
                   "Original H1274 initial-only mixed Normal M4 banner false alarms not used as server proof",
                   "Genuine B_UNPROVEN and active gaps >=15s are hard failures"],
       "plan028":"IN_PROGRESS"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(v,indent=2)+"\n")
    print("H1497_REAL_NATIVE_1800S_FINAL_SOURCE_L3_VERDICT",json.dumps({
      "scene":a.scene,"classification":v["classification"],
      "serverB":len(health_proven),"unproven":len(health_unproven),
      "defects":errors},sort_keys=True))
    if errors:raise SystemExit(1)
if __name__=="__main__":main()
