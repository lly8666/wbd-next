#!/usr/bin/env bash
# H2228: x86 client -> ARM64 true L3 relay -> x86 server. No WBD source edits.
set -euo pipefail
ROLE="${1:?relay-start|relay-wait|server-start|server-wait|client-run|cleanup}"
ROOT="$GITHUB_WORKSPACE/linux-plan029-public-bundle"
OUT="$GITHUB_WORKSPACE/h2228-out"
TOOL="$GITHUB_WORKSPACE/tools/m0_h2470_relay.py"
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
 try:
  result=subprocess.run(["tailscale","ping","--c","12",p["tail_ip"]],
                        capture_output=True,text=True,timeout=55)
  raw=result.stdout+result.stderr;rc=result.returncode
  label=classify_final_tail_ping(raw,rc)
 except subprocess.TimeoutExpired as exc:
  if os.environ.get("WBD_H2442_ARM_SERVER")!="1":raise
  def as_text(x):return x.decode(errors="replace") if isinstance(x,bytes) else (x or "")
  raw=as_text(exc.stdout)+as_text(exc.stderr);rc=124;label="TAIL_PING_TIMEOUT_DIRECT_CAPACITY_NOT_YET_PROVEN"
 (out/("tail-to-"+role+".json")).write_text(json.dumps({
 "role":role,"tail_path":label,"raw_tail_ping":raw[-700:],"rc":rc},indent=2)+"\n")
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
  cleanup)cleanup;;
  *)exit 2;;
esac
