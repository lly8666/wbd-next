#!/usr/bin/env bash
# Two isolated real Linux ARM64 V4 CLI endpoints, not an emulated packet fixture.
set -euo pipefail
test "$(uname -m)" = aarch64
: "$GITHUB_RUN_ID" "$GITHUB_SHA" "$GITHUB_WORKSPACE"
bundle="$GITHUB_WORKSPACE/arm64-public-bundle"
out="$GITHUB_WORKSPACE/arm64-netns-result"
mkdir -p "$out"
(cd "$bundle" && sha256sum -c SHA256SUMS)
# GitHub artifact ZIP extraction does not preserve executable mode.
# chmod changes metadata only, leaving the source-checked binary SHA256 intact.
chmod 0755 "$bundle/wbd-v4-client" "$bundle/wbd-v4-server"
python3 - "$bundle/manifest.json" "$GITHUB_SHA" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
assert m["source"]==sys.argv[2] and m["architecture"]=="aarch64",m
PY
# Exercise the real executable and dynamic loader, before privileged work.
for cmd in wbd-v4-client wbd-v4-server; do
  set +e
  timeout 5s env LD_LIBRARY_PATH="$bundle" "$bundle/$cmd" --help >"$out/$cmd-help.log" 2>&1
  rc=$?
  set -e
  if [ "$rc" -eq 124 ] || ! grep -q 'Usage of' "$out/$cmd-help.log"; then
    echo "ARM64_BIN_LOAD_FAILURE cmd=$cmd rc=$rc"; exit 1
  fi
done
if [ ! -c /dev/net/tun ] || ! command -v ip >/dev/null || ! command -v ping >/dev/null; then
  echo 'ARM64_OS_BLOCKED tun/ip/ping missing'; exit 77
fi
client_ns="wac$GITHUB_RUN_ID"
server_ns="was$GITHUB_RUN_ID"
client_made=0
server_made=0
stop_namespace(){
  ns="$1"
  for pid in $(sudo -n ip netns pids "$ns" 2>/dev/null || true); do
    if [[ "$pid" =~ ^[0-9]+$ ]]; then sudo -n kill -TERM "$pid" 2>/dev/null || true; fi
  done
}
cleanup(){
  set +e
  if [ "$client_made" -eq 1 ]; then stop_namespace "$client_ns"; fi
  if [ "$server_made" -eq 1 ]; then stop_namespace "$server_ns"; fi
  sleep 1
  if [ "$client_made" -eq 1 ]; then sudo -n ip netns del "$client_ns"; fi
  if [ "$server_made" -eq 1 ]; then sudo -n ip netns del "$server_ns"; fi
}
trap cleanup EXIT
if ! sudo -n ip netns add "$client_ns"; then
  echo 'ARM64_OS_BLOCKED CAP_NET_ADMIN namespace unavailable'; exit 77
fi
client_made=1
sudo -n ip netns add "$server_ns"
server_made=1
sudo -n ip link add v4ac type veth peer name v4as
sudo -n ip link set v4ac netns "$client_ns"
sudo -n ip link set v4as netns "$server_ns"
sudo -n ip -n "$client_ns" link set lo up
sudo -n ip -n "$server_ns" link set lo up
sudo -n ip -n "$client_ns" addr add 198.18.7.1/30 dev v4ac
sudo -n ip -n "$server_ns" addr add 198.18.7.2/30 dev v4as
sudo -n ip -n "$client_ns" link set v4ac up
sudo -n ip -n "$server_ns" link set v4as up
work="$RUNNER_TEMP/arm64-netns-secrets-$GITHUB_RUN_ID"
mkdir -p "$work"
chmod 0700 "$work"
umask 077
openssl rand -hex 32 >"$work/route-key"
openssl rand -hex 24 >"$work/password"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -subj '/CN=wbd.test' -addext 'subjectAltName=DNS:wbd.test' \
  -keyout "$work/server.key" -out "$work/server.crt" >"$out/certificate.log" 2>&1
chmod 0600 "$work/route-key" "$work/password" "$work/server.key"
# Shared credentials via private fd-checked files only, never argv secret.
set -- --username smoke --password-file "$work/password" \
  --route-key-hex-file "$work/route-key" --server-name wbd.test \
  --tunnel-id 00112233445566778899aabbccddeeff --mode normal
