#!/usr/bin/env python3
"""PLAN028 H1351 — native x86 original TLS/Rust five-client heterogeneous loss/delay gradient.

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
PHASES=(("first_wave",30,.2),("sustained",60,.35),
        ("overload",30,.5),("recovery",50,.35))
RATES=(9,9,7,7,6)
LOSSES=(0,1,5,15,30)
DELAYS=(0,50,150,250,250)
ROTATIONS=(600,600,600,600,600)

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: h1332.py --preflight | FROZEN_BINARY_DIR")
    assert os.environ.get("WBD_PLAN028_FAST_SCENE")=="pressure"
    assert os.environ.get("WBD_PLAN028_FAST_CAPACITY_STEPS")=="2"
    assert os.environ.get("WBD_PLAN028_QDISC_CLOCK_DIAG")=="1"
    assert os.environ.get("WBD_PLAN028_STATIC_OWNED_NEIGH")=="1", "test-only actual ARP control to deconfound netem dropping ARP"
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
    assert g["LONG_SCENE"]=="" and g["FAST_MTU_SHRINK"]=="" and g["STATIC_NEIGH"]=="1"
    g.update(LOSS=LOSSES,DELAY=DELAYS,RATE=RATES,
             FAST_PHASES=PHASES,ROTATION_SECONDS=ROTATIONS)
    plan={
        "profile":"H1351_REAL_HETEROGENEOUS_0_1_5_15_30PCT_AND_0_50_150_250MS",
        "original_product_source":ORIGINAL,
        "wrapper_source":os.environ.get("WBD_H1351_WRAPPER_SOURCE","PREFLIGHT_ONLY"),
        "five_client_modes":g["MODES"],
        "rates_mbps_per_direction":dict(zip(g["NAMES"],RATES)),
        "both_direction_physical_loss_pct":list(LOSSES),
        "both_direction_oneway_delay_ms":list(DELAYS),
        "phases":[{"name":n,"seconds":d,"scale":s} for n,d,s in PHASES],
        "game4_stages_mbps_per_direction":[1.4,2.45,3.5,2.45],
        "other_four_per_direction_at_peak_mbps":[4.5,4.5,3.5,3.0],
        "rotation_interval_seconds":600,
        "rotation_expected_during_180s":False,
        "max_offered_aggregate_one_direction_mbps":19,
        "traffic":"actual original TLS443 + Rust native ISA-L TUN, five authenticated mixed modes, real UDP plus Alice/Bob framed TCP",
        "scope":"L2 native Linux x86 five-client independent configured physical veth netem loss0/1/5/15/30% and one-way delay0/50/150/250/250ms; controlled real veth permanent ARP 10/10, not physical WAN, not L1 rotations"
    }
    assert sum(d for _,d,_ in PHASES)==170 and 10+170==180
    if sys.argv[1]=="--preflight":
        print("M0_PLAN028_H1351_HETEROGENEOUS_PRECHECK",json.dumps(plan,sort_keys=True),flush=True)
        return
    assert os.environ.get("GITHUB_SHA")==ORIGINAL, "frozen executable source authority"
    assert len(os.environ.get("WBD_H1351_WRAPPER_SOURCE",""))==40, "source-locked fixture/action SHA independent of binary SOURCE"
    fn()
    out=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"fixed-kernel-result"
    actual=json.loads((out/"h1250-matrix-plan.json").read_text())
    assert actual["source_sha"]==ORIGINAL
    assert [x["loss_pct"] for x in actual["clients"]]==list(LOSSES)
    assert [x["oneway_delay_ms"] for x in actual["clients"]]==list(DELAYS)
    assert [x["c2s_target_mbps"] for x in actual["clients"]]==list(RATES)
    assert [(x["name"],x["seconds"],x["rate_scale"]) for x in
            actual["capacity_phase_schedule"]]==list(PHASES)
    actual["h1351_specialization"]=plan
    actual["capacity_context"]="0/1/5/15/30% true physical netem and 0/50/150/250/250ms OS one-way delay, five real users lower load ~19Mbps one direction at peak, no rotation; per-VM logical cores/softirq measured not assumed; test-only native ARP static from real veth MAC prevents ARP packet loss confound"
    (out/"h1250-matrix-plan.json").write_text(json.dumps(actual,indent=2)+"\n")
    print("M0_PLAN028_H1351_ONE_NATIVE_X86_TRUE_HETEROGENEOUS_SCENE_CAPTURED",flush=True)

if __name__=="__main__":
    main()
