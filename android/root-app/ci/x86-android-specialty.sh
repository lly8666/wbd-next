#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
out=out/android-x86-d2-root/specialty
n=out/android-root-app-native
mkdir -p "$out"
test "$(cat "$n/SOURCE")" = "$GITHUB_SHA"
(cd "$n" && sha256sum -c SHA256SUMS) >"$out/source-sha.txt"
test -s "$n/wiring-specialty-amd64"
adb="$ANDROID_HOME/platform-tools/adb"
"$adb" install -r out/apk/app-su.apk
"$adb" install -r out/android-traffic-fixture/traffic-fixture.apk
"$adb" install -r out/android-traffic-fixture/traffic-fixture2.apk
"$adb" shell logcat -c
"$adb" shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step specialty_scope
scope=""
for i in $(seq 1 20);do
  scope="$("$adb" shell logcat -d -s WBD_X86_CI_ORIGINAL:I '*:S' | tr -d '\r' | sed -n 's/.*B90_SCOPE //p' | tail -1)"
  [[ -n "$scope" ]] && break
  sleep 0.5
done
read -r handle iface index mtu local extra <<<"$scope"
[[ "$handle" =~ ^[0-9]+$ && "$iface" =~ ^[a-zA-Z0-9_-]+$ && "$index" =~ ^[0-9]+$ && "$mtu" =~ ^[0-9]+$ && "$local" =~ ^[0-9.]+$ && -z "$extra" ]]
"$adb" shell pm list packages -U --user 0 | tr -d '\r' >"$out/fixture-packages.txt"
uid_of(){ awk -v p="package:$1" '$1==p && $2~/^uid:[0-9]+$/{sub(/^uid:/,"",$2);print $2}' "$out/fixture-packages.txt"; }
uid="$(uid_of org.wbdnext.testtraffic)"
bypass="$(uid_of org.wbdnext.testtraffic2)"
own="$(uid_of org.wbdnext.rootclient)"
manager="$(uid_of me.weishu.kernelsu)"
for id in "$uid" "$bypass" "$own" "$manager";do [[ "$id" =~ ^[0-9]+$ && "$id" -ge 10000 ]];done
# Same proven root-owned directory and cp staging as D1. No cross-owner mv.
guest=/data/local/tmp/wbd-x86-ci
"$adb" push "$n/wiring-specialty-amd64" /data/local/tmp/wbd-b91-bin.stage
"$adb" push out/android-root-app-cn/wbd-cn-ipv4.txt /data/local/tmp/wbd-b91-cn.stage
"$adb" shell su -c 'set -eu; p=/data/local/tmp/wbd-x86-ci; test "$(stat -c %u "$p")" = 0; cp /data/local/tmp/wbd-b91-bin.stage "$p/wiring-specialty"; cp /data/local/tmp/wbd-b91-cn.stage "$p/cn.txt"; chmod 700 "$p/wiring-specialty"; chmod 600 "$p/cn.txt"' >"$out/stage.txt" 2>&1
"$adb" shell su -c 'sha256sum /data/local/tmp/wbd-x86-ci/wiring-specialty /data/local/tmp/wbd-x86-ci/libwbd_engine.so /data/local/tmp/wbd-x86-ci/cn.txt' >"$out/guest-sha.txt"
for f in "$n/wiring-specialty-amd64" "$n/libwbd_engine-amd64.so" out/android-root-app-cn/wbd-cn-ipv4.txt;do grep -Fq "$(sha256sum "$f" | cut -d' ' -f1)" "$out/guest-sha.txt";done
echo B91_TEST_STAGE_PASS
shard="${WBD_ANDROID_SPECIALTY_SHARD:-all}"
case "$shard" in
 combined-*) scenes=("$shard");;
 options-*) scenes=("$shard");;
 network-normal) scenes=(network-normal);;
 cycle-*) scenes=("$shard");;
 daily-normal) scenes=(daily-dns-physical-normal daily-dns-cn-normal daily-dns-tunnel-normal);;
 daily-fixed) scenes=(daily-dns-physical-fec-fixed);;
 daily-auto) scenes=(daily-dns-physical-fec-auto);;
 daily-game2) scenes=(daily-dns-physical-game2 daily-dns-physical-game2-fixed daily-dns-tunnel-game2);;
 daily-game4) scenes=(daily-dns-physical-game4 daily-dns-physical-game4-fixed daily-dns-cn-game4);;
 daily-route-*) scenes=("$shard");;
 mixed-*) m="${shard#mixed-}";scenes=("mixed-$m-lowfirst" "mixed-$m-lowlast")
  if [[ "$m" == game4* ]];then scenes+=("mixed-$m-lowmiddle" "mixed-$m-two");fi;;
 crash-*) scenes=("$shard");;
 dns6-relay) scenes=(dns6-relay);;
 wire-*) scenes=("$shard");;
 dns6) scenes=(system-dns6);;
 mtu-*)
  m="${shard#mtu-}"
  scenes=("mtu-$m-1280" "mtu-$m-1460" "mtu-$m-1500" "mtu-$m-peer1200");;
 routes) scenes=(route-single route-group route-all);;
 route-single|route-group|route-all) scenes=("$shard");;
 normal) scenes=(normal);;
 fec-fixed|fec-auto) scenes=("$shard");;
 game2) scenes=(game2 game2-fixed);;
 game4) scenes=(game4 game4-fixed);;
 dns-physical) scenes=(system-physical);;
 dns-tc) scenes=(system-physical-tc);;
 dns-tunnel) scenes=(system-tunnel);;
 dns-cn) scenes=(system-cn);;
 all) scenes=(system-physical system-tunnel system-cn route-single route-group route-all normal fec-fixed fec-auto game2 game2-fixed game4 game4-fixed);;
 *) echo "unknown specialty shard: $shard";exit 2;;
