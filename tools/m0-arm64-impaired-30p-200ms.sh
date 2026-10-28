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
profile="$WBD_STRESS_PROFILE"
case "$profile" in 0|1|2|3|4|5|6) ;; *) echo BAD_FIXED_PROFILE >&2;exit 2;; esac
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
  --tunnel-id 00112233445566778899aabbccddeeff --mode "$mode" --fec-profile "$profile"
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
# Keep original authenticated TLS/FakeTCP startup and native TUN zero-loss
# admission check. Apply true netem ONLY to sustained business phase.
test "$WBD_ARM64_CAPACITY_TRIAL" = impaired-60
case "$WBD_STRESS_NAME:$mode:$profile:$WBD_UNDERLAY_CAP_MBIT:$WBD_STRESS_MBIT" in
  fec6-150m-30p-200ms:fec-fixed:6:150:50|game4-20m-30p-200ms:game4:1:20:3) ;;
  *) echo "M0_IMPAIRED_UNAUTHORIZED_SCENARIO" >&2; exit 2;;
esac
# Each egress veth is the sole underlay for all auth lanes from its endpoint.
# netem rate is applied to surviving egress traffic (NOT a wire-time
# shaper before erased packet slots); capture the limitation in final report.
for spec in "$client_ns:v4ac" "$server_ns:v4as"; do
  nsname=$(echo "$spec" | cut -d: -f1)
  ifname=$(echo "$spec" | cut -d: -f2)
  sudo -n ip netns exec "$nsname" tc qdisc replace dev "$ifname" root \
    netem delay 200ms loss random 30% rate "$WBD_UNDERLAY_CAP_MBIT"mbit limit 20000
done
sudo -n ip netns exec "$client_ns" tc -d -s qdisc show dev v4ac >"$out/impair-c2s-config.txt"
sudo -n ip netns exec "$server_ns" tc -d -s qdisc show dev v4as >"$out/impair-s2c-config.txt"
grep -q "netem" "$out/impair-c2s-config.txt"
grep -q "netem" "$out/impair-s2c-config.txt"
# Diagnostic only; do not demand zero loss in intentionally damaged path.
(sudo -n ip netns exec "$client_ns" timeout 14s ping -n -I v4ac -i .35 -c 12 -W 1 198.18.7.2 \
  >"$out/underlay-loss-rtt-preflight.log" 2>&1 || true)
echo "M0_REAL_UNDERLAY_NETEM_APPLIED loss_pct=30 one_way_delay_ms=200" \
  "survivor_shaper_mbps=$WBD_UNDERLAY_CAP_MBIT" \
  "inner_offered_mbps=$WBD_STRESS_MBIT" \
  "scope=both_directions_shared_all_lanes"
