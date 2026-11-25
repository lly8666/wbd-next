#!/usr/bin/env bash
# D2-S1: real original Linux WBD server and the PRODUCTION Android
# RootClientService in one Android16 x86 KSU CI session. This step admits
# only authentic pre-auth TUN/RAW and records TLS/lease/M4 separately.
# No fake packets, no Java/Go forwarding loop, no untrusted root shortcuts.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
test "$WBD_D2_ORIGINAL" = 1
p=out/android-x86-original-linux
n=out/android-root-app-native
out=out/android-x86-d2-root
mkdir -p "$out"
test -s "$p/manifest.json" && test "$(cat "$p/SOURCE")" = "$GITHUB_SHA"
test -s "$n/manifest-ci-x86_64.json" && test "$(cat "$n/SOURCE")" = "$GITHUB_SHA"
(cd "$p" && sha256sum -c SHA256SUMS) >"$out/linux-source-sha.txt"
(cd "$n" && sha256sum -c SHA256SUMS) >"$out/android-source-sha.txt"
# actions/download-artifact extracts uploaded ELF bytes without executable mode.
# Restore executable permission ONLY after exact SHA checks; mode does not
# change content hash. Exit 126 in Action44246119539 occurred before server
# initialization, with guest and app source checks already PASS.
for binary in wbd-v4-server wbd-v4-client;do
  test -f "$p/$binary" && test ! -L "$p/$binary"
  chmod 0700 "$p/$binary"
  test -x "$p/$binary" || { echo "D2_S1_ORIGINAL_LINUX_ELF_NOT_EXECUTABLE" >&2; exit 126; }
done
python3 - <<'PY'
from pathlib import Path
import json,os
l=json.loads(Path("out/android-x86-original-linux/manifest.json").read_text())
a=json.loads(Path("out/android-root-app-native/manifest-ci-x86_64.json").read_text())
assert l["source"]==a["source"]==os.environ["GITHUB_SHA"]
assert l["donor_go"]==a["donor_go"]=="a7a82db31fe736ffedee330795a3234d358f1984"
assert l["android_ci_abi"]=="x86_64" and l["linux_arch"]=="amd64"
assert l["android_go_sha256"]==a["artifacts"]["wbd-v4-client-amd64"]["sha256"]
assert l["android_rust_sha256"]==a["artifacts"]["libwbd_engine-amd64.so"]["sha256"]
print("D2_S1_SAME_SOURCE_ORIGINAL_LINUX_SERVER_AND_ANDROID_CLIENT_PASS")
PY
test -c /dev/net/tun
test -d "$RUNNER_TEMP"
if ip link show wbdvs4 >/dev/null 2>&1;then
  echo "D2_S1_REFUSE_PREEXISTING_HOST_TUN" >&2
  exit 19
fi
tmp="$(mktemp -d "$RUNNER_TEMP/wbd-d2-original-XXXXXXXX")"
chmod 700 "$tmp"
server_pid=""
host_observer_pid=""
activity_requested=0
host_rst_scope=0
phase=D2_S1_INIT
raw_iface=lo
raw_ip=127.0.0.1
if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 ]];then
  raw_iface=wbdtapci0
  raw_ip=10.0.2.2
  ip -o -4 addr show dev "$raw_iface" | grep -Fq '10.0.2.2/24' || {
    echo "D2_TAP_REFUSE_UNVERIFIED_HOST_TAP" >&2
    exit 27
  }
