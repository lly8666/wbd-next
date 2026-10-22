#!/usr/bin/env bash
# Build an exact-source original-Go V4 Linux ARM64 client+server and Rust owner.
# This is BUILD ONLY: real AF_PACKET/TUN, TLS/app bidirectional and Stop remain NOT_RUN.
set -euo pipefail
: "${GITHUB_SHA:?exact source required}"
: "${GITHUB_WORKSPACE:?Actions workspace required}"
test "$(uname -m)" = aarch64
GO_SOURCE=a7a82db31fe736ffedee330795a3234d358f1984
ISA_SOURCE=c387163fcbca62701d646149564c550c78a4f985
if [ ! -d legacy/.git ]; then
  git clone --quiet https://github.com/lly8666/wobuzhidao.git legacy
fi
git -C legacy checkout -q "$GO_SOURCE"
test "$(git -C legacy rev-parse HEAD)" = "$GO_SOURCE"
if [ ! -d "$RUNNER_TEMP/wbd-isa-l/.git" ]; then
  git clone --quiet https://github.com/intel/isa-l.git "$RUNNER_TEMP/wbd-isa-l"
fi
git -C "$RUNNER_TEMP/wbd-isa-l" checkout -q "$ISA_SOURCE"
test "$(git -C "$RUNNER_TEMP/wbd-isa-l" rev-parse HEAD)" = "$ISA_SOURCE"
export WBD_ISAL_PREFIX="$RUNNER_TEMP/wbd-isal-arm64-public"
export WBD_ISAL_SOURCE_SHA="$ISA_SOURCE"
(cd "$RUNNER_TEMP/wbd-isa-l" && ./autogen.sh &&   ./configure --prefix="$WBD_ISAL_PREFIX" --disable-shared --enable-static &&   make -j2 && make install)
test -s "$WBD_ISAL_PREFIX/lib/libisal.a"
rustup toolchain install 1.85.1 --profile minimal
cargo +1.85.1 build --release --locked -p wbd-engine   --features m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record,native_fec_acceleration
test -s target/release/libwbd_engine.so
files=(
 bridge_v4_linux_server_product.go bridge_v4_linux_client_product.go
 bridge_v4_game_cold_set.go bridge_v4_game_cold_set_test.go
 fec_v2_policy.go fec_v2_policy_test.go
 fec_v2_runtime_controller.go fec_v2_runtime_controller_test.go
 admission_v4.go admission_v4_test.go
 bridge_v4_probe_linux.go bridge_v4_probe_linux_test.go
 bridge_v4_embedded_linux.go bridge_v4_fec2_owner_off_linux.go
 bridge_v4_fec2_owner_probe_linux.go bridge_v4_fec2_release_client_linux.go
 bridge_v4_fec2_public_product_linux.go bridge_v4_fec2_public_mature_linux.go
 bridge_v4_fec2_public_mature_disabled_linux.go
 bridge_v4_fec2_owner_probe_linux_test.go bridge_v4_embedded_linux_test.go
 bridge_v4_embedded_perf_linux_test.go bridge_v4_normal_off_policy_linux.go
 bridge_v4_normal_off_policy_linux_test.go bridge_v4_fixed_pending_linux.go
 bridge_v4_fixed_pending_linux_test.go bridge_v4_live_fec2_kernel_linux_test.go
 bridge_v4_m4_linux_connect_stop_test.go
)
for file in "${files[@]}"; do
  test -f "r0/go_overlay/internal/realityfront/$file"
  cp "r0/go_overlay/internal/realityfront/$file" "legacy/internal/realityfront/$file"
done
mkdir -p legacy/internal/v4productcli legacy/cmd/wbd-v4-client legacy/cmd/wbd-v4-server
cp r0/go_overlay/internal/v4productcli/linux.go legacy/internal/v4productcli/linux.go
cp r0/go_overlay/internal/v4productcli/game_linux.go legacy/internal/v4productcli/game_linux.go
cp r0/go_overlay/internal/v4productcli/game_disabled_linux.go legacy/internal/v4productcli/game_disabled_linux.go
# These three real original-Go product files export the verified grouped Game
# symbols referenced by game_linux.go. Their source is this exact branch SHA.
for file in bridge_v4_game_native_linux.go bridge_v4_linux_game_product.go bridge_v4_linux_public_product.go; do
  cp "r0/go_overlay/internal/realityfront/$file" "legacy/internal/realityfront/$file"
done
cp r0/go_overlay/internal/v4productcli/secret_linux_test.go legacy/internal/v4productcli/secret_linux_test.go
cp r0/go_overlay/cmd/wbd-v4-client/main.go legacy/cmd/wbd-v4-client/main.go
cp r0/go_overlay/cmd/wbd-v4-server/main.go legacy/cmd/wbd-v4-server/main.go
mkdir -p arm64-public-bundle
export CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local
export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/release -lwbd_engine"
export LD_LIBRARY_PATH="$GITHUB_WORKSPACE/target/release:${LD_LIBRARY_PATH:-}"
(cd legacy && go test -tags wbd_v4_embedded_go,wbd_v4_fec2_product ./internal/v4productcli)
(cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product   -o "$GITHUB_WORKSPACE/arm64-public-bundle/wbd-v4-client" ./cmd/wbd-v4-client)
(cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product   -o "$GITHUB_WORKSPACE/arm64-public-bundle/wbd-v4-server" ./cmd/wbd-v4-server)
cp target/release/libwbd_engine.so arm64-public-bundle/libwbd_engine.so
(cd arm64-public-bundle && sha256sum wbd-v4-client wbd-v4-server libwbd_engine.so > SHA256SUMS)
python3 - <<'PY'
import os,json,pathlib,platform
d={"source":os.environ["GITHUB_SHA"],"go_source":"a7a82db31fe736ffedee330795a3234d358f1984",
   "isa_source":"c387163fcbca62701d646149564c550c78a4f985",
   "rust":"1.85.1","go":"1.23.12",
   "architecture":platform.machine(),"backend_requested":"native_fec_acceleration (pinned ISA-L static)",
   "scope":"NATIVE_ARM64_BINARY_BUILD_ONLY",
   "raw_tun_tls_app_stop":"NOT_RUN","android_vpn":"NOT_RUN","openwrt_device":"NOT_RUN"}
pathlib.Path("arm64-public-bundle/manifest.json").write_text(json.dumps(d,indent=2)+"\n")
PY
echo ARM64_PUBLIC_GO_RUST_SOURCE_LOCKED_BUILD_ONLY_PASS
