#!/usr/bin/env bash
# B2c2a authentic ORIGINAL Rust Android M4 ONE-TUN readv DNS53 observation.
# Host byte-level parser qualification, NOT kernel Android DNS interception.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?source checkout required}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?source required}"
mkdir -p out/android-b2c2-rust-ingress
cargo +1.85.1 test --locked -p wbd-engine --lib \
  b2c2_original_rust_m4 \
  -- --nocapture | tee out/android-b2c2-rust-ingress/test.log
python3 - <<'PY'
from pathlib import Path
import json,os,hashlib
out=Path("out/android-b2c2-rust-ingress")
log=(out/"test.log").read_text()
names=[
 "b2c2_original_rust_m4_tun_udp53_observes_real_query_bytes_without_mutation",
 "b2c2_original_rust_m4_tun_tcp53_is_only_flow_candidate",
 "b2c2_original_rust_m4_one_scatter_read_incomplete_never_second_reader",
 "b2c2_original_rust_m4_dns53_rejects_malformed_and_spoof_query",
 "b2c2_original_rust_m4_dns53_opt_and_bounded_wire_identity"
]
for name in names:
 assert f"test v4_android_dns_ingress::tests::{name} ... ok" in log,(name,log[-800:])
assert "test result: ok. 5 passed;" in log,log[-900:]
m4=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
lib=Path("crates/wbd-engine/src/lib.rs").read_text()
wire=Path("crates/wbd-engine/src/v4_android_dns_ingress.rs").read_text()
# The only TUN read remains the original Rust data path, not any Go,
# Java, JNI or independent DNS worker. All original seal/send remains.
assert m4.count("tun.read_ip_scatter(")==1
assert m4.count("fn tun_worker(")==1
assert "let read=tun.read_ip_scatter(" in m4
assert "if !original_complete_ipv4_head(head,n,lease)" in m4
assert "observe_ipv4_dns53(head,n)" in m4
assert m4.index("original_complete_ipv4_head(head,n,lease)") < m4.index("observe_ipv4_dns53(head,n)") < m4.index("seal_android_read_normal_ip(")
assert "android_normal_off_frame_budget(" in m4
assert "fn wbd_m0_embedded_go_loop_dns_ingress_observed(" in m4
assert "hijack_enabled.write(0)" in m4
assert "mod v4_android_dns_ingress;" in lib
assert "fn observe_ipv4_dns53" in wire
assert "std::thread" not in wire and "std::net::" not in wire
receipt={
 "schema":"wbd-android-b2c2a-original-rust-tun-dns-observer/v1",
 "source":os.environ["GITHUB_SHA"],
 "pure_rust_ipv4_udp_tcp_dns53_wire_tests":"PASS_FIVE_HOST_TESTS",
 "original_m4_single_tun_readv_source":"CONFIRMED_NO_ADDITIONAL_TUN_READER",
 "original_m1_m3_aeAD_pn_path":"PRESERVED_SOURCE_ONLY",
 "dns_observation_module_sha256":hashlib.sha256(wire.encode()).hexdigest(),
 "android_rust_m4_observed_stats_ffi":"CROSS_BUILD_PENDING",
 "dns_packet_diversion_or_local_answer":"DISABLED",
 "tunnel_dns_1_1_1_1_real_live_roundtrip":"NOT_CONNECTED",
 "android_system_resolver_udp_tcp_53":"NOT_CONNECTED",
 "real_android16_arm64_guest_p2_p3":"ENV_BLOCKED_NO_KVM",
 "physical_ksu_p5":"NOT_RUN"
}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("ANDROID_B2C2A_ORIGINAL_RUST_SINGLE_TUN_DNS53_OBSERVER_HOST_PASS_NO_REDIRECT")
PY
