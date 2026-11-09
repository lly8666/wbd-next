#!/usr/bin/env python3
"""PLAN028: only a genuine native ARM64/x86 original Go TLS/Rust M4
five-client rotating12 test can qualify the new server B cold RX gate.
Never convert a no-trigger clean run into readiness PASS.
"""
import argparse,json,pathlib,re

NAMES=("alice","bob","carol","dave","erin")
SOURCE_GO="a7a82db31fe736ffedee330795a3234d358f1984"
STOP="V4_PUBLIC_SHARED_TUN_STOP generation="

def get(root,name):
    return json.loads((root/name).read_text())

def classify(root,source):
    manifest=get(root.parent/"fixed-build","manifest.json")
    plan=get(root,"h1250-matrix-plan.json")
    assert manifest["source_sha"]==source==plan["source_sha"]
    assert manifest["original_go_sha"]==SOURCE_GO
    assert manifest["native_fec_acceleration"] is True
    assert manifest["architecture"] in ("native_aarch64","native_x86_64")
    assert plan["h1467_short_ab_case"]=="rotating12"
    assert plan["application_load_seconds"]==180
    assert len(plan["clients"])==5
    assert all(c["loss_pct"]==c["oneway_delay_ms"]==0 for c in plan["clients"])
    assert [c["s2c_target_mbps"] for c in plan["clients"]]==[12,2,2,2,2]
    text={role:(root/f"h1250-product-{role}.log").read_text(errors="replace")
          for role in ("server",)+NAMES}
    assert all(STOP in content for content in text.values())
    server=text["server"]
    client=text["alice"]
    server_deferred=server.count("V4_PUBLIC_NORMAL_TUN_CANDIDATE_DEFERRED role=server")
    server_proven=server.count("V4_PUBLIC_NORMAL_SERVER_TUN_PROMOTED_AFTER_CLIENT_AUTH_RX")
    # The actual five-client fixture uses the mixed Normal/Game 443
    # listener. Count the real mixed-server proof event, and retain
    # compatibility with the standalone multi-Normal admission path.
    mixed_go_ready=server.count("V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY")
    standalone_go_ready=server.count("V4_PUBLIC_MULTI_SERVER_B_CLIENT_READY")
    server_go_ready=mixed_go_ready+standalone_go_ready
    alice_proven=client.count("V4_PUBLIC_NORMAL_TUN_PROMOTED_AFTER_AUTH_RX")
    assert "V4_PUBLIC_MULTI_SERVER_B_CLIENT_UNPROVEN" not in server
    total={}
    for who in NAMES:
        s=get(root,f"h1250-s-{who}.json")
        c=get(root,f"h1250-c-{who}.json")
        assert s["start_ns"]==c["start_ns"]
        assert s["end_ns"]-s["start_ns"]==180_000_000_000
        assert c["end_ns"]-c["start_ns"]==180_000_000_000
        users={}
        for direction,tx,rx in (("downlink",s,c),("uplink",c,s)):
            left=tx["tx_bins_10ms"]["udp"]
            right=rx["rx_bins_10ms"]["udp"]
            assert len(left)==len(right)==19001
            missing=sum(left)-sum(right)
            users[direction]={"sent":sum(left),"received":sum(right),
                              "unique_missing":missing}
        total[who]=users
    alice_gen=len(re.findall(r"V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=\d+",client))
    # Both B admissions must be actually protected and promoted on each
    # side. Local TLS READY, first startup and absence of physical loss
    # never suffice for the conditional-fix gate.
    triggered=(server_deferred>=2 and server_proven>=2 and
               server_go_ready>=2 and alice_proven>=2 and alice_gen>=3)
    misses=[row[direction]["unique_missing"] for row in total.values()
            for direction in ("downlink","uplink")]
    missing=sum(misses)
    unique_zero_loss=all(n==0 for n in misses)
    result={
        "plan":"PLAN028","role_id":"M0","product_source_sha":source,
        "architecture":manifest["architecture"],
        "native_app_seconds":180,"true_client_count":5,
        "owned_all_six_stop":True,
        "server_replacement_deferred_count":server_deferred,
        "server_auth_client_cold_proven_count":server_proven,
        "server_go_proof_barrier_count":server_go_ready,
        "mixed_server_go_proof_barrier_count":mixed_go_ready,
        "standalone_go_proof_barrier_count":standalone_go_ready,
        "alice_client_authenticated_generation_promotions":alice_proven,
        "alice_client_generation_starts":alice_gen,
        "two_actual_server_B_gates_triggered":triggered,
        "per_user_original_udp":total,"original_unique_missing_all_directions":missing,
        "all_directions_unique_udp_zero":unique_zero_loss,
        "verdict":("PASS_SCOPED_TRIGGERED_SERVER_B_READY_AND_ZERO_UNIQUE_UDP_LOSS"
                   if triggered and unique_zero_loss else
                   "FAIL_OR_NOT_TRIGGERED_KEEP_OPEN"),
    }
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--art",type=pathlib.Path,required=True)
    ap.add_argument("--source",required=True)
    ap.add_argument("--out",type=pathlib.Path,required=True)
    args=ap.parse_args()
    result=classify(args.art,args.source)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print("PLAN028_H1480_REAL_NATIVE_READY_GATE",json.dumps(result,sort_keys=True),flush=True)
    if result["verdict"]!="PASS_SCOPED_TRIGGERED_SERVER_B_READY_AND_ZERO_UNIQUE_UDP_LOSS":
        raise SystemExit("native original B client receiver readiness not proven or genuine loss remains")
if __name__=="__main__":
    main()
