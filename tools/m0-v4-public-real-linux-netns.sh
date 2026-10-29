#!/usr/bin/env bash
# Actual original Go V4 public client and server, no Go/Rust test binary.
# 2 isolated namespaces + real raw veth + original TLS + scoped native
# Rust M1/M3/M4 owner + real TUN + kernel UDP echo + signal/Stop cleanup.
set -euo pipefail
ROOT="${1:?expected argument: directory containing the V4 client, server and Rust native library}"
ROOT="$(realpath "$ROOT")"
LOSS="${WBD_V4_PUBLIC_KERNEL_LOSS:-0}"
MODE="${WBD_V4_PUBLIC_MODE:-normal}"
case "$MODE" in
  normal|fec-fixed|fec-auto|game2|game4) ;;
  *) echo "V4 public product mode not yet authenticated/installed: $MODE" >&2; exit 2 ;;
esac
FEC=0 GAME=0
case "$MODE" in
  fec-fixed|fec-auto) FEC=1 ;;
  game2) GAME=2 ;;
  game4) GAME=4 ;;
esac
if [[ "$LOSS" != 0 && "$LOSS" != 1 ]];then
  echo "invalid exact public V4 netem loss selector" >&2;exit 2
fi
PACKETS=5
if [[ "$LOSS" == 1 ]];then PACKETS=512;fi
# A single group of actual PUBLIC native FEC2 traffic; keep original
# Normal/off mode and its accepted 512-packet reference unchanged.
if [[ "$FEC" == 1 ]];then
  [[ "$LOSS" == 0 ]] || { echo "FEC2 product mode loss not yet qualified" >&2;exit 2; }
  PACKETS=64
fi
test -x "$ROOT/wbd-v4-client" && test -x "$ROOT/wbd-v4-server"
test -s "$ROOT/libwbd_engine.so" && test -c /dev/net/tun
: "${GITHUB_RUN_ID:?source-locked GitHub Actions only}"
ART="${GITHUB_WORKSPACE:?}/fixed-kernel-result"
TMP="${RUNNER_TEMP:?}/wbd-v4-public-${GITHUB_RUN_ID}"
mkdir -m 0700 -p "$TMP"
NSC="v4cl_${GITHUB_RUN_ID}" NSS="v4sv_${GITHUB_RUN_ID}"
PIDC='' PIDS='' APPS=''
cleanup(){
  set +e
  for p in "$PIDC" "$PIDS" "$APPS"; do
    if [[ -n "$p" ]]; then sudo -n kill -TERM "$p" 2>/dev/null || true; fi
  done
  sleep 0.3
  for ns in "$NSC" "$NSS"; do
    sudo -n ip netns del "$ns" 2>/dev/null || true
  done
  rm -rf "$TMP"
}
trap cleanup EXIT
sudo -n ip netns add "$NSC"
sudo -n ip netns add "$NSS"
sudo -n ip link add wbdvc0 type veth peer name wbdvs0
sudo -n ip link set wbdvc0 netns "$NSC"
sudo -n ip link set wbdvs0 netns "$NSS"
sudo -n ip -n "$NSC" link set lo up
sudo -n ip -n "$NSS" link set lo up
sudo -n ip -n "$NSC" addr add 10.25.0.2/24 dev wbdvc0
sudo -n ip -n "$NSS" addr add 10.25.0.1/24 dev wbdvs0
sudo -n ip -n "$NSC" link set wbdvc0 up
sudo -n ip -n "$NSS" link set wbdvs0 up
sudo -n ip netns exec "$NSC" iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
sudo -n ip netns exec "$NSS" iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
  -keyout "$TMP/server-key.pem" -out "$TMP/server-cert.pem" \
  -subj '/CN=wbd-v4.example.test' -addext 'subjectAltName=DNS:wbd-v4.example.test' \
  >"$TMP/certificate-create.log" 2>&1
