"""PLAN027 N: genuine Game2FEC6 outer-DATA-OFF 10Mbps/30pct/250ms, 60s.
One Linux original TLS two-lane product scene; reuse frozen Normal product binary.
No claim that parity copies are outer R or that different packet mixes prove gain.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.fec_w167_dual_arch_matrix import _config
from tools.network_harness.runner import LinuxExperiment


def configuration(scene, source, run_id):
    assert scene["schema_version"] == 1 and scene["public_mode"] == "game2-fec"
    assert scene["scenario_id"] == "plan027-c-game2-fec-10m-250ms-loss30-60s"
    assert (scene["duration_s"], scene["warmup_s"], scene["drain_s"], scene["tun_mtu"]) == (60,5,10,1400)
    mix = [(96,10),(288,15),(1060,30),(1200,45)]
    for role in ("windows_to_linux", "linux_to_windows"):
        v = scene[role]
        assert (v["offered_mbps"],v["delay_ms"],v["loss_pct"],v["tc_rate_mbps"]) == (10,250,30,None)
        assert [(r["udp_payload_bytes"],r["packets_weight"]) for r in v["packet_mix"]] == mix
    cfg = _config("game2_fixed6", "game2", "fixed6", 1, 30, source,
                  run_id, "amd64", traffic_mbps=10)
    cfg["id"] = "M0_PLAN027_N_GAME2_FEC6_LOSS30_OUTER_OFF"
    cfg["seed"] = scene["seed"]
    cfg["product"]["repair_enabled"] = False
    cfg["traffic"].update(c2s_mbps=10,s2c_mbps=10,udp_share=1.0,
                          sizes=[list(x) for x in mix],deadline_ms=6000)
    cfg["warmup_s"] = 5
    cfg["drain_s"] = 10
    cfg["phases"] = [{"name":"iid","seconds":60,
                      "c2s":{"delay_ms":250,"loss_pct":30,"rate_mbps":0},
                      "s2c":{"delay_ms":250,"loss_pct":30,"rate_mbps":0}}]
    cfg["acceptance"]["require_retransmission"] = False
    cfg["bundles"]["A"].update(
        run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64,
        repair_enabled=False,require_go_rx_handoff=True)
    cfg = validate(cfg)
    cfg["bundles"]["A"] = {
        "source":source,"recovery_policy":"outer-opportunistic-v3",
        "repair_enabled":False,"require_go_rx_handoff":True}
    return cfg


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--bundle",required=True)
    a.add_argument("--product-source",required=True)
    a.add_argument("--scenario",required=True)
    a.add_argument("--out",required=True)
    args = a.parse_args()
    assert platform.machine()=="x86_64"
    assert len(os.environ["GITHUB_SHA"])==40 and len(args.product_source)==40
    assert Path(args.scenario).name=="plan027-c-game2-fec-10m-250ms-loss30-60s.json"
    scene=json.loads(Path(args.scenario).read_text())
    bundle=Path(args.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==args.product_source and manifest["architecture"]=="x86_64"
    checks=dict(line.split(maxsplit=1) for line in (bundle/"SHA256SUMS").read_text().splitlines())
    checks={k.lstrip("*"):v for v,k in checks.items()}
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for name in names:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==checks[name]
    root=Path(args.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in names:(home/name).symlink_to(bundle/name)
    cfg=configuration(scene,args.product_source,int(os.environ["GITHUB_RUN_ID"]))
    case=root/"game2-fec6-off-loss30"
    leg=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    proof=t.get("game_fec_native_proof",{})
    policy=t.get("game_outer_policy",{})
    verdict=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
             and t.get("effective_config_verified") is True
             and t.get("outer_repair_native_verified") is True
             and t.get("go_receive_handoff_verified") is True
             and t.get("stop_drained_both") is True
             and leg.get("cleanup",{}).get("owned_namespaces_absent") is True
             and isinstance(proof,dict) and set(proof)=={"client","server"}
             and isinstance(policy,dict) and set(policy)=={"client","server"})
    for role in ("client","server"):
        row=policy.get(role,{})
        if (row.get("repair_enabled")!=0
            or row.get("outer_data_retransmitted")!=0
            or row.get("parity_separate")!=1
            or proof.get(role,{}).get("parity_copied",0)<=0):
            verdict=False
    result={"product_source":args.product_source,
            "fixture_source":os.environ["GITHUB_SHA"],
            "original_go_tls_rust_game2_fec6":True,
            "same_frozen_binary_as_R_N_normal":True,
            "scenario":scene["scenario_id"],
            "binary_sha256":{n:checks[n] for n in names},
            "native_result":leg.get("result"),"failures":leg.get("failures",[]),
            "limits":leg.get("limits",[]),
            "outer_data_off_readback":t.get("outer_repair_native_verified"),
            "original_go_handoff":t.get("go_receive_handoff_verified"),
            "owned_stop":t.get("stop_drained_both"),
            "owned_namespaces_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
            "fec_proof":proof,"outer_policy":policy,
            "first_business":{},"cpu_s":{},"rss_peak_bytes":{},"netem_drops":{},
            "outer_F_R_C":"NOT_COMPARABLE_GAME_MULTI_LANE; FEC parity is not outer DATA R",
            "verdict":"NOT_RUN"}
    for direction,role in (("c2s","client"),("s2c","server")):
        rows=[x for x in leg.get("observed",[]) if x.get("phase")=="iid" and x.get("direction")==direction]
        offered=sum(float(x.get("injected_app_mbps") or 0) for x in rows)
        arrived=sum(float(x.get("cohort_delivered_app_mbps") or 0) for x in rows)
        result["first_business"][direction]={
            "offered_mbps":offered,"delivered_mbps":arrived,
            "delivered_fraction":arrived/offered if offered else None,
            "first_p99_ms":next((x.get("first_arrival_ms",{}).get("p99_ms") for x in rows
                                  if x.get("protocol")=="udp"),None)}
        if offered<9.5 or arrived<=0:verdict=False
        result["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_peak_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
    snapshots=json.loads((case/"network-snapshots.json").read_text())
    before=next((x for x in snapshots if x["name"]=="before-iid"),None)
    after=next((x for x in snapshots if x["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def dropped(s):
            if s is None:return None
            q=[x for x in s["network"][role]["qdisc"] if x.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        b,e=dropped(before),dropped(after)
        delta=e-b if isinstance(b,int) and isinstance(e,int) else None
        result["netem_drops"][role]=delta
        if not isinstance(delta,int) or delta<=0:verdict=False
    result["verdict"]=("PASS_SCOPED_GAME2FEC6_OUTER_OFF_TRUE_30LOSS"
                        if verdict else "FAIL_OR_INCONCLUSIVE")
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_N_GAME2FEC6_OFF30_VERDICT",result["verdict"],flush=True)
    if not verdict:raise SystemExit(2)


if __name__=="__main__":main()
