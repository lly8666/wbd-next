#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
o=out/appflow-crash
mkdir -p "$o"
(cd out/native && sha256sum -c SHA256SUMS) >"$o/native-hashes.txt"
test "$(cat out/native/SOURCE)" = "$GITHUB_SHA"
test "$(adb shell getenforce | tr -d '\r')" = Enforcing
uid="$(python3 - <<'PY'
import json
x=json.load(open("out/appflow/summary.json"))
assert x["status"]=="APP_UID_TUN_ROUNDTRIP_PASS"
assert 10000<=x["app_uid"]<=199999
print(x["app_uid"])
PY
)"
token="kill${GITHUB_SHA:0:16}"
remote="/data/local/tmp/wbd-watch-${token}.json"
adb push out/native/bin/probe-x86_64-linux-android /data/local/tmp/wbd-app-native >"$o/stage.txt"
adb shell chmod 0755 /data/local/tmp/wbd-app-native
trap 'adb shell su -c "rm -f /data/local/tmp/wbd-watch-kill${GITHUB_SHA:0:16}.json" >/dev/null 2>&1 || true; adb shell rm -f /data/local/tmp/wbd-app-native >/dev/null 2>&1 || true' EXIT
adb shell su -c 'ip -4 rule show' >"$o/rule-before.txt"
adb shell su -c 'ip -4 route show table all' >"$o/route-before.txt"
set +e
timeout --signal=TERM --kill-after=2s 16s adb shell su -c \
 "/data/local/tmp/wbd-app-native appflow-kill ${uid} ${token}" \
 >"$o/killed-worker.stdout" 2>"$o/killed-worker.stderr"
rc=$?
set -e
echo "$rc" >"$o/killed-worker.exit"
found=0
for i in $(seq 1 35);do
 if adb shell su -c "cat $remote" >"$o/watchdog.json" 2>"$o/watchdog.err";then
   if python3 -m json.tool "$o/watchdog.json" >/dev/null 2>&1;then found=1;break;fi
 fi
 sleep 0.2
done
if [[ "$found" != 1 ]];then
 echo '{"status":"MISSING_WATCHDOG_ATTESTATION"}' >"$o/watchdog.json"
fi
adb shell su -c 'ip -4 rule show' >"$o/rule-after.txt"
adb shell su -c 'ip -4 route show table all' >"$o/route-after.txt"
adb shell su -c 'ip -4 route show table 235' >"$o/table235-after.txt"
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path("out/appflow-crash")
r=lambda f:(p/f).read_text(errors="replace").strip()
w=json.loads(r("watchdog.json"))
errors=[]
expected="kill"+os.environ["GITHUB_SHA"][:16]
if r("killed-worker.exit")=="0":errors.append("owner was not killed")
if r("killed-worker.exit")=="124":errors.append("worker timed out, not verified SIGKILL")
if "WBD_APPFLOW_READY "+expected not in r("killed-worker.stdout"):
    errors.append("worker never signalled armed route")
if w.get("status")!="CLEANED":errors.append("independent watchdog did not confirm cleanup")
if not w.get("rule_seen_after_owner_exit") or not w.get("rule_removed_by_watchdog"):
    errors.append("no orphaned policy rule removed by watcher")
if not w.get("rule_absent") or not w.get("table235_empty"):
    errors.append("owned rule/table persists after cleanup")
if r("rule-before.txt")!=r("rule-after.txt"):errors.append("global IPv4 rules differ")
if r("route-before.txt")!=r("route-after.txt"):errors.append("global IPv4 routes differ")
if r("table235-after.txt"):errors.append("policy table235 not empty")
out={"schema":"android-ksu-sigkill-watchdog/v1",
     "source":os.environ["GITHUB_SHA"],"app_uid":json.load(open("out/appflow/summary.json"))["app_uid"],
     "worker_exit":r("killed-worker.exit"),"watchdog":w,
     "status":"SIGKILL_WATCHDOG_CLEANUP_PASS" if not errors else "FAIL","errors":errors,
     "scope":"KSU shell fixture SIGKILL of real native appflow worker on same AVD, after ordinary App roundtrip"}
(p/"summary.json").write_text(json.dumps(out,indent=2,sort_keys=True))
print(json.dumps(out,indent=2,sort_keys=True))
if errors:raise SystemExit("SIGKILL orphan-rule cleanup not proven")
PY
