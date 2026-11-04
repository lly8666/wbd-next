#!/usr/bin/env bash
# PLAN028 original Go TLS: two independent accounts, one server port,
# one real Rust kernel TUN reader, A then A+B then B, both real native Stop.
set -euo pipefail
ROOT="$(realpath "$1")"
SIBLING_SWITCH="${WBD_PLAN028_SIBLING_PHYSICAL_SWITCH:-0}"
if [[ "$SIBLING_SWITCH" != 0 && "$SIBLING_SWITCH" != 1 ]];then
  echo 'invalid sibling physical switch selector' >&2;exit 2
fi
test -x "$ROOT/wbd-v4-client" && test -x "$ROOT/wbd-v4-server"
test -s "$ROOT/libwbd_engine.so" && test -c /dev/net/tun
: "$GITHUB_RUN_ID" "$GITHUB_WORKSPACE" "$RUNNER_TEMP"
TAG="$(printf %s "$GITHUB_RUN_ID" | tail -c 7)"
NSS="wbdsv$TAG"; NSA="wbdca$TAG"; NSB="wbdcb$TAG"; NSR="wbdcr$TAG"; NSD="wbdcd$TAG"
BR="wbdb$TAG"; RS="wbdrs$TAG"; RA="wbdra$TAG"; RB="wbdrb$TAG"; RR="wbdrp$TAG"; RD="wbdrd$TAG"
TMP="$RUNNER_TEMP/wbd-plan028-$GITHUB_RUN_ID"
ART="$GITHUB_WORKSPACE/fixed-kernel-result"
mkdir -m 0700 -p "$TMP" "$ART"
S_PID=''; A_PID=''; B_PID=''; R_PID=''; D_PID=''; ECHO_PID=''
cleanup(){
  local result=$?
  set +e
  if [[ "$result" != 0 ]];then
    echo "PLAN028_REAL_MULTI_NATIVE_FAIL_EXIT result=$result" >&2
    for file in server.log A.log B.log R.log D.log echo.log A-only.log A-plus-B.log B-plus-A.log A-three.log B-three.log D-three.log R-handover.log B-survive-R.log D-survive-R.log B-only.log;do
      if [[ -f "$TMP/$file" ]];then
        echo "=== $file failure scope ===" >&2
        tail -45 "$TMP/$file" | sed -E 's/(password|secret|route-key|credential)[=:][^ ]+/\\1=[REDACTED]/Ig' >&2
      fi
    done
  fi
  for p in "$S_PID" "$A_PID" "$B_PID" "$R_PID" "$D_PID" "$ECHO_PID";do
    if [[ -n "$p" ]];then sudo -n kill -TERM "$p" 2>/dev/null || true;fi
  done
  for dev in "$RS" "$RA" "$RB" "$RR" "$RD" "$BR";do sudo -n ip link del "$dev" 2>/dev/null || true;done
  for ns in "$NSS" "$NSA" "$NSB" "$NSR" "$NSD";do sudo -n ip netns del "$ns" 2>/dev/null || true;done
  rm -rf "$TMP"
}
trap cleanup EXIT
for ns in "$NSS" "$NSA" "$NSB" "$NSR" "$NSD";do
  sudo -n ip netns add "$ns"
  sudo -n ip -n "$ns" link set lo up
done
sudo -n ip link add "$BR" type bridge
sudo -n ip link set "$BR" up
for def in "$RS wbdvs0 $NSS 10.25.0.1/24" \
           "$RA wbdva0 $NSA 10.25.0.2/24" \
           "$RB wbdvb0 $NSB 10.25.0.3/24" \
           "$RR wbdvr0 $NSR 10.25.0.4/24" \
           "$RD wbdvd0 $NSD 10.25.0.5/24"; do
  read -r host peer ns cidr <<<"$def"
  sudo -n ip link add "$host" type veth peer name "$peer"
  sudo -n ip link set "$host" master "$BR"
  sudo -n ip link set "$host" up
  sudo -n ip link set "$peer" netns "$ns"
  sudo -n ip -n "$ns" addr add "$cidr" dev "$peer"
  sudo -n ip -n "$ns" link set "$peer" up
  sudo -n ip netns exec "$ns" iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