chmod 0600 "$TMP/server-key.pem"
ROUTE='aabbccddeeff0011223344556677889900112233445566778899aabbccddeeff'
TUNNEL='102030405060708090a0b0c0d0e0f001'
USER='v4qualified'
PASS='v4-real-original-tls-credential-20261020'
# Startup uses exactly the production binaries and unmodified original Go
# TLS/FakeTCP code. PID belongs to the exec'd process in each netns.
sudo -n ip netns exec "$NSS" bash -c "
  echo \$\$ > '$TMP/server.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
    --raw-interface wbdvs0 --local-ip 10.25.0.1 --local-port 443 \
    --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
    --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
    --username '$USER' --password '$PASS' --tunnel-id '$TUNNEL' \
    --tls-cert '$TMP/server-cert.pem' --tls-key '$TMP/server-key.pem' \
    --mode "$MODE" --fec-profile 1" >"$TMP/server.log" 2>&1 &
PIDS=$!
sleep 1
sudo -n ip netns exec "$NSC" bash -c "
  echo \$\$ > '$TMP/client.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-client' \
    --raw-interface wbdvc0 --local-ip 10.25.0.2 --local-port 41031 \
    --peer-ip 10.25.0.1 --peer-port 443 \
    --tun-name wbdvc4 --tun-ipv4 10.66.0.2/24 \
    --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
    --username '$USER' --password '$PASS' --tunnel-id '$TUNNEL' \
    --mode "$MODE" --fec-profile 1" >"$TMP/client.log" 2>&1 &
PIDC=$!
# Real server-side Python socket only ECHOES a real UDP packet the Linux
# kernel accepted from the owner TUN. It never makes fake TCP ciphertext.
sudo -n ip netns exec "$NSS" env WBD_REAL_COUNT="$PACKETS" python3 -u -c '
import socket,time,os
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.1",45901));s.settimeout(28)
try:
    # Count distinct ORIGINAL UDP payloads, not received retries. The
    # Native outer repair is only opportunistic; duplicate delivery never
    # satisfies the independent application first-unique counter.
    distinct=set()
    target=int(os.environ["WBD_REAL_COUNT"])
    while len(distinct)<target:
        data,src=s.recvfrom(8192)
        assert data.startswith(b"WBD_REAL_V4_ORIGINAL_GO/")
        distinct.add(data)
        s.sendto(b"V4_SERVER_APP_ECHO/"+data,src)
finally:s.close()
' >"$TMP/echo.log" 2>&1 &
APPS=$!
# Allow real original Go TLS and Rust M4 worker start; fail if no actual
# readiness within a bounded time. Never infer readiness from config.
ready=0
for i in {1..40}; do
  if [[ "$GAME" != 0 ]];then
    if grep -q "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=$GAME" "$TMP/client.log" &&
       grep -q "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=$GAME" "$TMP/server.log";then
      ready=1;break
    fi
  elif grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$TMP/client.log" &&
       grep -q 'V4_ORIGINAL_GO_SERVER_NATIVE_READY' "$TMP/server.log"; then
    ready=1;break
  fi
  sleep 0.25
done
if [[ "$ready" != 1 ]];then
  echo 'M0_V4_PUBLIC_REAL_CLIENT_SERVER_NOT_READY' >&2
  sed -E 's/(credential|password|secret|token|key)[=:][^ ]+/\1=[REDACTED]/Ig' "$TMP/client.log" "$TMP/server.log" | tail -65 >&2
  exit 1
fi
# Real LOSS is imposed on the actual Linux underlay AFTER both original
# Go TLS handshakes and both native Rust/M4 driver bindings are READY.
# The exact existing CLI binaries, not an alternative sender, handle it.
if [[ "$LOSS" == 1 ]];then
  sudo -n ip netns exec "$NSC" tc qdisc add dev wbdvc0 root netem loss 1%
  sudo -n ip netns exec "$NSS" tc qdisc add dev wbdvs0 root netem loss 1%
