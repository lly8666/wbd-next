"""PLAN027 integration: one 300s Normal outer-ON original Linux duplex TCP/UDP.
Exact frozen Go TLS/Rust source. Two independent TCP streams plus new UDP,
real 1%-loss/25ms tc. One native run, no generated synthetic traffic claims.
"""
import argparse
import copy
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.m0_plan027_linux_repair_pair import configuration as original_normal
from tools.network_harness.runner import LinuxExperiment


def configuration(scene,source,run_id):
    assert scene["schema_version"]==1
    assert scene["scenario_id"]=="plan027-integration-normal-on-300s-mixed-hol"
    assert (scene["public_mode"],scene["outer_repair"])==("normal","on")
    assert (scene["duration_s"],scene["warmup_s"],scene["drain_s"],scene["tun_mtu"])==(300,5,10,1400)
    assert (scene["offered_mbps_each_direction"],scene["udp_share"],scene["tcp_flows"])==(10,.6,2)
    assert (scene["one_way_delay_ms"],scene["loss_pct"])==(25,1)
    assert scene["packet_mix"]==[[64,10],[128,15],[512,25],[1200,50]]
    zero=json.loads(Path("scenarios/plan027-h539-normal-10m-250ms-loss0-60s.json").read_text())
    c=original_normal(zero,source,run_id,True)
    c["id"]="M0_PLAN027_INTEGRATION_NORMAL_ON_300S_MIXED_TCP_UDP_HOL"
    c["seed"]=scene["seed"]
    c["warmup_s"]=5
    c["drain_s"]=10
    c["traffic"].update(c2s_mbps=10,s2c_mbps=10,
                        udp_share=.6,tcp_flows=2,probe_hz=20,deadline_ms=6000,
                        sizes=scene["packet_mix"],observe_independent_flows=True,
                        observe_size_classes=False)
    c["acceptance"].update(cross_business_hol=True,
                           require_retransmission=False,
                           max_repair_fresh_pct=10)
    c["phases"]=[{"name":"iid","seconds":300,
                  "c2s":{"delay_ms":25,"loss_pct":1,"rate_mbps":0},
                  "s2c":{"delay_ms":25,"loss_pct":1,"rate_mbps":0}}]
    tmp=copy.deepcopy(c)
    tmp["bundles"]["A"].update(run_id=run_id,artifact_id=run_id,attempt=1,sha256="0"*64)
    full=validate(tmp)
    full["bundles"]["A"]=c["bundles"]["A"]
    return full


def main():
    p=argparse.ArgumentParser()
    for n in ("bundle","product-source","scenario","out"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-integration-normal-on-300s-mixed-hol.json"
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    m=json.loads((bundle/"manifest.json").read_text())
    assert m["source"]==a.product_source and m["architecture"]=="x86_64"
    names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    hashes={}
    for line in (bundle/"SHA256SUMS").read_text().splitlines():
        dig,name=line.split(maxsplit=1)
        hashes[name.lstrip("*")]=dig
    for name in names:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==hashes[name]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in names:(home/name).symlink_to(bundle/name)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    case=root/"native-normal-on-300s"
    leg=LinuxExperiment(cfg,root/"bundle-A",case,"A").run()
    t=leg.get("telemetry",{})
    hol=leg.get("cross_business_hol",{})
    result={"source_sha":a.product_source,
            "fixture_source_sha":os.environ["GITHUB_SHA"],
            "binary_sha256":{n:hashes[n] for n in names},
            "scope":"Linux original Go TLS/Rust M4 Normal repair ON, 300s stable 10Mbps per direction .6 UDP/.4 TCP two independent TCP sockets, 25ms one-way/1pct true tc, 5s warmup 10s drain",
            "native_result":leg.get("result"),
            "failures":leg.get("failures",[]),"limits":leg.get("limits",[]),
            "native_repair_ON_readback":t.get("outer_repair_native_verified"),
            "native_policy_readback":t.get("recovery_policy_verified"),
            "original_go_handoff":t.get("go_receive_handoff_verified"),
            "owned_stop":t.get("stop_drained_both"),
            "owned_netns_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
            "native_300s_key_rotation":"NOT_OBSERVED_SEPARATE_HANDSHAKE_OR_ROTATION_TELEMETRY_REQUIRED",
            "independent_cross_business_hol":hol,
            "first_business":{},"F_R_C":{},"process_cpu_s_steady":{},
            "rss_peak_bytes":{},"tc_netem_drops":{},"verdict":"NOT_RUN"}
    passed=(leg.get("result")=="PASS_SCOPED_OBSERVATION"
            and t.get("effective_config_verified") is True
            and t.get("outer_repair_native_verified") is True
            and t.get("recovery_policy_verified") is True
            and t.get("go_receive_handoff_verified") is True
            and t.get("stop_drained_both") is True
            and leg.get("cleanup",{}).get("owned_namespaces_absent") is True
            and isinstance(hol,dict)
            and set(hol)=={"c2s/iid","s2c/iid"}
            and all(len(hol[d].get("tcp_independent_socket_flows",[]))==2
                    for d in ("c2s/iid","s2c/iid")))
    for direction,role in (("c2s","client"),("s2c","server")):
        rows=[v for v in leg.get("observed",[])
              if v.get("phase")=="iid" and v.get("direction")==direction]
        result["first_business"][direction]={}
        for proto,minimum in (("udp",4),("tcp",1)):
            selected=[v for v in rows if v.get("protocol")==proto]
            offered=sum(float(v.get("injected_app_mbps") or 0) for v in selected)
            arrived=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in selected)
            result["first_business"][direction][proto]={
                "offered_mbps":offered,"unique_delivered_mbps":arrived,
                "delivered_fraction":arrived/offered if offered else None,
                "p99_ms":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in selected),None),
                "missing_after_drain":sum(int(v.get("missing_after_drain",0)) for v in selected)}
            if offered<minimum or arrived<=0:passed=False
        ledger=leg.get("v3_repair_accounting",{}).get(direction,{})
        f=ledger.get("first_wire_bytes")
        repair=ledger.get("conservative_charged_wire_bytes")
        result["F_R_C"][direction]={
            "F_real_m4_ip_bytes":f,"R_real_m4_ip_bytes":repair,
            "R_over_F":repair/f if isinstance(f,int) and f>0 and isinstance(repair,int) else None,
            "C":"NOT_MEASURED_PHYSICAL_WIRE"}
        if not isinstance(f,int) or f<=0 or not isinstance(repair,int) or repair<0 or repair>f*.10000001:
            passed=False
        result["process_cpu_s_steady"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        result["rss_peak_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        if not isinstance(result["process_cpu_s_steady"][role],(int,float)):passed=False
    snapshots=json.loads((case/"network-snapshots.json").read_text())
    before=next((s for s in snapshots if s["name"]=="before-iid"),None)
    after=next((s for s in snapshots if s["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def drop(s):
            if s is None:return None
            q=[v for v in s["network"][role]["qdisc"] if v.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        b,e=drop(before),drop(after)
        delta=e-b if isinstance(b,int) and isinstance(e,int) else None
        result["tc_netem_drops"][role]=delta
        if not isinstance(delta,int) or delta<=0:passed=False
    result["verdict"]=("PASS_SCOPED_NORMAL_ON_300S_MIXED_HOL_NOT_PHYSICAL_ROTATION"
                        if passed else "FAIL_OR_INCONCLUSIVE")
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_INTEGRATION_300S_VERDICT",result["verdict"],flush=True)
    if not passed:raise SystemExit(2)

if __name__=="__main__":main()
