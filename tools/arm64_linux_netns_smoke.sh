#!/usr/bin/env bash
# Two isolated real Linux ARM64 V4 CLI endpoints, not an emulated packet fixture.
# PLAN029 opt-in reuses the SAME ORIGINAL kernel/netns fixture on native x86_64
# and native aarch64; all legacy ARM64 frozen-source calls are unchanged.
set -euo pipefail
if [[ "${WBD_PLAN029_LINUX_DUAL_ISA:-0}" == 1 ]];then
  case "$(uname -m)" in x86_64|aarch64) ;; *) echo PLAN029_WRONG_NATIVE_ISA; exit 2;; esac
  test "$(uname -m)" = "${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}"
else
  test "$(uname -m)" = aarch64
fi
: "$GITHUB_RUN_ID" "$GITHUB_SHA" "$GITHUB_WORKSPACE"
bundle="${WBD_PLAN029_LINUX_BUNDLE:-$GITHUB_WORKSPACE/arm64-public-bundle}"
out="${WBD_PLAN029_LINUX_OUTPUT:-$GITHUB_WORKSPACE/arm64-netns-result}"
mkdir -p "$out"
(cd "$bundle" && sha256sum -c SHA256SUMS)
# GitHub artifact ZIP extraction does not preserve executable mode.
# chmod changes metadata only, leaving the source-checked binary SHA256 intact.
chmod 0755 "$bundle/wbd-v4-client" "$bundle/wbd-v4-server"
python3 - "$bundle/manifest.json" "${WBD_ARM64_FROZEN_SOURCE:-$GITHUB_SHA}" <<'PY'
import json,sys,os,platform
m=json.load(open(sys.argv[1]))
expected=(platform.machine() if os.environ.get("WBD_PLAN029_LINUX_DUAL_ISA")=="1"
          else "aarch64")
actual_source=(m.get("source_sha") if os.environ.get("WBD_PLAN029_LINUX_DUAL_ISA")=="1"
               else m.get("source"))
assert actual_source==sys.argv[2] and m["architecture"]==expected,m
assert expected in ("x86_64","aarch64") and platform.machine()==expected
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
# Explicit current-Game protected group, never conflate Game4/FEC with
# Normal's standalone FEC mode. Both original TLS peers receive SAME flag.
game_fec_args=()
if [ -n "${WBD_ARM64_GAME_FEC_PROFILE:-}" ]; then
  if [ "$WBD_ARM64_GAME_FEC_PROFILE" != 6 ] || {
    [ "$mode" != game4 ] && ! { [ "$mode" = game2 ] && [ "${WBD_PLAN029_LINUX_COVERAGE:-0}" = 1 ]; };
  }; then
    echo 'ARM64_GAME_FEC_TEST_ONLY_FIXED6_GAME4_OR_SCOPED_GAME2' >&2; exit 2
  fi
  game_fec_args=(--game-fec fixed6)