fi
if [[ "$GAME" != 0 ]];then
  # After true Go TLS and Rust M4 device readiness, break exactly the
  # FIRST Game's original TCP carrier in both directions. The second
  # logical UDP app still must arrive over a healthy independent lane.
  sudo -n ip netns exec "$NSC" iptables -I OUTPUT 1 -p tcp --dport 443 -j DROP
  sudo -n ip netns exec "$NSS" iptables -I OUTPUT 1 -p tcp --sport 443 -j DROP
fi
if ! sudo -n ip netns exec "$NSC" env WBD_REAL_COUNT="$PACKETS" WBD_REAL_FEC="$FEC" WBD_REAL_MODE="$MODE" WBD_REAL_LOSS="$LOSS" python3 -u -c '
import socket,time,os
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.2",45902));s.settimeout(12)
count=int(os.environ["WBD_REAL_COUNT"])
fec=os.environ.get("WBD_REAL_FEC")=="1"
loss=os.environ.get("WBD_REAL_LOSS")=="1"
if fec or loss:
    # Under actual kernel netem loss, per-packet UDP stop-and-wait
    # DEADLOCKS on one missing echo and starves all subsequent genuine
    # M2 mature-gap evidence. Use a bounded real application source burst
    # on the very same public Rust transport binaries. No app retries,
    # no fake TCP ACK, no alternate FEC codec and no assumed UDP recovery.
    payloads={}
    for i in range(count):
        msg=(b"WBD_REAL_V4_ORIGINAL_GO/"+str(i).encode()+b"/"+bytes([i%256])*64)
        payloads[msg]=i
        assert s.sendto(msg,("10.66.0.1",45901))==len(msg)
        time.sleep(.003)
    unique=set()
    # Real independent UDP loss is not guaranteed delivery by the outer
    # one-shot repair. Account every offered first source, even missing ones.
    deadline=time.monotonic()+6 if loss else None
    s.settimeout(.5 if loss else 24)
    while len(unique)<count:
        if loss and time.monotonic()>=deadline:break
        try:data,src=s.recvfrom(8192)
        except socket.timeout:
            if loss:continue
            raise
        assert data.startswith(b"V4_SERVER_APP_ECHO/")
        assert src[0]=="10.66.0.1"
        msg=data[len(b"V4_SERVER_APP_ECHO/"):]
        assert msg in payloads,(msg,len(unique))
        index=payloads[msg]
        if index not in unique:
            unique.add(index)
    if loss:
        assert len(unique)>0,"no real first app delivery"
        print("M0_V4_PUBLIC_REAL_NETEM_APP_ACCOUNTING offered="+str(count)+
              " first_unique_delivered="+str(len(unique))+
              " missing="+str(count-len(unique)),flush=True)
    if fec:
        print("M0_PUBLIC_ORIGINAL_GO_V4_FEC2_REAL_GROUP_APP_FIRST_DELIVERY_PASS mode="+os.environ.get("WBD_REAL_MODE","")+" delivered="+str(len(unique)),flush=True)
else:
    for i in range(count):
        msg=(b"WBD_REAL_V4_ORIGINAL_GO/"+str(i).encode()+b"/"+bytes([i%256])*64)
        s.sendto(msg,("10.66.0.1",45901))
        data,src=s.recvfrom(8192)
        assert data==b"V4_SERVER_APP_ECHO/"+msg,(i,data)
        assert src[0]=="10.66.0.1"
        print("M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK",i,flush=True)
