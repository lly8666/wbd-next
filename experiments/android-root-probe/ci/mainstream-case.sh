#!/usr/bin/env bash
# One emulator. Ordinary App packets via KSU TUN (UDP, DNS53, TCP HTTP) and
# separately real netd-selected default-network Socket to 10.0.2.2 host.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
o=out/mainstream
mkdir -p "$o"
test "$(cat out/native/SOURCE)" = "$GITHUB_SHA"
(cd out/native && sha256sum -c SHA256SUMS) >"$o/native-hashes.txt"
test -s out/apk/host-tls.crt && test -s out/apk/host-tls.key
python3 -u experiments/android-root-probe/ci/underlay-echo.py \
 out/apk/host-tls.crt out/apk/host-tls.key >"$o/host-echo.log" 2>&1 &
hostpid=$!
clean(){
  kill "$hostpid" 2>/dev/null || true
  wait "$hostpid" 2>/dev/null || true
  adb shell rm -f /data/local/tmp/wbd-app-native >/dev/null 2>&1 || true
}
trap clean EXIT
ready=0
for i in $(seq 1 30);do
  if python3 - <<'PY'
import socket
try:
 with socket.create_connection(("127.0.0.1",18317),timeout=1.0) as s:
  s.sendall(b"wbd-host-health\n")
  data=s.recv(100)
  assert data==b"wbd-underlay-ok-health\n",repr(data)
except Exception:raise SystemExit(1)
PY
  then
    if python3 - <<'PY'
    import socket,ssl
    ctx=ssl.create_default_context(cafile="out/apk/host-tls.crt")
    ctx.minimum_version=ssl.TLSVersion.TLSv1_2
    try:
     with socket.create_connection(("127.0.0.1",18318),timeout=1.5) as sock:
      with ctx.wrap_socket(sock,server_hostname="wbd-ci-host.test") as tls:
       tls.sendall(b"wbd-tls-health\n")
       value=tls.recv(100)
       assert value==b"wbd-tls-ok-health\n",repr(value)
    except Exception:
     raise SystemExit(1)
    PY
    then ready=1;break;fi
  fi
  sleep 0.3
done
if [[ "$ready" != 1 ]];then
 echo "ENV_BLOCKED: host underlay echo not ready"
 cat "$o/host-echo.log"
 exit 2
fi
adb shell getprop ro.build.version.sdk >"$o/api.txt"
adb shell getenforce >"$o/selinux.txt"
adb shell pm path org.wbdnext.rootprobe >"$o/app-package.txt"
adb shell su -c 'ip -4 rule show' >"$o/rule-before.txt"
adb shell su -c 'ip -4 route show table all' >"$o/route-before.txt"
adb shell dumpsys connectivity >"$o/connectivity-before.txt" 2>&1 || true
adb push out/native/bin/probe-x86_64-linux-android /data/local/tmp/wbd-app-native >"$o/native-stage.txt"
adb shell chmod 0755 /data/local/tmp/wbd-app-native
adb shell run-as org.wbdnext.rootprobe rm -f files/mainstream-result.json
adb shell am start -W -n org.wbdnext.rootprobe/.MainstreamActivity >"$o/app-start.txt"
found=0
for i in $(seq 1 48);do
 if adb shell run-as org.wbdnext.rootprobe cat files/mainstream-result.json >"$o/app-mainstream.json" 2>"$o/read.err";then
  if python3 -m json.tool "$o/app-mainstream.json" >/dev/null 2>&1;then found=1;break;fi
 fi
 sleep 1
done
if [[ "$found" != 1 ]];then
 echo '{"status":"APP_RESULT_MISSING"}' >"$o/app-mainstream.json"
fi
adb logcat -d -s WBD_MAINSTREAM:I >"$o/logcat.txt" 2>&1 || true
adb shell su -c 'ip -4 rule show' >"$o/rule-after.txt"
adb shell su -c 'ip -4 route show table all' >"$o/route-after.txt"
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path("out/mainstream")
read=lambda f:(p/f).read_text(errors="replace").strip()
a=json.loads(read("app-mainstream.json"))
native=a.get("native") or {}
ev=native.get("evidence") or {}
extra=ev.get("mainstream") or {}
dns=extra.get("dns_udp53") or {}
tcp=extra.get("tcp_http") or {}
clean=native.get("cleanup") or {}
net=a.get("netd_underlay") or {}
u=a.get("udp") or {}
d=a.get("dns") or {}
t=a.get("tcp") or {}
errors=[]
def req(v,reason):
 if not v: errors.append(reason)
