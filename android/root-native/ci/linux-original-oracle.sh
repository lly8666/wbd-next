#!/usr/bin/env bash
# A3 Linux original server oracle: real Linux peer, NOT Android guest traffic.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test -n "$GITHUB_SHA" && test -n "$GITHUB_RUN_ID" && test -n "$GH_TOKEN"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
test "$(uname -m)" = aarch64
test "$(git -C legacy rev-parse HEAD)" = a7a82db31fe736ffedee330795a3234d358f1984
mkdir -p out/android-a3-linux/validated-native fixed-kernel-result
gh run download "$GITHUB_RUN_ID" --repo "$GITHUB_REPOSITORY" \
  --name "android-root-product-a1-$GITHUB_SHA" \
  --dir out/android-a3-linux/validated-native
test "$(cat out/android-a3-linux/validated-native/SOURCE)" = "$GITHUB_SHA"
(cd out/android-a3-linux/validated-native && sha256sum -c SHA256SUMS)
python3 - <<'PY'
import hashlib,json,os,pathlib
p=pathlib.Path("out/android-a3-linux/validated-native")
m=json.loads((p/"manifest.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
assert m["donor_go"]=="a7a82db31fe736ffedee330795a3234d358f1984"
assert m["android_abis"]==["arm64"] and m["go_os"]=="android"
for name in ("wbd-v4-client-arm64","libwbd_engine-arm64.so"):
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==m["artifacts"][name]["sha256"]
    assert m["artifacts"][name]["elf"]["machine"]==183
    assert m["artifacts"][name]["elf"]["min_pt_load_align"]>=16384
print("ANDROID_A3_SAME_SOURCE_BIONIC_ARM64_ASSETS_VERIFIED")
PY
# Same donor and current overlay as the proven Android native builder.
# Historic PLAN020 result blobs are deliberately NOT repinned.
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
    echo "donor overlay collision: $name" >&2;exit 1;
  }
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
# linux.go now names the same pure-Go pinned CN8503 cold parser package.
# The Linux oracle donor overlay must assemble that library too, even
# though the Android-only CLI flag is rejected and no Linux DNS path runs.
mkdir -p legacy/internal/v4productcli/dnsnative
cp r0/go_overlay/internal/v4productcli/dnsnative/*.go legacy/internal/v4productcli/dnsnative/
for role in client server;do
  cp "r0/go_overlay/cmd/wbd-v4-$role/main.go" "legacy/cmd/wbd-v4-$role/main.go"
done
test ! -e legacy/internal/realityfront/v4_route_prelude.go
python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("out/android-a3-linux")
m=json.loads((p/"validated-native/manifest.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
assert m["donor_go"]=="a7a82db31fe736ffedee330795a3234d358f1984"
(p/"assembly.json").write_text(json.dumps({
 "schema":"android-a3-current-overlay-assembly-v1",
 "source":os.environ["GITHUB_SHA"],"go_donor":m["donor_go"],
 "assembly":"same_current_android_original_go_donor_overlay",
 "historic_plan020":"PRESERVED_UNMODIFIED_NOT_USED",
 "linux_real_protocol":"NOT_RUN"},indent=2)+"\n")
print("ANDROID_A3_ORIGINAL_LINUX_SERVER_CURRENT_DONOR_OVERLAY_PASS")
PY
rustup toolchain install 1.85.1 --profile minimal
cargo +1.85.1 build --locked --release -p wbd-engine \
  --features m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record \
  >out/android-a3-linux/rust-build.log 2>&1 || {
    tail -90 out/android-a3-linux/rust-build.log >&2
    exit 1
  }
cp target/release/libwbd_engine.so out/android-a3-linux/
export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/release -lwbd_engine"
export LD_LIBRARY_PATH="$GITHUB_WORKSPACE/target/release"
# A34: original donor typed error/deadline Go tests, not mocked network.
(cd legacy && timeout 180s go test -count=1 -tags wbd_v4_embedded_go,wbd_v4_fec2_product -run '^TestV4AndroidCold(FixedFailureClasses|DeadlineUnknownIsNotMisreported)$' ./internal/realityfront)
echo ANDROID_A34_ORIGINAL_GO_TLS_CLASSIFIER_HOST_PASS
for role in client server; do
  (cd legacy && go build -trimpath -buildvcs=false -tags wbd_v4_embedded_go,wbd_v4_fec2_product -o "$GITHUB_WORKSPACE/out/android-a3-linux/wbd-v4-$role" "./cmd/wbd-v4-$role")
done
python3 - <<'PY'
import hashlib,json,os,pathlib,struct
p=pathlib.Path("out/android-a3-linux")
sha={}
for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
    b=(p/name).read_bytes()
    assert b[:5]==b"\x7fELF\x02" and struct.unpack_from("<H",b,18)[0]==183,name
    sha[name]=hashlib.sha256(b).hexdigest()
a=json.loads((p/"validated-native/manifest.json").read_text())
m={"schema":"android-root-a3-original-linux-oracle/v1","source":os.environ["GITHUB_SHA"],
   "go_donor":a["donor_go"],"linux_native_sha256":sha,
   "android_bionic_go_sha256":a["artifacts"]["wbd-v4-client-arm64"]["sha256"],
   "android_bionic_rust_sha256":a["artifacts"]["libwbd_engine-arm64.so"]["sha256"],
   "linux_real_protocol":"NOT_RUN","android16_ksu_runtime":"NOT_RUN",
   "android_to_linux_live_protocol":"NOT_RUN",
   "physical_device":"DEFERRED_ACTIONS_FIRST"}
(p/"manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
PY
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iproute2 iptables openssl tcpdump
test -c /dev/net/tun
bash -n tools/m0-v4-public-real-linux-netns.sh
WBD_V4_PUBLIC_MODE=normal WBD_V4_PUBLIC_AUTO_IP=1 WBD_V4_PUBLIC_WIRE_AUDIT=1 \
  bash tools/m0-v4-public-real-linux-netns.sh out/android-a3-linux \
  >out/android-a3-linux/live-original-linux.log 2>&1 || {
    tail -120 out/android-a3-linux/live-original-linux.log >&2
    exit 1
  }
grep -Fq 'M0_PUBLIC_ORIGINAL_GO_V4_NORMAL_OFF_TWO_REAL_CLI_TLS_RUST_M4_TUN_UDP_STOP_PASS' out/android-a3-linux/live-original-linux.log
grep -Fq 'M0_PLAN028_REAL_AUTO_LEASE_NATIVE_IP_BOUND_PASS' out/android-a3-linux/live-original-linux.log
grep -Fq 'M0_PLAN028_TLS_REAL_TCP_REASSEMBLED_CLIENTHELLO_NO_PRELUDE_PASS' out/android-a3-linux/live-original-linux.log
python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("out/android-a3-linux")
r=json.loads(pathlib.Path("fixed-kernel-result/plan028-tls-wire-audit.json").read_text())
assert r["result"]=="REAL_TCP_STREAM_TLS_FIRST_FLIGHT_PASS"
assert r["client_first_payload"]=="TLS_Handshake_ClientHello"
assert r["server_first_payload"]=="TLS_Handshake_ServerHello"
assert r["server_early_application_bytes"]==0
assert r["session_id_length"]==32
assert 43 in map(int,r["extension_types"]) and 51 in map(int,r["extension_types"])
m=json.loads((p/"manifest.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
m["linux_real_protocol"]="PASS_ORIGINAL_LINUX_CLIENT_SERVER_NORMAL_OFF_TLS_LEASE_UDP_STOP"
m["linux_wire"]="PASS_STANDARD_TLS_CLIENTHELLO_NO_PRELUDE"
m["android16_ksu_runtime"]="NOT_RUN"
m["android_to_linux_live_protocol"]="NOT_RUN"
(p/"manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
print("ANDROID_A3_LINUX_SERVER_ORACLE_PASS_ANDROID_RUNTIME_NOT_RUN")
PY
 \
  ./internal/realityfront)
echo ANDROID_A34_ORIGINAL_GO_TLS_CLASSIFIER_HOST_PASS
for role in client server;do
  (cd legacy && go build -trimpath -buildvcs=false \
    -tags wbd_v4_embedded_go,wbd_v4_fec2_product \
    -o "$GITHUB_WORKSPACE/out/android-a3-linux/wbd-v4-$role" \
    "./cmd/wbd-v4-$role")
done
python3 - <<'PY'
import hashlib,json,os,pathlib,struct
p=pathlib.Path("out/android-a3-linux")
sha={}
for name in ("wbd-v4-client","wbd-v4-server","libwbd_engine.so"):
    b=(p/name).read_bytes()
    assert b[:5]==b"\x7fELF\x02" and struct.unpack_from("<H",b,18)[0]==183,name
    sha[name]=hashlib.sha256(b).hexdigest()
a=json.loads((p/"validated-native/manifest.json").read_text())
m={"schema":"android-root-a3-original-linux-oracle/v1","source":os.environ["GITHUB_SHA"],
   "go_donor":a["donor_go"],"linux_native_sha256":sha,
   "android_bionic_go_sha256":a["artifacts"]["wbd-v4-client-arm64"]["sha256"],
   "android_bionic_rust_sha256":a["artifacts"]["libwbd_engine-arm64.so"]["sha256"],
   "linux_real_protocol":"NOT_RUN","android16_ksu_runtime":"NOT_RUN",
   "android_to_linux_live_protocol":"NOT_RUN",
   "physical_device":"DEFERRED_ACTIONS_FIRST"}
(p/"manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
PY
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq iproute2 iptables openssl tcpdump
test -c /dev/net/tun
bash -n tools/m0-v4-public-real-linux-netns.sh
WBD_V4_PUBLIC_MODE=normal WBD_V4_PUBLIC_AUTO_IP=1 WBD_V4_PUBLIC_WIRE_AUDIT=1 \
  bash tools/m0-v4-public-real-linux-netns.sh out/android-a3-linux \
  >out/android-a3-linux/live-original-linux.log 2>&1 || {
    tail -120 out/android-a3-linux/live-original-linux.log >&2
    exit 1
  }
grep -Fq 'M0_PUBLIC_ORIGINAL_GO_V4_NORMAL_OFF_TWO_REAL_CLI_TLS_RUST_M4_TUN_UDP_STOP_PASS' out/android-a3-linux/live-original-linux.log
grep -Fq 'M0_PLAN028_REAL_AUTO_LEASE_NATIVE_IP_BOUND_PASS' out/android-a3-linux/live-original-linux.log
grep -Fq 'M0_PLAN028_TLS_REAL_TCP_REASSEMBLED_CLIENTHELLO_NO_PRELUDE_PASS' out/android-a3-linux/live-original-linux.log
python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("out/android-a3-linux")
r=json.loads(pathlib.Path("fixed-kernel-result/plan028-tls-wire-audit.json").read_text())
assert r["result"]=="REAL_TCP_STREAM_TLS_FIRST_FLIGHT_PASS"
assert r["client_first_payload"]=="TLS_Handshake_ClientHello"
assert r["server_first_payload"]=="TLS_Handshake_ServerHello"
assert r["server_early_application_bytes"]==0
assert r["session_id_length"]==32
assert 43 in map(int,r["extension_types"]) and 51 in map(int,r["extension_types"])
m=json.loads((p/"manifest.json").read_text())
assert m["source"]==os.environ["GITHUB_SHA"]
m["linux_real_protocol"]="PASS_ORIGINAL_LINUX_CLIENT_SERVER_NORMAL_OFF_TLS_LEASE_UDP_STOP"
m["linux_wire"]="PASS_STANDARD_TLS_CLIENTHELLO_NO_PRELUDE"
m["android16_ksu_runtime"]="NOT_RUN"
m["android_to_linux_live_protocol"]="NOT_RUN"
(p/"manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
print("ANDROID_A3_LINUX_SERVER_ORACLE_PASS_ANDROID_RUNTIME_NOT_RUN")
PY
