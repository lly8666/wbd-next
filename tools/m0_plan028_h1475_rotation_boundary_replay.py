#!/usr/bin/env python3
"""Original H1473 10ms source-locked app loss vs M4 stage first-sample replay.

A 10ms bucket persistent deficit is NOT an exact packet-drop timestamp.
A 500ms M4 first sample is NOT an exact route promotion timestamp.
No product runs, no old artifact rewrite, and no mock receiver.
"""
import argparse
import json
import pathlib
import re

SOURCE="66fb6b4454b1ce4297ab04efa20c7f931ff12383"
ACTION=42595013191
ARTIFACT=13663646307
ROLES=("alice","bob","carol","dave","erin")
STOP="V4_PUBLIC_SHARED_TUN_STOP generation="

def read(path):
    return json.loads(path.read_text())

def records(path,needle):
    return [line for line in path.read_text(errors="replace").splitlines() if needle in line]

def fields(line):
    return dict(re.findall(r"([a-z_0-9]+)=([^ ]+)",line))

def persistent_deficits(sent,received):
    assert len(sent)==len(received)==19001,"10ms original application clock"
    cumulative=[]
    delta=0
    for a,b in zip(sent,received):
        delta+=int(a)-int(b)
        cumulative.append(delta)
    suffix=[0]*len(cumulative)
    future_min=10**30
    for i in range(len(cumulative)-1,-1,-1):
        future_min=min(future_min,cumulative[i])
        suffix[i]=future_min
    events=[]
    prev=0
    for i,n in enumerate(suffix):
        if n>prev:
            events.append({"app_10ms_bucket_s":round(i/100,2),
                           "new_permanent_deficit":n-prev,
                           "total_permanent_deficit":n})
            prev=n
    assert prev==delta,"suffix of cumulative unique TX/RX mismatch"
    return events,delta

