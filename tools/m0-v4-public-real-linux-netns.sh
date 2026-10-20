#!/usr/bin/env bash
# Actual original Go V4 public client and server, no Go/Rust test binary.
# 2 isolated namespaces + real raw veth + original TLS + scoped native
# Rust M1/M3/M4 owner + real TUN + kernel UDP echo + signal/Stop cleanup.
set -euo pipefail
ROOT="${1:?expected argument: directory containing the V4 client, server and Rust native library}"
ROOT="$(realpath "$ROOT")"
LOSS="${WBD_V4_PUBLIC_KERNEL_LOSS:-0}"
if [[ "$LOSS" != 0 && "$LOSS" != 1 ]];then
  echo "invalid exact public V4 netem loss selector" >&2;exit 2
fi
PACKETS=5
if [[ "$LOSS" == 1 ]];then PACKETS=512;fi
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
sudo -n ip netns exec "$NSS" env WBD_REAL_COUNT="$PACKETS" python3 -u -c '
import socket,time,os
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.1",45901));s.settimeout(28)
try:
    for i in range(int(os.environ["WBD_REAL_COUNT"])):
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
# Real LOSS is imposed on the actual Linux underlay AFTER both original
# Go TLS handshakes and both native Rust/M4 driver bindings are READY.
# The exact existing CLI binaries, not an alternative sender, handle it.
if [[ "$LOSS" == 1 ]];then
  sudo -n ip netns exec "$NSC" tc qdisc add dev wbdvc0 root netem loss 1%
  sudo -n ip netns exec "$NSS" tc qdisc add dev wbdvs0 root netem loss 1%
fi
sudo -n ip netns exec "$NSC" env WBD_REAL_COUNT="$PACKETS" python3 -u -c '
import socket,time,os
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.2",45902));s.settimeout(12)
for i in range(int(os.environ["WBD_REAL_COUNT"])):
    msg=(b"WBD_REAL_V4_ORIGINAL_GO/"+str(i).encode()+b"/"+bytes([i%256])*64)
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
test "$(grep -c 'M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK' "$ART/public-v4-normal-business.log")" -eq "$PACKETS"
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/client.log"
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=server' "$TMP/server.log"
if [[ "$LOSS" == 1 ]];then
  sudo -n ip netns exec "$NSC" tc -s qdisc show dev wbdvc0 >"$TMP/kernel-client-netem.txt"
  sudo -n ip netns exec "$NSS" tc -s qdisc show dev wbdvs0 >"$TMP/kernel-server-netem.txt"
  python3 - "$TMP" "$ART" <<'PY'
import pathlib,re,sys
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2])
def read(name):return (p/name).read_text()
drops=sum(sum(map(int,re.findall(r'dropped (\\d+)',read(n)))) for n in
    ('kernel-client-netem.txt','kernel-server-netem.txt'))
repairs=sum(sum(map(int,re.findall(r'original_frozen_retransmitted=(\\d+)',read(n))))
    for n in ('client.log','server.log'))
copied=sum(sum(map(int,re.findall(r'real_first_copy=(\\d+)',read(n))))
    for n in ('client.log','server.log'))
acks=sum(sum(map(int,re.findall(r'authenticated_ack=(\\d+)',read(n))))
    for n in ('client.log','server.log'))
assert drops>0,f"kernel 1% dropped=0 not a real loss proof"
assert copied>=1024,f"true first-copy count wrong: {copied}"
assert repairs>0,f"no real M2 original-frozen retransmissions: {repairs}"
assert acks>0,f"no real peer AEAD kind1 receipt retirement: {acks}"
marker=f"M0_V4_PUBLIC_REAL_1PCT_M2_FROZEN_BIDIRECTIONAL_RECOVERY_PASS original_tls=1 real_udp_echo=512 kernel_netem_drops={drops} native_m2_frozen_retransmitted={repairs} authenticated_m2_acks={acks} actual_kernel_first_copied={copied} Stop_drained_both=1"
(out/'v4-public-1pct-authentic-M2-recovery.log').write_text(marker+'\\n')
print(marker)
PY
else
  echo 'M0_PUBLIC_ORIGINAL_GO_V4_NORMAL_OFF_TWO_REAL_CLI_TLS_RUST_M4_TUN_UDP_STOP_PASS'
fi
