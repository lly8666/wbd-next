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
python3 - "$bundle/manifest.json" "${WBD_ARM64_FROZEN_SOURCE:-$GITHUB_SHA}" <<'PY'
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
# The exact tuple guard for Linux FakeTCP extends only to the authenticated
# grouped Game lanes when this independent Game trial is selected.
mode="${WBD_V4_MODE:-normal}"
case "$mode" in
  normal|fec-fixed|fec-auto) game_lanes=0; last_cport=50001; last_sport=443 ;;
  game2) game_lanes=2; last_cport=50002; last_sport=444 ;;
  game4) game_lanes=4; last_cport=50004; last_sport=446 ;;
  *) echo "ARM64_MODE_UNSUPPORTED $mode" >&2; exit 2 ;;
esac
client_ready_marker=V4_ORIGINAL_GO_CLIENT_NATIVE_READY
server_ready_marker=V4_ORIGINAL_GO_SERVER_NATIVE_READY
stop_marker=V4_PUBLIC_NATIVE_STOP_DRAINED
if [ "$game_lanes" -gt 0 ]; then
  client_ready_marker=V4_ORIGINAL_GO_GAME_NATIVE_READY
  server_ready_marker=V4_ORIGINAL_GO_GAME_NATIVE_READY
  stop_marker=V4_PUBLIC_GAME_NATIVE_STOP_DRAINED
fi
export WBD_V4_GAME_LANES="$game_lanes"
# Raw FakeTCP SYN/SYNACK uses no kernel TCP socket. The kernel otherwise emits
# a real TCP RST to that unmatched tuple, and the original Go client closes.
# Rules are tuple-exact, in two *ephemeral namespaces*, never on the host.
# This is transport preflight, not a replacement for any Go/Rust business code.
sudo -n ip netns exec "$client_ns" iptables -w -A OUTPUT -o v4ac -p tcp   -s 198.18.7.1 -d 198.18.7.2 --sport "50001:$last_cport" --dport "443:$last_sport"   --tcp-flags RST RST -j DROP
sudo -n ip netns exec "$server_ns" iptables -w -A OUTPUT -o v4as -p tcp   -s 198.18.7.2 -d 198.18.7.1 --sport "443:$last_sport" --dport "50001:$last_cport"   --tcp-flags RST RST -j DROP
echo "ORIGINAL_LINUX_FAKE_TCP_KERNEL_RST_GUARD_SCOPED"
sudo -n ip netns exec "$client_ns" iptables -w -nvxL OUTPUT >"$out/client-rst-preflight.txt"
sudo -n ip netns exec "$server_ns" iptables -w -nvxL OUTPUT >"$out/server-rst-preflight.txt"
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
# Fixed and Normal are separate exact-source functional cases.
# Shared credentials via private fd-checked files only, never argv secret.
set -- --username smoke --password-file "$work/password" \
  --route-key-hex-file "$work/route-key" --server-name wbd.test \
  --tunnel-id 00112233445566778899aabbccddeeff --mode "$mode" --fec-profile 1
client_mtu_args=(); server_mtu_args=()
# Older frozen bundles do not expose this flag. Default smoke keeps their
# original argv; explicit MTU tests require the new real CLI capability.
if [ -n "${WBD_ARM64_OUTER_MTU+x}" ]; then
  client_mtu_args=(--outer-mtu "$WBD_ARM64_OUTER_MTU")
  server_mtu_args=(--outer-mtu "$WBD_ARM64_OUTER_MTU")
fi
if [ -n "${WBD_ARM64_SERVER_OUTER_MTU+x}" ]; then
  server_mtu_args=(--outer-mtu "$WBD_ARM64_SERVER_OUTER_MTU")
fi
sudo -n ip netns exec "$server_ns" env LD_LIBRARY_PATH="$bundle" "$bundle/wbd-v4-server" "$@" \
  --raw-interface v4as --local-ip 198.18.7.2 --local-port 443 \
  "${server_mtu_args[@]}" \
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
  "${client_mtu_args[@]}" \
  --local-port 50001 --peer-port 443 --tun-name wbdcl --tun-ipv4 10.188.18.1/24 \
  >"$out/client.log" 2>&1 &
client_launcher=$!
ready=0
for i in $(seq 1 200); do
  if grep -q "$client_ready_marker" "$out/client.log" \
    && grep -q "$server_ready_marker" "$out/server.log"; then ready=1; break; fi
  # A just-forked sudo/ip-netns process can hand off to its child before
  # the Go process prints anything. Avoid an empty-log false failure in <1s.
  if [ "$i" -ge 10 ] && { ! kill -0 "$client_launcher" 2>/dev/null || ! kill -0 "$server_launcher" 2>/dev/null; }; then
    echo "ARM64_LAUNCHER_EXITED_DURING_HANDSHAKE iteration=$i" >&2
    sleep .3
    break
  fi
  sleep .2
