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
activity_requested=0
phase=D2_S1_INIT
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
d={"schema":"wbd-android-x86-original-root-d2-s1/v1",
 "source":os.environ["GITHUB_SHA"],"phase":os.environ["WBD_D2_PHASE"],
 "exit_code":int(os.environ["WBD_D2_RC"]),
 "linux_real_original_server":"PASS" if (p/"server-started.txt").exists() else "NOT_PROVEN",
 "ephemeral_app_private_secrets":"PASS" if (p/"secret-stage-enum.txt").exists() else "NOT_PROVEN",
 "signed_app_requested_original_root_service":"PASS" if has("ORIGINAL_ROOT_SERVICE_START_REQUESTED") else "NOT_PROVEN",
 "original_go_root_process_launched":"PASS" if has("ROOT_PROCESS_LAUNCHED") else "NOT_PROVEN",
 "original_android_tun_configured":"PASS" if has("ORIGINAL_GO_TUN_KERNEL_CONFIGURED") else "NOT_PROVEN",
 "original_android_raw_af_packet":"PASS" if has("ORIGINAL_GO_RAW_SOCKET_READY") else "NOT_PROVEN",
 "real_peer_synack":"PASS" if has("ORIGINAL_GO_TCP_SYNACK_SEEN") else "NOT_PROVEN",
 "tls_authenticated_32_lease":"PASS" if has("AUTHENTICATED_LEASE_OS_READBACK") and
    "V4_ORIGINAL_GO_SERVER_NATIVE_READY" in server else "NOT_PROVEN",
 "original_rust_m4_and_uid_ready":"PASS" if has("NATIVE_M4_AND_UID_READY") else "NOT_PROVEN",
 "tcp_udp_bidirectional_application_data":"NOT_RUN",
 "owned_stop_verified":"PASS" if has("ORIGINAL_GO_RUST_STOP_JOINED") and
    has("ORIGINAL_GO_UID_ROUTE_STOP_DRAINED") else "NOT_PROVEN",
 "route_rollback_kernel_proved":"NOT_RUN",
 "system_dns_takeover":"NOT_RUN"}
(p/"receipt.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print("D2_S1_ORIGINAL_ROOT_STAGED",
 d["linux_real_original_server"],
 d["original_android_tun_configured"],
 d["original_android_raw_af_packet"],
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
  if [[ -n "$server_pid" ]];then
    kill -TERM "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  # No default route/DNS/ip rule changes. Tear down only our own ephemeral
  # host TUN if original Go Stop failed; the CI host is disposable.
  sudo -n ip link del wbdvs4 >/dev/null 2>&1 || true
  receipt "$rc" || true
  rm -rf "$tmp"
  exit "$rc"
}
trap cleanup EXIT
umask 077
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
phase=D2_S1_ORIGINAL_LINUX_SERVER
# Android Emulator 10.0.2.2 maps to host loopback. Whether its user-mode
# NAT preserves raw FakeTCP SYN/SYNACK is explicitly unproven; never call it
# a TLS PASS until BOTH original server and Android receipts prove it.
timeout --signal=TERM --kill-after=5s 180s sudo -n env \
  LD_LIBRARY_PATH="$GITHUB_WORKSPACE/$p" "$GITHUB_WORKSPACE/$p/wbd-v4-server" \
  --raw-interface lo --local-ip 127.0.0.1 --local-port 443 \
  --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
  --server-name wbd-v4.example.test \
  --route-key-hex-file "$tmp/route.hex" --users-file "$tmp/users.json" \
  --lease-pool 10.66.0.128/25 --tls-cert "$tmp/server-cert.pem" \
  --tls-key "$tmp/server-key.pem" --mode normal --fec-profile 1 \
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
phase=D2_S1_PRODUCTION_ROOT_SERVICE
adb shell logcat -c >"$out/logcat-reset.txt" 2>&1 || true
adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity \
  --es ci_step start >"$out/start-activity.txt" 2>&1
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
  if grep -Fq 'NATIVE_M4_AND_UID_READY' "$out/app-diagnostic-enums.txt";then
    echo "D2_S1_AUTHENTICATED_ORIGINAL_RUST_M4_AND_UID_READY_OBSERVED"
    break
  fi
  if grep -Eq 'ROOT_PROCESS_EXIT_(NONZERO|139|132)|ROOT_LAUNCH_FAILED|START_REFUSED|ORIGINAL_ROOT_SERVICE_CI_START_BLOCKED' \
      "$out/app-diagnostic-enums.txt";then
    echo "D2_S1_ORIGINAL_GO_EARLY_EXIT_BEFORE_AUTH_HANDSHAKE"
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
# Write only exact real original server milestone types. Do not upload
# stdout/stderr, SNI, account, key, cert or traffic bytes.
: >"$out/server-stage-enums.txt"
for marker in V4_ORIGINAL_GO_SERVER_NATIVE_READY V4_PUBLIC_MULTI_SESSION_READY V4_PUBLIC_SHARED_TUN_STOP_DRAINED;do
  if grep -Fq "$marker" "$tmp/server.log";then
    echo "$marker" >>"$out/server-stage-enums.txt"
  fi
done
if ! grep -Fq 'ORIGINAL_ROOT_SERVICE_START_REQUESTED' "$out/app-diagnostic-enums.txt" ||
   ! grep -Fq 'ROOT_PROCESS_LAUNCHED' "$out/app-diagnostic-enums.txt" ||
   ! grep -Fq 'ORIGINAL_GO_TUN_KERNEL_CONFIGURED' "$out/app-diagnostic-enums.txt" ||
   ! grep -Fq 'ORIGINAL_GO_RAW_SOCKET_READY' "$out/app-diagnostic-enums.txt";then
  echo "D2_S1_ORIGINAL_ANDROID_ROOT_TUN_RAW_NOT_PROVEN" >&2
  exit 24
fi
phase=D2_S1_PRODUCTION_TUN_RAW_PASS
echo "D2_S1_ORIGINAL_ANDROID_PRODUCTION_ROOT_SERVICE_TUN_RAW_PASS"
echo "D2_ANDROID_ORIGINAL_TLS_AUTH_LEASE_M4_APP_DATA_NOT_YET_PROVEN"