# One measurement job per Action; no on-demand Rust/Go compilation.
if [ "$WBD_ARM64_CAPACITY_TRIAL" = impaired-60 ]; then
  rate="$WBD_STRESS_MBIT"
  duration="$WBD_STRESS_SECONDS"
  case "$rate" in 3|10|20|50|100|200|500) ;; *) exit 2;; esac
  case "$duration" in 60|120) ;; *) exit 2;; esac
  printf '%s\n' "$WBD_STRESS_NAME $mode fixed_grade=$profile rate=$rate duration=$duration" >"$out/stress-effective.txt"
  (uname -a; for f in /sys/fs/cgroup/cpu.max /sys/fs/cgroup/cpu/cpu.cfs_quota_us /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory/memory.limit_in_bytes; do if [ -r "$f" ]; then printf "HOST_CGROUP_FOUND %s " "$f"; cat "$f"; else printf "HOST_CGROUP_UNAVAILABLE %s\n" "$f"; fi; done) >"$out/host-system.txt"
  (for f in /proc/pressure/cpu /proc/pressure/memory; do if [ -r "$f" ]; then cat "$f"; else echo "PSI_UNAVAILABLE $f"; fi; done) >"$out/host-psi-before.txt"
  sudo -n ip netns exec "$client_ns" tc -s qdisc show dev v4ac >"$out/underlay-client-qdisc-before.txt"
  sudo -n ip netns exec "$server_ns" tc -s qdisc show dev v4as >"$out/underlay-server-qdisc-before.txt"
  touch "$out/sampling-active"
  (
    while [ -f "$out/sampling-active" ]; do
      echo "SAMPLE_UNIX_MS $(date +%s%3N)"
      ps -C wbd-v4-client,wbd-v4-server,iperf3 -o pid=,comm=,pcpu=,rss=,etime= || true
      echo "CGROUP_CPU_STAT"
      cat /sys/fs/cgroup/cpu.stat || true
      echo "CGROUP_MEMORY_CURRENT"
      cat /sys/fs/cgroup/memory.current || true
      echo "NETEM_EGRESS_C2S"
      sudo -n ip netns exec "$client_ns" tc -s qdisc show dev v4ac || true
      echo "NETEM_EGRESS_S2C"
      sudo -n ip netns exec "$server_ns" tc -s qdisc show dev v4as || true
      sleep 1
    done
  ) >"$out/host-1hz.txt" 2>"$out/host-1hz.stderr" &
  monitor=$!
  (sudo -n ip netns exec "$client_ns" timeout 68s ping -n -I wbdcl -i .1 -c 540 -W 1 10.188.18.2 >"$out/tun-rtt-probes.log" 2>&1 || true) &
  rtt=$!
  sudo -n ip netns exec "$server_ns" iperf3 -s -1 -B 10.188.18.2 -p 5201 >"$out/iperf-server.log" 2>&1 &
  sleep 1
  set +e
  sudo -n ip netns exec "$client_ns" timeout 140s iperf3 -c 10.188.18.2 -B 10.188.18.1 -p 5201 --bidir -u -b "$rate"M -l 1000 -t "$duration" -J >"$out/iperf-client.json" 2>"$out/iperf-client.stderr"
  stress_rc=$?
  set -e
  wait "$rtt" || true
  rm -f "$out/sampling-active"
  wait "$monitor" || true
  (for f in /proc/pressure/cpu /proc/pressure/memory; do if [ -r "$f" ]; then cat "$f"; else echo "PSI_UNAVAILABLE $f"; fi; done) >"$out/host-psi-after.txt"
  sudo -n ip netns exec "$client_ns" tc -s qdisc show dev v4ac >"$out/underlay-client-qdisc-after.txt"
  sudo -n ip netns exec "$server_ns" tc -s qdisc show dev v4as >"$out/underlay-server-qdisc-after.txt"
  sudo -n ip -s -n "$client_ns" link show v4ac >"$out/underlay-client-interface-after.txt"
  sudo -n ip -s -n "$server_ns" link show v4as >"$out/underlay-server-interface-after.txt"
  echo "$stress_rc" >"$out/iperf-exit.txt"
  if [ "$stress_rc" -ne 0 ]; then
    echo "M0_GRADE_STRESS_IPERF_FAILED exit=$stress_rc" >&2
    tail -n 25 "$out/iperf-client.stderr" >&2 || true
    echo "M0_IMPAIRED_IPERF_FAILURE_RECORDED_NOT_SILENCED" >&2
  fi
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
if [ "$WBD_ARM64_CAPACITY_TRIAL" = impaired-60 ]; then
  OUTPUT="$out" python3 - <<'PY'
import json,os,pathlib,re,math,statistics
p=pathlib.Path(os.environ["OUTPUT"])
scenario=os.environ["WBD_STRESS_NAME"]
mode=os.environ["WBD_V4_MODE"]
profile=int(os.environ["WBD_STRESS_PROFILE"])
target=int(os.environ["WBD_STRESS_MBIT"])*1000000
raw=(p/"iperf-client.json").read_text(errors="replace")
try:
 d=json.loads(raw)
except Exception as e:
 d={"error":"INVALID_IPERF_JSON "+str(e)}
