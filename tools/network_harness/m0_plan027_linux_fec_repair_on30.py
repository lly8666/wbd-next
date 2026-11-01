"""PLAN027 single-lane Fixed6/Auto ON: two independent Actions, one native job each.
Each uses identical original Go TLS+Rust M4 frozen product source/packet mix
as its already-observed OFF counterpart. Not a same-VM CPU A/B experiment.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_fixed6_off30 import configuration as fixed_off
from tools.network_harness.m0_plan027_linux_auto_off30 import configuration as auto_off
from tools.network_harness.runner import LinuxExperiment


def configuration(scene, source, run_id, mode):
    assert mode in ("fixed6", "auto")
    assert scene["scenario_id"]=="plan027-c-game2-fec-10m-250ms-loss30-60s"
    cfg=(fixed_off if mode=="fixed6" else auto_off)(scene,source,run_id)
    cfg["id"]="M0_PLAN027_INTEGRATION_"+mode.upper()+"_OUTER_ON_10M250MS30P"
    cfg["product"]["repair_enabled"]=True
    cfg["bundles"]["A"]["repair_enabled"]=True
    tmp=copy.deepcopy(cfg)
    tmp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    v=validate(tmp)
    v["bundles"]["A"]=cfg["bundles"]["A"]
    return v


def main():
    p=argparse.ArgumentParser()
    for name in ("bundle","product-source","scenario","out"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--mode",required=True,choices=("fixed6","auto"))
    a=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-c-game2-fec-10m-250ms-loss30-60s.json"
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    m=json.loads((bundle/"manifest.json").read_text())
    assert m["source"]==a.product_source and m["architecture"]=="x86_64"
    hashes={}
    for line in (bundle/"SHA256SUMS").read_text().splitlines():
        digest,name=line.split(maxsplit=1)
        hashes[name.lstrip("*")]=digest
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for name in names:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==hashes[name]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in names:(home/name).symlink_to(bundle/name)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]),a.mode)
    case=root/("native-"+a.mode+"-on30")
    leg=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    fec=t.get("fec_final_readback",{})
    tx=t.get("FEC_k_r_parity_queue_decode",{})
    parity=tx.get("real_tx_owner_end_snapshot",{}) if isinstance(tx,dict) else {}
    result={"product_source_sha":a.product_source,
            "fixture_source_sha":os.environ["GITHUB_SHA"],
            "binary_sha256":{n:hashes[n] for n in names},
            "mode":a.mode,
            "native_mode":"fec-fixed" if a.mode=="fixed6" else "fec-auto",
            "scope":"Original Go TLS two original Linux endpoints and Rust M4 single lane FEC, outer repair ON, 10Mbps each, 250ms one-way, real IID30pct tc/60s, UDP96/288/1060/1200B mix10/15/30/45",
            "source_off_baseline_is_different_VM_not_AB":True,
            "native_result":leg.get("result"),
            "failures":leg.get("failures",[]),"limits":leg.get("limits",[]),
            "native_fec_final_readback":fec,
            "native_real_fec_tx":tx,
            "native_outer_on_readback":t.get("outer_repair_native_verified"),
            "native_policy_readback":t.get("recovery_policy_verified"),
            "native_original_go_handoff":t.get("go_receive_handoff_verified"),
            "owned_stop":t.get("stop_drained_both"),
            "owned_namespaces_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
            "unique_first_business":{},"original_m4_F_R_C":{},
            "cpu_s":{},"rss_peak_bytes":{},"tc_netem_drops":{},
            "verdict":"NOT_RUN"}
    ok=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
        and t.get("effective_config_verified") is True
        and t.get("outer_repair_native_verified") is True
        and t.get("recovery_policy_verified") is True
        and t.get("go_receive_handoff_verified") is True
        and t.get("stop_drained_both") is True
        and leg.get("cleanup",{}).get("owned_namespaces_absent") is True
        and isinstance(fec,dict) and set(fec)=={"client","server"}
        and isinstance(parity,dict) and set(parity)=={"client","server"})
    expected_mode="fixed" if a.mode=="fixed6" else "auto"
    for role in ("client","server"):
        read=fec.get(role,[])
        if (len(read)!=5 or read[0]!=expected_mode
            or (a.mode=="fixed6" and int(read[3])!=6)
            or (parity.get(role) or {}).get("rsent",0)<=0):
            ok=False
    for direction,role in (("c2s","client"),("s2c","server")):
        rows=[v for v in leg.get("observed",[])
              if v.get("direction")==direction and v.get("phase")=="iid" and v.get("protocol")=="udp"]
        offered=sum(float(v.get("injected_app_mbps") or 0) for v in rows)
        first=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in rows)
        result["unique_first_business"][direction]={
            "offered_mbps":offered,"unique_first_mbps":first,
            "first_fraction":first/offered if offered else None,
            "p99_ms_delivered_only":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in rows),None),
            "missing_after_drain":sum(int(v.get("missing_after_drain",0)) for v in rows)}
        if offered<9.5 or first<offered*.99:ok=False
        ledger=leg.get("v3_repair_accounting",{}).get(direction,{})
        f=ledger.get("first_wire_bytes")
        r=ledger.get("conservative_charged_wire_bytes")
        result["original_m4_F_R_C"][direction]={
            "F_ip_bytes_full":f,"R_ip_bytes_full":r,
            "R_over_F":r/f if isinstance(f,int) and f>0 and isinstance(r,int) else None,
            "R_over_F_plus_R":r/(f+r) if isinstance(f,int) and isinstance(r,int) and f+r>0 else None,
            "C":"NOT_MEASURED_PHYSICAL_WIRE"}
        if not isinstance(f,int) or f<=0 or not isinstance(r,int) or r<0 or r>f*.10000001:
            ok=False
        result["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_peak_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role],(int,float)):ok=False
    snaps=json.loads((case/"network-snapshots.json").read_text())
    before=next((v for v in snaps if v["name"]=="before-iid"),None)
    after=next((v for v in snaps if v["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def dropped(s):
            if s is None:return None
            q=[v for v in s["network"][role]["qdisc"] if v.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        b,e=dropped(before),dropped(after)
        delta=e-b if isinstance(b,int) and isinstance(e,int) else None
        result["tc_netem_drops"][role]=delta
        if not isinstance(delta,int) or delta<=0:ok=False
    result["verdict"]=("PASS_SCOPED_"+a.mode.upper()+"_NATIVE_REPAIR_ON_TRUE30" if ok
                       else "FAIL_OR_INCONCLUSIVE")
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_INTEGRATION_FEC_SINGLE_LANE_ON",a.mode,result["verdict"],flush=True)
    if not ok:raise SystemExit(2)

if __name__=="__main__":main()
