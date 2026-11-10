#!/usr/bin/env python3
"""H1495: immutable H1491/H1492/H1493 native ARM64 ZIP forensic replay.

Does not change original Action outcomes. Distinguishes actual server native
B Health proof from old M4_READY-only reporter. Cold B proof is exact original
port; first ensure NO cross-client port collisions. A 30%-loss B_UNPROVEN is
a real missing authenticated receiver proof, never automatically PASS.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import zipfile

SOURCE="57b0d0cded995cf26b6f8ea43a3d4588e6e61d27"
ORIGINAL_GO="a7a82db31fe736ffedee330795a3234d358f1984"
FILES={
 "capacity":("b6f47708245416255edd92239d964956b057171edde64d101675f827a791f431",13695371981,42660921771),
 "heterogeneous":("8f4a91e701d08647cd85bab3975c40176d7a4ec5fba295d8588c5c679a712437",13697040991,42660921499),
 "baseline":("0ab86404895523f58f6c9f09690eac7c477460176c44f1683ac7768dd4408477",13697290581,42660921629),
}
NAMES=("alice","bob","carol","dave","erin")
NORMAL=("alice","bob","erin")

def load(z,name):
    return json.loads(z.read(name))
def guard_zip(path,kind):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==FILES[kind][0],kind+"_immutable_ZIP_SHA"
    z=zipfile.ZipFile(path)
    assert z.testzip() is None,kind+"_ZIP_CRC"
    m=load(z,"fixed-build/manifest.json")
    assert m["source_sha"]==SOURCE and m["original_go_sha"]==ORIGINAL_GO
    assert m["architecture"]=="native_aarch64" and m["native_fec_acceleration"] is True
    assert m["isa_l_source"]=="c387163fcbca62701d646149564c550c78a4f985"
    return z

def app_counts(z,prefix):
    out={}
    for who in NAMES:
        c=load(z,prefix+"h1250-c-"+who+".json")
        s=load(z,prefix+"h1250-s-"+who+".json")
        assert c["role"]=="client" and s["role"]=="server"
        directions={}
        for direction in ("uplink","downlink"):
            tx,rx=(c,s) if direction=="uplink" else (s,c)
            assert len(tx["stats"]["udp"])==len(rx["stats"]["udp"])==5
            sent=sum(v["tx_packets"] for v in tx["stats"]["udp"])
            got=sum(v["rx_packets"] for v in rx["stats"]["udp"])
            assert sent>0 and got>0 and sent>=got
            directions[direction]={"sent":sent,"unique_delivered":got,"missing":sent-got}
        out[who]=directions
    return out

def leases_and_stops(z,prefix,plan):
    logs={who:z.read(prefix+"h1250-product-"+who+".log").decode(errors="replace")
          for who in ("server",)+NAMES}
    for who,log in logs.items():
        assert "V4_PUBLIC_SHARED_TUN_STOP generation=" in log,who+"_native_owned_Stop"
    q={}
    for match in re.findall(
      r"M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=([\d.]+) offered=(\d+) direct_delivered=(\d+) downstream_full=(\d+) pending_overflow=(\d+) pending_byte_limit=(\d+) pending_peak_packets=(\d+) pending_peak_bytes=(\d+)",
      logs["server"]):
        ip,offered,direct,full,overflow,bytes_drop,peak,peak_b=match
        q[ip]={"offered":int(offered),"direct":int(direct),
               "downstream_full":int(full),"pending_overflow":int(overflow),
               "pending_byte_limit":int(bytes_drop),"pending_peak_packets":int(peak),
               "pending_peak_bytes":int(peak_b)}
    assert set(q)=={x["lease"] for x in plan["clients"]},"all_five_server_shared_lease_queue"
    assert all(x["pending_peak_packets"]<=8 and x["pending_peak_bytes"]<=65536 for x in q.values())
    return logs,q

def proof_original_long(z,prefix,plan,logs):
    server=logs["server"]
    initial=set((ip,int(port)) for ip,port in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_READY role=server port=443 client_ipv4=([\d.]+) client_port=(\d+)",server))
    promoted=set(int(v) for v in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY role=server client_port=(\d+) source=authenticated_client_native_Health promoted=1",server))
    unproven=set(int(v) for v in re.findall(
       r"V4_PUBLIC_MIXED_NORMAL_B_UNPROVEN role=server client_port=(\d+)",server))
    assert not promoted&unproven,"same B cannot be proven and unproven"
    ports=collections.defaultdict(list)
    per_who={}
    for who in NORMAL:
        proof=[(int(g),ip,int(port)) for g,ip,port in re.findall(
           r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=(\d+).*?client_ipv4=([\d.]+) client_port=(\d+)",logs[who])]
        assert proof and proof[0][0]==1 and len(proof)>=11
        for gen,ip,port in proof:
            ports[port].append((who,gen,ip))
        per_who[who]=proof
        old=[int(x) for x in re.findall(
          r"V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=(\d+)",logs[who])]
        assert old==[gen for gen,_,_ in proof[:-1]],who+"_exact_old_generation_Stop"
    collisions={str(port):rows for port,rows in ports.items() if len(rows)!=1}
    assert not collisions,("cannot use port-only server B evidence with collisions",collisions)
    assert promoted<=set(ports),"server unexpected promoted port"
    # Server may publish an initial M4 without a previous A. For an
    # overlapping B, client Ready proves nothing unless server emitted the
    # SAME original client port's verified Health native promotion.
    results={}
    for who,proof in per_who.items():
        good=[g for g,ip,port in proof if (ip,port) in initial or port in promoted]
        bad=[{"generation":g,"client_port":port,"server_B_UNPROVEN":port in unproven}
             for g,ip,port in proof if (ip,port) not in initial and port not in promoted]
        results[who]={"client_native_ready_generations":len(proof),
           "original_server_native_authenticated_commits":len(good),
           "server_rejected_or_unproved_B":bad,
           "all_server_B_proven":not bad,
           "actual_owned_old_stops":len(proof)-1}
    assert sum(len(x["server_rejected_or_unproved_B"]) for x in results.values())==len(unproven)
    return {"server_initial_normal_M4":len(initial),
            "server_auth_client_Health_B_promotions":len(promoted),
            "server_auth_client_Health_B_UNPROVEN":len(unproven),
            "normal_per_client":results,
            "exact_port_unique_across_all_normal_ready":True}

def review_long(path,kind):
    with guard_zip(path,kind) as z:
        p="fixed-kernel-result/"
        plan=load(z,p+"h1250-matrix-plan.json")
        assert plan["source_sha"]==SOURCE and plan["long_scene"]==kind
        assert plan["application_load_seconds"]==1800
        assert plan["network_scope"]=="native Linux aarch64/aarch64 6-netns"
        assert len(plan["clients"])==5
        app=app_counts(z,p)
        logs,queues=leases_and_stops(z,p,plan)
        normal=proof_original_long(z,p,plan,logs)
        report=load(z,p+"h1274-thirty-minute-report.json")
        assert report["duration_seconds"]==1800
        actual_loss=[x["loss_pct"] for x in plan["clients"]]
        expected=[0,0,1,1,5] if kind=="baseline" else [0,1,5,15,30]
        assert actual_loss==expected
        zero_users=[x["who"] for x in plan["clients"] if x["loss_pct"]==0]
        zero_loss=all(app[w][d]["missing"]==0 for w in zero_users
                      for d in ("uplink","downlink"))
        game_proof={w:report["clients"][w]["rotation"]["result"] for w in ("carol","dave")}
        assert game_proof=={"carol":"PASS_SCOPED","dave":"PASS_SCOPED"},game_proof
        assert all(queues[x["lease"]]["pending_overflow"]==0 for x in plan["clients"])
        erin_gap={leg:report["clients"]["erin"]["directions"][leg][
            "largest_10ms_bucket_no_receive_while_sender_active_ms"]
            for leg in ("uplink","downlink")}
        if kind=="baseline":
            assert normal["server_auth_client_Health_B_UNPROVEN"]==0
            assert normal["server_auth_client_Health_B_promotions"]>=60
            assert all(v["all_server_B_proven"] for v in normal["normal_per_client"].values())
            assert zero_loss
            classification="PASS_SCOPED_REAL_1800S_NATIVE_ARM64_BASELINE_ALL_NORMAL_GAME_HANDOFFS"
        else:
            assert normal["server_auth_client_Health_B_UNPROVEN"]==12
            assert len(normal["normal_per_client"]["erin"]["server_rejected_or_unproved_B"])==12
            assert erin_gap["downlink"]>=750 and erin_gap["uplink"]>=750
            assert zero_loss
            classification="FAIL_PRODUCT_30PCT_ERIN_NORMAL_FIXED6_CLIENT_SERVER_B_DESYNC"
        return {"kind":kind,"original_action_id":FILES[kind][2],
            "original_artifact_id":FILES[kind][1],
            "original_action_conclusion":"FAIL_RETAINED",
            "original_zip_sha256":FILES[kind][0],"zip_crc":"PASS",
            "original_source_sha":SOURCE,"classification":classification,
            "original_5_client_udp":app,"original_six_exact_owned_Stop":True,
            "physical_loss_pct_by_client":actual_loss,"zero_damage_clients_zero_unique_udp":zero_loss,
            "per_client_server_shared_TUN_queue":queues,
            "new_B_original_native_evidence":normal,"Game2_Game4_rotations":game_proof,
            "Erin_longest_active_10ms_no_receive_gap_ms":erin_gap,
            "not_product_pass_if_false_reporter_marker":kind=="heterogeneous"}
def review_capacity(path):
    with guard_zip(path,"capacity") as z:
        results={}
        for case,n in (("capacity50","h1491-control"),("capacity_mixed","h1491-75")):
            v=load(z,"result/"+n+".json")
            assert v["source_sha"]==SOURCE and v["case"]==case
            assert v["classification"]=="PASS_SCOPED_ZEROLOSS_TRUE_ORIGINAL_NATIVE"
            assert v["host_cpu"]["result"]=="MEASURED"
            assert v["all_six_original_owned_Stop"]
            assert not v["measured_defects"]
            assert all(not x["directions"][d]["missing"] and not x["server_lease_queue"]["overflow"]
                       for x in v["real_UDP_and_lease_queue_by_user"].values()
                       for d in ("uplink","downlink"))
            prefix="paired/"+case+"/"
            plan=load(z,prefix+"h1250-matrix-plan.json")
            assert all(x["loss_pct"]==0 for x in plan["clients"])
            app=app_counts(z,prefix)
            logs,queues=leases_and_stops(z,prefix,plan)
            results[case]={"classification":v["classification"],
              "original_five_client_udp":app,
              "host_mean_busy_pct":v["host_cpu"]["mean_core_busy_pct"],
              "host_max_busy_pct":v["host_cpu"]["max_core_busy_pct"],
              "original_Native_CPU_RSS":v["all_process_cpu_rss"],
              "alice_actual_offered_mbps":v["actual_alice_mbps"],
              "all_6_original_Stop":True,
              "server_shared_queue":queues}
        assert [round(x["offered_mbps"]) for x in results["capacity_mixed"]["alice_actual_offered_mbps"]]==[30,50,75,50]
        return {"kind":"capacity","original_action_id":FILES["capacity"][2],
          "original_artifact_id":FILES["capacity"][1],
          "original_zip_sha256":FILES["capacity"][0],"zip_crc":"PASS",
          "original_source_sha":SOURCE,
          "classification":"PASS_SCOPED_SAME_VM_SEQUENTIAL_50_AND_75_REAL_NATIVE_ZEROLOSS",
          "actual_results":results,
          "old_rapid_rotation_alerts":"FALSE_ALERT_NO_ROTATION_BY_DESIGN_3600S_NOT_TESTED"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--capacity",required=True,type=pathlib.Path)
    parser.add_argument("--heterogeneous",required=True,type=pathlib.Path)
    parser.add_argument("--baseline",required=True,type=pathlib.Path)
    parser.add_argument("--out",required=True,type=pathlib.Path)
    a=parser.parse_args()
    outcomes=[review_capacity(a.capacity),
              review_long(a.heterogeneous,"heterogeneous"),
              review_long(a.baseline,"baseline")]
    v={"schema_version":1,"role_id":"M0","plan":"PLAN028",
       "source_sha":SOURCE,
       "review":"H1495 ORIGINAL THREE TRUE NATIVE ARM64 IMMUTABLE ZIP REPLAY",
       "old_actions_immutable":True,"all_zip_crc_sha_checked":True,
       "new_network_tests":0,"product_changed_during_replay":False,
       "original_runs":outcomes,
       "restrictions":["H1492 30pct Erin 12 original authenticated B_UNPROVEN and 72.7/128.9s gaps are real FAIL",
                       "H1493 original Action remains FAIL from obsolete M4 reporter even when native scope passes",
                       "30pct wire loss does not imply business zero-loss hard gate; genuine blackouts are retained",
                       "H1491 no-rotation schedule at 3600s is intentional L2 not L3 rotation",
                       "Windows Wintun/Npcap full independent managed DUT 1800s is NOT_QUALIFIED",
                       "Android/physical WAN NOT_RUN","PLAN028 IN_PROGRESS"]}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(v,indent=2)+"\n")
    print("H1495_THREE_IMMUTABLE_NATIVE_ARM64_ZIPS_OFFLINE_CAPACITY_PASS_BASELINE_PASS_HETERO_ERIN_FAIL")
if __name__=="__main__":main()