fi
adb(){ timeout --signal=TERM --kill-after=3s 35s "$ANDROID_HOME/platform-tools/adb" "$@"; }
receipt(){
  export WBD_D2_PHASE="$phase" WBD_D2_RC="$1"
  python3 - <<'PY'
from pathlib import Path
import json,os
p=Path("out/android-x86-d2-root")
data=(p/"app-diagnostic-enums.txt").read_text(errors="replace") if (p/"app-diagnostic-enums.txt").exists() else ""
server=(p/"server-stage-enums.txt").read_text(errors="replace") if (p/"server-stage-enums.txt").exists() else ""
def has(k):return k in data
def wire_status(name,key):
    try:
        d=json.loads((p/name).read_text())
        if (d.get("schema")!="wbd-d2-s1-cold-wire-flags-only/v1" or
            not d.get("wire_capture_format_valid") or
            d.get("tcp_frames_examined",0)<=0):
            return "NOT_PROVEN"
        value=d.get(key)
        return value if value in ("OBSERVED","NOT_OBSERVED") else "NOT_PROVEN"
    except (OSError,ValueError):
        return "NOT_PROVEN"
syn_classes=(
 ("ORIGINAL_GO_COLD_SYN_TX_OK","SENDTO_PASS_NOT_PEER_AUTH"),
 ("ORIGINAL_GO_COLD_SYN_TX_PERMISSION_DENIED","OS_PERMISSION_DENIED"),
 ("ORIGINAL_GO_COLD_SYN_TX_NETWORK_UNREACHABLE","OS_NETWORK_UNREACHABLE"),
 ("ORIGINAL_GO_COLD_SYN_TX_INVALID_ARGUMENT","OS_INVALID_ARGUMENT"),
 ("ORIGINAL_GO_COLD_SYN_TX_SOURCE_UNAVAILABLE","OS_SOURCE_UNAVAILABLE"),
 ("ORIGINAL_GO_COLD_SYN_TX_BUFFER_PRESSURE","OS_BUFFER_PRESSURE"),
 ("ORIGINAL_GO_COLD_SYN_TX_OTHER_FAILURE","OS_OTHER_FAILURE"))
syn_result=next((v for key,v in syn_classes if has(key)),"NOT_PROVEN")
d={"schema":"wbd-android-x86-original-root-d2-s1/v1",
 "source":os.environ["GITHUB_SHA"],"phase":os.environ["WBD_D2_PHASE"],
 "exit_code":int(os.environ["WBD_D2_RC"]),
 "linux_real_original_server":"PASS" if (p/"server-started.txt").exists() else "NOT_PROVEN",
 "ephemeral_app_private_secrets":"PASS" if (p/"secret-stage-enum.txt").exists() else "NOT_PROVEN",
 "host_loopback_port443_rst_quarantine":"SCOPED_ACTIVE" if
   os.environ.get("WBD_B108_CARRIER")!="1" and os.environ.get("WBD_D2_TAP_GUEST_PILOT")!="1" and (p/"host-rst-rule-enum.txt").exists() else "NOT_RUN",
 "host_tap_port443_rst_quarantine":"SCOPED_ACTIVE" if
   os.environ.get("WBD_D2_TAP_GUEST_PILOT")=="1" and (p/"host-rst-rule-enum.txt").exists() else "NOT_RUN",
 "signed_app_requested_original_root_service":"PASS" if has("ORIGINAL_ROOT_SERVICE_START_REQUESTED") else "NOT_PROVEN",
 "original_go_root_process_launched":"PASS" if has("ROOT_PROCESS_LAUNCHED") else "NOT_PROVEN",
 "original_android_tun_configured":"PASS" if has("ORIGINAL_GO_TUN_KERNEL_CONFIGURED") else "NOT_PROVEN",
 "original_android_raw_af_packet":"PASS" if has("ORIGINAL_GO_RAW_SOCKET_READY") else "NOT_PROVEN",
  "original_linux_server_untrusted_raw_initial_syn":"OBSERVED" if "V4_PUBLIC_ORIGINAL_SERVER_RAW_INITIAL_SYN_RX" in server else "NOT_PROVEN",
  "original_linux_server_untrusted_raw_synack_tx":"OBSERVED" if "V4_PUBLIC_ORIGINAL_SERVER_RAW_SYNACK_TX_OK" in server else "NOT_PROVEN",
 "original_android_cold_syn_send":syn_result,
  "guest_virtual_ethernet_syn_to_host":wire_status("guest-wire-summary.json","syn") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")!="1" else "NOT_RUN",
  "guest_virtual_ethernet_synack_from_host":wire_status("guest-wire-summary.json","synack") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")!="1" else "NOT_RUN",
  "guest_virtual_ethernet_rst_from_host":wire_status("guest-wire-summary.json","rst") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")!="1" else "NOT_RUN",
  "host_loopback_syn_to_original_server":wire_status("host-wire-summary.json","syn") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")!="1" else "NOT_RUN",
  "host_loopback_synack_from_server":wire_status("host-wire-summary.json","synack") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")!="1" else "NOT_RUN",
  "host_loopback_rst_from_server":wire_status("host-wire-summary.json","rst") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")!="1" else "NOT_RUN",
  "host_tap_syn_to_original_server":wire_status("host-wire-summary.json","syn") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")=="1" else "NOT_RUN",
  "host_tap_synack_from_server":wire_status("host-wire-summary.json","synack") if os.environ.get("WBD_D2_TAP_GUEST_PILOT")=="1" else "NOT_RUN",
 "original_android_unauth_rst_observed":"OBSERVED" if has("ORIGINAL_GO_COLD_UNAUTH_RST_RX") else "NOT_PROVEN",
 "real_peer_synack":"PASS" if has("ORIGINAL_GO_TCP_SYNACK_SEEN") or (p/"b110-game-wire-pass.txt").exists() else "NOT_PROVEN",
 "game_wire_and_native_ready":"PASS" if (p/"b110-game-wire-pass.txt").exists() else "NOT_PROVEN",
 "tunnel_dns_udp_tcp":"PASS" if (p/"b110-tunnel-dns-pass.txt").exists() else "NOT_RUN_OR_NOT_PROVEN",
 "production_network_auto_reconnect":"PASS" if (p/"b110-reconnect-pass.txt").exists() else "NOT_RUN_OR_NOT_PROVEN",
 "tls_authenticated_32_lease":"PASS" if has("AUTHENTICATED_LEASE_OS_READBACK") and
    ("V4_ORIGINAL_GO_SERVER_NATIVE_READY" in server or "V4_PUBLIC_MULTI_SESSION_READY" in server or (p/"b109-remote-auth-result.txt").exists()) else "NOT_PROVEN",
 "original_rust_m4_and_uid_ready":"PASS" if has("NATIVE_M4_AND_UID_READY") else "NOT_PROVEN",
 "test_carrier":"CI_ADB_VETH_TC" if os.environ.get("WBD_B108_CARRIER")=="1" else "EMULATOR_DEFAULT",
 "mode":os.environ.get("WBD_B109_MODE","normal"),
 "scene":os.environ.get("WBD_B110_SCENE",""),
 "native_fixed_final":(p/"b112-native-fec-final.txt").read_text().strip().split("ORIGINAL_ANDROID_FIXED_M4_FINAL ",1)[-1] if (p/"b112-native-fec-final.txt").exists() else "NOT_PROVEN",
 "carrier_rebound":"PASS" if (p/"b113-rebind.txt").exists() and "B113_CARRIER_REBOUND " in (p/"b113-rebind.txt").read_text() else "NOT_PROVEN",
 "loss_business_and_fec":"PASS" if (p/"b111-loss-result.txt").exists() else "NOT_PROVEN",
 "normal_fec_recovered_tun":"OBSERVED" if has("ORIGINAL_FEC_RECOVERED_TUN_OBSERVED") else "NOT_PROVEN",
 "game_fec_recovered_candidate":"OBSERVED" if has("ORIGINAL_GAME_FEC_RECOVERED_CANDIDATE_OBSERVED") else "NOT_PROVEN",
 "b109_independent_peer_auth":"PASS" if (p/"b109-remote-auth-result.txt").exists() else "NOT_PROVEN",
 "b108_carrier_admission":"PASS" if (p/"b108-carrier-admission.txt").exists() else "NOT_PROVEN",
 "b108_joined_stop_kernel":"PASS" if (p/"b108-stop-result.txt").exists() else "NOT_PROVEN",
 "tcp_udp_bidirectional_application_data":"PASS" if (p/"b108-remote-app-result.txt").exists() else "NOT_RUN",
 "owned_stop_verified":"PASS" if has("ORIGINAL_GO_RUST_STOP_JOINED") and
    has("ORIGINAL_GO_UID_ROUTE_STOP_DRAINED") else "NOT_PROVEN",
 "route_rollback_kernel_proved":"PASS" if (p/"b108-stop-result.txt").exists() else "NOT_RUN",
 "system_dns_takeover":"NOT_RUN"}
(p/"receipt.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print("D2_S1_ORIGINAL_ROOT_STAGED",
 d["linux_real_original_server"],
 d["original_android_tun_configured"],
 d["original_android_raw_af_packet"],
 "SYN_TX",d["original_android_cold_syn_send"],
 "TLS",d["tls_authenticated_32_lease"])
PY
}
cleanup(){
  local rc=$?
  trap - EXIT
  set +e
  if [[ "$activity_requested" == 1 ]];then
    adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity \
      --es ci_step stop >"$out/stop-activity.txt" 2>&1 || true
    sleep 3
    adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' \
      >"$out/app-diagnostic-enums.txt" 2>&1 || true
  fi
  if [[ -n "$host_observer_pid" ]];then
    kill -TERM "$host_observer_pid" 2>/dev/null || true
    for _ in $(seq 1 18);do
      if ! kill -0 "$host_observer_pid" 2>/dev/null;then break;fi
      sleep 0.2
    done
    if kill -0 "$host_observer_pid" 2>/dev/null;then
      kill -KILL "$host_observer_pid" 2>/dev/null || true
    fi
    wait "$host_observer_pid" 2>/dev/null || true
  fi
  # The guest PCAP is NEVER uploaded. Only fixed SYN/SYNACK/RST flags are
  # extracted from the real emulator virtual Ethernet frames.
  if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" != 1 && "${WBD_B108_CARRIER:-0}" != 1 ]];then
    python3 android/root-app/ci/x86-d2-cold-wire-observer.py guest \
      --input "$out/guest-ethernet.pcap" --output "$out/guest-wire-summary.json" \
      >"$tmp/guest-capture-parse.log" 2>&1 || true
    rm -f "$out/guest-ethernet.pcap"
  fi
  if [[ -n "$server_pid" ]];then
    kill -TERM "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  if [[ "$host_rst_scope" == 1 ]];then
    # Remove only the exact CI-owned rule, never reset host firewall state.
    sudo -n iptables -w -D OUTPUT -o "$raw_iface" -p tcp --sport 443 --tcp-flags RST RST -j DROP >/dev/null 2>&1 || true
  fi
  # No default route/DNS/ip rule changes. Tear down only our own ephemeral
  # host TUN if original Go Stop failed; the CI host is disposable.
  sudo -n ip link del wbdvs4 >/dev/null 2>&1 || true
  if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
    b108_cleanup
    if [[ -s "$out/b108-host-relay.log" ]];then cat "$out/b108-host-relay.log";fi
    if [[ -s "$out/b108-guest-relay.log" ]];then cat "$out/b108-guest-relay.log";fi
  fi
  receipt "$rc" || true
  rm -rf "$tmp"
  exit "$rc"
}
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  source android/root-app/ci/b108-wire-carrier.sh
fi
trap cleanup EXIT
umask 077
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  phase=B108_CARRIER_ADMISSION
  b108_setup
