"""PLAN027 original Normal 100Mbps each 25ms clean 1200B capacity screen.
One immutable real Go TLS+Rust M4 Linux product, repair OFF, no FEC/Game.
Do not assume green runner or injector rate proves business first delivery.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_repair_pair import configuration as normal_config
from tools.network_harness.runner import LinuxExperiment


def configuration(scene,source,run_id):
    assert scene["schema_version"]==1
    assert scene["scenario_id"]=="plan027-n-normal-off-100m-25ms-loss0-60s"
    assert scene["public_mode"]=="normal" and scene["outer_repair"]=="off"
    assert (scene["offered_mbps_each_direction"],scene["delay_ms_each_direction"],scene["loss_pct_each_direction"])==(100,25,0)
    assert (scene["warmup_s"],scene["duration_s"],scene["drain_s"],scene["tun_mtu"])==(5,60,10,1400)
    assert scene["packet_mix"]==[[1200,100]]
    base=json.loads(Path("scenarios/plan027-h539-normal-10m-2100ms-loss0-60s.json").read_text())
    c=normal_config(base,source,run_id,False)
    c["id"]="M0_PLAN027_N_ORIGINAL_NORMAL_100M_25MS_ZERO_REPAIR_OFF"
    c["seed"]=scene["seed"]
    c["traffic"].update(c2s_mbps=100,s2c_mbps=100,udp_share=1.0,
                        sizes=[[1200,100]],observe_size_classes=False,
                        observe_independent_flows=False,deadline_ms=6000)
    c["warmup_s"]=5
    c["drain_s"]=10
    c["phases"]=[{"name":"iid","seconds":60,
                  "c2s":{"delay_ms":25,"loss_pct":0,"rate_mbps":0},
                  "s2c":{"delay_ms":25,"loss_pct":0,"rate_mbps":0}}]
    t=copy.deepcopy(c)
    t["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    v=validate(t)
    v["bundles"]["A"]=c["bundles"]["A"]
    return v


def main():
    p=argparse.ArgumentParser()
    for name in ("bundle","product-source","scenario","out"):p.add_argument("--"+name,required=True)
    a=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-n-normal-off-100m-25ms-loss0-60s.json"
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    m=json.loads((bundle/"manifest.json").read_text())
    assert m["source"]==a.product_source and m["architecture"]=="x86_64"
    hashes={}
    for row in (bundle/"SHA256SUMS").read_text().splitlines():
        sha,name=row.split(maxsplit=1);hashes[name.lstrip("*")]=sha
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    for n in names:assert hashlib.sha256((bundle/n).read_bytes()).hexdigest()==hashes[n]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for n in names:(home/n).symlink_to(bundle/n)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    case=root/"normal-off100-clean"
    leg=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    result={"source_sha":a.product_source,"fixture_sha":os.environ["GITHUB_SHA"],
            "binary_sha256":{n:hashes[n] for n in names},
            "scenario":scene["scenario_id"],"native_result":leg.get("result"),
            "failures":leg.get("failures",[]),"limits":leg.get("limits",[]),
            "theory":{"business_mbps_each_direction":100,"payload_bytes":1200,
                      "approx_pps_each_direction":5208.333,
                      "RTT_ms":100,"business_BDP_bytes_each_direction":625000,
                      "nominal_total_bidirectional_business_pps":10416.666},
            "original_native_outer_off_verified":t.get("outer_repair_native_verified"),
            "original_go_handoff":t.get("go_receive_handoff_verified"),
            "owned_stop":t.get("stop_drained_both"),
            "owned_namespace_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
            "first_delivery":{},"cpu_s":{},"rss_peak_bytes":{},
            "host_pressure":{"psi_some_peak":leg.get("host",{}).get("cpu_psi_some_peak"),
                             "steal_pct_peak":leg.get("host",{}).get("steal_pct_peak")},
            "source_tun_drops":leg.get("source_tun_tx_drops_warmup"),
            "real_netem_drops":{},"verdict":"NOT_RUN"}
    ok=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
        and t.get("effective_config_verified") is True
        and t.get("outer_repair_native_verified") is True
        and t.get("go_receive_handoff_verified") is True
        and t.get("stop_drained_both") is True
        and leg.get("cleanup",{}).get("owned_namespaces_absent") is True)
    for direction,role in (("c2s","client"),("s2c","server")):
        rr=[v for v in leg.get("observed",[]) if v.get("direction")==direction
            and v.get("phase")=="iid" and v.get("protocol")=="udp"]
        offered=sum(float(v.get("injected_app_mbps") or 0) for v in rr)
        delivered=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in rr)
        result["first_delivery"][direction]={
            "offered_mbps":offered,"unique_first_mbps":delivered,
            "first_fraction":delivered/offered if offered else None,
            "missing_after_drain":sum(int(v.get("missing_after_drain",0)) for v in rr),
            "delivered_p99_ms":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in rr),None)}
        if offered<95 or delivered<offered*.999:ok=False
        acct=leg.get("v3_repair_accounting",{}).get(direction,{})
        if not isinstance(acct.get("first_wire_bytes"),int) or acct.get("conservative_charged_wire_bytes")!=0:
            ok=False
        result["cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_peak_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["cpu_s"][role],(int,float)):ok=False
    snaps=json.loads((case/"network-snapshots.json").read_text())
    before=next((x for x in snaps if x["name"]=="before-iid"),None)
    after=next((x for x in snaps if x["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def count(s):
            if s is None:return None
            q=[x for x in s["network"][role]["qdisc"] if x.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        b,e=count(before),count(after)
        n=e-b if isinstance(b,int) and isinstance(e,int) else None
        result["real_netem_drops"][role]=n
        if n!=0:ok=False
    result["verdict"]="PASS_SCOPED_NORMAL_OFF100_CLEAN_CAPACITY" if ok else "FAIL_OR_INCONCLUSIVE"
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_NORMAL_OFF100_CAP_VERDICT",result["verdict"],flush=True)
    if not ok:raise SystemExit(2)

if __name__=="__main__":main()
