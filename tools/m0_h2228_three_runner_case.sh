#!/usr/bin/env bash
# H2228: x86 client -> ARM64 true L3 relay -> x86 server. No WBD source edits.
set -euo pipefail
ROLE="${1:?relay-start|relay-wait|server-start|server-wait|client-run|cleanup}"
ROOT="$GITHUB_WORKSPACE/linux-plan029-public-bundle"
OUT="$GITHUB_WORKSPACE/h2228-out"
TOOL="$GITHUB_WORKSPACE/tools/m0_h2228_three_runner_relay.py"
NS=h228node
RT=h228rt
TMP="$RUNNER_TEMP/h2228-$GITHUB_RUN_ID"
mkdir -p "$OUT" "$TMP"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
MODE="${WBD_H2228_MODE:-normal}"
MODEL="${WBD_H2228_LOSS_MODEL:-burst}"
case "$MODE" in normal|fec-fixed) ;; *)exit 2;; esac
case "$MODEL" in iid|burst) ;; *)exit 2;; esac
export LD_LIBRARY_PATH="$ROOT:${LD_LIBRARY_PATH:-}"
secret(){
  printf 'H2228-TEST-ONLY/%s/%s' "$GITHUB_RUN_ID" "$GITHUB_SHA" |
    sha256sum |cut -d' ' -f1 > "$TMP/route-key.hex"
  chmod 600 "$TMP/route-key.hex"
}
spawn(){
  local f="$1";shift
  sudo -n ip netns exec "$NS" bash -c 'echo "$$" > "$1";shift;exec "$@"' bash "$f" "$@" &
}
await_artifact(){
  local name="$1" out="$2" ok=0
  mkdir -p "$out"
  for i in $(seq 1 380);do
    if gh run download "$GITHUB_RUN_ID" -R "$GITHUB_REPOSITORY" \
      -n "$name" -D "$out" >/dev/null 2>&1;then ok=1;break;fi
    sleep 5
  done
  test "$ok" == 1 || { echo "H2228_MISSING_PEER_RECEIPT $name" >&2;return 2; }
}
relay_start(){
  test "$(uname -m)" = aarch64
  test -s h2228-peer/client.json && test -s h2228-peer/server.json
  python3 "$TOOL" relay-net h2228-peer/client.json h2228-peer/server.json "$OUT/relay-topology.json"
  python3 "$TOOL" relay-snapshot cold "$OUT/relay-cold.json"
  python3 - "$OUT" <<'PY'
import json,pathlib,subprocess,sys
from tools.m0_h2228_three_runner_relay import classify_final_tail_ping
out=pathlib.Path(sys.argv[1])
for role in ("client","server"):
 p=json.load(open("h2228-peer/"+role+".json"))
 result=subprocess.run(["tailscale","ping","--c","12",p["tail_ip"]],
                       capture_output=True,text=True,timeout=55)
 raw=result.stdout+result.stderr
 label=classify_final_tail_ping(raw,result.returncode)
 (out/("tail-to-"+role+".json")).write_text(json.dumps({
 "role":role,"tail_path":label,"raw_tail_ping":raw[-700:],"rc":result.returncode},indent=2)+"\n")
PY
  python3 "$TOOL" control-serve h2228-peer/client.json h2228-peer/relay.json >"$OUT/control.log" 2>&1 &
  echo "$!" > "$TMP/control.pid"
  # Ready means a genuinely bound HTTP control socket, not merely a
  # daemon PID started in the background. Old H2228 action failed here.
  control_ready=0
  for i in $(seq 1 50);do
    if kill -0 "$(cat "$TMP/control.pid")" 2>/dev/null &&
       ss -ltn |grep -q ':18727 ';then control_ready=1;break;fi
    sleep .15
  done
  if [[ "$control_ready" != 1 ]];then
    echo "H2228_RELAY_CONTROL_BIND_FAILED tcp18727" >&2
    tail -40 "$OUT/control.log" >&2
    return 2
  fi
  python3 - <<'PY'
import json,os,pathlib
d=json.load(open("h2228-out/relay-topology.json"))
assert d["two_different_L2_segments"] and d["traffic"]=="REAL_IPV4_L3_ROUTING_NO_NAT"
p=pathlib.Path("h2228-out/relay-ready.json")
p.write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
 "arm64_relay_ready":True,"real_separate_layer2_segments":True,
 "netem_owned_router_egress_only":True})+"\n")
