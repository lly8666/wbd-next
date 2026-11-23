#!/usr/bin/env bash
# Original Rust ONLY, fixed-capacity authenticated-M4 candidate DNS53 NAT.
# Real IPv4/UDP packet/checksum bytes, but NOT Android TUN/netd runtime.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?source checkout required}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?missing SHA}"
mkdir -p out/android-b2c2b-dns-flow
cargo +1.85.1 test --locked -p wbd-engine --lib b2c2b \
  -- --nocapture 2>&1 | tee out/android-b2c2b-dns-flow/test.log
# B3 source-locked genuine original flow: two independent captured App DNS
# resolver IPs are tunneled and inverted without cross-transaction leakage.
cargo +1.85.1 test --locked -p wbd-engine --lib \
  b3_real_m4_captured_app_dns_two_resolvers_inverse_and_stop \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B6 independent full physical-TC + non-CN M3 inverse + TCP53 host pair.
cargo +1.85.1 test --locked -p wbd-engine --lib b6_original_m4 \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B29: Normal and Fixed/Auto reuse the same original M4 DNS classifier.
cargo +1.85.1 test --locked -p wbd-engine --lib \
  b29_original_m4_dns_feature7_requires_real_fec2_receiver \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B7 real App retries reuse bounded physical DNS generation ownership.
cargo +1.85.1 test --locked -p wbd-engine --lib b7_physical_dns \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B55: run the SAME original Android Game M4 scheduler pure Rust tests.
cargo +1.85.1 test --locked -p wbd-engine --lib --features m0_v4_embedded_go,fec2_product_record b55_android_game_ -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B56 same ORIGINAL Game M3/PN/ACK worker receives short RAW bursts
# and waits for kernel data/Stop without periodic 1s RX polling.
cargo +1.85.1 test --locked -p wbd-engine --lib --features m0_v4_embedded_go,fec2_product_record b56_android_game_ -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B57 original Game2/4 DF0 RFC791 + DF1 local PMTU, same B16 code.
cargo +1.85.1 test --locked -p wbd-engine --lib b57_android_game_ -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B59: test real 4096B-bounded EDNS physical answer fragmentation
# to the SAME original TUN in Normal and Game2/4; no TCP DNS proxy.
cargo +1.85.1 test --locked -p wbd-engine --lib b59_physical_dns_ \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B16: the same production IPv4 fragment and local ICMP codec runs on Host.
cargo +1.85.1 test --locked -p wbd-engine --lib b16_ \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
# B18/B19 original Rust PLAN027 quality + same-owner Auto revision host tests.
cargo +1.85.1 test --locked -p wbd-engine --lib \
  --features m0_v4_embedded_go,fec2_product_record b18_ \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
cargo +1.85.1 test --locked -p wbd-engine --lib \
  --features m0_v4_embedded_go,fec2_product_record b19_ \
  -- --nocapture 2>&1 | tee -a out/android-b2c2b-dns-flow/test.log
python3 - <<'PY'
from pathlib import Path
import hashlib,json,os
out=Path("out/android-b2c2b-dns-flow")
log=(out/"test.log").read_text()
names=[
 "b2c2b1_rust_udp53_tunnel_real_ipv4_packet_pair_inverse_and_checksums",
 "b2c2b1_rust_udp53_rejects_wrong_upstream_id_qname_and_replay",
 "b2c2b1_rust_udp53_owner_has_exact_bounded_capacity_and_stop",
 "b2c2b1_rust_udp53_rejects_fragments_and_malformed_without_packet_mutation",
 "b2c2b2_m4_uses_only_tunnel_dns_source_and_owned_reply_ports",
 "b2c2b3_physical_owned_ipv4_udp53_real_question_reply_checksum",
 "b2c2b3_physical_no_cross_flow_no_unowned_reply_after_stop",
 "b2c2b3_b4_physical_two_app_resolvers_reverse_order_and_stop"
]
for test in names:
 module=("v4_android_dns_physical_flow" if test.startswith("b2c2b3_")
         else "v4_android_dns_udp_flow")
 assert f"test {module}::tests::{test} ... ok" in log,test