s.close()
' >"$ART/public-v4-normal-business.log" 2>&1;then
  # Failure stays failure. Ask the REAL public processes to Stop so their
  # counters distinguish lost peer ACK, candidate/budget, and kernel TX.
  sudo -n kill -TERM "$(cat "$TMP/client.pid")" 2>/dev/null || true
  sudo -n kill -TERM "$(cat "$TMP/server.pid")" 2>/dev/null || true
  sleep 0.5
  {
    echo 'M0_V4_PUBLIC_KERNEL_NETEM_GENUINE_FAILURE'
    tail -5 "$ART/public-v4-normal-business.log"
    for role in client server;do
      echo "Original native $role readiness / M2 / Stop"
      grep -E 'V4_PUBLIC_M2_OUTER|V4_PUBLIC_NATIVE_STOP|V4_ORIGINAL_GO_.*_NATIVE_READY|V4_PUBLIC_GAME_KERNEL|V4_PUBLIC_GAME_NATIVE_STOP' "$TMP/$role.log" || true
    done
    if [[ "$GAME" != 0 ]];then
      echo "M0_GAME_APP_TIMED_OUT_DIAG mode=$MODE lane1_drop_rule_bytes:"
      sudo -n ip netns exec "$NSC" iptables -nvL OUTPUT | head -12 || true
      sudo -n ip netns exec "$NSS" iptables -nvL OUTPUT | head -12 || true
      echo "M0_GAME_AUTH_NATIVE_FINAL_SERVER_UDP_RECEIPT"
      tail -8 "$TMP/echo.log" || true
      for role in client server;do
        echo "M0_GAME_${role}_NATIVE_LAST_EVENTS"
        sed -E 's/(credential|password|secret|token|key)[=:][^ ]+/\1=[REDACTED]/Ig' "$TMP/$role.log" | tail -20 || true
      done
    fi
    if [[ "$LOSS" == 1 ]];then
      sudo -n ip netns exec "$NSC" tc -s qdisc show dev wbdvc0 || true
      sudo -n ip netns exec "$NSS" tc -s qdisc show dev wbdvs0 || true
    fi
  } | tee "$ART/v4-public-1pct-failure-diagnostics.log" >&2
  exit 1
fi
if [[ "$PACKETS" == 5 || "$FEC" == 1 ]];then cat "$ART/public-v4-normal-business.log";fi
if [[ "$GAME" != 0 ]];then
  echo "M0_GAME_PUBLIC_ORIGINAL_GO_M4_FIRST_APP_WITH_LANE1_DAMAGE_PASS lanes=$GAME udp=$PACKETS first_real_app=1 healthy_lane_no_hol=1"
fi
if [[ "$FEC" == 1 ]];then
  # Go policy monitor refuses premature APPLIED; wait for real ORIGINAL
  # 2s authentic M2 maturity + the following 2s Go policy decision turn.
  # Rust still requires M4 copied source/parity and genuine reverse receipt.
  sleep 5
fi
# Confirm clean signal-to-actual-Rust-Stop; no test-only positive receipt.
sudo -n kill -TERM "$(cat "$TMP/client.pid")"
sudo -n kill -TERM "$(cat "$TMP/server.pid")"
for i in {1..25};do
  if ! sudo -n kill -0 "$(cat "$TMP/client.pid")" 2>/dev/null &&
     ! sudo -n kill -0 "$(cat "$TMP/server.pid")" 2>/dev/null;then break;fi
  sleep 0.2
done
if sudo -n kill -0 "$(cat "$TMP/client.pid")" 2>/dev/null ||
   sudo -n kill -0 "$(cat "$TMP/server.pid")" 2>/dev/null;then
  echo 'M0_V4_REAL_RUST_STOP_JOIN_NOT_COMPLETE' >&2;exit 1
fi
# Sensitive logs contain NO TLS secret/cold/exporter keys. Persist only the
# exact readiness and packet count; erase ephemeral TLS files and logs.
if [[ "$GAME" != 0 ]];then
  grep -q "V4_ORIGINAL_GO_GAME_NATIVE_READY role=client lanes=$GAME" "$TMP/client.log"
  grep -q "V4_ORIGINAL_GO_GAME_NATIVE_READY role=server lanes=$GAME" "$TMP/server.log"