done
openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
  -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
  -subj '/CN=wbd-v4.example.test' -addext 'subjectAltName=DNS:wbd-v4.example.test' \
  >"$TMP/cert-create.log" 2>&1
cat >"$TMP/users.json" <<'JSON'
{"alice":"auth-alice-original-20261103","bob":"auth-bob-original-20261103"}
JSON
chmod 0600 "$TMP/users.json" "$TMP/key.pem"
env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-server" --init-route-key-file "$TMP/route-key.hex"
test "$(stat -c %a "$TMP/route-key.hex")" = 600
sudo -n ip netns exec "$NSS" bash -c "
  echo \$\$ > '$TMP/s.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
    --raw-interface wbdvs0 --local-ip 10.25.0.1 --local-port 443 \
    --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
    --server-name wbd-v4.example.test --route-key-hex-file '$TMP/route-key.hex' \
    --users-file '$TMP/users.json' --lease-pool 10.66.0.128/25 \
    --tls-cert '$TMP/cert.pem' --tls-key '$TMP/key.pem' --mode normal
" >"$TMP/server.log" 2>&1 &
S_PID=$!
for _ in {1..40};do
  if grep -q 'V4_PUBLIC_MULTI_SERVER_READY role=server port=443 cold_association_slots=32 native_owner_slots=16 shared_rust_tun=1' "$TMP/server.log";then break;fi
  sleep .25
done
grep -q 'V4_PUBLIC_MULTI_SERVER_READY role=server port=443 cold_association_slots=32 native_owner_slots=16 shared_rust_tun=1' "$TMP/server.log" || {
  tail -40 "$TMP/server.log" >&2; exit 1;
}
sudo -n ip netns exec "$NSS" python3 -u -c '
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.1",45901));s.settimeout(40)
try:
    for _ in range(150):
        msg,src=s.recvfrom(4096)
        assert msg.startswith(b"WBD_PLAN028_REAL_APP/")
        s.sendto(b"WBD_PLAN028_REAL_ECHO/"+msg,src)