PY
  echo H2228_REAL_ARM64_KERNEL_ROUTER_AND_NETEM_READY
}
server_start(){
  test "$(uname -m)" = x86_64
  test -x "$ROOT/wbd-v4-server" && test -s "$ROOT/libwbd_engine.so"
  python3 "$TOOL" node-net server h2228-peer/relay.json "$OUT/server-topology.json"
  secret
  openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
    -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
    -subj '/CN=wbd-h2228.example.test' \
    -addext 'subjectAltName=DNS:wbd-h2228.example.test' >"$OUT/openssl.log" 2>&1
  python3 - "$TMP/users.json" <<'PY'
import json,sys
json.dump({"bench%d"%i:"H2228-ONLY-PASS" for i in range(20)},open(sys.argv[1],"w"))
PY
  chmod 600 "$TMP/key.pem" "$TMP/users.json"
  local -a proxy_args=()
  if [[ "${WBD_H2417_SPLICE:-0}" == 1 ]];then proxy_args=(--tcp-proxy-cc bbr --tcp-proxy-port 46180);fi
  spawn "$TMP/server.pid" env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-server" "${proxy_args[@]}" \
    --raw-interface wan0 --local-ip 10.248.82.2 --local-port 443 \
    --tun-name wbds0 --tun-ipv4 10.66.0.1/24 \
    --server-name wbd-h2228.example.test --route-key-hex-file "$TMP/route-key.hex" \
    --users-file "$TMP/users.json" --lease-pool 10.66.0.128/25 \
    --tls-cert "$TMP/cert.pem" --tls-key "$TMP/key.pem" \
    --outer-mtu 1160 --mode shared >"$OUT/server.log" 2>&1
  echo "$!" >"$TMP/server-launch.pid"
  for i in $(seq 1 160);do
    if grep -Fq 'V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443' "$OUT/server.log";then break;fi
    sleep .25
  done
  grep -Fq 'V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443' "$OUT/server.log"
  if [[ "${WBD_H2417_SPLICE:-0}" == 1 ]];then
    grep -Fq WBD_TCP_SPLICE_READY "$OUT/server.log"
    if [[ -n "${WBD_H2420_ORDER:-}" ]];then bash tools/m0_h2420_splice_clean.sh server "$NS" "$TMP" "$OUT";elif [[ "${WBD_H2418_DIAG:-0}" == 1 ]];then bash tools/m0_h2418_splice_diag.sh server "$NS" "$TMP" "$OUT";else bash tools/m0_h2417_splice_exit.sh server "$NS" "$TMP" "$OUT";fi
  fi
  sudo -n ip netns exec "$NS" iperf3 -s -B 10.248.82.2 -p 5202 >"$OUT/iperf-direct.log" 2>&1 &
  echo "$!" >"$TMP/iperf-direct.pid"
  sudo -n ip netns exec "$NS" iperf3 -s -B 10.66.0.1 -p 5201 >"$OUT/iperf-wbd.log" 2>&1 &
  echo "$!" >"$TMP/iperf-wbd.pid"
  for i in $(seq 1 40);do
    if sudo -n ip netns exec "$NS" ss -ltn |grep -q ':5201 ' &&
       sudo -n ip netns exec "$NS" ss -ltn |grep -q ':5202 ';then break;fi
    sleep .2
  done
  sudo -n ip netns exec "$NS" ss -ltn >"$OUT/listeners.txt"
  grep -q ':5201 ' "$OUT/listeners.txt"
  grep -q ':5202 ' "$OUT/listeners.txt"
  python3 "$TOOL" node-snapshot server startup "$OUT/server-startup.json"
  python3 - <<'PY'
import json,os,pathlib
pathlib.Path("h2228-out/server-ready.json").write_text(json.dumps({
 "source_sha":os.environ["GITHUB_SHA"],"run_id":os.environ["GITHUB_RUN_ID"],
 "real_wbd_server_ready":True,"real_orig_go_rust":True,
 "real_iperf_direct_and_tun":True})+"\n")
PY
  echo H2228_REAL_SERVER_ORIGINAL_RUST_M4_AND_IPERF_READY
}
client_run(){
  test "$(uname -m)" = x86_64
  test -x "$ROOT/wbd-v4-client" && test -s "$ROOT/libwbd_engine.so"
  python3 "$TOOL" node-net client h2228-peer/relay.json "$OUT/client-topology.json"
  secret
  # H2227 already permits tag:ci TCP18727. A new relay may still
  # require a short bounded startup delay: strict HTTP source/token check
  # remains mandatory. Never skip the control preflight.
  relay_http_ready=0
  for i in $(seq 1 5);do
    if python3 "$TOOL" remote h2228-peer/relay.json health "$OUT/relay-health.json"         >"$OUT/relay-health-attempt.log" 2>&1;then relay_http_ready=1;break;fi
    sleep 2
  done
  if [[ "$relay_http_ready" != 1 ]];then
    echo H2228_RELAY_CONTROL_NOT_REACHABLE_REAL_NOT_RUN >&2
    tail -20 "$OUT/relay-health-attempt.log" >&2
    return 2
  fi
  python3 "$TOOL" node-snapshot client startup "$OUT/client-startup.json"
  local count=0
  shape(){
    local label="$1" loss="$2" delay="$3"
    python3 "$TOOL" remote h2228-peer/relay.json impair "$OUT/$label-shaping.json" \
      --loss "$loss" --delay "$delay" --model "$MODEL"
    sleep 1
  }
  relay_read(){
    local label="$1"
    # Keep relay receipt outside case-*.json glob: only genuine iperf
    # case files may count as measurements. Snapshot cannot fake TCP success.
    if [[ "$label" == case-* ]];then label="relay-receipt-$label";fi
    python3 "$TOOL" remote h2228-peer/relay.json snapshot "$OUT/$label-relay.json" || true
  }
  measure(){
    local label="$1" kind="$2" duration="$3" streams="$4" direction="$5"
    local casefile="$OUT/case-$(printf '%03d' "$count")-$label-$kind-${duration}s-${streams}p-$direction.json"
    count=$((count+1))
    local -a owner_check=()
    if [[ "$kind" == "wbd" ]];then
      # Only the root-owned ORIGINAL Go worker PID (not sudo launcher).
      # iperf3 control errors may occur while WBD remains completely alive.
      test -s "$TMP/client.pid" || {
        echo H2228_MISSING_REAL_NATIVE_PID_AT_WBD_MEASURE >&2; return 2;
      }
      owner_check=(--pidfile "$TMP/client.pid")
    fi
    python3 "$TOOL" iperf "$kind" "$duration" "$streams" "$direction" "$casefile" "${owner_check[@]}" \
      > "$casefile.txt" 2>&1 ||
      echo "H2228_OBSERVED_TCP_ERROR $label $kind $direction" |tee -a "$OUT/failures.log"
    relay_read "$(basename "$casefile" .json)"
  }
  # The relay has NO rate cap. Require a real unshaped two-hop reference
  # before interpreting 400ms/high-loss throughput. BBR/rmem same for both.
  shape clear-zero 0 0
  sudo -n ip netns exec "$NS" ping -c 4 -W 3 10.248.82.2 >"$OUT/clear-ping.txt"
  relay_read clear-before
  measure clear-zero direct 12 8 upload
  measure clear-zero direct 12 8 download
  relay_read clear-after
  if [[ "${WBD_H2417_SPLICE:-0}" == 1 ]];then
    if [[ -n "${WBD_H2420_ORDER:-}" ]];then bash tools/m0_h2420_splice_clean.sh client "$NS" "$TMP" "$OUT";elif [[ "${WBD_H2418_DIAG:-0}" == 1 ]];then bash tools/m0_h2418_splice_diag.sh client "$NS" "$TMP" "$OUT";else bash tools/m0_h2417_splice_exit.sh client "$NS" "$TMP" "$OUT";fi
    return
  fi
  local scenario_index=0
  for loss in 0 1 5 10 20;do
    local label="delay200-loss${loss}-${MODEL}"
    shape "$label" "$loss" 200
    relay_read "$label-before"
    # Actual end-to-end RTT; no unsupported '200ms precise wire RTT' claims.
    sudo -n ip netns exec "$NS" ping -n -c 5 -W 3 10.248.82.2       >"$OUT/$label-observed-rtt.txt" 2>&1 || true
    measure "$label" direct 20 4 upload
    measure "$label" direct 20 4 download
    local who="bench${scenario_index}"
    local pidfile="$TMP/client.pid"
    local localport="$((44100+2*scenario_index))"
    scenario_index=$((scenario_index+1))
    rm -f "$pidfile"
    spawn "$pidfile" env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-client" \
      --raw-interface wan0 --local-ip 10.248.81.2 \
      --local-port "$localport" --peer-ip 10.248.82.2 --peer-port 443 \
      --tun-name wbdc0 --server-name wbd-h2228.example.test \
      --route-key-hex-file "$TMP/route-key.hex" \
      --username "$who" --password H2228-ONLY-PASS --auto-ip \
      --installation-id-file "$TMP/install${scenario_index}" \
      --mode "$MODE" --fec-profile 6 --outer-repair on \
      --outer-mtu 1160 --tun-fq-maxrate-mbps 600 \
      >"$OUT/$label-client.log" 2>&1
    local parent=$!
    local ready=0 lease=""
    for i in $(seq 1 170);do
      if grep -Fq 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$OUT/$label-client.log";then
        lease="$(sed -n 's/.*V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=\([0-9.]*\)\/32.*/\1/p' "$OUT/$label-client.log"|tail -1)"
        if [[ "$lease" == 10.66.0.* ]] &&
           sudo -n ip netns exec "$NS" ip link show wbdc0 >/dev/null 2>&1;then ready=1;break;fi
      fi
      # sudo's launcher PID is not the real Go/Rust worker: it can
      # exit/reparent while its root-owned child continues cold TLS.
      # Never send SIGTERM solely because the parent shell job exited.
      if [[ -s "$pidfile" ]];then
        owned_pid="$(cat "$pidfile")"
        if ! sudo -n kill -0 "$owned_pid" 2>/dev/null;then
          echo "H2228_NATIVE_WORKER_EXIT_BEFORE_COLD_READY $label" |tee -a "$OUT/failures.log"
          break
        fi
      fi
      sleep .25
    done
    if [[ "$ready" == 1 ]];then
      sudo -n ip netns exec "$NS" ip route replace 10.66.0.1/32 dev wbdc0
      relay_read "$label-wbd-before"
      measure "$label" wbd 3 1 upload
      measure "$label" wbd 20 4 upload
      measure "$label" wbd 20 4 download
      relay_read "$label-wbd-after"
      if [[ "$(grep -c 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$OUT/$label-client.log" || true)" != 1 ]];then
        echo "H2228_IN_PROCESS_REAUTH $label" |tee -a "$OUT/failures.log"
        python3 - "$OUT/case-$(printf '%03d' "$count")-$label-wbd-reauth.json" <<'PY'
import json,sys
json.dump({"status":"ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE","kind":"wbd",
"mbps":None,"error":"IN_PROCESS_REAUTHENTICATION_DURING_TCP"},open(sys.argv[1],"w"))
PY
        count=$((count+1))
      fi
    else
      echo "H2228_WBD_COLD_READY_FAILED $label" |tee -a "$OUT/failures.log"
      python3 - "$OUT/case-$(printf '%03d' "$count")-$label-wbd-cold.json" <<'PY'
import json,sys
json.dump({"status":"ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE","kind":"wbd",
"mbps":None,"error":"NO_NATIVE_AUTHENTICATED_READY"},open(sys.argv[1],"w"))
PY
      count=$((count+1))
    fi
    if [[ -s "$pidfile" ]];then sudo -n kill -TERM "$(cat "$pidfile")" 2>/dev/null || true;fi
    for i in $(seq 1 80);do
      if [[ -s "$pidfile" ]] && ! sudo -n kill -0 "$(cat "$pidfile")" 2>/dev/null;then break;fi
      sleep .1
    done
    # Rust FEC actual grade is ONLY emitted on Stop; not before first TCP.
    if [[ "$MODE" == "fec-fixed" && "$ready" == 1 ]];then
      if ! python3 - "$OUT/$label-client.log" "$OUT/$label-fec6-applied.json" <<'PY'
import json,re,sys,pathlib
text=pathlib.Path(sys.argv[1]).read_text(errors="replace")
hits=re.findall(r"V4_PUBLIC_FEC2_READBACK role=client mode=(\w+) requested=(\d+) applied=(\d+) profile=(\d+) pending=(true|false)",text)
ok=bool(hits and hits[-1][0]=="fixed" and int(hits[-1][1])>0 and
hits[-1][1]==hits[-1][2] and hits[-1][3]=="6" and hits[-1][4]=="false")
json.dump({"real_rust_post_stop_fec6_applied":ok,
"last_readback":hits[-1] if hits else None},open(sys.argv[2],"w"))
if not ok:raise SystemExit(2)
PY
      then
        echo "H2228_FEC6_UNPROVEN_AFTER_STOP $label" |tee -a "$OUT/failures.log"
        python3 - "$OUT/case-$(printf '%03d' "$count")-$label-wbd-fec6.json" <<'PY'
import json,sys
json.dump({"status":"ERROR_TCP_CRASH_ABORT_OR_UNREACHABLE","kind":"wbd",
"mbps":None,"error":"FEC6_APPLIED_READBACK_UNPROVEN"},open(sys.argv[1],"w"))
PY
        count=$((count+1))
      fi
    fi
    if [[ -s "$pidfile" ]];then sudo -n kill -KILL "$(cat "$pidfile")" 2>/dev/null || true;fi
    sudo -n ip netns exec "$NS" ip link show wbdc0 >"$OUT/$label-tun-after.txt" 2>&1 || true
    relay_read "$label-final"
  done
  python3 "$TOOL" node-snapshot client final "$OUT/client-final.json" || true
  python3 "$TOOL" result "$MODE" "$MODEL" "$OUT" "$OUT/summary.json"
}
wait_pair(){
  await_artifact h2228-client-result h2228-client-result
  python3 - <<'PY'
import json,os
d=json.load(open("h2228-client-result/summary.json"))
assert d["source_sha"]==os.environ["GITHUB_SHA"] and d["run_id"]==os.environ["GITHUB_RUN_ID"]
assert d["real_three_runner_l3_relay"] and d["all_three_distinct_native_machines"]
print("H2228_THREE_NODE_PAIRED_RECEIPT_REAL_NOT_PERFORMANCE_PASS")
PY
}
cleanup(){
  if [[ "${WBD_H2417_SPLICE:-0}" == 1 && "${WBD_H2228_ROLE:-}" == server ]];then
    if [[ -n "${WBD_H2420_ORDER:-}" ]];then bash tools/m0_h2420_splice_clean.sh cleanup "$NS" "$TMP" "$OUT" || true;elif [[ "${WBD_H2418_DIAG:-0}" == 1 ]];then bash tools/m0_h2418_splice_diag.sh cleanup "$NS" "$TMP" "$OUT" || true;else bash tools/m0_h2417_splice_exit.sh cleanup "$NS" "$TMP" "$OUT" || true;fi
  fi
  for f in control.pid client.pid server.pid iperf-direct.pid iperf-wbd.pid;do
    test ! -s "$TMP/$f" || sudo -n kill -TERM "$(cat "$TMP/$f")" 2>/dev/null || true
  done
  python3 "$TOOL" clean "${WBD_H2228_ROLE:?}" || true
}
case "$ROLE" in
  relay-start)relay_start;;
  server-start)server_start;;
  client-run)client_run;;
  relay-wait)wait_pair;python3 "$TOOL" relay-snapshot end "$OUT/relay-end.json" || true;;
  server-wait)wait_pair;python3 "$TOOL" node-snapshot server end "$OUT/server-end.json" || true;;
  cleanup)cleanup;;
  *)exit 2;;
esac
