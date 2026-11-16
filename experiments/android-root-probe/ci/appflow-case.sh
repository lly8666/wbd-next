#!/usr/bin/env bash
# One ordinary APK UDP packet actually captured by the KSU-root TUN through
# an ephemeral exact app UID + destination /32 rule. Not a netd/NAT proof.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/appflow
o=out/appflow
test "$(cat out/native/SOURCE)" = "$GITHUB_SHA"
(cd out/native && sha256sum -c SHA256SUMS) >"$o/native-hashes.txt"
cp out/native/{SOURCE,manifest.json,SHA256SUMS} "$o/"
adb shell getprop ro.build.version.sdk >"$o/api.txt"
adb shell getenforce >"$o/selinux.txt"
adb shell getprop ro.kernel.qemu >"$o/qemu.txt"
adb shell pm path org.wbdnext.rootprobe >"$o/app-package.txt"
adb shell id >"$o/adb-identity.txt"
# ADB is only transport. KSU Root authorized the app via real Manager.
adb push out/native/bin/probe-x86_64-linux-android /data/local/tmp/wbd-app-native >"$o/native-stage.txt"
adb shell chmod 0755 /data/local/tmp/wbd-app-native
trap 'adb shell rm -f /data/local/tmp/wbd-app-native >/dev/null 2>&1 || true' EXIT
adb shell su -c 'ip -4 rule show' >"$o/rule-before.txt"
adb shell su -c 'ip -4 route show table all' >"$o/route-before.txt"
# Do not reuse the initial pre-grant JSON or previous app-flow result.
adb shell run-as org.wbdnext.rootprobe rm -f files/flow-result.json
adb shell am start -W -n org.wbdnext.rootprobe/.AppFlowActivity >"$o/start.txt"
have=0
for i in $(seq 1 45); do
 if adb shell run-as org.wbdnext.rootprobe cat files/flow-result.json >"$o/app-flow.json" 2>"$o/read.err"; then
   if python3 -m json.tool "$o/app-flow.json" >/dev/null 2>&1;then have=1;break;fi
 fi
 sleep 1
done
adb logcat -d -s WBD_APP_FLOW:I >"$o/app-logcat.txt" 2>&1 || true
if [[ "$have" != 1 ]];then
 echo '{"status":"APP_RESULT_MISSING","reason":"no real app private result"}' >"$o/app-flow.json"
fi
adb shell su -c 'ip -4 rule show' >"$o/rule-after.txt"
adb shell su -c 'ip -4 route show table all' >"$o/route-after.txt"
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path("out/appflow")
def read(f):return (p/f).read_text(errors="replace").strip()
a=json.loads(read("app-flow.json"))
m=json.loads(Path("out/native/manifest.json").read_text())
native=a.get("native") or {}
ev=native.get("evidence") or {}
cl=native.get("cleanup") or {}
uid=a.get("app_uid",0)
errors=[]
if m["source"]!=os.environ["GITHUB_SHA"] or read("SOURCE")!=os.environ["GITHUB_SHA"]:errors.append("native SOURCE mismatch")
if read("api.txt")!="36" or read("selinux.txt")!="Enforcing":errors.append("emulator API/SELinux mismatch")
if a.get("target_sdk")!=37 or uid<10000:errors.append("not the expected real ordinary APK")
if not "untrusted_app" in a.get("app_selinux",""):errors.append("not untrusted_app SELinux")
if a.get("su_exit")!=0 or native.get("root_uid")!=0:errors.append("real app->KSU UID0 unproven")
if not a.get("root_ready") or a.get("app_udp_sent_bytes",0)<1:errors.append("app DatagramSocket not used")
if a.get("status")!="APP_UID_TUN_ROUNDTRIP_PASS":errors.append("true ordinary App UDP TUN proof failed")
if native.get("app_uid")!=uid or ev.get("app_uid_rule")!=f"{uid}-{uid}":errors.append("UID-specific route not proven")
if ev.get("status")!="SUPPORTED_IN_SCOPE" or not ev.get("app_payload_on_tun"):errors.append("real app payload missing from TUN")
if ev.get("dst_ip")!="198.18.254.2" or ev.get("dst_port")!=49492:errors.append("wrong packet destination")
if not ev.get("tun_reply_injected_bytes",0)>28:errors.append("no TUN UDP return injection")
if not a.get("app_reply_bytes",0)>0:errors.append("ordinary app did not receive UDP reply")
if a.get("app_reply_payload")!=ev.get("tun_reply_payload"):errors.append("return payload mismatch")
if a.get("app_reply_source")!="198.18.253.2:49492":errors.append("return source not owned TUN peer")
if ev.get("tun_mtu")!=1400 or ev.get("udp_packet_bytes",0)<28:errors.append("TUN packet/MTU missing")
if not all(cl.get(k) is True for k in ("ok","rules_equal","routes_equal","tun_gone")):errors.append("owned cleanup failed")
if read("rule-before.txt")!=read("rule-after.txt"):errors.append("Android global policy rules changed")
if read("route-before.txt")!=read("route-after.txt"):errors.append("Android global route snapshots changed")
out={"schema":"android-ksu-app-origin-udp-case/v1","source":m["source"],"api":read("api.txt"),
"app_uid":uid,"app_context":a.get("app_selinux"),"su_exit":a.get("su_exit"),
"status":"APP_UID_TUN_ROUNDTRIP_PASS" if not errors else "FAIL",
"capture":ev,"app_reply":a.get("app_reply_payload"),"app_reply_source":a.get("app_reply_source"),"cleanup":cl,"errors":errors,
"netd_nat_tether_real_underlay":"NOT_RUN",
"scope":"one ordinary app UID to root-owned TUN using temporary exact /32 rule"}
(p/"summary.json").write_text(json.dumps(out,indent=2,sort_keys=True))
print(json.dumps(out,indent=2,sort_keys=True))
if errors:raise SystemExit("real App-origin packet capture not proven; see app-flow.json")
PY
