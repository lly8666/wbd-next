#!/usr/bin/env python3
"""One real signed-driver Windows/WSL2 Normal/off A=>B job.

A: current-source retained Go steady packet pump, same Rust M1/M3 DLL.
B: Rust native Wintun/Npcap owner. Both original TLS/OS/WAL/Stop. No new builds
between legs and no cross-VM CPU comparison.
"""
import hashlib,json,os,pathlib,shutil,subprocess,sys

root=pathlib.Path.cwd()
out=root/"result"/"wl-public"
ab=out/"wl-ab-v2"
ab.mkdir(parents=True,exist_ok=True)
scenario_path=os.environ.get("WBD_WL_V2_SCENARIO","")
if os.environ.get("WBD_WL_PUBLIC_MODES")!="normal" or not scenario_path:
    raise SystemExit("WL_V2_AB_REQUIRES_SINGLE_NORMAL_AND_SCENARIO")
from m0_wl_perf_v2_config import read_scenario
scenario=read_scenario(root/scenario_path)
if (root/scenario_path).resolve().parent!=(root/"scenarios").resolve():
    raise SystemExit("WL_V2_AB_UNSAFE_SCENARIO")
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()
def window_cpu(path,start,end):
    if not path.exists():return {"status":"NOT_MEASURED_NO_PROCESS_SAMPLE"}
    good=[]
    for line in path.read_text(errors="replace").splitlines():
        try:
            r=json.loads(line)
            t=float(r["monotonic_s"])
            if start<=t<=end and r.get("scope")=="SAME_WINDOWS_PROCESS_GO_PLUS_RUST_NOT_SEPARATELY_ATTRIBUTED":
                good.append(r)
        except (ValueError,KeyError,TypeError):continue
    if len(good)<2:return {"status":"NOT_MEASURED_SHORT_WINDOWS_SAMPLE_WINDOW","samples":len(good)}
    a,b=good[0],good[-1]
    elapsed=b["monotonic_s"]-a["monotonic_s"]
    cpu=b["cpu_total_s"]-a["cpu_total_s"]
    if elapsed<=0 or cpu<0:return {"status":"NOT_MEASURED_INVALID_COUNTER"}
    return {"status":"MEASURED_WINDOW","samples":len(good),"window_sample_span_s":round(elapsed,3),
            "cpu_seconds":round(cpu,4),"cpu_kernel_s":round(b["cpu_kernel_s"]-a["cpu_kernel_s"],4),
            "cpu_user_s":round(b["cpu_user_s"]-a["cpu_user_s"],4),
            "avg_pct_one_core":round(100*cpu/elapsed,3),
            "peak_rss_bytes":max(x["working_set_bytes"] for x in good),
            "peak_private_bytes":max(x["private_bytes"] for x in good),
            "rust_named_tx_cpu_delta_s":round(sum(x.get("thread_cpu",{}).get("rust_tx_cpu_delta_s",0) for x in good),4),
            "rust_named_rx_cpu_delta_s":round(sum(x.get("thread_cpu",{}).get("rust_rx_cpu_delta_s",0) for x in good),4),
            "scope":"WHOLE_EXE_GO_PLUS_RUST_PLUS_OS_KERNEL"}
