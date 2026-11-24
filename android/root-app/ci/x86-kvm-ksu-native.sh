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
tap_owned=0
tap_guest_boot=NOT_RUN
tap_phase=NOT_RUN
tap_rx_base=0
tap_rx_boot=0
tap_rx_original_start=""
tap_guest_l2_at_boot=NOT_RUN
tap_guest_l2_during_original=NOT_RUN
tap_wifi_flag=NOT_PROVEN
tap_dhcp_process=NOT_RUN
tap_dhcp_lease=NOT_PROVEN
tap_dhcp_cleanup=NOT_RUN
tap_dhcp_pidfile=""
tap_dhcp_leasefile=""
tap_dhcp_wrapper_pid=""
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
 "app_to_ksu_root":"PASS" if "APP_UID_SU_PASS" in read("app-su-receipt.txt") and
   "ORIGINAL_SIGNED_NATIVE_ASSETS_VERIFIED" in read("app-su-receipt.txt")
   else ("NOT_PROVEN" if read("grant-ui.txt") else "NOT_RUN"),
 "physical_network_app_readback":("PASS" if "PHYSICAL_NETWORK_EXACT_READBACK_PASS" in read("physical-network-receipt.txt") else
    ("ENV_BLOCKED" if "PHYSICAL_NETWORK_ENV_BLOCKED" in read("physical-network-receipt.txt") else "NOT_PROVEN")),
 "android_ui_navigation":"PASS" if "ANDROID_UI_NAVIGATION_PASS" in read("ui-smoke.txt") else ("NOT_PROVEN" if read("ui-smoke.txt") else "NOT_RUN"),
 "android_art_cold_controls":"PASS" if "ANDROID_ART_COLD_CONTROLS_PASS" in read("app-su-logcat-filtered.txt") else ("FAIL" if "ANDROID_ART_COLD_CONTROLS_FAIL" in read("app-su-logcat-filtered.txt") else "NOT_RUN"),
 "translated_arm64_rust_mtu":"PASS" if "WBD_TRANSLATED_ARM64_RUST_MTU_BUDGET_PASS" in read("translated-mtu.txt") and read("translated-mtu-code.txt").strip()=="0" else ("NOT_PROVEN" if read("translated-mtu-code.txt") else "NOT_RUN"),
 "translated_original_go_cshared_help":"PASS" if "WBD_ANDROID_ARM64_ORIGINAL_GO_CSHARED_HELP_PASS" in read("translated-go-help.txt") and read("translated-go-help-code.txt").strip()=="0" else ("NOT_PROVEN" if read("translated-go-help-code.txt") else "NOT_RUN"),
 "original_tls_auth_lease":"NOT_RUN","real_m3_m4_tcp_udp":"NOT_RUN",
 "owned_stop_route_rollback":"NOT_RUN",
 "system_dns_takeover":"NOT_RUN"}
(out/"receipt.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print("ANDROID_X86_KSU_ORIGINAL_NATIVE_D1_ADMISSION",d["original_x86_go_help"],d["phase"])
PY
}

