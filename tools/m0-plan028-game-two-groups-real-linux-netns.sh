#!/usr/bin/env bash
# PLAN028 two original Go TLS Game2/4 groups concurrently sharing a single
# server 443, ONE authenticated Rust TUN reader, two independent /32 leases.
set -euo pipefail
MODE="${WBD_PLAN028_GAME_MULTI_MODE:-game2}"
HANDOVER="${WBD_PLAN028_GAME_MULTI_HANDOVER:-0}"
GAME_FEC="${WBD_PLAN028_GAME_MULTI_FEC:-off}"
AUTO_ROUTE="${WBD_PLAN028_GAME_MULTI_AUTO_ROUTE:-0}"
AUTH_NEGATIVE="${WBD_PLAN028_GAME_MULTI_AUTH_NEGATIVE:-0}"
if [[ "$AUTH_NEGATIVE" != 0 && "$AUTH_NEGATIVE" != 1 ]];then echo "invalid auth negative selector" >&2;exit 2;fi
if [[ "$AUTH_NEGATIVE" == 1 && ( "$AUTO_ROUTE" != 1 || "$HANDOVER" != 1 || "$MODE" != game2 ) ]];then
  echo "auth negative real test requires auto-route Game2 with A2" >&2;exit 2
fi
if [[ "$AUTO_ROUTE" != 0 && "$AUTO_ROUTE" != 1 ]];then echo "invalid pre-ClientHello route source" >&2;exit 2;fi
PHYSICAL_SWITCH="${WBD_PLAN028_GAME_MULTI_PHYSICAL_SWITCH:-0}"
if [[ "$PHYSICAL_SWITCH" != 0 && "$PHYSICAL_SWITCH" != 1 ]];then echo "invalid physical source4 selector" >&2;exit 2;fi
DEAD90="${WBD_PLAN028_GAME_MULTI_DEAD90:-0}"
if [[ "$DEAD90" != 0 && "$DEAD90" != 1 ]];then echo "invalid Health90 selector" >&2;exit 2;fi
if [[ "$HANDOVER" != 0 && "$HANDOVER" != 1 ]];then echo "invalid Game handover selector" >&2; exit 2;fi
case "$GAME_FEC" in
  off) ;;
  fixed6) [[ "$MODE" == game4 ]] || { echo "fixed6 proof is Game4 only" >&2; exit 2; } ;;
  *) echo "invalid Game multi-cohort FEC: $GAME_FEC" >&2; exit 2 ;;
esac
case "$MODE" in
  game2) LANES=2 ;;
  game4) LANES=4 ;;
  *) echo "PLAN028 two-group real native only supports game2/game4" >&2;exit 2 ;;
esac
if [[ "$DEAD90" == 1 && ( "$MODE" != game2 || "$HANDOVER" != 0 || "$GAME_FEC" != off ) ]];then
  echo "natural Health90 requires Game2 two cohorts, no A2 or FEC" >&2;exit 2
fi
if [[ "$PHYSICAL_SWITCH" == 1 && ( "$MODE" != game4 || "$GAME_FEC" != fixed6 || "$HANDOVER" != 0 || "$DEAD90" != 0 ) ]];then
 echo "Game4 FEC6 physical switch is one protected two-group scenario" >&2;exit 2
fi
ROOT="$(realpath "${1:?fixed-build source directory}")"
test -x "$ROOT/wbd-v4-client" && test -x "$ROOT/wbd-v4-server"
test -s "$ROOT/libwbd_engine.so" && test -c /dev/net/tun
: "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}"
TAG="${GITHUB_RUN_ID: -7}"
NSS="vgsv$TAG"; NSA="vgca$TAG"; NSB="vgcb$TAG"; NSR="vgcr$TAG"
BR="vgb$TAG"; RS="vgs$TAG"; RA="vga$TAG"; RB="vgc$TAG"; RR="vgr$TAG"
TMP="$RUNNER_TEMP/plan028-game-groups-$TAG"
mkdir -m 0700 -p "$TMP"
PIDS=()
cleanup(){
  code=$?
  set +e
  if ((code));then
    echo "PLAN028_GAME_MULTIGROUP_NATIVE_FAIL code=$code" >&2
    for f in server.log A.log B.log R.log echo.log a_echo.log b_echo.log b_after.log r_echo.log r_b_echo.log denied-wrong_password.log denied-untrusted_cert.log;do
      if [[ -f "$TMP/$f" ]];then
        echo "=== $f ===" >&2;tail -60 "$TMP/$f" >&2
      fi
    done
  fi
  for p in "${PIDS[@]}";do sudo -n kill -TERM "$p" 2>/dev/null || true;done
  for p in "$RS" "$RA" "$RB" "$RR" "$BR";do sudo -n ip link del "$p" 2>/dev/null || true;done
  for n in "$NSS" "$NSA" "$NSB" "$NSR";do sudo -n ip netns del "$n" 2>/dev/null || true;done
  rm -rf "$TMP"
}
trap cleanup EXIT
for ns in "$NSS" "$NSA" "$NSB" "$NSR";do
  sudo -n ip netns add "$ns"
  sudo -n ip -n "$ns" link set lo up