def collect(label,rc):
    folder=ab/("leg-"+label)
    folder.mkdir(exist_ok=True)
    for name in ("report.json","wl-n0-windows-app.json","wl-n0-linux-app.json",
                 "wl-n0-netem-before.json","wl-n0-netem-after.json",
                 "windows-original-go-rust-process-1hz.jsonl","wl-v2-scenario.json"):
        source=out/name
        if source.exists():shutil.copy2(source,folder/name)
    report=json.loads((folder/"report.json").read_text()) if (folder/"report.json").exists() else {}
    row={"leg":label,"variant":"go-steady" if label=="A" else "rust-native",
         "source_sha":os.environ.get("GITHUB_SHA"),"exit_code":rc,
         "stop":report.get("stop"),"mode_public":report.get("mode_public"),
         "v2":report.get("WL_V2",{}),"error":report.get("error")}
    for side in ("windows","linux"):
        p=folder/("wl-n0-"+side+"-app.json")
        if p.exists():row[side]=json.loads(p.read_text())
    p=folder/"wl-n0-windows-app.json"
    if p.exists():
        w=row["windows"]
        row["cpu"]=window_cpu(folder/"windows-original-go-rust-process-1hz.jsonl",
                            float(w["measurement_start_monotonic_s"]),
                            float(w["measurement_end_monotonic_s"]))
    else:row["cpu"]={"status":"NOT_MEASURED_NO_REAL_APP"}
    # Actual qdisc packet/drop deltas, not declared 0% loss or a guessed host loss.
    def tc_counts(file):
        if not file.is_file():return {}
        try:
            d=json.loads(file.read_text())
            result={}
            for direction,key in (("windows_to_linux","ifb"),("linux_to_windows","eth0")):
                found=[x for x in d.get(key,[]) if x.get("kind")=="netem"]
                if len(found)!=1:continue
                q=found[0]
                stats=q.get("stats",{})
                result[direction]={k:q.get(k,stats.get(k)) for k in ("packets","bytes","drops","overlimits","requeues")}
            return result
        except (OSError,ValueError,TypeError):return {}
    before=tc_counts(folder/"wl-n0-netem-before.json")
    after=tc_counts(folder/"wl-n0-netem-after.json")
    row["actual_kernel_tc_delta"]={}
    for direction in ("windows_to_linux","linux_to_windows"):
        b=before.get(direction);e=after.get(direction)
        row["actual_kernel_tc_delta"][direction]=(
            {k:e[k]-b[k] if isinstance(e.get(k),int) and isinstance(b.get(k),int) and e[k]>=b[k] else None
             for k in ("packets","bytes","drops","overlimits","requeues")}
            if b and e else {"status":"NOT_MEASURED"})
    row["source_identity"]={}
    paths={"windows_exe":out/"wbd-client-embedded.exe",
           "rust_dll":out/"wbd_engine.dll",
           "linux_peer":root/"linux-product"/"wbd-v4-server",
           "wintun":out/"wintun.dll","wpcap":out/"wpcap.dll","packet":out/"Packet.dll"}
    for k,path in paths.items():
        row["source_identity"][k]=sha(path) if path.exists() else "MISSING"
    (folder/"leg-summary.json").write_text(json.dumps(row,indent=2,sort_keys=True)+"\n")
    return row
legs=[]
for label in ("B","A"):
    for name in ("report.json","wl-n0-windows-app.json","wl-n0-linux-app.json",
                 "wl-n0-netem-before.json","wl-n0-netem-after.json",
                 "windows-original-go-rust-process-1hz.jsonl"):
        (out/name).unlink(missing_ok=True)
    env=os.environ.copy()
    env["WBD_WL_PERF_AB_GO_STEADY"]="1" if label=="A" else "0"
    env["WBD_WL_PUBLIC_MODE"]="normal"
    print("WL_V2_AB_LEG_START "+label,flush=True)
    rc=subprocess.run([sys.executable,"tools/m0_wl_public_normal_e2e.py"],env=env).returncode
    row=collect(label,rc)
    legs.append(row)
    print("WL_V2_AB_LEG_END "+label+" rc="+str(rc)+" stop="+str(row["stop"]),flush=True)
    # Refuse any next leg without fully proven Stop; B-first protects Rust
    # evidence when the retained Go steady baseline crashes under pressure.
    if row["stop"]!="PASS_BOTH_OWNED":break

