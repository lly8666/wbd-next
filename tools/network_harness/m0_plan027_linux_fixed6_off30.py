"""PLAN027 N: single-lane Normal Fixed6 FEC at true 30% loss, outer DATA OFF.
Reuse the original R/Game2 immutable Linux Go TLS + Rust M4 binary. Test only
10Mbps each direction, 250ms one-way, 60s, same 910.8B weighted mix as Game2.
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
    assert scene["schema_version"]==1 and scene["public_mode"]=="game2-fec"
    assert (scene["duration_s"],scene["warmup_s"],scene["drain_s"],scene["tun_mtu"])==(60,5,10,1400)
    mix=[(96,10),(288,15),(1060,30),(1200,45)]
    for side in ("windows_to_linux","linux_to_windows"):
        q=scene[side]
        assert (q["offered_mbps"],q["delay_ms"],q["loss_pct"],q["tc_rate_mbps"])==(10,250,30,None)
        assert [(p["udp_payload_bytes"],p["packets_weight"]) for p in q["packet_mix"]]==mix
    # Shared traffic impairment borrowed only from existing Game2 scenario,
    # not its public mode. Exact effective mode is NORMAL Fixed6, single lane.
    c=_config("normal_maximum6","fec-fixed","off",6,30,source,run_id,
              "amd64",traffic_mbps=10)
    c["id"]="M0_PLAN027_N_FIXED6_10M_250MS_LOSS30_OUTER_OFF"
    c["seed"]=scene["seed"]
    c["product"]["repair_enabled"]=False
    c["traffic"].update(c2s_mbps=10,s2c_mbps=10,udp_share=1.0,
                        sizes=[list(x) for x in mix],deadline_ms=6000)
    c["warmup_s"]=5
    c["drain_s"]=10
    c["phases"]=[{"name":"iid","seconds":60,
                 "c2s":{"delay_ms":250,"loss_pct":30,"rate_mbps":0},
                 "s2c":{"delay_ms":250,"loss_pct":30,"rate_mbps":0}}]
    c["acceptance"]["require_retransmission"]=False
    c["acceptance"]["max_repair_fresh_pct"]=10
    c["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,
                             sha256="0"*64,repair_enabled=False,
                             require_go_rx_handoff=True)
    c=validate(c)
    c["bundles"]["A"]={"source":source,
                       "recovery_policy":"outer-opportunistic-v3",
                       "repair_enabled":False,"require_go_rx_handoff":True}
    return c


def main():
    p=argparse.ArgumentParser()
    for k in ("bundle","product-source","scenario","out"):
        p.add_argument("--"+k,required=True)
    a=p.parse_args()
    assert platform.machine()=="x86_64"
    assert Path(a.scenario).name=="plan027-c-game2-fec-10m-250ms-loss30-60s.json"
    assert len(os.environ["GITHUB_SHA"])==40 and len(a.product_source)==40
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==a.product_source and manifest["architecture"]=="x86_64"
    checksum={}
    for line in (bundle/"SHA256SUMS").read_text().splitlines():
        dig,name=line.split(maxsplit=1)
        checksum[name.lstrip("*")]=dig
    files=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for name in files:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==checksum[name]
    base=Path(a.out).resolve()
    base.mkdir(parents=True,exist_ok=True)
    home=base/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in files:(home/name).symlink_to(bundle/name)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    leg_dir=base/"normal-fixed6-off-loss30"
    leg=LinuxExperiment(cfg,base/"bundle-A",leg_dir,"A").run()
    t=leg.get("telemetry",{})
    result={"source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
            "original_same_binary_sha256":{n:checksum[n] for n in files},
            "scoped_mode":"Normal Fixed6 one lane, outer DATA OFF, 10Mbps each/250ms each/30pct real netem/60s",
            "packet_mix":"UDP96/288/1060/1200 weights10/15/30/45; same as Game2FEC6",
            "original_public_result":leg.get("result"),
            "failures":leg.get("failures",[]),"limits":leg.get("limits",[]),
            "native_fec_final_readback":t.get("fec_final_readback"),
            "native_fec_tx":t.get("FEC_k_r_parity_queue_decode"),
            "native_repair_off_readback":t.get("outer_repair_native_verified"),
            "native_policy_readback":t.get("recovery_policy_verified"),
            "original_go_handoff_readback":t.get("go_receive_handoff_verified"),
            "owned_stop":t.get("stop_drained_both"),
            "owned_namespaces_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
            "first_business":{},"ip_wire_F_R_C":{},"steady_cpu_s":{},
            "rss_peak_bytes":{},"tc_netem_drops":{},"verdict":"NOT_RUN"}
    fec=t.get("fec_final_readback",{})
    fec_data=t.get("FEC_k_r_parity_queue_decode",{})
    tx=fec_data.get("real_tx_owner_end_snapshot") if isinstance(fec_data,dict) else None
    passed=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
            and t.get("effective_config_verified") is True
            and t.get("outer_repair_native_verified") is True
            and t.get("recovery_policy_verified") is True
            and t.get("go_receive_handoff_verified") is True
            and t.get("stop_drained_both") is True
            and leg.get("cleanup",{}).get("owned_namespaces_absent") is True
            and isinstance(fec,dict) and set(fec)=={"client","server"}
            and isinstance(tx,dict) and set(tx)=={"client","server"})
    for direction,role in (("c2s","client"),("s2c","server")):
        row=[x for x in leg.get("observed",[]) if x.get("direction")==direction and x.get("phase")=="iid"]
        offered=sum(float(x.get("injected_app_mbps") or 0) for x in row)
        received=sum(float(x.get("cohort_delivered_app_mbps") or 0) for x in row)
        result["first_business"][direction]={
            "offered_mbps":offered,"unique_first_mbps":received,
            "delivered_fraction":received/offered if offered else None,
            "p99_ms":next((x.get("first_arrival_ms",{}).get("p99_ms")
                           for x in row if x.get("protocol")=="udp"),None)}
        if offered<9.5 or received<=0:passed=False
        account=leg.get("v3_repair_accounting",{}).get(direction,{})
        f=account.get("first_wire_bytes")
        r=account.get("conservative_charged_wire_bytes")
        result["ip_wire_F_R_C"][direction]={
            "F":f,"R":r,"C":"NOT_MEASURED_NOT_L2",
            "scope":"M4 actual source/repair IP bytes incl warmup"}
        if not isinstance(f,int) or f<=0 or r!=0:passed=False
        result["steady_cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_peak_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["steady_cpu_s"][role],(int,float)):passed=False
        if isinstance(tx,dict):
            evidence=tx.get(role) or {}
            if not isinstance(evidence,dict) or evidence.get("rsent",0)<=0:passed=False
    snaps=json.loads((leg_dir/"network-snapshots.json").read_text())
    b=next((v for v in snaps if v["name"]=="before-iid"),None)
    e=next((v for v in snaps if v["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def drops(v):
            if v is None:return None
            q=[x for x in v["network"][role]["qdisc"] if x.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        x,y=drops(b),drops(e)
        count=y-x if isinstance(x,int) and isinstance(y,int) else None
        result["tc_netem_drops"][role]=count
        if not isinstance(count,int) or count<=0:passed=False
    result["verdict"]=("PASS_SCOPED_FIXED6_OUTER_OFF_TRUE30_LOSS"
                       if passed else "FAIL_OR_INCONCLUSIVE")
    (base/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_N_FIXED6_OFF30_VERDICT",result["verdict"],flush=True)
    if not passed:raise SystemExit(2)


if __name__=="__main__":main()
