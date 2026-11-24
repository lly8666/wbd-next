#!/usr/bin/env bash
# PLAN029: same exact-SOURCE genuine Linux x86_64/aarch64 Go TLS+Rust owner.
# Two independent native runner jobs; native ISA only, no QEMU or Windows logic.
# Keep the ORIGINAL credential Go tree immutable. Include ALL current Go
# overlay files by the SAME source-locked installer/copy rules as the Linux
# x86 production build; a second stale hand-written list is not a release.
# BUILD ONLY: real application delivery, Stop and physical remain NOT_RUN.
set -euo pipefail
case "${WBD_LINUX_GLIBC_BUILD_BASELINE:-2.31}" in
  2.31) exec bash tools/m0_linux_glibc231_build.sh ;;
  2.31-inner) test "$(getconf GNU_LIBC_VERSION)" = "glibc 2.31" ;;
  host) ;; # Explicit host baseline for same-SOURCE A/B only.
  *) exit 2 ;;
esac
: "${GITHUB_SHA:?exact source required}"
: "${GITHUB_WORKSPACE:?Actions workspace required}"
: "${RUNNER_TEMP:?Actions temp required}"
case "$(uname -m)" in
  x86_64) GO_ARCH=amd64 ;;
  aarch64) GO_ARCH=arm64 ;;
  *) echo "PLAN029_NATIVE_ISA_REQUIRED" >&2; exit 2 ;;
esac
test "${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}" = "$(uname -m)"
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
# H2212: the original x86/ARM direct-copy product path predates H2208.
# Install the SAME three v4routekey Go blobs as the canonical plan020 manifest;
# a standalone ARM bundle must not omit an imported production Go package.
python3 - <<'PY'
import hashlib,json,pathlib
root=pathlib.Path.cwd()
ops=json.loads((root/"r0/go_overlay/assembly/manifest-plan020-m0.json").read_text())["operations"]
destdir=root/"legacy/internal/v4routekey"
destdir.mkdir(parents=True,exist_ok=True)
for name in ("short.go","short_test.go","cache.go"):
    path="internal/v4routekey/"+name
    row=[o for o in ops if o.get("path")==path]
    assert len(row)==1 and row[0].get("kind")=="create",path
    assert row[0].get("overlay_path")=="r0/go_overlay/"+path,path
    data=(root/row[0]["overlay_path"]).read_bytes()
    actual=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
    assert actual==row[0]["result_blob"],path
    dest=destdir/name
    assert not dest.is_symlink(),path
    if dest.exists(): assert dest.read_bytes()==data,path
    else: dest.write_bytes(data)
print("H2212_ORIGINAL_GO_ROUTEKEY_SAME_MANIFEST_3_FILES_PASS",flush=True)
PY
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
export WBD_ISAL_PREFIX="$RUNNER_TEMP/wbd-isal-plan029-$(uname -m)"
export WBD_ISAL_SOURCE_SHA="$ISA_SOURCE"
(cd "$RUNNER_TEMP/wbd-isa-l" && ./autogen.sh &&
  ./configure --prefix="$WBD_ISAL_PREFIX" --disable-shared --enable-static &&
  make -j2 && make install)
