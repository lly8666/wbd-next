"""Native original-Go TLS + Rust raw/TUN Linux client AND server, exact 24-scene outer repair.
Every scene starts two fresh original product executables in owned Linux namespaces.
Not a Windows emulator, fixture-only estimate, replay, or synthetic kernel result.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.fec_w167_dual_arch_matrix import _config, analyze, sha
from tools.network_harness.runner import LinuxExperiment

def prepare(scenario,source,run_id):
    assert scenario["schema_version"]==1
    rate=scenario["windows_to_linux"]["offered_mbps"]
    loss=scenario["windows_to_linux"]["loss_pct"]
    delay=scenario["windows_to_linux"]["delay_ms"]
    assert rate in (50,100) and loss in (1,5,10,30) and delay in (50,150,300)
    assert scenario["linux_to_windows"]["offered_mbps"]==rate
    assert scenario["linux_to_windows"]["loss_pct"]==loss
    assert scenario["linux_to_windows"]["delay_ms"]==delay
    assert scenario["duration_s"]==60 and scenario["tun_mtu"]==1400
    assert scenario["warmup_s"]==5 and scenario["drain_s"]==10
    config=_config("normal_off","normal","off",1,loss,source,run_id,"amd64",traffic_mbps=rate)
    config["id"]=f"M0_LINUX_DUAL_{rate}M_{loss}P_{delay}MS"
    config["seed"]=scenario["seed"]
    config["traffic"]["c2s_mbps"]=rate
    config["traffic"]["s2c_mbps"]=rate
    config["traffic"]["udp_share"]=.9  # real product UDP/TCP, unlike W168 UDP-only
    config["traffic"]["sizes"]=[[v["udp_payload_bytes"],v["packets_weight"]]
                                  for v in scenario["windows_to_linux"]["packet_mix"]]
    config["traffic"]["observe_size_classes"]=True
    config["traffic"]["deadline_ms"]=6000
    config["warmup_s"]=5
    config["drain_s"]=10
    config["phases"]=[{"name":"iid","seconds":60,
        "c2s":{"delay_ms":delay,"loss_pct":loss,"rate_mbps":0},
        "s2c":{"delay_ms":delay,"loss_pct":loss,"rate_mbps":0}}]
    # No V3 per-link rate cap: the same 50/100Mbps offered payload, not a
    # separate rate limiter masquerading as outer 10% quota.
    config["acceptance"]["require_retransmission"]=True
    config["acceptance"]["max_repair_fresh_pct"]=10
    # _config intentionally strips the artifact locator AFTER validating
    # its build-independent inputs. Restore placeholders only for a second
    # strict parameter validation; never pass fake locator to the runner.
    config["bundles"]["A"].update({
        "run_id":run_id,"artifact_id":run_id,"attempt":1,"sha256":"0"*64,
        "require_go_rx_handoff":True})
    config=validate(config)
    config["bundles"]["A"]={
        "source":source,"recovery_policy":"outer-opportunistic-v3",
        "require_go_rx_handoff":True}
    return config

def genuine_case(scene,leg,dir_path,hashes,source):
    out={"source":source,"scene":scene["scenario_id"],
         "requested_rate_mbps_each_direction":scene["windows_to_linux"]["offered_mbps"],
         "actual_result":leg.get("result"),
         "failures":leg.get("failures",[]),"limits":leg.get("limits",[]),
         "cleanup":leg.get("cleanup"),"binary_sha256":hashes,
         "original_tls_go_rust_client_and_server":True,
         "measure_duration_s":60,"repair":{},"measured_app":{},"netem_drops":{}}
    reason=[]
    if leg.get("result")!="PASS_SCOPED_OBSERVATION":reason.append("ORIGINAL_PRODUCT_NOT_FULL_PASS")
    if not leg.get("cleanup",{}).get("owned_namespaces_absent"):reason.append("OWNED_NETNS_NOT_CLEAN")
    if not leg.get("telemetry",{}).get("stop_drained_both"):reason.append("NATIVE_BOTH_STOP_NOT_PASS")
    if not leg.get("telemetry",{}).get("recovery_policy_verified"):reason.append("OUTER_ON_NOT_AUTHENTIC")
    for role,dirn in (("client","c2s"),("server","s2c")):
        v=leg.get("v3_repair_accounting",{}).get(dirn,{})
        f=v.get("first_wire_bytes");g=v.get("accepted_repair_wire_bytes")
        u=v.get("uncertain_repair_wire_bytes")
        if not all(type(x) is int and x>=0 for x in (f,g,u)) or not f:
            reason.append("NO_NATIVE_M4_LEDGER_"+role);continue
        r=g+u;rat=r/f;total=r/(f+r)
        target=scene["windows_to_linux"]["offered_mbps"]
        proxy=r/(target*1_000_000*(60+5)/8)
        out["repair"][role]={"F":f,"R_accepted":g,"R_uncertain_charged":u,
            "R_F":rat,"R_over_F_plus_R":total,
            "R_over_business_target_proxy":proxy,
            "accounting_scope":"real original M4 IP wire incl TCP/IP headers, not L2 or physical C"}
        if not r:reason.append("ZERO_OPPORTUNISTIC_REPAIR_"+role)
        if rat>.100000001 or total>.100000001:reason.append("REPAIR_OVER_10PCT_"+role)
        if scene["windows_to_linux"]["loss_pct"]==30 and proxy<.06:
            reason.append("HIGH_LOSS_REPAIR_INSUFFICIENT_"+role)
    for direction in ("c2s","s2c"):
        rows=[r for r in leg.get("observed",[])
              if r.get("phase")=="iid" and r.get("direction")==direction]
        offered=sum(float(r.get("injected_app_mbps") or 0) for r in rows)
        target=scene["windows_to_linux"]["offered_mbps"]
        out["measured_app"][direction]={"offered_mbps":offered,
            "protocols":[r.get("protocol") for r in rows],
            "unique_first_delivered_mbps":sum(float(r.get("cohort_delivered_app_mbps") or 0) for r in rows)}
        if offered<target*.95:reason.append("OFFER_CAPACITY_LIMITED_"+direction)
    snap=json.loads((dir_path/"network-snapshots.json").read_text())
    a=next((v for v in snap if v["name"]=="before-iid"),None)
    b=next((v for v in snap if v["name"]=="measurement-end"),None)
    for role in ("client","server"):
        def dropped(s):
            if not s:return None
            q=[v for v in s["network"][role]["qdisc"] if v.get("kind")=="netem"]
            return q[0].get("drops") if len(q)==1 else None
        first,last=dropped(a),dropped(b)
        out["netem_drops"][role]=last-first if all(type(v) is int for v in (first,last)) else None
        if not isinstance(out["netem_drops"][role],int) or out["netem_drops"][role]<=0:
            reason.append("TRUE_NETEM_LOSS_MISSING_"+role)
    out["process_measurement_cpu_s"]={
        role:leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        for role in ("client","server")}
    out["process_peak_rss_bytes"]={
        role:leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
        for role in ("client","server")}
    out["status"]="PASS_BOTH_REAL_LINUX_NATIVE_OUTER_REPAIR" if not reason else "FAIL_OR_INCONCLUSIVE"
    out["blockers"]=reason
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bundle",required=True);p.add_argument("--scenario",required=True)
    p.add_argument("--out",required=True);args=p.parse_args()
    source=os.environ["GITHUB_SHA"];assert len(source)==40
    assert platform.machine()=="x86_64"
    bundle=Path(args.bundle).resolve();base=Path(args.out).resolve();base.mkdir(parents=True,exist_ok=True)
    scene=json.loads(Path(args.scenario).read_text())
    expected_name=Path(args.scenario).stem
    assert scene["scenario_id"]==expected_name
    files=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    assert all((bundle/n).is_file() for n in (*files,"manifest.json","SHA256SUMS"))
    m=json.loads((bundle/"manifest.json").read_text())
    assert m["source"]==source and m["architecture"]=="x86_64"
    hashes={n:sha(bundle/n) for n in files}
    local=base/"bundle-A"/"fixed-build";local.mkdir(parents=True,exist_ok=True)
    for name in files:(local/name).symlink_to(bundle/name)
    cfg=prepare(scene,source,int(os.environ["GITHUB_RUN_ID"]))
    case=base/cfg["id"]
    leg=LinuxExperiment(cfg,base/"bundle-A",case,"A").run()
    result=genuine_case(scene,leg,case,hashes,source)
    (base/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print("M0_LINUX_DUAL_OUTER_RESULT",json.dumps(result,sort_keys=True),flush=True)
    if result["status"]!="PASS_BOTH_REAL_LINUX_NATIVE_OUTER_REPAIR":
        raise SystemExit(2)

if __name__=="__main__":main()
