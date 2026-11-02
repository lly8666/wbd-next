#!/usr/bin/env python3
"""H876: one Windows runner, one original TLS/Rust binary pair, sequential OFF/ON.

Each leg executes the EXISTING signed NPF/Wintun-to-WSL2 public mode runner,
including true UDP/TCP, Rust effective readback and both owned Stop. Only the
cold original --outer-repair flag differs; never parallelize two OS leases.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

root=pathlib.Path.cwd()
out=root/"result"/"wl-public"
pair=out/"outer-pair"
scenario=os.environ.get("WBD_WL_V2_SCENARIO","")
if os.environ.get("WBD_WL_PUBLIC_MODES")!="normal" or scenario!=(
    "scenarios/plan027-h876-normal-pair-10m-250ms-0loss-60s.json"):
    raise SystemExit("H876 refuses another mode or mutable scenario")
if pair.exists():
    raise SystemExit("H876 refuses stale pair results")
pair.mkdir(parents=True)
source=os.environ["GITHUB_SHA"]
legs=[]
result={"schema":"plan027-original-native-outer-pair/v1",
        "source_sha":source,"scenario":scenario,"order":"OFF_ON",
        "result":"NOT_RUN","legs":[],"attribution":"NOT_ESTABLISHED"}
(pair/"result.json").write_text(json.dumps(result,indent=2)+"\n")

for repair in ("off","on"):
    legdir=pair/repair
    legdir.mkdir()
    env=os.environ.copy()
    env["WBD_WL_OUTER_REPAIR"]=repair
    env["WBD_WL_PUBLIC_MODES"]="normal"
    print("PLAN027_H876_NATIVE_PAIR_BEGIN policy="+repair+" source="+source,flush=True)
    started=time.monotonic()
    child=subprocess.Popen([sys.executable,"-u","tools/m0_wl_public_modes_e2e.py"],
                           env=env)
    timed_out=False
    try:
        code=child.wait(timeout=360)
    except subprocess.TimeoutExpired:
        timed_out=True
        if os.name=="nt":
            subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],
                           stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                           timeout=25,check=False)
        if child.poll() is None:child.kill()
        child.wait(timeout=15)
        code=124
    report_path=out/"normal-report.json"
    if report_path.exists():
        shutil.copy2(report_path,legdir/"normal-report.json")
    archived=out/"mode-results"/"normal"
    if archived.is_dir():
        shutil.copytree(archived,legdir/"native-evidence")
    report=json.loads(report_path.read_text()) if report_path.is_file() else {}
    # Original Windows child must leave no attached WAL/route journal before
    # the subsequent generation is allowed to start on the SAME OS.
    wal_left=[str(p.relative_to(out)) for p in
              (out/"owned-wal.json.n4-owned-wal",out/"owned-wal.json.n4-owned-wal.routes")
              if p.exists()]
    native=report.get("WL_V2",{})
    effective=report.get("original_outer_repair_effective",{})
    windows=report.get("runtime_observability",{}).get("windows_original_process",{})
    expected=0 if repair=="off" else 1
    fractions=native.get("first_delivery_fraction",{})
    offers=native.get("offered_mbps",{})
    qualifies=(code==0 and not timed_out and not wal_left and
       report.get("source")==source and report.get("linux_binary_source")==source and
       report.get("mode_public")=="PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal" and
       report.get("stop")=="PASS_BOTH_OWNED" and
       native.get("status")=="MEASURED_BOTH_OS_KERNEL" and
       native.get("owned_stop")=="PASS_BOTH_OWNED" and
       all(effective.get(k) is True for k in ("windows","linux")) and
       effective.get("enabled")==expected and
       all(isinstance(fractions.get(k),(int,float)) and fractions[k]>=.999
           for k in ("windows","linux")) and
       all(isinstance(offers.get(k),(int,float)) and offers[k]>=9.5
           for k in ("windows","linux")) and
       windows.get("result")=="MEASURED_SAME_NATIVE_PID" and
       isinstance(windows.get("cpu_total_s"),(int,float)) and
       windows["cpu_total_s"]>0)
    entry={"policy":repair,"source_sha":source,"child_exit":code,
           "timed_out":timed_out,"wall_seconds":round(time.monotonic()-started,3),
           "result":"PASS" if qualifies else "FAIL",
           "mode_public":report.get("mode_public","NOT_RUN"),
           "original_effective":effective,"owned_stop":report.get("stop","NOT_RUN"),
           "first_delivery_fraction":fractions,"offered_mbps":offers,
           "first_delivered_mbps":native.get("first_delivered_mbps"),
           "windows_process_cpu_s":windows.get("cpu_total_s"),
           "windows_process_kernel_cpu_s":windows.get("cpu_kernel_s"),
           "windows_process_user_cpu_s":windows.get("cpu_user_s"),
           "windows_elapsed_s":windows.get("elapsed_s"),
           "windows_peak_working_set_bytes":windows.get("peak_working_set_bytes"),
           "windows_cli_sha256":report.get("windows_cli_sha256"),
           "linux_server_sha256":report.get("linux_server_sha256"),
           "wal_left":wal_left,"frc":"NOT_MEASURED_WINDOWS_OUTER"}
    legs.append(entry)
    result["legs"]=legs
    result["result"]="IN_PROGRESS" if qualifies else "FAIL"
    (pair/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    print("PLAN027_H876_NATIVE_PAIR_LEG "+json.dumps(entry,sort_keys=True),flush=True)
    if not qualifies:
        print("PLAN027_H876_PAIR_STOP_NO_SECOND_LEG",flush=True)
        sys.exit(1)

off,on=legs
if (off["windows_cli_sha256"]!=on["windows_cli_sha256"] or
    off["linux_server_sha256"]!=on["linux_server_sha256"] or
    not off["windows_cli_sha256"] or not off["linux_server_sha256"]):
    result["result"]="FAIL_BINARY_DRIFT"
    (pair/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    raise SystemExit("same runner must use identical original binary hashes")
c_off,c_on=off["windows_process_cpu_s"],on["windows_process_cpu_s"]
comparison={"cpu_on_minus_off_s":round(c_on-c_off,4),
            "relative_to_on":round((c_on-c_off)/c_on,5),
            "off_cpu_s":c_off,"on_cpu_s":c_on,
            "off_peak_rss_bytes":off["windows_peak_working_set_bytes"],
            "on_peak_rss_bytes":on["windows_peak_working_set_bytes"],
            "order":"OFF_ON","scope":"SAME_RUNNER_SAME_BINARY_SEQUENTIAL",
            "not_a_proven_optimization":True,
            "cold_start_and_stop_in_cpu_sample":True}
result["comparison"]=comparison
result["result"]="PASS_TWO_TRUE_NATIVE_LEGS"
result["attribution"]="MEASURED_TOTAL_CPU_DELTA_NOT_ISOLATED_ALGORITHM_OR_DRIVER"
(pair/"result.json").write_text(json.dumps(result,indent=2)+"\n")
print("PLAN027_H876_NATIVE_SAME_VM_PAIR "+json.dumps(comparison,sort_keys=True),flush=True)
