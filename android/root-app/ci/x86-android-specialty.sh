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
bypass="$(uid_of org.wbdnext.rootprobe)"
own="$(uid_of org.wbdnext.rootclient)"
manager="$(uid_of me.weishu.kernelsu)"
for id in "$uid" "$bypass" "$own" "$manager";do [[ "$id" =~ ^[0-9]+$ && "$id" -ge 10000 ]];done
guest=/data/local/tmp/wbd-b90-ci
"$adb" shell su -c "mkdir -m 700 $guest"
"$adb" push "$n/wiring-specialty-amd64" /data/local/tmp/wbd-b90-bin.tmp
"$adb" push "$n/libwbd_engine-amd64.so" /data/local/tmp/wbd-b90-lib.tmp
"$adb" push out/android-root-app-cn/wbd-cn-ipv4.txt /data/local/tmp/wbd-b90-cn.tmp
"$adb" shell su -c "mv /data/local/tmp/wbd-b90-bin.tmp $guest/test; mv /data/local/tmp/wbd-b90-lib.tmp $guest/libwbd_engine.so; mv /data/local/tmp/wbd-b90-cn.tmp $guest/cn.txt; chmod 700 $guest/test; chmod 600 $guest/libwbd_engine.so $guest/cn.txt"
"$adb" shell su -c "sha256sum $guest/test $guest/libwbd_engine.so $guest/cn.txt" >"$out/guest-sha.txt"
for f in "$n/wiring-specialty-amd64" "$n/libwbd_engine-amd64.so" out/android-root-app-cn/wbd-cn-ipv4.txt;do grep -Fq "$(sha256sum "$f" | cut -d' ' -f1)" "$out/guest-sha.txt";done
dns_pid=""
cleanup(){ if [[ -n "$dns_pid" ]];then sudo -n kill "$dns_pid" 2>/dev/null || true;wait "$dns_pid" 2>/dev/null || true;fi; }
trap cleanup EXIT
sudo -n timeout 90s python3 -u android/root-app/ci/b90-dns-fixture.py >"$out/dns-host.log" 2>&1 &
dns_pid=$!
for i in $(seq 1 20);do grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log" && break;sleep 0.2;done
dns=NOT_RUN
if grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log";then
  dns=FAIL
  if timeout 30s "$adb" shell su -c "$guest/test dns $scope $uid $bypass $own $manager $guest/cn.txt" >"$out/dns-android.log" 2>&1 &&
    grep -Fq B90_PHYSICAL_DNS_UDP_PASS "$out/dns-android.log" &&
    grep -Fq B90_PHYSICAL_DNS_TC_PASS "$out/dns-android.log" &&
    grep -Fq "B90_FIXTURE udp.wbd-b90.test UDP" "$out/dns-host.log" &&
    grep -Fq "B90_FIXTURE tc.wbd-b90.test UDP" "$out/dns-host.log" &&
    grep -Fq "B90_FIXTURE tc.wbd-b90.test TCP" "$out/dns-host.log";then dns=PASS;fi
else dns=ENV_BLOCKED;fi
cleanup;dns_pid=""
routes=FAIL
if timeout 240s "$adb" shell su -c "$guest/test routes $scope $uid $bypass $own $manager $guest/cn.txt" >"$out/routes-android.log" 2>&1 &&
  grep -Fq B90_ROUTE_SINGLE_UID_PACKET_CN_PASS "$out/routes-android.log" &&
  grep -Fq B90_ROUTE_GROUP_UID_PACKET_CN_PASS "$out/routes-android.log" &&
  grep -Fq B90_ROUTE_ALL_UID_PACKET_CN_PASS "$out/routes-android.log" &&
  grep -Fq B90_TUN_CLOSE_PASS "$out/routes-android.log";then routes=PASS;fi
"$adb" shell su -c "ip -4 rule show; ip -4 route show table 19842; ip link show dev wbdb90" >"$out/final-kernel.txt" 2>&1 || true
"$adb" shell su -c "rm -f $guest/test $guest/libwbd_engine.so $guest/cn.txt; rmdir $guest" || true
cat "$out/dns-android.log" "$out/routes-android.log" 2>/dev/null || true
export B90_DNS="$dns" B90_ROUTES="$routes"
python3 - "$out" <<'PY'
import json, os, pathlib, sys
p=pathlib.Path(sys.argv[1])
r={"source":os.environ["GITHUB_SHA"],"scope":"real Android kernel component test; test /32 not WBD peer lease", "physical_dns_udp_and_same_network_tcp":os.environ["B90_DNS"],"original_single_group_all_uid_route_and_cn_and_stop":os.environ["B90_ROUTES"],"system_resolver_interception":"NOT_RUN","authenticated_go_rust_handoff":"NOT_RUN","physical_network_lifecycle":"NOT_RUN"}
(p/"receipt.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r))
PY
[[ "$dns" == PASS && "$routes" == PASS ]]
