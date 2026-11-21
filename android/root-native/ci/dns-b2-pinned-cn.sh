#!/usr/bin/env bash
# B2 authentic pinned CN geosite source / Go matcher / real UDP TCP test.
# Host Linux only: NOT Android App/su/netd/KernelSU.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?Actions checkout required}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?expected source SHA missing}"
mkdir -p out/android-b2-cn-geosite
rev=41504eae2a11f305fe88cfc605cf6c105a80bf5a
archive="out/android-b2-cn-geosite/source-$rev.zip"
curl --fail --location --silent --show-error --retry 2 --connect-timeout 15 \
 --max-time 90 --proto '=https' --tlsv1.2 \
 "https://codeload.github.com/v2fly/domain-list-community/zip/$rev" \
 -o "$archive"
python3 experiments/android-root-probe/ci/cn-geosite-snapshot.py \
 "$archive" out/android-b2-cn-geosite >out/android-b2-cn-geosite/import-log.json
python3 - <<'PY'
import hashlib,json,pathlib
out=pathlib.Path("out/android-b2-cn-geosite")
data=(out/"wbd-cn-geosite.txt").read_bytes()
meta=json.loads((out/"cn-geosite-provenance.json").read_text())
expected="45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6"
assert hashlib.sha256(data).hexdigest()==expected,"pinned geosite immutable SHA mismatch"
assert meta["source_commit"]=="41504eae2a11f305fe88cfc605cf6c105a80bf5a"
assert meta["output_distinct_rules"]==8503
assert meta["kinds"]=={"domain":8431,"full":69,"regexp":3}
assert meta["text_sha256"]==expected
license=(out/"wbd-cn-geosite-license.txt").read_text()
assert "MIT License" in license and "V2Ray" in license
print("ANDROID_B2_PINNED_CN_GEOSITE_IMPORT_8503_PASS")
PY
export GO111MODULE=off GOTOOLCHAIN=local
export WBD_PINNED_CN_GEOSITE="$GITHUB_WORKSPACE/out/android-b2-cn-geosite/wbd-cn-geosite.txt"
go test -count=1 -timeout=65s -v \
 ./r0/go_overlay/internal/v4productcli/dnsnative \
 | tee out/android-b2-cn-geosite/go-matcher-wire.log
grep -Fq -- '--- PASS: TestPinnedCNGeosite8503FullTypedSnapshotAndNoSilentFallback' \
 out/android-b2-cn-geosite/go-matcher-wire.log
grep -Fq -- '--- PASS: TestPinnedCNGeositeOnRealUDPAndTCPDNSLoopback' \
 out/android-b2-cn-geosite/go-matcher-wire.log
grep -Fq -- '--- PASS: TestB2bSignedAPKRuleColdFileRequires0600NoSymlinkAndPinnedHash' \
 out/android-b2-cn-geosite/go-matcher-wire.log
# B5: same real pinned text through the Rust original-M4 full-type matcher.
# Host only; Go does not process DATA packets in the Android product.
cargo +1.85.1 test --locked -p wbd-engine --lib b5_cn8503 \
  -- --nocapture 2>&1 | tee out/android-b2-cn-geosite/rust-m4-cn-split.log
grep -Fq 'b5_cn8503_cold_match_domain_full_regex_and_no_false_suffix ... ok' \
  out/android-b2-cn-geosite/rust-m4-cn-split.log
grep -Fq 'b5_cn8503_cold_actual_pinned_rules_full_typed_when_supplied ... ok' \
  out/android-b2-cn-geosite/rust-m4-cn-split.log
printf '%s\n' 'ANDROID_B5_PINNED_CN8503_GO_TO_RUST_M4_FULL_TYPED_HOST_PASS'
python3 - <<'PY'
import hashlib,json,os,pathlib
out=pathlib.Path("out/android-b2-cn-geosite")
receipt={
 "schema":"wbd-android-b2-pinned-cn-geosite-go-loopback/v1",
 "source":os.environ["GITHUB_SHA"],
 "pinned_rule_source":"v2fly/domain-list-community@41504eae2a11f305fe88cfc605cf6c105a80bf5a",
 "pinned_rules_sha256":hashlib.sha256((out/"wbd-cn-geosite.txt").read_bytes()).hexdigest(),
 "rule_count":8503,"rule_types":{"domain":8431,"full":69,"regexp":3,"keyword":0},
 "real_go_matcher_full_typed_semantics":"PASS_FROM_GO_TEST",
 "real_dns_udp_tcp_loopback_with_pinned_cn_data":"PASS_FROM_GO_TEST",
 "android_production_cn_matcher_data_in_apk":"B2_JOB_ARTIFACT_ONLY_APK_JOB_MUST_VERIFY",
 "android_physical_and_tunnel_dns_socket_bind":"NOT_CONNECTED",
 "android_system_dns_interception":"NOT_CONNECTED",
 "android_p2_p3":"ENV_BLOCKED_ARM64_KVM_NOT_AVAILABLE"}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("ANDROID_B2_PINNED_CN_8503_GO_DNS_REAL_HOST_LOOPBACK_PASS")
PY
