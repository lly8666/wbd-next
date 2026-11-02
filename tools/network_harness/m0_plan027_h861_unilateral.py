"""One true original cold unidirectional Health-dead/rejoin product diagnostic.

A single c2s 105s tc 100% interval while s2c remains healthy, zero
app/probe during blackout, then genuine 2Mbps/dir new TUN traffic for 120s.
Retain first and native errors, never fake a symmetric healthy Health signal.
"""
import argparse
import hashlib
import json
import os
import platform
import re
from pathlib import Path
from tools.network_harness.m0_plan027_linux_blackhole_recover import configuration as bilateral
from tools.network_harness.runner import LinuxExperiment
FILES=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")

def configuration(scene,source,run):
    assert scene["schema_version"]==1 and scene["scenario_id"]=="plan027-n-cold-unilateral-c2s105-2m"
    assert (scene["offered_mbps_per_active_direction"],scene["one_way_delay_ms"],scene["probe_hz"],scene["outer_repair"])==(2,25,0,"off")
    assert scene["packet_mix"]==[[64,10],[128,15],[512,25],[1200,50]]
    assert [(p["seconds"],p["scale"],p["c2s_loss_pct"],p["s2c_loss_pct"]) for p in scene["phases"]]==[
      (20,1,0,0),(105,0,100,0),(120,1,0,0)]
    original=json.loads(Path("scenarios/plan027-n-normal-both-blackhole105-recover120.json").read_text())
    cfg=bilateral(original,source,run)
    cfg["id"]="M0_PLAN027_N_ONEWAY_C2S_AUTH_DEAD105_NEW_BUSINESS120"
    cfg["traffic"]["c2s_mbps"]=2
    cfg["traffic"]["s2c_mbps"]=2
    cfg["seed"]=scene["seed"]
    cfg["phases"]=[{"name":p["name"],"seconds":p["seconds"],"rate_scale":p["scale"],
                    "c2s":{"delay_ms":25,"loss_pct":p["c2s_loss_pct"],"rate_mbps":0},
                    "s2c":{"delay_ms":25,"loss_pct":p["s2c_loss_pct"],"rate_mbps":0}}
                   for p in scene["phases"]]
    return cfg

def stages(path,role):
    # Only already whitelisted fixed numeric original Go cold stages.
    text=path.read_text(errors="replace") if path.is_file() else ""
    pat=re.compile(r"V4_PUBLIC_COLD_STAGE role="+role+r" stage=(dead_drained|tun_trigger|syn_start|syn_established|first_syn|native_ready) unix_ms=(\d+)(?: elapsed_ms=(\d+))?")
    return [{"stage":m.group(1),"unix_ms":int(m.group(2)),
             "elapsed_ms":int(m.group(3)) if m.group(3) else None}
            for m in list(pat.finditer(text))[-12:]]

def main():
    p=argparse.ArgumentParser()
    for k in ("bundle","product-source","scenario","out"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    assert platform.machine()=="x86_64" and len(os.environ["GITHUB_SHA"])==40
    assert Path(a.scenario).name=="plan027-n-cold-unilateral-c2s105-2m.json"
    scene=json.loads(Path(a.scenario).read_text())
    product=Path(a.bundle).resolve()
    manifest=json.loads((product/"manifest.json").read_text())
    assert manifest["source"]==a.product_source and manifest["architecture"]=="x86_64"
    checks={}
    for row in (product/"SHA256SUMS").read_text().splitlines():
        digest,name=row.split(maxsplit=1);checks[name.lstrip("*")]=digest
    for name in FILES:assert hashlib.sha256((product/name).read_bytes()).hexdigest()==checks[name]
    root=Path(a.out).resolve();root.mkdir(parents=True,exist_ok=True)
    home=root/"bundle-A"/"fixed-build";home.mkdir(parents=True,exist_ok=True)
    for name in FILES:(home/name).symlink_to(product/name)
    cfg=configuration(scene,a.product_source,int(os.environ["GITHUB_RUN_ID"]))
    leg=LinuxExperiment(cfg,root/"bundle-A",root/"oneway","A").run()
    data={"source_sha":a.product_source,"fixture_source_sha":os.environ["GITHUB_SHA"],
          "binary_sha256":{n:checks[n] for n in FILES},
          "scope":"Original Go TLS Rust M4 Normal outer OFF true c2s-only105s tc100pct s2c0pct, no blackout app/probe, 2Mbps each 25ms before20/restore120; asymmetric Health generation test NOT 10Mbps acceptance",
          "native_result":leg.get("result"),"native_failures":leg.get("failures",[]),"native_limits":leg.get("limits",[]),
          "native_outer_off":leg.get("telemetry",{}).get("outer_repair_native_verified"),
          "original_go_rx_handoff":leg.get("telemetry",{}).get("go_receive_handoff"),
          "original_go_cold_stages":{role:stages(root/"oneway"/(role+"-product-markers.log"),role) for role in ("client","server")},
          "source_tun_drops":leg.get("source_tun_tx_drops_steady"),
          "max_zero_delivery_ms":leg.get("active_zero_delivery_ms"),
          "native_owned_stop":leg.get("telemetry",{}).get("stop_drained_both"),
          "native_cleanup":leg.get("cleanup",{}).get("owned_namespaces_absent"),
          "actual_blackhole_tc_drops":{},"recovery":{}}
    valid=(leg.get("result")=="PASS_SCOPED_OBSERVATION" and not leg.get("failures")
       and data["native_outer_off"] is True
       and data["native_owned_stop"] is True and data["native_cleanup"] is True)
    for role in ("client","server"):
        data["actual_blackhole_tc_drops"][role]=sum(int(v.get("drops") or 0) for x in leg.get("network_accounting",[])
            if x.get("phase")=="c2s_blackhole105" and x.get("role")==role
            for v in x.get("netem",[]))
    if data["actual_blackhole_tc_drops"]["client"]<=0:valid=False
    for direction in ("c2s","s2c"):
        rows=[x for x in leg.get("observed",[]) if x.get("phase")=="recovery120"
              and x.get("direction")==direction and x.get("protocol")=="udp"]
        offered=sum(float(v.get("injected_app_mbps") or 0) for v in rows)
        first=sum(float(v.get("cohort_delivered_app_mbps") or 0) for v in rows)
        data["recovery"][direction]={"offered_mbps":offered,"first_mbps":first,
            "first_fraction":first/offered if offered else None,
            "missing_after_drain":sum(int(v.get("missing_after_drain") or 0) for v in rows),
            "delivered_only_p99_ms":next((v.get("first_arrival_ms",{}).get("p99_ms") for v in rows),None)}
        if offered<1.9 or first<offered*.99:valid=False
    data["verdict"]="PASS_SCOPED_UNILATERAL_HEALTH_REJOIN_LOW_RATE" if valid else "FAIL_OR_INCONCLUSIVE_UNILATERAL_REJOIN"
    data["limitations"]=["Unilateral Health dead does not imply both ends must reconnect; exact native stage evidence is preserved without forcing equal generations","2Mbps source diagnostic is not 10Mbps recovery acceptance, native Stop and true source TUN drops remain authoritative","Window only 120s after restored, no physical Windows source"]
    (root/"result.json").write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print("PLAN027_UNILATERAL_COLD105",data["verdict"],flush=True)
    if not valid:raise SystemExit(2)

if __name__=="__main__":main()
