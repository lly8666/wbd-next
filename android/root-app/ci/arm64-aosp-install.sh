#!/usr/bin/env bash
# Source-locked ARM64 AOSP APK install/Activity smoke only.
# This is NOT KernelSU/root/TUN/RAW/Android↔Linux protocol qualification.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
p=out/android-a3-guest
test "$(cat "$p/SOURCE")" = "$GITHUB_SHA"
python3 - <<'PY'
import hashlib,json,os,pathlib
p=pathlib.Path("out/android-a3-guest")
m=json.loads((p/"manifest.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
assert m["arm64_native_source"]==os.environ["GITHUB_SHA"]
assert m["platform"]=="Android ARM64-v8a ONLY"
assert m["no_vpn_service_manifest_verified"]
apk=p/"wbd-root-arm64-debug.apk"
assert apk.is_file()
assert hashlib.sha256(apk.read_bytes()).hexdigest()==m["apk_sha256"]
print("ANDROID_ARM64_AOSP_SAME_SOURCE_APK_HASH_VERIFIED")
PY
abi="$(adb shell getprop ro.product.cpu.abi | tr -d '\r')"
api="$(adb shell getprop ro.build.version.sdk | tr -d '\r')"
abilist="$(adb shell getprop ro.product.cpu.abilist | tr -d '\r')"
test "$abi" = arm64-v8a
test "$api" = 36
case "$abilist" in
  *x86*|*armeabi*) echo "WRONG_ANDROID_ABI" >&2; exit 1;;
esac
adb install -r "$p/wbd-root-arm64-debug.apk"
adb shell pm path org.wbdnext.rootclient >"$p/package-path.txt"
grep -Fq 'package:' "$p/package-path.txt"
adb shell am start -W -n org.wbdnext.rootclient/.RootClientActivity >"$p/activity-launch.txt"
grep -Fq 'Status: ok' "$p/activity-launch.txt"
adb shell dumpsys activity activities >"$p/activities-private.txt"
grep -Fq 'org.wbdnext.rootclient' "$p/activities-private.txt"
adb shell am force-stop org.wbdnext.rootclient
rm -f "$p/activities-private.txt"
export WBD_AOSP_ABI="$abi" WBD_AOSP_API="$api" WBD_AOSP_ABILIST="$abilist"
python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("out/android-a3-guest")
receipt={"schema":"android-arm64-aosp-apk-install-activity/v1",
 "source":os.environ["GITHUB_SHA"],
 "observed_android_abi":os.environ["WBD_AOSP_ABI"],
 "observed_android_abilist":os.environ["WBD_AOSP_ABILIST"],
 "observed_android_api":int(os.environ["WBD_AOSP_API"]),
 "signed_apk_install_and_activity":"PASS_REAL_ARM64_AOSP_GUEST",
 "root_su":"NOT_RUN","ksu":"NOT_RUN",
 "bionic_go_rust_load":"NOT_RUN",
 "android_to_linux_real_tls_tcp_udp":"NOT_RUN",
 "physical":"DEFERRED_ACTIONS_FIRST"}
(p/"guest-receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("ANDROID_ARM64_AOSP_GUEST_APP_LAUNCH_PASS_NO_KSU_NO_PRODUCT_E2E")
PY
