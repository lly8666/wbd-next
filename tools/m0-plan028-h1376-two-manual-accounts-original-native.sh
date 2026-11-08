#!/usr/bin/env bash
# PLAN028 original Go TLS: two independent accounts, one server port,
# one real Rust kernel TUN reader, A then A+B then B, both real native Stop.
set -euo pipefail
ROOT="$(realpath "$1")"
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
cat >"$TMP/manual-leases.json" <<'JSON'
{"alice":"10.66.0.2/32","bob":"10.66.0.3/32"}
JSON
chmod 0600 "$TMP/users.json" "$TMP/manual-leases.json" "$TMP/key.pem"
env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-server" --init-route-key-file "$TMP/route-key.hex"
test "$(stat -c %a "$TMP/route-key.hex")" = 600
sudo -n ip netns exec "$NSS" bash -c "
  echo \$\$ > '$TMP/s.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
    --raw-interface wbdvs0 --local-ip 10.25.0.1 --local-port 443 \
    --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
    --server-name wbd-v4.example.test --route-key-hex-file '$TMP/route-key.hex' \
    --users-file '$TMP/users.json' --manual-client-leases-file '$TMP/manual-leases.json' \
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
    for _ in range(90):
        msg,src=s.recvfrom(4096)
        assert msg.startswith(b"WBD_PLAN028_REAL_APP/")
        s.sendto(b"WBD_PLAN028_REAL_ECHO/"+msg,src)
finally:s.close()
' >"$TMP/echo.log" 2>&1 &
ECHO_PID=$!
start_client(){
  local ns="$1" raw="$2" ip="$3" tun="$4" port="$5" user="$6" pass="$7" key="$8" logfile="$9"
  shift 9
  local pidfile="$1" client_lease="" client_tunnel=""
  if [[ "$user" == "alice" ]];then
    client_lease="10.66.0.2/32";client_tunnel="00112233445566778899aabbccddeeff"
  elif [[ "$user" == "bob" ]];then
    client_lease="10.66.0.3/32";client_tunnel="ffeeddccbbaa99887766554433221100"
  else
    echo "unknown original protected test principal" >&2;return 1
  fi
  sudo -n ip netns exec "$ns" bash -c "
    echo \$\$ > '$pidfile'
    exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-client' \
      --raw-interface '$raw' --local-ip '$ip' --local-port '$port' \
      --peer-ip 10.25.0.1 --peer-port 443 --tun-name '$tun' \
      --server-name wbd-v4.example.test --route-key-hex-file '$TMP/route-key.hex' --tls-ca-pem '$TMP/cert.pem' \
      --username '$user' --password '$pass' \
      --tun-ipv4 '$client_lease' --tunnel-id '$client_tunnel' --mode normal
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
  sudo -n ip netns exec "$ns" env WBD_SRC="$src" WBD_LABEL="$label" WBD_COUNT="$count" python3 -u -c '
import os,socket
ip=os.environ["WBD_SRC"];label=os.environ["WBD_LABEL"];count=int(os.environ["WBD_COUNT"])
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind((ip,0));s.settimeout(8)
try:
    for n in range(count):
        msg=b"WBD_PLAN028_REAL_APP/"+label.encode()+b"/"+str(n).encode()
        assert s.sendto(msg,("10.66.0.1",45901))==len(msg)
        data,src=s.recvfrom(4096)
        assert data==b"WBD_PLAN028_REAL_ECHO/"+msg and src[0]=="10.66.0.1",(label,n,data,src)
    print("M0_PLAN028_REAL_APP_ECHO_OK label=%s delivered=%d"%(label,count),flush=True)
finally:s.close()
' >"$output" 2>&1
}

