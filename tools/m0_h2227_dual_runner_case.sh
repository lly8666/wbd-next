#!/usr/bin/env bash
# H2227 exact-source Linux x86 / ARM64 dual-runner app TCP stress.
# Only private veth WAN netem, never management Tailscale or outer repair.
set -euo pipefail
ROLE="${1:?server-start|server-wait|client-run|cleanup}"
ROOT="$GITHUB_WORKSPACE/linux-plan029-public-bundle"
OUT="$GITHUB_WORKSPACE/h2227-out"
TOOL="$GITHUB_WORKSPACE/tools/m0_h2227_dual_runner_perf.py"
NS=h227peer
mkdir -p "$OUT"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
test -x "$ROOT/wbd-v4-server" && test -x "$ROOT/wbd-v4-client"
test -s "$ROOT/libwbd_engine.so"
: "${GITHUB_RUN_ID:?}" "${RUNNER_TEMP:?}"
TMP="$RUNNER_TEMP/h2227-$GITHUB_RUN_ID"
mkdir -p "$TMP"
printf 'WBD-H2227-CI-ONLY/%s/%s' "$GITHUB_RUN_ID" "$GITHUB_SHA" | sha256sum | cut -d' ' -f1 > "$TMP/route-key.hex"
chmod 600 "$TMP/route-key.hex"
export LD_LIBRARY_PATH="$ROOT:${LD_LIBRARY_PATH:-}"
start_server(){
  test -s h2227-peer/client.json
  python3 "$TOOL" topology server h2227-peer/client.json "$OUT/topology-server.json"
  openssl req -x509 -newkey rsa:2048 -sha256 -days 1 -nodes \
    -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
    -subj '/CN=wbd-h2227.example.test' \
    -addext 'subjectAltName=DNS:wbd-h2227.example.test' >"$OUT/cert-gen.log" 2>&1
  printf '{"perfcheck":"H2227-CI-TEST-ONLY"}\n' > "$TMP/users.json"
  chmod 600 "$TMP/users.json" "$TMP/key.pem"
  sudo -n ip netns exec "$NS" bash -c '
    echo "$$" > "$1";shift
    exec "$@"
  ' bash "$TMP/server.pid" env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-server" \
    --raw-interface wan0 --local-ip 10.247.27.1 --local-port 443 \
    --tun-name wbds0 --tun-ipv4 10.66.0.1/24 \
    --server-name wbd-h2227.example.test --route-key-hex-file "$TMP/route-key.hex" \
    --users-file "$TMP/users.json" --lease-pool 10.66.0.128/25 \
    --tls-cert "$TMP/cert.pem" --tls-key "$TMP/key.pem" \
    --outer-mtu 1160 --mode shared >"$OUT/server.log" 2>&1 &
  echo "$!" > "$TMP/server-sudo.pid"
  for i in $(seq 1 160);do
    if grep -Fq 'V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443' "$OUT/server.log" &&
      sudo -n ip netns exec "$NS" ip link show wbds0 >/dev/null 2>&1;then break;fi
    if ! kill -0 "$(cat "$TMP/server-sudo.pid")" 2>/dev/null;then
      echo H2227_SERVER_EXIT_BEFORE_READY;tail -90 "$OUT/server.log";return 1
    fi
    sleep .25
  done
  grep -Fq 'V4_PUBLIC_MIXED_MULTI_SERVER_READY role=server port=443' "$OUT/server.log"
  sudo -n ip netns exec "$NS" ip link show wbds0 >"$OUT/server-tun.txt"
  sudo -n ip netns exec "$NS" bash -c 'exec iperf3 -s -B 10.247.27.1 -p 5202' \
    >"$OUT/iperf-baseline-server.log" 2>&1 &
  echo "$!" > "$TMP/iperf-baseline.pid"
  sudo -n ip netns exec "$NS" bash -c 'exec iperf3 -s -B 10.66.0.1 -p 5201' \
    >"$OUT/iperf-business-server.log" 2>&1 &
  echo "$!" > "$TMP/iperf-business.pid"
  python3 "$TOOL" server-control h2227-peer/client.json >"$OUT/control.log" 2>&1 &
  echo "$!" > "$TMP/control.pid"
  for i in $(seq 1 35);do
    if sudo -n ip netns exec "$NS" ss -tln |grep -q ':5201 ' &&
      sudo -n ip netns exec "$NS" ss -tln |grep -q ':5202 ' &&
      kill -0 "$(cat "$TMP/control.pid")" 2>/dev/null;then break;fi
    sleep .2
  done
  sudo -n ip netns exec "$NS" ss -tln >"$OUT/server-listeners.txt"
  grep -q ':5201 ' "$OUT/server-listeners.txt"
  grep -q ':5202 ' "$OUT/server-listeners.txt"
  python3 "$TOOL" snapshot server startup "$OUT/server-startup.json"
  echo H2227_TWO_RUNNER_SERVER_REAL_RUST_M4_TUN_IPERF_READY
}
wait_server(){
  set +e
  received=0
  for i in $(seq 1 240);do
    if gh run download "$GITHUB_RUN_ID" -R "$GITHUB_REPOSITORY" \
       -n h2227-client-result -D h2227-client-result >/dev/null 2>&1;then
      received=1;break
    fi
    sleep 5
  done
  set -e
  python3 "$TOOL" snapshot server end "$OUT/server-end.json" || true
  sudo -n ip netns exec "$NS" tc -s qdisc show dev wan0 >"$OUT/server-final-qdisc.txt"
  test "$received" = 1 || { echo H2227_NO_DISTINCT_RUNNER_RESULT;return 2; }
  python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("h2227-client-result/summary.json")
assert p.is_file(),"missing paired client summary"
d=json.loads(p.read_text())
assert d["source_sha"]==os.environ["GITHUB_SHA"]
assert d["run_id"]==os.environ["GITHUB_RUN_ID"]
assert d["server_pair_required"]==True
assert d["classification"]=="REAL_TWO_RUNNER_APPPATH_SCOPED",d["classification"]
print("H2227_PAIR_FULL_SOURCE_LOCKED_PASS_NOT_WINDOWS_ISP")
PY
}
run_client(){
  test -s h2227-peer/server.json
  python3 "$TOOL" topology client h2227-peer/server.json "$OUT/topology-client.json"
  for i in $(seq 1 25);do
    if python3 "$TOOL" remote-health h2227-peer/server.json >"$OUT/control-health.txt" 2>&1;then break;fi
    sleep 2
  done
  python3 "$TOOL" remote-health h2227-peer/server.json >"$OUT/control-health.txt"
  python3 "$TOOL" snapshot client startup "$OUT/client-startup.json"
  local idx=0 local_mode="" loss="" delay=5
  baseline(){
    local label="$1" duration="$2" streams="$3" direction="$4"
    local path="$OUT/case-$(printf '%03d' "$idx")-${label}-${direction}.json"
    idx=$((idx+1))
    python3 "$TOOL" iperf baseline "$duration" "$streams" "$direction" "$path" \
      >"$path.txt" 2>&1 || {
       echo "H2227_OBSERVED_IPERF_BASELINE_FAIL $label $direction" |tee -a "$OUT/failures.log"
      }
  }
  python3 "$TOOL" impair 0 5 >"$OUT/client-qdisc-0.json"
  python3 "$TOOL" remote-impair h2227-peer/server.json 0 5 >"$OUT/server-qdisc-0.json"
  baseline raw-0 12 4 upload
  baseline raw-0 12 4 download
  # Independent A/B: default 600-Mbps TUN fq vs explicit off at 0% loss.
  # This changes only the supported CLI option, NOT outer retransmission.
  for scenario in '0:600' '0:0' '0.1:600' '1:600' '3:600';do
    IFS=':' read -r loss fq <<< "$scenario"
    python3 "$TOOL" impair "$loss" "$delay" >"$OUT/client-qdisc-$loss-fq$fq.json"
    python3 "$TOOL" remote-impair h2227-peer/server.json "$loss" "$delay" >"$OUT/server-qdisc-$loss-fq$fq.json"
    baseline "raw-$loss-fq$fq" 6 4 upload
    baseline "raw-$loss-fq$fq" 6 4 download
    for local_mode in normal fec-fixed;do
      local name="${local_mode}-loss${loss}-fq${fq}"
      sudo -n ip netns exec "$NS" bash -c '
        echo "$$" > "$1";shift
        exec "$@"
      ' bash "$TMP/client.pid" env LD_LIBRARY_PATH="$ROOT" "$ROOT/wbd-v4-client" \
        --raw-interface wan0 --local-ip 10.247.27.2 \
        --local-port "$((44000+idx))" \
        --peer-ip 10.247.27.1 --peer-port 443 \
        --tun-name wbdc0 --server-name wbd-h2227.example.test \
        --route-key-hex-file "$TMP/route-key.hex" \
        --username perfcheck --password H2227-CI-TEST-ONLY --auto-ip \
        --installation-id-file "$TMP/install-${name//./-}" \
        --mode "$local_mode" --fec-profile 6 --outer-repair on \
        --outer-mtu 1160 --tun-fq-maxrate-mbps "$fq" \
        >"$OUT/client-$name.log" 2>&1 &
      local pid=$!
      echo "$pid" >"$TMP/client-sudo.pid"
      local ready=0 lease=""
      for i in $(seq 1 180);do
        if grep -Fq 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$OUT/client-$name.log";then
          lease="$(sed -n 's/.*V4_PUBLIC_LEASE_APPLIED role=client.*os_readback=\([0-9.]*\)\/32.*/\1/p' "$OUT/client-$name.log"|tail -1)"
          if [[ "$lease" == 10.66.0.* ]] && sudo -n ip netns exec "$NS" ip link show wbdc0 >/dev/null 2>&1;then
            ready=1;break
          fi
        fi
        if ! kill -0 "$pid" 2>/dev/null;then break;fi
        sleep .25
      done
      # H2227 correction: source owner prints FEC2_READBACK only AFTER
      # monitorPublicNativePeer returns and authenticated Rust Stop drains.
      # Starting/stopping before the first business packet was a fixture
      # false-fail: DO NOT wait for readback before running iperf3.
      if [[ "$ready" != 1 ]];then
        echo "H2227_REAL_NATIVE_COLD_OR_CRASH_FAIL $name" | tee -a "$OUT/failures.log"
        python3 - "$OUT/case-$(printf '%03d' "$idx")-$name-cold.json" "$name" <<'PY'
import json,sys
json.dump({"status":"ERROR","business_mbps":None,"raw_baseline":False,"error":"NATIVE_COLD_READY_FAILED","mode":sys.argv[2]},open(sys.argv[1],"w"))
PY
        idx=$((idx+1))
      else
        sudo -n ip netns exec "$NS" ip route replace 10.66.0.1/32 dev wbdc0
        python3 "$TOOL" snapshot client "$name-before" "$OUT/$name-before.json"
        ready_count_start="$(grep -c -F 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$OUT/client-$name.log" || true)"
        # 1Hz real process CPU/RSS and owned qdisc live telemetry. No args,
        # secret values, packet payloads, or speculative throughput numbers.
        (
          while kill -0 "$pid" 2>/dev/null;do
            date -u +%Y-%m-%dT%H:%M:%SZ
            sudo -n ip netns exec "$NS" ps -eo pid,ppid,pcpu,rss,stat,comm |
              grep -E '(^[[:space:]]*PID|wbd-v4-|iperf3)' || true
            sudo -n ip netns exec "$NS" tc -s qdisc show dev wan0 || true
            sleep 1
          done
        ) >"$OUT/$name-cpu-rss-qdisc-1hz.log" 2>&1 &
        sampler_pid=$!
        for spec in '3 1 upload' '12 1 upload' '12 1 download' '12 4 upload' '12 4 download';do
          read -r seconds streams direction <<<"$spec"
          path="$OUT/case-$(printf '%03d' "$idx")-$name-${seconds}s-${streams}p-$direction.json"
          idx=$((idx+1))
          python3 "$TOOL" iperf wbd "$seconds" "$streams" "$direction" "$path" --pid "$pid" \
            >"$path.txt" 2>&1 || {
              echo "H2227_REAL_BUSINESS_TCP_FAIL $name $seconds $streams $direction"|tee -a "$OUT/failures.log"
            }
          if ! kill -0 "$pid" 2>/dev/null;then
            echo "H2227_NATIVE_CLIENT_EXIT $name" |tee -a "$OUT/failures.log"
            break
          fi
        done
        kill "$sampler_pid" 2>/dev/null || true
        wait "$sampler_pid" 2>/dev/null || true
        python3 "$TOOL" snapshot client "$name-after" "$OUT/$name-after.json" || true
        ready_count_end="$(grep -c -F 'V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client' "$OUT/client-$name.log" || true)"
        if [[ "$ready_count_start" != "$ready_count_end" ]];then
          echo "H2227_SAME_PID_REAUTH_DURING_TCP $name" |tee -a "$OUT/failures.log"
          python3 - "$OUT/case-$(printf '%03d' "$idx")-$name-reauth.json" <<'PY'