e=d.get("end",{})
f=e.get("sum_received",{})
b=e.get("sum_received_bidir_reverse",{})
rates=[f.get("bits_per_second"),b.get("bits_per_second")]
loss=[f.get("lost_percent"),b.get("lost_percent")]
offered=[f.get("packets"),b.get("packets")]
seconds=[f.get("seconds"),b.get("seconds")]
rtt=[float(x) for x in re.findall(r"\btime=([0-9.]+) ms",(p/"tun-rtt-probes.log").read_text())]
def quantile(v,q):
 if not v:return None
 v=sorted(v)
 k=min(len(v)-1,int((len(v)-1)*q))
 return v[k]
def qdisc(fn):
 z=(p/fn).read_text(errors="replace")
 return {"dropped":sum(map(int,re.findall(r"\bdropped (\d+)",z))),
         "overlimits":sum(map(int,re.findall(r"\boverlimits (\d+)",z))),
         "backlog_bytes":sum(map(int,re.findall(r"\bbacklog (\d+)b",z))),
         "backlog_packets":sum(map(int,re.findall(r"\bbacklog \d+b (\d+)p",z))),
         "has_netem":bool(re.search(r"\bnetem\b",z))}
c=qdisc("underlay-client-qdisc-after.txt")
v=qdisc("underlay-server-qdisc-after.txt")
rb={}
logs={}
for side in ("client","server"):
 log=(p/(side+".log")).read_text(errors="replace")
 logs[side]={"bytes":len(log),"game_ready":bool(re.search("V4_ORIGINAL_GO_GAME_NATIVE_READY role="+side,log)),
 "auth_rejected_nonzero":bool(re.search(r"auth_rejected=[1-9]",log)),
 "fec_line_count":log.count("V4_PUBLIC_FEC2_READBACK role="+side),
 "fec_report_tail":[line[:600] for line in log.splitlines() if ("FEC2" in line or "GAME_KERNEL" in line or "M2_" in line)][-12:]}
 m=re.findall(r"V4_PUBLIC_FEC2_READBACK role="+side+
 r" mode=(\w+) requested=(\d+) applied=(\d+) profile=(\d+) pending=(\w+)",log)
 rb[side]=dict(zip(("mode","requested","applied","profile","pending"),m[-1])) if m else None
applied=(all(x and x["mode"]=="fixed" and x["profile"]=="6" and x["pending"]=="false" and int(x["applied"])>0 for x in rb.values())
         if mode=="fec-fixed" else
         all(logs[side]["game_ready"] and not logs[side]["auth_rejected_nonzero"] for side in ("client","server")))
host=(p/"host-1hz.txt").read_text(errors="replace")
procs={}
for m in re.finditer(r"^\s*(\d+)\s+(wbd-v4-client|wbd-v4-server|iperf3)\s+([0-9.]+)\s+(\d+)\s+(\S+)",host,re.M):
 pid,name,cpu,rss,uptime=m.groups()
 x=procs.setdefault(name,{"cpu_pct_samples":[],"rss_kib_samples":[]})
 x["cpu_pct_samples"].append(float(cpu))
 x["rss_kib_samples"].append(int(rss))
ps={name:{"samples":len(x["cpu_pct_samples"]),
          "cpu_percent_max":max(x["cpu_pct_samples"]),
          "cpu_percent_mean":round(statistics.mean(x["cpu_pct_samples"]),2),
          "rss_kib_max":max(x["rss_kib_samples"])} for name,x in procs.items()}
n=len(re.findall("SAMPLE_UNIX_MS",host))
stats=[]
for block in d.get("intervals",[]):
 stats.append([{"bits_per_second":stream.get("bits_per_second"),
                "lost_packets":stream.get("lost_packets"),
                "jitter_ms":stream.get("jitter_ms"),
                "sender":stream.get("sender")} for stream in block.get("streams",[])])
rc=int((p/"iperf-exit.txt").read_text().strip())
measured=(rc==0 and all(isinstance(x,(int,float)) for x in rates+loss)
          and all(isinstance(x,(int,float)) and x>=55 for x in seconds))
actual_loss_bounded=measured and max(loss)<=1.0
actual_rate_bounded=measured and min(rates)>=.8*target
proof=(c["has_netem"] and v["has_netem"] and
       c["dropped"]>0 and v["dropped"]>0)
