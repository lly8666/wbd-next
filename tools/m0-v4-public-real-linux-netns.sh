#!/usr/bin/env bash
# Actual original Go V4 public client and server, no Go/Rust test binary.
# 2 isolated namespaces + real raw veth + original TLS + scoped native
# Rust M1/M3/M4 owner + real TUN + kernel UDP echo + signal/Stop cleanup.
set -euo pipefail
ROOT="${1:?expected argument: directory containing the V4 client, server and Rust native library}"
ROOT="$(realpath "$ROOT")"
test -x "$ROOT/wbd-v4-client" && test -x "$ROOT/wbd-v4-server"
test -s "$ROOT/libwbd_engine.so" && test -c /dev/net/tun
: "${GITHUB_RUN_ID:?source-locked GitHub Actions only}"
ART="${GITHUB_WORKSPACE:?}/fixed-kernel-result"
TMP="${RUNNER_TEMP:?}/wbd-v4-public-${GITHUB_RUN_ID}"
mkdir -m 0700 -p "$TMP"
NSC="v4cl_${GITHUB_RUN_ID}" NSS="v4sv_${GITHUB_RUN_ID}"
PIDC='' PIDS='' APPS=''
cleanup(){
  set +e
  for p in "$PIDC" "$PIDS" "$APPS"; do
    if [[ -n "$p" ]]; then sudo -n kill -TERM "$p" 2>/dev/null || true; fi
  done
  sleep 0.3
  for ns in "$NSC" "$NSS"; do
    sudo -n ip netns del "$ns" 2>/dev/null || true
  done
  rm -rf "$TMP"
}
trap cleanup EXIT
sudo -n ip netns add "$NSC"
sudo -n ip netns add "$NSS"
sudo -n ip link add wbdvc0 type veth peer name wbdvs0
sudo -n ip link set wbdvc0 netns "$NSC"
sudo -n ip link set wbdvs0 netns "$NSS"
sudo -n ip -n "$NSC" link set lo up
sudo -n ip -n "$NSS" link set lo up
sudo -n ip -n "$NSC" addr add 10.25.0.2/24 dev wbdvc0
sudo -n ip -n "$NSS" addr add 10.25.0.1/24 dev wbdvs0
sudo -n ip -n "$NSC" link set wbdvc0 up
sudo -n ip -n "$NSS" link set wbdvs0 up
sudo -n ip netns exec "$NSC" iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
sudo -n ip netns exec "$NSS" iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
  -keyout "$TMP/server-key.pem" -out "$TMP/server-cert.pem" \
  -subj '/CN=wbd-v4.example.test' -addext 'subjectAltName=DNS:wbd-v4.example.test' \
  >"$TMP/certificate-create.log" 2>&1
chmod 0600 "$TMP/server-key.pem"
ROUTE='aabbccddeeff0011223344556677889900112233445566778899aabbccddeeff'
TUNNEL='102030405060708090a0b0c0d0e0f001'
USER='v4qualified'
PASS='v4-real-original-tls-credential-20261020'
# Startup uses exactly the production binaries and unmodified original Go
# TLS/FakeTCP code. PID belongs to the exec'd process in each netns.
sudo -n ip netns exec "$NSS" bash -c "
  echo \$\$ > '$TMP/server.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
    --raw-interface wbdvs0 --local-ip 10.25.0.1 --local-port 443 \
    --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
    --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
    --username '$USER' --password '$PASS' --tunnel-id '$TUNNEL' \
    --tls-cert '$TMP/server-cert.pem' --tls-key '$TMP/server-key.pem' \
    --mode normal" >"$TMP/server.log" 2>&1 &
PIDS=$!
sleep 1
sudo -n ip netns exec "$NSC" bash -c "
  echo \$\$ > '$TMP/client.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-client' \
    --raw-interface wbdvc0 --local-ip 10.25.0.2 --local-port 41031 \
    --peer-ip 10.25.0.1 --peer-port 443 \
    --tun-name wbdvc4 --tun-ipv4 10.66.0.2/24 \
    --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
    --username '$USER' --password '$PASS' --tunnel-id '$TUNNEL' \
    --mode normal" >"$TMP/client.log" 2>&1 &
PIDC=$!
# Real server-side Python socket only ECHOES a real UDP packet the Linux
# kernel accepted from the owner TUN. It never makes fake TCP ciphertext.
sudo -n ip netns exec "$NSS" python3 -u -c '
import socket,time
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.1",45901));s.settimeout(28)
try:
    for i in range(5):
        data,src=s.recvfrom(8192)
        assert data.startswith(b"WBD_REAL_V4_ORIGINAL_GO")
        s.sendto(b"V4_SERVER_APP_ECHO/"+data,src)
finally:s.close()
' >"$TMP/echo.log" 2>&1 &
APPS=$!
# Allow real original Go TLS and Rust M4 worker start; fail if no actual
# readiness within a bounded time. Never infer readiness from config.
ready=0
for i in {1..40}; do
  if grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$TMP/client.log" &&
     grep -q 'V4_ORIGINAL_GO_SERVER_NATIVE_READY' "$TMP/server.log"; then
    ready=1;break
  fi
  sleep 0.25
done
if [[ "$ready" != 1 ]];then
  echo 'M0_V4_PUBLIC_REAL_CLIENT_SERVER_NOT_READY' >&2
  sed -E 's/(credential|password|secret|token|key)[=:][^ ]+/\1=[REDACTED]/Ig' "$TMP/client.log" "$TMP/server.log" | tail -65 >&2
  exit 1
fi
sudo -n ip netns exec "$NSC" python3 -u -c '
import socket,time
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.2",45902));s.settimeout(12)
for i in range(5):
    msg=(b"WBD_REAL_V4_ORIGINAL_GO/"+str(i).encode()+b"/"+bytes([i])*64)
    s.sendto(msg,("10.66.0.1",45901))
    data,src=s.recvfrom(8192)
    assert data==b"V4_SERVER_APP_ECHO/"+msg,(i,data)
    assert src[0]=="10.66.0.1"
    print("M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK",i,flush=True)
s.close()
' >"$ART/public-v4-normal-business.log" 2>&1
cat "$ART/public-v4-normal-business.log"
# Confirm clean signal-to-actual-Rust-Stop; no test-only positive receipt.
sudo -n kill -TERM "$(cat "$TMP/client.pid")"
sudo -n kill -TERM "$(cat "$TMP/server.pid")"
for i in {1..25};do
  if ! sudo -n kill -0 "$(cat "$TMP/client.pid")" 2>/dev/null &&
     ! sudo -n kill -0 "$(cat "$TMP/server.pid")" 2>/dev/null;then break;fi
  sleep 0.2
done
if sudo -n kill -0 "$(cat "$TMP/client.pid")" 2>/dev/null ||
   sudo -n kill -0 "$(cat "$TMP/server.pid")" 2>/dev/null;then
  echo 'M0_V4_REAL_RUST_STOP_JOIN_NOT_COMPLETE' >&2;exit 1
fi
# Sensitive logs contain NO TLS secret/cold/exporter keys. Persist only the
# exact readiness and packet count; erase ephemeral TLS files and logs.
grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$TMP/client.log"
grep -q 'V4_ORIGINAL_GO_SERVER_NATIVE_READY' "$TMP/server.log"
test "$(grep -c 'M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK' "$ART/public-v4-normal-business.log")" -eq 5
echo 'M0_PUBLIC_ORIGINAL_GO_V4_NORMAL_OFF_TWO_REAL_CLI_TLS_RUST_M4_TUN_UDP_STOP_PASS'