import json,sys
json.dump({"status":"ERROR","business_mbps":None,"raw_baseline":False,
           "error":"SAME_PROCESS_AUTHENTICATED_GENERATION_CHANGED_DURING_TCP"},
          open(sys.argv[1],"w"))
PY
          idx=$((idx+1))
        fi
      fi
      sudo -n kill -TERM "$(cat "$TMP/client.pid")" 2>/dev/null || true
      for i in $(seq 1 45);do
        if ! kill -0 "$pid" 2>/dev/null;then break;fi
        sleep .1
      done
      # Require genuine post-Stop readback from the actual Rust FEC owner,
      # NOT a request flag or a pre-business status. Review all captured
      # iperf TCP results even when the final FEC grade is unproven.
      if [[ "$ready" == 1 && "$local_mode" == "fec-fixed" ]];then
        for j in $(seq 1 80);do
          if grep -q 'V4_PUBLIC_FEC2_READBACK role=client' "$OUT/client-$name.log";then break;fi
          sleep .1
        done
        python3 - "$OUT/client-$name.log" "$OUT/$name-fec6-proof.json" \
          "$OUT/case-$(printf '%03d' "$idx")-$name-fec6-proof.json" <<'PY'
import json,pathlib,re,sys
log=pathlib.Path(sys.argv[1]).read_text(errors="replace")
rows=re.findall(r"V4_PUBLIC_FEC2_READBACK role=client mode=(\w+) requested=(\d+) applied=(\d+) profile=(\d+) pending=(true|false)",log)
# Source has monitor/Stop-only actual grade, so absent is UNKNOWN/FAIL,
# never silently applied. No reconnect or requested grade substitution.
valid=False
if rows:
 mode,req,applied,grade,pending=rows[-1]
 valid=(mode=="fixed" and int(req)>0 and req==applied and
        int(grade)==6 and pending=="false")