fi
# H2181: requested cross-platform Linux native capability supplement.
# Existing H2177/archived frozen ARM64 paths are unchanged unless explicit.
client_extra=();server_extra=()
if [[ "${WBD_PLAN029_LINUX_COVERAGE:-0}" == 1 ]];then
  case "${WBD_PLAN029_LINUX_STARTUP_PADDING:-off}" in
    off|tls|flows) ;;
    *) echo PLAN029_INVALID_LINUX_PAD_REQUEST >&2;exit 2 ;;
  esac
  if [[ "$game_lanes" -gt 0 || "$mode" == normal || "$mode" == fec-fixed || "$mode" == fec-auto ]];then
    client_extra+=(--startup-padding "${WBD_PLAN029_LINUX_STARTUP_PADDING:-off}")
    server_extra+=(--startup-padding "${WBD_PLAN029_LINUX_STARTUP_PADDING:-off}")
  elif [[ "${WBD_PLAN029_LINUX_STARTUP_PADDING:-off}" != off ]];then
    echo PLAN029_LINUX_FEC_PADDING_NOT_WIRED >&2;exit 2
  fi
  case "${WBD_PLAN029_LINUX_CLIENT_CIPHER:-chacha20-poly1305}" in
    chacha20-poly1305|aes-128-gcm|aes-256-gcm)
      client_extra+=(--record-cipher "${WBD_PLAN029_LINUX_CLIENT_CIPHER:-chacha20-poly1305}") ;;
    *) echo PLAN029_INVALID_CIPHER_CASE >&2;exit 2 ;;
  esac
  case "${WBD_PLAN029_LINUX_OUTER_REPAIR:-on}" in
    on|off)
      client_extra+=(--outer-repair "${WBD_PLAN029_LINUX_OUTER_REPAIR:-on}")
      server_extra+=(--outer-repair "${WBD_PLAN029_LINUX_OUTER_REPAIR:-on}") ;;
    *) echo PLAN029_INVALID_REPAIR_CASE >&2;exit 2 ;;
  esac
  if [[ -n "${WBD_PLAN029_LINUX_GAME4_COPY:-}" ]];then
    [[ "$mode" == game4 ]] || { echo PLAN029_GAME4_COPY_REQUIRES_GAME4 >&2;exit 2; }
    client_extra+=(--game4-copy-schedule "$WBD_PLAN029_LINUX_GAME4_COPY")
    server_extra+=(--game4-copy-schedule "$WBD_PLAN029_LINUX_GAME4_COPY")
  fi
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
# A pre-ClientHello ephemeral X25519 route exchange needs NO operator
# shared route-key; the real TLS certificate must still verify on client.
# Keep old explicit route file for the historical frozen rollback scenes.
route_args=(--route-key-hex-file "$work/route-key")
if [[ "${WBD_ARM64_USE_AUTO_ROUTE:-0}" == 1 ]];then route_args=();fi
set -- --username smoke --password-file "$work/password" "${route_args[@]}" \
  --server-name wbd.test \
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
sudo -n ip netns exec "$server_ns" env LD_LIBRARY_PATH="$bundle" "$bundle/wbd-v4-server" "$@" "${game_fec_args[@]}" "${server_extra[@]}" \
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
# A newly opened TUN precedes original Go's raw AF_PACKET receive socket.
# The first source-locked SYN MUST start only after the REAL server raw
# endpoint has bound its exact port; do not silently paper over cold loss.
raw_listen=0
# Normal emits an explicit raw-listener log; manual Game2/4's
# original runGameServer opens ONE shared AF_PACKET ReceivePort=443 socket
# for ALL game lanes before the first SYN (game_linux.go), not one per lane.
# Check the genuine socket in this dedicated server netns before SYN:
# zero is a hard failure, but requiring n=2/4 falsely deadlocks cold join.
# This is only startup readiness; after TLS each n-lane protected group
# must still qualify real per-lane kernel copies, FEC and exact Stop.
raw_deadline_loops=100
if [ "$game_lanes" -gt 0 ];then raw_deadline_loops=300;fi
for i in $(seq 1 "$raw_deadline_loops"); do
  if [ "$game_lanes" -eq 0 ];then
    if grep -Eq 'V4_PUBLIC_RAW_AF_PACKET_READY role=server attempt=[0-9]+ interface=v4as port=443' "$out/server.log"; then
      raw_listen=1;break
    fi
  else
    packet_sockets=$(sudo -n ip netns exec "$server_ns" sh -c "tail -n +2 /proc/net/packet | wc -l" 2>/dev/null | tr -d '[:space:]' || true)
    # The original Game manual server has ONE receive-port-443 socket;
    # additional lane sockets belong to clients or post-auth Rust M4 only.
    if [[ "$packet_sockets" =~ ^[0-9]+$ ]] && [ "$packet_sockets" -ge 1 ];then
      echo "ARM64_GAME_SERVER_TRUE_AF_PACKET_SOCKET_PRE_SYN_READY sockets=$packet_sockets required=1 shared_port=443 lanes=$game_lanes"
      raw_listen=1;break
    fi
  fi
  if ! kill -0 "$server_launcher" 2>/dev/null; then break; fi
  sleep .1
