#!/usr/bin/env python3
"""H1356 OFFLINE ONLY: source-locked H1355 Game2 Fixed6 outer-counter replay.

Original H1286 rapid report uses Game2 Off marker for ALL game2, so it
incorrectly emits NO_REAL_OUTER_COUNTER on Carol's actual Game2 Fixed6.
Read authenticated mode+actual per-client FEC policy from original product
log; parse the original Game2 FEC STOP records without changing product,
networking, FEC, seed, counters, samples, or original warning.
"""
import argparse,json,pathlib,runpy,re
SOURCE="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
H1355_WRAPPER="0f1aea9ca1dbf868860d9daf01aa480f75c82d17"
H1355_ORIGINAL_ACTION=42436151532
H1355_RAW_ARTIFACT=13599652010
def load(p):return json.loads(p.read_text())
def parse_counters(lines,kind):
    rows=[line for line in lines.splitlines()
          if kind in line]
    def value(s,k):
        m=re.search(r"\b"+re.escape(k)+r"=(\d+)",s)
        assert m is not None,(kind,k,s)
        return int(m.group(1))
    return {"generation_stop_samples":len(rows),
      **{k:sum(value(s,k) for s in rows)
          for k in ("copied_appearance","first_record_wire_bytes","copy_record_wire_bytes")}}