finally:s.close()
' >"$TMP/echo.log" 2>&1 &
ECHO_PID=$!
start_client(){
  local ns="$1" raw="$2" ip="$3" tun="$4" port="$5" user="$6" pass="$7" key="$8" logfile="$9"
  shift 9
  local pidfile="$1"
  sudo -n ip netns exec "$ns" bash -c "
    echo \$\$ > '$pidfile'
    exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-client' \
      --raw-interface '$raw' --local-ip '$ip' --local-port '$port' \
      --peer-ip 10.25.0.1 --peer-port 443 --tun-name '$tun' \
      --server-name wbd-v4.example.test --route-key-hex-file '$TMP/route-key.hex' --tls-ca-pem '$TMP/cert.pem' \
      --username '$user' --password '$pass' \
      --auto-ip --installation-id-file '$key' --mode normal
  " >"$logfile" 2>&1 &
}
get_auto_ip(){
  python3 - "$1" <<'PY'
import pathlib,re,ipaddress,sys
text=pathlib.Path(sys.argv[1]).read_text()
v=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.[0-9]+)/32',text)
assert len(v)==1,v
assert ipaddress.ip_address(v[0]) in ipaddress.ip_network("10.66.0.128/25")
print(v[0])
PY
}
await_client(){
  local file="$1" active="$2"
  for _ in {1..80};do
    if grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$file" &&
       [[ "$(grep -c 'V4_PUBLIC_MULTI_SESSION_READY role=server' "$TMP/server.log" || true)" -ge "$active" ]];then
      return 0
    fi
    sleep .25
  done
  echo 'PLAN028 original Go TLS/Rust per-client not ready' >&2
  tail -50 "$file" "$TMP/server.log" >&2
  return 1
}
echo_udp(){
  local ns="$1" src="$2" label="$3" count="$4" output="$5"
  sudo -n ip netns exec "$ns" env WBD_SRC="$src" WBD_LABEL="$label" WBD_COUNT="$count" WBD_DELAY_S="${WBD_APP_ECHO_DELAY_S:-0}" python3 -u -c '
import os,socket,time
ip=os.environ["WBD_SRC"];label=os.environ["WBD_LABEL"];count=int(os.environ["WBD_COUNT"])
delay=float(os.environ.get("WBD_DELAY_S","0"))
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind((ip,0));s.settimeout(8)
try:
    print("M0_PLAN028_REAL_APP_CLOCK label=%s started_ns=%d"%(label,time.time_ns()),flush=True)
    for n in range(count):
        msg=b"WBD_PLAN028_REAL_APP/"+label.encode()+b"/"+str(n).encode()
        assert s.sendto(msg,("10.66.0.1",45901))==len(msg)
        data,src=s.recvfrom(4096)
        assert data==b"WBD_PLAN028_REAL_ECHO/"+msg and src[0]=="10.66.0.1",(label,n,data,src)
        if delay:time.sleep(delay)
    print("M0_PLAN028_REAL_APP_CLOCK label=%s finished_ns=%d"%(label,time.time_ns()),flush=True)
    print("M0_PLAN028_REAL_APP_ECHO_OK label=%s delivered=%d"%(label,count),flush=True)
finally:s.close()
' >"$output" 2>&1
}
start_client "$NSA" wbdva0 10.25.0.2 wbdva4 41031 alice auth-alice-original-20261103 "$TMP/install-A" "$TMP/A.log" "$TMP/a.pid"
A_PID=$!
await_client "$TMP/A.log" 1
IPA="$(get_auto_ip "$TMP/A.log")"
sudo -n ip -n "$NSA" route replace 10.66.0.1/32 dev wbdva4
echo_udp "$NSA" "$IPA" "A_ONLY" 5 "$TMP/A-only.log"
start_client "$NSB" wbdvb0 10.25.0.3 wbdvb4 42031 bob auth-bob-original-20261103 "$TMP/install-B" "$TMP/B.log" "$TMP/b.pid"
B_PID=$!
await_client "$TMP/B.log" 2
IPB="$(get_auto_ip "$TMP/B.log")"
[[ "$IPA" != "$IPB" ]] || { echo 'two original protected accounts got same /32' >&2;exit 1; }
sudo -n ip -n "$NSB" route replace 10.66.0.1/32 dev wbdvb4
echo_udp "$NSA" "$IPA" "A_PLUS_B_A" 12 "$TMP/A-plus-B.log" &
P_A=$!
echo_udp "$NSB" "$IPB" "A_PLUS_B_B" 12 "$TMP/B-plus-A.log" &
P_B=$!
wait "$P_A"
wait "$P_B"
# THIRD independent installation, but Alice owns two installations while
# Bob owns one. All THREE genuine original-Go TLS /32 owners must coexist
# inside one server and ONE Rust kernel TUN reader; never share an M1 queue.
start_client "$NSD" wbdvd0 10.25.0.5 wbdvd4 44031 alice auth-alice-original-20261103 "$TMP/install-D" "$TMP/D.log" "$TMP/d.pid"
D_PID=$!
await_client "$TMP/D.log" 3
IPD="$(get_auto_ip "$TMP/D.log")"
[[ "$IPD" != "$IPA" && "$IPD" != "$IPB" ]] || {
  echo "same-account separate installation or separate account got a duplicate /32" >&2
  exit 1
}
sudo -n ip -n "$NSD" route replace 10.66.0.1/32 dev wbdvd4
echo_udp "$NSA" "$IPA" "ALICE_OLD_INSTALL_3DEVICES" 6 "$TMP/A-three.log" &
P_A3=$!
echo_udp "$NSB" "$IPB" "BOB_ACCOUNT_3DEVICES" 6 "$TMP/B-three.log" &
P_B3=$!
echo_udp "$NSD" "$IPD" "ALICE_SECOND_INSTALLATION_3DEVICES" 6 "$TMP/D-three.log" &
P_D3=$!
wait "$P_A3"
wait "$P_B3"
wait "$P_D3"
# New standalone PLAN028 physical switch+three-device scenario. It uses
# this SAME original Go/Rust server, independent protected installations,
# true rtnetlink source IPv4 change and one shared Rust TUN owner. It never
# creates a second recovery controller or repeats the older R matrix.
if [[ "$SIBLING_SWITCH" == 1 ]];then
  # Both independent siblings begin continuous real application traffic
  # BEFORE Alice's physical IP changes. Their native TUNs/leases must be
  # stable THROUGH the new TLS+Rust generation and its first data.
  old_a_mtu="$(sudo -n ip -j -n "$NSA" link show wbdva4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  old_b_mtu="$(sudo -n ip -j -n "$NSB" link show wbdvb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  old_d_mtu="$(sudo -n ip -j -n "$NSD" link show wbdvd4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  WBD_APP_ECHO_DELAY_S=.5 echo_udp "$NSB" "$IPB" "BOB_DURING_ALICE_PHYSICAL_SWITCH" 24 "$TMP/B-continuous.log" &
  cont_b=$!
  WBD_APP_ECHO_DELAY_S=.5 echo_udp "$NSD" "$IPD" "ALICE_DEVICE_D_DURING_A_SWITCH" 24 "$TMP/D-continuous.log" &
  cont_d=$!
  for _ in {1..80};do
    if grep -q 'M0_PLAN028_REAL_APP_CLOCK label=BOB_DURING_ALICE_PHYSICAL_SWITCH started_ns=' "$TMP/B-continuous.log" &&
       grep -q 'M0_PLAN028_REAL_APP_CLOCK label=ALICE_DEVICE_D_DURING_A_SWITCH started_ns=' "$TMP/D-continuous.log";then break;fi
    sleep .05
  done
  grep -q 'M0_PLAN028_REAL_APP_CLOCK label=BOB_DURING_ALICE_PHYSICAL_SWITCH started_ns=' "$TMP/B-continuous.log"
  grep -q 'M0_PLAN028_REAL_APP_CLOCK label=ALICE_DEVICE_D_DURING_A_SWITCH started_ns=' "$TMP/D-continuous.log"
  # Real A source-route and physical MTU OS change; B and D underlays
  # are untouched, no fake app notification or router instrumentation.
  changed_ns="$(date +%s%N)"
  sudo -n ip -n "$NSA" addr add 10.25.0.9/24 dev wbdva0
  sudo -n ip -n "$NSA" link set wbdva0 mtu 1280
  sudo -n ip -n "$NSA" route replace 10.25.0.1/32 dev wbdva0 src 10.25.0.9
  sudo -n ip -j -n "$NSA" route get 10.25.0.1 >"$ART/plan028-sibling-new-physical-route.json"
  sudo -n ip -j -n "$NSA" link show wbdva0 >"$ART/plan028-sibling-new-underlay-link.json"
  python3 - "$ART/plan028-sibling-new-physical-route.json" "$ART/plan028-sibling-new-underlay-link.json" <<'PY'
import json,sys
route=json.load(open(sys.argv[1]))[0]
link=json.load(open(sys.argv[2]))[0]
assert route.get("prefsrc",route.get("src"))=="10.25.0.9",route
assert link["mtu"]==1280,link
PY
  ready=0
  for _ in {1..160};do
    if grep -q 'V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client source=rtnetlink_os_readback' "$TMP/A.log" &&
       grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1' "$TMP/A.log" &&
       grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/A.log" &&
       grep -q 'V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=same-lease-new-generation' "$TMP/server.log";then
      ready=1;break
    fi
    sleep .25
  done
  [[ "$ready" == 1 ]] || {
    echo "H1107 three-device native Alice source switch did not recover" >&2
    tail -85 "$TMP/A.log" "$TMP/server.log" >&2;exit 1
  }
  ready_ns="$(date +%s%N)"
  wait "$cont_b"
  wait "$cont_d"
  grep -q 'M0_PLAN028_REAL_APP_ECHO_OK label=BOB_DURING_ALICE_PHYSICAL_SWITCH delivered=24' "$TMP/B-continuous.log"
  grep -q 'M0_PLAN028_REAL_APP_ECHO_OK label=ALICE_DEVICE_D_DURING_A_SWITCH delivered=24' "$TMP/D-continuous.log"
  # New TLS retained Alice's /32; other two independent authenticated
  # /32 leases were not overwritten, nor were their TUN device MTUs.
  echo_udp "$NSA" "$IPA" "ALICE_AFTER_PHYSICAL_SOURCE_RECOVERY" 5 "$TMP/A-recovered.log"
  first_business_ns="$(date +%s%N)"
  new_a_mtu="$(sudo -n ip -j -n "$NSA" link show wbdva4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  new_b_mtu="$(sudo -n ip -j -n "$NSB" link show wbdvb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  new_d_mtu="$(sudo -n ip -j -n "$NSD" link show wbdvd4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  [[ "$new_a_mtu" -ge 576 && "$new_a_mtu" -lt "$old_a_mtu" &&
     "$new_a_mtu" -le 1280 && "$new_b_mtu" == "$old_b_mtu" &&
     "$new_d_mtu" == "$old_d_mtu" ]] || {
    echo "one-device MTU change incorrectly affected independent TUNs" >&2;exit 1
  }
  python3 - "$TMP/A.log" "$TMP/server.log" "$TMP/B-continuous.log" "$TMP/D-continuous.log" \
   "$changed_ns" "$ready_ns" "$first_business_ns" "$old_a_mtu" "$new_a_mtu" "$old_b_mtu" "$old_d_mtu" \
   "$ART/plan028-three-device-source-switch.json" <<'PY'