result={"status":"PASS_REAL_AUTHENTICATED_RUST_FEC6_APPLIED" if valid
        else "FAIL_NO_REAL_APPLIED_FEC6_READBACK",
        "post_stop_readback":rows[-1] if rows else None,
        "client_log_source":"real original Go TLS Rust native Stop"}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n")
if not valid:
 pathlib.Path(sys.argv[3]).write_text(json.dumps({
  "status":"ERROR","business_mbps":None,"raw_baseline":False,
  "error":"REAL_FEC6_APPLIED_PROOF_MISSING_AFTER_BUSINESS_AND_STOP"})+"\n")
print("H2227_REAL_FEC6_POST_STOP_GRADE "+result["status"],flush=True)
PY
        if [[ -s "$OUT/case-$(printf '%03d' "$idx")-$name-fec6-proof.json" ]];then
          idx=$((idx+1))
          echo "H2227_REAL_FEC6_NOT_APPLIED_AFTER_BUSINESS $name" |tee -a "$OUT/failures.log"
        fi
      fi
      sudo -n kill -KILL "$(cat "$TMP/client.pid")" 2>/dev/null || true
      sudo -n ip netns exec "$NS" ip link show wbdc0 >"$OUT/$name-tun-after.txt" 2>&1 || true
    done
  done
  python3 "$TOOL" summary "$OUT" "$OUT/summary.json" || true
  python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("h2227-out/summary.json")