def replay(root):
    prior=load(root/"h1286-rapid-report.json")
    plan=load(root/"h1250-matrix-plan.json")
    specialized=load(root/"h1355-native-l1-owner-rotation.json")
    assert plan["source_sha"]==prior["source_sha"]==specialized["source_sha"]==SOURCE
    assert plan["h1355_specialization"]["wrapper_source"]==specialized["wrapper_source"]==H1355_WRAPPER
    assert specialized["classification"]=="PASS_SCOPED_NATIVE_X86_GAME2_FIXED6_TWO_REAL_ROTATIONS_FIVE_CLIENT"
    assert not specialized["native_app_or_owner_errors"] and not specialized["capacity_limit_clients"]
    assert prior["rotation_verdict"]=="PASS_ALL_FIVE_SCOPED"
    assert prior["alerts"]==[{"who":"carol","kind":"NO_REAL_OUTER_COUNTER"}],prior["alerts"]
    carol_log=(root/"h1250-product-carol.log").read_text(errors="replace")
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=2 mode=fixed profile=6" in carol_log
    assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=2 mode=off" not in carol_log
    assert "WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP" not in carol_log
    true_counts=parse_counters(carol_log,"WBD_GAME_FEC_LINUX_NORMAL_OUTER_STOP")
    assert true_counts["generation_stop_samples"]==3
    assert true_counts["first_record_wire_bytes"]>0
    assert true_counts["copy_record_wire_bytes"]>0
    assert true_counts["copied_appearance"]>0
    src=runpy.run_path("tools/m0-plan028-h1286-rapid-report.py",run_name="h1356_original_report_no_main")
    raw_outer=src["outer_counts"]
    fn=src["analyze"]
    globals_=fn.__globals__
    assert globals_["outer_counts"] is raw_outer
    def correct_game2_policy_outer(log,mode):
        if mode=="game2" and ("V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=2 mode=fixed profile=6" in log):
            assert "WBD_GAME_FEC_LINUX_NORMAL_OUTER_STOP" in log
            assert "WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP" not in log
            # Only the outer-STOP marker differs. Both Game2 and Game4 FEC
            # counters share the original three exact field names and units.
            return raw_outer(log,"game4")
        return raw_outer(log,mode)
    globals_["outer_counts"]=correct_game2_policy_outer
    after=fn(root,str(root/"h1250-product-server.log"))
    assert not after["alerts"],after["alerts"]
    assert after["performance_verdict"]=="NO_CONFIGURED_ALERTS"
    assert after["rotation_verdict"]==prior["rotation_verdict"]
    for who in ("alice","bob","dave","erin"):
        assert after["clients"][who]==prior["clients"][who],who
    for key in ("rotation","directions","server_per_lease_queue"):
        assert after["clients"]["carol"][key]==prior["clients"]["carol"][key],key
    revised=after["clients"]["carol"]["outer_cosmetic"]
    assert revised["observed_retired_generations"]==3
    for label,source_label in (
      ("copied_original_record_count","copied_appearance"),
      ("first_record_wire_bytes","first_record_wire_bytes"),
      ("cosmetic_accepted_repeat_record_wire_bytes","copy_record_wire_bytes")):
        assert revised[label]==true_counts[source_label],(label,revised,true_counts)
    assert after["total_client_outer_record"]["first_record_wire_bytes"]==(
        prior["total_client_outer_record"]["first_record_wire_bytes"]+
        true_counts["first_record_wire_bytes"])
    assert after["total_client_outer_record"]["cosmetic_accepted_repeat_record_wire_bytes"]==(
        prior["total_client_outer_record"]["cosmetic_accepted_repeat_record_wire_bytes"]+
        true_counts["copy_record_wire_bytes"])
    # Refuse to imply every native quanta and FEC block was the nominal fixed
    # grade, or credit external cosmetic repeats as FEC app recovery.
    fec=[line for line in carol_log.splitlines() if "V4_PUBLIC_GAME_FEC_COUNTERS role=client lanes=2" in line]
    native=[line for line in carol_log.splitlines() if "M0_GAME_M4_FEC_BACKEND_READBACK" in line]
    assert len(fec)==len(native)==3
    def total(lines,k):
        return sum(int(re.search(r"\b"+re.escape(k)+r"=(\d+)",line).group(1)) for line in lines)
    real_fec={"source_offered":total(fec,"source_offered"),
              "parity_offered":total(fec,"parity_offered"),
              "parity_copied":total(fec,"parity_copied"),
              "recovered_candidate":total(fec,"recovered_candidate"),
              "native_tx_quanta":total(native,"tx_native_quanta"),
              "scalar_tx_quanta":total(native,"tx_scalar_quanta")}
    assert real_fec["source_offered"]>0 and real_fec["parity_copied"]>0
    assert real_fec["native_tx_quanta"]>0 and real_fec["scalar_tx_quanta"]>0
    return {"schema_version":1,
      "classification":"PASS_SCOPED_OFFLINE_H1355_GAME2_FIXED6_ACTUAL_OUTER_COUNTS",
      "original_product_source":SOURCE,"original_h1355_wrapper":H1355_WRAPPER,
      "original_action":H1355_ORIGINAL_ACTION,"original_action_conclusion":"success",
      "original_raw_artifact_id":H1355_RAW_ARTIFACT,"network_rerun":False,
      "original_general_report_alerts_preserved":prior["alerts"],
      "original_general_report_performance_verdict":prior["performance_verdict"],
      "original_specialized_network_audit":specialized["classification"],
      "corrected_general_report_alerts":after["alerts"],
      "corrected_general_report_performance_verdict":after["performance_verdict"],
      "actual_fixed6_authenticated_client_evidence":"Carol original Go TLS443 + Rust M4 FEC mode=fixed profile=6 applied 3 times; old generation Stop 1,2",
      "original_carol_fec_stop_counter_samples":true_counts,
      "true_fec2_per_generation_actual_counters":real_fec,
      "corrected_carol_outer_record":revised,
      "corrected_five_client_outer_record":after["total_client_outer_record"],
      "rotations_and_app_original_unchanged":True,
      "limits":["Original H1355 general report warning remains stored and reproducible",
                "No product change, no network rerun; corrected report-only marker for Game2 FEC6",
                "R/(F+R) counts cosmetic record repeats and excludes control C and FEC symbols, NOT business recoveries",
                "Real FEC blocks may be short with scalar and native quanta mixed; zero physical loss does not trigger FEC recovery",
                "Only native x86 180s and Game2 Fixed6; no L3/Windows/physical WAN qualification"]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--art",required=True);p.add_argument("--out",required=True)
    args=p.parse_args();r=replay(pathlib.Path(args.art))
    pathlib.Path(args.out).write_text(json.dumps(r,indent=2)+"\n")
    print("M0_PLAN028_H1356_OFFLINE_GAME2_FIXED6_REAL_ORIGINAL_OUTER_COUNTS",r["classification"],flush=True)
if __name__=="__main__":
    main()
