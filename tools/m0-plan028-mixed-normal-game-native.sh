#!/usr/bin/env bash
# PLAN028 single ORIGINAL Go TLS server443 with simultaneous Normal auto,
# Game2 and Game4 FEC6. Three native x86/x86 devices, one real Rust TUN
# reader and genuine IPv4 UDP. No TLS prelude, no generated data packets.
set -euo pipefail
ROOT="$(realpath "$1")"
test -x "$ROOT/wbd-v4-client" && test -x "$ROOT/wbd-v4-server"
test -s "$ROOT/libwbd_engine.so" && test -c /dev/net/tun
: "$GITHUB_RUN_ID" "$RUNNER_TEMP"
TAG="$(printf '%s' "$GITHUB_RUN_ID" | tail -c 7)"
NSS="mxs$TAG"; NSA="mxa$TAG"; NSB="mxb$TAG"; NSC="mxc$TAG"
BR="mxx$TAG"
TMP="$RUNNER_TEMP/plan028-mixed-443-$TAG"
mkdir -p "$TMP"
declare -a PIDS=()
cleanup(){
  code=$?
  set +e
  if ((code));then
    echo "M0_PLAN028_MIXED_NATIVE_FAIL code=$code" >&2
    for f in server.log A.log B.log C.log echo.log A-udp.log B-udp.log C-udp.log B-after.log C-after.log;do
      if test -f "$TMP/$f";then echo "== $f ==" >&2;tail -65 "$TMP/$f" >&2;fi
    done
  fi
  for f in server.pid A.pid B.pid C.pid echo.pid;do
    if test -f "$TMP/$f";then sudo -n kill -TERM "$(cat "$TMP/$f")" 2>/dev/null || true;fi
  done
  for p in "$NSS" "$NSA" "$NSB" "$NSC";do sudo -n ip netns del "$p" 2>/dev/null || true;done
  sudo -n ip link del "$BR" 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT
for ns in "$NSS" "$NSA" "$NSB" "$NSC";do
  sudo -n ip netns add "$ns"
  sudo -n ip -n "$ns" link set lo up
done
sudo -n ip link add "$BR" type bridge
sudo -n ip link set "$BR" up
for item in \
  "mhs0 mxs0 $NSS 10.25.0.1/24" \
  "mha0 mxa0 $NSA 10.25.0.2/24" \
  "mhb0 mxb0 $NSB 10.25.0.3/24" \
  "mhc0 mxc0 $NSC 10.25.0.4/24";do
  read -r host guest ns cidr <<< "$item"
  sudo -n ip link add "$host" type veth peer name "$guest"
  sudo -n ip link set "$host" master "$BR"
  sudo -n ip link set "$host" up
  sudo -n ip link set "$guest" netns "$ns"
  sudo -n ip -n "$ns" addr add "$cidr" dev "$guest"
  sudo -n ip -n "$ns" link set "$guest" up
  sudo -n ip netns exec "$ns" iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
done
openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
  -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
  -subj '/CN=wbd-v4.example.test' \
  -addext 'subjectAltName=DNS:wbd-v4.example.test' >"$TMP/cert-create.log" 2>&1
cat >"$TMP/users.json" <<'JSON'
{"alice":"alice-mixed-protected","bob":"bob-mixed-protected","carol":"carol-mixed-protected"}
JSON
chmod 0600 "$TMP/users.json" "$TMP/key.pem"
env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-server" --init-route-key-file "$TMP/route-key.hex"
sudo -n ip netns exec "$NSS" bash -c "
 echo \$\$ > '$TMP/server.pid'
 exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
   --raw-interface mxs0 --local-ip 10.25.0.1 --local-port 443 \
   --tun-name mxs4 --tun-ipv4 10.66.0.1/24 \
   --server-name wbd-v4.example.test --route-key-hex-file '$TMP/route-key.hex' \
   --users-file '$TMP/users.json' --lease-pool 10.66.0.128/25 \
   --tls-cert '$TMP/cert.pem' --tls-key '$TMP/key.pem' --mode shared
" >"$TMP/server.log" 2>&1 &
PIDS+=("$!")
for i in {1..100};do
 if grep -Fq "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" "$TMP/server.log";then break;fi
 sleep .25
done
grep -Fq "V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443" "$TMP/server.log"

sudo -n ip netns exec "$NSS" bash -c "
 echo \$\$ > '$TMP/echo.pid'
 exec python3 -u -c '
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((\"10.66.0.1\",45901))
s.settimeout(60)
try:
  for i in range(160):
    data,addr=s.recvfrom(4096)
    assert data.startswith(b\"WBD_MIXED443/\")
    s.sendto(b\"WBD_MIXED_ECHO/\"+data,addr)
finally:s.close()
'
" >"$TMP/echo.log" 2>&1 &
PIDS+=("$!")

start_client(){
 local ns="$1" guest="$2" ip="$3" tun="$4" port="$5" who="$6" secret="$7" mode="$8" extra="$9"
 sudo -n ip netns exec "$ns" bash -c "
 echo \$\$ > '$TMP/$who.pid'
 exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-client' \
  --raw-interface '$guest' --local-ip '$ip' --local-port '$port' \
  --peer-ip 10.25.0.1 --peer-port 443 --tun-name '$tun' \
  --server-name wbd-v4.example.test --route-key-hex-file '$TMP/route-key.hex' \
  --tls-ca-pem '$TMP/cert.pem' --username '$who' --password '$secret' \
  --auto-ip --installation-id-file '$TMP/install-$who' --mode '$mode' $extra
 " >"$TMP/$who.log" 2>&1 &
 PIDS+=("$!")
}
# Interleave 2+4+1 raw source TCP ports to expose first-flight mux errors.
start_client "$NSA" mxa0 10.25.0.2 mxa4 41031 alice alice-mixed-protected game2 '--record-cipher chacha20-poly1305'
start_client "$NSB" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 '--game-fec fixed6 --record-cipher aes-256-gcm'
start_client "$NSC" mxc0 10.25.0.4 mxc4 43031 carol carol-mixed-protected fec-auto '--record-cipher aes-128-gcm'
for i in {1..140};do
 if grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=2" "$TMP/alice.log" &&
    grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=4" "$TMP/bob.log" &&
    grep -Fq "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" "$TMP/carol.log" &&
    grep -Fq "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443" "$TMP/server.log" &&
    grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=2" "$TMP/server.log" &&
    grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=4" "$TMP/server.log";then break;fi
 sleep .25
done
for pair in "alice 2" "bob 4";do
 read -r who lanes <<< "$pair"
 grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=$lanes" "$TMP/$who.log"
done
grep -Fq "V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client" "$TMP/carol.log"
grep -Fq "V4_PUBLIC_MIXED_NORMAL_READY role=server port=443" "$TMP/server.log"
grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=4" "$TMP/server.log"
grep -Fq "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=2" "$TMP/server.log"

lease(){
 grep 'V4_PUBLIC_LEASE_APPLIED role=client' "$TMP/$1.log" | \
   sed -n 's/.*os_readback=\([0-9.]*\)\/32.*/\1/p' | tail -1
}
IPA="$(lease alice)"; IPB="$(lease bob)"; IPC="$(lease carol)"
for a in "$IPA" "$IPB" "$IPC";do
 [[ "$a" == 10.66.0.* ]] || { echo "missing verified OS IP $a" >&2;exit 1; }
done
[[ "$IPA" != "$IPB" && "$IPA" != "$IPC" && "$IPB" != "$IPC" ]]
for pair in "$NSA mxa4" "$NSB mxb4" "$NSC mxc4";do
 read -r ns tun <<< "$pair"
 sudo -n ip -n "$ns" route replace 10.66.0.1/32 dev "$tun"
done
# Real OS actual readback, never an inferred configuration.
for item in "$NSA alice mxa4" "$NSB bob mxb4" "$NSC carol mxc4" "$NSS server mxs4";do
 read -r ns who iface <<< "$item"
 sudo -n ip -n "$ns" -j link show dev "$iface" >"fixed-kernel-result/plan028-h1151-$who-tun.json"
done
send_udp(){
 local ns="$1" addr="$2" tag="$3" count="$4" log="$5"
 sudo -n ip netns exec "$ns" python3 - "$addr" "$tag" "$count" >"$log" <<'PY'
import socket,sys
src,tag,count=sys.argv[1],sys.argv[2],int(sys.argv[3])
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((src,0));s.settimeout(3)
for i in range(count):
  msg=(f"WBD_MIXED443/{tag}/{i}").encode()
  expected=b"WBD_MIXED_ECHO/"+msg
  for attempt in range(4):
    s.sendto(msg,("10.66.0.1",45901))
    try:
      payload,addr=s.recvfrom(4096)
      if payload==expected and addr[0]=="10.66.0.1":break
    except socket.timeout:pass
  else:raise SystemExit(f"real UDP failure {tag} #{i}")
  print(f"REAL_MIXED_UDP {tag} {i}",flush=True)
s.close()
PY
}
send_udp "$NSA" "$IPA" GAME2_A 12 "$TMP/A-udp.log" &
PA=$!
send_udp "$NSB" "$IPB" GAME4_FEC6_B 12 "$TMP/B-udp.log" &
PB=$!
send_udp "$NSC" "$IPC" NORMAL_AUTO_C 12 "$TMP/C-udp.log" &
PC=$!
wait "$PA" "$PB" "$PC"
grep -Fq "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6" "$TMP/bob.log"
# Client A only stops; independent Game4 and Normal still deliver traffic.
sudo -n kill -TERM "$(cat "$TMP/alice.pid")"
for i in {1..80};do
 if grep -Fq "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=2" "$TMP/alice.log";then break;fi
 sleep .25
done
grep -Fq "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=2" "$TMP/alice.log"
send_udp "$NSB" "$IPB" GAME4_B_AFTER_A_STOP 6 "$TMP/B-after.log" &
PB=$!
send_udp "$NSC" "$IPC" NORMAL_C_AFTER_A_STOP 6 "$TMP/C-after.log" &
PC=$!
wait "$PB" "$PC"
sudo -n kill -TERM "$(cat "$TMP/bob.pid")"
sudo -n kill -TERM "$(cat "$TMP/carol.pid")"
sudo -n kill -TERM "$(cat "$TMP/server.pid")"
for i in {1..100};do
 if grep -Fq "V4_PUBLIC_SHARED_TUN_STOP generation=" "$TMP/server.log" &&
    grep -Fq "V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason=server-close" "$TMP/server.log" &&
    [[ "$(grep -c 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log" || true)" -ge 2 ]];then break;fi
 sleep .25
done
grep -Fq "V4_PUBLIC_SHARED_TUN_STOP generation=" "$TMP/server.log"
grep -Fq "V4_PUBLIC_MIXED_NORMAL_STOP_DRAINED reason=server-close" "$TMP/server.log"
[[ "$(grep -c 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log")" -ge 2 ]]
python3 - "$TMP/server.log" "$TMP/bob.log" "$TMP/carol.log" "$IPA" "$IPB" "$IPC" <<'PY'
import json,pathlib,re,sys
server=pathlib.Path(sys.argv[1]).read_text()
game=pathlib.Path(sys.argv[2]).read_text()
normal=pathlib.Path(sys.argv[3]).read_text()
assert server.count("V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=")>=2
assert server.count("V4_PUBLIC_MIXED_NORMAL_READY role=server port=443")==1
assert "V4_PUBLIC_PER_CLIENT_NORMAL_FEC_READY mode=auto" in server
assert "V4_PUBLIC_GAME_MULTI_GROUP_READY" in server
assert "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6" in game
assert "V4_PUBLIC_MIXED_NORMAL_FEC_EFFECTIVE mode=auto" in server
assert "V4_PUBLIC_NATIVE_STOP_DRAINED role=client" in normal
vals={}
for who in ("alice","bob","carol","server"):
  raw=json.loads(pathlib.Path(f"fixed-kernel-result/plan028-h1151-{who}-tun.json").read_text())
  assert len(raw)==1 and raw[0]["mtu"]>=1100,(who,raw)
  vals[who]=raw[0]["mtu"]
assert vals["server"]>=vals["bob"] and vals["server"]>=vals["carol"],vals
result={"source":"original Go TLS Rust native","server_port":443,
 "native_peers":["game2-off-ChaCha","game4-fixed6-AES256","normal-auto-AES128"],
 "distinct_authenticated_client_ips":sys.argv[4:7],
 "client_os_inner_mtu":vals,
 "real_udp_echoes":{"game2":12,"game4":18,"normal":18},
 "game2_stop_did_not_stop_game4_or_normal":True,
 "shared_rust_tun_reader_final_stop":True}
pathlib.Path("fixed-kernel-result/plan028-h1151-mixed-one443.json").write_text(json.dumps(result,indent=2)+"\n")
print("M0_PLAN028_H1151_X86_ORIGINAL_TLS_ONE443_NORMAL_GAME2_GAME4_FEC6_48_REAL_UDP_EXACT_STOP_PASS",flush=True)
PY
echo "M0_PLAN028_H1151_NATIVE_X86_MIXED_ONE_PORT_ONE_RUST_TUN_PASS"
