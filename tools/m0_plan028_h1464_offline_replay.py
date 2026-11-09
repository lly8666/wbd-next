#!/usr/bin/env python3
"""Rejudge H1461's two immutable original artifacts, never launch a native test.

This parser has a separate source SHA; original source and all six original
Stop/UDP/TCP evidence remain frozen at Action42578056120 SOURCE66fb.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shutil

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE="66fb6b4454b1ce4297ab04efa20c7f931ff12383"
ACTION=42578056120
ARCHIVES={
    600:{"artifact_id":13656024788,
         "artifact_name":"plan028-h1461-real-fiveclient-600s-capacity75-42578056120"},
    1800:{"artifact_id":13657785615,
          "artifact_name":"plan028-h1461-real-fiveclient-1800s-heterogeneous-42578056120"}
}
NAMES=("alice","bob","carol","dave","erin")
STOP="V4_PUBLIC_SHARED_TUN_STOP generation="

def module(file, name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"tools"/file)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def phase_totals(art,who,direction):
    src=load(art/("h1250-c-"+who+".json"))
    srv=load(art/("h1250-s-"+who+".json"))
    tx,rx=(src,srv) if direction=="uplink" else (srv,src)
    return [
        {"stage_index":i,"sent":t["tx_packets"],"received":r["rx_packets"],
         "missing":t["tx_packets"]-r["rx_packets"]}
        for i,(t,r) in enumerate(zip(tx["stats"]["udp"],rx["stats"]["udp"]))
    ]

def replay(input_root, output, reviewer_sha):
    assert len(reviewer_sha)==40
    assert reviewer_sha!=SOURCE, "replay wrapper must be a separate new source"
    analyzer=module("m0-plan028-h1274-30min-report.py","h1464_phase_report")
    verifier=module("m0_plan028_h1461_five_client_soak_verdict.py","h1464_verdict")
    output.mkdir(parents=True,exist_ok=True)
    outcomes={}
    one_build_manifest=None
    for duration in (600,1800):
        origin=input_root/str(duration)
        assert origin.is_dir(), origin
        manifest=load(origin/"fixed-build/manifest.json")
        assert manifest["source_sha"]==SOURCE and manifest["architecture"]=="native_x86_64"
        assert manifest["native_fec_acceleration"] is True
        if one_build_manifest is None:one_build_manifest=manifest
        else:assert one_build_manifest==manifest, "both old runners must share one exact compiled product"
        work=output/("reparsed-"+str(duration))
        work.mkdir(exist_ok=True)
        art=work/"fixed-kernel-result"
        shutil.copytree(origin/"fixed-kernel-result",art,dirs_exist_ok=True)
        plan=load(art/"h1250-matrix-plan.json")
        assert plan["source_sha"]==SOURCE and plan["application_load_seconds"]==duration
        assert len(plan["clients"])==5 and {p["who"] for p in plan["clients"]}==set(NAMES)
        for who in NAMES:
            for role in ("c","s"):
                raw=load(art/("h1250-"+role+"-"+who+".json"))
                assert raw["end_ns"]-raw["start_ns"]==duration*1_000_000_000
        original_report_name=("h1461-six-hundred-report.json" if duration==600
                              else "h1274-thirty-minute-report.json")
        old_report=load(art/original_report_name)
        assert len(old_report["clients"])==5
        assert all(not old_report["clients"][who]["directions"][direction]["phases"]
                   for who in NAMES for direction in ("uplink","downlink")), (
                       "unexpected old report: this replay is only for exact broken H1461 reporter")
        full=analyzer.analyze(art,art/"h1250-product-server.log")
        (art/original_report_name).write_text(json.dumps(full,indent=2)+"\n")
        assert full["source_sha"]==SOURCE and full["duration_seconds"]==duration
        assert full["rotation_verdict"]=="PASS_ALL_FIVE_SCOPED"
        assert len(full["clients"])==5
        assert all(len(full["clients"][who]["directions"][direction]["phases"])==5
                   for who in NAMES for direction in ("uplink","downlink"))
        assert all(sum(x["seconds"] for x in full["clients"][who]["directions"][direction]["phases"])==duration
                   for who in NAMES for direction in ("uplink","downlink"))
        stop={who:STOP in (art/("h1250-product-"+who+".log")).read_text(errors="replace")
              for who in ("server",)+NAMES}
        assert all(stop.values()), "original six Stop receipts missing"
        failure=None
        try:
            verifier.report(art,duration,SOURCE,reviewer_sha)
        except RuntimeError as exc:
            failure=str(exc)
        verdict=load(art/"h1461-native-verdict.json")
        assert verdict["source_sha"]==SOURCE and verdict["wrapper_sha"]==reviewer_sha
        assert verdict["status"].startswith("FAIL_SCOPED")
        assert failure is not None, "a real zero-loss failure must not become green"
        assert all(verdict["original_six_owned_final_stop"].values())
        missing={who:{direction:phase_totals(art,who,direction)
                     for direction in ("uplink","downlink")} for who in NAMES}
        alice_down=sum(p["missing"] for p in missing["alice"]["downlink"])
        if duration==600:
            assert verdict["total_true_queue_overflow"]==45
            assert alice_down==32
            assert [p["missing"] for p in missing["alice"]["downlink"]]==[0,0,0,32,0]
            assert full["alert_count"]==1
            assert any("ORIGINAL_SERVER_8_SLOT_QUEUE_OVERFLOW_45" in x for x in verdict["hard_faults"])
        else:
            assert verdict["total_true_queue_overflow"]==0
            assert alice_down==351
            assert full["alert_count"]==0
            assert any("alice_downlink_NO_CONFIGURED_LOSS_UDP_MISSING_351" in x
                       for x in verdict["hard_faults"])
        outcomes[str(duration)]={
            "duration_seconds":duration,
            "original_action":ACTION,
            "original_artifact_id":ARCHIVES[duration]["artifact_id"],
            "original_artifact_name":ARCHIVES[duration]["artifact_name"],
            "original_product_source":SOURCE,
            "offline_reviewer_source":reviewer_sha,
            "original_manifest_sha256":sha(origin/"fixed-build/manifest.json"),
            "original_product_sha256":manifest["sha256"],
            "all_original_5_authentic_clients_and_6_Stop":True,
            "original_1800_authentic_rotation_verdict":full["rotation_verdict"],
            "true_per_lease_queue_overflow":verdict["total_true_queue_overflow"],
            "original_report_alert_count":full["alert_count"],
            "offline_strict_verdict":verdict["status"],
            "strict_negative_reason":verdict["hard_faults"],
            "alice_downlink_unique_udp_missing":alice_down,
            "five_client_per_direction_per_phase_unique_packets":missing,
            "uncorrected_h1461_phase_report":"INVALID_EMPTY_PHASES",
            "corrected_original_report":str(art/original_report_name),
            "corrected_strict_verdict":str(art/"h1461-native-verdict.json")
        }
    summary={
        "schema_version":1,"role_id":"M0","plan":"PLAN028","check":"H1464_ORIGINAL_TWO_SOAK_OFFLINE_REPLAY",
        "source_sha":SOURCE,"reviewer_source_sha":reviewer_sha,
        "network_rerun":"NONE","native_product_binary_rebuild":"NONE",
        "original_run":ACTION,"scopes":outcomes,
        "final":"PASS_OFFLINE_FORENSIC_REPRODUCED_TWO_REAL_NEGATIVE_AND_1800_CONTINUITY",
        "official_Windows_1800":"NOT_QUALIFIED",
        "old_SOURCE548_75mbps":"HISTORICAL_FAIL_RETAINED"
    }
    path=output/"h1464-original-two-soak-replay.json"
    path.write_text(json.dumps(summary,indent=2)+"\n")
    print("H1464_IMMUTABLE_ORIGINAL_NATIVE_600_AND_1800_NEGATIVE_REPLAY_PASS",
          json.dumps({dur:{"lost_alice_downlink":row["alice_downlink_unique_udp_missing"],
                           "queue_overflow":row["true_per_lease_queue_overflow"],
                           "stop":row["all_original_5_authentic_clients_and_6_Stop"],
                           "native_rotation":row["original_1800_authentic_rotation_verdict"]}
                      for dur,row in outcomes.items()},sort_keys=True),flush=True)
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=pathlib.Path,required=True)
    p.add_argument("--out",type=pathlib.Path,required=True)
    p.add_argument("--reviewer",required=True)
    a=p.parse_args()
    replay(a.input,a.out,a.reviewer)

if __name__=="__main__":
    main()