else
  grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$TMP/client.log"
  grep -q 'V4_ORIGINAL_GO_SERVER_NATIVE_READY' "$TMP/server.log"
fi
if [[ "$GAME" != 0 ]];then
  test "$(grep -c 'M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK' "$ART/public-v4-normal-business.log")" -eq "$PACKETS"
  for role in client server;do
    grep -q "V4_PUBLIC_GAME_NATIVE_STOP_DRAINED role=$role lanes=$GAME" "$TMP/$role.log"
    grep -q "V4_PUBLIC_GAME_KERNEL role=$role lanes=$GAME" "$TMP/$role.log"
  done
  python3 - "$TMP" "$GAME" <<'PY'
import pathlib,re,sys
p=pathlib.Path(sys.argv[1]);n=int(sys.argv[2])
for role in ("client","server"):
    data=(p/(role+".log")).read_text()
    matches=re.findall(r"V4_PUBLIC_GAME_KERNEL role="+role+
        r" lanes="+str(n)+r" copied=(\d+) delivered=(\d+) rejected=(\d+)",data)
    assert matches and int(matches[-1][0])>=5 and int(matches[-1][1])>=5,        (role,matches)
PY
elif [[ "$FEC" == 1 ]];then
  grep -q "M0_PUBLIC_ORIGINAL_GO_V4_FEC2_REAL_GROUP_APP_FIRST_DELIVERY_PASS mode=$MODE delivered=$PACKETS" "$ART/public-v4-normal-business.log"
  for role in client server;do
    if [[ "$MODE" == fec-fixed ]];then
      # Historical Fixed gate still requires the old mature receipt witness.
      # PLAN027 has not retired this production dependency yet.
      expected="V4_PUBLIC_FEC2_READBACK role=$role mode=fixed requested=1 applied=1 profile=[0-6] pending=false"
    else
      # A 64-record Auto burst cannot fill the new 1024-PN sender window.
      # No CLOSE/mature matched Quality is guaranteed: pending is correct,
      # not a product failure and never evidence of an applied Auto policy.
      expected="V4_PUBLIC_FEC2_READBACK role=$role mode=auto requested=1 applied=[01] profile=[0-6] pending=(true|false)"
    fi
    if ! grep -Eq "$expected" "$TMP/$role.log";then
      echo "M0_PUBLIC_V4_FEC2_READBACK_MISSING role=$role mode=$MODE" >&2
      grep -E 'V4_PUBLIC_FEC2_READBACK|V4_PUBLIC_M2_OUTER|V4_PUBLIC_NATIVE_STOP' "$TMP/$role.log" >&2 || true
      exit 1
    fi
  done
elif [[ "$LOSS" == 1 ]];then
  # True 1pct UDP loss is counted by distinct first echo and missing,
  # rather than requiring unrecoverable original UDP to have 512 echoes.
  grep -Eq '^M0_V4_PUBLIC_REAL_NETEM_APP_ACCOUNTING offered=512 first_unique_delivered=[0-9]+ missing=[0-9]+$' "$ART/public-v4-normal-business.log"
  cp "$ART/public-v4-normal-business.log" "$ART/v4-public-1pct-business.log"
else
  test "$(grep -c 'M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK' "$ART/public-v4-normal-business.log")" -eq "$PACKETS"
fi
if [[ "$GAME" == 0 ]];then
  grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/client.log"
  grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=server' "$TMP/server.log"
fi
if [[ "$LOSS" == 1 ]];then
  sudo -n ip netns exec "$NSC" tc -s qdisc show dev wbdvc0 >"$TMP/kernel-client-netem.txt"
  sudo -n ip netns exec "$NSS" tc -s qdisc show dev wbdvs0 >"$TMP/kernel-server-netem.txt"
  python3 - "$TMP" "$ART" <<'PY'
