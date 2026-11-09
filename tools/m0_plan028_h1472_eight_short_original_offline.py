#!/usr/bin/env python3
"""Replay eight immutable authentic PLAN028 x86 five-client 180s scenes, OFFLINE.

No original network product is run. This code is a different reviewer SOURCE
from both the old and patched frozen Go TLS443/Rust ISA-L producer sources.
"""
import argparse
import hashlib
import json
import pathlib
import re

NEW="66fb6b4454b1ce4297ab04efa20c7f931ff12383"
OLD="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
DONOR="a7a82db31fe736ffedee330795a3234d358f1984"
ISAL="c387163fcbca62701d646149564c550c78a4f985"
BIN={
  NEW:{"wbd-v4-client":"c2c5531168dfcd62624bd0910b52a606a413bad1eced3f69ce6ac577d66442c1",
       "wbd-v4-server":"3ddbde8284fc1fcfa1af8097e3c8f6724e8f247367676d47f49553f8b293cf42",
       "libwbd_engine.so":"c15070d091e8d45c6c1cccacaa49c2c374a409c4718f2fc7c9370df59d6392b7"},
  OLD:{"wbd-v4-client":"f3b42cba7e3246a5b5fa324f160df0abade58d19414b7d6c43e5b389100c85ea",
       "wbd-v4-server":"bbfc2af8bda9965e5f9f68af0b3a3feba186eca8a5ede07043e991fdf9d97c83",
       "libwbd_engine.so":"ee9aaf3eeb517e4a7b5b73b739eb9b9af75638bd3d5c3e6c4945af7a28fd78f7"}
}
NAMES=("alice","bob","carol","dave","erin")
STOP="V4_PUBLIC_SHARED_TUN_STOP generation="
ART={
 "capacity":{"action":42590018240,"id":13661277093,"zip_sha256":"aa25c612ffcc84d2ed43f3e17ce0ef05e61bd73029b6aa1547d738afcc254e6e"},
 "generation":{"action":42590018240,"id":13660868907,"zip_sha256":"5ccdcc7040becb140bcd258ac333a8b1914fd2e2db97069f3c06f4723414c8b5"},
 "oldnew":{"action":42590601995,"id":13661168078,"zip_sha256":"1650cc938f484958694fa3e8fb1b3f085d1ef9ab227533d9f825f3a936974a21"},
 "newold":{"action":42590601995,"id":13660943781,"zip_sha256":"44eb133d91e910242764cdb99e50b4a7704621f2079b6eb2432ff99ef80ed40a"}
}
FILES=[
 ("capacity","capacity_mixed",NEW,"capacity_mixed"),
 ("capacity","capacity_large",NEW,"capacity_large"),
 ("generation","static12",NEW,"static12"),
 ("generation","rotating12",NEW,"rotating12"),
 ("oldnew","old",OLD,"capacity_mixed"),
 ("oldnew","new",NEW,"capacity_mixed"),
 ("newold","new",NEW,"capacity_mixed"),
 ("newold","old",OLD,"capacity_mixed")
]
QUEUE_RE=re.compile(r"M0_SHARED_TUN_LEASE_QUEUE_DIAG ip=(\d+\.\d+\.\d+\.\d+) offered=(\d+) direct_delivered=(\d+) downstream_full=(\d+) pending_overflow=(\d+) pending_byte_limit=(\d+) pending_peak_packets=(\d+) pending_peak_bytes=(\d+)")

def read(p):
    return json.loads(p.read_text())

def manifest_at(root,case):
    if (root/"paired"/case/"manifest.json").exists():
        return root/"paired"/case/"manifest.json"
    return root/"fixed-build"/"manifest.json"

def verify_manifest(path,source):
    m=read(path)
    assert m["source_sha"]==source,(path,m.get("source_sha"),source)
    assert m["original_go_sha"]==DONOR and m["architecture"]=="native_x86_64"
    if source==NEW:
        assert m["isa_l_source"]==ISAL and m["native_fec_acceleration"] is True
    else:
        # H1360's 6c5 archive predates manifest ISA-L metadata. Do NOT
        # invent a source-c387 readback for it: exact three ELF SHA values
        # plus original per-scene Game4 native_linked=1 are available.
        assert "isa_l_source" not in m and "native_fec_acceleration" not in m
    assert m["sha256"]==BIN[source],(path,"product binary manifest does not match historical source")
    return hashlib.sha256(path.read_bytes()).hexdigest()

