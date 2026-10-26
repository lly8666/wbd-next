"""W167: same-job native original-Go/Rust real-TUN 20s IID loss matrix.

Runs ONLY the original product in unique owned namespaces, never mock traffic.
Architecture matched; intentionally not a CI overall success qualification.
250Mbps is a HARD STOP while FEC status.capacity_stop remains true.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
from pathlib import Path

from tools.network_harness.config import validate
from tools.network_harness.runner import LinuxExperiment

MODES=(
    ("normal_off", "normal", "off", 1),
    ("normal_maximum6", "fec-fixed", "off", 6),
    ("normal_auto", "fec-auto", "off", 1),
    ("game2_off", "game2", "off", 1),
    ("game2_fixed6", "game2", "fixed6", 1),
    ("game4_off", "game4", "off", 1),
    ("game4_fixed6", "game4", "fixed6", 1),
)
LOSSES=(1,5,15,30)

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as file:
        for piece in iter(lambda:file.read(1024*1024),b""):
            h.update(piece)
    return h.hexdigest()

def _config(name,mode,game_fec,profile,loss,source,run_id,arch):
    # Validator's mandatory frozen artifact locator is replaced BEFORE it
    # reaches the product runner, which consumes a locally built native bundle.
    # Run-id placeholder never appears in saved/requested artifact provenance.
    tmp={
        "version":1,"id":f"W167_{arch}_{name}_{loss}IID",
        "owner":"fec-network-work","seed":168000+loss,
        "policy":"outer-opportunistic-v3",
        "product":{"mode":mode,"fec_profile":profile,"game_fec":game_fec,
                   "repair_enabled":True},
        "traffic":{"c2s_mbps":10,"s2c_mbps":10,"udp_share":0.96,
                   "sizes":[[64,6],[128,8],[255,6],[512,10],[900,20],[1200,50]],
                   "tcp_flows":2,"probe_hz":20,"deadline_ms":6000,
                   "burst_ms":0,"max_packets":5000000,
                   "observe_size_classes":True,
                   "observe_independent_flows":True,
                   "allow_fragmentation":False},
        "network":{"outer_mtu":1500,"lane_loss":"shared",
                   "queue_packets":32768,"netem_rng":"unseeded_recorded",
                   "owned_veth_static_neighbour":True,"v3_timeline":True},
        "warmup_s":2,"drain_s":4,
        "phases":[{"name":"iid","seconds":20,
                   "c2s":{"delay_ms":75,"loss_pct":loss,"rate_mbps":100},
                   "s2c":{"delay_ms":75,"loss_pct":loss,"rate_mbps":100}}],
        "acceptance":{"injection_tolerance_pct":10,
                      "require_retransmission":False,
                      "require_zero_source_tun_drops_full_run":False,
                      "cross_business_hol":True},
        "bundles":{"A":{"source":source,"run_id":run_id,"attempt":1,
                        "artifact_id":run_id,"sha256":"0"*64,
                        "recovery_policy":"outer-opportunistic-v3"}},
        "order":"A"
    }
    cfg=validate(tmp)
    cfg["bundles"]["A"]={"source":source,"recovery_policy":"outer-opportunistic-v3"}
    return cfg

def timeline_cpu(path):
    if not path.exists():return {"status":"NOT_OBSERVED"}
    rows=[]
    for line in path.read_text().splitlines():
        if "V4_PUBLIC_TIMELINE " not in line:continue
        nums=dict((k,int(v)) for k,v in re.findall(r"([a-z_]+)=([0-9]+)",line))
        if "rust_rx_cpu_ns" in nums and "rust_tx_cpu_ns" in nums:rows.append(nums)
    if len(rows)<2:return {"status":"NOT_OBSERVED"}
    rx=rows[-1]["rust_rx_cpu_ns"]-rows[0]["rust_rx_cpu_ns"]
    tx=rows[-1]["rust_tx_cpu_ns"]-rows[0]["rust_tx_cpu_ns"]
    if min(rx,tx)<0:return {"status":"INVALID_COUNTER_RESET"}
    return {"status":"RUST_NATIVE_RX_TX_THREADS_ONLY_WHOLE_TIMELINE",
            "rust_rx_cpu_s":rx/1e9,"rust_tx_cpu_s":tx/1e9,
            "rust_rx_tx_sum_cpu_s":(rx+tx)/1e9,
            "note":"Not all Rust work; Go TLS and FFI may run on other threads. Process RSS cannot be language-separated."}

def analyze(case_dir,leg):
    t=leg.get("telemetry",{})
    per={}
    for role in ("client","server"):
        p=t.get("counters",{}).get(role,{})
        if leg.get("request_id","").find("game")!=-1:
            ratio={"status":"NOT_APPLICABLE_GAME_FIRST_LANE_COPIES_ARE_NOT_OUTER_RETRANSMISSION"}
        else:
            first=p.get("first_wire_bytes")
            good=p.get("repair_accepted_wire_bytes")
            uncertain=p.get("repair_uncertain_wire_bytes")
            if all(type(v) is int and v>=0 for v in (first,good,uncertain)) and first+good+uncertain>0:
                ratio={"status":"OBSERVED_NATIVE_PRODUCT_DATA_WIRE_ACCOUNTING_WHOLE_RUN",
                       "first_wire_bytes":first,"repair_accepted_wire_bytes":good,
                       "repair_uncertain_wire_bytes":uncertain,
                       "repair_over_first_plus_repair_pct":
                           100*(good+uncertain)/(first+good+uncertain),
                       "repair_definitely_sent_pct":
                           100*good/(first+good+uncertain),
                       "note":"Product outer DATA ledger, includes warmup+measurement+drain; not entire veth link incl parity, ACK, TLS control and retransmitted L2."}
            else:ratio={"status":"NOT_OBSERVED"}
        per[role]={
            "outer_repair_policy_readback":t.get("outer_repair_native_verified"),
            "outer_retransmission_fraction":ratio,
            "process_measurement_cpu_s":leg.get("measurement_cost",{}).get(role,{}).get("cpu_s"),
            "process_peak_rss_bytes":leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes"),
            "rust_thread_cpu":timeline_cpu(case_dir/"A"/f"{role}-v3-timeline.log"),
        }
    return {"case_result":leg.get("result"),"phase_seconds":leg.get("measurement_seconds"),
            "actual":leg.get("observed",[]),"cpu_memory_outer":per,
            "native_game_policy":t.get("game_outer_policy","NOT_APPLICABLE"),
            "host_pressure_peak":leg.get("host",{}).get("cpu_psi_some_peak"),
            "host_steal_peak":leg.get("host",{}).get("steal_pct_peak"),
            "limits":leg.get("limits",[]),"failures":leg.get("failures",[]),
            "qualification":"OBSERVED_WITHIN_ONE_ARCH_SCENARIO_ONLY; PROCESS_RSS_AND_CPU_NOT_SPLIT_GO_RUST"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bundle",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--arch",required=True,choices=("arm64","amd64"))
    args=ap.parse_args()
    src=os.environ["GITHUB_SHA"]
    actual=platform.machine()
    assert actual=={"arm64":"aarch64","amd64":"x86_64"}[args.arch],(args.arch,actual)
    bundle=Path(args.bundle).resolve()
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=True)
    assert all((bundle/n).is_file() for n in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so","manifest.json","SHA256SUMS"))
    manifest=json.loads((bundle/"manifest.json").read_text())
    assert manifest["source"]==src and manifest["architecture"]==actual
    hashes={n:sha(bundle/n) for n in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so")}
    # Existing original-product runner requires fixed-build under bundle-A.
    local=out/"bundle-A"/"fixed-build"
    local.mkdir(parents=True)
    for name in hashes:
        os.symlink(bundle/name,local/name)
    run_id=int(os.environ["GITHUB_RUN_ID"])
    results=[]
    for label,mode,gfec,profile in MODES:
        for loss in LOSSES:
            cfg=_config(label,mode,gfec,profile,loss,src,run_id,args.arch)
            name=cfg["id"]
            leg=LinuxExperiment(cfg,out/"bundle-A",out/name,"A").run()
            result=analyze(out/name,leg)
            result.update(id=name,mode=mode,game_fec=gfec,requested_loss_pct=loss,
                          source_sha=src,architecture=actual,
                          original_go_client_sha256=hashes["wbd-v4-client"],
                          original_go_server_sha256=hashes["wbd-v4-server"],
                          native_rust_shared_sha256=hashes["libwbd_engine.so"])
            results.append(result)
            (out/"progress.json").write_text(json.dumps({
                "source":src,"architecture":actual,"completed":len(results),
                "total_10mbps_cases":len(MODES)*len(LOSSES),
                "cases":results},indent=2)+"\n")
            print("FEC_W167_CASE",json.dumps({k:result[k] for k in
                  ("id","case_result","architecture","requested_loss_pct")}),flush=True)
            risk=result["host_pressure_peak"]
            # One real observable host contention/cleanup trigger stops the
            # remainder, not a false "pass". Continue regular 10Mbps cases
            # only while resources and namespace cleanup prove safe.
            if (leg.get("cleanup",{}).get("owned_namespaces_absent") is not True
                or (type(risk) in (int,float) and risk>20)
                or (type(result["host_steal_peak"]) in (int,float)
                    and result["host_steal_peak"]>5)):
                (out/"STOP_CAPACITY.txt").write_text(
                    "STOP: product namespace cleanup or current host CPU PSI/steal limit; subsequent cases NOT_RUN\n")
                print("FEC_W167_CAPACITY_STOP",name,flush=True)
                break
        if (out/"STOP_CAPACITY.txt").exists():break
    # This remains a historical hard stop. New user requested 250Mbps, but
    # FEC autonomous status explicitly forbids heavy runs until cleared.
    gate=json.loads(Path("docs/evidence/fec-network-work/status.json").read_text())
    high={"requested_rate_mbps_per_direction":250,"random_loss_pct":30,
          "fec_mode":"fec-fixed","fec_profile":6,"seconds":20,
          "result":"NOT_RUN_CAPACITY_STOP" if gate["capacity_stop"] else "NOT_RUN_NEEDS_SEPARATE_GUARDED_JOB",
          "reason":"Existing recorded CPU PSI capacity_stop and no real-time overload abort for 250Mbps. Never silently override or label a 10Mbps run as a 250Mbps test."}
    (out/"highrate-250M-status.json").write_text(json.dumps(high,indent=2)+"\n")
    complete={"schema":"FEC_W167_ARCH_MATRIX_V1","source":src,"architecture":actual,
              "binary_hashes":hashes,"cases_completed":len(results),
              "cases_expected":len(MODES)*len(LOSSES),
              "high_rate":high,
              "overall_qualification":"MIXED_INDIVIDUAL_REAL_SCENARIOS_ONLY_NO_AGGREGATE_GREEN"}
    (out/"summary.json").write_text(json.dumps(complete,indent=2)+"\n")
    # An observed failing scenario is evidence and should not suppress the
    # next low-load case. Fail workflow if any selected case didn't execute.
    if len(results)!=len(MODES)*len(LOSSES):
        raise SystemExit("CAPACITY_STOP_OR_INCOMPLETE_MATRIX; see progress.json")

if __name__=="__main__":
    main()
