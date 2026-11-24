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
 routes) scenes=(route-single route-group route-all);;
 route-single|route-group|route-all) scenes=("$shard");;
 normal) scenes=(normal fec-fixed fec-auto);;
 game2) scenes=(game2 game2-fixed);;
 game4) scenes=(game4 game4-fixed);;
 dns-physical) scenes=(system-physical);;
 dns-tunnel) scenes=(system-tunnel);;
 dns-cn) scenes=(system-cn);;
 all) scenes=(system-physical system-tunnel system-cn route-single route-group route-all normal fec-fixed fec-auto game2 game2-fixed game4 game4-fixed);;
 *) echo "unknown specialty shard: $shard";exit 2;;
esac
: >"$out/results.tsv"
dns_pid=""
uid_pid=""
cleanup(){
 if [[ -n "$uid_pid" ]];then kill "$uid_pid" 2>/dev/null || true;wait "$uid_pid" 2>/dev/null || true;fi
 if [[ -n "$dns_pid" ]];then sudo -n kill "$dns_pid" 2>/dev/null || true;wait "$dns_pid" 2>/dev/null || true;fi
}
trap cleanup EXIT
# Real local DNS fixture; a failure cannot block independent native tests.
if [[ "$shard" == dns-physical || "$shard" == dns-cn || "$shard" == all ]];then
 sudo -n timeout 190s python3 -u android/root-app/ci/b90-dns-fixture.py >"$out/dns-host.log" 2>&1 &
 dns_pid=$!
 for i in $(seq 1 20);do grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log" && break;sleep 0.2;done
fi
if [[ "$shard" == route-* || "$shard" == routes || "$shard" == all ]];then
 timeout 240s python3 -u android/root-app/ci/b94-uid-echo.py >"$out/uid-host.log" 2>&1 &
 uid_pid=$!
 for i in $(seq 1 20);do grep -Fq B94_UID_FIXTURE_READY "$out/uid-host.log" && break;sleep .2;done