done
if [ "$raw_listen" -ne 1 ];then
  echo "ARM64_OS_SERVER_RAW_LISTENER_NOT_READY_BEFORE_CLIENT_SYN mode=$mode loops=$raw_deadline_loops"
  echo "ARM64_GAME_ORIGINAL_SHARED_AF_PACKET_OBSERVED sockets=${packet_sockets:-NONE} required=1 lanes=$game_lanes"
  ps -eo pid,stat,wchan:28,comm | grep -E 'wbd-v4|sudo|ip netns' | tail -n 16 || true
  sudo -n ip netns pids "$server_ns" || true
  tail -n 40 "$out/server.log" || true
  exit 1
fi
if [ "$game_lanes" -eq 0 ];then
  echo ARM64_REAL_GO_AF_PACKET_SERVER_LISTENING_BEFORE_SYN_PASS
else
  echo ARM64_GAME_SERVER_KERNEL_AF_PACKET_LANES_BEFORE_SYN_PASS
fi
sudo -n ip netns exec "$client_ns" env LD_LIBRARY_PATH="$bundle" SSL_CERT_FILE="$work/server.crt" "$bundle/wbd-v4-client" "$@" "${game_fec_args[@]}" "${client_extra[@]}" \
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
# The exact original pinned X25519 route classifier is only a pre-TLS gate;
# certificate validation and protected password still authorize this owner.
if [[ "${WBD_ARM64_USE_AUTO_ROUTE:-0}" == 1 ]];then
  grep -q 'V4_PUBLIC_ROUTE_PREHELLO role=client mode=ephemeral_x25519' "$out/client.log"
  grep -q 'V4_PUBLIC_ROUTE_PREHELLO role=server mode=ephemeral_x25519' "$out/server.log"
  echo ARM64_NATIVE_NO_MANUAL_ROUTE_X25519_TLS_CERT_VERIFIED_PASS
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
# Actual routed physical MTU change AFTER authenticated original TLS and
# normal business; do not touch Wintun/TUN to fake correct budget derivation.
# A product that cannot rebind or fail-close in a bounded manner must FAIL.
if [ "${WBD_ARM64_LIVE_MTU_CYCLE:-0}" = 1 ]; then
  [ "$mode" = normal ] || { echo ARM64_LIVE_MTU_NORMAL_ONLY >&2; exit 2; }
  echo 'ARM64_LIVE_PHYSICAL_MTU_CHANGE_BEGIN old=1500 new=1280' | tee -a "$out/dynamic-mtu.txt"
  sudo -n ip -n "$client_ns" link set v4ac mtu 1280
  sudo -n ip -n "$server_ns" link set v4as mtu 1280
  for ns in "$client_ns" "$server_ns";do
    port=v4ac; [ "$ns" = "$server_ns" ] && port=v4as
    got=$(sudo -n ip -j -n "$ns" link show "$port" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["mtu"])')
    test "$got" = 1280 || { echo 'ARM64_LIVE_PHYSICAL_MTU_OS_READBACK_FAIL'; exit 1; }
  done
  sleep 3
  sudo -n ip netns exec "$client_ns" ping -n -I wbdcl -s 64 -c 3 -W 2 10.188.18.2 > "$out/dynamic-small-c2s.log" 2>&1 || { echo ARM64_LIVE_MTU_SMALL_C2S_FAIL;exit 1; }
  sudo -n ip netns exec "$server_ns" ping -n -I wbdsv -s 64 -c 3 -W 2 10.188.18.1 > "$out/dynamic-small-s2c.log" 2>&1 || { echo ARM64_LIVE_MTU_SMALL_S2C_FAIL;exit 1; }
  grep -q '0% packet loss' "$out/dynamic-small-c2s.log"
  grep -q '0% packet loss' "$out/dynamic-small-s2c.log"
  for direction in c2s s2c;do
    ns="$client_ns";device=wbdcl
    if [ "$direction" = s2c ];then ns="$server_ns";device=wbdsv;fi
    actual=$(sudo -n ip -j -n "$ns" link show "$device" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["mtu"])')
    echo "ARM64_LIVE_MTU_PHASE mid direction=$direction inner_os=$actual physical_os=1280" | tee -a "$out/dynamic-mtu.txt"
    if [ "$actual" -gt 1209 ];then
      echo "ARM64_LIVE_MTU_NARROW_NOT_APPLIED direction=$direction actual=$actual maximum=1209" | tee -a "$out/dynamic-mtu.txt"
      exit 1
    fi
  done
  sudo -n ip -n "$client_ns" link set v4ac mtu 1500
  sudo -n ip -n "$server_ns" link set v4as mtu 1500
  sudo -n ip netns exec "$client_ns" ping -n -I wbdcl -s 64 -c 3 -W 2 10.188.18.2 > "$out/dynamic-restored.log" 2>&1
  grep -q '0% packet loss' "$out/dynamic-restored.log"
  echo ARM64_LIVE_MTU_1460_1280_RECOVER_REAL_OS_PASS | tee -a "$out/dynamic-mtu.txt"
