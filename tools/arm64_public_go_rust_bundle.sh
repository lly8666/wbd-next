#!/usr/bin/env bash
# One exact-source original-Go TLS/Rust/ISA-L ARM64 native product bundle.
# Keep the ORIGINAL credential Go tree immutable. Include ALL current Go
# overlay files by the SAME source-locked installer/copy rules as the Linux
# x86 production build; a second stale hand-written list is not a release.
# BUILD ONLY: real application delivery, Stop and physical remain NOT_RUN.
set -euo pipefail
: "${GITHUB_SHA:?exact source required}"
: "${GITHUB_WORKSPACE:?Actions workspace required}"
: "${RUNNER_TEMP:?Actions temp required}"
test "$(uname -m)" = aarch64
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
GO_SOURCE=a7a82db31fe736ffedee330795a3234d358f1984
ISA_SOURCE=c387163fcbca62701d646149564c550c78a4f985
if [ ! -d legacy/.git ]; then
  git clone --quiet https://github.com/lly8666/wobuzhidao.git legacy
fi
git -C legacy checkout -q "$GO_SOURCE"
test "$(git -C legacy rev-parse HEAD)" = "$GO_SOURCE"
python3 -m unittest tests.test_m0_install_public_faketcp tests.test_m0_plan028_default_assembly -v
python3 tools/m0_install_public_faketcp.py --check-only
mkdir -p legacy/internal/faketcp legacy/internal/v4productcli legacy/cmd/wbd-v4-client legacy/cmd/wbd-v4-server
# The shared installer applies every pinned original+result FakeTCP blob:
# including H1285 pre-detach protected native M4 overflow and two tests.
python3 tools/m0_install_public_faketcp.py legacy
cp r0/go_overlay/internal/faketcp/raw_detached_data_linux.go legacy/internal/faketcp/
cp r0/go_overlay/internal/faketcp/raw_detached_data_linux_test.go legacy/internal/faketcp/
# Identical to the main Linux x86 original-Go production build:
# exact original TLS blob guard, 2 test collision owners, all named overlays.
python3 tools/m0_install_public_realityfront_tests.py legacy
for f in r0/go_overlay/internal/realityfront/*.go; do
  name="$(basename "$f")"
  case "$name" in
    tls_test.go|wire_qualification_test.go)
      continue ;;
    tls.go)
      test "$(git -C legacy hash-object internal/realityfront/tls.go)" = 518a18104803baf75c703fd8b038f2126beb8d64
      cp "$f" legacy/internal/realityfront/tls.go
      continue ;;
  esac
  dst="legacy/internal/realityfront/$name"
  test ! -e "$dst" || { echo "refusing foreign source collision: $dst" >&2; exit 1; }
  cp "$f" "$dst"
done
cp r0/go_overlay/internal/v4productcli/*.go legacy/internal/v4productcli/
cp r0/go_overlay/cmd/wbd-v4-client/main.go legacy/cmd/wbd-v4-client/
cp r0/go_overlay/cmd/wbd-v4-server/main.go legacy/cmd/wbd-v4-server/
# Original native Go 64/65 transition boundary, malformed hard-denials and
# Game2 stale-cold cross-generation isolation are mandatory, not optional.
(cd legacy && go test -count=1 ./internal/faketcp -run 'TestPLAN028PreDetach|TestStageTransition|TestDetachedDataKernelFilterPreservesHandshakeAndControl')
if [ ! -d "$RUNNER_TEMP/wbd-isa-l/.git" ]; then
  git clone --quiet https://github.com/intel/isa-l.git "$RUNNER_TEMP/wbd-isa-l"
fi
git -C "$RUNNER_TEMP/wbd-isa-l" checkout -q "$ISA_SOURCE"
test "$(git -C "$RUNNER_TEMP/wbd-isa-l" rev-parse HEAD)" = "$ISA_SOURCE"
export WBD_ISAL_PREFIX="$RUNNER_TEMP/wbd-isal-arm64-public"
export WBD_ISAL_SOURCE_SHA="$ISA_SOURCE"
(cd "$RUNNER_TEMP/wbd-isa-l" && ./autogen.sh &&
  ./configure --prefix="$WBD_ISAL_PREFIX" --disable-shared --enable-static &&
  make -j2 && make install)
test -s "$WBD_ISAL_PREFIX/lib/libisal.a"
nm -g "$WBD_ISAL_PREFIX/lib/libisal.a" | grep -Eq ' [TW] ec_encode_data$'
rustup toolchain install 1.85.1 --profile minimal
features=m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record,native_fec_acceleration
cargo +1.85.1 build --release --locked -p wbd-engine --features "$features"
cargo +1.85.1 test --locked -p wbd-engine --features "$features" --lib v4_game_lane::tests
cargo +1.85.1 test --locked -p wbd-engine --features "$features" --lib v4_fec2_live_rx::tests
test -s target/release/libwbd_engine.so
mkdir -p arm64-public-bundle
export CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local
export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/release -lwbd_engine"
export LD_LIBRARY_PATH="$GITHUB_WORKSPACE/target/release:${LD_LIBRARY_PATH:-}"
(cd legacy && go test -count=1 -tags wbd_v4_embedded_go,wbd_v4_fec2_product ./internal/v4productcli)
(cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product -o "$GITHUB_WORKSPACE/arm64-public-bundle/wbd-v4-client" ./cmd/wbd-v4-client)
(cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product -o "$GITHUB_WORKSPACE/arm64-public-bundle/wbd-v4-server" ./cmd/wbd-v4-server)
cp target/release/libwbd_engine.so arm64-public-bundle/libwbd_engine.so
(cd arm64-public-bundle && sha256sum wbd-v4-client wbd-v4-server libwbd_engine.so > SHA256SUMS)
python3 - <<'PY'
import hashlib,json,os,pathlib,platform
p=pathlib.Path("arm64-public-bundle")
names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
hashes={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}
assert all((p/n).stat().st_size>100000 for n in names)
assert platform.machine()=="aarch64"
d={"schema_version":1,"source_sha":os.environ["GITHUB_SHA"],
   "original_go_sha":"a7a82db31fe736ffedee330795a3234d358f1984",
   "isa_l_source":"c387163fcbca62701d646149564c550c78a4f985",
   "rust":"1.85.1","go":"1.23.12",
   "architecture":platform.machine(),"sha256":hashes,
   "rust_native_fec_acceleration":True,
   "original_go_faketcp":"11-source-locked-records",
   "original_go_native_client_and_server":"all-current-v4productcli-overlay-files",
   "native_server_cold_cohort":"exact protected epoch PLUS original adjacent 5tuple",
   "scope":"NATIVE_ARM64_BINARY_BUILD_ONLY",
   "raw_tun_tls_app_stop":"NOT_RUN","android_vpn":"NOT_RUN","openwrt_device":"NOT_RUN"}
p.joinpath("manifest.json").write_text(json.dumps(d,indent=2)+"\n")
print("ARM64_PUBLIC_GO_RUST_SOURCE_LOCKED_BUILD_ONLY_PASS",flush=True)
PY