if not p.exists():
 d={"classification":"FAIL_NO_REAL_MEASUREMENTS","cases":[],"fails":[{"error":"NO_SUMMARY"}]}
else:d=json.loads(p.read_text())
d.update({"source_sha":os.environ["GITHUB_SHA"],
  "run_id":os.environ["GITHUB_RUN_ID"],
  "server_pair_required":True,
  "native_wbd_tls_rust":True,
  "client_arch":"x86_64","server_arch":"aarch64",
  "physical_windows_isp":"NOT_RUN",
  "windows_npcap":"NOT_RUN",
  "retransmission_changed":False,
  "tun_fq_600_vs_0":"0pct_loss_controlled_ab_test",
  "known_driver_constraints":"raw AF_PACKET requires L2 VXLAN over authenticated Tailscale; BBR is kernel TCP only"})
p.write_text(json.dumps(d,indent=2)+"\n")
print("H2227_RESULT "+d["classification"])
PY
}
cleanup(){
  for f in client.pid server.pid iperf-baseline.pid iperf-business.pid control.pid;do
    test ! -s "$TMP/$f" || sudo -n kill -TERM "$(cat "$TMP/$f")" 2>/dev/null || true
  done
  python3 "$TOOL" teardown
}
case "$ROLE" in
  server-start)start_server;;
  server-wait)wait_server;;
  client-run)run_client;;
  cleanup)cleanup;;
  *)echo "H2227_INVALID_ROLE" >&2;exit 2;;
esac