def evaluate(root,reviewer):
    assert len(reviewer)==40 and reviewer!=SOURCE
    manifest=read(root/"fixed-build/manifest.json")
    assert manifest["source_sha"]==SOURCE
    assert manifest["native_fec_acceleration"] is True
    assert manifest["architecture"]=="native_x86_64"
    assert len(manifest["sha256"])==3
    observed={}
    for case in ("rotating12","static12"):
        art=root/"paired"/case
        plan=read(art/"h1250-matrix-plan.json")
        assert plan["source_sha"]==SOURCE
        assert plan["h1467_short_ab_case"]==case
        assert len(plan["clients"])==5
        assert plan["application_load_seconds"]==180
        assert all(x["loss_pct"]==0 for x in plan["clients"])
        out={}
        for who in ROLES:
            server=read(art/("h1250-s-"+who+".json"))
            client=read(art/("h1250-c-"+who+".json"))
            assert server["start_ns"]==client["start_ns"]
            assert server["end_ns"]-server["start_ns"]==180000000000
            sent=server["tx_bins_10ms"]["udp"]
            got=client["rx_bins_10ms"]["udp"]
            events,missing=persistent_deficits(sent,got)
            assert STOP in (art/("h1250-product-"+who+".log")).read_text(errors="replace")
            out[who]={"original_s2c_unique_app_missing":missing,
                      "permanent_app_10ms_loss_onsets":events}
        assert STOP in (art/"h1250-product-server.log").read_text(errors="replace")
        alice_client=art/"h1250-product-alice.log"
        logs=records(alice_client,"V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG role=client")
        first_by_gen={}
        for line in logs:
            d=fields(line);g=int(d["generation"]);ts=int(d["mono_ns"])
            first_by_gen[g]=min(first_by_gen.get(g,ts),ts)
        assert len(first_by_gen)==(3 if case=="rotating12" else 1)
        start=read(art/"h1250-c-alice.json")["start_ns"]
        m4=[{"generation":g,
             "first_500ms_M4_sample_from_app_start_s":round((ts-start)/1e9,3)}
            for g,ts in sorted(first_by_gen.items())]
        m2=records(alice_client,"V4_PUBLIC_M2_OUTER role=client")
        total_first_wire=sum(int(fields(line)["first_wire_bytes"]) for line in m2)
        total_repair=sum(int(fields(line)["repair_accepted_wire_bytes"]) for line in m2)
        total_original_retrans=sum(int(fields(line)["original_frozen_retransmitted"]) for line in m2)
        assert len(m2)==len(m4)
        rx=records(alice_client,"V4_PUBLIC_RX_CHAIN role=client")
        delivered=sum(int(fields(line)["tun_delivered"]) for line in rx)
        assert len(rx)==len(m4)
        all_server=records(art/"h1250-product-server.log","M0_SHARED_TUN_LEASE_QUEUE_DIAG")
        lease=next(item["lease"] for item in plan["clients"] if item["who"]=="alice")
        own=[fields(line) for line in all_server if "ip="+lease+" " in line]
        assert len(own)==1
        server_offered=int(own[0]["offered"])
        overflow=int(own[0]["pending_overflow"])
        assert overflow==0
        out["alice_original_M4_first_500ms_samples"]=m4
        out["alice_total_original_M2_first_wire_bytes"]=total_first_wire
        out["alice_M2_repair_accepted_bytes"]=total_repair
        out["alice_M2_original_frozen_retransmitted"]=total_original_retrans
        out["alice_Rust_M3_native_TUN_delivered_all_generations"]=delivered
        out["alice_original_server_TUN_offered"]=server_offered
        out["alice_server_offered_minus_client_M3_delivered"]=server_offered-delivered
        out["alice_server_queue_overflow"]=overflow
        observed[case]=out
    rotating=observed["rotating12"]
    static=observed["static12"]
    assert rotating["alice"]["original_s2c_unique_app_missing"]==13
    assert static["alice"]["original_s2c_unique_app_missing"]==0
    assert rotating["carol"]["original_s2c_unique_app_missing"]==3
    assert all(static[who]["original_s2c_unique_app_missing"]==0 for who in ROLES)
    events=rotating["alice"]["permanent_app_10ms_loss_onsets"]
    assert [(e["app_10ms_bucket_s"],e["new_permanent_deficit"]) for e in events]==[
        (39.39,5),(39.4,3),(132.85,4),(132.86,1)]
    first=rotating["alice_original_M4_first_500ms_samples"]
    assert [x["generation"] for x in first]==[1,2,3]
    comparison={
        "alice_loss_onsets_first_generation_before_M4_first_sample_s":round(
            first[1]["first_500ms_M4_sample_from_app_start_s"]-39.39,3),
        "alice_loss_onsets_second_generation_before_M4_first_sample_s":round(
            first[2]["first_500ms_M4_sample_from_app_start_s"]-132.85,3),
        "M2_first_wire_rotated_minus_static_bytes":
            rotating["alice_total_original_M2_first_wire_bytes"]-static["alice_total_original_M2_first_wire_bytes"],
        "M2_first_wire_rotated_vs_static_pct":round(100*(
            rotating["alice_total_original_M2_first_wire_bytes"]/
            static["alice_total_original_M2_first_wire_bytes"]-1),5),
        "different_fault_boundaries":"Original server queue0 in both, rotating gap between server offered and client M3; exact missing packet path unproven."
    }
    result={"schema_version":1,"role_id":"M0","plan":"PLAN028",
            "original_source_sha":SOURCE,"offline_reviewer_sha":reviewer,
            "original_action_id":ACTION,"original_artifact_id":ARTIFACT,
            "no_new_native_test":True,"same_runner_execution_order":["rotating12","static12"],
            "observations":observed,"comparison":comparison,
            "classification":"OFFLINE_PASS_REAL_ROTATION_10MS_BOUNDARY_CORRELATION_PRODUCT_ZEROLOSS_STILL_FAIL",
            "limits":["10ms app deficits not individual packet timestamps",
                      "first M4 stage sample occurs after promotion, not exact commit",
                      "180s accumulated M2 first copy bytes not peak 10ms bandwidth",
                      "M3 delivered counts include UDP and TCP; not equal UDP-only deficit",
                      "No Windows original L3 1800 qualification"]}
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    p.add_argument("--reviewer",required=True)
    a=p.parse_args()
    result=evaluate(a.root,a.reviewer)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("H1475_10MS_ORIGINAL_ROTATION_LOSS_ONSET_OFFLINE_PASS",
          json.dumps(result["comparison"],sort_keys=True),flush=True)

if __name__=="__main__":
    main()