fi
failed=0
record(){ printf '%s\t%s\n' "$1" "$2" >>"$out/results.tsv";echo "B92_RESULT $shard $1 $2";if [[ "$2" != PASS ]];then failed=1;fi; }
invoke(){ timeout "$1" "$adb" shell su -c "$guest/wiring-specialty $2 $scope $uid $bypass $own $manager $guest/cn.txt"; }
clean_kernel(){
 local name="$1" rc=0
 {
 for cmd in 'ip -4 rule show' 'ip -4 route show table all' 'ip -o link show' 'iptables -w 2 -t nat -S OUTPUT';do
  printf 'READBACK %s\n' "$cmd"
  "$adb" shell "su -c '$cmd'" || rc=1
 done
 } >"$out/$name-kernel.txt" 2>&1
 if [[ "$rc" != 0 ]];then cat "$out/$name-kernel.txt";return 1;fi
 if grep -Eq '(^|[[:space:]])9099:|lookup (19842|19843|19845)( |$)|table (19842|19843|19845)( |$)|wbdb90:|wbdb91dns:|wbdb91m4:|wbd_dns0:|wbd-next-root-(app-tcp-dns|system-dns)-v1' "$out/$name-kernel.txt";then
  grep -E 'lookup (19842|19843|19845)( |$)|table (19842|19843|19845)( |$)|wbdb90:|wbdb91dns:|wbdb91m4:|wbd_dns0:|wbd-next-root-(app-tcp-dns|system-dns)-v1' "$out/$name-kernel.txt" | sed -n '1,25p'
  return 1
 fi
 return 0
}
# B91 physical UDP/TC TCP already passed; no standalone repeat.
clean=1
if ! clean_kernel baseline;then clean=0;fi
for scene in "${scenes[@]}";do
 if [[ "$clean" != 1 ]];then record "$scene" NOT_RUN;continue;fi
 if [[ "$scene" == system-physical || "$scene" == system-cn ]] && ! grep -Fq B90_DNS_FIXTURE_READY "$out/dns-host.log";then record "$scene" ENV_BLOCKED;continue;fi
 limit=85s
 if [[ "$scene" == route-* ]];then limit=180s;fi
 status=FAIL
 if invoke "$limit" "$scene" >"$out/$scene.log" 2>&1;then
  case "$scene" in
   system-*) if grep -Fq "B91_SYSTEM_DNS_QUERY_PASS $scene" "$out/$scene.log" && grep -Fq "B91_SYSTEM_DNS_STOP_PASS $scene" "$out/$scene.log";then status=PASS;fi ;;
   route-*) m="$(printf '%s' "$scene" | cut -d- -f2 | tr 'a-z' 'A-Z')"
     if grep -Fq "B90_ROUTE_$m"_"UID_PACKET_CN_PASS" "$out/$scene.log" && grep -Fq "B90_ROUTE_$m"_"STOP_PASS" "$out/$scene.log" && grep -Fq B90_TUN_CLOSE_PASS "$out/$scene.log";then status=PASS;fi ;;
   *) if grep -Fq "B91_NATIVE_M4_STARTED $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_APP_TX_PASS $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_UID_STOP_PASS $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_STOP_PASS $scene" "$out/$scene.log" &&
       grep -Fq "B91_NATIVE_TUN_CLOSE_PASS $scene" "$out/$scene.log";then status=PASS;fi ;;
  esac
 fi
 if [[ "$scene" == system-physical ]] && ! grep -Fq "B90_FIXTURE system.wbd-b91.test" "$out/dns-host.log";then status=FAIL;fi
 if [[ "$scene" == system-cn ]] && ! grep -Fq "B90_FIXTURE cn.wbd-b91.test" "$out/dns-host.log";then status=FAIL;fi
 if [[ "$scene" == route-* && "$status" != PASS ]];then
  # Read-only guest diagnostics; never disable netd/BPF/SELinux or change App permissions.
  for cmd in "iptables -w 2 -nvxL OUTPUT" "iptables -w 2 -t mangle -nvxL OUTPUT" "ip -4 rule show" "ip -4 route get 192.0.2.1 uid $uid" "dumpsys netpolicy";do
   printf "READBACK %s\n" "$cmd"
   "$adb" shell "su -c '$cmd'" || true
  done >"$out/$scene-egress.txt" 2>&1
  "$adb" shell logcat -d -b all | grep -E "avc: denied|netd.*(deny|reject|blocked)|TrafficController" | tail -60 >"$out/$scene-egress-logcat.txt" || true
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
export B91_CLEAN="$clean" B92_SHARD="$shard"
python3 - "$out" <<'PY'
import json, os, pathlib, sys
p=pathlib.Path(sys.argv[1])
rows=dict(line.split("\t") for line in (p/"results.tsv").read_text().splitlines())
native={}
for scene in ("normal","fec-fixed","fec-auto","game2","game2-fixed","game4","game4-fixed"):
 f=p/(scene+".log")
 if not f.exists():continue
 t=f.read_text(errors="replace")
 native[scene]={"cold_association":"PASS" if "B91_ORIGINAL_ASSOCIATIONS_ESTABLISHED "+scene in t else "NOT_PROVEN","authenticated_native_started":"PASS" if "B91_NATIVE_M4_STARTED "+scene in t else "NOT_PROVEN","native_stop":"PASS" if "B91_NATIVE_STOP_PASS "+scene in t else "NOT_PROVEN","ordinary_app_tx":"PASS" if "B91_NATIVE_APP_TX_PASS "+scene in t else "NOT_PROVEN"}
r={"source":os.environ["GITHUB_SHA"],"shard":os.environ["B92_SHARD"],"native_stages":native,"scope":"Android real kernel/Resolver and real original Go TLS+native M4; cold association frames exchanged in-process, no remote WBD M4 peer", "scenes":rows,"kernel_cleanup":"PASS" if os.environ["B91_CLEAN"]=="1" else "NOT_PROVEN","physical_network_lifecycle":"NOT_RUN","peer_raw_syn_tls_m4":"NOT_PROVEN","arm64_physical":"NOT_RUN"}
(p/"receipt.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r))
PY
test "$failed" = 0
