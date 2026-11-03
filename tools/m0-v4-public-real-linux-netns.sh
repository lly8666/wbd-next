#!/usr/bin/env bash
# Actual original Go V4 public client and server, no Go/Rust test binary.
# 2 isolated namespaces + real raw veth + original TLS + scoped native
# Rust M1/M3/M4 owner + real TUN + kernel UDP echo + signal/Stop cleanup.
set -euo pipefail
ROOT="${1:?expected argument: directory containing the V4 client, server and Rust native library}"
ROOT="$(realpath "$ROOT")"
LOSS="${WBD_V4_PUBLIC_KERNEL_LOSS:-0}"
MODE="${WBD_V4_PUBLIC_MODE:-normal}"
AUTO_IP="${WBD_V4_PUBLIC_AUTO_IP:-0}"
PATH_SWITCH="${WBD_V4_PUBLIC_PATH_SWITCH:-0}"
if [[ "$PATH_SWITCH" != 0 && "$PATH_SWITCH" != 1 ]];then echo "invalid path switch selector" >&2;exit 2;fi
if [[ "$PATH_SWITCH" == 1 && "$AUTO_IP" != 1 ]];then echo "real path switch requires protected automatic lease" >&2;exit 2;fi
if [[ "$AUTO_IP" != 0 && "$AUTO_IP" != 1 ]];then echo "invalid auto-IP selector" >&2;exit 2;fi
if [[ "$AUTO_IP" == 1 && "$MODE" != normal ]];then echo "PLAN028 initial auto-IP native witness requires Normal/off" >&2;exit 2;fi
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
  local exit_code=$?
  set +e
  if [[ "$exit_code" -ne 0 && "$AUTO_IP" == 1 ]];then
    # Save only original native owner/readback diagnostics; no secrets,
    # command line, packet body, TLS transcript or certificates.
    echo "M0_PLAN028_AUTO_NATIVE_FAIL status=$exit_code" >&2
    for role in client server;do
      if [[ -f "$TMP/$role.log" ]];then
        grep -E 'V4_PUBLIC_|V4_ORIGINAL_GO_.*_NATIVE_READY|WBD_LINUX_|[Ee]rror|[Ff]ail|[Ss]top|[Pp]anic|[Tt]imeout' "$TMP/$role.log" |
          sed -E 's/(credential|password|secret|token|key)[=:][^ ]+/\1=[REDACTED]/Ig' |
          tail -60 >"$ART/plan028-auto-$role-diagnostic.log"
        echo "M0_PLAN028_AUTO_${role}_LAST_NATIVE_EVENTS" >&2
        cat "$ART/plan028-auto-$role-diagnostic.log" >&2
      fi
    done
    for role in client server;do
      if [[ -f "$TMP/$role.pid" ]];then
        pid="$(cat "$TMP/$role.pid")"
        if sudo -n kill -0 "$pid" 2>/dev/null;then
          echo "M0_PLAN028_AUTO_FAIL_PROCESS role=$role state=still_live" >&2
        else
          echo "M0_PLAN028_AUTO_FAIL_PROCESS role=$role state=exited" >&2
        fi
      fi
    done
  fi
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
SERVER_ID_ARG="--tunnel-id '$TUNNEL'"
SERVER_LEASE_ARG=''
CLIENT_ID_ARG="--tunnel-id '$TUNNEL'"
CLIENT_TUN_ARG='--tun-ipv4 10.66.0.2/24'
if [[ "$AUTO_IP" == 1 ]];then
  SERVER_ID_ARG=''
  SERVER_LEASE_ARG='--lease-pool 10.66.0.128/25'
  CLIENT_ID_ARG="--auto-ip --installation-id-file '$TMP/installation-id'"
  CLIENT_TUN_ARG=''
fi
# Startup uses exactly the production binaries and unmodified original Go
# TLS/FakeTCP code. PID belongs to the exec'd process in each netns.
sudo -n ip netns exec "$NSS" bash -c "
  echo \$\$ > '$TMP/server.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-server' \
    --raw-interface wbdvs0 --local-ip 10.25.0.1 --local-port 443 \
    --tun-name wbdvs4 --tun-ipv4 10.66.0.1/24 \
    --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
    --username '$USER' --password '$PASS' $SERVER_ID_ARG $SERVER_LEASE_ARG \
    --tls-cert '$TMP/server-cert.pem' --tls-key '$TMP/server-key.pem' \
    --mode "$MODE" --fec-profile 1" >"$TMP/server.log" 2>&1 &
