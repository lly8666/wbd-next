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
set +e
sudo -n ip netns exec "$NS" env WBD_REAL_TUN=1   LD_LIBRARY_PATH="$LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"   "$BIN" -test.v -test.count=1   -test.run '^TestR0V4(NativeRustTunKernelAppFirst|EmbeddedRealM4RawToTun)$'
RC=$?
set -e
if ((RC!=0)); then
  echo "TUN_APP_FIRST_PACKET_FAIL exit=$RC" >&2; exit "$RC";
fi
echo 'TUN_APP_FIRST_PACKET_PASS: isolated netns actual kernel TUN -> UDP application socket.'
echo 'TUN_APP_BIDIRECTIONAL_PASS: real Go application -> kernel TUN -> Rust scoped AEAD -> M4 UDP -> Go TLS peer.'
echo 'TUN_TO_REAL_RAW_FAKETCP_PASS: real kernel IPv4/TCP raw socket -> Go TLS authenticated peer.'
echo 'REAL_RAW_BIDIRECTIONAL_TUN_PASS: Go raw IPv4/TCP -> Rust M1 AEAD -> real TUN app, plus real raw S2C Go peer.'
echo 'EMBEDDED_REAL_RAW_TO_TUN_APP_PASS: private Go authenticated non-_test adapter -> original Rust owner -> real M4 raw/TUN kernel; single C2S direction only.'
echo 'EMBEDDED_REAL_TUN_TO_RAW_GO_PEER_PASS: same non-test Go embedded Rust owner M4 kernel TUN -> M1/M3 S2C -> real raw TCP to independent Go TLS peer.'
echo 'Original pinned Go SYN remains test generated; driver held async loan, B01-B04, veth netem and product enablement NOT_RUN.'