sudo -n ip netns exec "$server_ns" env LD_LIBRARY_PATH="$bundle" "$bundle/wbd-v4-server" "$@" \
  --raw-interface v4as --local-ip 198.18.7.2 --local-port 443 \
  --tun-name wbdsv --tun-ipv4 10.188.18.2/24 \
  --tls-cert "$work/server.crt" --tls-key "$work/server.key" \
  >"$out/server.log" 2>&1 &
server_launcher=$!
found=0
for i in $(seq 1 75); do
  if sudo -n ip -n "$server_ns" link show wbdsv >/dev/null 2>&1; then found=1; break; fi
  if ! kill -0 "$server_launcher" 2>/dev/null; then break; fi
  sleep .2
done
if [ "$found" -ne 1 ]; then
  echo 'ARM64_OS_SERVER_TUN_START_FAIL'
  tail -n 35 "$out/server.log" || true
  exit 1
fi
sudo -n ip netns exec "$client_ns" env LD_LIBRARY_PATH="$bundle" "$bundle/wbd-v4-client" "$@" \
  --raw-interface v4ac --local-ip 198.18.7.1 --peer-ip 198.18.7.2 \
  --local-port 50001 --peer-port 443 --tun-name wbdcl --tun-ipv4 10.188.18.1/24 \
  >"$out/client.log" 2>&1 &
client_launcher=$!
ready=0
for i in $(seq 1 200); do
  if grep -q V4_ORIGINAL_GO_CLIENT_NATIVE_READY "$out/client.log" \
    && grep -q V4_ORIGINAL_GO_SERVER_NATIVE_READY "$out/server.log"; then ready=1; break; fi
  if ! kill -0 "$client_launcher" 2>/dev/null || ! kill -0 "$server_launcher" 2>/dev/null; then break; fi
  sleep .2
done
if [ "$ready" -ne 1 ]; then
  echo 'ARM64_OS_REAL_GO_TLS_RUST_NOT_READY'
  tail -n 50 "$out/client.log" || true
  tail -n 50 "$out/server.log" || true
  exit 1
fi
sudo -n ip netns exec "$client_ns" ping -n -I wbdcl -c 3 -W 2 10.188.18.2 \
  >"$out/c2s.log" 2>&1
sudo -n ip netns exec "$server_ns" ping -n -I wbdsv -c 3 -W 2 10.188.18.1 \
  >"$out/s2c.log" 2>&1
grep -q '0% packet loss' "$out/c2s.log"
grep -q '0% packet loss' "$out/s2c.log"
stop_namespace "$client_ns"
stop_namespace "$server_ns"
for i in $(seq 1 75); do
  if grep -q V4_PUBLIC_NATIVE_STOP_DRAINED "$out/client.log" \
    && grep -q V4_PUBLIC_NATIVE_STOP_DRAINED "$out/server.log"; then break; fi
  sleep .2
done
grep -q V4_PUBLIC_NATIVE_STOP_DRAINED "$out/client.log"
grep -q V4_PUBLIC_NATIVE_STOP_DRAINED "$out/server.log"
cleanup
trap - EXIT
if sudo -n ip netns list | grep -Eq "($client_ns|$server_ns)"; then
  echo 'ARM64_NETNS_CLEANUP_FAILED'; exit 1
fi
OUTPUT="$out" python3 - <<'PY'
import pathlib,json,hashlib,os
p=pathlib.Path(os.environ["OUTPUT"])
sha=lambda n:hashlib.sha256((p/n).read_bytes()).hexdigest()
files=("client.log","server.log","c2s.log","s2c.log")
d={"source":os.environ["GITHUB_SHA"],"run":os.environ["GITHUB_RUN_ID"],
"qualification":"PASS_SCOPED_TWO_ARM64_NETNS_GENUINE_GO_TLS_RUST_RAW_TUN",
"bidirectional":"3_ICMP_PER_DIRECTION","owned_stop":"TWO_DRAINED","netns_cleanup":"PASS",
"impairment":"NOT_RUN","physical":"NOT_RUN","logs_sha256":{f:sha(f) for f in files}}
(p/"receipt.json").write_text(json.dumps(d,indent=2)+"\n")
print("ARM64_NATIVE_OS_TWO_WAY_APP_STOP_PASS")
PY