fi
# The proven original Linux netns FakeTCP oracle drops kernel-generated
# TCP RST. In the new Android-emulator loopback transport apply ONLY an
# exact short-lived OUTPUT/lo/443 RST rule, never a global default route,
# DNS setting or general firewall reset. Restore it in the EXIT trap.
if sudo -n iptables -w -C OUTPUT -o "$raw_iface" -p tcp --sport 443 --tcp-flags RST RST -j DROP >/dev/null 2>&1;then
  echo "D2_S1_REFUSE_EXISTING_RST_SUPPRESSION_RULE" >&2
  exit 26
fi
sudo -n iptables -w -I OUTPUT 1 -o "$raw_iface" -p tcp --sport 443 --tcp-flags RST RST -j DROP
host_rst_scope=1
if [[ "${WBD_D2_TAP_GUEST_PILOT:-0}" == 1 ]];then
  echo D2_HOST_TAP_PORT443_RST_QUARANTINED >"$out/host-rst-rule-enum.txt"
elif [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  echo B108_HOST_VETH_PORT443_RST_QUARANTINED >"$out/host-rst-rule-enum.txt"
else
  echo D2_HOST_LOOPBACK_PORT443_RST_QUARANTINED >"$out/host-rst-rule-enum.txt"
fi
# A read-only native Linux AF_PACKET loopback counter. It makes zero
# firewall/route/packet modifications and NEVER logs captured packet bytes.
# Starts before original Linux server to observe both the first guest SYN
# (if SLIRP forwards it) and authentic server SYNACK (if any).
if [[ "${WBD_B108_CARRIER:-0}" != 1 ]];then
sudo -n python3 android/root-app/ci/x86-d2-cold-wire-observer.py host \
  --output "$out/host-wire-summary.json" --max-seconds 150 \
  --interface "$raw_iface" --expected-ip "$raw_ip" \
  >"$tmp/host-wire-observer.log" 2>&1 &
host_observer_pid=$!
sleep 0.2
if ! kill -0 "$host_observer_pid" 2>/dev/null;then
  echo "D2_S1_READONLY_HOST_AF_PACKET_OBSERVER_UNAVAILABLE" >&2
  exit 28
fi
fi
# Original CLI generates its own genuine 32-byte route secret.
env LD_LIBRARY_PATH="$GITHUB_WORKSPACE/$p" "$p/wbd-v4-server" \
  --init-route-key-file "$tmp/route.hex" \
  >"$tmp/original-route-generate.log" 2>&1
test "$(stat -c %a "$tmp/route.hex")" = 600
openssl rand -hex 32 >"$tmp/password"
python3 - "$tmp" <<'PY'
import pathlib,sys,json
p=pathlib.Path(sys.argv[1])
pw=(p/"password").read_text().strip()
assert len(pw)==64 and all(c in "0123456789abcdef" for c in pw)
(p/"users.json").write_text(json.dumps({"wbd-ci-session":pw})+"\n")
PY
chmod 600 "$tmp/password" "$tmp/users.json"
openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
  -keyout "$tmp/server-key.pem" -out "$tmp/server-cert.pem" \
  -subj '/CN=wbd-v4.example.test' \
  -addext 'subjectAltName=DNS:wbd-v4.example.test' \
  >"$tmp/openssl.log" 2>&1
chmod 600 "$tmp/server-key.pem" "$tmp/server-cert.pem"
# One original listener for all seven requested modes in the wiring matrix.
server_mode=normal
if [[ "${WBD_ANDROID_WIRING_MATRIX:-0}" == 1 ]];then server_mode=shared;fi
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  case "${WBD_B109_MODE:-normal}" in
    normal|fec-fixed|fec-auto) server_mode=normal;;
    game2|game2-fixed|game4|game4-fixed) server_mode=shared;;
    *) exit 2;;
  esac
  echo "B109_REMOTE_MODE ${WBD_B109_MODE:-normal} server=$server_mode"