def case_inspect(root,folder,source,case):
    art=root/"paired"/folder
    assert art.is_dir(),("archive extraction layout mismatch",art)
    mh=verify_manifest(manifest_at(root,folder),source)
    plan=read(art/"h1250-matrix-plan.json")
    assert plan["source_sha"]==source and plan["h1467_short_ab_case"]==case
    assert plan["application_load_seconds"]==180 and plan["simultaneous_stress_seconds"]==170
    assert plan["network_scope"]=="native Linux x86_64/x86_64 6-netns"
    assert plan["server_port"]==443
    assert [x["who"] for x in plan["clients"]]==list(NAMES)
    assert all(x["loss_pct"]==x["oneway_delay_ms"]==0 for x in plan["clients"])
    assert plan["physical_l2_arp_control"]=="test_only_permanent_actual_peer_mac"
    target=75 if case.startswith("capacity") else 12
    assert [x["c2s_target_mbps"] for x in plan["clients"]]==[target,2,2,2,2]
    assert [x["s2c_target_mbps"] for x in plan["clients"]]==[target,2,2,2,2]
    assert plan["h1467_normal_alice_packet_mix"]==([[1024,1]] if case=="capacity_large" else [[256,3],[1024,7]])
    intended_rotations=(case=="rotating12")
    assert plan["rotation_seconds"]["alice"]==(97 if intended_rotations else 3600)
    original_logs={}
    for who in ("server",)+NAMES:
        logfile=art/("h1250-product-"+who+".log")
        assert logfile.is_file(),logfile
        original_logs[who]=logfile.read_text(errors="replace")
        assert STOP in original_logs[who],("six original owned final Stop required",who,folder)
    assert "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" in original_logs["server"]
    assert "M0_GAME_M4_FEC_BACKEND_READBACK selected=prefer-native native_linked=1" in original_logs["dave"], (
        "Original source-specific native FEC2/ISA-L runtime readback absent",source,folder)
    raw_queue=QUEUE_RE.findall(original_logs["server"])
    assert len(raw_queue)==5,(folder,"expect five distinct original native /32 receipts",raw_queue)
    q={r[0]:{"offered":int(r[1]),"direct_delivered":int(r[2]),"downstream_full":int(r[3]),
             "pending_overflow":int(r[4]),"pending_byte_limit":int(r[5]),
             "pending_peak_packets":int(r[6]),"pending_peak_bytes":int(r[7])} for r in raw_queue}
    assert len(q)==5 and all(row["pending_peak_packets"]<=8 and row["pending_peak_bytes"]<=65536 for row in q.values())
    phase_plan=[("warmup",10,.3)]+[(x["name"],x["seconds"],x["rate_scale"]) for x in plan["capacity_phase_schedule"]]
    assert sum(x[1] for x in phase_plan)==180 and len(phase_plan)==5
    cpu=read(art/"h1250-cpu-rss.json")
    rapid=read(art/"h1286-rapid-report.json")
    assert rapid["source_sha"]==source and rapid["duration_seconds"]==180
    if intended_rotations:
        assert rapid["rotation_verdict"]=="PASS_ALL_FIVE_SCOPED" and rapid["alert_count"]==0
    else:
        assert rapid["rotation_verdict"]=="SOME_CLIENT_ROTATION_FAILURES"
        assert all(e["kind"] in ("ROTATION_CONTINUITY_NOT_PROVEN","SERVER_PER_LEASE_QUEUE_OVERFLOW")
                   for e in rapid["alerts"]),rapid["alerts"]
    records={}
    for spec in plan["clients"]:
        who=spec["who"]
        c=read(art/("h1250-c-"+who+".json"))
        s=read(art/("h1250-s-"+who+".json"))
        assert c["role"]=="client" and s["role"]=="server"
        assert c["end_ns"]-c["start_ns"]==s["end_ns"]-s["start_ns"]==180_000_000_000
        dirs={}
        for name in ("uplink","downlink"):
            tx,rx=(c,s) if name=="uplink" else (s,c)
            assert len(tx["stats"]["udp"])==len(rx["stats"]["udp"])==len(phase_plan)
            phases=[]
            for i,(phase,secs,scale) in enumerate(phase_plan):
                t=tx["stats"]["udp"][i];r=rx["stats"]["udp"][i]
                assert t["phase"]==r["phase"]==phase
                phases.append({"phase":phase,"seconds":secs,
                               "unique_udp_tx":t["tx_packets"],"unique_udp_rx":r["rx_packets"],
                               "missing":t["tx_packets"]-r["rx_packets"],
                               "offered_udp_mbps":round(t["tx_bytes"]*8/(secs*1e6),4),
                               "actual_udp_rx_mbps":round(r["rx_bytes"]*8/(secs*1e6),4)})
            dirs[name]={"phases":phases,"total_missing":sum(x["missing"] for x in phases),
                        "total_sent":sum(x["unique_udp_tx"] for x in phases),
                        "total_unique_delivered":sum(x["unique_udp_rx"] for x in phases)}
        records[who]={"lease":spec["lease"],"mode":spec["mode"],
                      "source_s2c_queue":q[spec["lease"]],"directions":dirs,
                      "original_client_generations":original_logs[who].count("V4_PUBLIC_PATH_NEW_GENERATION_READY role=client"),
                      "original_old_exact_Stop":original_logs[who].count("V4_PUBLIC_PATH_OLD_EXACT_STOP role=client")}
    if intended_rotations:
        assert records["alice"]["original_client_generations"]>=2
        assert records["alice"]["original_old_exact_Stop"]>=1
    else:
        assert records["alice"]["original_client_generations"]==1
        assert records["alice"]["original_old_exact_Stop"]==0
    alice=records["alice"]
    allevents=sum(v["directions"][direction]["total_missing"] for v in records.values() for direction in ("uplink","downlink"))
    alloverflow=sum(v["source_s2c_queue"]["pending_overflow"] for v in records.values())
    assert allevents>=0 and alloverflow>=0
    return {
      "source_sha":source,"case":case,"manifest_sha256":mh,
      "original_application_seconds":180,"original_authenticated_five_clients":True,
      "original_six_owned_final_Stops":True,
      "rotation_qualifier":("PASS_SCOPED_AUTHENTIC_M4" if intended_rotations else "NOT_REQUESTED_NOT_FAIL"),
      "original_H1286_raw_alert_count":rapid["alert_count"],
      "original_H1286_raw_alerts":rapid["alerts"],
      "original_alice_server_queue_overflow":alice["source_s2c_queue"]["pending_overflow"],
      "all_five_server_lease_queue_overflow":alloverflow,
      "original_alice_DL_missing":alice["directions"]["downlink"]["total_missing"],
      "original_alice_UL_missing":alice["directions"]["uplink"]["total_missing"],
      "original_total_unique_UDP_missing":allevents,
      "strict_zero_loss":"PASS_SCOPED" if allevents==0 and alloverflow==0 else "FAIL_SCOPED",
      "actual_process_cpu_onecore_pct":{who:cpu[who]["average_one_core_cpu_percent"] for who in ("server",)+NAMES},
      "original_per_user":records,
      "raw_worker_500ms_samples":{"client_alice":original_logs["alice"].count("V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG"),
                                   "server":original_logs["server"].count("V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG")},
      "limitations":["180-second Linux native 6-netns, not formal Windows L3 1800",
                     "0%-netem does not guarantee underlying kernel zero drops",
                     "single same-host A/B per order cannot alone prove root cause"]
    }

