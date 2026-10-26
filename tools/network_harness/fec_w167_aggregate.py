"""Strict evidence-only W168 56-case rollup. Missing results stay NOT_RUN."""
import argparse
import csv
import json
from pathlib import Path

ARCH=("arm64","amd64")
VARIANTS=("normal_off","normal_maximum6","normal_auto",
          "game2_off","game2_fixed6","game4_off","game4_fixed6")
LOSSES=(1,5,15,30)

def read_case(directory):
    p=directory/"progress.json"
    if not p.is_file():
        return {"result":"NOT_RUN_OR_ARTIFACT_MISSING","reason":"missing progress.json"}
    try:
        x=json.loads(p.read_text())
        if x.get("completed")!=1 or len(x.get("cases",[]))!=1:
            return {"result":"INVALID_OR_INCOMPLETE","reason":"not exactly one completed case"}
        row=x["cases"][0]
        out={"result":row.get("case_result","NOT_OBSERVED"),
             "pressure_peak_pct":row.get("host_pressure_peak"),
             "steal_peak_pct":row.get("host_steal_peak"),
             "architecture":row.get("architecture"),
             "source_sha":row.get("source_sha"),
             "host_limits":row.get("limits",[]),
             "failures":row.get("failures",[])}
        for role in ("client","server"):
            a=row.get("cpu_memory_outer",{}).get(role,{})
            out[role+"_cpu_s_20s"]=a.get("process_measurement_cpu_s")
            out[role+"_cpu_util_one_core_pct"]=a.get("process_cpu_pct_one_core")
            out[role+"_rust_rx_tx_share_pct_approx"]=a.get("rust_native_rx_tx_share_of_process_cpu_pct_approx")
            out[role+"_other_cpu_share_pct_approx"]=a.get("non_rx_tx_worker_cpu_pct_approx")
            rss=a.get("process_peak_rss_bytes")
            out[role+"_rss_peak_mib"]=round(rss/1048576,3) if isinstance(rss,int) else None
            rust=a.get("rust_thread_cpu",{})
            native=rust.get("rust_rx_tx_sum_cpu_s") if isinstance(rust,dict) else None
            out[role+"_rust_rx_tx_cpu_s_full_run"]=native
            out[role+"_rust_rx_tx_cpu_s_20s"]=rust.get("measurement_rust_sum_cpu_s") if isinstance(rust,dict) else None
            out[role+"_rust_cpu_window_status"]=rust.get("measurement_window_status") if isinstance(rust,dict) else None
            o=a.get("outer_retransmission_fraction",{})
            out[role+"_native_outer_repair_on_verified"]=a.get("outer_repair_policy_readback")
            out[role+"_repair_of_data_pct"]=o.get("repair_over_first_plus_repair_pct")
            # Suppress old artifact numerical ratios; numerator pre-netem,
            # veth TX denominator post-netem. Never mix counter stages.
            out[role+"_repair_of_all_outer_veth_pct_approx"]=None
            out[role+"_full_outer_fraction_status"]="NOT_COMPARABLE_COUNTER_BOUNDARY" if o.get("status","").startswith("OBSERVED_") else "NOT_OBSERVED"
            out[role+"_outer_metric_status"]=o.get("status")
        for direction in ("c2s","s2c"):
            for proto in ("udp","tcp"):
                vals=[x for x in row.get("actual",[])
                      if x.get("direction")==direction and x.get("protocol")==proto]
                if len(vals)==1:
                    q=vals[0];key=direction+"_"+proto
                    out[key+"_loss_pct"]=q.get("loss_pct")
                    out[key+"_missing"]=q.get("missing_after_drain")
                    out[key+"_sent"]=q.get("sent")
                    out[key+"_delivered"]=q.get("delivered")
                    out[key+"_arrival_app_mbps"]=q.get("cohort_delivered_app_mbps")
        return out
    except (OSError,ValueError,TypeError,KeyError) as e:
        return {"result":"INVALID_ARTIFACT","reason":str(type(e).__name__)}

