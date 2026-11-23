"""Native original-Go TLS + Rust raw/TUN Linux client AND server, true cosmetic outer repair.
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

def prepare(scenario,source,run_id,mode):
    assert scenario["schema_version"]==1
    rate=scenario["windows_to_linux"]["offered_mbps"]
    loss=scenario["windows_to_linux"]["loss_pct"]
    delay=scenario["windows_to_linux"]["delay_ms"]
    assert rate==10 and loss in (0,1,5,10,20,30) and delay==250
    assert scenario["linux_to_windows"]["offered_mbps"]==rate
    assert scenario["linux_to_windows"]["loss_pct"]==loss
    assert scenario["linux_to_windows"]["delay_ms"]==delay
    assert scenario["duration_s"]==60 and scenario["tun_mtu"]==1400
    assert scenario["warmup_s"]==5 and scenario["drain_s"]==10
    modes={"normal":("normal","off"),"game2":("game2","off"),
           "game4":("game4","off"),"game2-fec":("game2","fixed6"),
           "game4-fec":("game4","fixed6")}
    public_mode,game_fec=modes[mode]
    config=_config(mode.replace("-","_"),public_mode,game_fec,1,
                   loss,source,run_id,"amd64",traffic_mbps=rate)
    config["id"]=f"M0_COSMETIC_{mode.replace('-','_')}_{loss}P_{delay}MS"
    config["product"]["repair_enabled"]=True
    config["network"]["outer_mtu"]=1400
    config["seed"]=scenario["seed"]
    config["traffic"]["c2s_mbps"]=rate
    config["traffic"]["s2c_mbps"]=rate
    # Existing real two-Linux original product capacity fixture uses UDP-only.
    # TCP congestion/window backpressure at 300ms masked 50/100Mbps offers
    # in source db24's 90/10 exploratory cases; keep those INCONCLUSIVE.
    # Preserve exact 96/288/1060/1200 packet mix and 24-scene dimensions.
    config["traffic"]["udp_share"]=1.0
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
    config["acceptance"]["require_retransmission"]=False
    config["acceptance"]["max_repair_fresh_pct"]=10
    # _config intentionally strips the artifact locator AFTER validating
    # its build-independent inputs. Restore placeholders only for a second
    # strict parameter validation; never pass fake locator to the runner.
    config["bundles"]["A"].update({
        "run_id":run_id,"artifact_id":run_id,"attempt":1,"sha256":"0"*64,
        "require_go_rx_handoff":True,"repair_enabled":True})
    config=validate(config)
    config["bundles"]["A"]={
        "source":source,"recovery_policy":"outer-opportunistic-v3",
        "require_go_rx_handoff":True,"repair_enabled":True}
    return config

def genuine_case(scene,leg,dir_path,hashes,source,mode):
    loss=scene["windows_to_linux"]["loss_pct"]
    out={"source":source,"scene":scene["scenario_id"],"mode":mode,
         "real_client_os":"Linux","real_server_os":"Linux",
         "traffic_profile":"NATIVE_ORIGINAL_TLS_TUN_UDP_ONLY_MIXED_96_288_1060_1200",
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
        if mode=="normal":
            v=leg.get("v3_repair_accounting",{}).get(dirn,{})
            f=v.get("first_wire_bytes");g=v.get("accepted_repair_wire_bytes")
            u=v.get("uncertain_repair_wire_bytes")
            if not all(type(x) is int and x>=0 for x in (f,g,u)) or not f:
                out["repair"][role]="NOT_MEASURED_ORIGINAL_M4_F_R"
                reason.append("NO_NATIVE_M4_LEDGER_"+role)
                continue
            r=g+u;rat=r/f;total=r/(f+r)
            out["repair"][role]={"F":f,"R_accepted":g,"R_uncertain_charged":u,
                "R_F":rat,"R_over_F_plus_R":total,
                "accounting_scope":"real original M4 IP wire; not FEC parity or L2"}
            if rat>.100000001 or total>.100000001 or (loss==0 and rat>.0005):
                reason.append("REPAIR_BUDGET_OR_ZERO_LOSS_OVER_"+role)
            if loss>0 and not r:reason.append("NO_GENUINE_OUTER_APPEARANCE_"+role)
        else:
            p=leg.get("telemetry",{}).get("game_outer_policy",{}).get(role,{})
            repeats=p.get("outer_data_retransmitted")
            out["repair"][role]={"original_outer_data_repeat_count":repeats,
               "outer_policy":p,"wire_R_F":
               "NOT_MEASURED_GAME_PARITY_AND_FIRST_LANE_COPIES_NOT_OUTER_R"}
            if p.get("repair_enabled")!=1 or type(repeats) is not int:
                reason.append("NO_NATIVE_GAME_OUTER_LEDGER_"+role)
            elif loss>0 and repeats==0:
                reason.append("GAME_OUTER_NONZERO_NOT_OBSERVED_"+role)
            if mode.endswith("-fec"):
                proof=leg.get("telemetry",{}).get("game_fec_native_proof",{}).get(role,{})
                out.setdefault("parity_separate",{})[role]=proof
                if proof.get("parity_copied",0)<=0 or p.get("parity_separate")!=1:
                    reason.append("GAME_FEC_PARITY_NOT_SEPARATE_"+role)
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
        delta=out["netem_drops"][role]
        if type(delta) is not int or (loss>0 and delta<=0) or (loss==0 and delta!=0):
            reason.append("TRUE_NETEM_READBACK_MISSING_"+role)
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
    p.add_argument("--out",required=True)
    p.add_argument("--mode",choices=("normal","game2","game4","game2-fec","game4-fec"),
                   required=True)
    args=p.parse_args()
    source=os.environ["GITHUB_SHA"];assert len(source)==40
    assert platform.machine()=="x86_64"
    bundle=Path(args.bundle).resolve();base=Path(args.out).resolve();base.mkdir(parents=True,exist_ok=True)
    scene=json.loads(Path(args.scenario).read_text())
    assert scene["public_mode"]==args.mode
    expected_name=Path(args.scenario).stem
    assert scene["scenario_id"]==expected_name
    files=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
    assert all((bundle/n).is_file() for n in (*files,"manifest.json","SHA256SUMS"))
    m=json.loads((bundle/"manifest.json").read_text())
    assert m["source_sha"]==source and m["architecture"]=="x86_64"
    hashes={n:sha(bundle/n) for n in files}
    local=base/"bundle-A"/"fixed-build";local.mkdir(parents=True,exist_ok=True)
    for name in files:(local/name).symlink_to(bundle/name)
    cfg=prepare(scene,source,int(os.environ["GITHUB_RUN_ID"]),args.mode)
    case=base/cfg["id"]
    leg=LinuxExperiment(cfg,base/"bundle-A",case,"A").run()
    result=genuine_case(scene,leg,case,hashes,source,args.mode)
    (base/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print("M0_LINUX_DUAL_OUTER_RESULT",json.dumps(result,sort_keys=True),flush=True)
    if result["status"]!="PASS_BOTH_REAL_LINUX_NATIVE_OUTER_REPAIR":
        raise SystemExit(2)

if __name__=="__main__":main()
