#!/usr/bin/env bash
# Original Rust ONLY, fixed-capacity authenticated-M4 candidate DNS53 NAT.
# Real IPv4/UDP packet/checksum bytes, but NOT Android TUN/netd runtime.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?source checkout required}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?missing SHA}"
mkdir -p out/android-b2c2b-dns-flow
cargo +1.85.1 test --locked -p wbd-engine --lib b2c2b1_rust_udp53 \
  -- --nocapture 2>&1 | tee out/android-b2c2b-dns-flow/test.log
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
 "b2c2b2_m4_uses_only_tunnel_dns_source_and_owned_reply_ports"
]
for test in names:
 assert f"test v4_android_dns_udp_flow::tests::{test} ... ok" in log,test
assert "test result: ok. 5 passed;" in log,log[-1500:]
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
assert m4.count("android_dns_flows.rewrite_query(")==2
assert "android_dns_flows,*android_dns_hijack_ready" in m4
owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
entry=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
assert "dns_flows.rewrite_reply(" in owner
assert "drain_windows_authenticated_kind1(" in owner
assert "receiver.accept_authenticated_link(" in owner
assert "android_dns_flows.stop();" in entry
assert "android_dns_hijack_ready:false" in entry
assert "android_dns_hijack_ready:true" not in entry
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
 "m4_live_rewrite_query_and_reply":"CONNECTED_BUT_COLD_DISABLED",
 "android_system_resolver":"NOT_CONNECTED",
 "physical_scoped_dns_and_tunnel_reply_backend":"NOT_CONNECTED",
 "android16_p2_p3":"ENV_BLOCKED_KVM_NOT_AVAILABLE",
 "physical_ksu_p5":"NOT_RUN"
}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("ANDROID_B2C2B2_ORIGINAL_RUST_M4_DNS_TX_RX_STOP_SOURCE_GATE_PASS_COLD_DISABLED")
PY
