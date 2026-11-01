"""PLAN027 Game4FEC6 original Linux outer DATA repair ON adapter proof.
Same SOURCE and 20Mbps/250ms/30% true netem previously tested OFF. This
records actual frozen outer copies and 4-lane copy policy, NOT ratio F/R/C.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_game4fec_zero20 import configuration as game4_off
from tools.network_harness.runner import LinuxExperiment


def configuration(scene,source,run_id):
    assert scene["scenario_id"]=="plan027-c-game4-fec-20m-250ms-loss30-60s"
    c=game4_off(scene,source,run_id)
    c["id"]="M0_PLAN027_INTEGRATION_GAME4FEC6_20M_250MS_LOSS30_OUTER_ON"
    c["product"]["repair_enabled"]=True
    c["bundles"]["A"]["repair_enabled"]=True
    tmp=copy.deepcopy(c)
    tmp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    c=validate(tmp)
    c["bundles"]["A"]={"source":source,"recovery_policy":"outer-opportunistic-v3",
                        "repair_enabled":True,"require_go_rx_handoff":True,
                        "game4_copy_schedule":"stagger-4-50-140"}
    return c


def main():
    parser=argparse.ArgumentParser()
    for k in ("bundle","product-source","scenario","out"):parser.add_argument("--"+k,required=True)
    a=parser.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-c-game4-fec-20m-250ms-loss30-60s.json"
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
    case=root/"game4-fec6-on-loss30"
    leg=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    policy=t.get("game_outer_policy",{})
    copy_schedule=t.get("game4_copy_schedule_readback",{})
    proof=t.get("game_fec_native_proof",{})
    passed=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
            and t.get("effective_config_verified") is True
            and t.get("outer_repair_native_verified") is True
            and t.get("go_receive_handoff_verified") is True
            and t.get("stop_drained_both") is True
            and leg.get("cleanup",{}).get("owned_namespaces_absent") is True
            and isinstance(policy,dict) and set(policy)=={"client","server"}
            and isinstance(copy_schedule,dict) and set(copy_schedule)=={"client","server"}
            and isinstance(proof,dict) and set(proof)=={"client","server"})
    for role in ("client","server"):
        p=policy.get(role,{})
        sch=copy_schedule.get(role,{})
        if (p.get("repair_enabled")!=1
            or p.get("outer_data_retransmitted",0)<=0
            or p.get("parity_separate")!=1
            or sch.get("mode")!=2
            or len(sch.get("sent",[]))!=4
            or not all(n>0 for n in sch.get("sent",[]))
            or proof.get(role,{}).get("parity_copied",0)<=0):
            passed=False
    result={
        "source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
        "same_off_source_binary_sha256":{n:hashes[n] for n in names},
        "scope":"Original Linux Go TLS Rust M4 Game4 fixed6 4 lanes outer DATA ON 20Mbps each/250ms one-way/30% true tc/60s, same mix as OFF control",
        "native_result":leg.get("result"),"failures":leg.get("failures",[]),
        "limits":leg.get("limits",[]),"game_fec_proof":proof,
        "game_outer_readback":policy,"game4_copy_schedule":copy_schedule,
        "native_outer_on_verified":t.get("outer_repair_native_verified"),
        "native_go_handoff":t.get("go_receive_handoff_verified"),
        "owned_stop":t.get("stop_drained_both"),
        "owned_namespaces_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
        "first_business":{},"cpu_s":{},"rss_bytes":{},"real_netem_drops":{},
        "F_R_C":"NOT_MEASURED_GAME_4LANE_COPIES_AND_PARITY_BYTE_DENOMINATOR; outer_data_retransmitted is a native COUNT not wire fraction",
        "verdict":"NOT_RUN"}
    for direction,role in (("c2s","client"),("s2c","server")):
        rows=[v for v in leg.get("observed",[]) if v.get("phase")=="iid" and v.get("direction")==direction]
        offered=sum(float(v.get("injected_app_mbps") or 0) for v in rows)
        first=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in rows)
        result["first_business"][direction]={
            "offered_mbps":offered,"unique_first_mbps":first,
            "first_fraction":first/offered if offered else None,
            "p99_ms":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in rows if v.get("protocol")=="udp"),None),
            "missing_after_drain":sum(int(v.get("missing_after_drain",0)) for v in rows)}
        if offered<19 or first<offered*.99:passed=False
        result["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role],(int,float)):passed=False
    snapshots=json.loads((case/"network-snapshots.json").read_text())
    b=next((v for v in snapshots if v["name"]=="before-iid"),None)
    e=next((v for v in snapshots if v["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def dropped(s):
            if s is None:return None
            q=[v for v in s["network"][role]["qdisc"] if v.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        start,end=dropped(b),dropped(e)
        delta=end-start if isinstance(start,int) and isinstance(end,int) else None
        result["real_netem_drops"][role]=delta
        if not isinstance(delta,int) or delta<=0:passed=False
    result["verdict"]="PASS_SCOPED_GAME4_FEC6_ON_NATIVE_COPIES_NOT_WIRE_RATIO" if passed else "FAIL_OR_INCONCLUSIVE"
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_GAME4_ON_VERDICT",result["verdict"],flush=True)
    if not passed:raise SystemExit(2)

if __name__=="__main__":main()