import json,re,pathlib,sys
a,server,b,d=map(lambda p:pathlib.Path(p).read_text(),sys.argv[1:5])
changed,ready,first=map(int,sys.argv[5:8])
old,new,bmtu,dmtu=map(int,sys.argv[8:12])
for log,label in ((b,"BOB_DURING_ALICE_PHYSICAL_SWITCH"),(d,"ALICE_DEVICE_D_DURING_A_SWITCH")):
    start=re.search(r'M0_PLAN028_REAL_APP_CLOCK label='+label+r' started_ns=(\d+)',log)
    finish=re.search(r'M0_PLAN028_REAL_APP_CLOCK label='+label+r' finished_ns=(\d+)',log)
    assert start and finish,(label,"timestamps missing")
    assert int(start[1])<changed<ready<int(finish[1]),(label,int(start[1]),changed,ready,int(finish[1]))
lease=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.[0-9]+)/32',a)
assert len(lease)==2 and len(set(lease))==1,lease
assert server.count('V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=same-lease-new-generation')==1
assert a.index('V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2')<a.index('V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1')
assert changed<ready<first
summary={"qualification":"TRUE_LINUX_X86_SAME_ACCOUNT_TWO_INSTALLATIONS_BOB_SIBLINGS_CONTINUOUS",
 "one_server_port":443,"distinct_protected_leases":3,"old_source4":"10.25.0.2",
 "new_source4":"10.25.0.9","physical_new_ipv4_mtu":1280,
 "outer_user_intent_ipv4":1460,"alice_lease4":lease[0],
 "client_a_tun_mtu_before":old,"client_a_tun_mtu_after_os":new,
 "sibling_b_tun_mtu_unchanged":bmtu,"sibling_alice_d_tun_mtu_unchanged":dmtu,
 "bob_while_A_switch_udp":24,"second_alice_device_while_A_switch_udp":24,
 "A_after_switch_udp":5,"new_original_tls_rust_M4":True,"old_native_stop":True,
 "physical_change_command_to_ready_ms":round((ready-changed)/1e6,2),
 "ready_to_first_5_echo_completed_ms":round((first-ready)/1e6,2),
 "native_notification_to_TLS_ms":"NOT_MEASURED",
 "TLS_authenticated_to_first_single_packet_ms":"NOT_MEASURED",
 "cpu_p99":"NOT_MEASURED"}
