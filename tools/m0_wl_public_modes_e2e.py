#!/usr/bin/env python3
"""One-source original Go/Rust Windows-Linux functional mode batch.

Reuse a single signed-driver/WSL host and compiled native artifacts.
Never derive product PASS from compile or a different mode. A failed
mode remains a FAIL with its exact original source and report.
"""
import os,sys,json,subprocess,pathlib
from m0_wl_mode_evidence import (
 archive_mode_evidence,capture_mode_evidence_baseline,
 select_source_locked_modes)
root=pathlib.Path.cwd()
out=root/"result"/"wl-public"
try:
 modes=select_source_locked_modes(
  os.environ.get("WBD_WL_PUBLIC_MODES","all"),
  performance=os.environ.get("WBD_WL_RUN_N0")=="1" or os.environ.get("WBD_WL_RUN_P200")=="1" or bool(os.environ.get("WBD_WL_V2_SCENARIO")))
except ValueError as error:
 raise SystemExit(str(error)) from error
results={}
failed=[]
for mode in modes:
 env=os.environ.copy()
 env["WBD_WL_PUBLIC_MODE"]=mode
 # Never reinterpret the preceding mode's report as this mode's result.
 (out/"report.json").unlink(missing_ok=True)
 baseline=capture_mode_evidence_baseline(out)
 print("WL_PUBLIC_REAL_MODE_START "+mode,flush=True)
 child=subprocess.run([sys.executable,"tools/m0_wl_public_normal_e2e.py"],env=env)
 report=out/"report.json"
 result=json.loads(report.read_text()) if report.exists() else {
  "mode":mode,"error":"missing genuine same-source report"}
 (out/(mode+"-report.json")).write_text(json.dumps(result,indent=2)+"\n")
 # Per-mode allowlisted redacted logs and sampled resource files survive
 # later uses of the same WSL2/Npcap/Go+Rust native runner.
 evidence=archive_mode_evidence(out,mode,os.environ["GITHUB_SHA"],result,child.returncode,baseline=baseline)
 # A native functional first/reverse/Stop PASS does NOT qualify a
 # selected throughput scenario if actual delivery/loss/kernel TC failed.
 performance=os.environ.get("WBD_WL_RUN_N0")=="1"
 stress=os.environ.get("WBD_WL_RUN_P200")=="1"
 rust_v2=bool(os.environ.get("WBD_WL_V2_SCENARIO"))
 v2=result.get("WL_V2",{}) if rust_v2 else {}
 # Intentional 1/5/10/30% outer loss must preserve all measured first
 # arrivals, not be forced through the no-loss >=99.9% hard gate.
 repair_scene=rust_v2 and os.environ["WBD_WL_V2_SCENARIO"].startswith(
  "scenarios/wl-outer-repair-")
 v2_delivery_ok=(not rust_v2 or (
  v2.get("status")=="MEASURED_BOTH_OS_KERNEL" and
  v2.get("owned_stop")=="PASS_BOTH_OWNED" and
  (repair_scene or all(v2.get("first_delivery_fraction",{}).get(k,0)>=.999
       for k in ("windows","linux")))))
 passed=child.returncode==0 and result.get("mode_public","").startswith("PASS_ACTUAL_") and (
  not performance or str(result.get("WL_N0","")).startswith("PASS_SCOPED_")) and (
  not stress or str(result.get("WL_P200","")).startswith("PASS_SCOPED_")) and v2_delivery_ok
 results[mode]={"result":"PASS" if passed else "FAIL",
   "error":result.get("error"),"report":mode+"-report.json",
   "WL_N0":result.get("WL_N0","NOT_RUN") if performance else "NOT_RUN",
   "WL_P200":result.get("WL_P200","NOT_RUN") if stress else "NOT_RUN",
   "WL_V2":v2.get("status","NOT_RUN") if rust_v2 else "NOT_RUN",
   "WL_V2_FIRST_DELIVERY":v2.get("first_delivery_fraction","NOT_MEASURED") if rust_v2 else "NOT_RUN",
   "evidence_manifest":str(evidence.relative_to(out)).replace(chr(92),"/") }
 print("WL_PUBLIC_REAL_MODE_RESULT "+mode+" "+results[mode]["result"],flush=True)
 if not passed:failed.append(mode)
summary={"source":os.environ["GITHUB_SHA"],
 "windows_linux_real_native_modes":results,
 "result":"FAIL" if failed else "PASS","failed_modes":failed,
 "WL_N0":results[modes[0]]["WL_N0"] if len(modes)==1 else "NOT_RUN",
 "WL_P200":results[modes[0]]["WL_P200"] if len(modes)==1 else "NOT_RUN",
 "WL_V2":results[modes[0]]["WL_V2"] if len(modes)==1 else "NOT_RUN",
 "WL_N1":"NOT_RUN","WL_N5":"NOT_RUN"}
(out/"mode-batch.json").write_text(json.dumps(summary,indent=2)+"\n")
print("WL_PUBLIC_REAL_MODE_BATCH "+summary["result"]+" "+",".join(failed),flush=True)
sys.exit(1 if failed else 0)