fi
# PLAN029 Linux-only coverage: verify the ORIGINAL owned TUN never
# exposes an IPv6 address/route. Linux kernels may omit /proc/sys/net/ipv6/
# conf/<device> entirely if the kernel TUN MTU is below IPv6's 1280 minimum
# (e.g. outer1280 -> inner1209). Absence is valid ONLY below that minimum;
# at >=1280 the owned per-interface disable_ipv6 readback MUST equal 1.
# Do not modify/read back host-global IPv6 as a surrogate.
if [[ "${WBD_PLAN029_LINUX_DUAL_ISA:-0}" == 1 ]];then
  for role in client server;do
    ns="$client_ns"; device=wbdcl
    if [[ "$role" == server ]];then ns="$server_ns"; device=wbdsv; fi
    native_tun_mtu=$(sudo -n ip -j -n "$ns" link show "$device" |
      python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')
    ipv6_conf="/proc/sys/net/ipv6/conf/$device/disable_ipv6"
    if sudo -n ip netns exec "$ns" test -f "$ipv6_conf";then
      applied=$(sudo -n ip netns exec "$ns" cat "$ipv6_conf")
      if [[ "$applied" != 1 ]];then
        echo "PLAN029_LINUX_OWNED_IPV6_NOT_DISABLED role=$role mtu=$native_tun_mtu got=$applied" >&2
        exit 1
      fi
      ipv6_mode=owned_disable_ipv6_1
    else
      if [[ "$native_tun_mtu" -ge 1280 ]];then
        echo "PLAN029_LINUX_OWNED_IPV6_SYSCTL_MISSING_ABOVE_MIN_MTU role=$role mtu=$native_tun_mtu" >&2
        exit 1
      fi
      ipv6_mode=kernel_below_ipv6_min_mtu_no_interface_sysctl
    fi
    owned_ipv6_addr=$(sudo -n ip -n "$ns" -6 -o addr show dev "$device")
    owned_ipv6_route=$(sudo -n ip -n "$ns" -6 route show dev "$device")
    if [[ -n "$owned_ipv6_addr" || -n "$owned_ipv6_route" ]];then
      echo "PLAN029_LINUX_OWNED_TUN_LEAKED_IPV6_ADDRESS_OR_ROUTE role=$role mtu=$native_tun_mtu" >&2
      exit 1
    fi
    echo "PLAN029_LINUX_OWNED_IPV6_BOUNDARY_PASS role=$role inner_mtu=$native_tun_mtu method=$ipv6_mode ipv6_addresses=0 ipv6_routes=0" |
      tee -a "$out/owned-ipv6.txt"
  done
  for direction in c2s s2c;do
    source_ns="$client_ns"; dest_ns="$server_ns"
    source_ip=10.188.18.1;dest_ip=10.188.18.2;app_port=47123
    if [[ "$direction" == s2c ]];then
      source_ns="$server_ns";dest_ns="$client_ns"
      source_ip=10.188.18.2;dest_ip=10.188.18.1;app_port=47124
    fi
    app="$GITHUB_WORKSPACE/tools/m0_plan029_linux_native_app.py"
    sudo -n ip netns exec "$dest_ns" env WBD_PLAN029_LINUX_TCP_TLS_SHAPE="${WBD_PLAN029_LINUX_TCP_TLS_SHAPE:-0}" python3 -u "$app" listener "$dest_ip" "$source_ip" "$app_port" "$direction" >"$out/app-$direction-listener.log" 2>&1 &
    listener_pid=$!
    app_ready=0
    for i in $(seq 1 70);do
      if grep -q "PLAN029_LINUX_APP_SOCKET_READY $direction" "$out/app-$direction-listener.log";then
        app_ready=1;break
      fi
      # Do not infer readiness from the short-lived sudo/ip-netns launcher
      # PID. On native ARM it may exit before the Python listener prints
      # READY while the real socket is already bound. Poll the marker.
      sleep .1
    done
    if [[ "$app_ready" != 1 ]];then
      echo "PLAN029_LINUX_APP_LISTENER_NOT_READY direction=$direction" >&2
      tail -n 25 "$out/app-$direction-listener.log" >&2;exit 1
    fi
    if ! timeout 40s sudo -n ip netns exec "$source_ns" env WBD_PLAN029_LINUX_TCP_TLS_SHAPE="${WBD_PLAN029_LINUX_TCP_TLS_SHAPE:-0}" python3 -u "$app" sender "$source_ip" "$dest_ip" "$app_port" "$direction" >"$out/app-$direction-sender.log" 2>&1;then
      echo "PLAN029_LINUX_APP_REAL_KERNEL_SEND_FAIL direction=$direction" >&2
      tail -n 25 "$out/app-$direction-sender.log" >&2; exit 1
    fi
    if ! wait "$listener_pid";then
      echo "PLAN029_LINUX_APP_REAL_KERNEL_RECEIVE_FAIL direction=$direction" >&2
      tail -n 25 "$out/app-$direction-listener.log" >&2;exit 1
    fi
    for role in sender listener;do
      grep -q "PLAN029_LINUX_APP_TRUE_KERNEL_PASS" "$out/app-$direction-$role.log"
    done
    echo "PLAN029_LINUX_REAL_KERNEL_TCP_UDP_BIDIRECTIONAL_PASS direction=$direction"
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
if [[ "${WBD_PLAN029_LINUX_COVERAGE:-0}" == 1 && "$game_lanes" -gt 0 ]];then
  for side in client server;do
    grep -Fq "V4_PUBLIC_GAME_PADDING_RAW_RECEIPT role=$side lanes=$game_lanes mode=${WBD_PLAN029_LINUX_STARTUP_PADDING:-off}" "$out/$side.log" || {
      echo "PLAN029_GAME_NATIVE_PADDING_READBACK_MISSING side=$side" >&2
      tail -n 35 "$out/$side.log" >&2;exit 1
    }
  done
  OUTPUT="$out" python3 - <<'PY'
import os,pathlib,re
out=pathlib.Path(os.environ["OUTPUT"]); mode=os.environ.get("WBD_PLAN029_LINUX_STARTUP_PADDING","off")
for role in ("client","server"):
    log=(out/(role+".log")).read_text(errors="replace")
    hits=re.findall(r"V4_PUBLIC_GAME_PADDING_RAW_RECEIPT role="+role+
        r" lanes=(2|4) mode=(off|tls|flows) padded_records=(\d+) padded_bytes=(\d+) original_TLS_Rust_M4=1 real_AF_PACKET_send=1",log)
    assert len(hits)==1,(role,hits)
    lanes,actual,records,bytes_=hits[0]
    records=int(records);bytes_=int(bytes_)
    assert mode==actual
    assert (mode!="off" or records==bytes_==0)
    assert bytes_<=500*records
    if mode=="flows":
        assert records>0 and bytes_>0,(role,records,bytes_)
    if mode=="tls":
        assert records>0 and bytes_>0,(role,records,bytes_)
print("PLAN029_LINUX_ORIGINAL_GAME_PADDING_ACTUAL_RAW_COPY_PASS mode="+mode,flush=True)
PY
fi
if [ "$game_lanes" -gt 0 ]; then
  # Game2/4 use authenticated GameAdapter grouped lanes, NOT Normal FEC2
  # operator policies. Demand real kernel input/output and no auth rejection.
  for side in client server; do
    grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=$side lanes=$game_lanes original_tls=1 rust_m4=1" "$out/$side.log"
    if [[ "${WBD_PLAN029_LINUX_DUAL_ISA:-0}" == 1 ]];then
      # The original GameTx counter 'rejected' is *lane_copy_drop*;
      # expired/unscheduled redundant copies can be discarded while the
      # first authenticated logical packet is delivered. Do not mislabel
      # it as an AEAD rejection or a missing TCP/UDP application packet.
      # Enforce positive original kernel copies, real first deliveries,
      # zero authenticated rejection, and all independently classified
      # product TX/RAW/MTU/queue pressure faults exactly zero below.
      # The legacy frozen ARM64 harness still requires rejected=0.
      :
    else
      grep -Eq "V4_PUBLIC_GAME_KERNEL role=$side lanes=$game_lanes copied=[1-9][0-9]* delivered=[1-9][0-9]* rejected=0 raw_received=[1-9][0-9]* auth_rejected=0" "$out/$side.log"
    fi
  done
  if [[ "${WBD_PLAN029_LINUX_DUAL_ISA:-0}" == 1 ]];then
    OUTPUT="$out" GAME_LANES="$game_lanes" python3 - <<'PY'
import json,os,pathlib,re
p=pathlib.Path(os.environ["OUTPUT"])
lanes=int(os.environ["GAME_LANES"])
status={"verified_original_game_lanes":lanes,"scope":"ORIGINAL_AUTHENTICATED_GAME_M4_KERNEL_COPIES"}
for role in ("client","server"):
    raw=(p/(role+".log")).read_text(errors="replace")
    rows=re.findall(r"V4_PUBLIC_GAME_KERNEL role="+role+
        rf" lanes={lanes} copied=(\d+) delivered=(\d+) rejected=(\d+)"
        r" raw_received=(\d+) auth_rejected=(\d+)",raw)
    assert len(rows)==1,(role,"original kernel readback not unique",rows)
    copied,delivered,copy_skips,raw_rx,auth_denied=map(int,rows[0])
    assert copied>0 and delivered>0 and raw_rx>0 and auth_denied==0,rows
    details=re.findall(
        r"M0_GAME_M4_TX_REJECT_BREAKDOWN offer=(\d+) slab=(\d+)"
        r" record=(\d+) policy=(\d+) raw=(\d+) raw_backpressure=(\d+)"
        r" raw_route=(\d+) raw_mtu=(\d+) total_rejected=(\d+)",raw)
    assert len(details)==1,(role,"original reject causes not unique",details)
    classification=list(map(int,details[0]))
    # Genuine Go/Rust M4 transport, slab/record/policy, path/MTU errors
    # must stay zero. Noncritical lane-copy skips remain *observed*, never
    # erased or called zero; original 2/4-lane business must still pass.
    assert all(v==0 for v in classification[:8]),(role,classification)
    assert classification[8]==copy_skips,(role,classification,copy_skips)
    assert (f"V4_ORIGINAL_GO_GAME_NATIVE_READY role={role} lanes={lanes}"
            in raw),("original protected Go TLS/Rust group missing",role)
    assert (f"V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role={role} lanes={lanes}"
            in raw),("original Rust M4 Stop incomplete",role)
    status[role]={"kernel_copied":copied,"first_delivered":delivered,
                  "lane_copy_skips_observed":copy_skips,
                  "raw_received":raw_rx,"auth_rejected":auth_denied,
                  "classified_transport_faults":classification[:8]}
(p/"game-kernel-copy-readback.json").write_text(
    json.dumps(status,sort_keys=True,indent=2)+"\n")
print("PLAN029_LINUX_NATIVE_GAME_KERNEL_RECEIPT_CHECKED "
      +json.dumps(status,sort_keys=True),flush=True)
PY
  fi
fi
if [ -n "${WBD_ARM64_GAME_FEC_PROFILE:-}" ]; then
  # Genuine Game FEC source/parity must have passed the actual kernel copy
  # before we can call this a protected-source native mode.
  for side in client server;do
    grep -Eq "V4_PUBLIC_GAME_FEC_COUNTERS role=$side lanes=$game_lanes source_offered=[1-9][0-9]* parity_offered=[1-9][0-9]* parity_copied=[1-9][0-9]*" "$out/$side.log" || {
      echo "ARM64_GAME4_FEC6_REAL_PARITY_MISSING role=$side" >&2;tail -n 18 "$out/$side.log" >&2;exit 1;
    }
  done
  echo ARM64_GAME4_FEC6_NATIVE_PARITY_KERNEL_COPIED_BOTH_PASS
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
import pathlib,json,hashlib,os,platform
p=pathlib.Path(os.environ["OUTPUT"])
sha=lambda n:hashlib.sha256((p/n).read_bytes()).hexdigest()
files=("client.log","server.log","c2s.log","s2c.log")
d={"source":os.environ.get("WBD_ARM64_FROZEN_SOURCE",os.environ["GITHUB_SHA"]),
"test_harness_source":os.environ["GITHUB_SHA"],"run":os.environ["GITHUB_RUN_ID"],
"qualification":("PASS_SCOPED_TWO_LINUX_SAME_ISA_NETNS_ORIGINAL_GO_TLS_RUST_RAW_TUN"
 if os.environ.get("WBD_PLAN029_LINUX_DUAL_ISA")=="1"
 else "PASS_SCOPED_TWO_ARM64_NETNS_GENUINE_GO_TLS_RUST_RAW_TUN"),
"actual_native_isa":platform.machine(),
"mode":os.environ.get("WBD_V4_MODE","normal"),
"game_fec_profile":os.environ.get("WBD_ARM64_GAME_FEC_PROFILE","off"),
"dynamic_mtu_cycle":os.environ.get("WBD_ARM64_LIVE_MTU_CYCLE","NOT_RUN"),
"native_fec_parity_execution":"NOT_PROVEN_BY_ICMP_CASE",
"game_lanes":int(os.environ.get("WBD_V4_GAME_LANES","0")),
"bidirectional":os.environ.get("WBD_V4_EXPECTED_ICMP","UNKNOWN")+"_ICMP_PER_DIRECTION","owned_stop":"TWO_DRAINED","netns_cleanup":"PASS",
"impairment":"NOT_RUN","physical":"NOT_RUN",
"capacity_trial":os.environ.get("WBD_ARM64_CAPACITY_TRIAL","NOT_RUN"),
"logs_sha256":{f:sha(f) for f in files}}
(p/"receipt.json").write_text(json.dumps(d,indent=2)+"\n")
if os.environ.get("WBD_PLAN029_LINUX_DUAL_ISA")=="1":
    for direction in ("c2s","s2c"):
        for role in ("sender","listener"):
            proof=json.loads(next(x.split(" ",1)[1] for x in
                (p/("app-"+direction+"-"+role+".log")).read_text().splitlines()
                if x.startswith("PLAN029_LINUX_APP_TRUE_KERNEL_PASS ")))
            assert proof["udp"]=="PASS_NATIVE_KERNEL_APP" and proof["tcp"]=="PASS_NATIVE_KERNEL_APP"
    d["real_linux_kernel_udp_tcp_both_directions"]="PASS"
    d["linux_owned_tun_ipv6_disable"]="PASS_BOTH_OWNED_TUN_ONLY"
    d["requested_outer_mtu"]=int(os.environ["WBD_ARM64_OUTER_MTU"])
    d["actual_client_server_isa"]=platform.machine()
    d["source_binary_sha256_verified"]=True
    (p/"receipt.json").write_text(json.dumps(d,indent=2)+"\n")
    print("PLAN029_LINUX_NATIVE_TWO_END_REAL_UDP_TCP_IPV6_MTU_STOP_PASS arch="+platform.machine())
else:
    print("ARM64_NATIVE_OS_TWO_WAY_APP_STOP_PASS")
PY