def aggregate(root):
    cases=[]
    for arch in ARCH:
        for variant in VARIANTS:
            for loss in LOSSES:
                entry={"arch":arch,"variant":variant,"loss_pct":loss,
                       "requested_business_mbps_each_dir":10,"measurement_seconds":20}
                path=root/("w168-result-"+arch+"-"+variant+"-IID"+str(loss))
                entry.update(read_case(path))
                cases.append(entry)
    present=sum(row.get("result") not in
                ("NOT_RUN_OR_ARTIFACT_MISSING","INVALID_ARTIFACT","INVALID_OR_INCOMPLETE")
                for row in cases)
    statuses={}
    for row in cases:
        k=row.get("result")
        statuses[k]=statuses.get(k,0)+1
    high={}
    for arch in ARCH:
        x=read_case(root/("w168-high-"+arch))
        high[arch]=x
    return {
        "schema":"FEC_W168_56_NATIVE_CASES_AGGREGATE_V2",
        "requested_cases":56,"cases_with_artifact":present,
        "status_counts":statuses,
        "overall":"COMPLETE_CASE_COVERAGE_NOT_ALL_PASS" if present==56
                  else "INCOMPLETE_OBSERVATION_NOT_QUALIFIED",
        "250mbps_fixed6_iid30_20s_by_arch":high,
        "cpu_caveat":"Go+Rust share process. Rust RX/TX native worker thread CPU is only partial attribution; RSS cannot be split into Go vs Rust.",
        "outer_caveat":"Normal DATA retry numerator is accepted+uncertain; approximate full veth TX denominator includes all classes and does not exactly align final native stop. Game copies and FEC parity NEVER counted as outer DATA retry.",
        "cases":cases}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    out=aggregate(args.root)
    (args.output/"summary.json").write_text(json.dumps(out,indent=2)+"\n")
    lines=["# W168 native ARM64 and x86_64 IID 20-second matrix","",
           "**Coverage: "+str(out["cases_with_artifact"])+"/56. Status: "+out["overall"]+"**","",
           "Independent 250Mbps/dir FEC6 IID30 UDP 20s by architecture: "+str({
               a:v.get("result") for a,v in out["250mbps_fixed6_iid30_20s_by_arch"].items()}),"",
           "|Arch|Mode|IID%|Result|C CPU%|S CPU%|C Rust RxTx share%|S Rust RxTx share%|C RSS MiB|S RSS MiB|Full outer DATA-repair fraction (C/S)%|",
           "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|"]
    for x in out["cases"]:
        def fmt(v):
            if v is None:return "NOT_OBSERVED"
            if isinstance(v,float):return f"{v:.3f}"
            return str(v)
        pair=fmt(x.get("client_repair_of_all_outer_veth_pct_approx"))+" / "+fmt(x.get("server_repair_of_all_outer_veth_pct_approx"))
        lines.append("|"+"|".join([
            x["arch"],x["variant"],str(x["loss_pct"]),x["result"],
            fmt(x.get("client_cpu_util_one_core_pct")),fmt(x.get("server_cpu_util_one_core_pct")),
            fmt(x.get("client_rust_rx_tx_share_pct_approx")),fmt(x.get("server_rust_rx_tx_share_pct_approx")),
            fmt(x.get("client_rss_peak_mib")),fmt(x.get("server_rss_peak_mib")),pair])+"|")
    lines.extend(["","**Important:** Full outer DATA retransmission ratio NOT_OBSERVED: native DATA repair is counted before netem, but veth TX excludes netem-dropped traffic. Do not divide these unlike counters. Native DATA retry / first+repair is valid. Product CPU and RSS cover Go+Rust process; rust native thread time alone does not prove complete language ownership. Game multi-lane replay traffic distinct from initial lane copies. Host CPU PSI >20% requires scoped caution.",""])
    (args.output/"summary.md").write_text("\n".join(lines))
    keys=sorted(set(k for x in out["cases"] for k in x if isinstance(x[k],(int,float,str,type(None)))))
    with (args.output/"summary.csv").open("w",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=keys,extrasaction="ignore")
        writer.writeheader()
        for x in out["cases"]:writer.writerow(x)
    print("W168_AGGREGATE",out["overall"],out["cases_with_artifact"],"/56")

if __name__=="__main__":
    main()
