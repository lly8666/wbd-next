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
# Source-locked Android root cold RST owner; host Go tests use only a fake iptables runner.
mkdir -p legacy/internal/v4productcli/rstguard
cp r0/go_overlay/internal/v4productcli/rstguard/*.go legacy/internal/v4productcli/rstguard/
(cd legacy && go test -count=1 ./internal/v4productcli/rootjournal)
echo ANDROID_B31_ORIGINAL_ROOT_UID_PEER_EXCEPTION_HOST_PASS
(cd legacy && go test -count=1 ./internal/v4productcli/rstguard)
echo ANDROID_A35_FAKE_RUNNER_RST_GUARD_JOURNAL_HOST_PASS
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
# A52: run the EXACT main H2229 cumulative appearance ACK ledger on host,
# including Android out-of-order wrap and 10ms deadline negative cases.
# Use the shared crate because ACK/SACK now consumes wbd-platform types.
# Android Bionic/owned RAW sendto remain separate device qualifications.
cargo +1.85.1 test --locked -p wbd-engine --lib --features fec2_product_record v4_presentation_ack::tests
echo ANDROID_A52_MAIN_H2229_AUTH_CUMULATIVE_ACK_RUST_HOST_PASS
# A46: run EXACT main/Windows H2216 IPv4 TTL NAT fixture against the
# same Rust wbd-platform source used by Android and Linux. Public DATA and
# pure ACK must pass; IP checksum corruption and zero TTL must still fail.
cargo +1.85.1 test --locked -p wbd-platform --lib \
  h2216_original_windows_128_to_116_client_public_nat_data_and_ack
echo ANDROID_A46_MAIN_WINDOWS_H2216_ROUTED_TTL_DATA_ACK_RUST_HOST_PASS
# A48: real Rust parser executes a checksum-only Android M3-pending fixture.
# The existing strict Linux/Windows DATA parser and M3 AEAD/PN are unchanged.
cargo +1.85.1 test --locked -p wbd-platform --lib a48_android_m3_pending_accepts_only_tcp_checksum_drift_as_untrusted
echo ANDROID_A48_ANDROID_BIONIC_TCP_CHECKSUM_ONLY_M3_PENDING_HOST_PASS
cargo +1.85.1 test --locked -p wbd-platform --lib a49_single_pass_matches_a48_two_pass_android_admission
echo ANDROID_A49_ANDROID_SINGLE_PASS_PARSER_EQUIVALENCE_HOST_PASS
cargo +1.85.1 build --locked --release -p wbd-engine \
  --features m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record \
  >out/android-a3-linux/rust-build.log 2>&1 || {
    tail -90 out/android-a3-linux/rust-build.log >&2
    exit 1
  }
cp target/release/libwbd_engine.so out/android-a3-linux/
export CGO_LDFLAGS="-L$GITHUB_WORKSPACE/target/release -lwbd_engine"
export LD_LIBRARY_PATH="$GITHUB_WORKSPACE/target/release"
# A34 source-locked original-Go TLS cold error/deadline classifier regression.
(cd legacy && timeout 180s go test -count=1 -run '^TestV4AndroidCold(FixedFailureClasses|DeadlineUnknownIsNotMisreported)$' ./internal/realityfront)
echo ANDROID_A34_ORIGINAL_GO_TLS_CLASSIFIER_HOST_PASS
# A38: actually run the genuine original protected admission 3-way
# self-signed TLS policy test (not a fake TLS verdict or source grep).
(cd legacy && timeout 180s go test -count=1 -run '^TestA38OriginalProtectedAdmissionCertVerifyPolicy$' ./internal/realityfront)
echo ANDROID_A38_ORIGINAL_PROTECTED_TLS_CERT_POLICY_REAL_GO_HOST_PASS
# B89: original TLS/epoch/multi-lane cold integration and Android-specific Rust mapping.
(cd legacy && timeout 180s go test -count=1 -v -run '^(TestPLAN028SharedNormalPerClientFECProtectedCapability|TestPLAN028MixedOne443OriginalProtectedNormalGame2Game4ColdPolicy|TestM0V4OriginalTLSGame2And4AuthenticatedColdSet|TestH2401GameColdAttemptTracksFreshLane1BeforeReply|TestFECGameProtectedV4ProfileWireOffAndFailClosed|TestA38OriginalProtectedAdmissionCertVerifyPolicy)$' ./internal/realityfront)
cargo +1.85.1 test --locked -p wbd-engine --lib --features fec2_product_record v4_android_game_cold::tests
# A41 actual original-Go Native Address parser, built with the native
# product tags (no fake Android guest, no fabricated lease OS receipt).
(cd legacy && timeout 180s go test -count=1 \
  -tags wbd_v4_embedded_go,wbd_v4_fec2_product \
  -run '^TestA41AndroidOriginalOwnedTunIPv4NativeGetifaddrs$' \
  ./internal/v4productcli)
echo ANDROID_A41_ORIGINAL_ANDROID_GETIFADDRS_LEASE32_REAL_GO_HOST_PASS
# A43: execute real kernel BPF attach/replacement with and without
# donor initial Ethernet port filter, not just Go BPF VM.
(cd legacy && timeout 180s go test -count=1 -run TestA43OriginalAndroidDetachedClientRXKernelQuiesce ./internal/faketcp)
echo ANDROID_A43_ORIGINAL_GO_CLIENT_RX_REAL_KERNEL_QUIESCE_HOST_PASS
# A44 source-locked genuine Go business witness decision (no synthetic PASS).
(cd legacy && timeout 180s go test -count=1 -tags wbd_v4_embedded_go,wbd_v4_fec2_product -run TestA44OriginalAndroidBusinessReceiptClasses ./internal/v4productcli)
echo ANDROID_A44_ORIGINAL_RUST_BUSINESS_WITNESS_CLASSIFIER_REAL_GO_HOST_PASS
# A45: original Go product classifies only actual native return-path counters.
# Real Rust ARM64 code is built, linked and symbol-checked by the same workflow.
(cd legacy && timeout 180s go test -count=1 -tags wbd_v4_embedded_go,wbd_v4_fec2_product -run TestA45OriginalAndroidReturnPathReceiptClasses ./internal/v4productcli)
echo ANDROID_A45_ORIGINAL_RETURN_PATH_AND_ICMP_CLASSIFIER_GO_HOST_PASS
# A47 original Go renderer against real compiled original Rust bridge.
(cd legacy && timeout 180s go test -count=1 -tags wbd_v4_embedded_go,wbd_v4_fec2_product -run 'Test(A47OriginalNumericNativeM4Snapshots|B58OriginalGoColdSixteenSelectedUIDs)' ./internal/v4productcli)
echo ANDROID_A47_REAL_ORIGINAL_GO_NUMERIC_M4_SNAPSHOT_HOST_PASS
if [[ "${WBD_ANDROID_WIRING_MATRIX:-0}" == 1 ]];then
  python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("out/android-a3-linux/host-cold-receipt.json")
p.write_text(json.dumps({"source":os.environ["GITHUB_SHA"],"original_go_tls_admission_and_game_cold_set":"PASS","android_rust_lane_canonicalization":"PASS","a48_a49_android_parser":"PASS","linux_dataplane":"NOT_RUN","android_peer_m4":"NOT_PROVEN"},indent=2)+"\n")
PY
  echo ANDROID_WIRING_HOST_COLD_ORACLE_PASS_NO_LINUX_DATAPLANE_RUN
  exit 0
fi
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
# Publish exactly the binaries this native oracle is about to execute.
(cd out/android-a3-linux && sha256sum wbd-v4-client wbd-v4-server libwbd_engine.so > SHA256SUMS)
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