assert "test result: ok. 8 passed;" in log,log[-1500:]
assert "test v4_android_dns_udp_flow::tests::b3_real_m4_captured_app_dns_two_resolvers_inverse_and_stop ... ok" in log
assert "test result: ok. 1 passed;" in log
assert 'test v4_android_dns_route::tests::b6_original_m4_dns_three_compat_modes_and_tcp53_passthrough ... ok' in log
assert 'test v4_android_dns_route::tests::b6_original_m4_cn_physical_tc_inverse_and_noncn_tunnel_inverse ... ok' in log
assert 'test result: ok. 2 passed;' in log
for test in (
 "b55_android_game_idle_event_wait_not_fixed_250ms_spin",
 "b55_android_game_game4_fec_and_health_due_not_delayed",
 "b55_android_game_business_burst_bounded_and_idle_reset"
):
 assert f"test v4_android_game_schedule::tests::{test} ... ok" in log
assert 'test result: ok. 3 passed;' in log
for test in (
 "b56_android_game_rx_event_driven_idle_not_periodic_1s",
 "b56_android_game_raw_rx_short_burst_and_stop_event_turn"
):
 assert f"test v4_android_game_schedule::tests::{test} ... ok" in log
assert 'test result: ok. 2 passed;' in log
assert 'test v4_android_dns_route::tests::b29_original_m4_dns_feature7_requires_real_fec2_receiver ... ok' in log
assert 'test v4_android_dns_physical_flow::tests::b7_physical_dns_app_retransmit_reuses_generation_slot_not_other_apps ... ok' in log
assert 'test v4_android_dns_physical_flow::tests::b7_physical_dns_retransmit_expiry_and_query_identity ... ok' in log
for scenario in (
 "b16_ordinary_df0_fragments_restore_all_ipv4_payload",
 "b16_df1_returns_icmp_pmtu_not_a_fragment",
 "b16_ipv4_options_copy_bit_first_and_later_fragments",
 "b16_existing_fragment_offset_mf_survives_refragment",
 "b16_bad_option_length_is_not_fragmented",
):
 assert f"test v4_android_ipv4_mtu::tests::{scenario} ... ok" in log
assert "test result: ok. 5 passed;" in log
for test in (
 "b59_physical_dns_edns_large_response_normal_game_ipv4_reassembles",
 "b59_physical_dns_small_reply_unchanged_one_tun_write",
 "b59_physical_dns_partial_tun_write_never_reports_complete"
):
 assert f"test v4_android_dns_physical_flow::b59_tests::{test} ... ok" in log,test
for test in (
 "b57_android_game_df0_udp_oversize_real_fragment_payload_roundtrip",
 "b57_android_game_large_udp_min_ipv4_mtu_bounded_dispatch",
 "b57_android_game_df1_local_pmtu_and_failed_dispatch"
):
 assert f"test v4_android_ipv4_mtu::tests::{test} ... ok" in log
assert "test result: ok. 3 passed;" in log
assert "test v4_embedded_go::b18_original_linux_android_quality_30_field_mapping ... ok" in log
assert "test v4_embedded_go::b19_original_android_auto_report_scopes_each_revision ... ok" in log
wire=Path("crates/wbd-engine/src/v4_android_dns_udp_flow.rs").read_text()
lib=Path("crates/wbd-engine/src/lib.rs").read_text()
m4=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
assert 'const TUNNEL_DNS:[u8;4]=[1,1,1,1];' in wire
assert 'const CAP:usize=64;' in wire
assert 'const MAX_AGE_MS:u64=12_000;' in wire
assert 'fn rewrite_query(' in wire and 'fn rewrite_reply(' in wire
# The negative fixture must mutate a NONZERO length byte. The earlier
# test p[24]=0 wrote zero onto an already-zero UDP high length byte and
# falsely expected a valid original query to fail admission.
assert '2=>p[25]=0, // corrupt actual nonzero UDP length LOW byte' in wire
assert 'fn set_checksums(' in wire and 'fn stop(&mut self)' in wire
assert 'mod v4_android_dns_udp_flow;' in lib
# Changes to any original-Rust Android DNS module MUST trigger the full
# source-locked product workflow, not governance-only green.
workflow=Path(".github/workflows/android-root-product-a1.yml").read_text()
assert '      - "crates/wbd-engine/src/v4_android_dns_*.rs"' in workflow

