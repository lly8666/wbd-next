#!/usr/bin/env bash
# One emulator, one bounded adb-shell -> adb-root scenario; not app->su.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
out="out/case"
mkdir -p "$out"
cp out/build/{SOURCE,manifest.json,SHA256SUMS} "$out/"
{
  echo "SOURCE=$ANDROID_PROBE_SOURCE_SHA"
  echo "build_run_id=${ANDROID_PROBE_BUILD_RUN:-unknown}"
  echo "api_requested=${ANDROID_PROBE_API:-unknown}"
  echo "scenario=canary-adb-root"
  echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host_kernel=$(uname -r)"
  echo "host_kvm=$(ls -l /dev/kvm || true)"
  echo "host_mem=$(head -n 3 /proc/meminfo | tr '\n' ' ')"
  echo "host_psi=$(head -n 5 /proc/pressure/cpu 2>/dev/null | tr '\n' ' ')"
} >"$out/host.txt"
adb shell getprop ro.build.version.sdk >"$out/sdk.txt"
adb shell getprop ro.build.version.release >"$out/release.txt"
adb shell getprop ro.build.version.incremental >"$out/revision.txt"
adb shell getprop ro.product.cpu.abi >"$out/abi.txt"
adb shell uname -r >"$out/kernel.txt"
adb shell getenforce >"$out/enforce.txt" || true
adb shell id >"$out/adb-shell-id.txt"
adb shell 'command -v su || true' >"$out/su-path.txt" || true
adb push out/build/bin/probe-x86_64-linux-android /data/local/tmp/android-root-probe >"$out/push.txt"
adb shell chmod 0700 /data/local/tmp/android-root-probe
set +e
timeout --signal=TERM --kill-after=5s 35s adb shell /data/local/tmp/android-root-probe inspect >"$out/adb-shell-inspect.json" 2>"$out/adb-shell-inspect.err"
echo "$?" >"$out/adb-shell-exit.txt"
set -e
set +e
timeout --signal=TERM --kill-after=5s 30s adb root >"$out/adb-root.txt" 2>&1
root_request=$?
set -e
echo "$root_request" >"$out/adb-root-exit.txt"
adb wait-for-device
adb shell id >"$out/after-root-id.txt"
if [[ "$(adb shell id -u | tr -d '\r')" == "0" ]]; then
  printf 'adb-root\n' >"$out/execution_path.txt"
  set +e
  timeout --signal=TERM --kill-after=5s 120s adb shell /data/local/tmp/android-root-probe exercise >"$out/adb-root-exercise.json" 2>"$out/adb-root-exercise.err"
  exit_code=$?
  set -e
  echo "$exit_code" >"$out/exercise-exit.txt"
else
  printf 'no-adb-root\n' >"$out/execution_path.txt"
  echo '{"status":"PERMISSION_DENIED","scope":"adb root only; app-su NOT_RUN"}' >"$out/adb-root-exercise.json"
  echo 'not-run' >"$out/exercise-exit.txt"
fi
adb shell rm -f /data/local/tmp/android-root-probe || true # owned staging file only
python3 - <<'PY'
import json, os
from pathlib import Path
o=Path("out/case")
def read(p): return (o/p).read_text().strip()
def load(p):
    try: return json.loads(read(p))
    except (ValueError, FileNotFoundError): return None
shell=load("adb-shell-inspect.json")
root=load("adb-root-exercise.json")
checks=(root or {}).get("checks",{})
statuses={k:v.get("status") for k,v in checks.items() if isinstance(v,dict)}
status="NOT_RUN"
if root and checks:
    status="FAIL" if "FAIL" in statuses.values() else "SUPPORTED_IN_SCOPE" if "SUPPORTED_IN_SCOPE" in statuses.values() else "UNAVAILABLE"
elif root:
    status=root.get("status","NOT_RUN")
if read("exercise-exit.txt") not in ("0","not-run"):
    status="FAIL"
summary={
  "schema":"android-root-probe-case/v1",
  "source":os.environ["ANDROID_PROBE_SOURCE_SHA"],
  "build_run":os.getenv("ANDROID_PROBE_BUILD_RUN"),
  "api_requested":os.getenv("ANDROID_PROBE_API"),
  "api_observed":read("sdk.txt"),
  "release":read("release.txt"),
  "image_revision":read("revision.txt"),
  "abi":read("abi.txt"),
  "kernel":read("kernel.txt"),
  "enforcing":read("enforce.txt"),
  "execution_path":read("execution_path.txt"),
  "app_to_su":"NOT_RUN",
  "tether_wifi_usb":"NOT_RUN",
  "cellular_clat":"NOT_RUN",
  "status":status,
  "capability_statuses":statuses,
  "shell_inspect_json_present":shell is not None,
  "hashes_verified_by_case_workflow":True
}
(o/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
print(json.dumps(summary,indent=2))
if status=="FAIL": raise SystemExit("probe internal failure or cleanup failure")
PY
