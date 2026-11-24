#!/usr/bin/env bash
# Real host DNS UDP/TCP loopback only: not Android system DNS or KSU.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?Actions checkout required}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?source required}"
mkdir -p out/android-b1-dnsnative
export GO111MODULE=off GOTOOLCHAIN=local
go test -count=1 -timeout=45s -v \
  ./r0/go_overlay/internal/v4productcli/dnsnative \
  | tee out/android-b1-dnsnative/wire-tests.log
grep -Fq "TestOriginalQNameSelectsCNPhysicalOrTunnelWithoutFakeIP" out/android-b1-dnsnative/wire-tests.log
grep -Fq -- "--- PASS: TestB2c3BootstrapPhysicalRealUDP53AndSameEndpointTCP" out/android-b1-dnsnative/wire-tests.log
grep -Fq -- "--- PASS: TestB2c3BootstrapCompressedCNAMEAAndAnswerIdentity" out/android-b1-dnsnative/wire-tests.log
grep -Fq -- "--- PASS: TestB2c3BootstrapRejectsMalformedNameOrUnavailablePhysical" out/android-b1-dnsnative/wire-tests.log
grep -Fq "TestTruncatedUDPOnlyTCP53SameEndpointAndPath" out/android-b1-dnsnative/wire-tests.log
grep -Fq "TestRefuseCrossFallbackIfSelectedPathFails" out/android-b1-dnsnative/wire-tests.log
grep -Fq "TestConcurrentQueriesCoalesceWithoutBackgroundTimers" out/android-b1-dnsnative/wire-tests.log
grep -Fq -- "--- PASS: TestB69IPv6DestinationRealUDPTCPSharedIPv4Upstream" out/android-b1-dnsnative/wire-tests.log
grep -Fq -- "--- PASS: TestB68DownstreamDNSRealSharedUDPTCPAndStop" out/android-b1-dnsnative/wire-tests.log
grep -Fq -- "--- PASS: TestB66SystemDNSRealUDPTCPModeAndStop" out/android-b1-dnsnative/wire-tests.log
grep -Fq -- "--- PASS: TestB64ActualAppTCPDNSPhysicalTunnelAndCN" out/android-b1-dnsnative/wire-tests.log
grep -Fq "PASS" out/android-b1-dnsnative/wire-tests.log
go test -count=1 -timeout=45s -v ./r0/go_overlay/internal/v4productcli/rootjournal \
  -run '^(TestB6(4OwnedTCPDNSSelectedAndAllAppRoutesRestore|5TetherOwnedForwardingAndRestore|6SystemDNSSelectedUIDRouteAndRestore|7CLATScopeOriginalIPv4OnIPv6Underlay|8TetherDNSExactDownstreamAndRestore|9SystemDNS6SelectedUIDRouteAndRestore)|TestB70IPv6OwnedCarrierAndRestore|TestB71IPv6TetherAndColdPeerScope)$' \
  | tee out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB64OwnedTCPDNSSelectedAndAllAppRoutesRestore" out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB65TetherOwnedForwardingAndRestore" out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB66SystemDNSSelectedUIDRouteAndRestore" out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB67CLATScopeOriginalIPv4OnIPv6Underlay" out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB68TetherDNSExactDownstreamAndRestore" out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB69SystemDNS6SelectedUIDRouteAndRestore" out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB70IPv6OwnedCarrierAndRestore" out/android-b1-dnsnative/app-tcp-owner-tests.log
grep -Fq -- "--- PASS: TestB71IPv6TetherAndColdPeerScope" out/android-b1-dnsnative/app-tcp-owner-tests.log
python3 - <<'PY'
import hashlib,json,os,pathlib
out=pathlib.Path("out/android-b1-dnsnative")
source=pathlib.Path("r0/go_overlay/internal/v4productcli/dnsnative/dns.go").read_bytes()
receipt={
 "schema":"wbd-android-b1-dns-wire-loopback/v1",
 "source":os.environ["GITHUB_SHA"],
 "component_sha256":hashlib.sha256(source).hexdigest(),
 "host_udp_tcp_loopback_wire":"PASS_FROM_REAL_GO_TEST",
 "fixed_production_upstreams":["223.5.5.5:53","1.1.1.1:53"],
 "local_loopback_ports":"EPHEMERAL_NOT_PORT_53",
 "selected_path_dialer":"DEPENDENCY_INJECTION_TEST_ONLY",
 "android_physical_network_and_tun_binding":"COMPILED_NETD_PHYSICAL_BOOTSTRAP_NOT_DEVICE_RUN",
 "b2c3_real_host_dns_bootstrap_udp_tcp_cname":"PASS",
 "android_system_resolver_dns_interception":"NOT_RUN",
 "android_go_rust_m4_dns_interception":"NOT_CONNECTED",
 "physical_android16_ksu":"DEFERRED",
 "android_p2_p3":"ENV_BLOCKED_NO_ACCESSIBLE_ARM64_KVM"}
(out/"receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print("ANDROID_B1_DNS_WIRE_REAL_LOOPBACK_ONLY_PASS")
PY