tap_pilot_receipt(){
  local rc="$1"
  mkdir -p out/android-x86-tap-guest
  WBD_TAP_GUEST_RC="$rc" WBD_TAP_GUEST_PHASE="$tap_phase" \
  WBD_TAP_GUEST_OWNED="$tap_owned" WBD_TAP_GUEST_BOOT="$tap_guest_boot" \
  WBD_TAP_L2_BOOT="$tap_guest_l2_at_boot" \
  WBD_TAP_L2_D2="$tap_guest_l2_during_original" \
  WBD_TAP_WIFI_FLAG="$tap_wifi_flag" \
  WBD_TAP_DHCP="$tap_dhcp_process" WBD_TAP_DHCP_LEASE="$tap_dhcp_lease" \
  WBD_TAP_DHCP_CLEANUP="$tap_dhcp_cleanup" \
  python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("out/android-x86-tap-guest")
r=pathlib.Path("out/android-x86-ksu-native/physical-network-receipt.txt")
physical=r.read_text().strip() if r.exists() else "NOT_PROVEN"
d={"schema":"wbd-d2-x86-original-tap-guest-pilot/v1",
   "source":os.environ["GITHUB_SHA"],
   "phase":os.environ["WBD_TAP_GUEST_PHASE"],
   "exit_code":int(os.environ["WBD_TAP_GUEST_RC"]),
   "host_tap_owned": "PASS" if os.environ["WBD_TAP_GUEST_OWNED"]=="1" else "NOT_PROVEN",
   "host_tap_exact_cleanup": ("NOT_RUN" if os.environ["WBD_TAP_GUEST_OWNED"]!="1" else
       ("PASS" if os.environ["WBD_TAP_GUEST_PHASE"]!="TAP_DELETE_FAILED" and
         not pathlib.Path("/sys/class/net/wbdtapci0").exists() else "FAIL")),
   "guest_boot_with_wifi_tap_argument":os.environ["WBD_TAP_GUEST_BOOT"],
   "emulator_wifi_tap_flag":os.environ["WBD_TAP_WIFI_FLAG"],
   "isolated_tap_dhcp_process":os.environ["WBD_TAP_DHCP"],
   "isolated_tap_dhcp_lease":os.environ["WBD_TAP_DHCP_LEASE"],
   "owned_dhcp_process_cleanup":os.environ["WBD_TAP_DHCP_CLEANUP"],
   "guest_to_host_tap_l2_during_boot":os.environ["WBD_TAP_L2_BOOT"],
   "guest_to_host_tap_l2_during_d2_session":os.environ["WBD_TAP_L2_D2"],
   "android_real_physical_network":"PASS" if physical=="PHYSICAL_NETWORK_EXACT_READBACK_PASS" else
      ("ENV_BLOCKED" if physical=="PHYSICAL_NETWORK_ENV_BLOCKED" else "NOT_PROVEN"),
   "slirp_bypass_for_original_syn":"NOT_PROVEN",
   "android_original_selected_interface":"NOT_PROVEN",
   "guest_ethernet_tcpdump_with_tap":"NOT_USED",
   "original_linux_raw_syn_rx":"NOT_PROVEN",
   "original_linux_raw_synack_tx":"NOT_PROVEN",
   "android_synack_tls_auth_lease_m4_stop":"NOT_PROVEN",
   "whole_android_linux_e2e":"NOT_PROVEN"}
d2=pathlib.Path("out/android-x86-d2-root/receipt.json")
diagnostic=pathlib.Path("out/android-x86-d2-root/app-diagnostic-enums.txt")
if diagnostic.exists():
    wire=diagnostic.read_text(errors="replace")
    for marker,label in (("CI_SELECTED_PHYSICAL_IFACE_WLAN0","WLAN0"),
                         ("CI_SELECTED_PHYSICAL_IFACE_ETH0","ETH0"),
                         ("CI_SELECTED_PHYSICAL_IFACE_OTHER","OTHER")):
        if marker in wire:
            d["android_original_selected_interface"]=label
            break
if d2.exists():
    data=json.loads(d2.read_text())
    for k,s in (("original_linux_server_untrusted_raw_initial_syn","original_linux_raw_syn_rx"),
                ("original_linux_server_untrusted_raw_synack_tx","original_linux_raw_synack_tx")):
        d[s]=data.get(k,"NOT_PROVEN")
    if (data.get("host_tap_syn_to_original_server")=="OBSERVED" and
        d["original_linux_raw_syn_rx"]=="OBSERVED"):
        d["slirp_bypass_for_original_syn"]="OBSERVED"
    d["android_synack_tls_auth_lease_m4_stop"]="PASS" if all(
        data.get(k)=="PASS" for k in ("real_peer_synack","tls_authenticated_32_lease",
                                     "original_rust_m4_and_uid_ready",
                                     "owned_stop_verified")) else "NOT_PROVEN"
(p/"receipt.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print("D2_TAP_GUEST_PILOT",d["phase"],d["guest_boot_with_wifi_tap_argument"],
      d["android_real_physical_network"],d["slirp_bypass_for_original_syn"])
PY
}
cleanup(){
  local rc=$?
  trap - EXIT
  receipt "$rc" || true
  # Snapshot the kernel TAP RX BEFORE killing the guest. Shutdown traffic
  # cannot be credited to the original Go D2 session.
  if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 && "$tap_owned" == 1 &&
        -n "$tap_rx_original_start" &&
        -r /sys/class/net/wbdtapci0/statistics/rx_packets ]];then
    tap_rx_final="$(cat /sys/class/net/wbdtapci0/statistics/rx_packets)"
    if [[ "$tap_rx_final" =~ ^[0-9]+$ ]] &&
       (( tap_rx_final > tap_rx_original_start ));then
      tap_guest_l2_during_original=OBSERVED
    elif [[ "$tap_rx_final" =~ ^[0-9]+$ ]];then
      tap_guest_l2_during_original=NOT_OBSERVED
    else
      tap_guest_l2_during_original=NOT_PROVEN
    fi
  fi
  if test -n "$EMU_PID";then
    timeout 10s "$ANDROID_HOME/platform-tools/adb" emu kill >"$out/guest-cleanup.txt" 2>&1 || true
    kill -TERM "$EMU_PID" 2>/dev/null || true
    for _ in $(seq 1 20);do
      if ! kill -0 "$EMU_PID" 2>/dev/null;then break;fi
      sleep 0.2
    done
    kill -KILL "$EMU_PID" 2>/dev/null || true
  fi
  if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 ]];then
    # Stop the single DHCP process owned by this job, never any system daemon.
    if [[ -n "$tap_dhcp_pidfile" && -s "$tap_dhcp_pidfile" ]];then
      own_dhcp_pid="$(cat "$tap_dhcp_pidfile")"
      if [[ "$own_dhcp_pid" =~ ^[0-9]+$ && "$own_dhcp_pid" -gt 1 ]] &&
         [[ -r "/proc/$own_dhcp_pid/cmdline" ]] &&
         tr '\0' ' ' <"/proc/$own_dhcp_pid/cmdline" |
           grep -Fq -- '--interface=wbdtapci0';then
        sudo -n kill -TERM "$own_dhcp_pid" >/dev/null 2>&1 || true
        for i in $(seq 1 25);do
          if ! sudo -n kill -0 "$own_dhcp_pid" 2>/dev/null ||
             [[ "$(ps -o stat= -p "$own_dhcp_pid" 2>/dev/null)" == Z* ]];then
            break
          fi
          sleep 0.1
        done
        if sudo -n kill -0 "$own_dhcp_pid" 2>/dev/null &&
           [[ "$(ps -o stat= -p "$own_dhcp_pid" 2>/dev/null)" != Z* ]];then
          tap_dhcp_cleanup=FAIL
          tap_phase=DHCP_CLEANUP_FAILED
          rc=32
        else
          tap_dhcp_cleanup=PASS
        fi
      elif [[ ! -d "/proc/${own_dhcp_pid:-invalid}" ]];then
        tap_dhcp_cleanup=PASS
      else
        tap_dhcp_cleanup=FAIL
        tap_phase=DHCP_PID_OWNERSHIP_UNPROVEN
        rc=32
      fi
    fi
    if [[ "$tap_owned" == 1 ]];then
      sudo -n ip link del wbdtapci0 >/dev/null 2>&1 || true
      if ip link show wbdtapci0 >/dev/null 2>&1;then
        tap_phase=TAP_DELETE_FAILED
        rc=31
      fi
    fi
    tap_pilot_receipt "$rc" || true
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
  local -a cold_wire_capture=()
  local -a tap_args=()
  if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 && "$stage" == second ]];then
    tap_args=(-wifi-tap wbdtapci0)
  fi
  if [[ "${WBD_D2_ORIGINAL:-0}" == 1 && "$stage" == second &&
        "${WBD_D2_TAP_GUEST_PILOT:-0}" != 1 ]];then
    # Official emulator virtual-LAN capture: private, ephemeral, never
    # uploaded. Only TCP SYN/SYNACK/RST enums are extracted at D2 cleanup.
    mkdir -p out/android-x86-d2-root
    cold_wire_capture=(-tcpdump "$GITHUB_WORKSPACE/out/android-x86-d2-root/guest-ethernet.pcap")
  fi
  "$emulator" -avd wbd_ksu36 -ramdisk "$GITHUB_WORKSPACE/out/ksu/patched-ramdisk.img" \
     -no-snapshot-load -no-snapshot-save -no-window -no-audio -no-boot-anim \
     -gpu swiftshader_indirect -accel on -memory 3072 "${tap_args[@]}" "${cold_wire_capture[@]}" \
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
if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 ]];then
  test "${WBD_D2_ORIGINAL:-0}" = 1 || { tap_phase=REFUSE_NON_ORIGINAL; exit 27; }
  test -c /dev/net/tun || { tap_phase=ENV_BLOCKED_TUN_DEVICE; exit 27; }
  if ip link show wbdtapci0 >/dev/null 2>&1;then
    tap_phase=REFUSE_PREEXISTING_TAP
    exit 27
  fi
  if ip -4 route show table main exact 10.0.2.0/24 | grep -q .;then
    tap_phase=ENV_BLOCKED_TAP_SUBNET_CONFLICT
    exit 27
  fi
  if ! timeout 15s "$emulator" -help-all >"$out/wifi-tap-help-private.txt" 2>&1 ||
     ! grep -Eq -- '(^|[[:space:]])-wifi-tap([[:space:]]|$)' "$out/wifi-tap-help-private.txt";then
    rm -f "$out/wifi-tap-help-private.txt"
    tap_phase=ENV_BLOCKED_EMULATOR_WIFI_TAP_FLAG
    exit 27
  fi
  tap_wifi_flag=ADVERTISED_NOT_GUEST_EGRESS_VERIFIED
  rm -f "$out/wifi-tap-help-private.txt"
  sudo -n ip tuntap add dev wbdtapci0 mode tap user "$(id -un)"
  tap_owned=1
  sudo -n ip addr add 10.0.2.2/24 dev wbdtapci0
  sudo -n ip link set dev wbdtapci0 up
  ip -o -4 addr show dev wbdtapci0 | grep -Fq '10.0.2.2/24' || {
    tap_phase=ENV_BLOCKED_HOST_TAP_READBACK
    exit 27
  }
  tap_rx_base="$(cat /sys/class/net/wbdtapci0/statistics/rx_packets)"
  [[ "$tap_rx_base" =~ ^[0-9]+$ ]] || { tap_phase=ENV_BLOCKED_HOST_TAP_RX_COUNTER; exit 27; }
  tap_rx_boot="$tap_rx_base"
  tap_phase=HOST_TAP_READY
  # Real, isolated DHCP for the genuine Android virtio Wi-Fi interface.
  # Offer only a short on-link IPv4 lease. No default gateway, DNS server,
  # NAT, forwarding or changes to host/system network policy.
  dnsmasq=/usr/sbin/dnsmasq
  if [[ ! -x "$dnsmasq" ]];then
    if ! timeout 100s sudo -n env DEBIAN_FRONTEND=noninteractive \
       apt-get install -y -qq dnsmasq-base >"$out/dhcp-package-private.txt" 2>&1;then
      rm -f "$out/dhcp-package-private.txt"
      tap_phase=ENV_BLOCKED_ISOLATED_DHCP_PACKAGE
      exit 33
    fi
    rm -f "$out/dhcp-package-private.txt"
  fi
  test -x "$dnsmasq" || { tap_phase=ENV_BLOCKED_ISOLATED_DHCP_BINARY; exit 33; }
  mkdir -p out/android-x86-tap-guest
  tap_dhcp_pidfile="$GITHUB_WORKSPACE/out/android-x86-tap-guest/dhcp-root.pid"
  tap_dhcp_leasefile="$GITHUB_WORKSPACE/out/android-x86-tap-guest/dhcp-leases-private.txt"
  test ! -e "$tap_dhcp_pidfile" || { tap_phase=REFUSE_PREEXISTING_DHCP_PID;exit 33; }
  sudo -n sh -c 'echo "$$" > "$1"; shift; exec "$@"' sh \
    "$tap_dhcp_pidfile" "$dnsmasq" --keep-in-foreground --conf-file=/dev/null \
    --port=0 --no-resolv --no-hosts --interface=wbdtapci0 --bind-interfaces \
    --user=root --group=root \
    --dhcp-range=10.0.2.16,10.0.2.19,255.255.255.0,5m \
    --dhcp-option=option:router --dhcp-option=option:dns-server \
    --dhcp-leasefile="$tap_dhcp_leasefile" \
    >"$out/dhcp-private.log" 2>&1 &
  tap_dhcp_wrapper_pid=$!
  for i in $(seq 1 60);do
    if [[ -s "$tap_dhcp_pidfile" ]];then
      own_dhcp_pid="$(cat "$tap_dhcp_pidfile")"
      if [[ "$own_dhcp_pid" =~ ^[0-9]+$ ]] &&
         sudo -n kill -0 "$own_dhcp_pid" 2>/dev/null;then break;fi
    fi
    sleep 0.1
  done
  if [[ ! -s "$tap_dhcp_pidfile" ]] ||
     ! sudo -n kill -0 "$(cat "$tap_dhcp_pidfile")" 2>/dev/null;then
    tap_phase=ENV_BLOCKED_ISOLATED_DHCP_START
    exit 33
  fi
  tap_dhcp_process=PASS
  tap_phase=WIFI_TAP_DHCP_READY