done
sudo -n ip link add "$BR" type bridge
sudo -n ip link set "$BR" up
for def in "$RS wbdvs0 $NSS 10.25.0.1/24" "$RA wbdva0 $NSA 10.25.0.2/24" "$RB wbdvb0 $NSB 10.25.0.3/24" "$RR wbdvr0 $NSR 10.25.0.4/24";do
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
env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-server" --init-route-key-file "$TMP/route-key.hex"
ROUTE_ARG="--route-key-hex-file '$TMP/route-key.hex'"
# AUTO_ROUTE kept only as a scenario selector, no ephemeral pre-TLS exchange.
sudo -n ip netns exec "$NSS" bash -c "
 echo \$\$ > '$TMP/server.pid'
 exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
  --raw-interface wbdvs0 --local-ip 10.25.0.1 --local-port 443 \
  --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
  --server-name wbd-v4.example.test $ROUTE_ARG \
  --users-file '$TMP/users.json' --lease-pool 10.66.0.128/25 \
  --tls-cert '$TMP/cert.pem' --tls-key '$TMP/key.pem' --mode "$MODE" --game-fec "$GAME_FEC"
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
  for _ in range(600):
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
  exec env LD_LIBRARY_PATH='$ROOT' SSL_CERT_FILE='$TMP/cert.pem' '$ROOT/wbd-v4-client' \
   --raw-interface '$raw' --local-ip '$ip' --local-port '$port' \
   --peer-ip 10.25.0.1 --peer-port 443 --tun-name '$tun' \
   --server-name wbd-v4.example.test $ROUTE_ARG --tls-ca-pem '$TMP/cert.pem' \
   --username '$user' --password '$password' \
   --auto-ip --installation-id-file '$key' --mode "$MODE" --game-fec "$GAME_FEC"
 " >"$log" 2>&1 &
 PIDS+=("$!")
}
await_group(){
 local log="$1" count="$2"
 for _ in {1..120};do
  if grep -q "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=$LANES" "$log" &&
     [[ "$(grep -c 'V4_PUBLIC_GAME_MULTI_GROUP_READY role=server' "$TMP/server.log" || true)" -ge "$count" ]];then
   return 0
  fi
  sleep .25
 done
 echo "PLAN028 authentic $MODE groups not ready" >&2
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
 sudo -n ip netns exec "$ns" env GAME_DELAY_S="${GAME_DELAY_S:-0}" GAME_SRC="$source" GAME_LABEL="$label" GAME_QTY="$qty" python3 -u -c '
import os,socket,time
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ["GAME_SRC"],0));s.settimeout(10)
label=os.environ["GAME_LABEL"].encode()
print("PLAN028_GAME_APP_CLOCK label=%s started_ns=%d"%(label.decode(),time.time_ns()),flush=True)
for i in range(int(os.environ["GAME_QTY"])):
  m=b"WBD_GAME_GROUP/"+label+b"/"+str(i).encode()
  assert s.sendto(m,("10.66.0.1",45901))==len(m)
  data,peer=s.recvfrom(4096)
  assert data==b"WBD_GAME_ECHO/"+m and peer[0]=="10.66.0.1",(label,i,data,peer)
  if os.environ.get("GAME_DELAY_S"):time.sleep(float(os.environ["GAME_DELAY_S"]))