assert 'hijack_enabled.write(0)' in m4
assert m4.count("tun.read_ip_scatter(")==1
# B15 adds the real Fixed/DF0 jumbo DNS rewrite on the same M4 TX owner.
assert m4.count("android_dns_flows.rewrite_query(")==3
assert "android_dns_flows,*android_dns_hijack_ready" in m4
owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
entry=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
assert "dns_flows.rewrite_reply(" in owner
assert "drain_windows_authenticated_kind1(" in owner
assert "receiver.accept_authenticated_link(" in owner
assert "android_dns_flows.stop();" in entry
assert "android_dns_hijack_ready:false" in entry
assert "android_dns_hijack_ready:true" not in entry
assert "e.android_dns_hijack_ready=true;" in entry
assert "pub extern \"C\" fn wbd_m0_embedded_go_android_tunnel_dns_enable(" in entry
assert "e.android_tun.is_none()" in entry and "e.client_lease_ipv4.is_none()" in entry
assert "android_dns_physical_ready:false" in entry
assert "android_dns_physical_ready:true" not in entry
# B5 retains exactly one M4 TUN reader and both Rust-owned DNS paths.
assert 'mod v4_android_cn_dns;' in lib
assert 'e.android_cn_dns=Some(Arc::new(matcher));' in entry
assert m4.count('crate::v4_android_dns_route::choose(')==2
assert 'DnsRoute::PhysicalUDP' in m4
assert 'DnsRoute::TunnelUDP' in m4
assert 'DnsRoute::TCP53OriginalTunnel' in m4
assert 'android_cn_dns.is_some()' in m4
assert m4.count("tun.read_ip_scatter(")==1