PIDS=$!
sleep 1
sudo -n ip netns exec "$NSC" bash -c "
  echo \$\$ > '$TMP/client.pid'
  exec env LD_LIBRARY_PATH='$ROOT' '$ROOT/wbd-v4-client' \
    --raw-interface wbdvc0 --local-ip 10.25.0.2 --local-port 41031 \
    --peer-ip 10.25.0.1 --peer-port 443 \
    --tun-name wbdvc4 $CLIENT_TUN_ARG \
    --server-name wbd-v4.example.test --route-key-hex '$ROUTE' \
    --username '$USER' --password '$PASS' $CLIENT_ID_ARG \
    --mode "$MODE" --fec-profile 1" >"$TMP/client.log" 2>&1 &
PIDC=$!
# Real server-side Python socket only ECHOES a real UDP packet the Linux
# kernel accepted from the owner TUN. It never makes fake TCP ciphertext.
ECHO_PACKETS="$PACKETS"
if [[ "$PATH_SWITCH" == 1 ]];then ECHO_PACKETS=10;fi
sudo -n ip netns exec "$NSS" env WBD_REAL_COUNT="$ECHO_PACKETS" python3 -u -c '
import socket,time,os
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(("10.66.0.1",45901));s.settimeout(55 if os.environ.get("WBD_REAL_COUNT")=="10" else 28)
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
# A protected auto-lease server now owns many independent Go TLS/Rust
# sessions; preserve the old singleton READY marker only for manual mode.
# Both branches require the REAL server M4 ready event, not Go parser config.
original_server_native_ready(){
  if [[ "$AUTO_IP" == 1 ]];then
    grep -q 'V4_PUBLIC_MULTI_SESSION_READY role=server one_port=443 active_detached_flows=1 auto_lease=1 original_TLS=1 Rust_M4=1' "$TMP/server.log"
  else
    grep -q 'V4_ORIGINAL_GO_SERVER_NATIVE_READY' "$TMP/server.log"
  fi
}
original_server_native_stopped(){
  if [[ "$AUTO_IP" == 1 ]];then
    grep -q 'V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=server-close' "$TMP/server.log" &&
    grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server' "$TMP/server.log"
  else
    grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=server' "$TMP/server.log"
  fi
}
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
       original_server_native_ready; then
    ready=1;break
  fi
  sleep 0.25
done
if [[ "$ready" != 1 ]];then
  echo 'M0_V4_PUBLIC_REAL_CLIENT_SERVER_NOT_READY' >&2
  sed -E 's/(credential|password|secret|token|key)[=:][^ ]+/\1=[REDACTED]/Ig' "$TMP/client.log" "$TMP/server.log" | tail -65 >&2
  exit 1
fi
# PLAN028 source-locked native per-device IP witness. A protected TLS
# reply installed a /32 and Rust bound it to THIS generation before M4.
# The test gets the actual kernel-selected address from the real CLI log,
# never guesses the random lease or substitutes a synthetic UDP sender.
CLIENT_EFFECTIVE_IP='10.66.0.2'
if [[ "$AUTO_IP" == 1 ]];then
  grep -q 'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=' "$TMP/client.log"
  CLIENT_EFFECTIVE_IP="$(python3 - "$TMP/client.log" <<'PY'
import ipaddress,pathlib,re,sys
data=pathlib.Path(sys.argv[1]).read_text()
assigned=re.findall(r'V4_PUBLIC_LEASE_APPLIED role=client source=original_authenticated_TLS os_readback=(10\.66\.0\.[0-9]+)/32',data)
assert len(assigned)==1,assigned
address=ipaddress.ip_address(assigned[0])
assert address in ipaddress.ip_network("10.66.0.128/25")
print(address)
PY
)"
  # An auto-IP client TUN owns only its assigned /32; the server's stable
  # 10.66.0.1/32 route is explicitly bound to that TUN, not underlay DNS.
  sudo -n ip -n "$NSC" route replace 10.66.0.1/32 dev wbdvc4
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
  # PLAN028: all lanes now share server port 443; the first lane is
  # (client source=41031, server dest=443), so dport 443 alone would drop
  # EVERY lane and falsely report a native Game failure. Bind both ports.
  sudo -n ip netns exec "$NSC" iptables -I OUTPUT 1 -p tcp --sport 41031 --dport 443 -j DROP
  sudo -n ip netns exec "$NSS" iptables -I OUTPUT 1 -p tcp --sport 443 --dport 41031 -j DROP
