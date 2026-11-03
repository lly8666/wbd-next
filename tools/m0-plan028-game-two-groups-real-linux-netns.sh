#!/usr/bin/env bash
# PLAN028 two original Go TLS Game2 groups concurrently sharing a single
# server 443, ONE authenticated Rust TUN reader, two independent /32 leases.
set -euo pipefail
MODE="${WBD_PLAN028_GAME_MULTI_MODE:-game2}"
case "$MODE" in
  game2) LANES=2 ;;
  game4) LANES=4 ;;
  *) echo "PLAN028 two-group real native only supports game2/game4" >&2;exit 2 ;;
esac
ROOT="$(realpath "${1:?fixed-build source directory}")"
test -x "$ROOT/wbd-v4-client" && test -x "$ROOT/wbd-v4-server"
test -s "$ROOT/libwbd_engine.so" && test -c /dev/net/tun
: "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}"
TAG="${GITHUB_RUN_ID: -7}"
NSS="vgsv$TAG"; NSA="vgca$TAG"; NSB="vgcb$TAG"
BR="vgb$TAG"; RS="vgs$TAG"; RA="vga$TAG"; RB="vgc$TAG"
TMP="$RUNNER_TEMP/plan028-game-groups-$TAG"
mkdir -m 0700 -p "$TMP"
PIDS=()
cleanup(){
  code=$?
  set +e
  if ((code));then
    echo "PLAN028_GAME_MULTIGROUP_NATIVE_FAIL code=$code" >&2
    for f in server.log A.log B.log echo.log a_echo.log b_echo.log b_after.log;do
      if [[ -f "$TMP/$f" ]];then
        echo "=== $f ===" >&2;tail -60 "$TMP/$f" >&2
      fi
    done
  fi
  for p in "${PIDS[@]}";do sudo -n kill -TERM "$p" 2>/dev/null || true;done
  for p in "$RS" "$RA" "$RB" "$BR";do sudo -n ip link del "$p" 2>/dev/null || true;done
  for n in "$NSS" "$NSA" "$NSB";do sudo -n ip netns del "$n" 2>/dev/null || true;done
  rm -rf "$TMP"
}
trap cleanup EXIT
for ns in "$NSS" "$NSA" "$NSB";do
  sudo -n ip netns add "$ns"
  sudo -n ip -n "$ns" link set lo up
done
sudo -n ip link add "$BR" type bridge
sudo -n ip link set "$BR" up
for def in "$RS wbdvs0 $NSS 10.25.0.1/24" "$RA wbdva0 $NSA 10.25.0.2/24" "$RB wbdvb0 $NSB 10.25.0.3/24";do
  read -r host guest ns addr <<<"$def"
  sudo -n ip link add "$host" type veth peer name "$guest"
  sudo -n ip link set "$host" master "$BR"
  sudo -n ip link set "$host" up
  sudo -n ip link set "$guest" netns "$ns"
  sudo -n ip -n "$ns" addr add "$addr" dev "$guest"
  sudo -n ip -n "$ns" link set "$guest" up
  sudo -n ip netns exec "$ns" iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
done
openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
  -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
  -subj '/CN=wbd-v4.example.test' -addext 'subjectAltName=DNS:wbd-v4.example.test' \
  >"$TMP/cert-create.log" 2>&1
cat >"$TMP/users.json" <<'JSON'
{"alice":"game-alice-protected-20261103","bob":"game-bob-protected-20261103"}
JSON
chmod 0600 "$TMP/users.json" "$TMP/key.pem"
ROUTE='aabbccddeeff0011223344556677889900112233445566778899aabbccddeeff'
sudo -n ip netns exec "$NSS" bash -c "
 echo \$\$ > '$TMP/server.pid'
 exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
  --raw-interface wbdvs0 --local-ip 10.25.0.1 --local-port 443 \
  --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
  --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
  --users-file '$TMP/users.json' --lease-pool 10.66.0.128/25 \
  --tls-cert '$TMP/cert.pem' --tls-key '$TMP/key.pem' --mode "$MODE"
" >"$TMP/server.log" 2>&1 &
PIDS+=("$!")
for _ in {1..80};do
 if grep -q "V4_PUBLIC_GAME_MULTI_SERVER_READY role=server port=443 lanes_per_group=$LANES" "$TMP/server.log";then break;fi
 sleep .25
done
grep -q "V4_PUBLIC_GAME_MULTI_SERVER_READY role=server port=443 lanes_per_group=$LANES" "$TMP/server.log"

# One real server inner IPv4 UDP echo; no shadow tunnel or synthesized
# FakeTCP/TLS receipt. Both clients send through their own real TUN.
sudo -n ip netns exec "$NSS" python3 -u -c '
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.1",45901));s.settimeout(45)
try:
  for _ in range(30):
    data,src=s.recvfrom(4096)
    assert data.startswith(b"WBD_GAME_GROUP/"),(src,data)
    s.sendto(b"WBD_GAME_ECHO/"+data,src)
