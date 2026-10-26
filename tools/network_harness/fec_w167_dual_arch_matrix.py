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
import time
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

def _config(name,mode,game_fec,profile,loss,source,run_id,arch,traffic_mbps=10):
    # Validator's mandatory frozen artifact locator is replaced BEFORE it
    # reaches the product runner, which consumes a locally built native bundle.
    # Run-id placeholder never appears in saved/requested artifact provenance.
    tmp={
        "version":1,"id":f"W168_{arch}_{name}_{traffic_mbps}Mbps_{loss}IID",
        "owner":"fec-network-work","seed":168000+loss,
        "policy":"outer-opportunistic-v3",
        "product":{"mode":mode,"fec_profile":profile,"game_fec":game_fec,
                   "repair_enabled":True},
        "traffic":{"c2s_mbps":traffic_mbps,"s2c_mbps":traffic_mbps,"udp_share":1.0,
                   "sizes":[[64,6],[128,8],[255,6],[512,10],[900,20],[1200,50]],
                   "tcp_flows":2,"probe_hz":20,"deadline_ms":6000,
                   "burst_ms":0,"max_packets":5000000,
                   "observe_size_classes":True,
                   "observe_independent_flows":False,
                   "allow_fragmentation":False},
        "network":{"outer_mtu":1500,"lane_loss":"shared",
                   "queue_packets":32768,"netem_rng":"unseeded_recorded",
                   "owned_veth_static_neighbour":True,"v3_timeline":True},
        "warmup_s":2,"drain_s":4,
        "phases":[{"name":"iid","seconds":20,
                   "c2s":{"delay_ms":75,"loss_pct":loss,"rate_mbps":0},
                   "s2c":{"delay_ms":75,"loss_pct":loss,"rate_mbps":0}}],
        "acceptance":{"injection_tolerance_pct":10,
                      "require_retransmission":False,
                      "require_zero_source_tun_drops_full_run":False,
                      "cross_business_hol":False},
        "bundles":{"A":{"source":source,"run_id":run_id,"attempt":1,
                        "artifact_id":run_id,"sha256":"0"*64,
                        "recovery_policy":"outer-opportunistic-v3"}},
        "order":"A"
    }
    if traffic_mbps==250:
        # Same actual original Go TLS Rust FEC6 product, no outer rate limit.
        # Pure near-MTU 1200B avoids inventing extra high-PPS small-packet load.
        tmp["traffic"]["sizes"]=[[1200,100]]
        tmp["traffic"]["observe_size_classes"]=False
        tmp["traffic"]["max_packets"]=5000000
    cfg=validate(tmp)
    cfg["bundles"]["A"]={"source":source,"recovery_policy":"outer-opportunistic-v3"}
    return cfg

def timeline_cpu(path, measurement_window_monotonic=None):
    """Native Rust M4 worker thread CPU, aligned to iid 20s window when possible."""
    if not path.exists():return {"status":"NOT_OBSERVED"}
    rows=[]
    for line in path.read_text().splitlines():
        if "V4_PUBLIC_TIMELINE " not in line:continue
        nums=dict((k,int(v)) for k,v in re.findall(r"([a-z_]+)=([0-9]+)",line))
        if "rust_rx_cpu_ns" in nums and "rust_tx_cpu_ns" in nums:rows.append(nums)
    if len(rows)<2:return {"status":"NOT_OBSERVED"}
    whole_rx=rows[-1]["rust_rx_cpu_ns"]-rows[0]["rust_rx_cpu_ns"]
    whole_tx=rows[-1]["rust_tx_cpu_ns"]-rows[0]["rust_tx_cpu_ns"]
    if min(whole_rx,whole_tx)<0:return {"status":"INVALID_COUNTER_RESET"}
    out={"status":"RUST_NATIVE_RX_TX_THREADS_ONLY_WHOLE_TIMELINE",
         "rust_rx_cpu_s":whole_rx/1e9,
         "rust_tx_cpu_s":whole_tx/1e9,
         "rust_rx_tx_sum_cpu_s":(whole_rx+whole_tx)/1e9,
         "measurement_window_status":"NOT_OBSERVED",
         "note":"Worker thread clocks not all Rust code. Sampling window and Go process threads differ; memory not attributable by language."}
    if measurement_window_monotonic:
        # Go emits realtime unix_ns, harness kernel snapshots emit monotonic ns.
        # Pair using current realtime-monotonic offset on the same VM.
        offset=time.time_ns()-time.monotonic_ns()
        start,end=(x+offset for x in measurement_window_monotonic)
        timed=[row for row in rows if row.get("unix_ns") is not None]
        if len(timed)>=2:
            a=min(timed,key=lambda row:abs(row["unix_ns"]-start))
            b=min(timed,key=lambda row:abs(row["unix_ns"]-end))
            if (a["unix_ns"]<b["unix_ns"] and
                max(abs(a["unix_ns"]-start),abs(b["unix_ns"]-end))<=800_000_000):
                rx=b["rust_rx_cpu_ns"]-a["rust_rx_cpu_ns"]
                tx=b["rust_tx_cpu_ns"]-a["rust_tx_cpu_ns"]
                if min(rx,tx)>=0:
                    out["measurement_window_status"]="ALIGNED_WITHIN_800MS_EACH_BOUNDARY"
                    out["measurement_rust_rx_cpu_s"]=rx/1e9
                    out["measurement_rust_tx_cpu_s"]=tx/1e9
                    out["measurement_rust_sum_cpu_s"]=(rx+tx)/1e9
                    out["boundary_offset_start_ms"]=(a["unix_ns"]-start)/1e6
                    out["boundary_offset_end_ms"]=(b["unix_ns"]-end)/1e6
    return out