test -s "$WBD_ISAL_PREFIX/lib/libisal.a"
nm -g "$WBD_ISAL_PREFIX/lib/libisal.a" > "$WBD_ISAL_PREFIX/isal-symbols.txt"
grep -E ' [TW] ec_encode_data$' "$WBD_ISAL_PREFIX/isal-symbols.txt"
echo "PLAN029_NATIVE_ISAL_ARCHIVE_SYMBOL_PASS"
rustup toolchain install 1.85.1 --profile minimal
features=m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record,native_fec_acceleration
cargo +1.85.1 build --release --locked -p wbd-engine --features "$features"
cargo +1.85.1 test --locked -p wbd-engine --features "$features" --lib v4_game_lane::tests
cargo +1.85.1 test --locked -p wbd-engine --features "$features" --lib v4_fec2_live_rx::tests
# Shared Linux protocol/core and bounded source policy, no Windows GUI/Direct claim.
cargo +1.85.1 test --locked -p wbd-engine --features "$features" --lib v4_client_startup_padding::tests
test -s target/release/libwbd_engine.so
mkdir -p linux-plan029-public-bundle
export CGO_ENABLED=1 GOOS=linux GOARCH="$GO_ARCH" GOTOOLCHAIN=local
export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/release -lwbd_engine"
export LD_LIBRARY_PATH="$GITHUB_WORKSPACE/target/release:${LD_LIBRARY_PATH:-}"
# Run ORIGINAL real Go TLS/crypto tests for both encrypted config
# directions, bounded/truncated framing, v1 fail-closed and verified mode.
# Pure original-Go protected TLS tests intentionally exclude the native
# embedded-Go test tag: its unrelated raw-kernel probes require additional
# fixture helpers. The real tagged native product still compiles/tests below.
(cd legacy && go test -count=1 ./internal/realityfront -run '^TestH2202')
(cd legacy && go test -count=1 -tags wbd_v4_embedded_go,wbd_v4_fec2_product ./internal/v4productcli)
(cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product -o "$GITHUB_WORKSPACE/linux-plan029-public-bundle/wbd-v4-client" ./cmd/wbd-v4-client)
(cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product -o "$GITHUB_WORKSPACE/linux-plan029-public-bundle/wbd-v4-server" ./cmd/wbd-v4-server)
cp target/release/libwbd_engine.so linux-plan029-public-bundle/libwbd_engine.so
(cd linux-plan029-public-bundle && sha256sum wbd-v4-client wbd-v4-server libwbd_engine.so > SHA256SUMS)
if [[ "${WBD_LINUX_GLIBC_BUILD_BASELINE:-}" == 2.31-inner ]]; then
  python3 tools/m0_linux_glibc_abi.py linux-plan029-public-bundle 2.31
else
  python3 tools/m0_linux_glibc_abi.py linux-plan029-public-bundle
fi
export WBD_BUILD_GLIBC="$(getconf GNU_LIBC_VERSION)"
python3 - <<'PY'
import hashlib,json,os,pathlib,platform
p=pathlib.Path("linux-plan029-public-bundle")
names=("wbd-v4-client","wbd-v4-server","libwbd_engine.so")
hashes={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in names}
assert all((p/n).stat().st_size>100000 for n in names)
assert platform.machine() in ("aarch64","x86_64")
assert platform.machine()==os.environ["WBD_PLAN029_LINUX_EXPECTED_ARCH"]
d={"schema_version":1,"source_sha":os.environ["GITHUB_SHA"],
   "original_go_sha":"a7a82db31fe736ffedee330795a3234d358f1984",
   "isa_l_source":"c387163fcbca62701d646149564c550c78a4f985",
   "rust":"1.85.1","go":"1.23.12",
   "build_glibc":os.environ["WBD_BUILD_GLIBC"],
   "elf_version_needs":json.loads((p/"glibc-abi.json").read_text()),
   "architecture":platform.machine(),"sha256":hashes,
   "rust_native_fec_acceleration":True,
   "original_go_faketcp":"11-source-locked-records",
   "original_go_native_client_and_server":"all-current-v4productcli-overlay-files",
   "native_server_cold_cohort":"exact protected epoch PLUS original adjacent 5tuple",
   "scope":"NATIVE_LINUX_DUAL_ISA_BINARY_BUILD_ONLY",
   "raw_tun_tls_app_stop":"NOT_RUN","android_vpn":"NOT_RUN","openwrt_device":"NOT_RUN"}
p.joinpath("manifest.json").write_text(json.dumps(d,indent=2)+"\n")
print("PLAN029_LINUX_GO_RUST_SOURCE_LOCKED_BUILD_ONLY_PASS arch="+platform.machine(),flush=True)
PY