finally:s.close()
' >"$TMP/echo.log" 2>&1 &
PIDS+=("$!")
start_client(){
 local ns="$1" raw="$2" ip="$3" tun="$4" port="$5" user="$6" password="$7" key="$8" log="$9"
 sudo -n ip netns exec "$ns" bash -c "
  echo \$\$ > '$TMP/$user.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-client' \
   --raw-interface '$raw' --local-ip '$ip' --local-port '$port' \
   --peer-ip 10.25.0.1 --peer-port 443 --tun-name '$tun' \
   --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
   --username '$user' --password '$password' \
   --auto-ip --installation-id-file '$key' --mode "$MODE"
 " >"$log" 2>&1 &
 PIDS+=("$!")
}
await_group(){
 local log="$1" count="$2"
 for _ in {1..120};do
  if grep -q 'V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=$LANES' "$log" &&
     [[ "$(grep -c 'V4_PUBLIC_GAME_MULTI_GROUP_READY role=server' "$TMP/server.log" || true)" -ge "$count" ]];then
   return 0
  fi
  sleep .25
 done
 echo "PLAN028 authentic Game2 groups not ready" >&2
 return 1
}
read_lease(){
 python3 - "$1" <<'PY'
import pathlib,re,ipaddress,sys
text=pathlib.Path(sys.argv[1]).read_text()
m=re.findall(r"V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.[0-9]+)/32",text)
assert len(m)==1,m
assert ipaddress.ip_address(m[0]) in ipaddress.ip_network("10.66.0.128/25")
print(m[0])
PY
}
send_udp(){
 local ns="$1" source="$2" label="$3" qty="$4" target="$5"
 sudo -n ip netns exec "$ns" env GAME_SRC="$source" GAME_LABEL="$label" GAME_QTY="$qty" python3 -u -c '
import os,socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ["GAME_SRC"],0));s.settimeout(10)
label=os.environ["GAME_LABEL"].encode()
for i in range(int(os.environ["GAME_QTY"])):
  m=b"WBD_GAME_GROUP/"+label+b"/"+str(i).encode()
  assert s.sendto(m,("10.66.0.1",45901))==len(m)
  data,peer=s.recvfrom(4096)
  assert data==b"WBD_GAME_ECHO/"+m and peer[0]=="10.66.0.1",(label,i,data,peer)
print("PLAN028_GAME_REAL_APP_OK label=%s bytes=%d"%(label.decode(),int(os.environ["GAME_QTY"])),flush=True)
' >"$target" 2>&1
}
start_client "$NSA" wbdva0 10.25.0.2 wbdva4 41031 alice game-alice-protected-20261103 "$TMP/install-A" "$TMP/A.log"
await_group "$TMP/A.log" 1
IPA="$(read_lease "$TMP/A.log")"
sudo -n ip -n "$NSA" route replace 10.66.0.1/32 dev wbdva4
send_udp "$NSA" "$IPA" "A_ONLY" 3 "$TMP/a_echo.log"
start_client "$NSB" wbdvb0 10.25.0.3 wbdvb4 42031 bob game-bob-protected-20261103 "$TMP/install-B" "$TMP/B.log"
await_group "$TMP/B.log" 2
IPB="$(read_lease "$TMP/B.log")"
[[ "$IPA" != "$IPB" ]] || { echo "protected Game accounts share /32" >&2;exit 1; }
sudo -n ip -n "$NSB" route replace 10.66.0.1/32 dev wbdvb4
send_udp "$NSA" "$IPA" "A_PLUS_B_A" 6 "$TMP/a_echo.log" &
a_echo_pid=$!
send_udp "$NSB" "$IPB" "A_PLUS_B_B" 6 "$TMP/b_echo.log" &
b_echo_pid=$!
wait "$a_echo_pid" "$b_echo_pid"
# Only client A stops. Do not Stop the one server or B's Rust Game owner.
sudo -n kill -TERM "$(cat "$TMP/alice.pid")"
for _ in {1..80};do
 if grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=2' "$TMP/A.log";then break;fi
 sleep .25
done
grep -q 'V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=2' "$TMP/A.log"
send_udp "$NSB" "$IPB" "B_AFTER_A_STOP" 6 "$TMP/b_after.log"
sudo -n kill -TERM "$(cat "$TMP/bob.pid")"
sudo -n kill -TERM "$(cat "$TMP/server.pid")"
for _ in {1..80};do
 if [[ "$(grep -c 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log" || true)" -ge 2 ]] &&
    grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log";then break;fi
 sleep .25
done
grep -q 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log"
[[ "$(grep -c 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log")" -eq 2 ]]
grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log"
echo "M0_PLAN028_GAME_TWO_PROTECTED_ACCOUNTS_ONE_443_ONE_RUST_TUN_NATIVE_PASS groups=2 lanes_each=$LANES verified_leases=2 simultaneous_udp=1 B_survives_A_stop=1 native_stop_drained=1"
