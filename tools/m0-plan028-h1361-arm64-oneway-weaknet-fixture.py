#!/usr/bin/env python3
"""PLAN028 H1361 — native ARM64 original TLS/Rust five-client heterogeneous loss/delay gradient.

Load the existing 180s ORIGINAL Go TLS/Rust 5-client network harness without
editing it. Change ONLY test-network loss/rates and disable timer turnovers by
arming well past the 180s sample. No product code/config/protocol change.
"""
import json
import os
import pathlib
import runpy
import sys

ORIGINAL="24e1fe6c4eab2a1abb7fb8a6d2093abaf57c0f73"
PHASES=(("first_wave",30,.2),("sustained",60,.35),
        ("overload",30,.45),("recovery",50,.35))
RATES=(5,5,4,4,4)
LOSSES=(0,1,5,15,30)
DELAYS=(0,15,50,100,125)
ROTATIONS=(600,600,600,600,600)

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: h1332.py --preflight | FROZEN_BINARY_DIR")
    assert os.environ.get("WBD_PLAN028_FAST_SCENE")=="pressure"
    assert os.environ.get("WBD_PLAN028_FAST_CAPACITY_STEPS")=="2"
    assert os.environ.get("WBD_PLAN028_QDISC_CLOCK_DIAG")=="1"
    assert os.environ.get("WBD_PLAN028_STATIC_OWNED_NEIGH")=="1", "test-only actual ARP control to deconfound netem dropping ARP"
    assert os.environ.get("WBD_PLAN028_APP_ONEWAY")=="1"
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
    assert g["ONEWAY_APP"]=="1" and g["ONEWAY_HEALTH_BLACKHOLE"]==""
    assert g["EXTRA"][3][:2]==("--game-fec","fixed6")
    g.update(LOSS=LOSSES,DELAY=DELAYS,RATE=RATES,
             FAST_PHASES=PHASES,ROTATION_SECONDS=ROTATIONS)
    plan={
        "profile":"H1361_NATIVE_ARM_ONEWAY_30PCT125MS_SOURCE24E1",
        "original_product_source":ORIGINAL,
        "wrapper_source":os.environ.get("WBD_H1361_WRAPPER_SOURCE","PREFLIGHT_ONLY"),
        "five_client_modes":g["MODES"],
        "rates_mbps_per_direction":dict(zip(g["NAMES"],RATES)),
        "both_direction_physical_loss_pct":list(LOSSES),
        "both_direction_oneway_delay_ms":list(DELAYS),
        "phases":[{"name":n,"seconds":d,"scale":s} for n,d,s in PHASES],
        "game4_true_active_downlink_stages_mbps":[.8,1.4,1.8,1.4],
        "true_user_application_directions":["uplink","downlink","uplink","downlink","uplink"],
        "rotation_interval_seconds":600,
        "rotation_expected_during_180s":False,
        "max_true_active_uplink_inner_mbps":5.85,
        "max_true_active_downlink_inner_mbps":4.05,
        "traffic":"native ARM64 original Go TLS443 + Rust M4 five authenticated strict one-way UDP app only, no reverse user UDP/TCP or probe; original encrypted Health remains",
        "scope":"L1/L2 real native ARM64 original true one-way loss0/1/5/15/30pct 0/15/50/100/125ms, test-only real veth ARP 10/10; NOT H1318 10s reverse Health blackout repeat, no physical WAN"
    }
    assert sum(d for _,d,_ in PHASES)==170 and 10+170==180
    assert abs((RATES[0]+RATES[2]+RATES[4])*.45-5.85)<1e-9
    assert abs((RATES[1]+RATES[3])*.45-4.05)<1e-9
    if sys.argv[1]=="--preflight":
        print("M0_PLAN028_H1361_HETEROGENEOUS_PRECHECK",json.dumps(plan,sort_keys=True),flush=True)
        return
    assert os.environ.get("GITHUB_SHA")==ORIGINAL, "frozen executable source authority"
    assert len(os.environ.get("WBD_H1361_WRAPPER_SOURCE",""))==40, "source-locked fixture/action SHA independent of binary SOURCE"
    fn()
    out=pathlib.Path(os.environ["GITHUB_WORKSPACE"])/"fixed-kernel-result"
    actual=json.loads((out/"h1250-matrix-plan.json").read_text())
    assert actual["source_sha"]==ORIGINAL
    assert [x["loss_pct"] for x in actual["clients"]]==list(LOSSES)
    assert [x["oneway_delay_ms"] for x in actual["clients"]]==list(DELAYS)
    assert actual["application_scene"]=="strict_oneway"
    assert actual["application_directionality"]==dict(zip(g["NAMES"],("uplink","downlink","uplink","downlink","uplink")))
    assert [x["c2s_target_mbps"] for x in actual["clients"]]==[5,0,4,0,4]
    assert [x["s2c_target_mbps"] for x in actual["clients"]]==[0,5,0,4,0]
    assert [(x["name"],x["seconds"],x["rate_scale"]) for x in
            actual["capacity_phase_schedule"]]==list(PHASES)
    actual["h1361_specialization"]=plan
    actual["capacity_context"]="native ARM64 original SOURCE24e 0/1/5/15/30pct physical loss 0/15/50/100/125ms delay strict one-way app: peak active UL5.85 DL4.05Mbps, no rotations, guest CPU and real qdisc measured"
    (out/"h1250-matrix-plan.json").write_text(json.dumps(actual,indent=2)+"\n")
    print("M0_PLAN028_H1361_NATIVE_ARM_TRUE_ONEWAY_APP_CAPTURED",flush=True)

if __name__=="__main__":
    main()
