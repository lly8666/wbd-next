#!/usr/bin/env python3
"""One-VM OLD then NEW paired receipt, strict source/measurement qualification.
Never assert a percent efficiency win across unlike complete paths."""
import hashlib,json,math,os,pathlib,sys
root=pathlib.Path(sys.argv[1])
old=root/"old"; new=root/"new"
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=load(root/"build-manifest.json")
config=load(root/"legacy-patch.json")
new_p=new/"normal-off-dev-10mbps.json"
new_r=load(new_p) if new_p.exists() else None
old_biz=load(old/"biz.json") if (old/"biz.json").exists() else None
old_tgt=load(old/"target.json") if (old/"target.json").exists() else None
start=int((old/"start-monotonic-ns.txt").read_text()) if (old/"start-monotonic-ns.txt").exists() else None
old_resources=old/"resources.jsonl"
ticks=os.sysconf("SC_CLK_TCK")
def cpu_rows():
    if not old_resources.exists() or start is None:return {"result":"NOT_RUN"}
    rows=[]
    for line in old_resources.open():
        try:rows.append(json.loads(line))
        except json.JSONDecodeError:continue
    if not rows:return {"result":"UNAVAILABLE"}
    begin=start+10_000_000_000;end=start+70_000_000_000
    output={"result":"MEASURED","samples":len(rows),"components":{}}
    for key in ("client","server"):
        valid=[row for row in rows if row.get("processes",{}).get(key,{}).get("present") and row.get("processes",{}).get(key,{}).get("stat")]
        def closest(ns):
            return min(valid,key=lambda row:abs(row["monotonic_ns"]-ns)) if valid else None
        a,b=closest(begin),closest(end)
        if not a or not b:
            output["components"][key]={"result":"UNAVAILABLE"};continue
        x=a["processes"][key]["stat"];y=b["processes"][key]["stat"]
        ut=(y["utime_ticks"]-x["utime_ticks"])/ticks
        st=(y["stime_ticks"]-x["stime_ticks"])/ticks
        rss=max((row["processes"][key]["stat"]["rss_pages"]*os.sysconf("SC_PAGE_SIZE") for row in valid if begin<=row["monotonic_ns"]<=end),default=0)
        output["components"][key]={"user_cpu_s":ut,"system_cpu_s":st,
          "total_cpu_s":ut+st,"peak_rss_bytes_sampled":rss,
          "start_monotonic_ns":a["monotonic_ns"],"end_monotonic_ns":b["monotonic_ns"],
          "sampled_clock_delta_seconds":(b["monotonic_ns"]-a["monotonic_ns"])/1e9}
    return output
def app_stats(sender,receiver):
    if not sender or not receiver:return {"result":"NOT_RUN"}
    st,rv=sender["stats"],receiver["stats"]
    offered=sum(st.get("sent_bytes_by_second",[])[10:70])
    arrived=sum(rv.get("recv_bytes_by_second",[])[10:70])
    return {"offered_udp_payload_bytes":offered,"delivered_udp_payload_bytes":arrived,
      "offered_udp_payload_mbps":offered*8/60e6,
      "delivered_udp_payload_mbps":arrived*8/60e6,
      "offered_packets":sum(st.get("sent_packets_by_second",[])[10:70]),
      "delivered_unique_packets":sum(rv.get("recv_packets_by_second",[])[10:70]),
      "missing_or_not_delivered":max(0,sum(st.get("sent_packets_by_second",[])[10:70])-sum(rv.get("recv_packets_by_second",[])[10:70]))}
old_cpu=cpu_rows()
older={"source_sha":manifest["legacy_source_sha"],
 "topology":"5_network_namespace_full_Go_product_veth_TPROXY_raw_TUN",
 "duration_s":70,"measured_s":60,"warmup_s":10,
 "normal_lane_count":1,"fec_off":True,
 "c2s":app_stats(old_biz,old_tgt),
 "s2c":app_stats(old_tgt,old_biz),
 "product_process_cpu":old_cpu,
 "generator_cpu_total_seconds":(old_biz or {}).get("generator_process_cpu_seconds"),
 "actual_harness_patch_sha256":config["old_harness_sha256"],
 "result":"MEASUREMENT_RECORDED" if old_biz and old_tgt and old_cpu.get("result")=="MEASURED" else "INCOMPLETE"}