pathlib.Path(sys.argv[12]).write_text(json.dumps(summary,indent=2)+"\n")
print("M0_PLAN028_TRUE_NATIVE_X86_TWO_ALICE_DEVICES_BOB_UNINTERRUPTED_DURING_A_PHYSICAL_SOURCE_SWITCH_PASS "+
 "sibling_b_24=1 sibling_alice_d_24=1 own_lease_retained=1 new_real_udp=5 "+
 "outer1460_to_physical1280=1 sibling_tun_mtu_unchanged=1",flush=True)
PY
  for p in "$A_PID" "$B_PID" "$D_PID" "$S_PID";do
    sudo -n kill -TERM "$p"
  done
  for _ in {1..80};do
    if ! sudo -n kill -0 "$(cat "$TMP/a.pid")" 2>/dev/null &&
       ! sudo -n kill -0 "$(cat "$TMP/b.pid")" 2>/dev/null &&
       ! sudo -n kill -0 "$(cat "$TMP/d.pid")" 2>/dev/null &&
       ! sudo -n kill -0 "$(cat "$TMP/s.pid")" 2>/dev/null;then break;fi
    sleep .25
  done
  for pair in "A a" "B b" "D d" "server s";do
    read -r name short <<<"$pair"
    if sudo -n kill -0 "$(cat "$TMP/$short.pid")" 2>/dev/null;then
      echo "H1107 owned Stop not joined $name" >&2;exit 1
    fi
  done
  for name in A B D;do
    grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client' "$TMP/$name.log"
  done
  grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server' "$TMP/server.log"
  echo "M0_PLAN028_NATIVE_X86_SIBLING_SOURCE_SWITCH_EXACT_RUST_STOP_PASS"
  exit 0