# These are real manual-IP original-Go TLS/Rust product clients, never
# an auto-lease impersonation. Both distinct server-owned /32s are checked
# only AFTER protected TLS user/password authentication.
start_client "$NSA" wbdva0 10.25.0.2 wbdva4 41031 alice auth-alice-original-20261103 "$TMP/install-A" "$TMP/A.log" "$TMP/a.pid"
A_PID=$!
await_client "$TMP/A.log" 1
IPA="10.66.0.2"
sudo -n ip -n "$NSA" -j addr show dev wbdva4 >"$ART/h1376-alice-native-tun-ip.json"
sudo -n ip -n "$NSA" route replace 10.66.0.1/32 dev wbdva4
echo_udp "$NSA" "$IPA" "A_ONLY_AUTH_MANUAL" 5 "$TMP/A-only.log"
start_client "$NSB" wbdvb0 10.25.0.3 wbdvb4 42031 bob auth-bob-original-20261103 "$TMP/install-B" "$TMP/B.log" "$TMP/b.pid"
B_PID=$!
await_client "$TMP/B.log" 2
IPB="10.66.0.3"
sudo -n ip -n "$NSB" -j addr show dev wbdvb4 >"$ART/h1376-bob-native-tun-ip.json"
sudo -n ip -n "$NSB" route replace 10.66.0.1/32 dev wbdvb4
echo_udp "$NSA" "$IPA" "A_AND_B_ACTIVE_A" 12 "$TMP/A-plus-B.log" &
PA=$!
echo_udp "$NSB" "$IPB" "A_AND_B_ACTIVE_B" 12 "$TMP/B-plus-A.log" &
PB=$!
wait "$PA"
wait "$PB"
sudo -n kill -TERM "$(cat "$TMP/a.pid")"
for _ in {1..80};do
 if ! sudo -n kill -0 "$(cat "$TMP/a.pid")" 2>/dev/null;then break;fi
 sleep .25
done
if sudo -n kill -0 "$(cat "$TMP/a.pid")" 2>/dev/null;then
 echo "REAL MANUAL A ORIGINAL NATIVE STOP FAILED" >&2;exit 1
fi
grep -Fq "V4_PUBLIC_NATIVE_STOP_DRAINED role=client" "$TMP/A.log"
echo_udp "$NSB" "$IPB" "B_ALONE_AFTER_A_EXACT_STOP" 12 "$TMP/B-only.log"
start_client "$NSR" wbdvr0 10.25.0.4 wbdvr4 43031 alice auth-alice-original-20261103 "$TMP/install-A" "$TMP/R.log" "$TMP/r.pid"
R_PID=$!
await_client "$TMP/R.log" 3
sudo -n ip -n "$NSR" route replace 10.66.0.1/32 dev wbdvr4
echo_udp "$NSR" "$IPA" "A_NEW_TLS_AFTER_OLD_STOP" 6 "$TMP/R-handover.log" &
PR=$!
echo_udp "$NSB" "$IPB" "B_WHILE_A_NEW_TLS" 6 "$TMP/B-survive-R.log" &
PBR=$!
wait "$PR"
wait "$PBR"
sudo -n kill -TERM "$(cat "$TMP/r.pid")"
for _ in {1..80};do
 if ! sudo -n kill -0 "$(cat "$TMP/r.pid")" 2>/dev/null;then break;fi
 sleep .25
done
if sudo -n kill -0 "$(cat "$TMP/r.pid")" 2>/dev/null;then
 echo "REAL MANUAL A reauth NATIVE STOP FAILED" >&2;exit 1
fi
grep -Fq "V4_PUBLIC_NATIVE_STOP_DRAINED role=client" "$TMP/R.log"
echo_udp "$NSB" "$IPB" "B_AFTER_ALL_A_STOP" 6 "$TMP/B-survive-all-A.log"
sudo -n kill -TERM "$(cat "$TMP/b.pid")"
sudo -n kill -TERM "$(cat "$TMP/s.pid")"
for _ in {1..80};do
 if ! sudo -n kill -0 "$(cat "$TMP/b.pid")" 2>/dev/null &&
    ! sudo -n kill -0 "$(cat "$TMP/s.pid")" 2>/dev/null;then break;fi
 sleep .25
