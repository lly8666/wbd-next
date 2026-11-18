#!/usr/bin/env bash
# x86_64 Android16 real KernelSU host admission and exact original Go/Rust
# native help. No pretend TLS/M4/APP->su claims: this is D1 PARTIAL only.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export ANDROID_AVD_HOME="$GITHUB_WORKSPACE/out/ksu/avd-home"
out=out/android-x86-ksu-native
mkdir -p "$out"
phase=PREFLIGHT
EMU_PID=""
adb(){ timeout --signal=TERM --kill-after=3s 35s "$ANDROID_HOME/platform-tools/adb" "$@"; }
receipt(){
  local rc="$1"
  export WBD_X86_KSU_PHASE="$phase" WBD_X86_KSU_EXIT="$rc"
  python3 - <<'PY'
import os,json,pathlib
out=pathlib.Path("out/android-x86-ksu-native")
def read(n):
  p=out/n
  return p.read_text(errors="replace") if p.exists() else ""
d={"schema":"wbd-android-x86-kvm-ksu-original-native-d1-admission/v1",
 "source":os.environ["GITHUB_SHA"],"phase":os.environ["WBD_X86_KSU_PHASE"],
 "exit_code":int(os.environ["WBD_X86_KSU_EXIT"]),
 "guest_kernel_x86_64":"PASS" if read("uname.txt").strip()=="x86_64" else "NOT_PROVEN",
 "android_api36":"PASS" if read("sdk.txt").strip()=="36" else "NOT_PROVEN",
 "ksu_shell_root":"PASS" if "uid=0(" in read("ksu-id.txt") else "NOT_PROVEN",
 "original_x86_go_help":"PASS" if read("go-help-code.txt").strip()=="1" and
   "Usage of wbd-v4-client:" in read("go-help.txt") and
   "flag: help requested" in read("go-help.txt") and
   all(flag in read("go-help.txt") for flag in
       ("-android-network-handle","-raw-interface","-tun-name","-username")) and
   "panic:" not in read("go-help.txt") and
   "fatal error:" not in read("go-help.txt") else "NOT_PROVEN",
 "signed_ci_apk_activity":"PASS" if "Starting: Intent" in read("activity.txt") else "NOT_PROVEN",
 "app_to_ksu_root":"NOT_RUN","physical_network_app_readback":"NOT_RUN",
 "original_tls_auth_lease":"NOT_RUN","real_m3_m4_tcp_udp":"NOT_RUN",
 "owned_stop_route_rollback":"NOT_RUN",
 "system_dns_takeover":"NOT_RUN"}
(out/"receipt.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print("ANDROID_X86_KSU_ORIGINAL_NATIVE_D1_ADMISSION",d["original_x86_go_help"],d["phase"])
PY
}
cleanup(){
  local rc=$?
  trap - EXIT
  receipt "$rc" || true
  if test -n "$EMU_PID";then
    timeout 10s "$ANDROID_HOME/platform-tools/adb" emu kill >"$out/guest-cleanup.txt" 2>&1 || true
    kill -TERM "$EMU_PID" 2>/dev/null || true
    for _ in $(seq 1 20);do
      if ! kill -0 "$EMU_PID" 2>/dev/null;then break;fi
      sleep 0.2
    done
    kill -KILL "$EMU_PID" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
test -c /dev/kvm
test -s out/ksu/patched-ramdisk.img
test -s out/ksu/manager.apk
test "$(cat out/android-root-app-native/SOURCE)" = "$GITHUB_SHA"
test "$(cat out/android-x86-ci-app/SOURCE)" = "$GITHUB_SHA"
(cd out/android-root-app-native && sha256sum -c SHA256SUMS) >"$out/native-sha.txt"
(cd out/android-x86-ci-app && sha256sum -c SHA256SUMS) >"$out/apk-sha.txt"
apk=out/android-x86-ci-app/wbd-root-x86-ci-only.apk
unzip -p "$apk" assets/native-amd64/wbd-v4-client-amd64 >"$out/apk-go"
unzip -p "$apk" assets/native-amd64/libwbd_engine-amd64.so >"$out/apk-rust.so"
cmp "$out/apk-go" out/android-root-app-native/wbd-v4-client-amd64
cmp "$out/apk-rust.so" out/android-root-app-native/libwbd_engine-amd64.so
readelf -h "$out/apk-go" >"$out/go-elf.txt"
grep -q 'Advanced Micro Devices X86-64' "$out/go-elf.txt"
readelf -d "$out/apk-go" >"$out/go-linker.txt"
grep -Fq 'Shared library: [libwbd_engine.so]' "$out/go-linker.txt"
grep -Eq 'Library runpath: \[\$ORIGIN(:\$ORIGIN)*\]' "$out/go-linker.txt"
mkdir -p "$HOME/.android"
if [[ ! -s "$HOME/.android/adbkey" ]];then
  adb keygen "$HOME/.android/adbkey" >"$out/adb-key.txt" 2>&1
fi
adb start-server >"$out/adb-server.txt" 2>&1
emulator="$ANDROID_HOME/emulator/emulator"
start_guest(){
  local stage="$1"
  "$emulator" -avd wbd_ksu36 -ramdisk "$GITHUB_WORKSPACE/out/ksu/patched-ramdisk.img" \
     -no-snapshot-load -no-snapshot-save -no-window -no-audio -no-boot-anim \
     -gpu swiftshader_indirect -accel on -memory 3072 \
     >"$out/emulator-$stage.log" 2>&1 &
  EMU_PID=$!
  local t
  for t in $(seq 1 100);do
    adb devices -l >"$out/devices-$stage.txt" 2>&1 || true
    if grep -Eq 'emulator-[0-9]+[[:space:]]+device([[:space:]]|$)' "$out/devices-$stage.txt";then break;fi
    if ! kill -0 "$EMU_PID" 2>/dev/null;then
      echo "ENV_BLOCKED AVD_EXITED_BEFORE_ADB" >&2;exit 12
    fi
    sleep 2
  done
  grep -Eq 'emulator-[0-9]+[[:space:]]+device([[:space:]]|$)' "$out/devices-$stage.txt" || {
    echo "ENV_BLOCKED ADB_UNAVAILABLE" >&2;exit 13;
  }
  for t in $(seq 1 110);do
    if [[ "$(adb shell getprop sys.boot_completed | tr -d '\r')" == 1 ]] &&
       adb shell pm path android 2>&1 | grep -q '^package:';then break;fi
    if ! kill -0 "$EMU_PID" 2>/dev/null;then
      echo "ENV_BLOCKED AVD_DIED_DURING_BOOT" >&2;exit 14
    fi
    sleep 2
  done
  test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1
  adb shell pm path android | grep -q '^package:'
  test "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = 36
  test "$(adb shell getenforce | tr -d '\r')" = Enforcing
}
phase=FIRST_KSU_BOOT
start_guest first
adb install -r out/ksu/manager.apk >"$out/install-manager.txt"
adb install -r "$apk" >"$out/install-ci-app.txt"
adb shell pm path org.wbdnext.rootclient >"$out/ci-app-pm.txt"
grep -q '^package:' "$out/ci-app-pm.txt"
adb shell monkey -p me.weishu.kernelsu -c android.intent.category.LAUNCHER 1 \
  >"$out/manager-first.txt" 2>&1 || true
sleep 4
adb emu kill >"$out/first-stop.txt" 2>&1 || true
for t in $(seq 1 45);do
  if ! adb devices | grep -q 'emulator-.*device';then break;fi
  sleep 1
done
phase=SECOND_KSU_BOOT
start_guest second
if ! adb shell pm path me.weishu.kernelsu | grep -q '^package:';then
  adb install -r out/ksu/manager.apk >"$out/reinstall-manager.txt"
fi
if ! adb shell pm path org.wbdnext.rootclient | grep -q '^package:';then
  adb install -r "$apk" >"$out/reinstall-ci-app.txt"
fi
adb shell am start -n me.weishu.kernelsu/me.weishu.kernelsu.ui.MainActivity \
  >"$out/manager-second.txt" 2>&1
for t in $(seq 1 50);do
  adb shell su -c id >"$out/ksu-id.txt" 2>&1 || true
  if grep -q 'uid=0(' "$out/ksu-id.txt";then break;fi
  sleep 2
done
grep -q 'uid=0(' "$out/ksu-id.txt"
adb shell uname -m >"$out/uname.txt"
adb shell getprop ro.build.version.sdk >"$out/sdk.txt"
test "$(tr -d '\r' <"$out/uname.txt")" = x86_64
adb shell am start -n org.wbdnext.rootclient/.RootClientActivity \
  >"$out/activity.txt" 2>&1
grep -q 'Starting: Intent' "$out/activity.txt"
phase=ORIGINAL_X86_NATIVE_GO_ELF_HELP
adb push "$out/apk-go" /data/local/tmp/wbd-x86-ci-go.stage >"$out/push-go.txt"
adb push "$out/apk-rust.so" /data/local/tmp/wbd-x86-ci-rust.stage >"$out/push-rust.txt"
adb shell su -c 'set -eu; umask 077; p=/data/local/tmp/wbd-x86-ci; test ! -e "$p"; mkdir -m 700 "$p"; test "$(stat -c %u "$p")" = 0; cp /data/local/tmp/wbd-x86-ci-go.stage "$p/wbd-v4-client-amd64"; cp /data/local/tmp/wbd-x86-ci-rust.stage "$p/libwbd_engine.so"; chmod 700 "$p/wbd-v4-client-amd64"; chmod 600 "$p/libwbd_engine.so"' \
  >"$out/stage.txt" 2>&1
sha_go="$(sha256sum "$out/apk-go" | cut -d ' ' -f1)"
sha_rust="$(sha256sum "$out/apk-rust.so" | cut -d ' ' -f1)"
adb shell su -c 'sha256sum /data/local/tmp/wbd-x86-ci/wbd-v4-client-amd64 /data/local/tmp/wbd-x86-ci/libwbd_engine.so' \
  >"$out/device-sha.txt"
grep -Fq "$sha_go" "$out/device-sha.txt"
grep -Fq "$sha_rust" "$out/device-sha.txt"
set +e
adb shell su -c '/data/local/tmp/wbd-x86-ci/wbd-v4-client-amd64 --help' \
  >"$out/go-help.txt" 2>&1
code=$?
set -e
echo "$code" >"$out/go-help-code.txt"
# The ORIGINAL pinned Go CLI returns flag.ErrHelp to main, which calls
# log.Fatal and exits 1 after printing its complete real flag set.
# Only admit this exact help receipt, not an arbitrary exec error with rc 1.
if [[ "$code" != 1 ]] ||
   ! grep -Fq 'Usage of wbd-v4-client:' "$out/go-help.txt" ||
   ! grep -Fq 'flag: help requested' "$out/go-help.txt" ||
   ! grep -Fq 'android-network-handle' "$out/go-help.txt" ||
   ! grep -Fq 'raw-interface' "$out/go-help.txt" ||
   ! grep -Fq 'tun-name' "$out/go-help.txt" ||
   ! grep -Fq 'username' "$out/go-help.txt" ||
   grep -Eq 'panic:|fatal error:' "$out/go-help.txt";then
  echo "ANDROID_X86_ORIGINAL_GO_ELF_HELP_FAIL rc=$code" >&2
  exit 17
fi
echo "ANDROID_X86_ORIGINAL_GO_ELF_HELP_PASS"
echo "D1_APP_SU_AND_TLS_M4_NOT_RUN"