fi
phase=D2_S1_ORIGINAL_LINUX_SERVER
# Android Emulator 10.0.2.2 maps to host loopback. Whether its user-mode
# NAT preserves raw FakeTCP SYN/SYNACK is explicitly unproven; never call it
# a TLS PASS until BOTH original server and Android receipts prove it.
timeout --signal=TERM --kill-after=5s 240s sudo -n env \
  LD_LIBRARY_PATH="$GITHUB_WORKSPACE/$p" "$GITHUB_WORKSPACE/$p/wbd-v4-server" \
  --raw-interface "$raw_iface" --local-ip "$raw_ip" --local-port 443 \
  --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
  --server-name wbd-v4.example.test \
  --route-key-hex-file "$tmp/route.hex" --users-file "$tmp/users.json" \
  --lease-pool 10.66.0.128/25 --tls-cert "$tmp/server-cert.pem" \
  --tls-key "$tmp/server-key.pem" --mode "$server_mode" --fec-profile 1 \
  >"$tmp/server.log" 2>&1 &
server_pid=$!
for i in $(seq 1 40);do
  if sudo -n ip link show wbdvs4 >/dev/null 2>&1 &&
     kill -0 "$server_pid" 2>/dev/null;then break;fi
  if ! kill -0 "$server_pid" 2>/dev/null;then
    echo "D2_S1_REAL_ORIGINAL_SERVER_EARLY_EXIT" >&2;exit 22
  fi
  sleep 0.4
done
sudo -n ip link show wbdvs4 >/dev/null 2>&1 || {
  echo "D2_S1_REAL_ORIGINAL_SERVER_TUN_NOT_CREATED" >&2; exit 23;
}
echo REAL_ORIGINAL_LINUX_SERVER_TUN_PASS >"$out/server-started.txt"
# The CI test App has no secret-bearing Intent or command-line parameters.
# Inject secrets as 0600 only to this disposable Android app UID sandbox.
phase=D2_S1_APP_PRIVATE_SECRETS
# The separate CI-only Root Probe App is the ONLY permitted UID route target.
# NEVER select KernelSU Manager or another installed application implicitly.
test -s out/apk/app-su.apk
test "$(cat out/apk/SOURCE)" = "$GITHUB_SHA"
(cd out/apk && sha256sum -c SHA256SUMS) >"$out/target-app-source-sha.txt"
adb install -r out/apk/app-su.apk >"$out/target-app-install.txt" 2>&1
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  adb install -r out/android-traffic-fixture/traffic-fixture.apk >"$out/b108-ordinary-app-install.txt" 2>&1
fi
adb shell pm path org.wbdnext.rootprobe >"$out/target-app-installed.txt" 2>&1
grep -q "^package:" "$out/target-app-installed.txt"
adb push "$tmp/password" /data/local/tmp/wbd-d2-pass.tmp \
  >"$out/push-password.txt" 2>&1
adb push "$tmp/route.hex" /data/local/tmp/wbd-d2-route.tmp \
  >"$out/push-route.txt" 2>&1