def iid_window(case_dir):
    p=case_dir/"network-snapshots.json"
    try:
        rows=json.loads(p.read_text())
        begin=next(x["ns"] for x in rows if x["name"]=="before-iid")
        end=next(x["ns"] for x in rows if x["name"]=="measurement-end")
        return (begin,end) if end>begin else None
    except (OSError,KeyError,ValueError,StopIteration,TypeError):
        return None

def outer_link_tx_bytes(case_dir,role):
    """Whole warmup+measurement+drain veth TX, not only product DATA."""
    p=case_dir/"network-snapshots.json"
    try:
        snapshots=json.loads(p.read_text())
        start=next(x for x in snapshots if x["name"]=="warmup-start")
        end=next(x for x in snapshots if x["name"]=="drain-end")
        dev={"client":"wbnc0","server":"wbns0"}[role]
        def tx(s):
            item=next(v for v in s["network"][role]["links"] if v["ifname"]==dev)
            return int(item.get("stats64",item.get("stats",{}))["tx"]["bytes"])
        delta=tx(end)-tx(start)
        return delta if delta>0 else None
    except (OSError,ValueError,TypeError,KeyError,StopIteration):
        return None


def analyze(case_dir,leg):
    t=leg.get("telemetry",{})
    per={}
    measurement_window=iid_window(case_dir)
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
                       "outer_veth_tx_bytes_all_classes":outer_link_tx_bytes(case_dir,role),
                       # The retry ledger is pre-netem; veth TX is after
                       # actual random losses. Ratios mix different stages.
                       "repair_over_full_veth_tx_pct_approx":None,
                       "outer_link_fraction_note":"NOT_COMPARABLE_PRE_NETEM_REPAIR_VS_POST_NETEM_VETH; preserve raw counters without fabricating a whole-outer percentage. Native DATA-only share remains measured.",
                       "repair_definitely_sent_pct":
                           100*good/(first+good+uncertain),
                       "note":"Product outer DATA ledger, includes warmup+measurement+drain; not entire veth link incl parity, ACK, TLS control and retransmitted L2."}
            else:ratio={"status":"NOT_OBSERVED"}
        per[role]={
            "outer_repair_policy_readback":t.get("outer_repair_native_verified"),
            "outer_retransmission_fraction":ratio,
            "process_measurement_cpu_s":leg.get("measurement_cost",{}).get(role,{}).get("cpu_s"),
            "process_peak_rss_bytes":leg.get("host",{}).get("processes",{}).get(role,{}).get("rss_peak_bytes"),
            "rust_thread_cpu":timeline_cpu(case_dir/f"{role}-v3-timeline.log",measurement_window),
        }
    for role in ("client","server"):
        cost=per[role]
        proc=cost.get("process_measurement_cpu_s")
        seconds=leg.get("measurement_seconds")
        rust=cost.get("rust_thread_cpu",{})
        if type(proc) in (int,float) and type(seconds) in (int,float) and seconds>0 and proc>=0:
            cost["process_cpu_pct_one_core"]=100*proc/seconds
        else:
            cost["process_cpu_pct_one_core"]=None
        worker=rust.get("measurement_rust_sum_cpu_s")
        if (type(proc) in (int,float) and proc>0 and
            type(worker) in (int,float) and worker>=0):
            cost["rust_native_rx_tx_share_of_process_cpu_pct_approx"]=100*worker/proc
            cost["non_rx_tx_worker_cpu_pct_approx"]=100*(proc-worker)/proc
            cost["cpu_split_note"]="Approx sampled native worker RX/TX thread time divided by whole Go+Rust process CPU, aligned within <=800ms per endpoint; remaining includes Go, Rust on other threads, scheduler/FFI; not exact Go-vs-Rust split."
        else:
            cost["rust_native_rx_tx_share_of_process_cpu_pct_approx"]=None
            cost["non_rx_tx_worker_cpu_pct_approx"]=None
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
    ap.add_argument("--case",choices=[row[0] for row in MODES])
    ap.add_argument("--loss",type=int,choices=LOSSES)
    ap.add_argument("--traffic-mbps",type=int,choices=(10,250),default=10)
    args=ap.parse_args()
    if (args.case is None)!=(args.loss is None):
        ap.error("--case and --loss must be used together")
    if args.traffic_mbps==250 and (args.case!="normal_maximum6" or args.loss!=30):
        ap.error("250Mbps is only an isolated Normal fixed Maximum6 IID30 20s case")
    expected_count=1 if args.case is not None else len(MODES)*len(LOSSES)
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
            if args.case is not None and (label!=args.case or loss!=args.loss):
                continue
            cfg=_config(label,mode,gfec,profile,loss,src,run_id,args.arch,traffic_mbps=args.traffic_mbps)
            name=cfg["id"]
            leg=LinuxExperiment(cfg,out/"bundle-A",out/name,"A").run()
            result=analyze(out/name,leg)
            result.update(id=name,mode=mode,game_fec=gfec,requested_loss_pct=loss,
                          requested_business_mbps_per_direction=args.traffic_mbps,
                          source_sha=src,architecture=actual,
                          original_go_client_sha256=hashes["wbd-v4-client"],
                          original_go_server_sha256=hashes["wbd-v4-server"],
                          native_rust_shared_sha256=hashes["libwbd_engine.so"])
            results.append(result)
            (out/"progress.json").write_text(json.dumps({
                "source":src,"architecture":actual,"completed":len(results),
                "total_10mbps_cases":expected_count,
                "cases":results},indent=2)+"\n")
            print("FEC_W167_CASE",json.dumps({k:result[k] for k in
                  ("id","case_result","architecture","requested_loss_pct")}),flush=True)
            # W168 user explicitly disables performance ceiling auto-stop.
            # PSI, steal, RSS and delivery still recorded as evidence.
            # Any damaged product/namespace cleanup remains a real case FAIL.
    # Scoped W168 user override: 10Mbps no auto-stop and a separate isolated
    # 250Mbps high-FEC case is permitted; old owner capacity_stop unchanged.
    gate=json.loads(Path("docs/evidence/fec-network-work/status.json").read_text())
    high={"requested_rate_mbps_per_direction":250,"random_loss_pct":30,
          "fec_mode":"fec-fixed","fec_profile":6,"seconds":20,
          "result":"THIS_JOB_250MBPS_CASE_RECORDED" if args.traffic_mbps==250 else "SEPARATE_ISOLATED_JOB_NOT_THIS_CASE",
          "historical_capacity_stop":gate["capacity_stop"],
          "reason":"W168 user expressly overrides performance-triggered stopping for separately isolated 250Mbps case; historical capacity_stop preserved; real product failure still red."}
    (out/"highrate-250M-status.json").write_text(json.dumps(high,indent=2)+"\n")
    complete={"schema":"FEC_W167_ARCH_MATRIX_V1","source":src,"architecture":actual,
              "binary_hashes":hashes,"cases_completed":len(results),
              "cases_expected":expected_count,
              "high_rate":high,
              "overall_qualification":"MIXED_INDIVIDUAL_REAL_SCENARIOS_ONLY_NO_AGGREGATE_GREEN"}
    (out/"summary.json").write_text(json.dumps(complete,indent=2)+"\n")
    # An observed failing scenario is evidence and should not suppress the
    # next low-load case. Fail workflow if any selected case didn't execute.
    if len(results)!=expected_count:
        raise SystemExit("CAPACITY_STOP_OR_INCOMPLETE_MATRIX; see progress.json")

if __name__=="__main__":
    main()
