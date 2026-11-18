#!/usr/bin/env bash
# D2-S0: genuine Linux original WBD server/client on x86_64 KVM host ISA.
# Build + real CLI help only; no Android TLS/M4/Stop E2E claims.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test -n "$GITHUB_SHA"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
test "$(uname -m)" = x86_64
test "$(git -C legacy rev-parse HEAD)" = a7a82db31fe736ffedee330795a3234d358f1984
p=out/android-x86-original-linux
n=out/android-root-app-native
mkdir -p "$p"
test -s "$n/SOURCE" && test "$(cat "$n/SOURCE")" = "$GITHUB_SHA"
(cd "$n" && sha256sum -c SHA256SUMS) >"$p/android-native-source-check.txt"
python3 - <<'PY'
from pathlib import Path
import json,os,hashlib
n=Path("out/android-root-app-native")
m=json.loads((n/"manifest-ci-x86_64.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
assert m["donor_go"]=="a7a82db31fe736ffedee330795a3234d358f1984"
assert m["android_abis"]==["x86_64"] and m["release"] is False
for name in ("wbd-v4-client-amd64","libwbd_engine-amd64.so"):
    assert m["artifacts"][name]["elf"]["machine"]==62
    assert hashlib.sha256((n/name).read_bytes()).hexdigest()==m["artifacts"][name]["sha256"]
print("D2_S0_ORIGINAL_ANDROID_X86_NATIVE_SOURCE_LOCK_PASS")
PY
# Exact pinned overlay assembly as android/root-native/ci/linux-original-oracle.sh.
# No alternative WBD wire implementation, no test-only fake TLS.
python3 tools/m0_install_public_faketcp.py --check-only
python3 tools/m0_install_public_faketcp.py legacy
cp r0/go_overlay/internal/faketcp/raw_detached_data_linux.go legacy/internal/faketcp/
cp r0/go_overlay/internal/faketcp/raw_detached_data_linux_test.go legacy/internal/faketcp/
for name in raw_android_network_android.go raw_android_network_linux.go;do
  test ! -e "legacy/internal/faketcp/$name"
  cp "r0/go_overlay/internal/faketcp/$name" "legacy/internal/faketcp/$name"
done
python3 tools/m0_install_public_realityfront_tests.py legacy
mkdir -p legacy/internal/v4productcli legacy/cmd/wbd-v4-client legacy/cmd/wbd-v4-server
for file in r0/go_overlay/internal/realityfront/*.go;do
  name="$(basename "$file")"
  case "$name" in
    tls_test.go|wire_qualification_test.go) continue ;;
    tls.go)
      test "$(git -C legacy hash-object internal/realityfront/tls.go)" = 518a18104803baf75c703fd8b038f2126beb8d64
      cp "$file" legacy/internal/realityfront/tls.go
      continue ;;
  esac
  test ! -e "legacy/internal/realityfront/$name" || {
    echo "original donor overlay collision $name" >&2; exit 1;
  }
  cp "$file" "legacy/internal/realityfront/$name"
done
cp r0/go_overlay/internal/v4productcli/*.go legacy/internal/v4productcli/
mkdir -p legacy/internal/v4productcli/rootjournal
cp r0/go_overlay/internal/v4productcli/rootjournal/*.go legacy/internal/v4productcli/rootjournal/
mkdir -p legacy/internal/v4productcli/dnsnative
cp r0/go_overlay/internal/v4productcli/dnsnative/*.go legacy/internal/v4productcli/dnsnative/
for role in client server;do
  cp "r0/go_overlay/cmd/wbd-v4-$role/main.go" "legacy/cmd/wbd-v4-$role/main.go"
done
test ! -e legacy/internal/realityfront/v4_route_prelude.go
# Exercise exact root-owned all-app kernel UID range commit/readback/Stop
# against a hostile fake ip(8) runner. Never require Android device root.
(cd legacy && go test -count=1 ./internal/v4productcli/rootjournal) >"$p/rootjournal-all-app-unit.txt" 2>&1 || {
  tail -80 "$p/rootjournal-all-app-unit.txt" >&2
  exit 1
}
echo ANDROID_ALL_APP_ROOTJOURNAL_EXACT_ROLLBACK_HOST_PASS
rustup toolchain install 1.85.1 --profile minimal
cargo +1.85.1 build --locked --release -p wbd-engine \
  --features m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record \
  >"$p/rust-build.log" 2>&1 || {
    tail -90 "$p/rust-build.log" >&2
    exit 1
  }
cp target/release/libwbd_engine.so "$p/libwbd_engine.so"
export CGO_ENABLED=1 GOOS=linux GOARCH=amd64 GOTOOLCHAIN=local
export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/release -lwbd_engine"
export LD_LIBRARY_PATH="$GITHUB_WORKSPACE/target/release"
for role in client server;do
  (cd legacy && go build -trimpath -buildvcs=false \
    -tags wbd_v4_embedded_go,wbd_v4_fec2_product \
    -o "$GITHUB_WORKSPACE/$p/wbd-v4-$role" \
    "./cmd/wbd-v4-$role")
done
for role in client server;do
  readelf -h "$p/wbd-v4-$role" >"$p/elf-$role.txt"
  readelf -d "$p/wbd-v4-$role" >"$p/linker-$role.txt"
  grep -Fq 'Advanced Micro Devices X86-64' "$p/elf-$role.txt"
  grep -Fq 'Shared library: [libwbd_engine.so]' "$p/linker-$role.txt"
  set +e
  timeout --signal=TERM --kill-after=2s 15s "$p/wbd-v4-$role" --help \
    >"$p/help-$role.txt" 2>&1
  rc=$?
  set -e
  printf '%s\n' "$rc" >"$p/help-$role-rc.txt"
  test "$rc" -eq 1
  grep -Fq "Usage of wbd-v4-$role:" "$p/help-$role.txt"
  grep -Fq 'flag: help requested' "$p/help-$role.txt"
  if grep -Eq 'panic:|fatal error:' "$p/help-$role.txt";then
    echo "D2_S0_ORIGINAL_LINUX_GO_HELP_RUNTIME_CRASH $role" >&2;exit 1
  fi
done
readelf -h "$p/libwbd_engine.so" >"$p/elf-rust.txt"
grep -Fq 'Advanced Micro Devices X86-64' "$p/elf-rust.txt"
python3 - <<'PY'
from pathlib import Path
import json,os,hashlib,struct
p=Path("out/android-x86-original-linux")
n=Path("out/android-root-app-native")
src=os.environ["GITHUB_SHA"]
a=json.loads((n/"manifest-ci-x86_64.json").read_text())
sha={}
for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
    b=(p/name).read_bytes()
    assert b[:5]==b"\x7fELF\x02" and struct.unpack_from("<H",b,18)[0]==62,name
    sha[name]=hashlib.sha256(b).hexdigest()
for role in ("client","server"):
    assert (p/("help-"+role+"-rc.txt")).read_text().strip()=="1"
    help=(p/("help-"+role+".txt")).read_text()
    assert "Usage of wbd-v4-"+role+":" in help and "flag: help requested" in help
out={"schema":"wbd-d2-s0-original-linux-server-x86_64-prep/v1",
 "source":src,"donor_go":a["donor_go"],"linux_arch":"amd64",
 "android_ci_abi":"x86_64",
 "android_go_sha256":a["artifacts"]["wbd-v4-client-amd64"]["sha256"],
 "android_rust_sha256":a["artifacts"]["libwbd_engine-amd64.so"]["sha256"],
 "linux_elf_sha256":sha,"original_linux_server_cli_helps":"PASS_REAL_LINUX_EXECUTED",
 "original_server_authenticated_session":"NOT_RUN",
 "android_x86_real_tls_lease":"NOT_RUN",
 "android_original_m4_tcp_udp":"NOT_RUN",
 "android_owned_stop":"NOT_RUN",
 "system_dns_takeover":"NOT_RUN"}
(p/"manifest.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
(p/"SOURCE").write_text(src+"\n")
print("D2_S0_ORIGINAL_LINUX_X86_SERVER_CLIENT_ELF_EXECUTED_HELP_PASS")
PY
(cd "$p" && sha256sum wbd-v4-server wbd-v4-client libwbd_engine.so SOURCE manifest.json >SHA256SUMS && sha256sum -c SHA256SUMS)