esac
: >"$out/results.tsv"
dns_pid=""
uid_pid=""
tcp_pids=()
local_aliases=()
cleanup(){
 if [[ "$shard" == network-normal && "$iface" == wlan0 ]];then "$adb" shell svc wifi enable >/dev/null 2>&1 || true;fi
 if [[ -n "$uid_pid" ]];then kill "$uid_pid" 2>/dev/null || true;wait "$uid_pid" 2>/dev/null || true;fi
 if [[ -n "$dns_pid" ]];then sudo -n kill "$dns_pid" 2>/dev/null || true;wait "$dns_pid" 2>/dev/null || true;fi
 for pid in "${tcp_pids[@]}";do kill "$pid" 2>/dev/null || true;wait "$pid" 2>/dev/null || true;done
 for address in "${local_aliases[@]}";do sudo -n ip addr del "$address/32" dev lo || true;done
}
trap cleanup EXIT
# Real local DNS fixture; a failure cannot block independent native tests.
if [[ "$shard" == dns-physical || "$shard" == dns-tc || "$shard" == dns-cn || "$shard" == dns6 || "$shard" == dns6-relay || "$shard" == crash-dns || "$shard" == daily-normal || "$shard" == daily-fixed || "$shard" == daily-auto || "$shard" == daily-game2 || "$shard" == daily-game4 || "$shard" == cycle-* || "$shard" == options-* || "$shard" == combined-* || "$shard" == network-normal || "$shard" == all ]];then
 sudo -n timeout 190s python3 -u android/root-app/ci/b90-dns-fixture.py >"$out/dns-host.log" 2>&1 &
 dns_pid=$!
 for i in $(seq 1 20);do grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log" && break;sleep 0.2;done
fi
if [[ "$shard" == route-* || "$shard" == routes || "$shard" == crash-* || "$shard" == daily-route-* || "$shard" == combined-* || "$shard" == cycle-* || "$shard" == all ]];then
 # The host owns these exact /32s ONLY during this isolated runner test.
 # No request can be intentionally sent to the external CN endpoint.
 for address in 192.0.2.1 1.0.1.1;do
  sudo -n ip addr add "$address/32" dev lo
  local_aliases+=("$address")
  ip -4 route get "$address" | grep -Eq "^local $address .*dev lo"
 done
 timeout 300s python3 -u android/root-app/ci/b94-uid-echo.py >"$out/uid-host.log" 2>&1 &
 uid_pid=$!
 for i in $(seq 1 20);do grep -Fq B94_UID_FIXTURE_READY "$out/uid-host.log" && break;sleep .2;done
fi
if [[ "$shard" == daily-route-* || "$shard" == combined-* ]];then
 for address in 192.0.2.1 1.0.1.1;do
  timeout 290s python3 -u android/root-app/ci/traffic-fixture/server.py --bind "$address" --port 18080 >"$out/tcp-$address.log" 2>&1 &
  tcp_pids+=("$!")
  for i in $(seq 1 25);do grep -Fq "WBD test echo TCP+UDP" "$out/tcp-$address.log" && break;sleep .2;done
  grep -Fq "WBD test echo TCP+UDP" "$out/tcp-$address.log"
 done
