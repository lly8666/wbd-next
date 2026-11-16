#!/usr/bin/env bash
# Accurate Apple Silicon host emulator/HVF eligibility; no Android guest, no exploit.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/dirtyfrag-mac-host
python3 - <<'PY'
import datetime,hashlib,json,os,pathlib,platform,shutil,subprocess
root=pathlib.Path(os.environ.get("ANDROID_HOME",str(pathlib.Path.home()/"Library/Android/sdk")))
official=root/"emulator/emulator"
selected=str(official) if official.is_file() else None
fallback=shutil.which("emulator")
def cmd(args,limit=15):
    try:
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=limit)
        return {"exit_code":p.returncode,"output":p.stdout[:1400]}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {"exit_code":None,"output":str(e)}
arch=platform.machine()
binary_kind=cmd(["file","-b",selected]) if selected else None
accel=cmd([selected,"-accel-check"],30) if selected else None
# Do not infer HVF absence from kern.hv_support (unknown on Apple Silicon);
# the native emulator's own acceleration check is the gate.
reason=("HOST_NOT_ARM64" if arch not in ("arm64","aarch64") else
        "NO_OFFICIAL_ARM64_MAC_EMULATOR" if not selected else
        "OFFICIAL_EMULATOR_BINARY_NOT_ARM64" if "arm64" not in (binary_kind or {}).get("output","").lower() else
        "EMULATOR_ACCELERATION_UNAVAILABLE" if (accel or {}).get("exit_code") != 0 else None)
sha=None
if selected:
    h=hashlib.sha256()
    with open(selected,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    sha=h.hexdigest()
d={
 "schema":"android16-dirtyfrag-mac-hvf-corrected/v2",
 "source":os.getenv("GITHUB_SHA","LOCAL_UNCOMMITTED"),
 "observed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "arch":arch,"host_kernel":platform.release(),
 "android_sdk_root":str(root),"official_emulator":selected,
 "path_emulator_fallback_unused":fallback,
 "official_emulator_file":binary_kind,
 "official_emulator_sha256":sha,
 "emulator_accel_check":accel,
 "old_image":"Google Play Android16 API36 arm64-v8a r07 advertised 2025-12-02",
 "old_image_catalog_commit":"7c23968450618e94727e190d3a2ad3cf8f24adf7",
 "guest_booted":False,"dirtyfrag_root":"NOT_RUN","wbd_post_root":"NOT_RUN",
 "status":"ENV_BLOCKED" if reason else "READY_FOR_GUEST_PREFLIGHT",
 "reason":reason or "Host and native emulator supported; actual guest/root NOT_RUN"
}
pathlib.Path("out/dirtyfrag-mac-host/summary.json").write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
print(json.dumps({k:d[k] for k in ("source","arch","official_emulator","official_emulator_file","emulator_accel_check","status","reason")},indent=2))
PY
shasum -a 256 experiments/android-root-probe/ci/dirtyfrag-mac-host-preflight.sh >out/dirtyfrag-mac-host/script.sha256