done
if [ "$ready" -ne 1 ]; then
  echo 'ARM64_OS_REAL_GO_TLS_RUST_NOT_READY'
  {
    echo "snapshot_iteration=$i client_launcher=$client_launcher server_launcher=$server_launcher"
    ps -p "$client_launcher,$server_launcher" -o pid,stat,comm || true
    echo "client namespace PIDs"; sudo -n ip netns pids "$client_ns" || true
    echo "server namespace PIDs"; sudo -n ip netns pids "$server_ns" || true
    echo "client interfaces"; sudo -n ip -s -n "$client_ns" link show || true
    echo "server interfaces"; sudo -n ip -s -n "$server_ns" link show || true
    echo "log sizes"; wc -c "$out/client.log" "$out/server.log"
    echo "client RST counters"; sudo -n ip netns exec "$client_ns" iptables -w -nvxL OUTPUT || true
    echo "server RST counters"; sudo -n ip netns exec "$server_ns" iptables -w -nvxL OUTPUT || true
  } >"$out/diagnostic.txt" 2>&1
  cat "$out/diagnostic.txt"
  tail -n 50 "$out/client.log" || true
  tail -n 50 "$out/server.log" || true
  exit 1
fi
# 3 request/reply observations certify Normal. Fixed needs enough authentic
# sources to form at least one <=16-source block and mature M2 feedback.
# One low-rate diagnostic (20 each way), NOT load/performance pressure.
count=3
interval=1
if [ "$mode" != normal ]; then count=20; interval=0.1; fi
sudo -n ip netns exec "$client_ns" ping -n -I wbdcl -i "$interval" -c "$count" -W 2 10.188.18.2 \
  >"$out/c2s.log" 2>&1
sudo -n ip netns exec "$server_ns" ping -n -I wbdsv -i "$interval" -c "$count" -W 2 10.188.18.1 \
  >"$out/s2c.log" 2>&1
grep -q '0% packet loss' "$out/c2s.log"
grep -q '0% packet loss' "$out/s2c.log"
if [ "${WBD_ARM64_MTU_BOUNDARY:-0}" = 1 ]; then
  # Read the actual post-auth TUN MTU, not an assumed 1200B fixture constant.
  for direction in c2s s2c; do
    ns="$client_ns"; device=wbdcl; target=10.188.18.2; role=client
    if [ "$direction" = s2c ]; then ns="$server_ns"; device=wbdsv; target=10.188.18.1; role=server; fi
    mtu=$(sudo -n ip -j -n "$ns" link show "$device" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["mtu"])')
    grep -Eq "V4_PUBLIC_MTU .*tun_mtu=$mtu " "$out/$role.log"
    # Keep the regression crossing the old 1135B ceiling and test the NEW boundary.
    for payload in 1107 1108 "$((mtu-29))" "$((mtu-28))"; do
      if [ "$((payload+28))" -gt "$mtu" ]; then continue; fi
      log="$out/mtu-${direction}-${payload}.log"
      sudo -n ip netns exec "$ns" ping -n -M do -I "$device" -s "$payload" -i .1 -c 3 -W 3 "$target" >"$log" 2>&1
      grep -Eq ', 0% packet loss' "$log"
    done
    # DF > actual interface MTU is a local error, never silent loss of a valid packet.
    if sudo -n ip netns exec "$ns" ping -n -M do -I "$device" -s "$((mtu-27))" -c 1 -W 1 "$target" >"$out/mtu-df-oversize-$direction.log" 2>&1; then
      echo 'unexpected DF packet beyond TUN MTU'; exit 1
    fi
    grep -Eqi "message too long|mtu=$mtu" "$out/mtu-df-oversize-$direction.log"
    echo "ARM64_REAL_MTU_BOUNDARY_PASS mode=$mode direction=$direction inner_ipv4=$mtu df_plus_one=REJECTED" >>"$out/mtu-boundary.txt"
  done
fi
export WBD_V4_EXPECTED_ICMP="$count"
# One bounded, real-product capacity discovery; not codec A/B, first-arrival
# p99, or a production rate guarantee. Do NOT repeat if capacity is insufficient.
if [ "$(printenv WBD_ARM64_CAPACITY_TRIAL || true)" = "udp10m" ]; then
  if [ "$mode" != normal ]; then echo 'ARM64_CAPACITY_NORMAL_ONLY' >&2; exit 2; fi
  command -v iperf3 >/dev/null || { echo 'ARM64_CAPACITY_NO_IPERF3' >&2; exit 77; }
  sudo -n ip netns exec "$server_ns" iperf3 -s -1 -B 10.188.18.2 -p 5201      >"$out/iperf-server.log" 2>&1 &
  sleep 1
  set +e
  sudo -n ip netns exec "$client_ns" timeout 95s iperf3     -c 10.188.18.2 -B 10.188.18.1 -p 5201     --bidir -u -b 10M -l 1000 -t 60 -J     >"$out/iperf-client.json" 2>"$out/iperf-client.stderr"
  trial_rc=$?
  set -e
  if [ "$trial_rc" -ne 0 ]; then
    echo "ARM64_CAPACITY_TRIAL_FAILED exit=$trial_rc" >&2
    tail -n 20 "$out/iperf-client.stderr" >&2 || true
    exit 1
  fi
  OUTPUT="$out" python3 - <<'PY'
