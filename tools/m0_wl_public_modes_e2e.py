#!/usr/bin/env python3
"""One-source original Go/Rust Windows-Linux functional mode batch.

Reuse a single signed-driver/WSL host and compiled native artifacts.
Never derive product PASS from compile or a different mode. A failed
mode remains a FAIL with its exact original source and report.
"""
import os,sys,json,subprocess,pathlib,shutil
root=pathlib.Path.cwd()
out=root/"result"/"wl-public"
modes=["normal","fixed","auto","game2","game4","game2-fec","game4-fec"]
if os.environ.get("WBD_WL_PUBLIC_MODES") in ("auto-revision","auto-adaptive"):
 modes=[os.environ["WBD_WL_PUBLIC_MODES"]]
results={}
failed=[]
for mode in modes:
 env=os.environ.copy()
 env["WBD_WL_PUBLIC_MODE"]=mode
 print("WL_PUBLIC_REAL_MODE_START "+mode,flush=True)
 child=subprocess.run([sys.executable,"tools/m0_wl_public_normal_e2e.py"],env=env)
 report=out/"report.json"
 result=json.loads(report.read_text()) if report.exists() else {
  "mode":mode,"error":"missing genuine same-source report"}
 (out/(mode+"-report.json")).write_text(json.dumps(result,indent=2)+"\n")
 # Keep the exact original-Go/Rust first error per mode; subsequent
 # modes reuse the same real WSL/driver but otherwise overwrite logs.
 for name in ("client.log","server.log","native-link-tcp443.log"):
  source=out/name
  if source.is_file():shutil.copyfile(source,out/(mode+"-"+name))
 passed=child.returncode==0 and result.get("mode_public","").startswith("PASS_ACTUAL_")
 results[mode]={"result":"PASS" if passed else "FAIL",
   "error":result.get("error"),"report":mode+"-report.json"}
 print("WL_PUBLIC_REAL_MODE_RESULT "+mode+" "+results[mode]["result"],flush=True)
 if not passed:failed.append(mode)
summary={"source":os.environ["GITHUB_SHA"],
 "windows_linux_real_native_modes":results,
 "result":"FAIL" if failed else "PASS","failed_modes":failed,
 "WL_N0":"NOT_RUN","WL_N1":"NOT_RUN","WL_N5":"NOT_RUN"}
(out/"mode-batch.json").write_text(json.dumps(summary,indent=2)+"\n")
print("WL_PUBLIC_REAL_MODE_BATCH "+summary["result"]+" "+",".join(failed),flush=True)
sys.exit(1 if failed else 0)
