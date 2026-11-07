#!/usr/bin/env python3
"""PLAN028 H1349 — one 0%-loss native x86 Game4 fixed6 capacity calibration.

Load the existing 180s ORIGINAL Go TLS/Rust 5-client network harness without
editing it. Change ONLY test-network loss/rates and disable timer turnovers by
arming well past the 180s sample. No product code/config/protocol change.
"""
import json
import os
import pathlib
import runpy
import sys

ORIGINAL="6c5fd909b9f42d1af89c698cdaabc79bbb72e589"
PHASES=(("first_wave",20,.15),("sustained",30,.25),
        ("climb_10",30,.5),("overload_20",30,1.0),("recovery",60,.5))
RATES=(2,2,2,20,2)
LOSSES=(0,0,0,0,0)
DELAYS=(0,0,0,0,0)
ROTATIONS=(600,600,600,600,600)

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: h1349.py --preflight | FROZEN_BINARY_DIR")
    assert os.environ.get("WBD_PLAN028_FAST_SCENE")=="pressure"
    assert os.environ.get("WBD_PLAN028_FAST_CAPACITY_STEPS")=="2"
    assert os.environ.get("WBD_PLAN028_QDISC_CLOCK_DIAG")=="1"
    assert not os.environ.get("WBD_PLAN028_STATIC_OWNED_NEIGH")
    assert not os.environ.get("WBD_PLAN028_APP_ONEWAY")
    assert not os.environ.get("WBD_PLAN028_ERIN_MAX_DELAY")
    assert not os.environ.get("WBD_PLAN028_30M_SCENE")
    script="tools/m0-plan028-h1259-five-client-recovery-netns.py"
    context=runpy.run_path(script,run_name="h1332_no_main")
    fn=context["main"]
    g=fn.__globals__
    assert g["FAST_SCENE"]=="pressure" and g["CAPACITY_STEPS"]=="2"
    assert len(g["NAMES"])==5 and g["MODES"]==(
        "normal","fec-auto","game2","game4","fec-fixed")
    assert g["LONG_SCENE"]=="" and g["FAST_MTU_SHRINK"]==""
    g.update(LOSS=LOSSES,DELAY=DELAYS,RATE=RATES,
             FAST_PHASES=PHASES,ROTATION_SECONDS=ROTATIONS)
    plan={
        "profile":"H1349_REAL_ZERO_LOSS_GAME4_FIXED6_STAGED",
        "original_product_source":ORIGINAL,
        "audit_workflow_source":os.environ.get("WBD_H1349_WRAPPER_SOURCE","PREFLIGHT_NOT_LOCKED"),
        "five_client_modes":g["MODES"],
        "rates_mbps_per_direction":dict(zip(g["NAMES"],RATES)),
        "both_direction_physical_loss_pct":list(LOSSES),
        "both_direction_oneway_delay_ms":list(DELAYS),
        "phases":[{"name":n,"seconds":d,"scale":s} for n,d,s in PHASES],
        "game4_logical_stages_mbps_per_direction":[3,5,10,20,10],
        "other_four_per_direction_at_peak_mbps":[2,2,2,2],
        "rotation_interval_seconds":600,
        "rotation_expected_during_180s":False,
        "max_offered_aggregate_one_direction_mbps":28,
        "traffic":"actual original TLS443+Rust TUN, five separately authenticated mixed-mode clients; Game4 fixed6 requested 3/5/10/20/10 Mbps logical each direction, business UDP/TCP counted separately",
        "scope":"L2 x86 guest-only 0%-loss Game4 fixed6 3/5/10/20/10 Mbps calibration; other four users remain active; not L1 rotations nor physical WiFi; VM per-core CPU measured, never extrapolate across hosts"
    }
    assert sum(d for _,d,_ in PHASES)==170 and 10+170==180
    # Regression against H1348 first-phase 2Mbps plan/report mismatch:
    # fail BEFORE any network if the exact desired logical Game4 rates
    # do not follow from the actual generator base rate and phase scales.
    assert [round(RATES[3]*scale,3) for _,_,scale in PHASES]==[3,5,10,20,10], "actual Game4 target did not match planned 5 tiers"
    if sys.argv[1]=="--preflight":
        print("M0_PLAN028_H1349_GAME4_PRECHECK",json.dumps(plan,sort_keys=True),flush=True)
        return
    assert os.environ.get("GITHUB_SHA")==ORIGINAL, "frozen executable source authority"
    assert len(os.environ.get("WBD_H1349_WRAPPER_SOURCE",""))==40, "actual fixture/action source must be recorded separately from frozen binary"
    fn()
    out=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"fixed-kernel-result"
    actual=json.loads((out/"h1250-matrix-plan.json").read_text())
    assert actual["source_sha"]==ORIGINAL
    assert [x["loss_pct"] for x in actual["clients"]]==[0]*5
    assert [x["oneway_delay_ms"] for x in actual["clients"]]==[0]*5
    assert [x["c2s_target_mbps"] for x in actual["clients"]]==list(RATES)
    assert [(x["name"],x["seconds"],x["rate_scale"]) for x in
            actual["capacity_phase_schedule"]]==list(PHASES)
    actual["h1349_specialization"]=plan
    actual["capacity_context"]="0% true netem, 5 real users; 3→5→10→5 Mbps Game4 fixed6 logical per direction, other four up to 2Mbps; no rotation. Actual host vCPU/CPU/softirq/core saturation measured, no fixed 4-core assumption."
    (out/"h1250-matrix-plan.json").write_text(json.dumps(actual,indent=2)+"\n")
    print("M0_PLAN028_H1349_GAME4_ONE_NATIVE_X86_ZERO_LOSS_SCENE_CAPTURED",flush=True)

if __name__=="__main__":
    main()
