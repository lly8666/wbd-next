#!/usr/bin/env bash
# H2216: original Go TLS + Rust native after DOUBLE NAT and routed-TTL decrement.
# Three independent NAT LANs, server DNAT TCP443, original native kernel TUN.
# Real IPv4 UDP echo/Stop; NOT equivalent to Windows Npcap or true ISP WAN.
set -euo pipefail
ROOT="$(realpath "$1")"
test -x "$ROOT/wbd-v4-client" && test -x "$ROOT/wbd-v4-server"
test -s "$ROOT/libwbd_engine.so" && test -c /dev/net/tun
: "$GITHUB_RUN_ID" "$RUNNER_TEMP"
TAG="$(printf '%s' "$GITHUB_RUN_ID" | tail -c 7)"
NSS="mxs$TAG"; NSA="mxa$TAG"; NSB="mxb$TAG"; NSC="mxc$TAG"
R0="mxr0$TAG"; R1="mxr1$TAG"; R2="mxr2$TAG"; R3="mxr3$TAG"
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
  for p in "$NSS" "$NSA" "$NSB" "$NSC" "$R0" "$R1" "$R2" "$R3";do sudo -n ip netns del "$p" 2>/dev/null || true;done
  sudo -n ip link del "$BR" 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT
for ns in "$NSS" "$NSA" "$NSB" "$NSC" "$R0" "$R1" "$R2" "$R3";do
  sudo -n ip netns add "$ns"
  sudo -n ip -n "$ns" link set lo up
done
sudo -n ip link add "$BR" type bridge
sudo -n ip link set "$BR" up
# Four genuine routing namespaces; no endpoint sees another LAN directly.
# Server private 10.25.0.1:443 is reached solely through 198.18.0.100 DNAT.
# The other three routers implement independent client-household SNAT.
for item in \
  "0 $R0 $NSS mhs0 mxs0 10.25.0.1 198.18.0.100" \
  "1 $R1 $NSA mha0 mxa0 10.25.0.2 198.18.0.11" \
  "2 $R2 $NSB mhb0 mxb0 10.25.0.3 198.18.0.12" \
  "3 $R3 $NSC mhc0 mxc0 10.25.0.4 198.18.0.13";do
  read -r index router device host guest private public <<< "$item"
  sudo -n ip link add "$host" type veth peer name "$guest"
  sudo -n ip link set "$host" netns "$router"
  sudo -n ip link set "$guest" netns "$device"
  sudo -n ip -n "$router" addr add 10.25.0.254/24 dev "$host"
  sudo -n ip -n "$router" link set "$host" up
  sudo -n ip -n "$device" addr add "$private/24" dev "$guest"
  sudo -n ip -n "$device" link set "$guest" up
  sudo -n ip -n "$device" route replace default via 10.25.0.254 dev "$guest"
  sudo -n ip link add "wht$index" type veth peer name "wrw$index"
  sudo -n ip link set "wht$index" master "$BR"
  sudo -n ip link set "wht$index" up
  sudo -n ip link set "wrw$index" netns "$router"
  sudo -n ip -n "$router" addr add "$public/24" dev "wrw$index"
  sudo -n ip -n "$router" link set "wrw$index" up
  sudo -n ip netns exec "$router" sysctl -q -w net.ipv4.ip_forward=1
  sudo -n ip netns exec "$router" sysctl -q -w net.ipv4.conf.all.rp_filter=0
  sudo -n ip netns exec "$router" iptables -w -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
  if [[ "$index" == 0 ]];then
    sudo -n ip netns exec "$router" iptables -w -t nat -A PREROUTING -i "wrw$index" -p tcp --dport 443 -j DNAT --to-destination 10.25.0.1:443
    sudo -n ip netns exec "$router" iptables -w -A FORWARD -i "wrw$index" -o "$host" -p tcp --dport 443 -j ACCEPT
  else
    sudo -n ip netns exec "$router" iptables -w -t nat -A POSTROUTING -s 10.25.0.0/24 -o "wrw$index" -j MASQUERADE
    sudo -n ip netns exec "$router" iptables -w -A FORWARD -i "$host" -o "wrw$index" -j ACCEPT
  fi
  sudo -n ip netns exec "$router" iptables -w -P FORWARD DROP
  sudo -n ip netns exec "$device" iptables -w -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