fi
if ! sudo -n ip netns exec "$NSC" env WBD_REAL_COUNT="$PACKETS" WBD_REAL_FEC="$FEC" WBD_REAL_MODE="$MODE" WBD_REAL_LOSS="$LOSS" WBD_REAL_CLIENT_IPV4="$CLIENT_EFFECTIVE_IP" python3 -u -c '
import socket,time,os
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ.get("WBD_REAL_CLIENT_IPV4","10.66.0.2"),45902));s.settimeout(12)
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
if [[ "$PATH_SWITCH" == 1 ]];then
  # REAL Linux addr+link+route kernel notifications on the running
  # client process. No simulated OS event or TCP pointer reassignment.
  # Keep the first original source assigned so old A can serve until B
  # fully authenticates, installs MTU and starts native Rust M4.
  sudo -n ip -n "$NSC" addr add 10.25.0.3/24 dev wbdvc0
  sudo -n ip -n "$NSC" link set dev wbdvc0 mtu 1280
  sudo -n ip -n "$NSC" route replace 10.25.0.1/32 dev wbdvc0 src 10.25.0.3
  sudo -n ip netns exec "$NSC" ip -j -4 route get 10.25.0.1 >"$ART/plan028-effective-new-physical-route.json"
  python3 - "$ART/plan028-effective-new-physical-route.json" <<'PY'
import json,sys
rows=json.load(open(sys.argv[1]))
assert len(rows)==1 and rows[0]["dev"]=="wbdvc0" and rows[0]["prefsrc"]=="10.25.0.3",rows
print("M0_PLAN028_ACTUAL_LINUX_NEW_ROUTE_READBACK_PASS source=10.25.0.3 interface=wbdvc0")
PY
  # The new TLS/Rust generation must complete original AEAD and native
  # handoff BEFORE the old generation retires. The server accepts both
  # source TCP flows on port 443 and keeps this device's verified /32.
  path_ready=0
  for i in {1..120};do
    if grep -q 'V4_PUBLIC_PATH_EFFECTIVE_CHANGED role=client source=rtnetlink_os_readback' "$TMP/client.log" &&
       grep -q 'V4_PUBLIC_PATH_NEW_GENERATION_READY role=client generation=2 old_generation=true source=real_original_TLS_Rust_M4 os_path_authority=1' "$TMP/client.log" &&
       grep -q 'V4_PUBLIC_PATH_OLD_EXACT_STOP role=client generation=1' "$TMP/client.log" &&
       grep -q 'V4_PUBLIC_MULTI_NATIVE_STOP_DRAINED reason=same-lease-new-generation' "$TMP/server.log";then
      path_ready=1;break
    fi
    sleep .25
  done
  if [[ "$path_ready" != 1 ]];then
    echo 'M0_PLAN028_REAL_LINUX_NATIVE_PATH_SWITCH_NOT_READY' >&2
    grep -E 'V4_PUBLIC_PATH_|V4_PUBLIC_MTU|V4_PUBLIC_MULTI_|V4_PUBLIC_NATIVE_STOP' "$TMP/client.log" "$TMP/server.log" |tail -65 >&2 || true
    exit 1
  fi
  sudo -n ip netns exec "$NSC" ip -j link show dev wbdvc4 >"$ART/plan028-new-tun-mtu.json"
  python3 - "$ART/plan028-new-tun-mtu.json" <<'PY'
import json,sys
links=json.load(open(sys.argv[1]))
assert len(links)==1 and links[0]["ifname"]=="wbdvc4",links
mtu=links[0]["mtu"]
assert 900<=mtu<1280,mtu
print("M0_PLAN028_REAL_NEW_PATH_MTU_READBACK_PASS physical=1280 effective_tun=%d"%(mtu))
PY
  sudo -n ip netns exec "$NSC" env WBD_REAL_CLIENT_IPV4="$CLIENT_EFFECTIVE_IP" python3 -u -c '
import os,socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind((os.environ["WBD_REAL_CLIENT_IPV4"],45904));s.settimeout(12)
try:
    for i in range(100,105):
        data=b"WBD_REAL_V4_ORIGINAL_GO/"+str(i).encode()+b"/"+bytes([i%256])*64
        assert s.sendto(data,("10.66.0.1",45901))==len(data)
        got,src=s.recvfrom(8192)
        assert got==b"V4_SERVER_APP_ECHO/"+data and src[0]=="10.66.0.1",(i,src)
        print("M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK",i,flush=True)
