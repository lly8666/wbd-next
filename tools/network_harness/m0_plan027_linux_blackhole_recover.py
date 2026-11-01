"""One real original Normal double-underlay blackhole >90s and 120s recovery.
Standalone event-scope; use identical original frozen Go TLS/Rust M4 binary.
Native Go Health is unmodified. Source traffic and test probes are quiet
during both-way 100%-loss interval. No promise of seamless restoration.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_idle100_wake import configuration as idle_base
from tools.network_harness.runner import LinuxExperiment


def configuration(scene,source,run_id):
    assert scene["schema_version"]==1 and scene["scenario_id"]=="plan027-n-normal-both-blackhole105-recover120"
    assert (scene["public_mode"],scene["outer_repair"],scene["warmup_s"],scene["drain_s"])==("normal","off",5,10)
    assert scene["probe_hz"]==0 and (scene["offered_mbps_per_active_direction"],scene["one_way_delay_ms"])==(10,25)
    assert scene["packet_mix"]==[[64,10],[128,15],[512,25],[1200,50]]
    assert [(p["name"],p["seconds"],p["scale"],p["loss_pct"]) for p in scene["phases"]]==[
        ("pre20",20,1,0),("double_blackhole105",105,0,100),("recovery120",120,1,0)]
    idle=json.loads(Path("scenarios/plan027-n-normal-idle100-then-wake-160s.json").read_text())
    c=idle_base(idle,source,run_id)
    c["id"]="M0_PLAN027_N_ORIGINAL_BOTH_BLACKHOLE105_RECOVERY120"
    c["phases"]=[
        {"name":p["name"],"seconds":p["seconds"],"rate_scale":p["scale"],
         "c2s":{"delay_ms":25,"loss_pct":p["loss_pct"],"rate_mbps":0},
         "s2c":{"delay_ms":25,"loss_pct":p["loss_pct"],"rate_mbps":0}}
        for p in scene["phases"]]
    temp=copy.deepcopy(c)
    temp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    full=validate(temp)
    full["bundles"]["A"]=c["bundles"]["A"]
    return full


def main():
    p=argparse.ArgumentParser()
    for k in ("bundle","product-source","scenario","out"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-n-normal-both-blackhole105-recover120.json"
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==a.product_source and manifest["architecture"]=="x86_64"
    hash_by_name={}
    for row in (bundle/"SHA256SUMS").read_text().splitlines():
        sha,name=row.split(maxsplit=1);hash_by_name[name.lstrip("*")]=sha
    files=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for n in files:
        assert hashlib.sha256((bundle/n).read_bytes()).hexdigest()==hash_by_name[n]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for n in files:(home/n).symlink_to(bundle/n)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    case=root/"double-blackhole-recovery"
    leg=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    phases=leg.get("observed",[])
    result={
        "source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
        "binary_sha256":{n:hash_by_name[n] for n in files},
        "scope":"Linux original Go TLS Rust M4 Normal DATA outer OFF 10Mbps each active/25ms true both-way 105s 100pct netem and 120s restored new business, no test probes",
        "native_result":leg.get("result"),"failures":leg.get("failures",[]),
        "limits":leg.get("limits",[]),"native_outer_off":t.get("outer_repair_native_verified"),
        "native_go_handoff":t.get("go_receive_handoff_verified"),
        "owned_stop":t.get("stop_drained_both"),
        "owned_netns_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
        "business":{},"actual_netem_drop_by_phase":{},
        "cpu_s":{},"rss_peak_bytes":{},
        "authenticated_generation_rejoin":"NOT_OBSERVED_BY_THIS_ORIGINAL_SAME_GENERATION_SCENE",
        "verdict":"NOT_RUN"}
    valid=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
           and t.get("outer_repair_native_verified") is True
           and t.get("go_receive_handoff_verified") is True
           and t.get("stop_drained_both") is True
           and leg.get("cleanup",{}).get("owned_namespaces_absent") is True)
    for ph in scene["phases"]:
        group=ph["name"];result["business"][group]={}
        for direction in ("c2s","s2c"):
            rr=[v for v in phases if v.get("phase")==group and v.get("direction")==direction and v.get("protocol")=="udp"]
            offered=sum(float(v.get("injected_app_mbps") or 0) for v in rr)
            arrived=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in rr)
            result["business"][group][direction]={
                "offered_mbps":offered,"unique_first_mbps":arrived,
                "first_fraction":arrived/offered if offered else None,
                "sent":sum(int(v.get("sent",0)) for v in rr),
                "p99_ms":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in rr),None),
                "missing_after_drain":sum(int(v.get("missing_after_drain",0)) for v in rr)}
            if group=="double_blackhole105":
                if offered or arrived or any(v.get("sent",0) for v in rr):valid=False
            elif offered<9.5 or arrived<offered*(.9 if group=="recovery120" else .999):
                valid=False
    for row in leg.get("network_accounting",[]):
        if row.get("phase") not in result["actual_netem_drop_by_phase"]:
            result["actual_netem_drop_by_phase"][row["phase"]]={}
        result["actual_netem_drop_by_phase"][row["phase"]][row["role"]]=[
            {"drops":q.get("drops"),"approx_loss_pct":q.get("approx_loss_pct")}
            for q in row.get("netem",[])]
    # A real qdisc 100%-loss interval without *any* packet count cannot prove
    # that authentic product control was actually dropped, even if configured.
    rows=result["actual_netem_drop_by_phase"].get("double_blackhole105",{})
    for role in ("client","server"):
        if sum(int(v.get("drops") or 0) for v in rows.get(role,[]))<=0:
            valid=False
        result["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_peak_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role],(int,float)):valid=False
    result["verdict"]=("PASS_SCOPED_REAL_DOUBLE_BLACKHOLE105_RECOVER120_NEW_BUSINESS" if valid
                      else "FAIL_OR_INCONCLUSIVE")
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_REAL_DOUBLE_BLACKHOLE_VERDICT",result["verdict"],flush=True)
    if not valid:raise SystemExit(2)

if __name__=="__main__":main()