# The attached netem rate only shapes the surviving packets. Do not claim
# it models on-wire time for frames intentionally erased before shaping.
quality=("PASS_SCOPED_SUSTAINED_LOSS" if measured and applied and proof
         and actual_loss_bounded and actual_rate_bounded
         else "FAIL_OR_INCONCLUSIVE_QUALIFICATION")
result={
 "schema":1,"run":os.environ["GITHUB_RUN_ID"],"harness_source":os.environ["GITHUB_SHA"],
 "original_product_source":os.environ["WBD_ARM64_FROZEN_SOURCE"],
 "binary_architecture":"native ARM64 original Go TLS Rust owner raw/TUN",
 "scenario":scenario,"mode":mode,"fixed_profile_requested":profile,
 "line_parameters":{"per_direction_survivor_shaper_mbps":int(os.environ["WBD_UNDERLAY_CAP_MBIT"]),
   "random_kernel_netem_loss_percent_requested":30,"one_way_delay_ms_requested":200,
   "shared_physical_veth_per_direction_across_game_lanes":True,
   "line_rate_scope_limitation":"NETEM_SHAPES_SURVIVING_EGRESS_ONLY; DROPPED_FRAMES_DO_NOT_USE_RATE_BUDGET; NOT_EXACT_PRELOSS_WIRE_CAPACITY"},
 "business_offered_target_mbps_per_direction":int(os.environ["WBD_STRESS_MBIT"]),
 "iperf_exit":rc,"iperf_error":d.get("error"),
 "actual_udp_received_mbps_each":[x/1e6 if x is not None else None for x in rates],
 "actual_udp_lost_pct_each":loss,"actual_udp_receiver_packets_each":offered,
 "receiver_observed_seconds_each":seconds,"per_interval_iperf_both_directions":stats,
 "netem_egress":{"client_to_server":c,"server_to_client":v},
 "impairment_real_kernel_drop_verified_both_directions":proof,
 "authenticated_effective_profile":rb,"live_runtime_evidence":logs,"runtime_applied_or_game_ready":applied,
 "host_process_1hz":ps,"host_sampling_samples":n,
 "icmp_probes_under_load":{"received":len(rtt),"rtt_p50_ms":quantile(rtt,.5),
                            "rtt_p95_ms":quantile(rtt,.95),"rtt_p99_ms":quantile(rtt,.99),
                            "sent_probe_count_requested":540,
                            "application_business_latency_p99":"NOT_RUN"},
 "host_instrumentation":["host-1hz.txt","host-psi-before.txt","host-psi-after.txt",
   "host-system.txt","underlay-client-qdisc-after.txt","underlay-server-qdisc-after.txt"],
 "measured_full_60s":measured,"received_rate_ge_80pct_offered":actual_rate_bounded,
 "observed_application_udp_loss_le_1pct":actual_loss_bounded,
 "quality":quality,"owned_stop":"PASSED_PRE_REPORT_BOTH",
 "notes":["Result describes Linux hosted ARM64 native; not physical Windows",
 "Game4 lane replication not same as FEC6 maximum",
 "No k/r group histogram, per-business first arrival 10ms, per-lane loss or queue age precise",
 "ICMP RTT not calibrated one-way latency and lost probes are censored"]}
(p/"impaired-30p-200ms-diagnostic.json").write_text(json.dumps(result,indent=2)+"\n")
print("M0_IMPAIRED_SUSTAINED_RECEIPT "+json.dumps({k:result[k] for k in
 ("scenario","actual_udp_received_mbps_each","actual_udp_lost_pct_each",
 "netem_egress","host_process_1hz","quality")}))
assert proof,"REAL_NETEM_IMPAIRMENT_NOT_VERIFIED"
assert applied,"LIVE_FEC_OR_GAME_NOT_APPLIED"
assert measured,"IPERF_GENUINE_60S_NOT_COMPLETED"
assert quality=="PASS_SCOPED_SUSTAINED_LOSS","EXPECTED_1PCT_OR_CAPACITY_UNMET"
PY
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