fi
failed=0
record(){ printf '%s\t%s\n' "$1" "$2" >>"$out/results.tsv";echo "B92_RESULT $shard $1 $2";if [[ "$2" != PASS ]];then failed=1;fi; }
invoke(){ timeout "$1" "$adb" shell su -c "$guest/wiring-specialty $2 $scope $uid $bypass $own $manager $guest/cn.txt"; }
clean_kernel(){
 local name="$1" rc=0
 {
 local cmds=('ip -4 rule show' 'ip -4 route show table all' 'ip -o link show' 'iptables -w 2 -t nat -S OUTPUT')
 if [[ "$shard" == dns6 ]];then cmds+=('ip -6 rule show' 'ip -6 route show table all' 'ip6tables -w 2 -t nat -S OUTPUT');fi
 for cmd in "${cmds[@]}";do
  printf 'READBACK %s\n' "$cmd"
  "$adb" shell "su -c '$cmd'" || rc=1
 done
 } >"$out/$name-kernel.txt" 2>&1
 if [[ "$rc" != 0 ]];then cat "$out/$name-kernel.txt";return 1;fi
 if grep -Eq '(^|[[:space:]])9099:|lookup (19842|19843|19845|19846)( |$)|table (19842|19843|19845|19846)( |$)|wbdb90:|wbdb91dns:|wbdb91m4:|wbdb100:|wbd_dns0:|wbd_dns6:|wbd-next-root-(app-tcp-dns|system-dns|system-dns6)-v1' "$out/$name-kernel.txt";then
  grep -E 'lookup (19842|19843|19845|19846)( |$)|table (19842|19843|19845|19846)( |$)|wbdb90:|wbdb91dns:|wbdb91m4:|wbdb100:|wbd_dns0:|wbd_dns6:|wbd-next-root-(app-tcp-dns|system-dns|system-dns6)-v1' "$out/$name-kernel.txt" | sed -n '1,25p'
  return 1
 fi
 return 0
}
# B91 physical UDP/TC TCP already passed; no standalone repeat.
clean=1
if ! clean_kernel baseline;then clean=0;fi
for scene in "${scenes[@]}";do
 if [[ "$clean" != 1 ]];then record "$scene" NOT_RUN;continue;fi
 if [[ "$scene" == network-normal ]];then
  status=FAIL
  if [[ "$iface" != wlan0 ]];then record "$scene" ENV_BLOCKED;continue;fi
  if ! grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log";then record "$scene" ENV_BLOCKED;continue;fi
  old_handle="$handle"
  "$adb" shell logcat -c
  "$adb" shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step lifecycle_watch >"$out/network-watch.txt"
  sleep .5
  "$adb" shell logcat -d -s WBD_X86_CI_ORIGINAL:I '*:S' | tr -d '\r' >"$out/network-watch-log.txt"
  if ! grep -Fq "B93_NETWORK_WATCH_ARMED $old_handle" "$out/network-watch-log.txt";then record "$scene" ENV_BLOCKED;continue;fi
  rc=0
  invoke 95s network-normal >"$out/$scene.log" 2>&1 || rc=$?
  "$adb" shell svc wifi enable >"$out/network-enable.txt" 2>&1
  recovered=0
  for _ in $(seq 1 30);do
   "$adb" shell logcat -c
   "$adb" shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step specialty_scope >/dev/null
   sleep .5
   fresh="$("$adb" shell logcat -d -s WBD_X86_CI_ORIGINAL:I '*:S' | tr -d '\r' | sed -n 's/.*B90_SCOPE //p' | tail -1)"
   read -r new_handle new_iface new_index new_mtu new_local new_extra <<<"$fresh"
   if [[ "$new_handle" =~ ^[0-9]+$ && "$new_handle" != "$old_handle" && "$new_iface" == wlan0 && "$new_index" =~ ^[0-9]+$ && "$new_mtu" =~ ^[0-9]+$ && "$new_local" =~ ^[0-9.]+$ && -z "$new_extra" ]];then
    scope="$fresh";recovered=1;break
   fi
  done
  if ! clean_kernel network-before-reconnect;then clean=0;fi
  if [[ "$recovered" == 1 && "$clean" == 1 ]];then
   echo "B105_NEW_PHYSICAL_NETWORK_PASS $old_handle $new_handle" >>"$out/$scene.log"
   if invoke 80s daily-dns-physical-normal >>"$out/$scene.log" 2>&1 &&
      grep -Fq B102_DAILY_DNS_PASS "$out/$scene.log";then
    echo B105_MANUAL_NEW_NETWORK_RECONNECT_PASS >>"$out/$scene.log"
    if [[ "$rc" == 0 ]] && grep -Fq B105_ACTIVE_SCOPE_STOP_PASS "$out/$scene.log" &&
       grep -Fq B106_ACTIVE_SELECTED_NETWORK_LOST_PASS "$out/$scene.log";then status=PASS;fi
   fi
  fi
  if ! clean_kernel "$scene";then clean=0;status=FAIL;fi
  cat "$out/$scene.log";record "$scene" "$status"
  continue
 fi
 if [[ "$scene" == crash-* ]];then
  status=FAIL
  code=0
  invoke 120s "$scene" >"$out/$scene.log" 2>&1 || code=$?
  recovery="recover-${scene#crash-}"
  echo "B100_CRASH_PROCESS_EXIT $scene $code" | tee -a "$out/$scene.log"
  # Each command is one fully quoted remote su invocation, exactly as
  # clean_kernel. B100 split the command at ';' in the adb remote shell.
  readback=0
  {
   for cmd in 'ip -4 rule show' 'ip -4 route show table all' 'ip -o link show' 'iptables -w 2 -t nat -S OUTPUT' 'ls -l /data/local/tmp/wbd-x86-ci/b100-recovery';do
    printf 'READBACK %s\n' "$cmd"
    "$adb" shell "su -c '$cmd'" || readback=1
   done
  } >"$out/$scene-after-exit.txt" 2>&1
  if [[ "$code" == 86 && "$readback" == 0 ]] && grep -Fq B100_CRASH_ARMED "$out/$scene.log" &&
     grep -Fq route-journal.json "$out/$scene-after-exit.txt" &&
     grep -Eq 'lookup 19842( |$)' "$out/$scene-after-exit.txt";then
   echo B101_CRASH_DURABLE_READBACK_PASS >>"$out/$scene.log"
   if invoke 120s "$recovery" >>"$out/$scene.log" 2>&1 &&
      grep -Fq "B100_RECOVER_PASS $recovery" "$out/$scene.log" &&
      grep -Fq B100_CRASH_IDEMPOTENT_RESTORE_PASS "$out/$scene.log";then status=PASS;fi
  fi
  if ! clean_kernel "$scene";then clean=0;status=FAIL;fi
  cat "$out/$scene-after-exit.txt" "$out/$scene.log"
  record "$scene" "$status"
  continue
 fi
 if [[ "$scene" == system-physical || "$scene" == system-physical-tc || "$scene" == system-cn || "$scene" == system-dns6 ]] && ! grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log";then record "$scene" ENV_BLOCKED;continue;fi
 limit=100s
 if [[ "$scene" == cycle-* ]];then
  limit=170s
  if ! grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log" || ! grep -Fq B94_UID_FIXTURE_READY "$out/uid-host.log";then record "$scene" ENV_BLOCKED;continue;fi
 fi
 if [[ "$scene" == daily-route-* ]];then limit=260s;fi
 if [[ "$scene" == combined-* ]];then limit=110s;fi
 if [[ "$scene" == daily-dns-* ]];then
  limit=100s
  if ! grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log";then record "$scene" ENV_BLOCKED;continue;fi
 fi
 if [[ "$scene" == route-* ]];then
  limit=240s
  if ! grep -Fq B94_UID_FIXTURE_READY "$out/uid-host.log";then record "$scene" ENV_BLOCKED;continue;fi
 fi
 status=FAIL
 if invoke "$limit" "$scene" >"$out/$scene.log" 2>&1;then
  case "$scene" in
   combined-*) if grep -Fq "B106_COMBINED_PASS $scene" "$out/$scene.log" &&
      grep -Fq B106_ACTIVE_UID_CN_FIB_PASS "$out/$scene.log" &&
      grep -Fq B91_NATIVE_STOP_PASS "$out/$scene.log" &&
      grep -Fq B91_NATIVE_TUN_CLOSE_PASS "$out/$scene.log";then
       expected=6;if [[ "$scene" == combined-group ]];then expected=10;fi
       if [[ "$(grep -c B106_ACTIVE_COMBINED_PROBE_PASS "$out/$scene.log")" == "$expected" ]] &&
          grep -Fq B107_SERVER_HOSTNAME_BOOTSTRAP_PASS "$out/$scene.log" &&
          grep -Fq "B90_FIXTURE target.test UDP" "$out/dns-host.log" &&
          grep -Fq "B90_FIXTURE default1.wbd-b107.test" "$out/dns-host.log";then
         status=PASS
         if [[ "$scene" == combined-group ]];then grep -Fq "B90_FIXTURE default2.wbd-b107.test" "$out/dns-host.log" || status=FAIL;fi
       fi
     fi ;;
   options-*) if grep -Fq "B105_OPTIONS_PASS $scene" "$out/$scene.log" &&
       grep -Fq B105_AUTH_OPTIONS_PASS "$out/$scene.log" &&
       grep -Fq B105_OUTER_ENABLED_PASS "$out/$scene.log" &&
       grep -Fq B105_SYSTEM_RESOLVER_WITH_M4_PASS "$out/$scene.log" &&
       grep -Fq B105_ORDINARY_BUSINESS_WITH_OPTIONS_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_UID_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_TUN_CLOSE_PASS "$out/$scene.log" &&
       grep -Fq "B90_FIXTURE system.wbd-b91.test" "$out/dns-host.log";then status=PASS;fi ;;
   cycle-*) if grep -Fq "B103_CYCLE_PASS $scene" "$out/$scene.log" &&
      [[ "$(grep -c B103_CYCLE_STOP_AND_PHYSICAL_PASS "$out/$scene.log")" == 3 ]] &&
      [[ "$(grep -c B91_NATIVE_STOP_PASS "$out/$scene.log")" == 3 ]] &&
      [[ "$(grep -c B91_NATIVE_TUN_CLOSE_PASS "$out/$scene.log")" == 3 ]] &&
      grep -Fq B103_STEADY_DNS_AND_ACTIVITY_SWITCH_PASS "$out/$scene.log";then status=PASS;fi ;;
   daily-route-*) if grep -Fq "B102_DAILY_ROUTE_PASS $scene" "$out/$scene.log" &&
       [[ "$(grep -c B102_DIRECT_TCP_UDP_PASS "$out/$scene.log")" == 4 ]];then status=PASS;fi ;;
   daily-dns-*) if grep -Fq "B102_DAILY_DNS_PASS $scene" "$out/$scene.log" &&
       grep -Fq B102_NATIVE_DNS_AND_BUSINESS_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_UID_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_TUN_CLOSE_PASS "$out/$scene.log";then
        status=PASS
        case "$scene" in
          daily-dns-physical-*) for stage in B102_NATIVE_DNS_UDP_ROUNDTRIP_PASS B102_APP_DNS_TCP_ROUNDTRIP_PASS;do grep -Fq "$stage" "$out/$scene.log" || status=FAIL;done;;
          daily-dns-cn-*) for stage in B102_NATIVE_DNS_UDP_ROUNDTRIP_PASS B102_APP_DNS_TCP_ROUNDTRIP_PASS B102_NATIVE_DNS_TUNNEL_TX_PASS;do grep -Fq "$stage" "$out/$scene.log" || status=FAIL;done;;
          daily-dns-tunnel-*) grep -Fq B102_NATIVE_DNS_TUNNEL_TX_PASS "$out/$scene.log" || status=FAIL;;
        esac
     fi ;;
   system-*) if grep -Fq "B91_SYSTEM_DNS_QUERY_PASS $scene" "$out/$scene.log" && grep -Fq "B91_SYSTEM_DNS_STOP_PASS $scene" "$out/$scene.log";then status=PASS;fi ;;
   dns6-relay) if grep -Fq B100_DNS6_RELAY_PASS "$out/$scene.log" &&
       grep -Fq B100_DNS6_RELAY_STOP_PASS "$out/$scene.log" &&
       [[ "$(grep -c B100_DNS6_RELAY_SOCKET_PASS "$out/$scene.log")" == 2 ]];then status=PASS;fi ;;
   mixed-*) if grep -Fq "B100_MIXED_MSS_PASS $scene" "$out/$scene.log" &&
       grep -Fq B99_RAW_WIRE_WITNESS "$out/$scene.log" &&
       grep -Fq B98_MTU_OS_READBACK_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_TUN_CLOSE_PASS "$out/$scene.log";then status=PASS;fi ;;
   wire-*) if grep -Fq "B99_WIRE_SCENE_PASS $scene" "$out/$scene.log" &&
       grep -Fq B99_RAW_WIRE_WITNESS "$out/$scene.log" &&
       grep -Fq B98_MTU_DF_OVERSIZE_REJECT_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_UID_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_TUN_CLOSE_PASS "$out/$scene.log";then status=PASS;fi ;;
   mtu-*) if grep -Fq "B98_MTU_SCENE_PASS $scene" "$out/$scene.log" &&
       grep -Fq B98_MTU_OS_READBACK_PASS "$out/$scene.log" &&
       [[ "$(grep -c B98_MTU_BOUNDARY_TX_PASS "$out/$scene.log")" == 2 ]] &&
       grep -Fq B98_MTU_DF_OVERSIZE_REJECT_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_UID_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_STOP_PASS "$out/$scene.log" &&
       grep -Fq B91_NATIVE_TUN_CLOSE_PASS "$out/$scene.log";then status=PASS;fi ;;
   route-*) m="$(printf '%s' "$scene" | cut -d- -f2 | tr 'a-z' 'A-Z')"
     if grep -Fq "B90_ROUTE_$m"_"UID_PACKET_CN_PASS" "$out/$scene.log" && grep -Fq "B90_ROUTE_$m"_"STOP_PASS" "$out/$scene.log" && grep -Fq B90_TUN_CLOSE_PASS "$out/$scene.log";then status=PASS;fi ;;
   *) if grep -Fq "B91_NATIVE_M4_STARTED $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_APP_TX_PASS $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_UID_STOP_PASS $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_STOP_PASS $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_TUN_CLOSE_PASS $scene" "$out/$scene.log";then status=PASS;fi ;;
  esac
 fi
 if [[ "$scene" == daily-dns-physical-* || "$scene" == daily-dns-cn-* ]];then
  name=system.wbd-b91.test;if [[ "$scene" == daily-dns-cn-* ]];then name=cn.wbd-b91.test;fi
  for proto in UDP TCP;do grep -Fq "B90_FIXTURE $name $proto" "$out/dns-host.log" || status=FAIL;done
 fi
 if [[ "$scene" == system-physical ]] && ! grep -Fq "B90_FIXTURE system.wbd-b91.test" "$out/dns-host.log";then status=FAIL;fi
 if [[ "$scene" == dns6-relay ]];then
  for proto in UDP TCP;do grep -Fq "B90_FIXTURE system.wbd-b91.test $proto" "$out/dns-host.log" || status=FAIL;done
 fi
 if [[ "$scene" == system-dns6 ]];then
  for proto in udp tcp;do grep -Fq "B99_DNS6_EXPLICIT_SOCKET_PASS $proto" "$out/$scene.log" || status=FAIL;done
  for proto in UDP TCP;do grep -Fq "B90_FIXTURE system.wbd-b91.test $proto" "$out/dns-host.log" || status=FAIL;done
 fi
 if [[ "$scene" == route-* ]];then
  grep -Fq "B99_UID_HOST_ECHO 1.0.1.1 WBD_B99_$uid" "$out/uid-host.log" || status=FAIL
  if [[ "$scene" == route-group ]];then grep -Fq B99_SECOND_SELECTED_UID_ECHO_PASS "$out/$scene.log" || status=FAIL
  else grep -Fq "B99_UID_HOST_ECHO 192.0.2.1 WBD_B99_$bypass" "$out/uid-host.log" || status=FAIL;fi
 fi
 if [[ "$scene" == system-cn ]] && ! grep -Fq "B90_FIXTURE cn.wbd-b91.test" "$out/dns-host.log";then status=FAIL;fi
 if [[ "$scene" == system-physical-tc ]];then
  for wire in UDP TCP;do if ! grep -Fq "B90_FIXTURE tc.wbd-b90.test $wire" "$out/dns-host.log";then status=FAIL;fi;done
 fi
 if [[ "$scene" == fec-fixed || "$scene" == fec-auto ]] && ! grep -Fq "B97_FEC_SOURCE_PARITY_PASS $scene" "$out/$scene.log";then status=FAIL;fi
 if [[ "$scene" == route-* && "$status" != PASS ]];then
  # Read-only guest diagnostics; never disable netd/BPF/SELinux or change App permissions.
  for cmd in "iptables -w 2 -nvxL OUTPUT" "iptables -w 2 -t mangle -nvxL OUTPUT" "ip -4 rule show" "ip -4 route get 192.0.2.1 uid $uid" "dumpsys netpolicy";do
   printf "READBACK %s\n" "$cmd"
   "$adb" shell "su -c '$cmd'" || true
  done >"$out/$scene-egress.txt" 2>&1
  "$adb" shell logcat -d -b all | grep -E "B95_FOREGROUND_UID|avc: denied|netd.*(deny|reject|blocked)|TrafficController" | tail -60 >"$out/$scene-egress-logcat.txt" || true
  cat "$out/uid-host.log"
  sed -n '1,90p' "$out/$scene-egress.txt"
 fi
 if [[ "$scene" == system-* && "$status" != PASS ]];then
  "$adb" shell "su -c 'ip -4 rule help'" >"$out/$scene-ip-rule-help.txt" 2>&1 || true
  cat "$out/$scene-ip-rule-help.txt"
 fi
 if ! clean_kernel "$scene";then clean=0;status=FAIL;echo "B91_KERNEL_CLEANUP_NOT_PROVEN $scene";fi
 record "$scene" "$status"
 cat "$out/$scene.log"
