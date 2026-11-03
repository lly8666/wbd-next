#!/usr/bin/env bash
# PLAN028: SOURCE-locked native Linux amd64 + cross-built Linux arm64.
# The ARM half is tested under QEMU-user in REAL kernel netns, not on ARM HW.
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_WORKSPACE:?}"
test "$(uname -m)" = x86_64
test "$(git -C legacy rev-parse HEAD)" = a7a82db31fe736ffedee330795a3234d358f1984
test "$(go version | awk '{print $3}')" = go1.23.12
rustup toolchain install 1.85.1 --profile minimal
rustup +1.85.1 target add aarch64-unknown-linux-gnu x86_64-unknown-linux-gnu
python3 tools/m0_install_public_faketcp.py legacy
for file in raw_detached_data_linux.go raw_detached_data_linux_test.go;do
 cp "r0/go_overlay/internal/faketcp/$file" "legacy/internal/faketcp/$file"
done
mkdir -p legacy/internal/v4productcli legacy/cmd/wbd-v4-client legacy/cmd/wbd-v4-server
# Same exact source list as the already-qualified M0 combined original-Go
# assembly; no different backend, wire, or alternative data plane.
for file in \
 bridge_v4_linux_server_product.go bridge_v4_linux_client_product.go \
 bridge_v4_game_cold_set.go bridge_v4_game_cold_set_test.go \
 fec_v2_policy.go fec_v2_policy_test.go \
 fec_v2_runtime_controller.go fec_v2_runtime_controller_test.go \
 admission_v4.go admission_v4_test.go v4_route_prelude.go v4_route_prelude_test.go \
 bridge_v4_probe_linux.go bridge_v4_probe_linux_test.go \
 bridge_v4_embedded_linux.go bridge_v4_fec2_owner_off_linux.go \
 bridge_v4_fec2_owner_probe_linux.go bridge_v4_fec2_release_client_linux.go \
 bridge_v4_fec2_public_product_linux.go bridge_v4_fec2_public_mature_linux.go \
 bridge_v4_fec2_public_mature_disabled_linux.go \
 bridge_v4_game_native_linux.go bridge_v4_game_native_linux_test.go \
 bridge_v4_linux_game_product.go \
 bridge_v4_fec2_owner_probe_linux_test.go \
 bridge_v4_embedded_linux_test.go bridge_v4_embedded_perf_linux_test.go \
 bridge_v4_normal_off_policy_linux.go bridge_v4_normal_off_policy_linux_test.go \
 bridge_v4_fixed_pending_linux.go bridge_v4_fixed_pending_linux_test.go \
 bridge_v4_live_fec2_kernel_linux_test.go bridge_v4_m4_linux_connect_stop_test.go
do
 test -f "r0/go_overlay/internal/realityfront/$file"
 cp "r0/go_overlay/internal/realityfront/$file" "legacy/internal/realityfront/$file"
done
for file in bridge_v4_linux_public_product.go bridge_v4_game_product_linux.go bridge_v4_linux_public_product_test.go bridge_v4_game_kernel_linux_test.go;do
 if [[ -f "r0/go_overlay/internal/realityfront/$file" ]];then
  cp "r0/go_overlay/internal/realityfront/$file" "legacy/internal/realityfront/$file"
 fi
done
for file in linux.go path_linux.go path_supervisor_linux.go game_linux.go;do
 cp "r0/go_overlay/internal/v4productcli/$file" "legacy/internal/v4productcli/$file"
done
cp r0/go_overlay/cmd/wbd-v4-client/main.go legacy/cmd/wbd-v4-client/main.go
cp r0/go_overlay/cmd/wbd-v4-server/main.go legacy/cmd/wbd-v4-server/main.go
mkdir -p mixed-isa-build/amd64 mixed-isa-build/arm64
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc
export CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc
features=m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record
for cpu in amd64 arm64;do
 case "$cpu" in
  amd64) triple=x86_64-unknown-linux-gnu;cc=gcc ;;
  arm64) triple=aarch64-unknown-linux-gnu;cc=aarch64-linux-gnu-gcc ;;
 esac
 cargo +1.85.1 build --locked --release --target "$triple" -p wbd-engine --features "$features"
 lib="$GITHUB_WORKSPACE/target/$triple/release/libwbd_engine.so"
 test -s "$lib"
 cp "$lib" "mixed-isa-build/$cpu/libwbd_engine.so"
 export CGO_ENABLED=1 GOOS=linux GOARCH="$cpu" CC="$cc" GOTOOLCHAIN=local
 export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/$triple/release -lwbd_engine"
 export LD_LIBRARY_PATH="$GITHUB_WORKSPACE/target/$triple/release:${LD_LIBRARY_PATH:-}"
 for kind in client server;do
  (cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product \
   -o "$GITHUB_WORKSPACE/mixed-isa-build/$cpu/wbd-v4-$kind" "./cmd/wbd-v4-$kind")
 done
 (cd "mixed-isa-build/$cpu" && sha256sum wbd-v4-client wbd-v4-server libwbd_engine.so >SHA256SUMS)
done
python3 - <<'PY'
import hashlib,json,os,pathlib,struct
root=pathlib.Path("mixed-isa-build")
result={"source":os.environ["GITHUB_SHA"],"original_go_source":"a7a82db31fe736ffedee330795a3234d358f1984",
        "go":"1.23.12","rust":"1.85.1","qualification":"BUILD_ONLY",
        "arm64_backend":"cross_compiled_generic_fec2","functional":"NOT_RUN"}
for cpu,machine in (("amd64",62),("arm64",183)):
    result[cpu]={}
    for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
        p=root/cpu/name
        b=p.read_bytes()
        assert b[:4]==bytes.fromhex("7f454c46") and struct.unpack_from("<H",b,18)[0]==machine,(p,b[:20])
        result[cpu][name]={"sha256":hashlib.sha256(b).hexdigest(),"elf_machine":machine}
(root/"manifest.json").write_text(json.dumps(result,indent=2))
print("M0_PLAN028_MIXED_ISA_BOTH_ORIGINAL_GO_RUST_SOURCE_LOCKED_BUILD_PASS",flush=True)
PY
