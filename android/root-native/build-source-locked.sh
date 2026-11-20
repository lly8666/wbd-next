#!/usr/bin/env bash
# Same-source Android 64-bit Go/Rust native build. ARM64 release; x86_64 CI-only.
# Real Go final link and phone traffic remain independent truthful gates.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?Actions checkout required}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?SOURCE required}"
test "$(git -C legacy rev-parse HEAD)" = "a7a82db31fe736ffedee330795a3234d358f1984"
: "${ANDROID_HOME:?NDK missing}"
ndk="$(find "$ANDROID_HOME/ndk" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n 1)"
tool="$ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"
test -x "$tool/aarch64-linux-android28-clang"
rustup toolchain install 1.85.1 --profile minimal
rustup target add --toolchain 1.85.1 aarch64-linux-android x86_64-linux-android
export CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER="$tool/aarch64-linux-android28-clang"
export CARGO_TARGET_X86_64_LINUX_ANDROID_LINKER="$tool/x86_64-linux-android28-clang"
# aws-lc-sys/cc-rs does NOT honor Cargo's linker setting for its C objects.
# NDK has API-qualified clang wrappers, not aarch64-linux-android-clang.
export CC_aarch64_linux_android="$tool/aarch64-linux-android28-clang"
export AR_aarch64_linux_android="$tool/llvm-ar"
export CC_x86_64_linux_android="$tool/x86_64-linux-android28-clang"
export AR_x86_64_linux_android="$tool/llvm-ar"
export RUSTFLAGS="-C link-arg=-Wl,-z,max-page-size=16384"
mkdir -p out/android-product-a1
# Exact public original-Go source-lock installation; do not duplicate legacy.
python3 tools/m0_install_public_faketcp.py --check-only
python3 tools/m0_install_public_faketcp.py legacy
cp r0/go_overlay/internal/faketcp/raw_detached_data_linux.go legacy/internal/faketcp/
cp r0/go_overlay/internal/faketcp/raw_detached_data_linux_test.go legacy/internal/faketcp/
# Source-locked Android-only pre-TLS physical Network binding. Original donor untouched.
for name in raw_android_network_android.go raw_android_network_linux.go; do
  test ! -e "legacy/internal/faketcp/$name" || { echo "donor collision: $name" >&2; exit 1; }
  cp "r0/go_overlay/internal/faketcp/$name" "legacy/internal/faketcp/$name"
done
python3 tools/m0_install_public_realityfront_tests.py legacy
mkdir -p legacy/internal/v4productcli legacy/cmd/wbd-v4-client legacy/cmd/wbd-v4-server
for file in r0/go_overlay/internal/realityfront/*.go; do
  name="${file##*/}"
  case "$name" in
    tls_test.go|wire_qualification_test.go) continue ;;
    tls.go)
      test "$(git -C legacy hash-object internal/realityfront/tls.go)" = 518a18104803baf75c703fd8b038f2126beb8d64
      cp "$file" "legacy/internal/realityfront/tls.go"
      continue ;;
  esac
  test ! -e "legacy/internal/realityfront/$name" || { echo "overlay collision: $name" >&2; exit 1; }
  cp "$file" "legacy/internal/realityfront/$name"