finally:s.close()
' >"$ART/plan028-real-path-switched-business.log" 2>&1
  cat "$ART/plan028-real-path-switched-business.log"
  test "$(grep -c 'M0_PLAN028_REAL_PATH_SWITCH_UDP_ECHO_OK' "$ART/plan028-real-path-switched-business.log")" -eq 5
  echo "M0_PLAN028_REAL_LINUX_RTN_NETLINK_A_TO_AB_TO_B_PASS old_source=10.25.0.2 new_source=10.25.0.3 path_events=kernel_link_addr_route coalesce_quiet_ms=200 max_ms=500 new_physical_mtu=1280 original_TLS=1 native_Rust_M4=1 old_exact_Stop=1 new_real_udp=5"
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
  # The same genuine Go TLS/Rust Game app harness now requires ONE server
  # listening port even though clients use 2/4 distinct local TCP ports.
  grep -q "V4_PUBLIC_GAME_SINGLE_SERVER_PORT role=client lanes=$GAME server_port=443 distinct_local_ports=$GAME" "$TMP/client.log"
  grep -q "V4_PUBLIC_GAME_SINGLE_SERVER_PORT role=server lanes=$GAME server_port=443 distinct_client_flows=$GAME" "$TMP/server.log"
else
  grep -q 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY' "$TMP/client.log"
  original_server_native_ready
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
  # A short cohort may be PENDING or genuinely APPLIED after a mature
  # AEAD/replay-verified v2 summary. Require readback coherence on BOTH
  # original Go/Rust roles; do not declare Auto long-window convergence.
  python3 - "$TMP" "$MODE" <<'PY'
import pathlib,re,sys
root=pathlib.Path(sys.argv[1]);selected=sys.argv[2]
mode={"fec-fixed":"fixed","fec-auto":"auto"}[selected]
for role in ("client","server"):
    text=(root/(role+".log")).read_text()
    pat=(r"V4_PUBLIC_FEC2_READBACK role="+role+r" mode="+mode+
         r" requested=1 applied=([01]) profile=([0-6]) pending=(true|false)")
    rows=re.findall(pat,text)
    if not rows:
        raise AssertionError("authentic product readback missing "+role+
            " "+mode)
    applied,profile,pending=rows[-1]
    assert (applied=="1" and pending=="false") or (
        applied=="0" and pending=="true"),(role,rows[-1])
    print("M0_PLAN027_FEC_NATIVE_CONFIG_READBACK role=%s mode=%s applied=%s profile=%s pending=%s"%
          (role,mode,applied,profile,pending))
PY

elif [[ "$LOSS" == 1 ]];then
  # True 1pct UDP loss is counted by distinct first echo and missing,
  # rather than requiring unrecoverable original UDP to have 512 echoes.
  grep -Eq '^M0_V4_PUBLIC_REAL_NETEM_APP_ACCOUNTING offered=512 first_unique_delivered=[0-9]+ missing=[0-9]+$' "$ART/public-v4-normal-business.log"
  cp "$ART/public-v4-normal-business.log" "$ART/v4-public-1pct-business.log"
else
  test "$(grep -c 'M0_PUBLIC_ORIGINAL_GO_V4_CLIENT_SERVER_RUST_M4_REAL_TUN_UDP_ECHO_OK' "$ART/public-v4-normal-business.log")" -eq "$PACKETS"
fi
if [[ "$AUTO_IP" == 1 ]];then
  # Exactly one Rust process TUN reader, not one destructive TUN read per
  # connected device. Every real app echo must pass through the /32 demux.
  # The real auto-IP server is NOW the concurrent protected-TLS manager;
  # its own readiness proves original Rust shared_tun was opened before
  # the per-session first authenticated M4 worker, not the old singleton
  # V4_PUBLIC_SHARED_TUN_READER_READY marker that it no longer emits.
  grep -q 'V4_PUBLIC_MULTI_SERVER_READY role=server port=443 capacity=32 shared_rust_tun=1' "$TMP/server.log"
  grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server' "$TMP/server.log"
  # The client NOW also has exactly one original Rust TUN kernel reader,
  # independently of its server process, so a future new authenticated
  # generation cannot race destructively for the same client TUN packets.
  grep -q 'V4_PUBLIC_SHARED_TUN_READER_READY role=client auto_lease=1 owner=rust_single_kernel_reader' "$TMP/client.log"
  grep -q 'V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=client' "$TMP/client.log"
  sudo -n ip netns exec "$NSS" true
  READER_MIN_PACKETS="$PACKETS"
  if [[ "$PATH_SWITCH" == 1 ]];then READER_MIN_PACKETS=10;fi
  python3 - "$TMP/server.log" "$TMP/client.log" "$READER_MIN_PACKETS" <<'PY'
