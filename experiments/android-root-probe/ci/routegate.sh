#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/routegate
o=out/routegate
cp out/build/{SOURCE,manifest.json,SHA256SUMS} "$o/"
adb shell getprop ro.build.version.sdk >"$o/api.txt"
adb shell getprop ro.build.version.release >"$o/release.txt"
adb shell getenforce >"$o/enforce.txt"
adb shell id >"$o/shell-id.txt"
adb push out/build/bin/probe-x86_64-linux-android /data/local/tmp/android-root-probe >"$o/push.txt"
trap 'adb shell rm -f /data/local/tmp/android-root-probe >/dev/null 2>&1 || true' EXIT
adb shell chmod 0700 /data/local/tmp/android-root-probe
timeout 30s adb root >"$o/root.txt" 2>&1
adb wait-for-device
adb shell id >"$o/root-id.txt"
adb shell getenforce >"$o/enforce-root.txt"
timeout 5s adb shell ip -4 rule show >"$o/system-rule-before.txt"
timeout 5s adb shell ip -4 route show table all >"$o/system-route-before.txt"
set +e
timeout --signal=TERM --kill-after=4s 45s adb shell /data/local/tmp/android-root-probe routegate >"$o/probe.json" 2>"$o/probe.err"
rc=$?
set -e
echo "$rc" >"$o/probe.exit"
timeout 5s adb shell ip -4 rule show >"$o/system-rule-after.txt"
timeout 5s adb shell ip -4 route show table all >"$o/system-route-after.txt"
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path("out/routegate")
get=lambda f:(p/f).read_text().strip()
d=json.loads(get("probe.json"))
m=json.loads(Path("out/build/manifest.json").read_text())
err=[]
if m["source"]!=get("SOURCE") or m["source"]!=os.environ["GITHUB_SHA"]:err.append("SOURCE mismatch")
if get("api.txt")!=os.environ["ANDROID_PROBE_API"]:err.append("API mismatch")
if get("enforce-root.txt")!="Enforcing":err.append("SELinux not Enforcing")
if d.get("global_changes") is not False:err.append("global change assertion missing")
for f in ("rule","route"):
    if get("system-"+f+"-before.txt")!=get("system-"+f+"-after.txt"):err.append("global "+f+" changed")
if get("probe.exit")!="0":err.append("probe exit nonzero")
if d.get("status")=="SUPPORTED_IN_SCOPE":
    v=d.get("evidence",{})
    if d.get("before")==d.get("after"):err.append("namespace identity not distinct")
    if v.get("unmarked_negative") is not True:err.append("unmarked negative missing")
    if v.get("marked_udp_tun_read_bytes",0)<28:err.append("marked TUN packet missing")
    if v.get("SO_MARK_readback")!=0x23500:err.append("socket mark readback missing")
    if "interface gone" not in d.get("cleanup",""):err.append("TUN cleanup missing")
elif d.get("status") not in ("ENV_BLOCKED","PERMISSION_DENIED"):err.append("fixture failed")
status="FAIL" if err else d["status"]
s={"schema":"android-routegate-case/v1","source":m["source"],"api":get("api.txt"),
   "status":status,"evidence":d,"errors":err,
   "app_to_su":"NOT_RUN","netd_nat_tether":"NOT_RUN"}
(p/"summary.json").write_text(json.dumps(s,indent=2,sort_keys=True))
print(json.dumps(s,indent=2))
if err:raise SystemExit("fixture failed")
if status!="SUPPORTED_IN_SCOPE":raise SystemExit("isolated netns blocked; no route writes")
PY
