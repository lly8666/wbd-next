"""PLAN027: native Auto 1->15->30->1 uplink, 5->0 downlink, 150s low-loss.
One SOURCE-frozen original Linux Go TLS+Rust M4 experiment, outer repair OFF.
Captures native Auto-quality/stage logs separately from final readback; no
invented downshift PASS if native stage records are absent or ambiguous.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_auto_off30 import configuration as auto_configuration
from tools.network_harness.runner import LinuxExperiment


def configuration(scene, source, run_id):
    assert scene["schema_version"]==1
    assert scene["scenario_id"]=="plan027-n-auto-rise-fall-10m-250ms-240s"
    assert (scene["product_mode"],scene["outer_repair"],scene["fec_start_profile"])==("fec-auto","off",1)
    assert (scene["offered_mbps_each_direction"],scene["one_way_delay_ms_each_direction"],scene["tun_mtu"])==(10,250,1400)
    assert (scene["warmup_s"],scene["drain_s"])==(5,10)
    mix=[(96,10),(288,15),(1060,30),(1200,45)]
    assert [(x["udp_payload_bytes"],x["packets_weight"]) for x in scene["packet_mix"]]==mix
    phases=[("uplink1_down5",25,1,5),("uplink15_down0",30,15,0),
            ("uplink30_down0",35,30,0),("uplink1_down0_low150",150,1,0)]
    assert [(x["name"],x["seconds"],x["c2s_loss_pct"],x["s2c_loss_pct"])
            for x in scene["phases"]]==phases
    base=json.loads(Path("scenarios/plan027-c-game2-fec-10m-250ms-loss30-60s.json").read_text())
    cfg=auto_configuration(base,source,run_id)
    cfg["id"]="M0_PLAN027_N_AUTO_RISE_FALL_UP1_15_30_1_DOWN5_0_240S"
    cfg["phases"]=[
        {"name":name,"seconds":sec,
         "c2s":{"delay_ms":250,"loss_pct":up,"rate_mbps":0},
         "s2c":{"delay_ms":250,"loss_pct":down,"rate_mbps":0}}
        for name,sec,up,down in phases]
    cfg["warmup_s"]=5
    cfg["drain_s"]=10
    cfg["seed"]=20261102
    tmp=copy.deepcopy(cfg)
    tmp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    validate(tmp)
    return cfg


def main():
    parser=argparse.ArgumentParser()
    for k in ("bundle","product-source","scenario","out"):
        parser.add_argument("--"+k,required=True)
    a=parser.parse_args()
    assert platform.machine()=="x86_64"
    assert Path(a.scenario).name=="plan027-n-auto-rise-fall-10m-250ms-240s.json"
    assert len(os.environ["GITHUB_SHA"])==40 and len(a.product_source)==40
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==a.product_source and manifest["architecture"]=="x86_64"
    hashes={}
    for line in (bundle/"SHA256SUMS").read_text().splitlines():
        dig,name=line.split(maxsplit=1);hashes[name.lstrip("*")]=dig
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for name in names:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==hashes[name]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in names:(home/name).symlink_to(bundle/name)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    case=root/"auto-multiphase"
    native=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=native.get("telemetry",{})
    final=t.get("fec_final_readback")
    result={
        "source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
        "same_frozen_bin_sha256":{n:hashes[n] for n in names},
        "scenario":scene["scenario_id"],
        "scope":"Native original Linux Go TLS/Rust M4 real Auto 10Mbps each 250ms each, source loss 1-15-30-1 pct, reverse5-0-0-0 pct, last150s low, outer DATA repair OFF",
        "native_result":native.get("result"),"failures":native.get("failures",[]),
        "limits":native.get("limits",[]),
        "native_final_readback":final,
        "native_outer_off_readback":t.get("outer_repair_native_verified"),
        "native_policy_readback":t.get("recovery_policy_verified"),
        "native_go_handoff":t.get("go_receive_handoff_verified"),
        "owned_stop":t.get("stop_drained_both"),
        "owned_netns_cleanup":native.get("cleanup",{}).get("owned_namespaces_absent"),
        "phase_business":{},"quality_timeline":{},
        "total_cpu_s_steady_240s":{},"rss_peak_bytes":{},
        "native_phase_transition_qualification":"NOT_RUN",
        "verdict":"NOT_RUN"}
    passed=(native.get("result")=="PASS_SCOPED_OBSERVATION"
            and t.get("effective_config_verified") is True
            and t.get("outer_repair_native_verified") is True
            and t.get("recovery_policy_verified") is True
            and t.get("go_receive_handoff_verified") is True
            and t.get("stop_drained_both") is True
            and native.get("cleanup",{}).get("owned_namespaces_absent") is True
            and isinstance(final,dict) and set(final)=={"client","server"}
            and all(v[0]=="auto" and 1<=int(v[3])<=6 for v in final.values()))
    for phase in scene["phases"]:
        rows=[x for x in native.get("observed",[]) if x.get("phase")==phase["name"]]
        detail={}
        for direction in ("c2s","s2c"):
            picked=[x for x in rows if x.get("direction")==direction and x.get("protocol")=="udp"]
            offered=sum(float(x.get("injected_app_mbps") or 0) for x in picked)
            first=sum(float(x.get("cohort_delivered_app_mbps") or 0) for x in picked)
            detail[direction]={"offered_mbps":offered,"unique_first_mbps":first,
                "first_fraction":first/offered if offered else None,
                "missing_after_drain":sum(int(x.get("missing_after_drain",0)) for x in picked),
                "p99_ms":next((x.get("first_arrival_ms",{}).get("p99_ms") for x in picked),None)}
            if offered<9.5 or first<=0:passed=False
        result["phase_business"][phase["name"]]=detail
    for role in ("client","server"):
        lines=(case/(role+"-auto-quality.log")).read_text().splitlines()
        quality=[v for v in lines if "V4_PUBLIC_FEC2_AUTO_QUALITY " in v]
        stage=[v for v in lines if "V4_PUBLIC_FEC2_AUTO_STAGE " in v]
        result["quality_timeline"][role]={
            "quality_samples":len(quality),"native_stage_events":stage[-24:],
            "quality_tail_samples":quality[-6:],
            "source":"real native whitelist-only Auto quality/stage logs capped at 160 lines"}
        result["total_cpu_s_steady_240s"][role]=native.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_peak_bytes"][role]=native.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["total_cpu_s_steady_240s"][role],(int,float)):passed=False
    # Native stage events have timestamps/grades; the human-reviewed stage
    # transition and 120s hold gate require inspecting those actual events.
    # Do NOT label final readback alone as proven downgrade within 120s.
    result["native_phase_transition_qualification"]="NATIVE_STAGE_LOG_ATTACHED_REVIEW_REQUIRED" if all(
        result["quality_timeline"][r]["native_stage_events"] for r in ("client","server")
    ) else "NOT_OBSERVED_STAGE_EVENTS"
    result["verdict"]=("PASS_SCOPED_REAL_AUTO_LIFECYCLE_MEASUREMENT_NOT_TRANSITION_GATE"
                        if passed else "FAIL_OR_INCONCLUSIVE")
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_AUTO_TIMELINE_VERDICT",result["verdict"],result["native_phase_transition_qualification"],flush=True)
    if not passed:raise SystemExit(2)

if __name__=="__main__":main()