issues=[]
if len(legs)!=2:issues.append("both legs did not complete owned Stop")
for leg in legs:
    if leg["exit_code"]!=0 or leg["stop"]!="PASS_BOTH_OWNED":issues.append(leg["leg"]+" product/Stop failure")
    if leg["v2"].get("status")!="MEASURED_BOTH_OS_KERNEL":issues.append(leg["leg"]+" scenario "+str(leg["v2"].get("status")))
    if leg["v2"].get("scenario_sha256")!=scenario["scenario_sha256"]:issues.append(leg["leg"]+" scenario mismatch")
    if leg["cpu"].get("status")!="MEASURED_WINDOW":issues.append(leg["leg"]+" process CPU window incomplete")
    if leg["source_identity"].get("wintun")=="MISSING" or leg["source_identity"].get("rust_dll")=="MISSING":
        issues.append(leg["leg"]+" binary/driver identity incomplete")
if len(legs)==2:
    if legs[0]["source_identity"]!=legs[1]["source_identity"]:
        issues.append("reused exe/dll/linux peer/driver SHA differs between legs")
def metrics(leg):
    if "windows" not in leg or "linux" not in leg:return {"status":"NOT_MEASURED"}
    w,l=leg["windows"],leg["linux"]
    delivered=float(w["received_payload_mbps"])+float(l["received_payload_mbps"])
    received_gb=delivered*scenario["duration_s"]/8000
    cpu=leg["cpu"]
    return {"offered_mbps":{"windows":w["sent_payload_mbps"],"linux":l["sent_payload_mbps"]},
            "first_delivered_mbps":{"windows":w["received_payload_mbps"],"linux":l["received_payload_mbps"]},
            "generator_cpu_s":{"windows":w["sender_cpu_seconds"],"linux":l["sender_cpu_seconds"]},
            "whole_exe_cpu_s":cpu.get("cpu_seconds"),"peak_rss_bytes":cpu.get("peak_rss_bytes"),
            "cpu_seconds_per_first_delivered_GB":round(cpu["cpu_seconds"]/received_gb,4) if received_gb>0 and cpu.get("cpu_seconds") is not None else None,
            "first_delivered_fraction":{"windows":w["received_first_packets"]/max(1,l["sent_packets"]),
                                       "linux":l["received_first_packets"]/max(1,w["sent_packets"])}}
rows={leg["leg"]:metrics(leg) for leg in legs}
result={"schema_version":2,"source_sha":os.environ.get("GITHUB_SHA"),
        "scenario_id":scenario["scenario_id"],"scenario_sha256":scenario["scenario_sha256"],
        "run_id":os.environ.get("GITHUB_RUN_ID"),"runner":os.environ.get("RUNNER_NAME"),
        "comparison_scope":"SAME_VM_SAME_BINARIES_CURRENT_SOURCE_GO_STEADY_VS_RUST_NATIVE",
        "order":["B","A"],"legs":rows,"issues":issues,
        "status":"INCONCLUSIVE_OR_FAILED" if issues else "COMPARABLE_OBSERVATION_NOT_PRODUCT_QUALIFICATION"}
if len(legs)==2 and not issues:
    a,b=rows["A"],rows["B"]
    if a["cpu_seconds_per_first_delivered_GB"] and b["cpu_seconds_per_first_delivered_GB"]:
        result["rust_vs_go_cpu_seconds_per_GB_ratio"]=round(b["cpu_seconds_per_first_delivered_GB"]/a["cpu_seconds_per_first_delivered_GB"],4)
    result["delivered_fraction_99_9_gate"]={
       leg:all(f>=.999 for f in m["first_delivered_fraction"].values()) for leg,m in rows.items()}
(ab/"report.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
(out/"normal-report.json").write_text(json.dumps({"source":os.environ.get("GITHUB_SHA"),
    "mode":"normal","mode_public":"PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal" if not issues else "FAIL_OR_INCONCLUSIVE_V2_AB",
    "stop":"PASS_BOTH_OWNED" if all(x["stop"]=="PASS_BOTH_OWNED" for x in legs) else "FAIL_OWNED_STOP",
    "WL_V2_AB":result["status"],"ab_report":"wl-ab-v2/report.json"},indent=2)+"\n")
print("WL_V2_AB_RESULT "+json.dumps(result,sort_keys=True),flush=True)
sys.exit(1 if issues else 0)
