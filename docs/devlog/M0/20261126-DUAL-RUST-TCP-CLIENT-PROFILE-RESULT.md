# M0 client CPU profile result and continuation

Exact existing B native x86 product (86e3ec3, build artifact15113365713) with same clean download, run45813361467, artifact15113333515 verified ZIP SHA256. 2427 samples, lost=0, record terminated by SIGINT after test, valid report. Top self sample is kernel spin unlock 8.12%, wake branch 5.97% (packet_rcv 3.71%, tcp_data_ready 2.22%); chacha open 4.08%, native task switch 3.26%, shared TUN switch 2.97%, inner IPv4 encode 1.61%, malloc 1.07%, TCP checksum 0.95%. Both M4 thread names truncated identically; cannot assign per-symbol totals to TX specifically. Diagnostic workload not a new performance qualification. Earlier measured TX CPU and reverse packet growth require reducing actual per-packet/kernel work, not just micro-optimizing TCP arithmetic. First small candidate separate input turn count from generated TCP staging count, keeping original 32-packet RAW cap and no wait to fill. Preserve current compiler comparison independent.

H2454/H2455 context_refs accumulation exceeded bounded hot cursor; main run45813471410 FAIL (scope audit unbounded context_refs). Correct by retaining only active references; historical docs remain in git; no governance checker changes, no historical PASS rewrite. Previous H2453 main PASS. Older refs retained in this index:
- docs/decisions/M0-DUAL-RUST-TCP-CONSTRUCTION-20261126.md
- docs/devlog/M0/20261126-DUAL-RUST-TCP-REGISTRATION.md
- docs/devlog/M0/20261126-DUAL-RUST-TCP-CORE-HANDOFF.md
- docs/devlog/M0/20261126-DUAL-RUST-TCP-ENDPOINT-HANDOFF.md
- docs/devlog/M0/20261126-DUAL-RUST-TCP-NORMAL-HANDOFF.md
- docs/devlog/M0/20261126-DUAL-RUST-TCP-NORMAL-RESULT.md
- docs/devlog/M0/20261126-DUAL-RUST-TCP-CLEAN-ABBA-INTENT.md
- docs/evidence/M0/20261126-DUAL-RUST-TCP-CLEAN-ABBA.json
- docs/devlog/M0/20261126-DUAL-RUST-TCP-CPU-TOOLCHAIN-INTENT.md
- docs/devlog/M0/20261126-DUAL-RUST-TCP-CLIENT-PROFILE-FIX.md