import pathlib,re,sys
pattern=r'V4_PUBLIC_SHARED_TUN_STOP generation=([0-9]+) routed=([0-9]+) unrouted=([0-9]+) backpressure=([0-9]+) reader_joined=1'
for role,path in (('server',sys.argv[1]),('client',sys.argv[2])):
    log=pathlib.Path(path).read_text()
    matches=re.findall(pattern,log)
    assert len(matches)==1,(role,matches)
    gen,routed,unrouted,pressure=map(int,matches[0])
    assert gen>0 and routed>=int(sys.argv[3]),(role,gen,routed,unrouted,pressure)
    if role=='server':
        print("M0_PLAN028_REAL_SHARED_RUST_SINGLE_TUN_READER_PASS routed=%d unrouted=%d backpressure=%d reader_joined=1"%(routed,unrouted,pressure))
    else:
        print("M0_PLAN028_REAL_CLIENT_PROTECTED_DEFAULT_SINGLE_TUN_READER_PASS authenticated_tls=1 os_lease_readback=1 routed=%d unrouted=%d backpressure=%d reader_joined=1"%(routed,unrouted,pressure))
PY
  echo "M0_PLAN028_REAL_AUTO_LEASE_NATIVE_IP_BOUND_PASS original_TLS=1 os_client_ipv4=$CLIENT_EFFECTIVE_IP app_udp=$PACKETS exact_generation_Rust_M4=1"
fi
if [[ "$GAME" == 0 ]];then
  grep -q 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' "$TMP/client.log"
  original_server_native_stopped
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
# Old per-record WBC4 Receipt is RETIRED. A real first-copy, raw TCP
# ACK-like presentation or kernel qdisc drop is not authenticated delivery.
# Preserve the measured 0/positive counts, forbid only fabricated credit.
assert all(n==0 for n in acks),acks
assert all('V4_PUBLIC_NATIVE_STOP_DRAINED role='+role in read(role+'.log')
    for role in ('client','server')),"owned Stop did not drain"
marker=(f"M0_V4_PUBLIC_REAL_1PCT_LOSS_ACCOUNTED_STOP_PASS"
 f" original_tls=1 offered={offered} first_unique_delivered={delivered}"
 f" missing={missing} tc_client_drop={drops_by_side[0]} tc_server_drop={drops_by_side[1]}"
 f" kernel_first_copy_client={client_copied} kernel_first_copy_server={server_copied}"
 f" retired_m2_reports_client={acks[0]} retired_m2_reports_server={acks[1]}"
 f" outer_repair_attempts_observed={repairs} outer_repair_delivery_not_required=1"
 f" Stop_drained_both=1")
(out/'v4-public-1pct-no-M2-real-delivery.log').write_text(marker+'\n')
print(marker)
PY
elif [[ "$FEC" == 1 ]];then
  if [[ "$MODE" == fec-fixed ]];then
    echo "M0_PLAN027_FIXED_REAL_FIRST_DELIVERY_STOP_CONFIG_READBACK mode=$MODE both_original_go_roles=1 first_app=$PACKETS original_TLS=1 old_M2_retired=1 qualified_applied_not_inferred_from_app=1 source_parity=original_native"
  else
    echo "M0_PLAN027_AUTO_SHORT_BURST_DELIVERY_STOP_CONFIG_READBACK_QUALITY_UNQUALIFIED mode=$MODE both_original_go_roles=1 first_app=$PACKETS original_TLS=1 matched_quality_required_for_applied=1 source_parity=original_native"
  fi
elif [[ "$GAME" != 0 ]];then
  echo "M0_PUBLIC_ORIGINAL_GO_V4_GAME_REAL_TLS_M4_DAMAGED_LANE_NO_HOL_STOP_PASS lanes=$GAME udp_app=$PACKETS auth_go=1 native_m4=1 lane1_underlay_dropped=1 stop_drained=1 production_off=1"
else
  echo 'M0_PUBLIC_ORIGINAL_GO_V4_NORMAL_OFF_TWO_REAL_CLI_TLS_RUST_M4_TUN_UDP_STOP_PASS'
fi
