#!/usr/bin/env bash
# Runnable, developer-only real Linux UDP kernel V4 integration. NOT production V4.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PIN=a7a82db31fe736ffedee330795a3234d358f1984
PREBUILT=""
LEGACY=""
ALL=0
usage() {
  cat <<'HELP'
Usage: tools/run-v4-kernel-loopback.sh [--legacy PATH] [--all]
       tools/run-v4-kernel-loopback.sh --prebuilt DIR [--all]
Reproducible real Go credential-checked V4 TLS, Rust ScopedOwner, Linux
sendmmsg/recvmmsg kernel loopback in BOTH directions, all three cipher suites.
Not a production TUN/raw entrypoint or a product feature-enabled runtime.
--legacy uses local pinned lly8666/wobuzhidao git checkout (not modified).
Otherwise a temporary upstream checkout is fetched. --prebuilt reuses the
source-matched CI binaries without recompiling. --all adds the extended suite.
HELP
}
while (($#)); do
  case "$1" in
    --legacy) (($# >= 2)) || { usage >&2; exit 2; }; LEGACY="$2"; shift 2;;
    --prebuilt) (($# >= 2)) || { usage >&2; exit 2; }; PREBUILT="$2"; shift 2;;
    --all) ALL=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2;;
  esac
done
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]] || {
  echo 'Requires Linux x86_64 glibc.' >&2; exit 2;
}
[[ -z "$PREBUILT" || -z "$LEGACY" ]] || {
  echo 'Choose --prebuilt or --legacy, not both.' >&2; exit 2;
}
OUT="$ROOT/target/m0-v4-kernel-loopback"
mkdir -p "$OUT"
if [[ -n "$PREBUILT" ]]; then
  PREBUILT="$(cd -- "$PREBUILT" && pwd)"
  BIN="$PREBUILT/owner-go.test"
  LIB_DIR="$PREBUILT"
else
  command -v cargo >/dev/null && command -v go >/dev/null &&
    command -v git >/dev/null && command -v nm >/dev/null || {
      echo 'Requires Go 1.23.12, Rust 1.85.1, git, nm, CGO and C compiler.' >&2; exit 2;
    }
  [[ "$(go version | awk '{print $3}')" == go1.23.12 ]] || {
    echo 'Expected pinned Go 1.23.12.' >&2; exit 2;
  }
  [[ "$(rustc --version)" == 'rustc 1.85.1 (4eb161250 2025-03-15)' ]] || {
    echo 'Expected pinned Rust 1.85.1.' >&2; exit 2;
  }
  TMP="$(mktemp -d)"
  trap 'rm -rf -- "$TMP"' EXIT
  mkdir -p "$TMP/legacy"
  if [[ -z "$LEGACY" ]]; then
    git clone -q --filter=blob:none https://github.com/lly8666/wobuzhidao.git "$TMP/upstream"
    LEGACY="$TMP/upstream"
  fi
  git -C "$LEGACY" cat-file -e "$PIN^{commit}" || {
    echo 'Pinned legacy Go commit unavailable.' >&2; exit 2;
  }
  git -C "$LEGACY" archive "$PIN" | tar -x -C "$TMP/legacy"
  cd "$ROOT"
  cargo build --release --locked -p wbd-engine
  if nm -D target/release/libwbd_engine.so | grep -Eq ' wbd_m0_test_probe_'; then
    echo 'CRITICAL: test C symbols leaked into ordinary ABI.' >&2; exit 1;
  fi
  cargo build --release --locked -p wbd-engine --features m0_v4_probe
  for f in admission_v4.go admission_v4_test.go \
      bridge_v4_probe_linux.go bridge_v4_probe_linux_test.go; do
    cp "$ROOT/r0/go_overlay/internal/realityfront/$f" \
      "$TMP/legacy/internal/realityfront/$f"
  done
  BIN="$OUT/owner-go.test"
  (cd "$TMP/legacy"
    CGO_ENABLED=1 CGO_LDFLAGS="-L$ROOT/target/release -lwbd_engine" \
      go test -tags wbd_v4_native_probe -c -o "$BIN" ./internal/realityfront)
  LIB_DIR="$ROOT/target/release"
fi
[[ -s "$BIN" && -s "$LIB_DIR/libwbd_engine.so" ]] || {
  echo 'Native Go executable or Rust library missing.' >&2; exit 1;
}
if ((ALL)); then
  FILTER='^TestR0V4NativeRust(ProbeActualProtectedFreshOwner|ProtectedAEADReplayAllCiphers|ProtectedNormalOffLinkFirstPacket|ProtectedNormalOffBidirectionalScopedFirst|LinuxKernelBudget|LinuxKernelRoutePmtu|M4KernelUdpScopedTxFirstPacket|M4KernelUdpC2SIntoOriginalOwner|GoAdmissionRetainedHeapIndicative)$'
else
  FILTER='^TestR0V4NativeRust(M4KernelUdpScopedTxFirstPacket|M4KernelUdpC2SIntoOriginalOwner)$'
fi
set +e
LD_LIBRARY_PATH="$LIB_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
 "$BIN" -test.v -test.count=1 -test.run "$FILTER" >"$OUT/go.log" 2>&1
CODE=$?
set -e
cat "$OUT/go.log"
if ((CODE)); then
  echo "FAIL: Linux kernel loopback integration, exit $CODE" >&2; exit "$CODE"
fi
for name in M4KernelUdpScopedTxFirstPacket M4KernelUdpC2SIntoOriginalOwner; do
  grep -q -- "--- PASS: TestR0V4NativeRust$name" "$OUT/go.log" || {
    echo "Required real Linux I/O case missing: $name" >&2; exit 1;
  }
done
echo 'PASS: Go protected TLS ⇄ normal Rust ScopedOwner ⇄ actual Linux UDP kernel I/O.'
echo 'NO product V4 enablement, raw/TUN app delivery or driver-held Stop qualification.'
echo "Log: $OUT/go.log"
