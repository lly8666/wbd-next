"""PLAN027: bounded numeric original Rust worker CPU on same-VM R100 OFF/ON.
Only parse already-sanitized native Stop worker counters; no raw TLS logs,
new per-record sampling, OS addresses, packet data or guessed language split.
"""
import argparse
import json
import re
from pathlib import Path

PATTERN=re.compile(
    r"V4_PUBLIC_WORKER_CPU role=(client|server) rx_thread_cpu_ns=(\d+) tx_thread_cpu_ns=(\d+)"
)

def read_worker(log,role):
    matches=[m for m in PATTERN.finditer(log) if m.group(1)==role]
    if len(matches)!=1:
        return {"status":"NOT_OBSERVED","sample_count":len(matches)}
    m=matches[0]
    rx=int(m.group(2))/1e9
    tx=int(m.group(3))/1e9
    return {"status":"OBSERVED_ORIGINAL_NATIVE_STOP","rx_thread_cpu_s_full_owner":rx,
            "tx_thread_cpu_s_full_owner":tx,"tracked_rust_rx_tx_cpu_s":rx+tx}

def parse(root):
    output={"metric":"original Rust RX/TX worker thread CPU as one native Stop snapshot",
            "product_source_sha":None,"fixture_source_sha":None,
            "window_note":"Rust Stop counts full native owner lifetime; compare to whole-process full observation, NOT steady-only 60s CPU. Difference may include startup/Stop untracked threads and sampling mismatch.",
            "legs":{},"delta":{"client":{},"server":{}},"status":"NOT_RUN"}
    main=json.loads((root/"result.json").read_text())
    assert main["verdict"]=="PASS_SCOPED_ORIGINAL_NORMAL100_SAME_VM_OFF_ON_COST_NOT_OPTIMIZATION"
    assert main["one_vm_sequential_order"]==["OFF","ON"]
    output["product_source_sha"]=main["product_source_sha"]
    output["fixture_source_sha"]=main["fixture_sha"]
    ok=True
    for leg in ("off","on"):
        native=json.loads((root/("leg-"+leg)/"result.json").read_text())
        assert native["result"]=="PASS_SCOPED_OBSERVATION"
        role_data={}
        for role in ("client","server"):
            worker=read_worker((root/("leg-"+leg)/(role+"-product-markers.log")).read_text(),role)
            whole=native["host"]["processes"][role]["cpu_s_observed_including_warmup_setup_drain"]
            worker["whole_process_cpu_s_full_observation"]=whole
            worker["steady_process_cpu_s_60"]=native["measurement_cost"][role]["cpu_s"]
            if worker["status"]!="OBSERVED_ORIGINAL_NATIVE_STOP":ok=False
            role_data[role]=worker
        output["legs"][leg.upper()]=role_data
    if ok:
        for role in ("client","server"):
            a=output["legs"]["OFF"][role]
            b=output["legs"]["ON"][role]
            output["delta"][role]={
                "full_process_ON_minus_OFF_s":b["whole_process_cpu_s_full_observation"]-a["whole_process_cpu_s_full_observation"],
                "tracked_rust_rx_ON_minus_OFF_s":b["rx_thread_cpu_s_full_owner"]-a["rx_thread_cpu_s_full_owner"],
                "tracked_rust_tx_ON_minus_OFF_s":b["tx_thread_cpu_s_full_owner"]-a["tx_thread_cpu_s_full_owner"],
                "tracked_rust_rx_tx_ON_minus_OFF_s":b["tracked_rust_rx_tx_cpu_s"]-a["tracked_rust_rx_tx_cpu_s"],
                "steady_process_ON_minus_OFF_s":b["steady_process_cpu_s_60"]-a["steady_process_cpu_s_60"],
                "untracked_languages":"UNKNOWN: whole-minus-two-Rust-workers cannot be labeled Go alone"
            }
    output["status"]="PASS_SCOPED_NUMERIC_RUST_WORKER_COST_ATTRIBUTION" if ok else "INCONCLUSIVE_MISSING_OR_REPEATED_NATIVE_WORKER_MARKER"
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    root=Path(a.root)
    out=parse(root)
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    # Numeric-only result; never expose raw Go TLS/product logs.
    print("PLAN027_R100_WORKER_ATTRIBUTION",json.dumps(out,sort_keys=True),flush=True)
    if out["status"]!="PASS_SCOPED_NUMERIC_RUST_WORKER_COST_ATTRIBUTION":
        raise SystemExit(2)

if __name__=="__main__":main()