assert 'pub extern "C" fn wbd_m0_embedded_go_android_physical_dns_enable(' in entry
assert "e.android_dns_physical_ready=true;" in entry
physical=Path("crates/wbd-engine/src/v4_android_dns_physical_flow.rs").read_text()
platform=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
assert 'struct PhysicalDnsUdpFlows' in physical
assert 'FIRST_DNS_ID:u16=0x7100' in physical
assert 'MAX_AGE_MS:u64=12_000' in physical
assert 'pub(crate) fn receive(' in physical and 'pub(crate) fn prepare(' in physical
assert m4.count("physical_flows.prepare(")==2
assert 'physical_flows.receive(' in m4 and 'physical_flows.stop();' in m4
assert m4.count('if new_slot{physical_flows.cancel(id);}')==2
assert 'let identical=self.entries.iter().position(' in physical
assert 'Ok((dns.len(),synthetic,new_slot))' in physical
assert 'AndroidBoundPhysicalDnsUdp::open(' in m4
assert 'wait_tun_and_physical_dns(' in m4
assert 'tun.write_scoped_physical_dns_ip(' in m4
assert 'pub struct AndroidBoundPhysicalDnsUdp' in platform
assert 'bind_underlay_socket(fd.as_raw_fd(),network_handle,interface)?' in platform
assert 'getsockopt(' in platform and 'getsockname(' in platform
assert 'actual[expected.as_bytes().len()]!=0' in platform
assert 'pub fn write_scoped_physical_dns_ip(' in platform
# B59 original generation produces IPv4 DNS fragments only after the
# owned physical socket plus original App ID/QNAME/lease have matched.
game=Path("crates/wbd-engine/src/v4_android_game_m4.rs").read_text()
assert 'pub(crate) fn emit_physical_dns_tun_reply(' in physical
assert 'crate::v4_android_ipv4_mtu::fragment(' in physical
assert m4.count("emit_physical_dns_tun_reply(")==1
assert game.count("emit_physical_dns_tun_reply(")==1
assert 'frame.single_business_payload_mtu' in m4
assert 'inner_mtu,&mut physical_fragment' in game
assert 'pub fn write_scoped_physical_dns_ipv4_fragment(' in platform
assert m4.count('write_scoped_physical_dns_ipv4_fragment(')==1
assert game.count('write_scoped_physical_dns_ipv4_fragment(')==1
assert "std::net::" not in wire and "read_ip_scatter" not in wire
receipt={
 "schema":"wbd-android-b2c2b1-original-rust-dns-udp-inverse-map/v1",
 "source":os.environ["GITHUB_SHA"],
 "rust_udp_packet_pair_checksum_and_inverse_map":"PASS",
 "rust_dns_txid_qname_src_and_reply_validation":"PASS",
 "bounded_slots":64,"expiry_ms":12000,
 "capacity_fail_closed_and_stop_revoke":"PASS",
 "malformed_fragment_no_mutation":"PASS",
 "source_sha256":hashlib.sha256(wire.encode()).hexdigest(),
 "original_android_arm64_rust_elf_compilation":"SEPARATE_JOB_PENDING",
 "m4_dns_capture_hijack_enabled":0,
 "m4_tx_rx_same_owner_dns_hooks":"SOURCE_GATE_PASS",
 "m4_live_rewrite_query_and_reply":"COLD_OPTIN_WIRED_SOURCE_AND_HOST_ONLY",
 "b3_original_app_dns_two_resolvers_ipv4_udp_inverse_and_stop":"HOST_PASS",
 "android_tunnel_dns_real_native_cold_grant":"REQUIRES_REAL_TLS_LEASE_RAW_TUN",
 "android_tunnel_dns_physical_device_e2e":"NOT_RUN",
 "android_system_resolver":"NOT_CONNECTED",
 "physical_scoped_dns_and_tunnel_reply_backend":"EXPLICIT_APP_UDP53_PHYSICAL_COLD_GRANT_WIRED_DEVICE_NOT_RUN",
 "physical_actual_udp53_socket":"NOT_OPENED_DEFAULT_FALSE",
 "physical_reply_aead_authentication":"NOT_APPLICABLE_CONNECTED_KERNEL_UDP_ID_QNAME",
 "physical_ipv4_checksums_original_resolution_rewrite":"HOST_PASS",
 "b59_physical_edns_ipv4_original_tun_fragment_576_1260_1460":"HOST_PASS",
 "b59_normal_game_same_tun_fragmented_dns_source":"SOURCE_WIRED_DEVICE_NOT_RUN",
 "b59_real_android_physical_dns_jumbo_e2e":"NOT_RUN",
 "android16_p2_p3":"ENV_BLOCKED_KVM_NOT_AVAILABLE",
 "physical_ksu_p5":"NOT_RUN"
}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("ANDROID_B59_PHYSICAL_EDNS_JUMBO_NORMAL_GAME_ORIGINAL_TUN_IPV4_FRAGMENT_HOST_PASS")
print("ANDROID_B3_ORIGINAL_GO_RUST_TUNNEL_UDP_DNS_OPTIN_AND_INVERSE_MAP_HOST_PASS")
print("ANDROID_B2C2C_ORIGINAL_RUST_M4_PHYSICAL_DNS_UDP_AND_TUNNEL_OWNER_SOURCE_GATE_PASS_COLD_DISABLED")
print("ANDROID_B4_RUST_M4_PHYSICAL_DNS_COLD_GRANT_TWO_RESOLVERS_STOP_HOST_PASS")
print("ANDROID_B6_M4_TWO_DNS_BACKENDS_TC_TCP53_SINGLE_TUN_READER_HOST_PASS")
print("ANDROID_B7_PHYSICAL_DNS_APP_RETRANSMIT_INVERSE_MAP_REUSE_STOP_HOST_PASS")
PY