done
# A28 main brought the original offline v2 short-route-key package.
# The fixed donor lacks this package: assemble the EXACT public overlay
# for original Go's shared client/server parser (not a second KDF stack).
test -d r0/go_overlay/internal/v4routekey
test ! -e legacy/internal/v4routekey || {
  echo "source-locked original Go v4routekey donor collision" >&2
  exit 1
}
mkdir -p legacy/internal/v4routekey
cp r0/go_overlay/internal/v4routekey/*.go legacy/internal/v4routekey/
cp r0/go_overlay/internal/v4productcli/*.go legacy/internal/v4productcli/
mkdir -p legacy/internal/v4productcli/rootjournal
cp r0/go_overlay/internal/v4productcli/rootjournal/*.go legacy/internal/v4productcli/rootjournal/
# Source-locked Android root cold RST owner; host Go tests use only a fake iptables runner.
mkdir -p legacy/internal/v4productcli/rstguard
cp r0/go_overlay/internal/v4productcli/rstguard/*.go legacy/internal/v4productcli/rstguard/
(cd legacy && go test -count=1 ./internal/v4productcli/rstguard)
echo ANDROID_A35_FAKE_RUNNER_RST_GUARD_JOURNAL_HOST_PASS
# B1 native DNS transport is source-locked but NOT yet connected
# to Android system resolver/TUN capture or Network socket binding.
mkdir -p legacy/internal/v4productcli/dnsnative
cp r0/go_overlay/internal/v4productcli/dnsnative/*.go legacy/internal/v4productcli/dnsnative/
# Portable kernel-policy tests remain host-Go; x86_64 Android is CI-only, not a shipped ABI.
(cd legacy && go test -count=1 ./internal/v4productcli/rootjournal)
(cd legacy && go test -count=1 ./internal/v4routekey)
# Android ARM64 cross-compile only; test ELF is NOT executed or deployed.
(cd legacy && GOOS=android GOARCH=arm64 CGO_ENABLED=0 GOTOOLCHAIN=local go test -c \
  -o "$GITHUB_WORKSPACE/out/android-product-a1/dnsnative-arm64.test" \
  ./internal/v4productcli/dnsnative)
test -s out/android-product-a1/dnsnative-arm64.test
cp r0/go_overlay/cmd/wbd-v4-client/main.go legacy/cmd/wbd-v4-client/
# Build-tagged test-only c-shared entry calls original Go Run("client").
# It is EXCLUDED from the official ARM64 executable and signed Root APK.
test ! -e legacy/cmd/wbd-v4-client/ksu_cshared_entry_android.go
cp r0/go_overlay/cmd/wbd-v4-client/ksu_cshared_entry_android.go legacy/cmd/wbd-v4-client/
cp r0/go_overlay/cmd/wbd-v4-server/main.go legacy/cmd/wbd-v4-server/
# Android ARM64 first authentic Go/Rust product is Normal/off only.
# Use the ALREADY-EXISTING original-Go !wbd_v4_fec2_product source variants.
# Native Fixed/Auto and Game are explicitly UNAVAILABLE until real ARM64
# FEC/M2/Game kernels exist; never introduce dummy C ABI to force green.
# Keep original Rust Health/M1/M3 + future codec in this source stage.
features=m0_v4_probe,m0_v4_embedded_go,fec2_product_record
go_tags=wbd_v4_embedded_go
for pair in "aarch64 arm64" "x86_64 amd64"; do
  read -r triple goarch <<< "$pair"
  rust_target="$triple-linux-android"
  cc="$tool/${rust_target}28-clang"
  test -x "$cc"
  "$cc" -c -std=c11 -Wall -Wextra -Werror android/root-native/android_abi.c -o "out/android-product-a1/abi-$goarch.o"
  cargo +1.85.1 build --release --locked --target "$rust_target" -p wbd-engine --features "$features"
  lib="target/$rust_target/release/libwbd_engine.so"
  test -s "$lib"
  cp "$lib" "out/android-product-a1/libwbd_engine-$goarch.so"
  # All cold+M4 symbols must resolve from the SAME real Rust AEAD/PN owner;
  # these native methods actually start/join original M1/M3 Bionic workers.
  # Building their ELF does NOT prove kernel permission or live traffic.
  # Under set -o pipefail, llvm-nm | grep -q can report SIGPIPE (141)
  # when grep exits after the FIRST valid symbol; it was wrongly logged as
  # "MISSING" on SOURCE 2b8e even though readelf/nm proved the ABI exists.
  # Materialize the full exported-symbol table exactly ONCE before checking.
  # Every symbol below must still be exported by the SAME real Rust ELF.
  symbol_table="out/android-product-a1/libwbd_engine-$goarch.dynsym.txt"
  "$tool/llvm-nm" -D "$lib" > "$symbol_table"
  test -s "$symbol_table"
  for symbol in wbd_m0_embedded_go_prepare_client wbd_m0_embedded_go_stage \
      wbd_m0_embedded_go_commit wbd_m0_embedded_go_stop \
      wbd_m0_embedded_go_android_bind_physical \
      wbd_m0_embedded_go_attach_raw_rx_on_interface \
      wbd_m0_embedded_go_attach_tun \
      wbd_m0_embedded_go_loop_start wbd_m0_embedded_go_loop_stats \
      wbd_m0_embedded_go_loop_business_receipts \
      wbd_m0_embedded_go_loop_return_path_receipts \
       wbd_m0_embedded_go_loop_dns_ingress_observed \
       wbd_m0_embedded_go_loop_thread_cpu \
       wbd_m0_embedded_go_loop_physical_scope_invalid \
      wbd_m0_embedded_go_loop_authenticated_dead \
      wbd_m0_embedded_go_loop_authenticated_peer_predead \
      wbd_m0_embedded_go_loop_authenticated_peer_health \
      wbd_m0_embedded_go_public_native_health_config \
      wbd_m0_embedded_go_public_native_health_effective \
      wbd_m0_embedded_go_normal_off_stage \
      wbd_m0_embedded_go_normal_off_readback \
      wbd_m0_embedded_go_bind_authenticated_client_ipv4 \
      wbd_m0_embedded_go_observed_tx_ipv4_mtu; do
    grep -Eq " [TW] ${symbol}$" "$symbol_table" || {
      echo "ANDROID_ARM64_ORIGINAL_RUST_ELF_EXPORT_MISSING: $symbol" >&2
      exit 1
    }
  done
done
# The authenticated cold Rust owner is a genuine cross-target ABI milestone,
# while full Go/M4 product linking has a separately failing/passing gate.
# Persist exact hashes+16KiB ELF evidence for ARM64 only even if Go fails.
python3 - <<'PY'
import hashlib,json,os,pathlib,struct
p=pathlib.Path("out/android-product-a1")
def inspect(path,expected_machine):
    b=path.read_bytes()
    assert b[:5]==b"\x7fELF\x02",(path,"not ELF64")
    bo="<" if b[5]==1 else ">"
    assert struct.unpack_from(bo+"H",b,18)[0]==expected_machine,(path,"wrong ELF machine")
    phoff=struct.unpack_from(bo+"Q",b,32)[0]
    entsize,phnum=struct.unpack_from(bo+"HH",b,54)
    aligns=[struct.unpack_from(bo+"Q",b,phoff+i*entsize+48)[0]
        for i in range(phnum) if struct.unpack_from(bo+"I",b,phoff+i*entsize)[0]==1]
    assert aligns and min(aligns)>=(16384 if expected_machine==183 else 4096),(path,aligns)
    return {"sha256":hashlib.sha256(b).hexdigest(),"machine":expected_machine,
            "min_pt_load_align":min(aligns)}
d={"schema":"android-root-product-a1-rust-cold-build/v1",
   "source":os.environ["GITHUB_SHA"],
   "pinned_original_go":"a7a82db31fe736ffedee330795a3234d358f1984",
   "scope":"ORIGINAL_ARM64_NORMAL_OFF_M1_M3_M4_HEALTH_COMPILED_ONLY",
   "android_c_abi_static_checks":"PASS_IN_WORKFLOW",
   "original_rust_cold_prepare_stage_commit_stop_symbols":"PASS_IN_WORKFLOW",
   "android_original_owner_network_raw_tun_ffi_symbols":"PASS_IN_WORKFLOW",
   "native":{abi:inspect(p/("libwbd_engine-"+abi+".so"),mach)
             for abi,mach in (("arm64",183),("amd64",62))},
   "original_go_full_link":"NOT_YET_RUN_AT_THIS_STAGE",
   "authenticated_product_M4_worker":"SOURCE_COMPILED_NOT_EXECUTED",
   "original_health_clock_control":"SOURCE_COMPILED_NOT_EXECUTED",
   "eventfd_owned_stop_join":"SOURCE_COMPILED_NOT_EXECUTED",
   "real_server_TLS_auth_lease_data_stop":"NOT_RUN",
   "physical_android_load":"NOT_RUN"}
(p/"rust-cold-stage-manifest.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
(p/"SOURCE").write_text(os.environ["GITHUB_SHA"]+"\n")
PY
# Genuine original-Go Normal/off link remains a hard gate. Android CGo
# links only mandatory native original M1/M3/M4/Health/Stop. Optional
# Fixed/FEC/Game and Linux-only diagnostics fail closed in Go, not via
# fabricated native ELF symbols or a suppressed linker error.
for pair in "aarch64 arm64" "x86_64 amd64"; do
  read -r triple goarch <<< "$pair"
  rust_target="$triple-linux-android"
  cc="$tool/${rust_target}28-clang"
  export GOOS=android GOARCH="$goarch" CGO_ENABLED=1 GOTOOLCHAIN=local CC="$cc"
  # Android x86_64 KVM + NDK translation (and real ARM64 Bionic)
  # does not reliably propagate a privileged "su -c" LD_LIBRARY_PATH to
  # the translated AArch64 dynamic linker. The real original-Go binary
  # and its shared-Rust owner are staged in the SAME owned root directory.
  # DT_RUNPATH=$ORIGIN makes this an actual relocatable Android product,
  # instead of a Host-only Go/Rust link or a privileged-env guess.
  export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/$rust_target/release -lwbd_engine -Wl,-z,max-page-size=16384 -Wl,-rpath,\$ORIGIN"
  (cd legacy && go build -trimpath -buildvcs=false -tags "$go_tags" -o "$GITHUB_WORKSPACE/out/android-product-a1/wbd-v4-client-$goarch" ./cmd/wbd-v4-client)
  # Test actual source-locked linked ELF rather than checking only flags.
  readelf -d "out/android-product-a1/wbd-v4-client-$goarch" \
    >"out/android-product-a1/linker-$goarch.txt"
  grep -Fq 'Shared library: [libwbd_engine.so]' "out/android-product-a1/linker-$goarch.txt"
  grep -Eq 'Library runpath: \[\$ORIGIN(:\$ORIGIN)*\]' "out/android-product-a1/linker-$goarch.txt"
  unset CGO_LDFLAGS
  # Quarantined ARM64 NativeBridge diagnosis; x86 native product is built above.
  if [[ "$goarch" == "arm64" ]]; then
  # Exact-SHA Android ARM64 diagnosis ONLY: distinguish Bionic/native
  # translator, pure-Go runtime, and real Rust dlopen from original WBD.
  # Not included in APK; no mock TLS/AEAD/client/server/data path.
  "$cc" -std=c11 -O2 -Wall -Wextra -Werror -fPIE -pie \
    -Wl,-z,max-page-size=16384 \
    -o "$GITHUB_WORKSPACE/out/android-product-a1/ksu-arm64-ndk-probe" \
    android/root-app/ci/nativebridge-arm64-ndk-probe.c -ldl
  GO111MODULE=off CGO_ENABLED=0 GOTOOLCHAIN=local \
    go build -trimpath -buildvcs=false \
    -o "$GITHUB_WORKSPACE/out/android-product-a1/ksu-arm64-go-probe" \
    android/root-app/ci/nativebridge-arm64-go-probe.go
  # Distinguish Android NativeBridge's direct Go executable startup from
  # a real NDK dlopen of the genuine Go runtime's c-shared initializer.
  # Strictly test-only; this Go .so is NOT included in the Root APK.
  GO111MODULE=off CGO_ENABLED=1 GOTOOLCHAIN=local \
    CGO_LDFLAGS="-Wl,-z,max-page-size=16384" \
    go build -buildmode=c-shared -trimpath -buildvcs=false \
    -o "$GITHUB_WORKSPACE/out/android-product-a1/libksu-arm64-go-cshared-probe.so" \
    android/root-app/ci/nativebridge-arm64-go-cshared-probe.go
  # Isolated toolchain copy: NEVER patch system Go, original donor,
  # or real product ELF. The Android NativeBridge guest reports an
  # undefined MRS MIDR_EL1 instruction in Go1.23 runtime internal/cpu.
  python3 android/root-app/ci/nativebridge-go-midrel1-isolate.py
  patched_go_root="$GITHUB_WORKSPACE/out/nativebridge-go-patched-goroot"
  GOROOT="$patched_go_root" GO111MODULE=off CGO_ENABLED=0 GOTOOLCHAIN=local \
    go build -trimpath -buildvcs=false \
    -o "$GITHUB_WORKSPACE/out/android-product-a1/ksu-arm64-go-midr-isolate" \
    android/root-app/ci/nativebridge-arm64-go-probe.go
  GOROOT="$patched_go_root" GO111MODULE=off CGO_ENABLED=1 GOTOOLCHAIN=local \
    CGO_LDFLAGS="-Wl,-z,max-page-size=16384" \
    go build -buildmode=c-shared -trimpath -buildvcs=false \
    -o "$GITHUB_WORKSPACE/out/android-product-a1/libksu-arm64-go-cshared-midr-isolate.so" \
    android/root-app/ci/nativebridge-arm64-go-cshared-probe.go
  # Test-only full original-Go product logic through a verified NativeBridge
  # c-shared runtime. This is the exact source-locked donor/overlay and real
  # Rust .so, but a quarantined patched Go1.23 GOROOT plus a test-only export.
  # The NativeBridge translator cannot execute klauspost/cpuid/v2
  # MIDR_EL1 system-register reads. Its upstream noasm tag is used ONLY
  # in this diagnostic c-shared build; not in the official product.
  # The signed APK's unmodified GO executable remains the actual product and
  # MUST continue to fail its own x86 NativeBridge gate if SIGSEGV persists.
  GOROOT="$patched_go_root" CGO_ENABLED=1 GOTOOLCHAIN=local \
    CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/$rust_target/release -lwbd_engine -Wl,-z,max-page-size=16384 -Wl,-rpath,\$ORIGIN" \
    bash -c 'cd legacy && go build -buildmode=c-shared -trimpath -buildvcs=false \
      -tags "wbd_v4_embedded_go,wbd_ksu_cshared_test,noasm" \
      -o "$GITHUB_WORKSPACE/out/android-product-a1/libksu-arm64-original-go-cshared-midr.so" \
      ./cmd/wbd-v4-client'
  readelf -d "out/android-product-a1/libksu-arm64-original-go-cshared-midr.so" \
    >"out/android-product-a1/linker-original-go-cshared-midr.txt"
  grep -Fq 'Shared library: [libwbd_engine.so]' \
    "out/android-product-a1/linker-original-go-cshared-midr.txt"
  grep -Eq 'Library runpath: \[\$ORIGIN(:\$ORIGIN)*\]' \
    "out/android-product-a1/linker-original-go-cshared-midr.txt"
  "$tool/llvm-nm" -D "out/android-product-a1/libksu-arm64-original-go-cshared-midr.so" \
    >"out/android-product-a1/original-go-cshared-midr.dynsym.txt"
  grep -Eq '[[:space:]]WBD_AndroidRootOriginalGoHelp$' \
    "out/android-product-a1/original-go-cshared-midr.dynsym.txt"
  # Guard against the test-only symbol ever entering the signed executable.
  "$tool/llvm-nm" -D "out/android-product-a1/wbd-v4-client-$goarch" \
    >"out/android-product-a1/official-go-exports.txt"
  if grep -q WBD_AndroidRootOriginalGoHelp "out/android-product-a1/official-go-exports.txt";then
    echo "TEST_ONLY_GO_EXPORT_LEAKED_TO_OFFICIAL_PRODUCT" >&2
    exit 1
  fi
  python3 - <<'PYARM64'
from pathlib import Path
import struct
for name in ("ksu-arm64-ndk-probe","ksu-arm64-go-probe","libksu-arm64-go-cshared-probe.so","ksu-arm64-go-midr-isolate","libksu-arm64-go-cshared-midr-isolate.so","libksu-arm64-original-go-cshared-midr.so"):
    raw=(Path("out/android-product-a1")/name).read_bytes()
    assert raw[:5]==b"\x7fELF\x02" and struct.unpack_from("<H",raw,18)[0]==183,name
print("ARM64_NATIVEBRIDGE_DIAGNOSTIC_PROBES_SOURCE_COMPILED_ONLY")
PYARM64
  fi
done
python3 - <<'PY'
import json,os,hashlib,pathlib,struct
p=pathlib.Path("out/android-product-a1")
art=sorted(x for x in p.iterdir() if x.is_file())
def elf(path):
    b=path.read_bytes()
    assert b[:5]==b"\x7fELF\x02",path
    bo="<" if b[5]==1 else ">"
    e_type,e_machine=struct.unpack_from(bo+"HH",b,16)
    phoff=struct.unpack_from(bo+"Q",b,32)[0]
    entsize,phnum=struct.unpack_from(bo+"HH",b,54)
    aligns=[]
    for i in range(phnum):
        t=struct.unpack_from(bo+"I",b,phoff+i*entsize)[0]
        if t==1:aligns.append(struct.unpack_from(bo+"Q",b,phoff+i*entsize+48)[0])
    expected=62 if path.name in ("wbd-v4-client-amd64","libwbd_engine-amd64.so") else 183
    assert e_type in (2,3) and e_machine==expected,(path,"wrong ELF architecture",e_machine,expected)
    assert aligns and all(v>=(16384 if expected==183 else 4096) for v in aligns),(path,aligns)
    return {"type":e_type,"machine":e_machine,"min_pt_load_align":min(aligns)}
result={"schema":"android-root-product-a1-build/v1","source":os.environ["GITHUB_SHA"],
"donor_go":"a7a82db31fe736ffedee330795a3234d358f1984",
"rust_features":"m0_v4_probe,m0_v4_embedded_go,fec2_product_record","mode":"NORMAL_OFF_BUILD_ONLY",
"android_abis":["arm64"],"ci_only_abis":["x86_64"],"go_os":"android","android_api":28,
"go_build_tags":"wbd_v4_embedded_go","go_fec_game_native":"NOT_COMPILED_UNSUPPORTED",
"artifacts":{x.name:{"sha256":hashlib.sha256(x.read_bytes()).hexdigest(),
"elf":elf(x) if x.name.endswith(".so") or x.name in ("wbd-v4-client-arm64","wbd-v4-client-amd64") else None} for x in art},
"production_tls_auth_lease":"NOT_RUN","actual_tun_data":"NOT_RUN",
"android_root_app_install":"NOT_RUN","physical_acceleration":"NOT_RUN",
"real_server_connection":"NOT_RUN"}
(p/"manifest.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
# The release manifest remains ARM64-only; CI-only x86 has a separate manifest.
ci=dict(result)
ci["android_abis"]=["x86_64"]
ci["release"]=False
ci["artifacts"]={name:result["artifacts"][name] for name in ("wbd-v4-client-amd64","libwbd_engine-amd64.so")}
assert {ci["artifacts"][name]["elf"]["machine"] for name in ci["artifacts"]}=={62}
(p/"manifest-ci-x86_64.json").write_text(json.dumps(ci,indent=2,sort_keys=True)+"\n")
(p/"SOURCE").write_text(os.environ["GITHUB_SHA"]+"\n")
PY
(cd out/android-product-a1 && sha256sum * >SHA256SUMS && sha256sum -c SHA256SUMS)