def replay(root, out, reviewer):
    assert len(reviewer)==40 and reviewer not in (NEW,OLD)
    observed={}
    for subdir,folder,source,case in FILES:
        observed[f"{subdir}/{folder}"]=case_inspect(root/subdir,folder,source,case)
    get=lambda k:observed[k]
    # Source-frozen original action-specific negative controls; fail closed on
    # wrong archive, silent truncation, lost per-user stop, or false green.
    for k in ("capacity/capacity_mixed","capacity/capacity_large",
              "generation/static12","oldnew/old","oldnew/new"):
        assert get(k)["strict_zero_loss"]=="PASS_SCOPED",(k,get(k)["original_total_unique_UDP_missing"])
    # Zero app UDP does not imply zero internal original TUN queue loss:
    # newold/new delivered all app UDP, but its original server overflowed
    # 32 packets in an authenticated per-lease queue on this one host.
    new_jitter=get("newold/new")
    assert (new_jitter["original_total_unique_UDP_missing"],
            new_jitter["original_alice_server_queue_overflow"])==(0,32)
    assert new_jitter["strict_zero_loss"]=="FAIL_SCOPED"
    rotating=get("generation/rotating12")
    assert (rotating["original_alice_DL_missing"],rotating["original_total_unique_UDP_missing"],
            rotating["all_five_server_lease_queue_overflow"])==(16,25,0)
    oldbad=get("newold/old")
    assert (oldbad["original_alice_DL_missing"],oldbad["original_alice_UL_missing"],
            oldbad["original_alice_server_queue_overflow"])==(57,16,78)
    for item in observed.values():
        assert item["original_six_owned_final_Stops"] and item["original_authenticated_five_clients"]
        assert item["original_application_seconds"]==180
    original_runs={name:dict(data) for name,data in ART.items()}
    result={"schema_version":1,"role_id":"M0","plan":"PLAN028",
            "original_product_source_new":NEW,"original_product_source_old":OLD,
            "offline_reviewer_source":reviewer,"real_original_action_artifacts":original_runs,
            "network_reruns":0,"new_product_compiles":0,
            "case_count":len(observed),"actual_results":observed,
            "paired_comparisons":{
             "same_vm_new_mixed_vs_large":{"mixed":get("capacity/capacity_mixed")["strict_zero_loss"],
                                           "large":get("capacity/capacity_large")["strict_zero_loss"],
                                           "at_least_one_packet_rate_effect_reproduced":False},
             "same_vm_12mbps_static_vs_rotation":{"static_missing":get("generation/static12")["original_total_unique_UDP_missing"],
                                                  "rotation_missing":rotating["original_total_unique_UDP_missing"],
                                                  "rotation_authentic":"PASS_SCOPED",
                                                  "server_queue_overflow":0},
             "same_vm_AB_OLD_THEN_NEW":{"old_missing":get("oldnew/old")["original_total_unique_UDP_missing"],
                                        "new_missing":get("oldnew/new")["original_total_unique_UDP_missing"]},
             "same_vm_BA_NEW_THEN_OLD":{"new_missing":get("newold/new")["original_total_unique_UDP_missing"],
                                        "old_missing":oldbad["original_total_unique_UDP_missing"],
                                        "old_queue_overflow":78,
                                        "new_queue_overflow":new_jitter["original_alice_server_queue_overflow"]}
            },
            "strict_assessment":{
             "high_capacity_75mbps":"FEASIBLE_BUT_BURST_OR_HOST_SCHEDULING_INTERMITTENT; historical600 FAIL preserved",
             "generation_low_rate":"FAIL_SCOPED_ROTATING_12MBPS_NOT_STATIC_ON_ONE_HOST; phase-correlation only not packet-level cause",
             "old_source_guaranteed_better":"NOT_PROVEN; old lost73 and overflow78 on reversed host, new had zero app missing but queue overflow32",
             "original_cross_os_Windows_Wintun_1800":"NOT_QUALIFIED",
             "PLAN028":"IN_PROGRESS"
            },
            "verified":"AUTHENTIC_ORIGINAL_ZIP_CRC_CHECKED_LOCALLY_AND_SOURCE_LOCKED_EIGHT_SCENE_OFFLINE_REPLAY"}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n")
    print("H1472_SOURCE_LOCKED_EIGHT_TRUE_NATIVE_180S_OFFLINE_REPLAY_PASS",
          json.dumps({k:{"missing":v["original_total_unique_UDP_missing"],
                         "alice_dl":v["original_alice_DL_missing"],
                         "queue":v["all_five_server_lease_queue_overflow"],
                         "verdict":v["strict_zero_loss"]}
                      for k,v in observed.items()},sort_keys=True),flush=True)
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    p.add_argument("--reviewer",required=True)
    a=p.parse_args()
    replay(a.root,a.out,a.reviewer)

if __name__=="__main__":
    main()
