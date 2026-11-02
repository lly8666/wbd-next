"""PLAN027 R: SAME Linux VM sequential Normal100Mbps lossless OFF→ON.
Source-frozen original Go TLS + Rust M4 product f5, no product rebuild.
High-PPS shadow/cache tax discriminator; failure never called a CPU benefit.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_repair_pair import configuration as normal_base
from tools.network_harness.runner import LinuxExperiment

def configuration(scene,source,run_id,enabled):
    assert scene["schema_version"]==1 and scene["scenario_id"]=="plan027-n-normal-off-100m-25ms-loss0-60s"
    assert (scene["offered_mbps_each_direction"],scene["delay_ms_each_direction"],
            scene["loss_pct_each_direction"],scene["duration_s"])==(100,25,0,60)
    assert scene["packet_mix"]==[[1200,100]]
    original=json.loads(Path("scenarios/plan027-h539-normal-10m-250ms-loss0-60s.json").read_text())
    c=normal_base(original,source,run_id,enabled)
    c["id"]="M0_PLAN027_R_NORMAL_100M_25MS_ZERO_"+("ON" if enabled else "OFF")
    c["traffic"].update(c2s_mbps=100,s2c_mbps=100,
                        sizes=[[1200,100]],udp_share=1.0,deadline_ms=6000)
    for d in ("c2s","s2c"):
        c["phases"][0][d].update(delay_ms=25,loss_pct=0,rate_mbps=0)
    c["phases"][0]["seconds"]=60
    c["seed"]=scene["seed"]
    tmp=copy.deepcopy(c)
    tmp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    c=validate(tmp)
    c["bundles"]["A"]={"source":source,"recovery_policy":"outer-opportunistic-v3",
                       "repair_enabled":enabled,"require_go_rx_handoff":True}
    return c

def measure(leg,enabled):
    t=leg.get("telemetry",{})
    out={"native_result":leg.get("result"),"failures":leg.get("failures",[]),
         "limits":leg.get("limits",[]),"repair_enabled":enabled,
         "native_switch_readback":t.get("outer_repair_native_verified"),
         "policy_readback":t.get("recovery_policy_verified"),
         "original_go_handoff":t.get("go_receive_handoff_verified"),
         "owned_stop":t.get("stop_drained_both"),
         "owned_netns_cleanup":leg.get("cleanup",{}).get("owned_namespaces_absent"),
         "first":{},"F_R_C":{},"cpu_s":{},"rss_bytes":{},
         "host_psi_peak":leg.get("host",{}).get("cpu_psi_some_peak"),
         "host_steal_peak":leg.get("host",{}).get("steal_pct_peak")}
    passed=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
            and t.get("outer_repair_native_verified") is True
            and t.get("recovery_policy_verified") is True
            and t.get("go_receive_handoff_verified") is True
            and t.get("stop_drained_both") is True
            and leg.get("cleanup",{}).get("owned_namespaces_absent") is True)
    for direction,role in (("c2s","client"),("s2c","server")):
        rows=[x for x in leg.get("observed",[])
              if x.get("phase")=="iid" and x.get("direction")==direction
              and x.get("protocol")=="udp"]
        offered=sum(float(v.get("injected_app_mbps") or 0) for v in rows)
        first=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in rows)
        out["first"][direction]={"offered_mbps":offered,
                                 "unique_first_mbps":first,
                                 "first_fraction":first/offered if offered else None,
                                 "p99_ms":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in rows),None),
                                 "missing_after_drain":sum(int(v.get("missing_after_drain",0)) for v in rows)}
        if offered<95 or first<offered*.999:passed=False
        a=leg.get("v3_repair_accounting",{}).get(direction,{})
        f=a.get("first_wire_bytes")
        r=a.get("conservative_charged_wire_bytes")
        out["F_R_C"][direction]={"F_m4_ip_bytes":f,"R_m4_ip_bytes":r,
                                "R_over_F":r/f if isinstance(r,int) and isinstance(f,int) and f>0 else None,
                                "C":"NOT_MEASURED_PHYSICAL_CONTROL"}
        if not isinstance(f,int) or f<=0 or not isinstance(r,int) or r<0 or r>f*.1:
            passed=False
        if not enabled and r!=0:passed=False
        out["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        out["rss_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(out["cpu_s"][role],(float,int)):passed=False
    out["verdict"]="PASS_SCOPED_NATIVE_LEG" if passed else "FAIL_OR_INCONCLUSIVE"
    return out

def main():
    p=argparse.ArgumentParser()
    for n in ("bundle","product-source","scenario","out"):p.add_argument("--"+n,required=True)
    args=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(args.scenario).name=="plan027-n-normal-off-100m-25ms-loss0-60s.json"
    source=args.product_source
    assert len(source)==40
    sc=json.loads(Path(args.scenario).read_text())
    bundle=Path(args.bundle).resolve()
    m=json.loads((bundle/"manifest.json").read_text())
    assert m["source"]==source and m["architecture"]=="x86_64"
    hashes={}
    for row in (bundle/"SHA256SUMS").read_text().splitlines():
        sha,name=row.split(maxsplit=1);hashes[name.lstrip("*")]=sha
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for n in names:
        assert hashlib.sha256((bundle/n).read_bytes()).hexdigest()==hashes[n]
    root=Path(args.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for n in names:(home/n).symlink_to(bundle/n)
    result={"product_source_sha":source,"fixture_sha":os.environ["GITHUB_SHA"],
            "binary_sha256":{n:hashes[n] for n in names},
            "scenario":sc["scenario_id"],"one_vm_sequential_order":["OFF","ON"],
            "theory":{"app_mbps_each":100,"avg_payload_B":1200,
                      "app_pps_each":10416.667,"business_BDP_bytes_RTT50ms_each":625000},
            "legs":{},"delta":{},"verdict":"NOT_RUN"}
    try:
        for name,enabled in (("OFF",False),("ON",True)):
            cfg=configuration(sc,source,int(os.environ["GITHUB_RUN_ID"]),enabled)
            run=LinuxExperiment(cfg,root/"bundle-A",root/("leg-"+name.lower()),"A").run()
            result["legs"][name]=measure(run,enabled)
            if result["legs"][name]["verdict"]!="PASS_SCOPED_NATIVE_LEG":
                break
        if set(result["legs"])=={"OFF","ON"}:
            a,b=result["legs"]["OFF"],result["legs"]["ON"]
            for role in ("client","server"):
                off,on=a["cpu_s"][role],b["cpu_s"][role]
                result["delta"][role]={
                    "ON_minus_OFF_cpu_s":on-off,
                    "fraction_of_ON_cpu":(on-off)/on if on else None,
                    "ON_minus_OFF_peak_RSS_bytes":b["rss_bytes"][role]-a["rss_bytes"][role]}
            result["verdict"]="PASS_SCOPED_ORIGINAL_NORMAL100_SAME_VM_OFF_ON_COST_NOT_OPTIMIZATION"
        else:result["verdict"]="FAIL_OR_INCONCLUSIVE"
        result["limits"]=["Same VM sequential OFF then ON, independent iid0% no causal per-packet language split",
                          "Whole Go+Rust CPU; extra ON egress vs bookkeeping not separately sampled",
                          "Exact product frozen f5, not newer Go cold reauth source",
                          "No physical wire C or Windows and 0% netem does not test repair recovery"]
    finally:
        (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("PLAN027_R_NORMAL100_PAIR",result["verdict"],flush=True)
    if result["verdict"]!="PASS_SCOPED_ORIGINAL_NORMAL100_SAME_VM_OFF_ON_COST_NOT_OPTIMIZATION":
        raise SystemExit(2)

if __name__=="__main__":main()