done
# There is no 10.25.0.1 LAN route from clients. The DNAT WAN gateway is required.
for device in "$NSA" "$NSB" "$NSC";do
  sudo -n ip netns exec "$device" ip route get 198.18.0.100 | grep -Fq 'via 10.25.0.254'
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
  --peer-ip 198.18.0.100 --peer-port 443 --tun-name '$tun' \
  --server-name wbd-v4.example.test --route-key-hex-file '$TMP/route-key.hex' \
  --username '$who' --password '$secret' \
  --auto-ip --installation-id-file '$TMP/install-$who' --mode '$mode' $extra
 " >"$TMP/$who.log" 2>&1 &
 PIDS+=("$!")
}
# Interleave 2+4+1 raw source TCP ports to expose first-flight mux errors.
start_client "$NSA" mxa0 10.25.0.2 mxa4 41031 alice alice-mixed-protected game2 '--record-cipher chacha20-poly1305 --tls-verify-server=true --tls-ca-pem "$TMP/cert.pem"'
start_client "$NSB" mxb0 10.25.0.3 mxb4 42031 bob bob-mixed-protected game4 '--game-fec fixed6 --record-cipher aes-256-gcm'
start_client "$NSC" mxc0 10.25.0.4 mxc4 43031 carol carol-mixed-protected fec-auto '--record-cipher aes-128-gcm --tls-verify-server=true --tls-ca-pem "$TMP/cert.pem"'
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
# Exact kernel NAT receipts: fail if any of the three client SNAT or server
# TCP443 DNAT chains did not observe packets. No fake protocol success.
sudo -n ip netns exec "$R0" iptables -w -t nat -nvL PREROUTING > fixed-kernel-result/h2216-server-dnat.txt
sudo -n ip netns exec "$R1" iptables -w -t nat -nvL POSTROUTING > fixed-kernel-result/h2216-client-a-snat.txt
sudo -n ip netns exec "$R2" iptables -w -t nat -nvL POSTROUTING > fixed-kernel-result/h2216-client-b-snat.txt
sudo -n ip netns exec "$R3" iptables -w -t nat -nvL POSTROUTING > fixed-kernel-result/h2216-client-c-snat.txt
python3 - <<'PY_H2216'
import pathlib,re,json,os
root=pathlib.Path("fixed-kernel-result")
for name,target in [("server-dnat","DNAT"),("client-a-snat","MASQUERADE"),("client-b-snat","MASQUERADE"),("client-c-snat","MASQUERADE")]:
    text=(root/f"h2216-{name}.txt").read_text()
    values=[int(m.group(1)) for m in re.finditer(r"^\s*(\d+)\s+\d+\s+"+target+r"\s",text,re.M)]
    if not values or max(values)<=0:raise SystemExit("H2216_KERNEL_NAT_COUNTER_FAIL "+name)
result={"qualification":"REAL_LINUX_NATIVE_NETNS_DOUBLE_NAT","source_sha":os.environ.get("GITHUB_SHA",""),
"original_go_tls":True,"rust_native_drivers":True,"one_server_443_dnat":True,
"clients":3,"independent_client_snat":3,"modes":["game2","game4-fixed6","fec-auto"],
"actual_kernel_udp_echo":True,"owned_stop":True,
"tls_verification":["opt-in","default-off","opt-in"],
"note":"not physical Windows Npcap/ISP NAT; per-hop TTL is route-modified"}
(root/"h2216-double-nat-proof.json").write_text(json.dumps(result,indent=2)+"\n")
print("H2216_REAL_LINUX_ROUTED_DOUBLE_NAT_3_CLIENTS_UDP_STOP_PASS")
PY_H2216
echo "M0_PLAN028_H1151_NATIVE_X86_MIXED_ONE_PORT_ONE_RUST_TUN_PASS"
