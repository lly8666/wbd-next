#!/usr/bin/env bash
set -euo pipefail
mkdir -p out/appcase
o=out/appcase
cp out/apk/{SOURCE,manifest.json,SHA256SUMS,badging.txt,compile-api.txt} "$o/"
adb shell getprop ro.build.version.sdk >"$o/api.txt"
adb shell getenforce >"$o/enforce.txt"
adb shell id >"$o/adb-shell-id.txt"
adb shell ls -l /system/xbin/su >"$o/su-file.txt" 2>&1 || true
# Staging via normal adb shell uid2000, never adb root as app-su authorization.
adb push out/native/bin/probe-x86_64-linux-android /data/local/tmp/wbd-app-native >"$o/push.txt"
adb shell chmod 0755 /data/local/tmp/wbd-app-native
trap 'adb shell rm -f /data/local/tmp/wbd-app-native >/dev/null 2>&1 || true' EXIT
adb install -r out/apk/app-su.apk >"$o/install.txt"
adb shell am start -W -n org.wbdnext.rootprobe/.ProbeActivity >"$o/start.txt"
have=0
for i in $(seq 1 38); do
 if adb shell run-as org.wbdnext.rootprobe cat files/result.json >"$o/app-result.json" 2>"$o/run-as.err"; then
  if python3 -m json.tool "$o/app-result.json" >/dev/null 2>&1;then have=1;break;fi
 fi
 sleep 1
done
adb logcat -d -s WBD_APP_SU:I >"$o/logcat.txt" 2>&1 || true
if [[ "$have" != 1 ]];then
 echo '{"status":"APP_RESULT_MISSING"}' >"$o/app-result.json"
fi
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path("out/appcase")
read=lambda f:(p/f).read_text(errors="replace").strip()
d=json.loads(read("app-result.json"))
m=json.loads(Path("out/apk/manifest.json").read_text())
errors=[]
if m["source"]!=read("SOURCE") or m["source"]!=os.environ["GITHUB_SHA"]:errors.append("app SOURCE mismatch")
if read("api.txt")!="36":errors.append("API not Android16")
if read("enforce.txt")!="Enforcing":errors.append("SELinux not enforcing")
if m["target_sdk"]!=37:errors.append("targetSdk not 37")
if d.get("app_uid",0)<10000:errors.append("ordinary app UID not observed")
if d.get("target_sdk")!=37:errors.append("app runtime targetSdk wrong")
if d.get("status")=="APP_SU_NATIVE_EXERCISE_PASS" and "uid=0(" not in d.get("su_stdout_stderr",""):errors.append("false root positive")
status="FAIL" if errors else d.get("status","APP_RESULT_MISSING")
summary={"schema":"android-app-su-case/v1","source":m["source"],
 "native_source":m["native_source"],"api":read("api.txt"),
 "execution_path":"actual APK normal UID -> existing su", "app_uid":d.get("app_uid"),
 "app_selinux":d.get("app_context"),"su_exit":d.get("su_exit"),
 "status":status,"authorized_app_su":status=="APP_SU_NATIVE_EXERCISE_PASS",
 "errors":errors,"limitations":"AOSP developer su is not a user-approval root manager"}
(p/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
print(json.dumps(summary,indent=2,sort_keys=True))
if status!="APP_SU_NATIVE_EXERCISE_PASS":raise SystemExit("APP->SU not proven; inspect original result")
PY
