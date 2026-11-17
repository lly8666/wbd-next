#!/usr/bin/env bash
# Exact ARM64 WBD product inside historical x86_64 KVM + KernelSU API36 AVD.
# "NativeBridge available" is NOT proof of execve(AArch64 ELF); execute it.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test -n "$GITHUB_SHA"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export ANDROID_AVD_HOME="$GITHUB_WORKSPACE/out/ksu/avd-home"
dir=out/android-ksu-arm64
mkdir -p "$dir"
adb(){ timeout --signal=TERM --kill-after=2s 28s "$ANDROID_HOME/platform-tools/adb" "$@"; }
emu_pid=""
phase="PREPARED"
cleanup(){
  local exit_rc=$?
  trap - EXIT
  set +e
  export WBD_EXIT_CODE="$exit_rc" WBD_PHASE="$phase"
  python3 - <<'PY'
import json,os,pathlib
root=pathlib.Path("out/android-ksu-arm64")
def txt(name):
    p=root/name
    return p.read_text(errors="replace").strip()[:8000] if p.exists() else ""
uid=txt("ksu-shell-id.txt")
execout=txt("arm64-exec.txt")
app=txt("app-launch.txt")
def probe_ok(output,exitfile,marker):
    return "PASS" if txt(exitfile)=="0" and marker in txt(output) else "NOT_PROVEN"
d={
 "schema":"wbd-android-kvm-x86_64-ksu-arm64-nativebridge-product/v1",
 "source":os.environ["GITHUB_SHA"],
 "phase":os.environ["WBD_PHASE"],
 "exit_code":int(os.environ["WBD_EXIT_CODE"]),
 "guest_arch":txt("guest-uname.txt"),
 "android_api":txt("guest-api.txt"),
 "ksu_root_shell":"PASS" if "uid=0(" in uid else "NOT_PROVEN",
 "ksu_app_su":"NOT_RUN",
 "selinux":txt("getenforce.txt"),
 "native_bridge_props":txt("native-bridge.txt"),
 "arm64_ndk_min_exec":probe_ok("ndk-min-exec.txt","ndk-min-exit-code.txt","WBD_ANDROID_ARM64_NDK_MIN_EXEC_PASS"),
 "arm64_pure_go_runtime":probe_ok("go-min-exec.txt","go-min-exit-code.txt","WBD_ANDROID_ARM64_PURE_GO_RUNTIME_PASS"),
 "arm64_rust_dlopen":probe_ok("rust-dlopen.txt","rust-dlopen-exit-code.txt","WBD_ANDROID_ARM64_RUST_DLOPEN_PASS"),
 "arm64_pure_go_tuned":probe_ok("go-min-tuned-exec.txt","go-min-tuned-exit-code.txt","WBD_ANDROID_ARM64_PURE_GO_RUNTIME_PASS"),
 "arm64_go_cshared":probe_ok("go-cshared-exec.txt","go-cshared-exit-code.txt","WBD_ANDROID_ARM64_GO_CSHARED_CALL_PASS"),
 "arm64_go_midr_isolate":probe_ok("go-midr-exec.txt","go-midr-exit-code.txt","WBD_ANDROID_ARM64_PURE_GO_RUNTIME_PASS"),
 "arm64_go_cshared_midr_isolate":probe_ok("go-cshared-midr-exec.txt","go-cshared-midr-exit-code.txt","WBD_ANDROID_ARM64_GO_CSHARED_CALL_PASS"),
 "arm64_native_exec":"PASS" if txt("arm64-exit-code.txt")=="0" and "ANDROID_AARCH64_GO_RUNTIME_STARTED" in execout else "NOT_PROVEN",
 "arm64_native_exit_code":txt("arm64-exit-code.txt"),
 "product_app_launch":"PASS" if "ACTIVITY_STARTED" in app else "NOT_PROVEN",
 "wbd_android_linux_tls_auth_lease":"NOT_RUN",
 "wbd_app_dns_tcp_udp_stop":"NOT_RUN",
 "android_arm64_physical_device":"NOT_RUN"
}
(root/"receipt.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print("ANDROID_KSU_ARM64_NATIVEBRIDGE_RECEIPT",d["ksu_root_shell"],d["arm64_native_exec"],d["phase"])
PY
  adb emu kill >"$dir/adb-emu-kill.txt" 2>&1 || true
  if [[ -n "$emu_pid" ]];then
    kill -TERM "$emu_pid" 2>/dev/null || true
    for _ in $(seq 1 15);do
      kill -0 "$emu_pid" 2>/dev/null || break
      sleep 0.2
    done
    kill -KILL "$emu_pid" 2>/dev/null || true
  fi
  exit "$exit_rc"
}
trap cleanup EXIT
test -s out/ksu/patched-ramdisk.img
test -s out/ksu/manager.apk
test -s out/android-root-app-native/wbd-v4-client-arm64
test -s out/android-root-app-native/libwbd_engine-arm64.so
# Test-only ARM64 executables built by the exact product SOURCE job;
# they are never shipped in the official APK or treated as WBD success.
test -s out/android-root-app-native/ksu-arm64-ndk-probe
test -s out/android-root-app-native/ksu-arm64-go-probe
test -s out/android-root-app-native/libksu-arm64-go-cshared-probe.so
test -s out/android-root-app-native/ksu-arm64-go-midr-isolate
test -s out/android-root-app-native/libksu-arm64-go-cshared-midr-isolate.so
test -s out/android-root-app-native/ksu-go-midrel1-isolation.json
test -s out/android-root-app/wbd-root-arm64-debug.apk
test "$(cat out/android-root-app-native/SOURCE)" = "$GITHUB_SHA"
test "$(cat out/android-root-app/SOURCE)" = "$GITHUB_SHA"
(cd out/android-root-app-native && sha256sum -c SHA256SUMS) >"$dir/source-verify.txt"
(cd out/android-root-app && sha256sum -c SHA256SUMS) >>"$dir/source-verify.txt"
unzip -p out/android-root-app/wbd-root-arm64-debug.apk \
  assets/native-arm64/wbd-v4-client-arm64 >"$dir/apk-go-arm64"
unzip -p out/android-root-app/wbd-root-arm64-debug.apk \
  assets/native-arm64/libwbd_engine-arm64.so >"$dir/apk-rust-arm64.so"
cmp "$dir/apk-go-arm64" out/android-root-app-native/wbd-v4-client-arm64
cmp "$dir/apk-rust-arm64.so" out/android-root-app-native/libwbd_engine-arm64.so
# Real ARM64 binary must discover the exact Rust .so beside itself under
# KernelSU. Source-lock the actual ELF's DT_NEEDED and $ORIGIN RUNPATH,
# not merely its compiler flag or the Android ABI marketing string.
readelf -d out/android-root-app-native/wbd-v4-client-arm64 \
  >"$dir/elf-dynamic-linker.txt"
grep -Fq 'Shared library: [libwbd_engine.so]' "$dir/elf-dynamic-linker.txt"
grep -Eq 'Library runpath: \[\$ORIGIN(:\$ORIGIN)*\]' "$dir/elf-dynamic-linker.txt"
python3 - <<'PY'
from pathlib import Path
import struct
for f in ("apk-go-arm64","apk-rust-arm64.so"):
    raw=(Path("out/android-ksu-arm64")/f).read_bytes()
    assert raw[:5]==b"\x7fELF\x02" and struct.unpack_from("<H",raw,18)[0]==183,f
print("KSU_EXACT_SOURCE_AND_AARCH64_ELF_ASSETS_PASS")
PY
test -c /dev/kvm
mkdir -p "$HOME/.android"
if [[ ! -s "$HOME/.android/adbkey" ]];then
  adb keygen "$HOME/.android/adbkey" >"$dir/adb-keygen.txt" 2>&1
fi
adb start-server >"$dir/adb-server.txt" 2>&1
emulator="$ANDROID_HOME/emulator/emulator"
start_guest(){
  local name="$1"
  "$emulator" -avd wbd_ksu36 -ramdisk "$GITHUB_WORKSPACE/out/ksu/patched-ramdisk.img" \
    -no-snapshot-load -no-snapshot-save -no-window -no-audio -no-boot-anim \
    -gpu swiftshader_indirect -accel on -memory 3072 \
    >"$dir/emulator-$name.log" 2>&1 &
  emu_pid=$!
  local end=$((SECONDS+145))
  until adb devices -l >"$dir/adb-$name.txt" 2>&1 &&
    grep -Eq 'emulator-[0-9]+[[:space:]]+device([[:space:]]|$)' "$dir/adb-$name.txt";do
    if ! kill -0 "$emu_pid" 2>/dev/null;then
      echo "ENV_BLOCKED: KSU emulator exited before ADB" >&2
      tail -n 90 "$dir/emulator-$name.log"
      return 1
    fi
    if ((SECONDS>=end));then
      echo "ENV_BLOCKED: KSU emulator never authorized ADB" >&2
      return 1
    fi
    sleep 2
  done
  end=$((SECONDS+210))
  while [[ "$(adb shell getprop sys.boot_completed | tr -d '\r')" != 1 ]];do
    if ((SECONDS>=end));then
      echo "ENV_BLOCKED: KSU AVD did not boot Android16" >&2
      tail -n 90 "$dir/emulator-$name.log"
      return 1
    fi
    sleep 2
  done
  end=$((SECONDS+95))
  while ! adb shell pm path android 2>&1 | grep -q '^package:';do
    if ((SECONDS>=end));then
      echo "ENV_BLOCKED: Android PackageManager absent" >&2
      return 1
    fi
    sleep 2
  done
  adb shell getprop ro.build.version.sdk | tr -d '\r' >"$dir/guest-api.txt"
  adb shell uname -m | tr -d '\r' >"$dir/guest-uname.txt"
  adb shell getenforce | tr -d '\r' >"$dir/getenforce.txt"
  test "$(cat "$dir/guest-api.txt")" = 36
  test "$(cat "$dir/guest-uname.txt")" = x86_64
  test "$(cat "$dir/getenforce.txt")" = Enforcing
}
phase="FIRST_KSU_ANDROID16_BOOT"
start_guest first
adb install -r out/ksu/manager.apk >"$dir/install-manager.txt"
adb install -r out/android-root-app/wbd-root-arm64-debug.apk >"$dir/install-app.txt"
adb shell pm path me.weishu.kernelsu >"$dir/manager-package.txt"
adb shell pm path org.wbdnext.rootclient >"$dir/product-package.txt"
grep -q '^package:' "$dir/manager-package.txt"
grep -q '^package:' "$dir/product-package.txt"
adb shell monkey -p me.weishu.kernelsu -c android.intent.category.LAUNCHER 1 \
  >"$dir/manager-first-launch.txt" 2>&1 || true
adb emu kill >"$dir/first-cold-stop.txt" 2>&1 || true
kill -TERM "$emu_pid" 2>/dev/null || true
for _ in $(seq 1 45);do
  kill -0 "$emu_pid" 2>/dev/null || break
  sleep 0.2
done
kill -KILL "$emu_pid" 2>/dev/null || true
emu_pid=""
phase="SECOND_KSU_ANDROID16_BOOT"
start_guest second
if ! adb shell pm path me.weishu.kernelsu | grep -q '^package:';then
  adb install -r out/ksu/manager.apk >"$dir/reinstall-manager.txt"
fi
if ! adb shell pm path org.wbdnext.rootclient | grep -q '^package:';then
  adb install -r out/android-root-app/wbd-root-arm64-debug.apk >"$dir/reinstall-product.txt"
fi
# KSU's real /system/bin/su is installed by the official Manager at
# second-boot startup. The known-good historical workflow explicitly
# re-launches MainActivity after reinstall; omitting that produced 127
# ("su: inaccessible or not found") in the first product gate, BEFORE any
# ARM64/NativeBridge syscall. Repeat exactly the proven init sequence.
adb shell am start -n me.weishu.kernelsu/me.weishu.kernelsu.ui.MainActivity \
  >"$dir/manager-second-launch.txt" 2>&1
ksu_ready=0
for _ in $(seq 1 18);do
  adb shell su -c id >"$dir/ksu-shell-id.txt" 2>&1 || true
  if grep -q 'uid=0(' "$dir/ksu-shell-id.txt";then
    ksu_ready=1
    break
  fi
  sleep 2
done
if [[ "$ksu_ready" != 1 ]];then
  echo "KSU_INIT_BLOCKED: official Manager did not provision real shell su after second boot" >&2
  cat "$dir/manager-second-launch.txt" "$dir/ksu-shell-id.txt" >&2
  exit 12
fi
adb shell su -c 'id -Z' >"$dir/ksu-shell-selinux.txt" 2>&1 || true
adb shell su -c 'cat /proc/self/status' >"$dir/ksu-capabilities.txt" 2>&1 || true
phase="NATIVEBRIDGE_ABI_AND_AARCH64_ELF_RUNTIME"
{
  echo "kernel=$(adb shell uname -m | tr -d '\r')"
  for key in ro.product.cpu.abilist ro.product.cpu.abilist64 \
      ro.dalvik.vm.native.bridge ro.enable.native.bridge.exec \
      ro.vendor.native_bridge;do
    printf '%s=%s\n' "$key" "$(adb shell getprop "$key" | tr -d '\r')"
  done
  adb shell 'ls -l /system/lib64/libndk_translation.so /system/lib64/libhoudini.so /apex/com.android.runtime/lib64/libndk_translation.so 2>&1' || true
  adb shell su -c 'ls -l /proc/sys/fs/binfmt_misc 2>&1' || true
} >"$dir/native-bridge.txt"
adb push out/android-root-app-native/wbd-v4-client-arm64 \
  /data/local/tmp/wbd-product-arm64 >"$dir/adb-push-arm64-go.txt"
adb push out/android-root-app-native/libwbd_engine-arm64.so \
  /data/local/tmp/libwbd_engine.so >"$dir/adb-push-arm64-rust.txt"
adb shell su -c 'chmod 755 /data/local/tmp/wbd-product-arm64; chmod 644 /data/local/tmp/libwbd_engine.so' \
  >"$dir/arm64-chmod.txt" 2>&1
local_hash="$(sha256sum out/android-root-app-native/wbd-v4-client-arm64 | cut -d ' ' -f1)"
remote_hash="$(adb shell su -c 'sha256sum /data/local/tmp/wbd-product-arm64' | tr -d '\r' | cut -d ' ' -f1)"
test "$local_hash" = "$remote_hash"
phase="NATIVEBRIDGE_LAYERED_ARM64_EXEC_DIAG"
adb push out/android-root-app-native/ksu-arm64-ndk-probe \
  /data/local/tmp/wbd-ndk-arm64-probe >"$dir/ndk-probe-push.txt"
adb push out/android-root-app-native/ksu-arm64-go-probe \
  /data/local/tmp/wbd-go-arm64-probe >"$dir/go-probe-push.txt"
adb push out/android-root-app-native/libksu-arm64-go-cshared-probe.so \
  /data/local/tmp/libwbd-go-cshared-test.so >"$dir/go-cshared-push.txt"
adb push out/android-root-app-native/ksu-arm64-go-midr-isolate \
  /data/local/tmp/wbd-go-arm64-midr-isolate >"$dir/go-midr-push.txt"
adb push out/android-root-app-native/libksu-arm64-go-cshared-midr-isolate.so \
  /data/local/tmp/libwbd-go-cshared-midr-isolate.so >"$dir/go-cshared-midr-push.txt"
adb shell su -c 'chmod 755 /data/local/tmp/wbd-ndk-arm64-probe /data/local/tmp/wbd-go-arm64-probe /data/local/tmp/wbd-go-arm64-midr-isolate; chmod 644 /data/local/tmp/libwbd-go-cshared-test.so /data/local/tmp/libwbd-go-cshared-midr-isolate.so' \
  >"$dir/probe-chmod.txt" 2>&1
# Each result is a real Bionic/NativeBridge process. Every probe is
# independent; never short-circuit before the original WBD execution.
set +e
adb shell su -c '/data/local/tmp/wbd-ndk-arm64-probe --self' >"$dir/ndk-min-exec.txt" 2>&1
ndkrc=$?
adb shell su -c '/data/local/tmp/wbd-go-arm64-probe' >"$dir/go-min-exec.txt" 2>&1
gorc=$?
adb shell su -c '/data/local/tmp/wbd-ndk-arm64-probe --dlopen /data/local/tmp/libwbd_engine.so' >"$dir/rust-dlopen.txt" 2>&1
rustrc=$?
adb shell su -c 'GODEBUG=asyncpreemptoff=1 GOMAXPROCS=1 /data/local/tmp/wbd-go-arm64-probe' \
  >"$dir/go-min-tuned-exec.txt" 2>&1
gotunedrc=$?
adb shell su -c '/data/local/tmp/wbd-ndk-arm64-probe --go-shared /data/local/tmp/libwbd-go-cshared-test.so' \
  >"$dir/go-cshared-exec.txt" 2>&1
gosharedrc=$?
adb shell su -c '/data/local/tmp/wbd-go-arm64-midr-isolate' >"$dir/go-midr-exec.txt" 2>&1
gomidrrc=$?
adb shell su -c '/data/local/tmp/wbd-ndk-arm64-probe --go-shared /data/local/tmp/libwbd-go-cshared-midr-isolate.so' >"$dir/go-cshared-midr-exec.txt" 2>&1
gosharedmidrrc=$?
set -e
printf '%s\n' "$ndkrc" >"$dir/ndk-min-exit-code.txt"
printf '%s\n' "$gorc" >"$dir/go-min-exit-code.txt"
printf '%s\n' "$rustrc" >"$dir/rust-dlopen-exit-code.txt"
printf '%s\n' "$gotunedrc" >"$dir/go-min-tuned-exit-code.txt"
printf '%s\n' "$gosharedrc" >"$dir/go-cshared-exit-code.txt"
printf '%s\n' "$gomidrrc" >"$dir/go-midr-exit-code.txt"
printf '%s\n' "$gosharedmidrrc" >"$dir/go-cshared-midr-exit-code.txt"
phase="ORIGINAL_ARM64_GO_RUST_EXEC_RUNTIME"
set +e
adb shell su -c 'LD_LIBRARY_PATH=/data/local/tmp /data/local/tmp/wbd-product-arm64 --help' \
  >"$dir/arm64-exec.txt" 2>&1
rc=$?
set -e
echo "$rc" >"$dir/arm64-exit-code.txt"
# The original Go may fail during executable startup; capture a real
# tombstone/crash buffer (no user credentials are supplied in this gate).
adb logcat -d -b crash -t 600 >"$dir/arm64-crash-logcat.txt" 2>&1 || true
adb logcat -d -t 800 >"$dir/arm64-recent-logcat.txt" 2>&1 || true
adb shell su -c 'ls -lt /data/tombstones' >"$dir/tombstone-list.txt" 2>&1 || true
adb shell su -c 'f=$(ls -t /data/tombstones/tombstone_* 2>/dev/null | head -1); test -n "$f" && head -n 220 "$f"' \
  >"$dir/latest-tombstone-excerpt.txt" 2>&1 || true
printf 'NDK_ARM64_EXIT=%s PURE_GO_ARM64_EXIT=%s RUST_DLOPEN_EXIT=%s PURE_GO_TUNED_EXIT=%s GO_CSHARED_EXIT=%s PURE_GO_MIDR_ISOLATE_EXIT=%s GO_CSHARED_MIDR_ISOLATE_EXIT=%s ORIGINAL_WBD_ARM64_EXIT=%s\n' \
  "$ndkrc" "$gorc" "$rustrc" "$gotunedrc" "$gosharedrc" "$gomidrrc" "$gosharedmidrrc" "$rc"
original_ready=0
if [[ "$rc" == 0 ]] &&
   grep -Eiq 'Usage of|Usage:|--peer-ip|peer-ip|--android-network-handle|android-network-handle' "$dir/arm64-exec.txt" &&
   ! grep -Eiq 'exec format|not executable|not found|failed to execute|bad ELF|Segmentation fault' "$dir/arm64-exec.txt";then
  echo "ANDROID_AARCH64_GO_RUNTIME_STARTED" >>"$dir/arm64-exec.txt"
  original_ready=1
else
  echo "ENV_BLOCKED_NATIVEBRIDGE_AARCH64_RAW_EXEC: original ARM64 WBD did not complete --help (exit $rc)" >&2
  cat "$dir/native-bridge.txt" >&2
  for f in ndk-min-exec.txt go-min-exec.txt rust-dlopen.txt go-min-tuned-exec.txt go-cshared-exec.txt go-midr-exec.txt go-cshared-midr-exec.txt arm64-exec.txt latest-tombstone-excerpt.txt;do
    echo "=== $f ===" >&2
    tail -n 85 "$dir/$f" >&2 || true
  done
fi
# Test the actual signed APK's Activity even when ARM64 Go runtime crashes;
# UI/AOSP PackageManager are independent evidence, NOT Go/TLS readiness.
phase="REAL_PRODUCT_APK_ACTIVITY"
adb shell am start -n org.wbdnext.rootclient/.RootClientActivity >"$dir/app-launch.txt" 2>&1
if grep -Eqi 'error|exception|permission denied' "$dir/app-launch.txt";then
  cat "$dir/app-launch.txt" >&2
  exit 11
fi
# ActivityManager returns "Starting" before Java onCreate; pidof may be
# empty until Zygote forks. Evidence requires an actual process, not just
# a successful shell command and a synthetic status flag.
app_ready=0
for _ in $(seq 1 20);do
  adb shell pidof org.wbdnext.rootclient >"$dir/app-process.txt" 2>&1 || true
  if grep -Eq '^[0-9]+([[:space:]][0-9]+)*$' "$dir/app-process.txt";then
    app_ready=1
    break
  fi
  sleep 1
done
adb shell dumpsys package org.wbdnext.rootclient >"$dir/app-package-dump.txt" 2>&1 || true
if [[ "$app_ready" != 1 ]];then
  adb logcat -d -t 800 >"$dir/app-logcat.txt" 2>&1 || true
  adb shell dumpsys activity activities >"$dir/app-activity-state.txt" 2>&1 || true
  echo "ANDROID_PRODUCT_ACTIVITY_FAILED_TO_START: no live process after accepted launch" >&2
  cat "$dir/app-launch.txt" "$dir/app-process.txt" >&2
  exit 11
fi
printf '\nACTIVITY_STARTED\n' >>"$dir/app-launch.txt"
if [[ "$original_ready" != 1 ]];then
  phase="ORIGINAL_ARM64_GO_RUNTIME_BLOCKED_APP_ACTIVITY_PROVEN"
  echo "ANDROID_REAL_APK_ACTIVITY_PASS_BUT_ORIGINAL_ARM64_GO_NOT_EXECUTABLE: device business NOT_RUN" >&2
  exit 10
fi
# Companion diagnostics never authorize the real protocol; negative results
# remain in the receipt and require their own review.
phase="KSU_ARM64_EXEC_AND_APK_ACTIVITY_PASS_P2_RUNTIME_ONLY"
echo "ANDROID_X86_KVM_REAL_KSU_ARM64_NATIVEBRIDGE_GO_RUNTIME_AND_APK_LAUNCH_PASS; APP_SU_AND_BUSINESS_NOT_RUN"
