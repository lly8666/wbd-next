#!/usr/bin/env bash
# Cold boot real KernelSU twice; do NOT invoke adb root. KSU's --allow-shell is a CI preflight only.
set -euo pipefail
# Unlike android-emulator-runner, our manually booted KSU AVD does not inject adb into PATH.
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export ANDROID_AVD_HOME="$GITHUB_WORKSPACE/out/ksu/avd-home"
test -s "$ANDROID_AVD_HOME/wbd_ksu36.ini"
"$ANDROID_HOME/emulator/emulator" -list-avds | grep -qx wbd_ksu36
cd "$GITHUB_WORKSPACE"
mkdir -p out/ksu out/appcase
emulator="$ANDROID_HOME/emulator/emulator"
rooted="$GITHUB_WORKSPACE/out/ksu/patched-ramdisk.img"
# Pre-generate and serve a stable CI-only ADB key BEFORE launching Play Store AVD.
# This configures the emulator control channel; it is NOT app Root authorization.
mkdir -p "$HOME/.android"
if [[ ! -s "$HOME/.android/adbkey" ]]; then
  adb keygen "$HOME/.android/adbkey" >out/ksu/adb-keygen.txt 2>&1
fi
adb start-server >out/ksu/adb-server-start.txt 2>&1
adb devices -l >out/ksu/adb-devices-initial.txt
EMU_PID=""
cleanup() {
  adb emu kill >/dev/null 2>&1 || true
  if [[ -n "$EMU_PID" ]];then
    kill "$EMU_PID" >/dev/null 2>&1 || true
    wait "$EMU_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
start_avd() {
  local phase="$1"
  "$emulator" -avd wbd_ksu36 -ramdisk "$rooted" \
    -no-snapshot-load -no-snapshot-save -no-window -no-audio -no-boot-anim \
    -gpu swiftshader_indirect -accel on -memory 3072 \
    >"out/ksu/emulator-$phase.log" 2>&1 &
  EMU_PID=$!
  # Avoid 300-second opaque wait on "device unauthorized".
  local authorized=0
  for n in $(seq 1 90); do
    adb devices -l >"out/ksu/adb-devices-$phase.txt" 2>&1 || true
    if grep -Eq 'emulator-[0-9]+[[:space:]]+device([[:space:]]|$)' "out/ksu/adb-devices-$phase.txt"; then
      authorized=1
      break
    fi
    if grep -Eq 'emulator-[0-9]+[[:space:]]+unauthorized' "out/ksu/adb-devices-$phase.txt"; then
      printf '%s\n' "ADB_UNAUTHORIZED on $phase at $n" >"out/ksu/adb-unauthorized-$phase.txt"
    fi
    if ! kill -0 "$EMU_PID" 2>/dev/null; then
      tail -n 100 "out/ksu/emulator-$phase.log"
      echo "ENV_BLOCKED: emulator process exited before ADB online"
      exit 3
    fi
    sleep 2
  done
  if [[ "$authorized" != 1 ]]; then
    echo "ENV_BLOCKED: ADB never reached authorized 'device' on $phase; never confuse with KSU app authorization"
    tail -n 90 "out/ksu/emulator-$phase.log"
    exit 3
  fi
  local booted=0
  for n in $(seq 1 140);do
    if [[ "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1 ]];then booted=1;break;fi
    sleep 2
  done
  if [[ "$booted" != 1 ]];then
    echo "ENV_BLOCKED: patched AVD boot failed in phase $phase"
    tail -n 90 "out/ksu/emulator-$phase.log"
    exit 3
  fi
  adb shell getenforce >"out/ksu/enforce-$phase.txt"
  adb shell uname -r >"out/ksu/kernel-$phase.txt"
  adb shell getprop ro.build.version.sdk >"out/ksu/api-$phase.txt"
  test "$(tr -d '\r' <"out/ksu/api-$phase.txt")" = 36
  test "$(tr -d '\r' <"out/ksu/enforce-$phase.txt")" = Enforcing
}
start_avd first
adb install -r out/ksu/manager.apk >out/ksu/install-manager.txt
adb shell pm path me.weishu.kernelsu >out/ksu/manager-pm-first.txt 2>&1 || true
adb shell pm list packages | grep -E 'kernelsu|rootprobe' >out/ksu/packages-first.txt || true
adb shell ls -l /data/adb /data/adb/ksud /system/bin/su /system/xbin/su >out/ksu/ksu-paths-first.txt 2>&1 || true
adb shell cat /proc/modules | grep -Ei 'kernelsu|ksu' >out/ksu/modules-first.txt 2>&1 || true
adb install -r out/apk/app-su.apk >out/ksu/install-test-app.txt
adb shell monkey -p me.weishu.kernelsu -c android.intent.category.LAUNCHER 1 >out/ksu/first-manager-launch.txt 2>&1 || true
sleep 5
adb emu kill >out/ksu/first-cold-stop.txt 2>&1 || true
wait "$EMU_PID" >/dev/null 2>&1 || true
for n in $(seq 1 40);do
  if ! adb devices | grep -q 'emulator-.*device';then break;fi
  sleep 1
done
start_avd second
adb shell pm path me.weishu.kernelsu >out/ksu/manager-pm-second-before.txt 2>&1 || true
adb shell pm list packages -u | grep -E 'kernelsu|rootprobe' >out/ksu/packages-second-all.txt || true
adb shell ls -l /data/adb /data/adb/ksud /system/bin/su /system/xbin/su >out/ksu/ksu-paths-second.txt 2>&1 || true
adb shell cat /proc/modules | grep -Ei 'kernelsu|ksu' >out/ksu/modules-second.txt 2>&1 || true
# If the manager was removed during cold boot, reinstall the same already SHA-verified
# official APK (not fake su), and check once. Real KSU kernel must independently work.
if ! grep -q '^package:' out/ksu/manager-pm-second-before.txt; then
  adb install -r out/ksu/manager.apk >out/ksu/reinstall-manager-second.txt
  adb shell pm path me.weishu.kernelsu >out/ksu/manager-pm-after-reinstall.txt 2>&1 || true
  adb shell am start -n me.weishu.kernelsu/me.weishu.kernelsu.ui.MainActivity >out/ksu/manager-second-launch.txt 2>&1 || true
  sleep 3
fi
adb shell su -c id >out/ksu/fixture-shell-su.txt 2>&1 || true
adb shell su -c '/data/adb/ksud debug info' >out/ksu/ksud-debug-info.txt 2>&1 || true
adb shell pm list packages | grep -E 'kernelsu|rootprobe' >out/ksu/packages.txt || true
adb shell getprop ro.build.type >out/ksu/build-type-second.txt
adb shell getprop ro.build.fingerprint >out/ksu/build-fingerprint-second.txt
# Trigger a real app request before explicitly granting ONLY our app in the manager UI.
adb shell am start -n org.wbdnext.rootprobe/.ProbeActivity >out/ksu/initial-app-launch.txt
sleep 5
python3 experiments/android-root-probe/ci/ksu-grant-ui.py
# Previous KSU root-generated TUN/raw PASS is source-locked and not rerun here.
# Prove the missing link: actual untrusted App DatagramSocket -> owned TUN.
bash experiments/android-root-probe/ci/appflow-case.sh
python3 - <<'PY'
import json,os,hashlib
from pathlib import Path
p=Path("out/ksu")
s=json.loads(Path("out/appflow/summary.json").read_text())
d={"schema":"android-ksu-real-app-uid-tun/v1",
"source":os.environ["GITHUB_SHA"],
"manager":"real KernelSU v3.3.1 on ephemeral Android16 API36 x86_64 AVD",
"manager_sha256":"b4a059ace71de2fa65cc7f12b1c58d55fc23ab25e057ee4230ce779742abe450",
"ksud_info":(p/"ksud-debug-info.txt").read_text(errors="replace")[:1200],
"patched_ramdisk_sha256":hashlib.sha256((p/"patched-ramdisk.img").read_bytes()).hexdigest(),
"app_uid":s.get("app_uid"),"status":s["status"],
"app_origin_udp_captured":s["status"]=="APP_UID_TUN_ROUNDTRIP_PASS",
"netd_nat_hotspot_usb":"NOT_RUN",
"scope":"one exact UID and one synthetic /32 temporary policy rule, AVD only"}
(p/"summary.json").write_text(json.dumps(d,indent=2,sort_keys=True))
if not d["app_origin_udp_captured"]:raise SystemExit("ordinary App-origin UDP TUN test failed")
PY