print("PLAN028_GAME_APP_CLOCK label=%s finished_ns=%d"%(label.decode(),time.time_ns()),flush=True)
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
if [[ "$GAME_FEC" == fixed6 ]];then
  # Real 64-packet UDP from each protected owner, not a fabricated FEC ACK.
  send_udp "$NSA" "$IPA" "GAME4_FEC_A" 64 "$TMP/a_echo.log" &
  fec_a=$!
  send_udp "$NSB" "$IPB" "GAME4_FEC_B" 64 "$TMP/b_echo.log" &
  fec_b=$!
  wait "$fec_a" "$fec_b"
fi
if [[ "$PHYSICAL_SWITCH" == 1 ]];then
  # Game4 fixed6 A and B already authenticated. Bob's continuous genuine
  # inner TUN/UDP must bracket Alice's true kernel source4 route change
  # AND the new TLS/Rust generation READY (not synthetic Go injection).
  ART="${GITHUB_WORKSPACE:?}/fixed-kernel-result"
  mkdir -p "$ART"
  a_old_mtu="$(sudo -n ip -j -n "$NSA" link show wbdva4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  b_old_mtu="$(sudo -n ip -j -n "$NSB" link show wbdvb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  GAME_DELAY_S=.5 send_udp "$NSB" "$IPB" "BOB_GAME4_DURING_A_SOURCE_SWITCH" 32 "$TMP/b_live.log" &
  b_live=$!
  for _ in {1..80};do
    grep -q 'PLAN028_GAME_APP_CLOCK label=BOB_GAME4_DURING_A_SOURCE_SWITCH started_ns=' "$TMP/b_live.log" && break
    sleep .05
  done
  grep -q 'PLAN028_GAME_APP_CLOCK label=BOB_GAME4_DURING_A_SOURCE_SWITCH started_ns=' "$TMP/b_live.log"
  changed_ns="$(date +%s%N)"
  sudo -n ip -n "$NSA" addr add 10.25.0.9/24 dev wbdva0
  sudo -n ip -n "$NSA" link set wbdva0 mtu 1280
  sudo -n ip -n "$NSA" route replace 10.25.0.1/32 dev wbdva0 src 10.25.0.9
  sudo -n ip -j -n "$NSA" route get 10.25.0.1 >"$ART/plan028-game4-os-route.json"
  sudo -n ip -j -n "$NSA" link show wbdva0 >"$ART/plan028-game4-os-link.json"
  done_ready=0
  for _ in {1..140};do
    if grep -q 'V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client source=rtnetlink_os_readback' "$TMP/A.log" &&
       grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1' "$TMP/A.log" &&
       grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/A.log";then
       done_ready=1;break
    fi
    sleep .25
  done
  [[ "$done_ready" == 1 ]] || { echo "native Game4 physical reauth/old exact Stop absent" >&2;exit 1; }
  ready_ns="$(date +%s%N)"
  wait "$b_live"
  grep -q 'PLAN028_GAME_REAL_APP_OK label=BOB_GAME4_DURING_A_SOURCE_SWITCH bytes=32' "$TMP/b_live.log"
  send_udp "$NSA" "$IPA" "A_GAME4_FEC_NEW_REAL_PATH" 64 "$TMP/a_recovered.log"
  a_end_ns="$(date +%s%N)"
  a_new_mtu="$(sudo -n ip -j -n "$NSA" link show wbdva4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  b_new_mtu="$(sudo -n ip -j -n "$NSB" link show wbdvb4 | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["mtu"])')"
  [[ "$a_new_mtu" -ge 576 && "$a_new_mtu" -lt "$a_old_mtu" && "$b_new_mtu" == "$b_old_mtu" ]] ||
     { echo "new physical Game4 budget or sibling TUN MTU mismatch" >&2;exit 1; }
  python3 - "$TMP/A.log" "$TMP/B.log" "$TMP/b_live.log" "$changed_ns" "$ready_ns" "$a_end_ns" "$a_old_mtu" "$a_new_mtu" "$b_old_mtu" "$b_new_mtu" "$ART/plan028-game4-sibling-real-switch.json" <<'PY'
import pathlib,json,re,sys
a,b,c=[pathlib.Path(x).read_text() for x in sys.argv[1:4]]
changed,ready,done=map(int,sys.argv[4:7])
old,new,bo,bn=map(int,sys.argv[7:11])
st=re.search(r'PLAN028_GAME_APP_CLOCK label=BOB_GAME4_DURING_A_SOURCE_SWITCH started_ns=(\d+)',c)
end=re.search(r'PLAN028_GAME_APP_CLOCK label=BOB_GAME4_DURING_A_SOURCE_SWITCH finished_ns=(\d+)',c)
assert st and end and int(st[1])<changed<ready<int(end[1])
leases=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.[0-9]+)/32',a)
assert len(leases)>=2 and len(set(leases))==1,leases
assert a.index('V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2') < a.index('V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1')
assert 'V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6' in a
assert 'V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6' in b
assert changed<ready<done
out={"scope":"NATIVE_LINUX_X86_GAME4_FIXED6_TWO_GROUPS_ALICE_REAL_SOURCE_SWITCH_BOB_CONTINUOUS",
"one_server_port":443,"original_go_tls_rust":True,"per_group_lanes":4,"real_source4_before":"10.25.0.2",
"real_source4_after":"10.25.0.9","outer_ipv4_user_intent":1460,"new_physical_mtu":1280,
"alice_lease_preserved":leases[0],"alice_tun_os_mtu_old":old,"alice_tun_os_mtu_new":new,
"bob_tun_os_mtu_old":bo,"bob_tun_os_mtu_new":bn,"bob_udp_during_switch":32,
"alice_new_udp":64,"new_tls_generation_ready":True,"old_exact_stop":True,
"physical_command_to_ready_ms":round((ready-changed)/1e6,2),
"ready_to_all_64_echo_ms":round((done-ready)/1e6,2),
"notification_to_tls_start_ms":"NOT_MEASURED","auth_to_first_single_packet_ms":"NOT_MEASURED","cpu_p99":"NOT_MEASURED"}
pathlib.Path(sys.argv[11]).write_text(json.dumps(out,indent=2)+"\n")
print("M0_PLAN028_GAME4_FEC6_TWO_GROUPS_REAL_SOURCE4_CHANGE_BOB_CONTINUOUS_PASS",flush=True)
PY
fi
if [[ "$HANDOVER" == 1 ]];then
  # Preserve the original A process PID; the replacement is the same
  # authenticated Alice installation but has a NEW physical TCP tuple.
  cp "$TMP/alice.pid" "$TMP/alice-old.pid"
  start_client "$NSR" wbdvr0 10.25.0.4 wbdvr4 43031 alice game-alice-protected-20261103 "$TMP/install-A" "$TMP/R.log"
  await_group "$TMP/R.log" 3
  IPR="$(read_lease "$TMP/R.log")"
  [[ "$IPR" == "$IPA" ]] || { echo 'Game authenticated successor changed original lease /32' >&2;exit 1; }
  sudo -n ip -n "$NSR" route replace 10.66.0.1/32 dev wbdvr4
  for _ in {1..80};do
    if grep -q 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=same-protected-cohort-new-generation' "$TMP/server.log";then break;fi
    sleep .25
  done
  grep -q 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=same-protected-cohort-new-generation' "$TMP/server.log"
  send_udp "$NSR" "$IPR" "ALICE_NEW_GENERATION" 6 "$TMP/r_echo.log" &
  p_r=$!
  send_udp "$NSB" "$IPB" "BOB_SURVIVES_SUCCESSOR" 6 "$TMP/r_b_echo.log" &
  p_b=$!
  wait "$p_r" "$p_b"
  if [[ "$AUTH_NEGATIVE" == 1 ]];then
    # A2/B remain live. Two real original FakeTCP/TLS negative admissions.
    openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
      -keyout "$TMP/untrusted-key.pem" -out "$TMP/untrusted.pem" \
      -subj '/CN=not-the-WBD-server' >"$TMP/untrusted-create.log" 2>&1
    attempt_denied(){
      local tag="$1" port="$2" trust="$3" password="$4" tun="$5" rc=0
      timeout 30s sudo -n ip netns exec "$NSR" \
        env LD_LIBRARY_PATH="$ROOT" SSL_CERT_FILE="$trust" "$ROOT/wbd-v4-client" \
        --raw-interface wbdvr0 --local-ip 10.25.0.4 --local-port "$port" \
        --peer-ip 10.25.0.1 --peer-port 443 --tun-name "$tun" \
        --server-name wbd-v4.example.test --route-key-hex-file "$TMP/route-key.hex" --tls-ca-pem "$trust" --username alice --password "$password" \
        --auto-ip --installation-id-file "$TMP/install-denied-$tag" --mode game2 \
        >"$TMP/denied-$tag.log" 2>&1 || rc=$?
      [[ "$rc" != 0 && "$rc" != 124 && "$rc" != 137 ]] || {
        echo "$tag not rejected promptly rc=$rc" >&2;exit 1;
      }
      ! grep -q 'V4_ORIGINAL_GO_GAME_NATIVE_READY role=client' "$TMP/denied-$tag.log" || {
        echo "unauthorized $tag entered native Rust owner" >&2;exit 1;
      }
    }
    attempt_denied wrong_password 45031 "$TMP/cert.pem" "NOT-the-alice-password" wbdvn1
    grep -q 'realityfront: admission authentication failed' "$TMP/denied-wrong_password.log"
    attempt_denied untrusted_cert 47031 "$TMP/untrusted.pem" "game-alice-protected-20261103" wbdvn2
    grep -Eq 'x509: certificate signed by unknown authority|certificate signed by unknown authority|tls: failed to verify certificate' "$TMP/denied-untrusted_cert.log"
    [[ "$(grep -c 'V4_PUBLIC_GAME_MULTI_GROUP_READY role=server' "$TMP/server.log" || true)" -eq 3 ]] || {
      echo "unauthorized candidate minted another Game group" >&2;exit 1;
    }
    send_udp "$NSB" "$IPB" "BOB_SURVIVES_INVALID_TLS_AND_PASSWORD" 3 "$TMP/r_b_echo.log"
    send_udp "$NSR" "$IPR" "A2_SURVIVES_INVALID_TLS_AND_PASSWORD" 3 "$TMP/r_echo.log"
    echo "M0_PLAN028_GAME2_AUTO_ROUTE_AUTH_REJECT_NATIVE_PASS wrong_password_no_native=1 untrusted_certificate_no_native=1 valid_A2_B_continuous_udp=1"
  fi
  if [[ "$GAME_FEC" == fixed6 ]];then
    send_udp "$NSR" "$IPR" "GAME4_FEC_A2" 64 "$TMP/r_echo.log" &
    fec_r=$!
    send_udp "$NSB" "$IPB" "GAME4_FEC_B2" 64 "$TMP/r_b_echo.log" &
    fec_b2=$!
    wait "$fec_r" "$fec_b2"
  fi
