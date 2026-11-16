#!/usr/bin/env bash
# Single Apple Silicon Actions host acceleration preflight. No guest/exploit.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/dirtyfrag-mac-host
python3 - <<'PY'
import datetime,json,os,pathlib,platform,shutil,subprocess
def command(argv):
    try:
        p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                         text=True,timeout=12)
        return {"exit_code":p.returncode,"output":p.stdout[:1500]}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {"exit_code":None,"output":str(e)}
arch=platform.machine()
hvf=command(["sysctl","-n","kern.hv_support"])
candidate=shutil.which("emulator")
if not candidate:
    for root in (os.getenv("ANDROID_HOME"),os.getenv("ANDROID_SDK_ROOT")):
        if root and pathlib.Path(root,"emulator/emulator").exists():
            candidate=str(pathlib.Path(root,"emulator/emulator"))
            break
acc=command([candidate,"-accel-check"]) if candidate else {"exit_code":None,"output":"emulator not on runner"}
hvf_ok=hvf["exit_code"]==0 and hvf["output"].strip()=="1"
acc_ok=acc["exit_code"]==0 and ("accel" in acc["output"].lower() or "hypervisor" in acc["output"].lower())
reason=("HOST_NOT_APPLE_ARM64" if arch not in ("arm64","aarch64") else
        "MACOS_HVF_UNAVAILABLE" if not hvf_ok else
        "ANDROID_MAC_ARM64_EMULATOR_MISSING" if not candidate else
        "EMULATOR_ACCEL_CHECK_FAILED" if not acc_ok else None)
d={
 "schema":"android16-dirtyfrag-mac-host-eligibility/v1",
 "source":os.getenv("GITHUB_SHA","LOCAL_UNCOMMITTED"),
 "observed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "host_arch":arch,"host_kernel":platform.release(),
 "hvf_sysctl":hvf,"emulator_binary":candidate,"emulator_accel_check":acc,
 "image_candidate":"Google Play API36 arm64-v8a r07 (listed 2025-12-02)",
 "image_snapshot_source":"7c23968450618e94727e190d3a2ad3cf8f24adf7",
 "image_not_downloaded":True,"guest_booted":False,
 "dirtyfrag_root":"NOT_RUN","post_root_wbd":"NOT_RUN",
 "status":"ENV_BLOCKED" if reason else "READY_FOR_GUEST_PREFLIGHT",
 "reason":reason or "ARM64/HVF/emulator available; historical image/guest and exploit still NOT_RUN"
}
pathlib.Path("out/dirtyfrag-mac-host/summary.json").write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
print(json.dumps({k:d[k] for k in
("source","host_arch","hvf_sysctl","emulator_binary","emulator_accel_check","status","reason")},indent=2))
PY
shasum -a 256 experiments/android-root-probe/ci/dirtyfrag-mac-host-preflight.sh >out/dirtyfrag-mac-host/script.sha256