fi
# A is still LIVE. A fresh authenticated Go TLS client in another real
# netns uses the SAME installation identity and a NEW underlay five-tuple.
# Server must grant one generation overlap, retain its logical epoch and
# lease /32, publish the new Rust owner only after M4 starts and then Stop A.
sudo -n kill -0 "$(cat "$TMP/a.pid")"
start_client "$NSR" wbdvr0 10.25.0.4 wbdvr4 43031 alice auth-alice-original-20261103 "$TMP/install-A" "$TMP/R.log" "$TMP/r.pid"
R_PID=$!
await_client "$TMP/R.log" 4
IPR="$(get_auto_ip "$TMP/R.log")"
[[ "$IPR" == "$IPA" ]] || { echo "same authenticated installation lost original /32" >&2;exit 1; }
sudo -n ip -n "$NSR" route replace 10.66.0.1/32 dev wbdvr4
for _ in {1..48};do
  if grep -q 'V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=same-lease-new-generation' "$TMP/server.log";then break;fi
  sleep .25
done
grep -q 'V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=same-lease-new-generation' "$TMP/server.log"
echo_udp "$NSR" "$IPR" "ALICE_NEW_GENERATION" 6 "$TMP/R-handover.log" &
P_R=$!
echo_udp "$NSB" "$IPB" "BOB_SURVIVES_ALICE_RECONNECT" 6 "$TMP/B-survive-R.log" &
P_BS=$!
echo_udp "$NSD" "$IPD" "ALICE_SECOND_INSTALL_SURVIVES_TAKEOVER" 6 "$TMP/D-survive-R.log" &
P_DS=$!
wait "$P_R"
wait "$P_BS"
wait "$P_DS"
sudo -n kill -TERM "$(cat "$TMP/a.pid")"
for _ in {1..48};do
  if ! sudo -n kill -0 "$(cat "$TMP/a.pid")" 2>/dev/null;then break;fi
  sleep .25
done
if sudo -n kill -0 "$(cat "$TMP/a.pid")" 2>/dev/null;then
  echo 'PLAN028 client A original Rust Stop incomplete' >&2;exit 1
fi
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/A.log"
sudo -n kill -TERM "$(cat "$TMP/r.pid")"
for _ in {1..48};do
  if ! sudo -n kill -0 "$(cat "$TMP/r.pid")" 2>/dev/null;then break;fi
  sleep .25
done
if sudo -n kill -0 "$(cat "$TMP/r.pid")" 2>/dev/null;then
  echo 'PLAN028 replacement Alice native Rust Stop incomplete' >&2;exit 1
fi
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/R.log"
sudo -n kill -TERM "$(cat "$TMP/d.pid")"
for _ in {1..48};do
  if ! sudo -n kill -0 "$(cat "$TMP/d.pid")" 2>/dev/null;then break;fi
  sleep .25
done
if sudo -n kill -0 "$(cat "$TMP/d.pid")" 2>/dev/null;then
  echo 'PLAN028 independent Alice installation native Rust Stop incomplete' >&2;exit 1