req(read("api.txt")=="36" and read("selinux.txt")=="Enforcing","Android16/KSU AVD SELinux")
req(a.get("app_uid",0)>=10000 and "untrusted_app" in a.get("app_context","")
    and a.get("target_sdk")==37,"real normal targetSdk37 App UID/context")
req(a.get("root_ready") and a.get("su_exit")==0 and native.get("root_uid")==0,"real app KSU su UID0")
req(a.get("status")=="APP_DNS_TLS_MAINSTREAM_PASS","App end-to-end mainstream result")
req(u.get("status")=="PASS" and u.get("receive_bytes",0)>0,"App real UDP roundtrip")
req(d.get("status")=="PASS" and d.get("answer")=="198.18.254.2" and
    dns.get("status")=="SUPPORTED_IN_SCOPE","App direct DNS UDP53 real TUN")
req(t.get("status")=="PASS" and t.get("http_status")==200 and
    tcp.get("real_app_tcp_syn_seen") and tcp.get("real_app_http_get_seen") and
    tcp.get("normal_app_acked_tun_response") and tcp.get("status")=="SUPPORTED_IN_SCOPE",
    "App real TCP handshake GET/HTTP TUN")
req(net.get("status")=="PASS" and net.get("socket_bound_to_active_network") and
    net.get("interface") and net.get("routes",0)>=1 and net.get("internet_capability") is True,
    "Android netd active Network underlay Socket to emulator host")
sdns=a.get("system_dns") or {}
tls=a.get("tls_underlay") or {}
req(sdns.get("status")=="PASS" and sdns.get("using_android_network_resolver") and
    sdns.get("answer_count",0)>0 and sdns.get("has_ipv4"),
    "Android Network.getAllByName real resolver failed")
req(tls.get("status")=="PASS" and tls.get("server_identity_verified") and
    tls.get("hostname_verified") and tls.get("network_bound_socket") and
    tls.get("protocol") in ("TLSv1.2","TLSv1.3") and
    tls.get("reply")=="wbd-tls-ok-"+str(a.get("token","")),
    "authenticated Android SSLSocket over netd default network failed")
req("HOST_TLS_ACCEPT "+str(a.get("token","missing")) in read("host-echo.log"),
    "host TLS server never accepted ordinary App nonce")
req(tls.get("certificate_sha256")==json.loads(Path("out/apk/manifest.json").read_text()).get("tls_fixture_public_cert_sha256"),
    "actual pinned TLS public cert hash mismatch")
req("HOST_ACCEPT "+str(a.get("token","missing")) in read("host-echo.log"),
    "host TCP server never saw actual App token via underlay")
req((extra.get("underlay_marker") or {}).get("real_app_underlay_completed_before_rule_release") is True and
    a.get("underlay_completion_marker_bytes",0)>0,
    "host netd socket not proven before UID route released")
req(clean.get("ok") and clean.get("rules_equal") and clean.get("routes_equal") and
    clean.get("tun_gone"),"root-owned network cleanup")
req(read("rule-before.txt")==read("rule-after.txt"),"system rule snapshot changed")
req(read("route-before.txt")==read("route-after.txt"),"system routes snapshot changed")
req(json.loads(Path("out/native/manifest.json").read_text()).get("source")==os.environ["GITHUB_SHA"],
    "source/hash mismatch")
summary={"schema":"android-ksu-mainstream-traffic/v1","source":os.environ["GITHUB_SHA"],
 "status":"MAINSTREAM_DNS_TLS_PASS" if not errors else "FAIL",
 "app_uid":a.get("app_uid"),"app_selinux":a.get("app_context"),
 "app_su_exit":a.get("su_exit"),"udp":u,"dns":dns,"tcp":tcp,
 "netd_underlay":net,"system_dns":sdns,"tls_underlay":tls,"cleanup":clean,"errors":errors,
 "scope":"real App UDP/DNS UDP53/TCP HTTP via synthetic TUN; real default Network bound Socket to emulator host. Not system resolver/physical modem/tether/NAT"}
(p/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
print(json.dumps(summary,indent=2,sort_keys=True))
if errors:raise SystemExit("mainstream real App traffic gate failed; preserve app JSON and host logs")
PY