done
if [[ -s "$out/uid-host.log" ]];then cat "$out/uid-host.log";fi
if [[ -s "$out/dns-host.log" ]];then cat "$out/dns-host.log";fi
export B91_CLEAN="$clean" B92_SHARD="$shard"
python3 - "$out" <<'PY'
import json, os, pathlib, sys
p=pathlib.Path(sys.argv[1])
rows=dict(line.split("\t") for line in (p/"results.tsv").read_text().splitlines())
native={}
uid_stages={}
dns_stages={}
mtu_stages={}
wire_stages={}
recovery_stages={}
dns6_relay={}
mixed_mss={}
daily={}
cycles={}
active_scope={}
for scene in rows:
 f=p/(scene+".log")
 if not f.exists():continue
 t=f.read_text(errors="replace")
 if scene.startswith("combined-"):
  active_scope[scene]={"hostname_bootstrap":"PASS" if "B107_SERVER_HOSTNAME_BOOTSTRAP_PASS " in t else "NOT_PROVEN","actual_probes":[x for x in t.splitlines() if x.startswith("B106_ACTIVE_COMBINED_PROBE_PASS ")],"remote_tcp_udp":"NOT_PROVEN"}
 if scene=="network-normal":
  active_scope[scene]={"selected_network_lost":"PASS" if "B106_ACTIVE_SELECTED_NETWORK_LOST_PASS " in t else "NOT_PROVEN","native_scope_invalid":"PASS" if "B105_NATIVE_PHYSICAL_SCOPE_INVALID_PASS" in t else "NOT_PROVEN","explicit_reconnect":"PASS" if "B105_MANUAL_NEW_NETWORK_RECONNECT_PASS" in t else "NOT_PROVEN","production_rootservice_auto_reconnect":"NOT_PROVEN"}
 if scene.startswith("cycle-"):
  cycles[scene]={"connections":t.count("B103_CYCLE_CONNECT "),"stop_and_physical":t.count("B103_CYCLE_STOP_AND_PHYSICAL_PASS "),"steady_dns_activity_switch":"PASS" if "B103_STEADY_DNS_AND_ACTIVITY_SWITCH_PASS " in t else "NOT_PROVEN","production_rootservice_auto_reconnect":"NOT_PROVEN"}
 if scene.startswith("daily-"):
  daily[scene]={"physical_dns_udp":"PASS" if "B102_NATIVE_DNS_UDP_ROUNDTRIP_PASS " in t else "NOT_RUN_OR_NOT_PROVEN","physical_dns_tcp":"PASS" if "B102_APP_DNS_TCP_ROUNDTRIP_PASS " in t else "NOT_RUN_OR_NOT_PROVEN","tunnel_dns_tx":"PASS" if "B102_NATIVE_DNS_TUNNEL_TX_PASS " in t else "NOT_RUN_OR_NOT_PROVEN","direct_tcp_udp_trials":t.count("B102_DIRECT_TCP_UDP_PASS "),"remote_m4":"NOT_PROVEN"}
 if scene.startswith("crash-"):
  recovery_stages[scene]={"exit86":"PASS" if "B100_CRASH_PROCESS_EXIT "+scene+" 86" in t else "NOT_PROVEN","durable_readback":"PASS" if "B101_CRASH_DURABLE_READBACK_PASS" in t else "NOT_PROVEN","recover":"PASS" if "B100_RECOVER_PASS " in t else "NOT_PROVEN","idempotent":"PASS" if "B100_CRASH_IDEMPOTENT_RESTORE_PASS " in t else "NOT_PROVEN"}
 if scene=="dns6-relay":
  dns6_relay={"socket_passes":t.count("B100_DNS6_RELAY_SOCKET_PASS "),"stop":"PASS" if "B100_DNS6_RELAY_STOP_PASS" in t else "NOT_PROVEN","nat_capture":"ENV_BLOCKED_B99"}
 if scene.startswith("mixed-"):
  mixed_mss[scene]={"readback":"PASS" if "B98_MTU_OS_READBACK_PASS " in t else "NOT_PROVEN","wire":"PASS" if "B100_MIXED_MSS_PASS " in t else "NOT_PROVEN","witness":[x for x in t.splitlines() if x.startswith("B99_RAW_WIRE_WITNESS ")],"stop":"PASS" if "B91_NATIVE_STOP_PASS " in t else "NOT_PROVEN"}
 if scene.startswith("wire-"):
  wire_stages[scene]={"wire":"PASS" if "B99_WIRE_SCENE_PASS " in t else "NOT_PROVEN","witness":[x for x in t.splitlines() if x.startswith("B99_RAW_WIRE_WITNESS ")],"native_stop":"PASS" if "B91_NATIVE_STOP_PASS " in t else "NOT_PROVEN"}
 if scene.startswith("mtu-"):
  mtu_stages[scene]={"os_readback":"PASS" if "B98_MTU_OS_READBACK_PASS " in t else "NOT_PROVEN","boundary_tx_checks":t.count("B98_MTU_BOUNDARY_TX_PASS "),"df_oversize":"PASS" if "B98_MTU_DF_OVERSIZE_REJECT_PASS " in t else "NOT_PROVEN","native_stop":"PASS" if "B91_NATIVE_STOP_PASS " in t else "NOT_PROVEN","scope":"ordinary IPv4 UDP and native counter evidence; no independent raw wire capture"}
 if scene.startswith("route-"):
  uid_stages[scene]={"java_echo_passes":t.count("B94_UID_SOCKET_ROUNDTRIP_PASS echo\n"),"inet4_echo_passes":t.count("B94_UID_SOCKET_ROUNDTRIP_PASS echo4\n"),"physical_java_passes":t.count("B94_UID_PHYSICAL_BASELINE_PASS baseline\n"),"physical_inet4_passes":t.count("B94_UID_PHYSICAL_BASELINE_PASS baseline4\n"),"trials_per_socket":2}
 if scene.startswith("system-"):
  dns_stages[scene]={"owner":"PASS" if "B95_SYSTEM_DNS_OWNER_READY "+scene in t else "NOT_PROVEN","query":"PASS" if "B91_SYSTEM_DNS_QUERY_PASS "+scene in t else "NOT_PROVEN","stop":"PASS" if "B91_SYSTEM_DNS_STOP_PASS "+scene in t else "NOT_PROVEN"}