import pathlib,json,os
p=pathlib.Path(os.environ["OUTPUT"])
d=json.loads((p/"iperf-client.json").read_text())
if "error" in d: raise SystemExit("IPERF_ERROR "+str(d["error"]))
e=d.get("end",{})
assert isinstance(e,dict) and e.get("streams"),"iperf3 stream receipt missing"
receipt={"source":os.environ.get("WBD_ARM64_FROZEN_SOURCE",os.environ["GITHUB_SHA"]),
"harness_source":os.environ["GITHUB_SHA"],"target_bps_each_direction":10000000,
"duration_requested_sec":60,"iperf3_end":e,
"qualifier":"CAPACITY_TRIAL_ONLY","first_arrival_p99":"NOT_RUN",
"native_scalar_AB":"NOT_RUN","physical":"NOT_RUN"}
(p/"capacity.json").write_text(json.dumps(receipt,indent=2)+"\n")
print("ARM64_NORMAL_UDP_BIDIRECTIONAL_CAPACITY_TRIAL_RECORDED")
PY
fi
# Fixed's Go monitor cadence=200ms but authenticated maturity=2s.
# Give exactly one quiet maturity opportunity after the real 20+20 sources.
if [ "$mode" = fec-fixed ] || [ "$mode" = fec-auto ]; then sleep 3; fi
stop_namespace "$client_ns"
stop_namespace "$server_ns"
for i in $(seq 1 75); do
  if grep -q "$stop_marker" "$out/client.log" \
    && grep -q "$stop_marker" "$out/server.log"; then break; fi
  sleep .2
done
grep -q "$stop_marker" "$out/client.log"
grep -q "$stop_marker" "$out/server.log"
if [ "$game_lanes" -gt 0 ]; then
  # Game2/4 use authenticated GameAdapter grouped lanes, NOT Normal FEC2
  # operator policies. Demand real kernel input/output and no auth rejection.
  for side in client server; do
    grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=$side lanes=$game_lanes original_tls=1 rust_m4=1" "$out/$side.log"
    grep -Eq "V4_PUBLIC_GAME_KERNEL role=$side lanes=$game_lanes copied=[1-9][0-9]* delivered=[1-9][0-9]* rejected=0 raw_received=[1-9][0-9]* auth_rejected=0" "$out/$side.log"
  done
fi
if [ "$mode" = fec-fixed ] || [ "$mode" = fec-auto ]; then
  # Policy requested isn't necessarily applied. No hardware/backend PASS
  # unless both sides report applied>0 and pending=false.
  grep -q 'V4_PUBLIC_FEC2_READBACK role=client' "$out/client.log"
  grep -q 'V4_PUBLIC_FEC2_READBACK role=server' "$out/server.log"
  expected="$mode"
  expected="${expected#fec-}"
  if ! grep -Eq "V4_PUBLIC_FEC2_READBACK role=client mode=$expected requested=[0-9]+ applied=[1-9][0-9]* .*pending=false" "$out/client.log" \
    || ! grep -Eq "V4_PUBLIC_FEC2_READBACK role=server mode=$expected requested=[0-9]+ applied=[1-9][0-9]* .*pending=false" "$out/server.log"; then
    echo "ARM64_FEC2_${expected}_REAL_PRODUCT_NOT_APPLIED (original requested vs applied)"
    tail -n 15 "$out/client.log" || true
    tail -n 15 "$out/server.log" || true
    exit 1
  fi
fi
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
d={"source":os.environ.get("WBD_ARM64_FROZEN_SOURCE",os.environ["GITHUB_SHA"]),
"test_harness_source":os.environ["GITHUB_SHA"],"run":os.environ["GITHUB_RUN_ID"],
"qualification":"PASS_SCOPED_TWO_ARM64_NETNS_GENUINE_GO_TLS_RUST_RAW_TUN",
"mode":os.environ.get("WBD_V4_MODE","normal"),
"native_fec_parity_execution":"NOT_PROVEN_BY_ICMP_CASE",
"game_lanes":int(os.environ.get("WBD_V4_GAME_LANES","0")),
"bidirectional":os.environ.get("WBD_V4_EXPECTED_ICMP","UNKNOWN")+"_ICMP_PER_DIRECTION","owned_stop":"TWO_DRAINED","netns_cleanup":"PASS",
"impairment":"NOT_RUN","physical":"NOT_RUN",
"capacity_trial":os.environ.get("WBD_ARM64_CAPACITY_TRIAL","NOT_RUN"),
"logs_sha256":{f:sha(f) for f in files}}
(p/"receipt.json").write_text(json.dumps(d,indent=2)+"\n")
print("ARM64_NATIVE_OS_TWO_WAY_APP_STOP_PASS")
PY
