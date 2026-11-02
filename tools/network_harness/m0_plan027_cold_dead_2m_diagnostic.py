"""Source-locked 2Mbps cold reauthorization discriminating diagnostic only.

Use EXACT original Go TLS/Rust Linux product whose 10Mbps real 105s blackout
left 379 missing and 27 upstream TUN drops. No accepted performance re-scope:
keep same 105s genuine bilateral 100% tc blackhole, no synthetic probes.
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
from tools.network_harness.m0_plan027_linux_blackhole_recover import configuration as blackhole10
from tools.network_harness.runner import LinuxExperiment

FILES=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")

def configuration(scene, source, run_id):
    assert scene["schema_version"]==1 and scene["scenario_id"]=="plan027-n-cold-dead105-2m-diagnostic"
    assert (scene["offered_mbps_per_active_direction"],scene["one_way_delay_ms"],
            scene["probe_hz"],scene["outer_repair"])==(2,25,0,"off")
    assert scene["packet_mix"]==[[64,10],[128,15],[512,25],[1200,50]]
    assert [(p["name"],p["seconds"],p["scale"],p["loss_pct"]) for p in scene["phases"]]==[
        ("pre20",20,1,0),("double_blackhole105",105,0,100),("recovery120",120,1,0)]
    original=json.loads(Path("scenarios/plan027-n-normal-both-blackhole105-recover120.json").read_text())
    cfg=blackhole10(original,source,run_id)
    # Only the ACTIVE source injection rate changes. Phases, tc, dead policy,
    # original owners, TLS, native flow and loss stay byte-for-byte the same.
    cfg["id"]="M0_PLAN027_N_COLD_REAUTH_DEAD105_SOURCE_2M_DIAGNOSTIC"
    cfg["traffic"]["c2s_mbps"]=2
    cfg["traffic"]["s2c_mbps"]=2
    cfg["seed"]=scene["seed"]
    return cfg

def evaluate(leg):
    t=leg.get("telemetry",{})
    out={"native_result":leg.get("result"),"native_failures":leg.get("failures",[]),
         "native_limits":leg.get("limits",[]),"business":{},
         "source_tun_tx_kernel_drops":leg.get("source_tun_tx_drops_steady",{}),
         "zero_delivery_ms":leg.get("active_zero_delivery_ms",{}),
         "original_go_handoff":t.get("go_receive_handoff_verified"),
         "native_outer_off":t.get("outer_repair_native_verified"),
         "owned_stop":t.get("stop_drained_both"),
         "owned_namespaces_absent":leg.get("cleanup",{}).get("owned_namespaces_absent"),
         "host_psi_peak_pct":leg.get("host",{}).get("cpu_psi_some_peak"),
         "host_steal_peak_pct":leg.get("host",{}).get("steal_pct_peak"),
         "original_process_cpu_s":{},"original_process_rss_peak_bytes":{},
         "actual_bilateral_blackhole_tc_drops":{}}
    valid=(leg.get("result") in ("PASS_SCOPED_OBSERVATION","INCONCLUSIVE")
           and not leg.get("failures") and t.get("go_receive_handoff_verified") is True
           and t.get("outer_repair_native_verified") is True
           and t.get("stop_drained_both") is True
           and leg.get("cleanup",{}).get("owned_namespaces_absent") is True)
    rows=leg.get("observed",[])
    for phase in ("pre20","double_blackhole105","recovery120"):
        out["business"][phase]={}
        for direction in ("c2s","s2c"):
            rr=[x for x in rows if x.get("phase")==phase and
                x.get("direction")==direction and x.get("protocol")=="udp"]
            offered=sum(float(x.get("injected_app_mbps") or 0) for x in rr)
            first=sum(float(x.get("cohort_delivered_app_mbps") or 0) for x in rr)
            out["business"][phase][direction]={
                "offered_mbps":offered,"first_mbps":first,
                "first_fraction":first/offered if offered else None,
                "missing_after_drain":sum(int(x.get("missing_after_drain",0)) for x in rr),
                "p99_delivered_only_ms":next((x.get("first_arrival_ms",{}).get("p99_ms") for x in rr),None),
                "sent":sum(int(x.get("sent",0)) for x in rr)}
            if phase=="double_blackhole105":
                if offered or first or any(x.get("sent",0) for x in rr):valid=False
            elif not rr or offered<1.9:valid=False
    for role in ("client","server"):
        drop=sum(int(x.get("drops") or 0) for row in leg.get("network_accounting",[])
                 if row.get("phase")=="double_blackhole105" and row.get("role")==role
                 for x in row.get("netem",[]))
        out["actual_bilateral_blackhole_tc_drops"][role]=drop
        if drop<=0:valid=False
        out["original_process_cpu_s"][role]=leg.get("measurement_cost",{}).get(role,{}).get("cpu_s")
        out["original_process_rss_peak_bytes"][role]=leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes")
    out["diagnostic_status"]="COMPLETE_SOURCE_RATE_DISCRIMINATOR_NOT_RECOVERY_PASS" if valid else "INCOMPLETE_OR_NATIVE_FAILURE"
    return out

def main():
    p=argparse.ArgumentParser()
    for key in ("bundle","product-source","scenario","out"):p.add_argument("--"+key,required=True)
    a=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-n-cold-dead105-2m-diagnostic.json"
    scene=json.loads(Path(a.scenario).read_text())
    bundle=Path(a.bundle).resolve()
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==a.product_source and manifest["architecture"]=="x86_64"
    hashes={}
    for row in (bundle/"SHA256SUMS").read_text().splitlines():
        hash,name=row.split(maxsplit=1);hashes[name.lstrip("*")]=hash
    for name in FILES:
        assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==hashes[name]
    root=Path(a.out).resolve()
    root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build"
    home.mkdir(parents=True,exist_ok=True)
    for name in FILES:(home/name).symlink_to(bundle/name)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    native=LinuxExperiment(cfg,root/"bundle-A",root/"cold-2m","A").run()
    result={"source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
            "binary_sha256":{name:hashes[name] for name in FILES},
            "scope":"Diagnostic only, ORIGINAL Go TLS Rust normal outer OFF: 2Mbps each 25ms active, 20s active/105s true both tc100% no app or probes/120s clean new UDP, same exact source and loss as earlier 10Mbps native INCONCLUSIVE.",
            "theory":{"mean_payload_bytes":753.6,"pps_each":331.74,
                      "business_BDP_bytes_each_RTT50ms":12500,
                      "original_10m_approx_pps_each":1658.7},
            "comparison_fixed":{"source_sha":a.product_source,
              "run_id":41368426841,"offered_mbps_each":10,
              "unique_first_fraction":{"c2s":1.0,"s2c":0.9981344292521493},
              "missing_recovery":{"c2s":0,"s2c":379},
              "source_tun_tx_drops_steady":{"client":0,"server":27},
              "zero_delivery_ms":{"c2s_udp":1230,"s2c_udp":1260},
              "result":"INCONCLUSIVE"},
            "native":evaluate(native)}
    result["verdict"]="DIAGNOSTIC_COMPLETE_NOT_BUSINESS_ACCEPTANCE" if result["native"]["diagnostic_status"].startswith("COMPLETE") else "DIAGNOSTIC_INCOMPLETE"
    (root/"result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PLAN027_COLD_DEAD_RATE_DIAGNOSTIC",result["verdict"],flush=True)
    if result["verdict"]!="DIAGNOSTIC_COMPLETE_NOT_BUSINESS_ACCEPTANCE":
        raise SystemExit(2)

if __name__=="__main__":main()