for scene in ("normal","fec-fixed","fec-auto","game2","game2-fixed","game4","game4-fixed"):
 f=p/(scene+".log")
 if not f.exists():continue
 t=f.read_text(errors="replace")
 native[scene]={"cold_association":"PASS" if "B91_ORIGINAL_ASSOCIATIONS_ESTABLISHED "+scene in t else "NOT_PROVEN","authenticated_native_started":"PASS" if "B91_NATIVE_M4_STARTED "+scene in t else "NOT_PROVEN","native_stop":"PASS" if "B91_NATIVE_STOP_PASS "+scene in t else "NOT_PROVEN","ordinary_app_tx":"PASS" if "B91_NATIVE_APP_TX_PASS "+scene in t else "NOT_PROVEN","java_tx":"PASS" if "B95_NATIVE_SOCKET_TX_PASS "+scene+" 1\n" in t else "NOT_PROVEN","inet4_tx":"PASS" if "B95_NATIVE_SOCKET_TX_PASS "+scene+" send4\n" in t else "NOT_PROVEN","fec_source_parity":"PASS" if "B97_FEC_SOURCE_PARITY_PASS "+scene+" " in t else "NOT_PROVEN"}
r={"source":os.environ["GITHUB_SHA"],"shard":os.environ["B92_SHARD"],"native_stages":native,"uid_stages":uid_stages,"dns_stages":dns_stages,"mtu_stages":mtu_stages,"wire_stages":wire_stages,"mixed_mss":mixed_mss,"daily":daily,"cycles":cycles,"active_scope":active_scope,"recovery_stages":recovery_stages,"dns6_relay":dns6_relay,"scope":"Android real kernel/Resolver and real original Go TLS+native M4; cold association frames exchanged in-process, no remote WBD M4 peer", "scenes":rows,"kernel_cleanup":"PASS" if os.environ["B91_CLEAN"]=="1" else "NOT_PROVEN","physical_network_lifecycle":"NOT_RUN","peer_raw_syn_tls_m4":"NOT_PROVEN","arm64_physical":"NOT_RUN"}
(p/"receipt.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r))
PY
test "$failed" = 0