adb push "$tmp/server-cert.pem" /data/local/tmp/wbd-d2-ca.tmp \
  >"$out/push-ca.txt" 2>&1
# Avoid nested adb->su->sh expansion of App-UID/ownership checks. Check
# exact CI source before pushing, then run from original D1 root-owned stage.
# The script contains only fixed paths/permission rules, never credentials.
script=android/root-app/ci/x86-d2-install-credentials-android.sh
test -s "$script"
bash -n "$script"
adb push "$script" /data/local/tmp/wbd-d2-cred-stage.sh >"$out/push-stage-script.txt" 2>&1
script_sha="$(sha256sum "$script" | cut -d ' ' -f1)"
adb shell su -c 'sha256sum /data/local/tmp/wbd-d2-cred-stage.sh' >"$out/android-stage-script-sha.txt"
grep -Fq "$script_sha" "$out/android-stage-script-sha.txt"
adb shell su -c 'test -d /data/local/tmp/wbd-x86-ci'
adb shell su -c 'cp /data/local/tmp/wbd-d2-cred-stage.sh /data/local/tmp/wbd-x86-ci/wbd-d2-cred-stage.sh'
adb shell su -c 'chmod 700 /data/local/tmp/wbd-x86-ci/wbd-d2-cred-stage.sh'
adb shell su -c '/system/bin/sh /data/local/tmp/wbd-x86-ci/wbd-d2-cred-stage.sh' \
  >"$out/android-private-credential-stage.txt" 2>&1 || {
    echo "D2_S1_ANDROID_PRIVATE_CREDENTIAL_STAGE_FAIL" >&2
    # Output only fixed enums, never shell stderr that could leak metadata.
    grep -E '^D2_CI_(ROOT_|APP_|EPHEMERAL_)' "$out/android-private-credential-stage.txt" >&2 || true
    exit 43
  }
grep -Fxq 'D2_CI_APP_PRIVATE_SECRET_STAGING_PASS' "$out/android-private-credential-stage.txt"
echo D2_CI_APP_PRIVATE_SECRET_STAGING_PASS >"$out/secret-stage-enum.txt"
echo D2_S1_CI_EPHEMERAL_APP_SECRET_STAGE_PASS
if [[ "${WBD_ANDROID_LIFECYCLE:-0}" == 1 ]];then
  phase=D2_ANDROID_ROOT_LIFECYCLE
  source android/root-app/ci/x86-root-lifecycle.sh
  exit
fi
if [[ "${WBD_ANDROID_WIRING_MATRIX:-0}" == 1 ]];then
  phase=D2_ANDROID_SEVEN_MODE_WIRING
  source android/root-app/ci/x86-seven-mode-wiring.sh
  exit
fi
phase=D2_S1_PRODUCTION_ROOT_SERVICE
adb shell logcat -c >"$out/logcat-reset.txt" 2>&1 || true
start_args=()
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  start_args=(--es ci_target traffic --es ci_mode "${WBD_B109_MODE:-normal}")
  if [[ "${WBD_B110_SCENE:-}" == normal-dns ]];then start_args+=(--es ci_scenario tunnel_dns);fi
  if [[ "${WBD_B110_SCENE:-}" == normal-dns-relay ]];then start_args+=(--es ci_scenario tunnel_dns_relay);fi
  if [[ "${WBD_B110_SCENE:-}" == normal-managed ]];then
    start_args+=(--es ci_scenario managed_default)
  fi
  if [[ "${WBD_B110_SCENE:-}" == normal-reconnect ]];then start_args+=(--es ci_scenario auto_reconnect);fi
fi
adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity \
  --es ci_step start "${start_args[@]}" >"$out/start-activity.txt" 2>&1
grep -q 'Starting: Intent' "$out/start-activity.txt"
activity_requested=1
# Only production RootClientService fixed enums count. Actual Go/Rust
# may fail before TLS due emulator NAT; we record the exact reached stage.
# D2-S1 established real original TUN/AF_PACKET. Unlike a pure smoke
# test, allow bounded original FakeTCP SYN/SYNACK and TLS/lease retries
# BEFORE requesting Stop. A RAW-ready marker alone is never TLS PASS.
raw_first=0
for i in $(seq 1 80);do
  adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' \
    >"$out/app-diagnostic-enums.txt" 2>&1 || true
  if [[ "$raw_first" == 0 ]] &&
     grep -Fq 'ORIGINAL_GO_RAW_SOCKET_READY' "$out/app-diagnostic-enums.txt";then
    raw_first="$i"
    echo "D2_S1_REAL_ORIGINAL_ANDROID_TUN_RAW_CONFIGURED_PASS"
  fi
  if [[ "${WBD_D2_PREAUTH_ONLY:-0}" == 1 && "$raw_first" != 0 ]] &&
     grep -Fq 'ORIGINAL_GO_TUN_KERNEL_CONFIGURED' "$out/app-diagnostic-enums.txt";then
    echo "D2_S1_PREAUTH_ONLY_REACHED_REAL_TUN_RAW_NO_RETRY"
    break
  fi
  if grep -Fq 'NATIVE_M4_AND_UID_READY' "$out/app-diagnostic-enums.txt";then
    echo "D2_S1_AUTHENTICATED_ORIGINAL_RUST_M4_AND_UID_READY_OBSERVED"
    break
  fi
  if grep -Eq 'ROOT_PROCESS_EXIT_(NONZERO|139|132)|ROOT_LAUNCH_FAILED|START_REFUSED|ORIGINAL_ROOT_SERVICE_CI_START_BLOCKED' \
      "$out/app-diagnostic-enums.txt";then
    echo "D2_S1_ORIGINAL_GO_EXIT_BEFORE_READY"
    grep -E "ORIGINAL_GO_POSTAUTH_ROUTE_FAILED_|ORIGINAL_GO_DNS6_(START_FAILED|UNAVAILABLE)_|ORIGINAL_GO_POSTAUTH_DNS[46]_READY|ORIGINAL_GO_POSTAUTH_IPV6_DROP_READY" "$out/app-diagnostic-enums.txt" || true
    break
  fi
  # 45s after first true RAW ready: original retries had meaningful time,
  # but CI cannot silently hang indefinitely behind emulator NAT.
  if [[ "$raw_first" != 0 ]] && (( i - raw_first >= 45 ));then
    echo "D2_S1_BOUNDED_AUTH_OBSERVATION_DONE"
    break
  fi
  sleep 1
