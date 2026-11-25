#!/usr/bin/env bash
# Sourced ONLY by the disposable hosted D2 job. No changes in product code.
# Exact selected IPv4/TCP:443 frames are redirected at tc, then passed
# unchanged to the real original server across an ADB reverse byte stream.
b108_root(){ adb shell "su -c '$*'"; }
b108_cleanup(){
 set +e
 if [[ "${WBD_B110_SCENE:-}" == normal-reconnect ]];then
  adb shell svc wifi enable >/dev/null 2>&1
 fi
 if [[ -n "${b110_dns_pid:-}" ]];then sudo -n kill "$b110_dns_pid" 2>/dev/null || true;wait "$b110_dns_pid" 2>/dev/null || true;fi
 if [[ "${b108_guest_filter:-0}" == 1 ]];then
  b108_root tc filter del dev "$b108_iface" egress pref 49152 protocol ip
 fi
 if [[ "${b108_guest_qdisc:-0}" == 1 ]];then b108_root tc qdisc del dev "$b108_iface" clsact;fi
 if [[ "${b108_guest_link:-0}" == 1 ]];then b108_root ip link del wbdrg0;fi
 b108_root pkill -TERM -x b108-wire-relay >/dev/null 2>&1 || true
 adb reverse --remove tcp:18443 >/dev/null 2>&1 || true
 if [[ -n "${b108_adb_pid:-}" ]];then kill "$b108_adb_pid" 2>/dev/null || true;wait "$b108_adb_pid" 2>/dev/null || true;fi
 if [[ -n "${b108_host_pid:-}" ]];then sudo -n kill "$b108_host_pid" 2>/dev/null || true;wait "$b108_host_pid" 2>/dev/null || true;fi
 if [[ "${b108_host_link:-0}" == 1 ]];then sudo -n ip link del wbdrh0;fi
 if [[ -n "${b108_echo_pid:-}" ]];then kill "$b108_echo_pid" 2>/dev/null || true;wait "$b108_echo_pid" 2>/dev/null || true;fi
 b108_root rm -f /data/local/tmp/wbd-x86-ci/b108-wire-relay /data/local/tmp/b108-wire-relay >/dev/null 2>&1 || true
}
b108_setup(){
 adb shell logcat -c
 adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step specialty_scope >/dev/null
 sleep 1
 local scope
 scope="$(adb shell logcat -d -s WBD_X86_CI_ORIGINAL:I '*:S' | tr -d '\r' | sed -n 's/.*B90_SCOPE //p' | tail -1)"
 read -r b108_handle b108_iface b108_index b108_mtu b108_ip extra <<<"$scope"
 [[ "$b108_iface" =~ ^(wlan0|eth0)$ && "$b108_ip" =~ ^10\.0\.2\.[0-9]+$ && "$b108_ip" != 10.0.2.2 && -z "$extra" ]]
 b108_root ip link show dev "$b108_iface"
 local mac
 mac="$(b108_root cat "/sys/class/net/$b108_iface/address" | tr -d '\r')"
 [[ "$mac" =~ ^([0-9a-f]{2}:){5}[0-9a-f]{2}$ ]]
 # Add exact local-only point-to-point path, never change default routing.
 sudo -n ip link add wbdrh0 type veth peer name wbdrh1
 b108_host_link=1
 sudo -n ip link set wbdrh0 address 02:00:00:00:08:01
 sudo -n ip link set wbdrh1 address 02:00:00:00:08:02
 sudo -n ip link set wbdrh0 up
 sudo -n ip link set wbdrh1 up
 sudo -n ip addr add 10.0.2.2/32 dev wbdrh0
 sudo -n ip route add "$b108_ip/32" dev wbdrh0 src 10.0.2.2
 sudo -n ip neigh add "$b108_ip" lladdr 02:00:00:00:08:02 nud permanent dev wbdrh0
 b108_root ip link add wbdrg0 type veth peer name wbdrg1
 b108_guest_link=1
 b108_root ip link set wbdrg0 address "$mac"
 b108_root ip link set wbdrg1 address 02:00:00:00:08:03
 b108_root ip link set wbdrg0 up
 b108_root ip link set wbdrg1 up
 b108_root ip link set wbdrg1 promisc on
 # No removal of netd's existing qdisc or filters. The filter is scoped
 # to the disposable runner's exact IP pair and original peer port.
 if ! b108_root tc qdisc show dev "$b108_iface" | grep -Fq clsact;then
  b108_root tc qdisc add dev "$b108_iface" clsact
  b108_guest_qdisc=1
 fi
 b108_root tc qdisc add dev wbdrg0 clsact
 b108_root tc filter add dev wbdrg0 ingress protocol ip pref 49152 u32 match ip src 10.0.2.2/32 match ip dst "$b108_ip/32" match ip protocol 6 0xff match ip sport 443 0xffff action mirred ingress redirect dev "$b108_iface"
 b108_root tc filter add dev "$b108_iface" egress protocol ip pref 49152 u32 match ip src "$b108_ip/32" match ip dst 10.0.2.2/32 match ip protocol 6 0xff match ip dport 443 0xffff action mirred egress redirect dev wbdrg0
 b108_guest_filter=1
 # Relay binaries are same-source host/Android, outside signed APK.
 chmod 700 "$n/b108-wire-relay-linux-amd64"
 sudo -n "$PWD/$n/b108-wire-relay-linux-amd64" host wbdrh1 "$b108_ip" 10.0.2.2 02:00:00:00:08:01 >"$out/b108-host-relay.log" 2>&1 &
 b108_host_pid=$!
 for _ in $(seq 1 30);do grep -Fq B108_RELAY_LISTENING "$out/b108-host-relay.log" && break;sleep .2;done
 grep -Fq B108_RELAY_LISTENING "$out/b108-host-relay.log"
 adb reverse tcp:18443 tcp:18443
 adb push "$n/b108-wire-relay-android-amd64" /data/local/tmp/b108-wire-relay >/dev/null
 b108_root cp /data/local/tmp/b108-wire-relay /data/local/tmp/wbd-x86-ci/b108-wire-relay
 b108_root chmod 700 /data/local/tmp/wbd-x86-ci/b108-wire-relay
 # Do not use the short adb() wrapper for this long-running helper.
 "$ANDROID_HOME/platform-tools/adb" shell "su -c '/data/local/tmp/wbd-x86-ci/b108-wire-relay guest wbdrg1 $b108_ip 10.0.2.2 $mac'" >"$out/b108-guest-relay.log" 2>&1 &
 b108_adb_pid=$!
 for _ in $(seq 1 30);do grep -Fq B108_RELAY_CONNECTED "$out/b108-guest-relay.log" && break;sleep .2;done
 grep -Fq B108_RELAY_CONNECTED "$out/b108-guest-relay.log"
 grep -Fq B108_RELAY_CONNECTED "$out/b108-host-relay.log"
 raw_iface=wbdrh0;raw_ip=10.0.2.2
 b108_root tc filter show dev "$b108_iface" egress >"$out/b108-guest-egress.txt"
 b108_root tc filter show dev wbdrg0 ingress >"$out/b108-guest-ingress.txt"
 grep -Fq 49152 "$out/b108-guest-egress.txt"
 grep -Fq 49152 "$out/b108-guest-ingress.txt"
 printf 'PASS\n' >"$out/b108-carrier-admission.txt"
 echo B108_CARRIER_KERNEL_ADMISSION_PASS
}
b108_traffic(){
 # Actual server TUN IP only, no direct physical listener.
 if [[ -z "${b108_echo_pid:-}" ]];then
  python3 -u android/root-app/ci/traffic-fixture/server.py --bind 10.66.0.1 --port 18080 >"$out/b108-echo.log" 2>&1 &
  b108_echo_pid=$!
  for _ in $(seq 1 30);do grep -Fq "WBD test echo TCP+UDP" "$out/b108-echo.log" && break;sleep .2;done
  grep -Fq "WBD test echo TCP+UDP" "$out/b108-echo.log"
 fi
 # Allow the real application transfer to complete on the CI-only carrier,
 # without changing ordinary socket timeouts or native product policy.
 local rc=0
 timeout --signal=TERM --kill-after=3s 85s "$ANDROID_HOME/platform-tools/adb" shell am instrument -w -e uid_probe daily-tunnel -e host 10.66.0.1 org.wbdnext.testtraffic/.TrafficInstrumentation >"$out/b108-traffic.txt" 2>&1 || rc=$?
 cat "$out/b108-traffic.txt"
 [[ "$rc" == 0 ]]
 grep -Fq "tcp_ok=8 udp_ok=8 samples=8" "$out/b108-traffic.txt"
 grep -Fq "echo_bytes_each_direction=1048576" "$out/b108-traffic.txt"
 grep -Fq "INSTRUMENTATION_CODE: -1" "$out/b108-traffic.txt"
 for side in host guest;do
  grep -Fq "B108_RELAY_FIRST_TX $side" "$out/b108-$side-relay.log"
  grep -Fq "B108_RELAY_FIRST_RX $side" "$out/b108-$side-relay.log"
 done
 echo B108_REAL_ANDROID_REMOTE_TCP_UDP_PASS
}

