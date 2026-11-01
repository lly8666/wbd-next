"""PLAN027 R: true 30%-loss Normal outer DATA repair OFF -> ON SAME VM.
Both source-frozen original Go TLS+Rust endpoints, one scenario, sequential owned
namespace/Stop; no extra binary builds and no unsupported business recovery claim.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.m0_plan027_linux_repair_pair import configuration
from tools.network_harness.runner import LinuxExperiment


def paired_config(scene, source, run_id, enabled):
    assert scene["schema_version"]==1
    assert scene["scenario_id"]=="wl-outer-repair-10m-250ms-loss30-60s"
    assert (scene["duration_s"],scene["warmup_s"],scene["drain_s"],scene["tun_mtu"])==(60,5,10,1400)
    mix=[(64,10),(128,15),(512,25),(1200,50)]
    for side in ("windows_to_linux","linux_to_windows"):
        p=scene[side]
        assert (p["offered_mbps"],p["delay_ms"],p["loss_pct"],p["tc_rate_mbps"])==(10,250,30,None)
        assert [(v["udp_payload_bytes"],v["packets_weight"]) for v in p["packet_mix"]]==mix
    zero=json.loads(Path("scenarios/plan027-h539-normal-10m-250ms-loss0-60s.json").read_text())
    cfg=configuration(zero,source,run_id,enabled)
    cfg["id"]="M0_PLAN027_R_PAIRED_NORMAL_10M_250MS_LOSS30_"+("ON" if enabled else "OFF")
    cfg["seed"]=scene["seed"]
    for direction in ("c2s","s2c"):cfg["phases"][0][direction]["loss_pct"]=30
    return cfg


def collect(leg, enabled, case):
    t=leg.get("telemetry",{})
    out={"native_result":leg.get("result"),
         "failures":leg.get("failures",[]),
         "limits":leg.get("limits",[]),
         "repair_switch_requested":"ON" if enabled else "OFF",
         "native_repair_switch_readback":t.get("outer_repair_native_verified"),
         "native_policy_readback":t.get("recovery_policy_verified"),
         "go_handoff_readback":t.get("go_receive_handoff_verified"),
         "owned_stop":t.get("stop_drained_both"),
         "owned_netns_cleanup":leg.get("cleanup",{}).get("owned_namespaces_absent"),
         "first_business":{},"outer_ip_wire":{},"cpu_s":{},"rss_bytes":{},
         "tc_netem_drops":{}}
    ok=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
        and t.get("outer_repair_native_verified") is True
        and t.get("recovery_policy_verified") is True
        and t.get("go_receive_handoff_verified") is True
        and t.get("stop_drained_both") is True
        and leg.get("cleanup",{}).get("owned_namespaces_absent") is True)
    for direction,role in (("c2s","client"),("s2c","server")):
        rows=[x for x in leg.get("observed",[]) if x.get("phase")=="iid"
              and x.get("direction")==direction]
        offered=sum(float(x.get("injected_app_mbps") or 0) for x in rows)
        first=sum(float(x.get("cohort_delivered_app_mbps") or 0) for x in rows)
        out["first_business"][direction]={
            "offered_mbps":offered,"unique_first_mbps":first,
            "fraction":first/offered if offered else None,
            "delivered_p99_ms":next((x.get("first_arrival_ms",{}).get("p99_ms")
                                      for x in rows if x.get("protocol")=="udp"),None),
            "missing_after_drain":sum(int(x.get("missing_after_drain",0)) for x in rows)}
        if offered<9.5 or first<=0:ok=False
        account=leg.get("v3_repair_accounting",{}).get(direction,{})
        f=account.get("first_wire_bytes")
        r=account.get("conservative_charged_wire_bytes")
        out["outer_ip_wire"][direction]={
            "F":f,"R":r,
            "R_over_F":r/f if isinstance(r,int) and isinstance(f,int) and f>0 else None,
            "R_over_F_plus_R":r/(f+r) if isinstance(r,int) and isinstance(f,int) and f+r>0 else None,
            "C":"NOT_MEASURED",
            "accounting_scope":"real original Go TLS Rust M4 IP first/repair wire bytes full warmup+measurement, not L2"}
        if not isinstance(f,int) or f<=0 or not isinstance(r,int) or r<0 or r>f*.100000001:
            ok=False
        if enabled and r==0:ok=False
        if not enabled and r!=0:ok=False
        out["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        out["rss_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(out["cpu_s"][role],(int,float)):ok=False
    snapshots=json.loads((case/"network-snapshots.json").read_text())
    before=next((x for x in snapshots if x["name"]=="before-iid"),None)
    after=next((x for x in snapshots if x["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def drops(s):
            if s is None:return None
            q=[x for x in s["network"][role]["qdisc"] if x.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        p,q=drops(before),drops(after)
        val=q-p if isinstance(p,int) and isinstance(q,int) else None
        out["tc_netem_drops"][role]=val
        if not isinstance(val,int) or val<=0:ok=False
    out["verdict"]="PASS_SCOPED_NATIVE_LEG" if ok else "FAIL_OR_INCONCLUSIVE"
    return out


def main():
    p=argparse.ArgumentParser()
    for name in ("bundle","product-source","scenario","out"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args()
    assert platform.machine()=="x86_64"
    assert len(os.environ["GITHUB_SHA"])==40 and len(args.product_source)==40
    assert Path(args.scenario).name=="wl-outer-repair-10m-250ms-loss30-60s.json"
    scene=json.loads(Path(args.scenario).read_text())
    bundle=Path(args.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==args.product_source and manifest["architecture"]=="x86_64"
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    hashes={}
    for row in (bundle/"SHA256SUMS").read_text().splitlines():
        digest,name=row.split(maxsplit=1)
        hashes[name.lstrip("*")]=digest
    for name in names:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==hashes[name]
    base=Path(args.out).resolve()
    base.mkdir(parents=True,exist_ok=True)
    home=base/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in names:(home/name).symlink_to(bundle/name)
    result={"source_sha":args.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
            "scenario":scene["scenario_id"],
            "binary_sha256":{n:hashes[n] for n in names},
            "scope":"Normal original Go TLS both Linux endpoints Rust M4 true30pct netem, one same VM OFF then ON, 10Mbps each/250ms one-way/60s UDP64/128/512/1200B weighted 10/15/25/50",
            "legs":{},"cost_delta":{},"verdict":"NOT_RUN"}
    try:
        for mode,enabled in (("OFF",False),("ON",True)):
            cfg=paired_config(scene,args.product_source,int(os.environ["GITHUB_RUN_ID"]),enabled)
            case=base/("normal-off" if not enabled else "normal-on")
            native=LinuxExperiment(cfg,base/"bundle-A",case,"A").run()
            result["legs"][mode]=collect(native,enabled,case)
            # A failed owned first leg never contaminates second leg/VM.
            if result["legs"][mode]["verdict"]!="PASS_SCOPED_NATIVE_LEG":
                break
        if len(result["legs"])==2:
            off,on=result["legs"]["OFF"],result["legs"]["ON"]
            result["cost_delta"]={
                role:{"on_minus_off_cpu_s":on["cpu_s"][role]-off["cpu_s"][role],
                      "share_of_on_cpu":(on["cpu_s"][role]-off["cpu_s"][role])/on["cpu_s"][role] if on["cpu_s"][role] else None,
                      "on_minus_off_peak_rss_bytes":on["rss_bytes"][role]-off["rss_bytes"][role]}
                for role in ("client","server")}
            result["verdict"]="PASS_SCOPED_NORMAL_REAL_LOSS30_PAIRED_COST_NOT_BUSINESS_REPAIR"
            result["limitations"]=[
                "One OFF->ON same-VM order, not a general CPU optimization gain",
                "True30pct netem and different stochastic drops per leg: do not assign delivery delta to repair",
                "Outer repair only cosmetic opportunistic TCP-like presentation, not authenticated business-FEC recovery",
                "C physical/near-wire not captured, F/R M4 IP wire over warmup+measurement while process CPU steady only",
                "No Windows original NPF/physical, per-flow TCP HOL, 300s or other FEC/Game ON claim"]
        else:result["verdict"]="FAIL_OR_INCONCLUSIVE"
    finally:
        (base/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("PLAN027_R_NORMAL_30PCT_PAIR_VERDICT",result["verdict"],flush=True)
    if result["verdict"]!="PASS_SCOPED_NORMAL_REAL_LOSS30_PAIRED_COST_NOT_BUSINESS_REPAIR":
        raise SystemExit(2)

if __name__=="__main__":main()