import pathlib,re,sys
p=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2])
def read(name):return (p/name).read_text()
# Genuine first app UDP underlay loss: all 512 offered stay in denominator,
# including datagrams no opportunistic outer repair could possibly recover.
app=(out/'public-v4-normal-business.log').read_text()
m=re.search(r'M0_V4_PUBLIC_REAL_NETEM_APP_ACCOUNTING offered=(\d+) first_unique_delivered=(\d+) missing=(\d+)',app)
assert m,"no application source/delivery denominator"
offered,delivered,missing=map(int,m.groups())
assert offered==512 and 0<delivered<=offered and missing==offered-delivered,(offered,delivered,missing)
drops_by_side=[sum(map(int,re.findall(r'dropped (\d+)',read(n)))) for n in
    ('kernel-client-netem.txt','kernel-server-netem.txt')]
assert all(n>0 for n in drops_by_side),f"bidirectional netem not evidenced: {drops_by_side}"
def counter(role,key):
    values=re.findall(r'\b'+re.escape(key)+r'=(\d+)',read(role+'.log'))
    assert values,(role,key)
    return int(values[-1])
client_copied=counter('client','real_first_copy')
server_copied=counter('server','real_first_copy')
acks=[counter(role,'authenticated_ack') for role in ('client','server')]
repairs=sum(counter(role,'original_frozen_retransmitted') for role in ('client','server'))
# A genuinely lost C2S source never generated a server echo; requiring
# >=1024 total driver first-copies was the old false no-loss assumption.
assert client_copied>=offered,(client_copied,offered)
assert server_copied>=delivered,(server_copied,delivered)
assert all(n>0 for n in acks),acks
assert all('V4_PUBLIC_NATIVE_STOP_DRAINED role='+role in read(role+'.log')
    for role in ('client','server')),"owned Stop did not drain"
marker=(f"M0_V4_PUBLIC_REAL_1PCT_LOSS_ACCOUNTED_STOP_PASS"
 f" original_tls=1 offered={offered} first_unique_delivered={delivered}"
 f" missing={missing} tc_client_drop={drops_by_side[0]} tc_server_drop={drops_by_side[1]}"
 f" kernel_first_copy_client={client_copied} kernel_first_copy_server={server_copied}"
 f" authenticated_m2_acks_client={acks[0]} authenticated_m2_acks_server={acks[1]}"
 f" outer_repair_attempts_observed={repairs} outer_repair_delivery_not_required=1"
 f" Stop_drained_both=1")
(out/'v4-public-1pct-authentic-M2-recovery.log').write_text(marker+'\n')
print(marker)
PY
elif [[ "$FEC" == 1 ]];then
  if [[ "$MODE" == fec-fixed ]];then
    echo "M0_PUBLIC_ORIGINAL_GO_V4_FEC2_APPLIED_REAL_AUTH_M2_GROUP_M4_TUN_STOP_PASS mode=$MODE both_original_go_roles=1 first_app=$PACKETS original_TLS=1 M2_mature=1 source_parity=original_native FEC2_production_off=1"
  else
    echo "M0_PLAN027_AUTO_SHORT_BURST_DELIVERY_STOP_PENDING_QUALITY_NOT_QUALIFIED mode=$MODE both_original_go_roles=1 first_app=$PACKETS original_TLS=1 matched_quality_required_for_applied=1 source_parity=original_native"
  fi
elif [[ "$GAME" != 0 ]];then
  echo "M0_PUBLIC_ORIGINAL_GO_V4_GAME_REAL_TLS_M4_DAMAGED_LANE_NO_HOL_STOP_PASS lanes=$GAME udp_app=$PACKETS auth_go=1 native_m4=1 lane1_underlay_dropped=1 stop_drained=1 production_off=1"
else
  echo 'M0_PUBLIC_ORIGINAL_GO_V4_NORMAL_OFF_TWO_REAL_CLI_TLS_RUST_M4_TUN_UDP_STOP_PASS'
fi