b110_dns(){
 # Only the original server TUN address has a DNS listener, never host
 # loopback or a public resolver. Ordinary App destination is the same
 # non-CN test IP used by B102; native tunnel DNS rewrites it.
 sudo -n python3 -u android/root-app/ci/b90-dns-fixture.py --bind 10.66.0.1 >"$out/b110-dns-host.log" 2>&1 &
 b110_dns_pid=$!
 for _ in $(seq 1 30);do grep -Fq B90_DNS_FIXTURE_READY "$out/b110-dns-host.log" && break;sleep .2;done
 grep -Fq B90_DNS_FIXTURE_READY "$out/b110-dns-host.log"
 for transport in udp tcp;do
  local dest=192.0.2.53
  # Default TCP53 is transparent, not rewritten. Only explicit App
  # TCP DNS interception can redirect an arbitrary destination.
  if [[ "$transport" == tcp && "${WBD_B110_SCENE:-}" == normal-dns ]];then dest=10.66.0.1;fi
  adb shell am instrument -w -e dns_probe daily4 -e dns_name system.wbd-b91.test -e dns_transport "$transport" -e dns_host "$dest" org.wbdnext.testtraffic/.TrafficInstrumentation >"$out/b110-dns-$transport.txt"
  cat "$out/b110-dns-$transport.txt"
  grep -Fq "daily_dns=$transport" "$out/b110-dns-$transport.txt"
  grep -Fq "INSTRUMENTATION_CODE: -1" "$out/b110-dns-$transport.txt"
  grep -Fq "B90_FIXTURE system.wbd-b91.test $(echo "$transport" | tr a-z A-Z)" "$out/b110-dns-host.log"
 done
 printf 'PASS\n' >"$out/b110-tunnel-dns-pass.txt"
 echo B110_REAL_TUNNEL_DNS_UDP_TCP_PASS
}
b110_reconnect(){
 [[ "$b108_iface" == wlan0 ]] || { echo B110_RECONNECT_ENV_BLOCKED_NOT_WIFI;return 1; }
 cp "$out/b108-traffic.txt" "$out/b110-first-traffic.txt"
 # Real production NetworkCallback must stop the first owner. No CI STOP
 # or START is sent before the second business check.
 adb shell svc wifi disable
 for _ in $(seq 1 50);do
  adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' >"$out/b110-first-stop.txt"
  if grep -Fq ORIGINAL_GO_COLD_RESELECT_STOP_CONFIRMED "$out/b110-first-stop.txt" &&
     grep -Fq OWNER_CLEANUP_FINISHED "$out/b110-first-stop.txt";then break;fi
  sleep .5
 done
 for marker in STOP_REQUESTED ORIGINAL_GO_COLD_RESELECT_STOP_CONFIRMED OWNER_CLEANUP_FINISHED;do
  grep -Fq "$marker" "$out/b110-first-stop.txt" || { echo "B110_AUTO_STOP_NOT_PROVEN $marker";return 1; }
 done
 b108_root test ! -e /sys/class/net/wbdv40
 adb shell svc wifi enable
 for _ in $(seq 1 70);do
  adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' >"$out/b110-reconnect-enums.txt"
  if [[ "$(grep -c NATIVE_M4_AND_UID_READY "$out/b110-reconnect-enums.txt" || true)" -ge 2 ]];then break;fi
  sleep .5
 done
 [[ "$(grep -c NATIVE_M4_AND_UID_READY "$out/b110-reconnect-enums.txt" || true)" -ge 2 ]] || { echo B110_SECOND_READY_NOT_PROVEN;return 1; }
 [[ "$(grep -c ROOT_PROCESS_LAUNCHED "$out/b110-reconnect-enums.txt" || true)" -ge 2 ]]
 [[ "$(grep -c AUTHENTICATED_LEASE_OS_READBACK "$out/b110-reconnect-enums.txt" || true)" -ge 2 ]]
 # Read real new Network after the service's independent restart.
 adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step specialty_scope >/dev/null
 sleep 1
 local fresh new_handle new_iface new_index new_mtu new_ip extra
 fresh="$(adb shell logcat -d -s WBD_X86_CI_ORIGINAL:I '*:S' | tr -d '\r' | sed -n 's/.*B90_SCOPE //p' | tail -1)"
 read -r new_handle new_iface new_index new_mtu new_ip extra <<<"$fresh"
 [[ "$new_handle" =~ ^[0-9]+$ && "$new_handle" != "$b108_handle" && "$new_iface" == "$b108_iface" && "$new_ip" == "$b108_ip" && -z "$extra" ]] || { echo B110_NEW_NETWORK_OR_CARRIER_NOT_PROVEN;return 1; }
 b108_traffic
 cp "$out/b108-traffic.txt" "$out/b110-second-traffic.txt"
 printf 'PASS\n' >"$out/b110-reconnect-pass.txt"
 echo "B110_PRODUCTION_AUTO_RECONNECT_BUSINESS_PASS $b108_handle $new_handle"
}