fi
phase=SECOND_KSU_BOOT
start_guest second
if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 ]];then
  tap_guest_boot=PASS
  if [[ -s "$tap_dhcp_leasefile" ]];then
    tap_dhcp_lease=OBSERVED
  fi
  tap_rx_boot="$(cat /sys/class/net/wbdtapci0/statistics/rx_packets)"
  if [[ "$tap_rx_boot" =~ ^[0-9]+$ ]] && (( tap_rx_boot > tap_rx_base ));then
    tap_guest_l2_at_boot=OBSERVED
  elif [[ "$tap_rx_boot" =~ ^[0-9]+$ ]];then
    tap_guest_l2_at_boot=NOT_OBSERVED
  else
    tap_guest_l2_at_boot=NOT_PROVEN
  fi
  tap_phase=TAP_GUEST_BOOTED
fi
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
if [[ "${WBD_ANDROID_COLD_SUITE:-0}" == 1 ]];then
  phase=ACTUAL_ANDROID_UI_SMOKE
  # Record independent UI outcome; keep the rest of the cold suite useful
  # even if a UI coordinate/guest rendering step fails.
  set +e
  python3 android/root-app/ci/x86-ui-smoke.py --out "$out" >"$out/ui-smoke.txt" 2>&1
  ui_rc=$?
  set -e
  echo "$ui_rc" >"$out/ui-smoke-code.txt"