fi
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/D.log"
echo_udp "$NSB" "$IPB" "B_ONLY_AFTER_A_STOP" 5 "$TMP/B-only.log"
sudo -n kill -TERM "$(cat "$TMP/b.pid")"
sudo -n kill -TERM "$(cat "$TMP/s.pid")"
for _ in {1..48};do
  if ! sudo -n kill -0 "$(cat "$TMP/b.pid")" 2>/dev/null &&
     ! sudo -n kill -0 "$(cat "$TMP/s.pid")" 2>/dev/null;then break;fi
  sleep .25
done
if sudo -n kill -0 "$(cat "$TMP/b.pid")" 2>/dev/null ||
   sudo -n kill -0 "$(cat "$TMP/s.pid")" 2>/dev/null;then
  echo 'PLAN028 B/server native Stop incomplete' >&2;exit 1
fi
grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/B.log"
grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server' "$TMP/server.log"
# A/R are two TLS generations of one installation, Bob and Alice-D are
# siblings. Every REAL client process now owns ONE Rust TUN reader joined
# AFTER its own M1/M4 generation native Stop; never a competing per-lane
# destructive TUN reader even when the same device reauthenticates.
for role in A B D R;do
  grep -q 'V4_PUBLIC_SHARED_TUN_READER_READY role=client auto_lease=1 owner=rust_single_kernel_reader' "$TMP/$role.log"
  grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client' "$TMP/$role.log"
done
python3 - "$TMP/server.log" <<'PY'
import pathlib,re,sys
t=pathlib.Path(sys.argv[1]).read_text()
assert t.count('V4_PUBLIC_MULTI_SESSION_READY role=server')>=4
assert t.count('V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=same-lease-new-generation')==1
assert t.count('V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=server-close')>=3
m=re.findall(r'V4_PUBLIC_SHARED_TUN_STOP generation=(\d+) routed=(\d+) unrouted=(\d+) backpressure=(\d+) reader_joined=1',t)
assert len(m)==1,m
generation,routed,unrouted,backpressure=map(int,m[0])
assert generation>0 and routed>=70,(generation,routed,unrouted,backpressure)
print("M0_PLAN028_REAL_TWO_ACCOUNT_SAME_SERVER_PORT_SHARED_RUST_TUN_PASS original_tls_sessions=4 distinct_auto_leases=3 server_port=443 A=5 overlap_A=12 overlap_B=12 triple_A=6 triple_B=6 triple_D=6 alice_new_generation=6 bob_while_alice_reauth=6 alice_sibling_while_reauth=6 B_after_A_Stop=5 routed=%d unrouted=%d backpressure=%d native_stop=1"%(routed,unrouted,backpressure),flush=True)
print("M0_PLAN028_REAL_THREE_DEVICE_SAME_ACCOUNT_TWO_INSTALLATIONS_ANOTHER_ACCOUNT_ONE_PORT_NATIVE_PASS protected_tls_sessions=4 distinct_installations=3 distinct_lease32=3 live_devices=3 server_port=443 shared_tun_single_reader=1 total_real_udp=70 exact_generation_Stop=1",flush=True)
print("M0_PLAN028_REAL_SAME_INSTALL_ZERO_EPOCH_NATIVE_A_TO_AB_TO_B_PASS same_verified_lease=1 fresh_original_go_tls=1 new_rust_owner=1 old_exact_Stop=1 other_account_delivered=1",flush=True)
PY
for pair in "A-only A_ONLY 5" "A-plus-B A_PLUS_B_A 12" "B-plus-A A_PLUS_B_B 12" "A-three ALICE_OLD_INSTALL_3DEVICES 6" "B-three BOB_ACCOUNT_3DEVICES 6" "D-three ALICE_SECOND_INSTALLATION_3DEVICES 6" "R-handover ALICE_NEW_GENERATION 6" "B-survive-R BOB_SURVIVES_ALICE_RECONNECT 6" "D-survive-R ALICE_SECOND_INSTALL_SURVIVES_TAKEOVER 6" "B-only B_ONLY_AFTER_A_STOP 5";do
  read -r file label count <<<"$pair"
  grep -q "M0_PLAN028_REAL_APP_ECHO_OK label=$label delivered=$count" "$TMP/$file.log"
done
echo 'M0_PLAN028_REAL_GO_TLS_TWO_ACCOUNTS_ONE_PORT_MULTIDEVICE_NATIVE_STOP_PASS'
