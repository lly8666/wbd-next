#!/usr/bin/env python3
"""One-source original Go/Rust Windows-Linux functional mode batch.

Reuse a single signed-driver/WSL host and compiled native artifacts.
Never derive product PASS from compile or a different mode. A failed
mode remains a FAIL with its exact original source and report.
"""
import os,sys,json,subprocess,pathlib
from m0_wl_mode_evidence import archive_mode_evidence,capture_mode_evidence_baseline
root=pathlib.Path.cwd()
out=root/"result"/"wl-public"
modes=["normal","fixed","auto","game2","game4","game2-fec","game4-fec"]
if os.environ.get("WBD_WL_PUBLIC_MODES") in ("auto-revision","auto-adaptive"):
 modes=[os.environ["WBD_WL_PUBLIC_MODES"]]
# A functional batch may reuse one VM for seven modes. A performance run
# MUST be exactly one named mode and one impairment scenario per Action.
if os.environ.get("WBD_WL_RUN_N0")=="1" and len(modes)!=1:
 raise SystemExit("WL_PERF_REQUIRES_ONE_MODE_ONE_SCENARIO")
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
 passed=child.returncode==0 and result.get("mode_public","").startswith("PASS_ACTUAL_")
 results[mode]={"result":"PASS" if passed else "FAIL",
   "error":result.get("error"),"report":mode+"-report.json",
   "evidence_manifest":str(evidence.relative_to(out)).replace(chr(92),"/") }
 print("WL_PUBLIC_REAL_MODE_RESULT "+mode+" "+results[mode]["result"],flush=True)
 if not passed:failed.append(mode)
summary={"source":os.environ["GITHUB_SHA"],
 "windows_linux_real_native_modes":results,
 "result":"FAIL" if failed else "PASS","failed_modes":failed,
 "WL_N0":"NOT_RUN","WL_N1":"NOT_RUN","WL_N5":"NOT_RUN"}
(out/"mode-batch.json").write_text(json.dumps(summary,indent=2)+"\n")
print("WL_PUBLIC_REAL_MODE_BATCH "+summary["result"]+" "+",".join(failed),flush=True)
sys.exit(1 if failed else 0)
