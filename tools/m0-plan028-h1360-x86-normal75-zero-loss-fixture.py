#!/usr/bin/env python3
"""PLAN028 H1360 — one 0%-loss native x86 Normal 75Mbps next bounded L2 tier.

Load the existing 180s ORIGINAL Go TLS/Rust 5-client network harness without
editing it. Change ONLY test-network loss/rates and disable timer turnovers by
arming well past the 180s sample. No product code/config/protocol change.
"""
import json
import os
import pathlib
import runpy
import sys

ORIGINAL=os.environ.get("WBD_PLAN028_H1458_PRODUCT_SOURCE","6c5fd909b9f42d1af89c698cdaabc79bbb72e589")
assert ORIGINAL in ("6c5fd909b9f42d1af89c698cdaabc79bbb72e589","548a47cc708d82d45e1722540b6677342f3c8c5b"), "unsupported source pin for H1458 opt-in"
PHASES=(("first_wave",30,1/3),("sustained",60,2/3),
        ("overload",30,1.0),("recovery",50,2/3))
RATES=(75,2,2,2,2)
LOSSES=(0,0,0,0,0)
DELAYS=(0,0,0,0,0)
ROTATIONS=(600,600,600,600,600)

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: h1360.py --preflight | FROZEN_BINARY_DIR")
    assert os.environ.get("WBD_PLAN028_FAST_SCENE")=="pressure"
    assert os.environ.get("WBD_PLAN028_FAST_CAPACITY_STEPS")=="2"
    assert os.environ.get("WBD_PLAN028_QDISC_CLOCK_DIAG")=="1"
    assert not os.environ.get("WBD_PLAN028_STATIC_OWNED_NEIGH")
    assert not os.environ.get("WBD_PLAN028_APP_ONEWAY")
    assert not os.environ.get("WBD_PLAN028_ERIN_MAX_DELAY")
    assert not os.environ.get("WBD_PLAN028_30M_SCENE")
    script="tools/m0-plan028-h1259-five-client-recovery-netns.py"
    context=runpy.run_path(script,run_name="h1360_no_main")
    fn=context["main"]
    g=fn.__globals__
    assert g["FAST_SCENE"]=="pressure" and g["CAPACITY_STEPS"]=="2"
    assert len(g["NAMES"])==5 and g["MODES"]==(
        "normal","fec-auto","game2","game4","fec-fixed")
    assert g["LONG_SCENE"]=="" and g["FAST_MTU_SHRINK"]==""
    g.update(LOSS=LOSSES,DELAY=DELAYS,RATE=RATES,
             FAST_PHASES=PHASES,ROTATION_SECONDS=ROTATIONS)
    plan={
        "profile":"H1360_REAL_ZERO_LOSS_NORMAL_STAGED",
        "original_product_source":ORIGINAL,
        "five_client_modes":g["MODES"],
        "rates_mbps_per_direction":dict(zip(g["NAMES"],RATES)),
        "wrapper_source":os.environ.get("WBD_H1360_WRAPPER_SOURCE","PREFLIGHT"),
        "both_direction_physical_loss_pct":list(LOSSES),
        "both_direction_oneway_delay_ms":list(DELAYS),
        "phases":[{"name":n,"seconds":d,"scale":s} for n,d,s in PHASES],
        "normal_stages_mbps_per_direction":[25,50,75,50],
        "other_four_per_direction_at_peak_mbps":[2,2,2,2],
        "rotation_interval_seconds":600,
        "rotation_expected_during_180s":False,
        "max_offered_aggregate_one_direction_mbps":83,
        "traffic":"actual original TLS443+Rust TUN, 5 separately authenticated mixed modes; Normal has 80% UDP/20% TCP",
        "scope":"L2 0%-loss capacity and recovery only, not L1 rotation or physical hardware, no static-ARP control"
    }
    assert sum(d for _,d,_ in PHASES)==170 and 10+170==180
    assert [round(RATES[0]*rate,3) for _,_,rate in PHASES]==[25,50,75,50]
    assert sum(RATES)==83
    if sys.argv[1]=="--preflight":
        print("M0_PLAN028_H1360_PRECHECK",json.dumps(plan,sort_keys=True),flush=True)
        return
    assert os.environ.get("GITHUB_SHA")==ORIGINAL, "frozen executable source authority"
    assert len(os.environ.get("WBD_H1360_WRAPPER_SOURCE",""))==40
    fn()
    out=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"fixed-kernel-result"
    actual=json.loads((out/"h1250-matrix-plan.json").read_text())
    assert actual["source_sha"]==ORIGINAL
    assert [x["loss_pct"] for x in actual["clients"]]==[0]*5
    assert [x["oneway_delay_ms"] for x in actual["clients"]]==[0]*5
    assert [x["c2s_target_mbps"] for x in actual["clients"]]==list(RATES)
    assert [(x["name"],x["seconds"],x["rate_scale"]) for x in
            actual["capacity_phase_schedule"]]==list(PHASES)
    actual["h1360_specialization"]=plan
    actual["capacity_context"]="0% true netem, 5 real users; 25→50→75→50 Mbps Normal, other modes max 2 Mbps; no timer rotation during test; actual runner vCPUs measured, H1332 previous 50Mbps source6c5 59.63% host peak; projected 75 near85% and stop if measured capacity exhausted"
    (out/"h1250-matrix-plan.json").write_text(json.dumps(actual,indent=2)+"\n")
    print("M0_PLAN028_H1360_ONE_NATIVE_X86_ZERO_LOSS_SCENE_CAPTURED",flush=True)

if __name__=="__main__":
    main()