fi
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
# D1 phase 2: the SAME signed CI-only original controller PACKAGE must
# request su from its own ordinary untrusted_app UID. ADB shell su/root
# above is NOT acceptable proof. A CI-only activity (not shipped on ARM64)
# first verifies the exact product NativePayload and then requests real su.
phase=CI_APP_UID_KSU_GRANT
adb logcat -c >"$out/logcat-clear.txt" 2>&1 || true
adb shell am start -n org.wbdnext.rootclient/.X86CiAppSuActivity \
  >"$out/app-su-first-request.txt" 2>&1
grep -q 'Starting: Intent' "$out/app-su-first-request.txt"
sleep 4
# Reuse historical KSU Manager UI grant, but pin exactly our signed package
# and its CI-only label. No direct ksud allowlist writes or fake su.
WBD_KSU_TARGET_PACKAGE=org.wbdnext.rootclient \
WBD_KSU_TARGET_LABEL='WBD x86 CI Root' \
  python3 experiments/android-root-probe/ci/ksu-grant-ui.py \
  >"$out/grant-ui.txt" 2>&1
adb shell am start -n org.wbdnext.rootclient/.X86CiAppSuActivity \
  >"$out/app-su-second-request.txt" 2>&1
grep -q 'Starting: Intent' "$out/app-su-second-request.txt"
for i in $(seq 1 55);do
  adb shell logcat -d -s WBD_X86_CI_APP_SU:I '*:S' \
    >"$out/app-su-logcat-filtered.txt" 2>&1 || true
  if grep -Fq 'APP_UID_SU_PASS' "$out/app-su-logcat-filtered.txt" &&
     grep -Fq 'ORIGINAL_SIGNED_NATIVE_ASSETS_VERIFIED' "$out/app-su-logcat-filtered.txt";then
    printf 'ORIGINAL_SIGNED_NATIVE_ASSETS_VERIFIED\nAPP_UID_SU_PASS\n' \
      >"$out/app-su-receipt.txt"
    break
  fi
  sleep 2
