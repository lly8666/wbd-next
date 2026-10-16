#!/usr/bin/env bash
# SOURCE-LOCKED, opt-in privileged real Linux TUN app first packet.
# This is real /dev/net/tun, not a fake device, and never a production V4 ABI.
set -euo pipefail
usage() {
  echo 'Usage: tools/run-v4-tun-netns.sh PREBUILT_DIR'
  echo 'Requires sudo, iproute2, /dev/net/tun and Linux x86_64 kernel netns CAP_NET_ADMIN.'
}
[[ $# == 1 ]] || { usage >&2; exit 2; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || {
  echo 'TUN_NETNS_UNSUPPORTED target'; exit 77;
}
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LIB_DIR="$(cd -- "$1" && pwd)"
BIN="$LIB_DIR/owner-go.test"
[[ -s "$BIN" && -s "$LIB_DIR/libwbd_engine.so" ]] || {
  echo 'Missing source-locked native Go/Rust binaries' >&2; exit 2;
}
if [[ ! -c /dev/net/tun ]] || ! command -v ip >/dev/null || ! command -v sudo >/dev/null; then
  echo 'TUN_NETNS_UNSUPPORTED /dev/net/tun, iproute2 or sudo missing'; exit 77
fi
NS="wbdm0_${GITHUB_RUN_ID:-$$}"
# Always clean up the namespace; no change to host routes, DNS or devices.
if ! sudo -n ip netns add "$NS"; then
  echo 'TUN_NETNS_UNSUPPORTED kernel refused isolated network namespace'; exit 77
fi
trap 'sudo -n ip netns del "$NS" || true' EXIT
sudo -n ip -n "$NS" link set lo up || {
  echo 'TUN_NETNS_UNSUPPORTED no loopback setup permission'; exit 77;
}
# Original pinned Go faketcp.newAssociationPeer SYN is 10.0.0.2:41001 →
# 10.0.1.1:443, not the former 127.0.0.1 fixed port fixture. Give both
# endpoints isolated kernel-local /32 addresses; no host routing is changed.
sudo -n ip -n "$NS" addr add 10.0.0.2/32 dev lo
sudo -n ip -n "$NS" addr add 10.0.1.1/32 dev lo
# Single explicitly chosen functional-exploration scenario. Do not infer
# RTT from configured delay; require observable kernel qdisc packet counters.
# Default invocation remains byte-for-byte baseline behavior.
PRELIM_MS="${WBD_M0_PRELIM_NETEM_DELAY_MS:-}"
STEADY="${WBD_M0_STEADY_BURST:-}"
BACKGROUND="${WBD_M0_BACKGROUND_LOOP:-}"
PERF="${WBD_M0_PERF_BASELINE:-}"
TARGETED="${WBD_M0_TARGETED_DROP:-}"
if [[ -n "$TARGETED" && "$TARGETED" != 1 ]]; then echo 'TARGETED_DROP_INVALID' >&2; exit 2; fi
LOSS="${WBD_M0_STEADY_LOSS_PERCENT:-}"
if [[ -n "$LOSS" ]]; then
  if [[ "$LOSS" != 1 || "$STEADY" != 1 || -n "$PRELIM_MS" ]]; then
    echo 'STEADY_LOSS_INVALID only 1% in isolated steady burst' >&2; exit 2
  fi
  if ! command -v tc >/dev/null; then
    echo 'STEADY_LOSS_UNSUPPORTED tc unavailable'; exit 77
  fi
  if ! sudo -n ip netns exec "$NS" tc qdisc replace dev lo root netem loss 1% limit 256; then
    echo 'STEADY_LOSS_UNSUPPORTED kernel qdisc refused'; exit 77
  fi
  echo 'STEADY_LOSS_QDISC_ATTACHED loss_percent=1 dev=lo bounded_packets=256'
  sudo -n ip netns exec "$NS" tc -s qdisc show dev lo
fi
if [[ -n "$PRELIM_MS" ]]; then
  if [[ "$PRELIM_MS" != 10 && "$PRELIM_MS" != 150 ]]; then
    echo 'PRELIM_NETEM_INVALID only bounded 10ms/150ms smoke is authorized' >&2
    exit 2
  fi
  if ! command -v tc >/dev/null; then
    echo 'PRELIM_NETEM_UNSUPPORTED tc unavailable'; exit 77
  fi
  if ! sudo -n ip netns exec "$NS" tc qdisc replace dev lo root netem delay "${PRELIM_MS}ms" limit 256; then
    echo 'PRELIM_NETEM_UNSUPPORTED kernel refused netem qdisc'; exit 77
  fi
  echo "PRELIM_NETEM_QDISC_ATTACHED delay_ms=$PRELIM_MS qdisc=netem dev=lo max_packets=256"
  sudo -n ip netns exec "$NS" tc -s qdisc show dev lo
fi
TEST_FILTER='^TestR0V4(NativeRustTunKernelAppFirst|EmbeddedRealM4RawToTun)$'
if [[ -n "$PRELIM_MS" ]]; then TEST_FILTER='^TestR0V4EmbeddedRealM4RawToTun$'; fi
if [[ "$STEADY" == 1 ]]; then TEST_FILTER='^TestR0V4EmbeddedSteadyBurst$'; fi
if [[ "$PERF" == 1 ]]; then
  if [[ -n "$STEADY" || -n "$LOSS" || -n "$PRELIM_MS" || -n "$TARGETED" || -n "$BACKGROUND" ]]; then
    echo 'PERF_INVALID multiple scenarios cannot share one perf runner' >&2; exit 2
  fi
  TEST_FILTER='^TestR0V4EmbeddedNormalOff10MbpsDevelopment$'
fi
if [[ "$BACKGROUND" == 1 ]]; then
  if [[ -n "$STEADY" || -n "$LOSS" || -n "$PRELIM_MS" || -n "$TARGETED" ]]; then
    echo 'BACKGROUND_LOOP_INVALID requires isolated owner functional case' >&2; exit 2
  fi
  TEST_FILTER='^TestR0V4EmbeddedIndependentRustOwnerLoop$'
fi
if [[ "$TARGETED" == 1 ]]; then
  if [[ -n "$STEADY" || -n "$LOSS" || -n "$PRELIM_MS" ]]; then
    echo 'TARGETED_DROP_INVALID independent functional namespace only' >&2; exit 2
  fi
  [[ "$(command -v tc || true)" ]] || { echo 'TARGETED_DROP_UNSUPPORTED tc absent'; exit 77; }
  TEST_FILTER='^TestR0V4EmbeddedKernelSpecificDataLossNoHOL$'
fi
set +e
sudo -n ip netns exec "$NS" env WBD_REAL_TUN=1 WBD_M0_STEADY_BURST="$STEADY" WBD_M0_STEADY_LOSS_PERCENT="$LOSS" WBD_M0_TARGETED_DROP="$TARGETED" WBD_M0_BACKGROUND_LOOP="$BACKGROUND" WBD_M0_PERF_BASELINE="$PERF" WBD_M0_PAIRED_OLD_NEW="$WBD_M0_PAIRED_OLD_NEW" WBD_M0_PERF_RECEIPT="$ROOT/native-probe-result/normal-off-dev-10mbps.json"   LD_LIBRARY_PATH="$LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"   "$BIN" -test.v -test.count=1   -test.run "$TEST_FILTER"
RC=$?
set -e
# The owned netns test runs as root; never let a successful measurement
# become an unauditable GitHub artifact due to the 0600 root-only receipt.
# Change ownership of ONLY the exact declared perf JSON after child exit;
# no private credentials or large traffic body are present in the receipt.
if [[ "$PERF" == 1 && -f "$ROOT/native-probe-result/normal-off-dev-10mbps.json" ]]; then
  sudo -n chown -- "$(id -u):$(id -g)" "$ROOT/native-probe-result/normal-off-dev-10mbps.json"
  chmod 0644 "$ROOT/native-probe-result/normal-off-dev-10mbps.json"
fi
if ((RC!=0)); then
  echo "TUN_APP_FIRST_PACKET_FAIL exit=$RC" >&2; exit "$RC";
fi
if [[ "$PERF" == 1 ]]; then
  [[ -s "$ROOT/native-probe-result/normal-off-dev-10mbps.json" ]] || {
    echo 'PERF_MEASUREMENT_INVALID missing actual Go kernel receipt' >&2; exit 1;
  }
  echo 'ORIGINAL_RUST_NORMAL_OFF_BILATERAL_DEVELOPMENT_MEASUREMENT_RECORDED 10s warmup 60s measurement fixed mix; this is NOT product qualification.'
  exit 0
fi
if [[ "$BACKGROUND" == 1 ]]; then
  echo 'ORIGINAL_RUST_BACKGROUND_OWNER_LOOP_FUNCTIONAL_PASS real independent Linux raw+TUN workers, not a sustained performance benchmark.'
  exit 0
fi
if [[ "$TARGETED" == 1 ]]; then
  echo 'TARGETED_ENCRYPTED_DATA_DROP_CASE_PASS original Go TLS PN0 lost in exact kernel u32 egress classifier; PN1 delivered by original Rust Normal/off to independent real TUN application.'
  exit 0
fi
if [[ "$LOSS" == 1 ]]; then
  QDISC="$(sudo -n ip netns exec "$NS" tc -s qdisc show dev lo)"
  echo "$QDISC"
  if [[ "$QDISC" != *"qdisc netem "* ]] || ! grep -Eq 'Sent [1-9][0-9]* bytes [1-9][0-9]* pkt' <<<"$QDISC"; then
    echo 'STEADY_LOSS_NOT_OBSERVED no actual qdisc processed packets'; exit 77
  fi
  DROPPED="$(sed -nE 's/.*\(dropped ([0-9]+),.*/\1/p' <<<"$QDISC" | head -1)"
  [[ "$DROPPED" =~ ^[0-9]+$ ]] || { echo 'STEADY_LOSS_NOT_OBSERVED drop counter missing'; exit 77; }
  echo "STEADY_LOSS_CASE_RECORDED configured_loss_percent=1 kernel_dropped_packets=$DROPPED observed_drop=$([[ "$DROPPED" -gt 0 ]] && echo yes || echo no)"
  echo 'STEADY_LOSS_LIMITS finite 12p/direction/cipher; no FEC, repair, throughput or product success claim.'
  exit 0
fi
if [[ "$STEADY" == 1 ]]; then
  echo 'STEADY_BURST_BASELINE_PASS same original owner 12 packets/direction/suite with exact app byte and PN/TCP seq.'
  exit 0
fi
if [[ -n "$PRELIM_MS" ]]; then
  QDISC="$(sudo -n ip netns exec "$NS" tc -s qdisc show dev lo)"
  echo "$QDISC"
  if [[ "$QDISC" != *"qdisc netem "* ]] || ! grep -Eq 'Sent [1-9][0-9]* bytes [1-9][0-9]* pkt' <<<"$QDISC"; then
    echo 'PRELIM_NETEM_NOT_OBSERVED kernel qdisc processed no measurable packets; delay NOT_VERIFIED'
    exit 77
  fi
  echo "PRELIM_NETEM_KERNEL_SMOKE_PASS delay_ms=$PRELIM_MS qdisc_packets_positive=true embedded_bilateral_3_ciphers=true"
  echo 'PRELIM_NETEM_LIMITS configured delay is NOT measured RTT; no load/throughput/p99/B04/product qualification.'
  exit 0
fi
echo 'TUN_APP_FIRST_PACKET_PASS: isolated netns actual kernel TUN -> UDP application socket.'
echo 'TUN_APP_BIDIRECTIONAL_PASS: real Go application -> kernel TUN -> Rust scoped AEAD -> M4 UDP -> Go TLS peer.'
echo 'TUN_TO_REAL_RAW_FAKETCP_PASS: real kernel IPv4/TCP raw socket -> Go TLS authenticated peer.'
echo 'REAL_RAW_BIDIRECTIONAL_TUN_PASS: Go raw IPv4/TCP -> Rust M1 AEAD -> real TUN app, plus real raw S2C Go peer.'
echo 'EMBEDDED_REAL_RAW_TO_TUN_APP_PASS: private Go authenticated non-_test adapter -> original Rust owner -> real M4 raw/TUN kernel; single C2S direction only.'
echo 'EMBEDDED_REAL_TUN_TO_RAW_GO_PEER_PASS: same non-test Go embedded Rust owner M4 kernel TUN -> M1/M3 S2C -> real raw TCP to independent Go TLS peer.'
echo 'Original pinned Go SYN remains test generated; driver held async loan, B01-B04, veth netem and product enablement NOT_RUN.'