newer={"source_sha":manifest["new_source_sha"],
 "result":new_r.get("result") if new_r else "NOT_RUN",
 "topology":"1_network_namespace_dev_Go_TLS_private_original_Rust_owner_real_raw_TUN",
 "warmup_s":10,"measured_s":60,
 "c2s":new_r.get("c2s") if new_r else None,
 "s2c":new_r.get("s2c") if new_r else None,
 "rust_rx_thread_cpu_seconds":new_r.get("original_rust_worker_rx_cpu_seconds") if new_r else None,
 "rust_tx_thread_cpu_seconds":new_r.get("original_rust_worker_tx_cpu_seconds") if new_r else None,
 "combined_new_process_cpu_seconds":(new_r["combined_process_user_cpu_seconds"]+new_r["combined_process_system_cpu_seconds"]) if new_r else None,
 "source_receipt_hash":sha(new_p) if new_r else None}
metadata=load(root/"runtime.json")
source_ok=new_r is not None and new_r.get("source_sha")==manifest["new_source_sha"] and new_r.get("run_id")==os.environ["GITHUB_RUN_ID"]
order=metadata["order"]
same_job=metadata["old_job_id"]==metadata["new_job_id"]==os.environ["GITHUB_JOB"]
sequential=metadata["old_end_monotonic_ns"]<=metadata["new_start_monotonic_ns"]
identity=metadata["old_runner"]==metadata["new_runner"]
status=("PAIRED_DIAGNOSTIC_ONLY_NOT_CAUSAL" if all((source_ok,same_job,sequential,identity,older["result"]=="MEASUREMENT_RECORDED")) and newer["result"] not in (None,"NOT_RUN","INVALID_MEASUREMENT") else "INCONCLUSIVE")
report={
"schema":1,"source_sha":manifest["new_source_sha"],
"task":"M0_023_OLD_GO_VS_NEW_RUST_SAME_VM_SEQUENTIAL",
"result":status,
"requested_mode":"paired_ab",
"order":order,"run_id":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],
"job_key":os.environ["GITHUB_JOB"],"same_job_verified":same_job,
"runner_identity_verified":identity,"nonoverlap_verified":sequential,"exact_sources_verified":source_ok,
"same_source_build_manifest_sha256":sha(root/"build-manifest.json"),
"legacy":older,"new":newer,"runner":metadata,
"rate_definition":"10Mbps/dir UDP application payload with equal 64/256/1200B count mix, no deliberate loss/delay, 10s warmup 60s measurement",
"causal_cost_improvement_percent":"NOT_QUALIFIED",
"confounders":["Old legacy product is full external TLS and separate five veth/TPROXY/real TUN namespaces; new is dev private test-fixture Go TLS in one netns loopback real raw/TUN. Different network topology and product functionality.","Old legacy generator independently owns both application processes while new go test goroutines run in same process as Rust CDylib. Separate process CPU is only available for old; Rust worker CLOCK_THREAD_CPUTIME_ID for new; residual includes Go/injector/runtime/kernel.","Legacy generator has WBDQ CRC per UDP payload; new app verifies a different payload schema. Memory allocations and CPU/perf do not isolate algorithm translation.","70s old script derived from pinned product source with test-harness-only anchored modifications. Runtime binaries unmodified pinned source. No product qualification on either side.","No RTT p99 parity, veth parity, full queue age or private key upload."],
"next_action":"Use matched full veth client/server paths and separated sender/receiver/injector CPU clocks for a fair paired qualification; retain original Rust bridge capability disabled until B01-B04."}
(root/"paired-summary.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"result":status,"old":older,"new":newer,"same_job":same_job,"sequential":sequential},indent=2))