done
if [[ ! -s "$out/app-su-receipt.txt" ]];then
  echo "ANDROID_X86_CI_APP_UID_KSU_SU_NOT_PROVEN" >&2
  exit 21
fi
echo "ANDROID_X86_CI_APP_UID_KSU_SU_PASS"
# Re-run the original PhysicalNetwork.available/exact under the same signed
# ordinary App UID, never from adb shell root or assumed emulator interface.
if grep -Fq 'PHYSICAL_NETWORK_EXACT_READBACK_PASS' "$out/app-su-logcat-filtered.txt";then
  echo PHYSICAL_NETWORK_EXACT_READBACK_PASS >"$out/physical-network-receipt.txt"
  echo ANDROID_X86_APP_PHYSICAL_NETWORK_EXACT_READBACK_PASS
elif grep -Fq 'PHYSICAL_NETWORK_ENV_BLOCKED' "$out/app-su-logcat-filtered.txt";then
  echo PHYSICAL_NETWORK_ENV_BLOCKED >"$out/physical-network-receipt.txt"
  echo ANDROID_X86_APP_PHYSICAL_NETWORK_ENV_BLOCKED
else
  echo PHYSICAL_NETWORK_NOT_PROVEN >"$out/physical-network-receipt.txt"
  echo ANDROID_X86_APP_PHYSICAL_NETWORK_NOT_PROVEN
