#!/usr/bin/env bash
# Real user-click APK packaged native invocation; never ADB-push any native
# file for this case. Earlier separate source-locked root tests already ran.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
o=out/device-diag;mkdir -p "$o"
test "$(cat out/diag/SOURCE)" = "$GITHUB_SHA"
(cd out/diag && sha256sum -c SHA256SUMS) >"$o/apk-hashes.txt"
test "$(adb shell getenforce | tr -d '\r')" = Enforcing
test "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = 36
# Assert source-locked original fixture has finished, and no staged helper.
test "$(python3 - <<'PY'
import json
print(json.load(open("out/tether-recovery/summary.json"))["status"])
PY
)" = SYNTHETIC_TETHER_NAT_AND_RECOVERY_PASS
adb shell su -c 'ip -4 rule show' >"$o/rules-before.txt"
adb shell su -c 'ip -4 route show table all' >"$o/routes-before.txt"
# Upgrade the previous ordinary App using the same disposable signing cert.
# ADB installs the APK ONLY. Actual native execution must be through App su.
adb install -r out/diag/device-diagnostic.apk >"$o/install.txt"
adb shell pm path org.wbdnext.rootprobe >"$o/apk-path.txt"
grep -q '^package:' "$o/apk-path.txt"
python3 experiments/android-root-probe/ci/device-diagnostic-ui.py
adb shell su -c 'ip -4 rule show' >"$o/rules-after.txt"
adb shell su -c 'ip -4 route show table all' >"$o/routes-after.txt"
cmp "$o/rules-before.txt" "$o/rules-after.txt"
cmp "$o/routes-before.txt" "$o/routes-after.txt"
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path("out/device-diag")
r=json.load(open(p/"device-report.json"))
m=json.load(open("out/diag/manifest.json"))
errors=[]
def need(ok,msg):
 if not ok:errors.append(msg)
need(r.get("source")==os.environ["GITHUB_SHA"] and m.get("source")==os.environ["GITHUB_SHA"],"SOURCE mismatch")
need(r.get("target_sdk")==37 and r.get("sdk")==36,"wrong Android target/runtime")
need(r.get("native_lib_present") is True,"APK did not extract bundled native binary")
need(r.get("root_verified") is True,"no true App->Root UID0 evidence")
need(r.get("core_ipv4_eligibility")=="CORE_IPV4_ROOT_PROBE_PASS","not actual TUN/raw core pass")
need(r.get("production_wifi_usb_vpn")=="NOT_RUN","misrepresented physical tether as passed")
cases={x["id"]:x for x in r.get("tests",[])}
for case in ("app_su","cap_net_admin","cap_net_raw","tun","raw_tcp","android_split_policy","android_split_uid_kernel","synthetic_tether_nat"):
 need(cases.get(case,{}).get("status")=="PASS",f"missing real {case} pass")
for case in ("ipv6_tun","policy_route"):
 need(cases.get(case,{}).get("status") in ("PASS","ENV_BLOCKED"),f"unclassified {case} outcome")
for case in ("physical_wifi_hotspot","physical_usb_tether","offload_bypass","production_wbd"):
 need(cases.get(case,{}).get("status")=="NOT_RUN",f"false positive {case}")
need("nativeLibraryDir" in str(cases.get("app_su",{}).get("evidence",{})) or
     "/libwbdprobe.so" in str(cases.get("app_su",{}).get("evidence",{})),
     "no native-in-APK execution path")
need((p/"rules-before.txt").read_text()==(p/"rules-after.txt").read_text(),"Android rules changed")
need((p/"routes-before.txt").read_text()==(p/"routes-after.txt").read_text(),"Android routes changed")
d={"schema":"android-real-ksu-self-contained-root-diagnostic/v1",
   "source":os.environ["GITHUB_SHA"],
   "status":"EMBEDDED_APK_DEVICE_DIAGNOSTIC_PASS" if not errors else "FAIL",
   "sdk":36,"target_sdk":37,
   "embedded_native_abi":r.get("abi"),"app_uid":r.get("app_uid"),
   "root_verified":r.get("root_verified"),
   "core_ipv4":r.get("core_ipv4_eligibility"),
   "ipv6_tun":cases.get("ipv6_tun",{}).get("status"),
   "policy_route":cases.get("policy_route",{}).get("status"),
   "synthetic_tether_nat":cases.get("synthetic_tether_nat",{}).get("status"),
   "android_split_policy":cases.get("android_split_policy",{}).get("status"),
   "android_split_uid_kernel":cases.get("android_split_uid_kernel",{}).get("status"),
   "physical_wifi_usb":"NOT_RUN","errors":errors}
(p/"summary.json").write_text(json.dumps(d,indent=2)+"\n")
print(json.dumps(d,indent=2))
if errors:raise SystemExit("embedded Android diagnostic App gate failed")
PY