fi
# Only client A stops. Do not Stop the one server or B's Rust Game owner.
if [[ "$HANDOVER" == 1 ]];then
  sudo -n kill -TERM "$(cat "$TMP/alice-old.pid")"
else
  sudo -n kill -TERM "$(cat "$TMP/alice.pid")"
fi
for _ in {1..80};do
 if grep -q "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=$LANES" "$TMP/A.log";then break;fi
 sleep .25
done
grep -q "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=client lanes=$LANES" "$TMP/A.log"
send_udp "$NSB" "$IPB" "B_AFTER_A_STOP" 6 "$TMP/b_after.log"
if [[ "$DEAD90" == 1 ]];then
  # A really lost, B continuous native original Go TLS/Rust M4 traffic.
  # Observe the existing Rust Health90 terminal state, never synthesize it.
  dead_started="$(date +%s)"
  dead_observed=0
  for tick in {1..25};do
    send_udp "$NSB" "$IPB" "BOB_CONTINUOUS_AFTER_A_LOSS_$tick" 1 "$TMP/b_after.log"
    if grep -q 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=authenticated-rust-game-health90 remaining_flows=2' "$TMP/server.log";then
      dead_observed=1;break
    fi
    sleep 5
  done
  [[ "$dead_observed" == 1 ]] || { echo "original Game M4 did not naturally retire dead A" >&2;exit 1; }
  dead_elapsed="$(( $(date +%s) - dead_started ))"
  ((dead_elapsed >= 85 && dead_elapsed <= 130)) || { echo "Health90 elapsed invalid: $dead_elapsed" >&2;exit 1; }
  [[ "$(grep -c 'reason=authenticated-rust-game-health90' "$TMP/server.log")" -eq 1 ]] || { echo "sibling B retired or duplicate Health90" >&2;exit 1; }
  send_udp "$NSB" "$IPB" "BOB_STILL_ALIVE_AFTER_A_HEALTH90" 4 "$TMP/b_after.log"
  echo "M0_PLAN028_GAME2_AUTHENTICATED_HEALTH90_EXACT_GROUP_RETIRE_NATIVE_PASS one_lost_group=1 remaining_lanes=2 sibling_B_udp_survives=1 seconds=$dead_elapsed"
