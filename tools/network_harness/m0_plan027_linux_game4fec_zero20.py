"""PLAN027 N Game4 fixed6 four-lane source-frozen Linux original product 20Mbps.
One 0%-loss/250ms/60s capacity screen before impairing higher-copy Game4,
outer DATA repair OFF. Verify the REAL four-copy scheduling, FEC, owned Stop.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_game2fec_off30 import configuration as game2_configuration
from tools.network_harness.runner import LinuxExperiment


def configuration(scene, source, run_id):
    assert scene["schema_version"]==1 and scene["public_mode"]=="game4-fec"
    assert scene["scenario_id"]=="plan027-c-game4-fec-20m-250ms-loss0-60s"
    assert (scene["duration_s"],scene["warmup_s"],scene["drain_s"],scene["tun_mtu"])==(60,5,10,1400)
    mix=[(96,10),(288,15),(1060,30),(1200,45)]
    for direction in ("windows_to_linux","linux_to_windows"):
        v=scene[direction]
        assert (v["offered_mbps"],v["delay_ms"],v["loss_pct"],v["tc_rate_mbps"])==(20,250,0,None)
        assert [(x["udp_payload_bytes"],x["packets_weight"]) for x in v["packet_mix"]]==mix
    # The existing Game2 config is the SAME original TLS/Rust binary and
    # native FEC6 path. Change only Game4 public mode/schedule, load and tc.
    game2=json.loads(Path("scenarios/plan027-c-game2-fec-10m-250ms-loss30-60s.json").read_text())
    cfg=game2_configuration(game2,source,run_id)
    cfg["id"]="M0_PLAN027_N_GAME4_FEC6_20M_250MS_LOSS0_OUTER_OFF"
    cfg["seed"]=scene["seed"]
    cfg["product"]["mode"]="game4"
    cfg["product"]["game4_copy_schedule"]="stagger-4-50-140"
    cfg["product"]["repair_enabled"]=False
    cfg["traffic"].update(c2s_mbps=20,s2c_mbps=20,
                          sizes=[list(x) for x in mix])
    for direction in ("c2s","s2c"):cfg["phases"][0][direction]["loss_pct"]=0
    cfg["bundles"]["A"]["game4_copy_schedule"]="stagger-4-50-140"
    tmp=copy.deepcopy(cfg)
    tmp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    cfg=validate(tmp)
    cfg["bundles"]["A"]={"source":source,
                         "recovery_policy":"outer-opportunistic-v3",
                         "repair_enabled":False,
                         "require_go_rx_handoff":True,
                         "game4_copy_schedule":"stagger-4-50-140"}
    return cfg


def main():
    parser=argparse.ArgumentParser()
    for k in ("bundle","product-source","scenario","out"):
        parser.add_argument("--"+k,required=True)
    a=parser.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-c-game4-fec-20m-250ms-loss0-60s.json"
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==a.product_source and manifest["architecture"]=="x86_64"
    hashes={}
    for line in (bundle/"SHA256SUMS").read_text().splitlines():
        d,n=line.split(maxsplit=1);hashes[n.lstrip("*")]=d
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for n in names:
        assert hashlib.sha256((bundle/n).read_bytes()).hexdigest()==hashes[n]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for n in names:(home/n).symlink_to(bundle/n)
    config=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    case=root/"game4-fec6-zero20"
    leg=LinuxExperiment(config,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    proof=t.get("game_fec_native_proof",{})
    policy=t.get("game_outer_policy",{})
    schedule=t.get("game4_copy_schedule_readback",{})
    valid=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
           and t.get("effective_config_verified") is True
           and t.get("outer_repair_native_verified") is True
           and t.get("go_receive_handoff_verified") is True
           and t.get("stop_drained_both") is True
           and leg.get("cleanup",{}).get("owned_namespaces_absent") is True
           and isinstance(proof,dict) and set(proof)=={"client","server"}
           and isinstance(policy,dict) and set(policy)=={"client","server"}
           and isinstance(schedule,dict) and set(schedule)=={"client","server"})
    for role in ("client","server"):
        p=policy.get(role,{})
        sch=schedule.get(role,{})
        if (p.get("repair_enabled")!=0 or p.get("outer_data_retransmitted")!=0
            or p.get("parity_separate")!=1 or sch.get("mode")!=2
            or not all(x>0 for x in sch.get("sent",[]))
            or len(sch.get("sent",[]))!=4
            or proof.get(role,{}).get("parity_copied",0)<=0):
            valid=False
    result={
        "source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
        "binary_sha256":{n:hashes[n] for n in names},
        "scenario":scene["scenario_id"],"native_result":leg.get("result"),
        "failures":leg.get("failures",[]),"limits":leg.get("limits",[]),
        "scope":"Original Linux Go TLS/Rust Game4 4 lanes fixed6, 20Mbps each/250ms one-way/0pct tc/60s, stagger-4-50-140 native copy, outer DATA OFF",
        "native_game_parity_proof":proof,"native_outer_policy":policy,
        "native_game4_copy_schedule":schedule,
        "native_outer_off_readback":t.get("outer_repair_native_verified"),
        "go_handoff":t.get("go_receive_handoff_verified"),
        "owned_stop":t.get("stop_drained_both"),
        "owned_netns_cleanup":leg.get("cleanup",{}).get("owned_namespaces_absent"),
        "first_business":{},"cpu_s":{},"rss_bytes":{},"tc_netem_drops":{},
        "verdict":"NOT_RUN"}
    for d,role in (("c2s","client"),("s2c","server")):
        rows=[v for v in leg.get("observed",[]) if v.get("phase")=="iid" and v.get("direction")==d]
        offered=sum(float(v.get("injected_app_mbps") or 0) for v in rows)
        first=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in rows)
        result["first_business"][d]={
            "offered_mbps":offered,"unique_first_mbps":first,
            "first_fraction":first/offered if offered else None,
            "p99_ms":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in rows if v.get("protocol")=="udp"),None),
            "missing_after_drain":sum(int(v.get("missing_after_drain",0)) for v in rows)}
        if offered<19 or first<offered*.999:valid=False
        result["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role],(int,float)):valid=False
    for row in leg.get("network_accounting",[]):
        if row.get("phase")=="iid":
            result["tc_netem_drops"][row["role"]]=sum(int(v.get("drops",0)) for v in row.get("netem",[]))
    result["verdict"]="PASS_SCOPED_GAME4_FEC6_20M_ZERO_OUTER_OFF_CAPACITY" if valid else "FAIL_OR_INCONCLUSIVE"
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_N_GAME4_20M_ZERO_VERDICT",result["verdict"],flush=True)
    if not valid:raise SystemExit(2)

if __name__=="__main__":main()
