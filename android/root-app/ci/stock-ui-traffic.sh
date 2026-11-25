#!/usr/bin/env bash
# Stock Android only: real UI + ordinary-UID socket echo, not Root/FakeTCP.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
api="${WBD_ANDROID_API:?}"
[[ "$api" == 35 || "$api" == 36 ]]
out=out/android-stock-suite
mkdir -p "$out"
app=out/android-root-release/android-root-app
fixture=out/android-root-release/android-traffic-fixture/traffic-fixture.apk
test "$(cat "$app/SOURCE")" = "$GITHUB_SHA"
(cd "$app" && sha256sum -c SHA256SUMS)
test -s "$fixture"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
export ANDROID_AVD_HOME="$RUNNER_TEMP/wbd-stock-avd"
mkdir -p "$ANDROID_AVD_HOME"
emu_pid=""; echo_pid=""
cleanup(){
  rc=$?
  trap - EXIT
  set +e
  if [[ -n "$echo_pid" ]];then kill "$echo_pid" 2>/dev/null;wait "$echo_pid" 2>/dev/null;fi
  if [[ -n "$emu_pid" ]];then timeout 10s adb emu kill >/dev/null 2>&1;kill "$emu_pid" 2>/dev/null;wait "$emu_pid" 2>/dev/null;fi
  printf '%s\n' "$rc" >"$out/exit-code.txt"
  exit "$rc"
}
trap cleanup EXIT
test -c /dev/kvm
sudo -n chmod a+rw /dev/kvm
sdk="$ANDROID_HOME/cmdline-tools/latest/bin"
image="system-images;android-$api;google_apis;x86_64"
printf 'y\n' | "$sdk/sdkmanager" "$image" >"$out/sdk-install.txt" 2>&1
printf 'no\n' | "$sdk/avdmanager" create avd -n wbd_stock -k "$image" --force >"$out/avd-create.txt" 2>&1
emulator -avd wbd_stock -no-window -no-audio -no-snapshot -no-boot-anim -gpu swiftshader_indirect -cores 2 -memory 3072 >"$out/emulator.txt" 2>&1 &
emu_pid=$!
for ((i=0;i<120;i++));do
  kill -0 "$emu_pid" || { tail -30 "$out/emulator.txt";exit 21; }
  if [[ "$(timeout 5s adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]];then break;fi
  sleep 3
done
test "$(adb shell getprop sys.boot_completed | tr -d '\r')" = 1
test "$(adb shell getprop ro.build.version.sdk | tr -d '\r')" = "$api"
adb shell uname -m >"$out/guest-arch.txt"
adb shell getprop ro.build.version.sdk >"$out/api.txt"
adb shell input keyevent 82
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
adb install "$app/wbd-root-arm64-debug.apk" >"$out/install-product.txt"
adb install "$fixture" >"$out/install-fixture.txt"
adb shell am start -W -n org.wbdnext.rootclient/.RootClientActivity >"$out/activity.txt"
set +e
if [[ "${WBD_B104_UI:-0}" == 1 ]];then
 python3 android/root-app/ci/x86-ui-smoke.py --out "$out" >"$out/ui-navigation.txt" 2>&1
 ui_rc=$?
 cat "$out/ui-navigation.txt"
 if [[ "$ui_rc" == 0 ]];then
   python3 android/root-app/ci/b104-ui-profiles.py --out "$out" >"$out/ui-smoke.txt" 2>&1
   ui_rc=$?
   cat "$out/ui-smoke.txt"
 fi
else
 python3 android/root-app/ci/x86-ui-smoke.py --out "$out" >"$out/ui-smoke.txt" 2>&1
 ui_rc=$?
fi
set -e
# No WBD session was started: this is an Android instrumentation admission.
python3 -u android/root-app/ci/traffic-fixture/server.py --bind 127.0.0.1 --port 18080 >"$out/echo.txt" 2>&1 &
echo_pid=$!
for ((i=0;i<30;i++));do
  if grep -q 'WBD test echo' "$out/echo.txt";then break;fi
  kill -0 "$echo_pid"
  sleep .2
done
grep -q 'WBD test echo' "$out/echo.txt"
uid="$(adb shell pm list packages -U org.wbdnext.testtraffic | tr -d '\r' | sed -n 's/^package:org.wbdnext.testtraffic uid:\([0-9]*\)$/\1/p')"
[[ "$uid" =~ ^[0-9]+$ && "$uid" -ge 10000 ]]
set +e
python3 android/root-app/ci/traffic-fixture/run.py --host 10.0.2.2 --samples 16 --mib 2 --expect-uid "$uid" --label "stock-api$api-no-wbd" --output "$out/ordinary-uid.json" >"$out/traffic.txt" 2>&1
traffic_rc=$?
set -e
python3 - "$out" "$api" "$ui_rc" "$traffic_rc" <<'PY'
import json,os,sys,pathlib
p=pathlib.Path(sys.argv[1])
(p/"receipt.json").write_text(json.dumps({"source":os.environ["GITHUB_SHA"],"api":int(sys.argv[2]),"production_signed_apk_ui":"PASS" if sys.argv[3]=="0" else "FAIL","ordinary_uid_socket_echo":"PASS" if sys.argv[4]=="0" else "FAIL","root":"NOT_RUN","wbd_tls_m4":"NOT_RUN"},indent=2)+"\n")
PY
test "$ui_rc" = 0 && test "$traffic_rc" = 0