fi
if [[ "$HANDOVER" == 1 ]];then
  send_udp "$NSR" "$IPR" "A2_AFTER_OLD_A_STOP" 3 "$TMP/r_echo.log"
fi
sudo -n kill -TERM "$(cat "$TMP/bob.pid")"
if [[ "$HANDOVER" == 1 ]];then sudo -n kill -TERM "$(cat "$TMP/alice.pid")";fi
sudo -n kill -TERM "$(cat "$TMP/server.pid")"
expected_server_close=2
if [[ "$DEAD90" == 1 ]];then expected_server_close=1;fi
for _ in {1..80};do
 if [[ "$(grep -c 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log" || true)" -ge "$expected_server_close" ]] &&
    grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log";then break;fi
 sleep .25
done
grep -q 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log"
[[ "$(grep -c 'V4_PUBLIC_GAME_GROUP_STOP_DRAINED reason=server-close' "$TMP/server.log")" -eq "$expected_server_close" ]]
grep -q 'V4_PUBLIC_SHARED_TUN_STOP generation=' "$TMP/server.log"
if [[ "$AUTO_ROUTE" == 1 ]];then
  for who in A B R;do
    ! grep -q 'V4_PUBLIC_ROUTE_PREHELLO' "$TMP/$who.log"
    grep -q "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=$LANES" "$TMP/$who.log"
  done
  ! grep -q 'V4_PUBLIC_ROUTE_PREHELLO' "$TMP/server.log"
  echo "M0_PLAN028_GAME2_PRESHARED_STANDARD_TLS_NO_PRELUDE_NATIVE_PASS same_server_port=443 accounts=2 install_successor=1 verified_server_certificate=1"
fi
if [[ "$GAME_FEC" == fixed6 ]];then
  fec_clients=(A B)
  [[ "$HANDOVER" == 0 ]] || fec_clients+=(R)
  for who in "${fec_clients[@]}";do
    grep -q "V4_PUBLIC_GAME_FEC_APPLIED role=client lanes=4 mode=fixed profile=6" "$TMP/$who.log"
  done
  # A was retired by its precise old generation; B and A2 by server Stop.
  # All three real driver-bound Rust groups must have copied FEC parity.
  python3 - "$TMP/server.log" "$((2+HANDOVER+PHYSICAL_SWITCH))" <<'PY'
import pathlib,re,sys
log=pathlib.Path(sys.argv[1]).read_text()
rows=re.findall(r"V4_PUBLIC_GAME_FEC_COUNTERS role=server lanes=4 source_offered=(\d+) parity_offered=(\d+) parity_copied=(\d+)",log)
assert len(rows)==int(sys.argv[2]),("expected authenticated old/new Game FEC cohorts",rows)
assert all(int(s)>=16 and int(p)>0 and int(k)>0 for s,p,k in rows),rows
print("M0_PLAN028_GAME4_FEC6_TWO_COHORTS_A2_NATIVE_COUNTERS_PASS groups=3 parity_kernel_nonzero=1",flush=True)
PY
fi
echo "M0_PLAN028_GAME_TWO_PROTECTED_ACCOUNTS_ONE_443_ONE_RUST_TUN_NATIVE_PASS groups=2 lanes_each=$LANES verified_leases=2 simultaneous_udp=1 B_survives_A_stop=1 native_stop_drained=1 handover_A_to_A2=$HANDOVER fec_fixed6=$([[ "$GAME_FEC" == fixed6 ]] && echo 1 || echo 0) natural_health90=$DEAD90 preshared_route_key=1 auth_negative=$AUTH_NEGATIVE"