done
if grep -Fq 'ORIGINAL_GO_TCP_SYNACK_SEEN' "$out/app-diagnostic-enums.txt";then
  echo "D2_S1_ANDROID_ORIGINAL_GO_REAL_PEER_SYNACK_OBSERVED"
else
  echo "D2_S1_ANDROID_SYNACK_NOT_PROVEN"
fi
if grep -Fq 'AUTHENTICATED_LEASE_OS_READBACK' "$out/app-diagnostic-enums.txt";then
  echo "D2_S1_ANDROID_ORIGINAL_AUTH_LEASE_OS_READBACK_OBSERVED"
else
  echo "D2_S1_ANDROID_ORIGINAL_AUTH_LEASE_NOT_PROVEN"
fi
# Write only exact original server milestone enums, never secret-bearing
# stdout/stderr. Auto-lease enters the shared server owner even in Normal.
# Allow the peer's independent ready publication to follow the client.
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  for _ in $(seq 1 30);do
    if grep -Eq 'V4_PUBLIC_MULTI_SESSION_READY|V4_ORIGINAL_GO_SERVER_NATIVE_READY|V4_PUBLIC_GAME_MULTI_GROUP_READY' "$tmp/server.log";then break;fi
    if ! kill -0 "$server_pid" 2>/dev/null;then break;fi
    sleep .2
  done
fi
: >"$out/server-stage-enums.txt"
for marker in V4_ORIGINAL_GO_SERVER_NATIVE_READY V4_PUBLIC_MULTI_SESSION_READY V4_PUBLIC_SHARED_TUN_STOP_DRAINED V4_PUBLIC_ORIGINAL_SERVER_RAW_INITIAL_SYN_RX V4_PUBLIC_ORIGINAL_SERVER_RAW_SYNACK_TX_OK V4_PUBLIC_GAME_MULTI_GROUP_READY;do
  if grep -Fq "$marker" "$tmp/server.log";then
    echo "$marker" >>"$out/server-stage-enums.txt"
  fi
done
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  # Original Game server logs committed lane ordinals. Print only count,
  # not endpoints or original protected session material.
  case "${WBD_B109_MODE:-normal}" in
    game2*) expected_lanes=2;;
    game4*) expected_lanes=4;;
    *) expected_lanes=0;;
  esac
  if (( expected_lanes > 0 ));then
    if grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=$expected_lanes original_tls=1 rust_m4=1" "$tmp/server.log";then
      printf 'V4_ORIGINAL_GO_GAME_NATIVE_READY lanes=%s\n' "$expected_lanes" >>"$out/server-stage-enums.txt"
    fi
    for lane in $(seq 1 "$expected_lanes");do
      if grep -Fq "V4_PUBLIC_GAME_GROUP_LANE_READY role=server lanes=$expected_lanes lane=$lane " "$tmp/server.log";then
        printf 'B109_SERVER_COMMITTED_LANE %s\n' "$lane" >>"$out/server-stage-enums.txt"
      fi
    done
  fi
  cat "$out/server-stage-enums.txt"
fi
if ! grep -Fq 'ORIGINAL_ROOT_SERVICE_START_REQUESTED' "$out/app-diagnostic-enums.txt" ||
   ! grep -Fq 'ROOT_PROCESS_LAUNCHED' "$out/app-diagnostic-enums.txt" ||
   ! grep -Fq 'ORIGINAL_GO_TUN_KERNEL_CONFIGURED' "$out/app-diagnostic-enums.txt" ||
   ! grep -Fq 'ORIGINAL_GO_RAW_SOCKET_READY' "$out/app-diagnostic-enums.txt";then
  echo "D2_S1_ORIGINAL_ANDROID_ROOT_TUN_RAW_NOT_PROVEN" >&2
  exit 24