done
if sudo -n kill -0 "$(cat "$TMP/b.pid")" 2>/dev/null||
   sudo -n kill -0 "$(cat "$TMP/s.pid")" 2>/dev/null;then
 echo "B/server original Rust Stop incomplete" >&2;exit 1
fi
grep -Fq "V4_PUBLIC_NATIVE_STOP_DRAINED role=client" "$TMP/B.log"
grep -Fq "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" "$TMP/server.log"
for role in A B R;do
 grep -Fq "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client" "$TMP/$role.log"
done
python3 - "$TMP/server.log" "$ART/h1376-alice-native-tun-ip.json" "$ART/h1376-bob-native-tun-ip.json" "$ART/h1376-original-two-manual-accounts.json" <<'PY_H1376'
import json,sys,pathlib,re
s=pathlib.Path(sys.argv[1]).read_text()
links=[json.loads(pathlib.Path(p).read_text()) for p in sys.argv[2:4]]
assert all(len(x)==1 and isinstance(x[0].get("mtu"),int) for x in links),links
actual=[]
for x in links:
  inet=[z["local"] for z in x[0]["addr_info"] if z["family"]=="inet"]
  assert len(inet)==1,inet
  actual.append(inet[0])
assert actual==["10.66.0.2","10.66.0.3"],actual
assert s.count("V4_PUBLIC_MULTI_SESSION_READY role=server")>=3
assert "V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server" in s
m=re.findall(r'V4_PUBLIC_SHARED_TUN_STOP generation=(\d+) routed=(\d+) unrouted=(\d+) backpressure=(\d+) reader_joined=1',s)
assert len(m)==1,m
generation,routed,unrouted,backpressure=map(int,m[0])
assert routed>=59 and unrouted==0 and backpressure==0,(generation,routed,unrouted,backpressure)
v={"classification":"PASS_SCOPED_ORIGINAL_LINUX_TWO_AUTHENTICATED_MANUAL_ACCOUNTS_TLS443_RUST_M4",
"test_platform":"REAL_LINUX_KERNEL_TUN_TWO_CLIENT_NETNS",
"actual_tls_sessions":3,"authenticated_accounts":["alice","bob"],
"server_authenticated_manual_leases4":{"alice":"10.66.0.2/32","bob":"10.66.0.3/32"},
"real_client_kernel_TUN_addresses":actual,
"A_to_A_plus_B_to_B_then_A_reauth_and_stop":True,
"one_original_server_port":443,"one_shared_original_server_Rust_TUN":True,
"real_UDP_echoes":59,"original_exact_all_client_Stop":True,"server_exact_shared_tun_Stop":True,
"server_routed":routed,"server_unrouted":unrouted,"server_backpressure":backpressure,
"windows_two_signed_authenticated_product_clients":"NOT_RUN",
"same_socket_hot_MTU":"NOT_RUN"}
pathlib.Path(sys.argv[4]).write_text(json.dumps(v,indent=2)+"\n")
print("M0_PLAN028_H1376_TWO_REAL_AUTH_MANUAL_ACCOUNTS_ORIGINAL_TLS443_RUST_TUN_STOP_PASS",flush=True)
PY_H1376
for item in \
 "A-only A_ONLY_AUTH_MANUAL 5" \
 "A-plus-B A_AND_B_ACTIVE_A 12" \
 "B-plus-A A_AND_B_ACTIVE_B 12" \
 "B-only B_ALONE_AFTER_A_EXACT_STOP 12" \
 "R-handover A_NEW_TLS_AFTER_OLD_STOP 6" \
 "B-survive-R B_WHILE_A_NEW_TLS 6" \
 "B-survive-all-A B_AFTER_ALL_A_STOP 6";do
 read -r file label count <<<"$item"
 grep -Fq "M0_PLAN028_REAL_APP_ECHO_OK label=$label delivered=$count" "$TMP/$file.log"
done
echo "M0_PLAN028_H1376_ORIGINAL_GO_TLS_MANUAL_ACCOUNT_MAP_A_B_AND_B_AFTER_A_STOP_PASS"