fi
if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 ]];then
  if ! grep -Fxq PHYSICAL_NETWORK_EXACT_READBACK_PASS "$out/physical-network-receipt.txt";then
    tap_phase=ENV_BLOCKED_REAL_ANDROID_PHYSICAL_NETWORK
    echo D2_TAP_GUEST_REAL_PHYSICAL_NETWORK_ENV_BLOCKED
    exit 29
  fi
  tap_phase=TAP_GUEST_REAL_NETWORK_EXACT_EGRESS_NOT_PROVEN
fi
echo "D1_REAL_ORIGINAL_CLIENT_TLS_M4_NOT_RUN"
if [[ "${WBD_ANDROID_COLD_SUITE:-0}" == 1 ]];then
  phase=COMBINED_ANDROID_COLD_SUITE
  # Same emulator session; no second KSU boot, no raw networking experiment.
  # ART logs were emitted before the final App->su PASS.
  art_rc=0
  grep -Fq ANDROID_ART_COLD_CONTROLS_PASS "$out/app-su-logcat-filtered.txt" || art_rc=1
  n=out/android-root-app-native
  adb push "$n/ksu-arm64-ndk-probe" /data/local/tmp/wbd-cold-arm64-probe >/dev/null
  adb push "$n/libwbd_engine-arm64.so" /data/local/tmp/libwbd_engine.so >/dev/null
  adb push "$n/libksu-arm64-original-go-cshared-midr.so" /data/local/tmp/libwbd-original-go-cshared-midr.so >/dev/null
  adb shell su -c 'chmod 755 /data/local/tmp/wbd-cold-arm64-probe; chmod 644 /data/local/tmp/libwbd_engine.so /data/local/tmp/libwbd-original-go-cshared-midr.so' >/dev/null
  adb shell su -c 'sha256sum /data/local/tmp/wbd-cold-arm64-probe /data/local/tmp/libwbd_engine.so /data/local/tmp/libwbd-original-go-cshared-midr.so' >"$out/translated-sha.txt"
  for name in ksu-arm64-ndk-probe libwbd_engine-arm64.so libksu-arm64-original-go-cshared-midr.so;do
    grep -Fq "$(sha256sum "$n/$name" | cut -d ' ' -f1)" "$out/translated-sha.txt"
  done
  set +e
  adb shell su -c '/data/local/tmp/wbd-cold-arm64-probe --mtu-budget /data/local/tmp/libwbd_engine.so' >"$out/translated-mtu.txt" 2>&1
  mturc=$?
  adb shell su -c '/data/local/tmp/wbd-cold-arm64-probe --original-go-help /data/local/tmp/libwbd-original-go-cshared-midr.so' >"$out/translated-go-help.txt" 2>&1
  gocshrc=$?
  set -e
  printf '%s\n' "$mturc" >"$out/translated-mtu-code.txt"
  printf '%s\n' "$gocshrc" >"$out/translated-go-help-code.txt"
  # Keep these as separate real results. No direct ARM64 Go ELF rerun,
  # no TLS or ISA-L performance claim. An unavailable translator is a
  # test-environment limitation rather than a production phone failure.
  if [[ "$mturc" == 0 && "$gocshrc" == 0 ]] &&
      grep -Fq WBD_TRANSLATED_ARM64_RUST_MTU_BUDGET_PASS "$out/translated-mtu.txt" &&
      grep -Fq WBD_ANDROID_ARM64_ORIGINAL_GO_CSHARED_HELP_PASS "$out/translated-go-help.txt";then
    if [[ "${art_rc:-1}" != 0 ]];then
      echo ANDROID_ART_COLD_CONTROLS_NOT_PROVEN
      exit 33
    fi
    if [[ "${ui_rc:-1}" != 0 ]];then
      echo ANDROID_UI_NAVIGATION_NOT_PROVEN
      exit 32
    fi
    echo ANDROID_COMBINED_COLD_SUITE_PASS
  else
    echo ANDROID_TRANSLATED_COLD_SUITE_NOT_PROVEN
    exit 31
  fi
fi
if [[ "${WBD_D2_ORIGINAL:-0}" == 1 ]];then
  # The separate D2-S1 job reuses this exact proven Android/KSU/App admission.
  # Start the REAL Linux server and production Android RootClientService,
  # never a second simulated data plane or root bypass.
  if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 ]];then
    if [[ -s "$tap_dhcp_leasefile" ]];then tap_dhcp_lease=OBSERVED;fi
    tap_rx_original_start="$(cat /sys/class/net/wbdtapci0/statistics/rx_packets)"
    if [[ ! "$tap_rx_original_start" =~ ^[0-9]+$ ]];then
      tap_phase=ENV_BLOCKED_HOST_TAP_D2_RX_COUNTER
      exit 30
    fi
  fi
  bash android/root-app/ci/x86-d2-original-root-preauth.sh
fi