fi
phase=D2_S1_PRODUCTION_TUN_RAW_PASS
echo "D2_S1_ORIGINAL_ANDROID_PRODUCTION_ROOT_SERVICE_TUN_RAW_PASS"
if [[ "${WBD_B108_CARRIER:-0}" == 1 ]];then
  phase=B108_ORIGINAL_REMOTE_AUTH
  for marker in ORIGINAL_GO_MODE_READBACK_MATCHED AUTHENTICATED_LEASE_OS_READBACK NATIVE_M4_AND_UID_READY;do
    grep -Fq "$marker" "$out/app-diagnostic-enums.txt" || { echo "B108_NOT_PROVEN $marker";exit 50; }
  done
  # Normal auto-lease uses the original multi-session Normal owner.
  # Game shared mode has its own original committed group/lane receipts.
  if (( expected_lanes == 0 ));then
    grep -Fq ORIGINAL_GO_TCP_SYNACK_SEEN "$out/app-diagnostic-enums.txt" || { echo B110_NORMAL_SYNACK_NOT_PROVEN;exit 50; }
    for marker in V4_PUBLIC_ORIGINAL_SERVER_RAW_INITIAL_SYN_RX V4_PUBLIC_ORIGINAL_SERVER_RAW_SYNACK_TX_OK V4_PUBLIC_MULTI_SESSION_READY;do
      grep -Fqx "$marker" "$out/server-stage-enums.txt" || { echo "B109_SERVER_NOT_PROVEN $marker";exit 50; }
    done
  else
    # Game does not emit Normal's standalone SYNACK MSS log. Require
    # the real Game-specific production READY plus each actual cold wire
    # direction on both relay sides, and the original peer lane commits.
    grep -Fq ORIGINAL_GO_GAME_NATIVE_READY "$out/app-diagnostic-enums.txt" || { echo B110_GAME_CLIENT_READY_NOT_PROVEN;exit 50; }
    for spec in "host SYN rx" "host SYNACK tx" "guest SYN tx" "guest SYNACK rx";do
      read -r side kind direction <<<"$spec"
      grep -Fqx "B110_WIRE_$kind role=$side direction=$direction distinct=$expected_lanes" "$out/b108-$side-relay.log" || { echo "B110_GAME_WIRE_NOT_PROVEN $spec";exit 50; }
    done
    for marker in V4_PUBLIC_GAME_MULTI_GROUP_READY "V4_ORIGINAL_GO_GAME_NATIVE_READY lanes=$expected_lanes";do
      grep -Fqx "$marker" "$out/server-stage-enums.txt" || { echo "B109_SERVER_NOT_PROVEN $marker";exit 50; }
    done
    for lane in $(seq 1 "$expected_lanes");do
      grep -Fqx "B109_SERVER_COMMITTED_LANE $lane" "$out/server-stage-enums.txt" || { echo "B109_SERVER_LANE_NOT_PROVEN $lane";exit 50; }
    done
    printf 'PASS\n' >"$out/b110-game-wire-pass.txt"
    echo "B110_GAME_REAL_WIRE_AND_AUTH_PASS lanes=$expected_lanes"
  fi
  for side in host guest;do
    grep -Fq "B108_RELAY_FIRST_TX $side" "$out/b108-$side-relay.log"
    grep -Fq "B108_RELAY_FIRST_RX $side" "$out/b108-$side-relay.log"
  done
  printf 'PASS\n' >"$out/b109-remote-auth-result.txt"
  echo B109_REAL_ORIGINAL_REMOTE_AUTH_PASS "${WBD_B109_MODE:-normal}"
  phase=B108_ORIGINAL_REMOTE_APP_BUSINESS
  if [[ "${WBD_B110_SCENE:-}" == *-loss ]];then
    # Only this disposable host helper receives the test loss signal.
    sudo -n pkill -USR1 -x b108-wire-relay
    for _ in $(seq 1 20);do grep -Fq B111_DOWNLINK_LOSS_ARMED "$out/b108-host-relay.log" && break;sleep .2;done
    grep -Fq B111_DOWNLINK_LOSS_ARMED "$out/b108-host-relay.log"
  fi
  b108_traffic
  if [[ "${WBD_B110_SCENE:-}" == fec-*-loss ]];then
    # Four additional ordinary bursts at five-second intervals: the
    # authenticated receiver quality windows can mature while real
    # bidirectional business remains active.
    cp "$out/b108-traffic.txt" "$out/b112-traffic-1.txt"
    for round in 2 3 4 5;do
      sleep 5
      b108_traffic
      cp "$out/b108-traffic.txt" "$out/b112-traffic-$round.txt"
    done
    echo B112_FIVE_ORDINARY_BURSTS_PASS
  fi
  printf 'PASS\n' >"$out/b108-remote-app-result.txt"
  case "${WBD_B110_SCENE:-}" in
    normal-dns|normal-dns-relay) phase=B110_TUNNEL_DNS;b110_dns;;
    normal-managed)
      phase=B121_MANAGED_DEFAULT
      for marker in ROUTE_SCOPE_ALL_ORDINARY_APPS_IPV4 ORIGINAL_GO_POSTAUTH_DNS4_READY ORIGINAL_GO_POSTAUTH_IPV6_DROP_READY;do
        grep -Fq "$marker" "$out/app-diagnostic-enums.txt" || { echo "B121_MANAGED_NOT_READY $marker";exit 54; }
      done
      if grep -Eq "ORIGINAL_GO_POSTAUTH_DNS6_READY|ORIGINAL_GO_DNS6_(START_FAILED|UNAVAILABLE)_" "$out/app-diagnostic-enums.txt";then echo B123_UNEXPECTED_DNS6;exit 54;fi
      adb shell "su -c 'test ! -e /sys/class/net/wbd_dns6 && test ! -e /data/local/tmp/wbd-next-root/system-dns6-journal.json'"
      echo B123_IPV4_ONLY_NO_DNS6_OWNER_PASS
      b110_dns
      echo B123_MANAGED_ALL_APPS_REAL_AUTH_BUSINESS_DNS_PASS;;
    normal-reconnect) phase=B110_PRODUCTION_RECONNECT;b110_reconnect;;
  esac
  adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step stop >"$out/stop-activity.txt"
  stop_count=1
  if [[ "${WBD_B110_SCENE:-}" == normal-reconnect ]];then stop_count=2;fi
  for _ in $(seq 1 40);do
    adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' >"$out/app-diagnostic-enums.txt"
    if [[ "$(grep -c OWNER_CLEANUP_FINISHED "$out/app-diagnostic-enums.txt" || true)" -ge "$stop_count" ]];then break;fi
    sleep .5
  done
  [[ "$(grep -c OWNER_CLEANUP_FINISHED "$out/app-diagnostic-enums.txt" || true)" -ge "$stop_count" ]]
  for marker in ORIGINAL_GO_RUST_STOP_JOINED ORIGINAL_GO_UID_ROUTE_STOP_DRAINED OWNER_CLEANUP_FINISHED;do
    if [[ "$(grep -c "$marker" "$out/app-diagnostic-enums.txt" || true)" -lt "$stop_count" ]];then echo "B108_STOP_NOT_PROVEN $marker";exit 51;fi
  done
  if (( expected_lanes > 0 ));then
    grep -Fq ORIGINAL_GO_GAME_GROUP_STOP_JOINED "$out/app-diagnostic-enums.txt" || { echo B110_GAME_JOINED_STOP_NOT_PROVEN;exit 51; }
  fi
  adb shell "su -c 'test ! -e /sys/class/net/wbdv40 && test ! -e /data/local/tmp/wbd-next-root/route-journal.json'"
  adb shell "su -c 'ip -4 rule show'" >"$out/b108-stop-rules.txt"
  adb shell "su -c 'ip -4 route show table all'" >>"$out/b108-stop-rules.txt"
  adb shell "su -c 'iptables -w 2 -t nat -S OUTPUT'" >>"$out/b108-stop-rules.txt"
  adb shell "su -c 'iptables -w 2 -S OUTPUT'" >>"$out/b108-stop-rules.txt"
  if grep -Eq 'lookup 19842( |$)|table 19842( |$)|wbd-next-root-rst-v1|wbd-next-root-(app-tcp-dns|system-dns)-v1' "$out/b108-stop-rules.txt";then exit 52;fi
  if [[ "${WBD_B110_SCENE:-}" == normal-managed ]];then
    adb shell "su -c 'test ! -e /data/local/tmp/wbd-next-root/ipv6-carrier-journal.json && test ! -e /data/local/tmp/wbd-next-root/system-dns-journal.json && test ! -e /data/local/tmp/wbd-next-root/system-dns6-journal.json && test ! -e /sys/class/net/wbd_dns0 && test ! -e /sys/class/net/wbd_dns6'"
    adb shell "su -c 'ip -6 rule show; ip -6 route show table all'" >>"$out/b108-stop-rules.txt"
    if grep -Eq "(lookup|table) 1984[567]( |$)|wbd-next-root-system-dns6-v1" "$out/b108-stop-rules.txt";then exit 54;fi
    echo B121_MANAGED_ALL_APPS_STOP_PASS
  fi
  activity_requested=0
  printf 'PASS\n' >"$out/b108-stop-result.txt"
  if [[ "${WBD_B110_SCENE:-}" == *-loss ]];then
    phase=B111_FEC_RECOVERY
    sudo -n pkill -TERM -x b108-wire-relay
    for _ in $(seq 1 20);do grep -Eq 'B111_DOWNLINK_LOSS_COUNTS eligible=[0-9]+ dropped=[1-9][0-9]*' "$out/b108-host-relay.log" && break;sleep .2;done
    grep -E 'B111_DOWNLINK_LOSS_COUNTS eligible=[0-9]+ dropped=[1-9][0-9]*' "$out/b108-host-relay.log"
    if (( expected_lanes == 0 ));then
      grep -F 'ORIGINAL_ANDROID_FIXED_M4_FINAL ' "$out/app-diagnostic-enums.txt" | tail -1 | tee "$out/b112-native-fec-final.txt"
      grep -Fq ORIGINAL_FEC_RECOVERED_TUN_OBSERVED "$out/app-diagnostic-enums.txt" || { echo B111_FEC_RECOVERED_TUN_NOT_PROVEN;exit 53; }
      echo B111_ORIGINAL_FEC_RECOVERED_TUN_PASS
      if grep -Eq ' reports=[1-9][0-9]* ' "$out/b112-native-fec-final.txt";then echo B112_REAL_REVERSE_QUALITY_PASS;fi
      if grep -Eq ' mature=[1-9][0-9]* applied=[1-9][0-9]*$' "$out/b112-native-fec-final.txt";then echo B112_NATIVE_MATURE_APPLIED_PASS;fi
      if [[ "${WBD_B114_FINAL_REGRESSION:-0}" == 1 ]];then
        grep -Eq ' reports=[1-9][0-9]* ' "$out/b112-native-fec-final.txt"
        grep -Eq ' mature=[1-9][0-9]* applied=[1-9][0-9]*$' "$out/b112-native-fec-final.txt"
      fi
    else
      grep -Fq ORIGINAL_GAME_FEC_RECOVERED_CANDIDATE_OBSERVED "$out/app-diagnostic-enums.txt" || { echo B111_GAME_FEC_CANDIDATE_NOT_PROVEN;exit 53; }
      echo B111_ORIGINAL_GAME_FEC_CANDIDATE_AND_BUSINESS_PASS
    fi
    printf 'PASS\n' >"$out/b111-loss-result.txt"
  fi
  phase=B108_ORIGINAL_REMOTE_APP_AND_STOP_PASS
  echo "$phase"
else
  echo "D2_ANDROID_ORIGINAL_TLS_AUTH_LEASE_M4_APP_DATA_NOT_YET_PROVEN"
fi
