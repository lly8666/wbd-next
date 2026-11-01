"""One source-frozen original Linux Normal payload-idle >90s then real new business.
Traffic/probe generator OFF for 100 seconds, product's own Health untouched.
Not a loss-of-Health or physical machine qualification.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_repair_pair import configuration as normal
from tools.network_harness.runner import LinuxExperiment


def configuration(scene,source,run_id):
    assert scene["schema_version"]==1 and scene["scenario_id"]=="plan027-n-normal-idle100-then-wake-160s"
    assert (scene["mode"],scene["repair"])==("normal","off")
    assert (scene["duration_s"],scene["warmup_s"],scene["drain_s"])==(160,5,10)
    assert (scene["mbps_each_direction_when_active"],scene["one_way_delay_ms"],scene["loss_pct"])==(10,25,0)
    assert scene["injected_probe_hz"]==0
    assert scene["udp_payload_mix"]==[[64,10],[128,15],[512,25],[1200,50]]
    assert [(p["name"],p["seconds"],p["rate_scale"]) for p in scene["phases"]]==[
        ("initial20",20,1),("payload_idle100",100,0),("resume40",40,1)]
    original=json.loads(Path("scenarios/plan027-h539-normal-10m-250ms-loss0-60s.json").read_text())
    cfg=normal(original,source,run_id,False)
    cfg["id"]="M0_PLAN027_N_NORMAL_REAL_PAYLOAD_IDLE100_WAKE40"
    cfg["traffic"].update(probe_hz=0,udp_share=1.0,deadline_ms=6000,
                          sizes=scene["udp_payload_mix"])
    cfg["phases"]=[{"name":p["name"],"seconds":p["seconds"],"rate_scale":p["rate_scale"],
                    "c2s":{"delay_ms":25,"loss_pct":0,"rate_mbps":0},
                    "s2c":{"delay_ms":25,"loss_pct":0,"rate_mbps":0}}
                   for p in scene["phases"]]
    cfg["warmup_s"]=5
    cfg["drain_s"]=10
    cfg["seed"]=20261102
    temp=copy.deepcopy(cfg)
    temp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    normalized=validate(temp)
    normalized["bundles"]["A"]=cfg["bundles"]["A"]
    return normalized


def main():
    p=argparse.ArgumentParser()
    for name in ("bundle","product-source","scenario","out"):
        p.add_argument("--"+name,required=True)
    a=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-n-normal-idle100-then-wake-160s.json"
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==a.product_source and manifest["architecture"]=="x86_64"
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    hashes={}
    for row in (bundle/"SHA256SUMS").read_text().splitlines():
        digest,name=row.split(maxsplit=1);hashes[name.lstrip("*")]=digest
    for name in names:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==hashes[name]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in names:(home/name).symlink_to(bundle/name)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    case=root/"real-idle100-wake40"
    leg=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    result={
        "source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
        "binary_sha256":{n:hashes[n] for n in names},
        "scope":"Original Go TLS+Rust Normal outer DATA repair OFF, 20s active then genuine 100s payload+probe generator silent then 40s new UDP first business each direction, 25ms clean",
        "native_result":leg.get("result"),"failures":leg.get("failures",[]),
        "limits":leg.get("limits",[]),
        "native_off_readback":t.get("outer_repair_native_verified"),
        "policy_readback":t.get("recovery_policy_verified"),
        "go_handoff":t.get("go_receive_handoff_verified"),
        "owned_stop":t.get("stop_drained_both"),
        "owned_netns_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
        "phase_business":{},"cpu_s":{},"rss_bytes":{},
        "real_idle_health_packets":"NOT_SEPARATELY_COUNTED_BY_THIS_FIXTURE",
        "independent_health_loss_and_lane_failure":"NOT_RUN",
        "verdict":"NOT_RUN"}
    passed=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
            and t.get("effective_config_verified") is True
            and t.get("outer_repair_native_verified") is True
            and t.get("recovery_policy_verified") is True
            and t.get("go_receive_handoff_verified") is True
            and t.get("stop_drained_both") is True
            and leg.get("cleanup",{}).get("owned_namespaces_absent") is True)
    rows=leg.get("observed",[])
    for ph in scene["phases"]:
        name=ph["name"]
        result["phase_business"][name]={}
        for direction in ("c2s","s2c"):
            rr=[x for x in rows if x.get("phase")==name and x.get("direction")==direction and x.get("protocol")=="udp"]
            offered=sum(float(x.get("injected_app_mbps") or 0) for x in rr)
            first=sum(float(x.get("cohort_delivered_app_mbps") or 0) for x in rr)
            result["phase_business"][name][direction]={
                "offered_mbps":offered,"unique_first_mbps":first,
                "fraction":first/offered if offered else None,
                "p99_ms":next((x.get("first_arrival_ms",{}).get("p99_ms") for x in rr),None),
                "sent":sum(int(x.get("sent",0)) for x in rr),
                "missing_after_drain":sum(int(x.get("missing_after_drain",0)) for x in rr)}
            if name=="payload_idle100":
                if offered!=0 or first!=0 or any(v.get("sent",0) for v in rr):passed=False
            elif offered<9.5 or first<offered*.999 or not rr:passed=False
    for role in ("client","server"):
        result["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role],(int,float)):passed=False
    for direction in ("c2s","s2c"):
        account=leg.get("v3_repair_accounting",{}).get(direction,{})
        if account.get("conservative_charged_wire_bytes")!=0:passed=False
    result["verdict"]=("PASS_SCOPED_100S_REAL_PAYLOAD_IDLE_AND_NEW_BUSINESS_WAKE"
                       if passed else "FAIL_OR_INCONCLUSIVE")
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_IDLE100_WAKE40_VERDICT",result["verdict"],flush=True)
    if not passed:raise SystemExit(2)

if __name__=="__main__":main()
