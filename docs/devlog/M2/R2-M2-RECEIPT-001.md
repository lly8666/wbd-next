# R2-M2-RECEIPT-001 · scoped atomic implementation

Owner: M2 | reservation_revision=2 | assignment_epoch=1 | branch=work/m2-r2-recovery.

## Intent and boundaries
- Added a pure Rust state module to wbd-recovery with an explicit authenticated-receipt input type. The constructor is only legal after an M3-verified record open; it does not perform authentication. M0 must own the verified-record-to-receipt adapter at integration. No raw wire bytes are passed to the release method.
- Pages are 256-bit aligned, sorted, capped at eight, and reject received bits beyond largest_data_pn. Zero is negative evidence only in an explicitly reported page and only for an extant data shadow. There is no cumulative prefix and no shadow for burned/control PN.
- New report_seq follows u32 serial order; duplicate/older positive bits can still release once but cannot create new hole evidence or witness timing.
- A small three-distinct-original-data-witness RACK-like gate or PTO can nominate repair. Each candidate has PN, origin generation, retry epoch, a short dispatch deadline, and the same immutable frozen handle. Up to 32 per poll, at most two accepted/uncertain repair attempts. Expiration releases once; no socket, seal, PN allocator, engine or platform import.
- All clocks supplied as MonoNs; bounded capacity configured at construction. Tests prefixed r2_ live in the library test binary so the already-installed worker-native Actions consumer runs exactly that binary.

## Deliberate non-qualification / M0 boundary
- This is an isolated minimal receipt state, not engine-connected receipt wire decoding, RX feedback generation, actual M1 arena memory layout, M3 ciphertext authentication, real TX outcome batching, full global 1s F/R/L budget, full RTT estimator, or large-PPS scheduler qualification. RECOVERY_ENGINE_READY=false, product/performance/physical NOT_RUN.
- M0 must supply the authenticated opposite-direction lane/epoch binding and enforce the full send-result and shared budget integration before enabling it. No changes to root Cargo, engine, platform, public types, wire codec or CI have been made.
- Verification is pending the exact-source native Actions run; no PASS is claimed by this initial code commit.

Next after S: inspect actual worker-native/Governance runs and artifacts; add exact evidence receipt S, then separate cursor-only H and recheck remote.

## Observed exact-SOURCE Actions (post-S; no rerun/dispatch)
- [worker-native 38538225302 attempt 1](https://github.com/lly8666/wbd-next/actions/runs/38538225302): SUCCESS. Ubuntu 24.04 x86_64, Rust 1.85.1, compiled-once build+consume, **8/8 r2_ tests**, zero failures. Executed test binary SHA256 8b702fd99d67b3ef9138b42a68830fbb42abd6ca6b0866bbe44701b1d45e0f40; output SHA256 7c44e47740efd4e69434e76500e64e067d985514223104ce7978f14b62daaa15; result artifact 11881450665.
- [Governance 38538225279 attempt 1](https://github.com/lly8666/wbd-next/actions/runs/38538225279): SUCCESS; branch M2 actual scope attested.
- [R0 static audit 38538225295 attempt 1](https://github.com/lly8666/wbd-next/actions/runs/38538225295): SUCCESS (not R2 proof).
- [Old G2 scaffold 38538225378 attempt 1](https://github.com/lly8666/wbd-next/actions/runs/38538225378): FAILURE in consume, despite compiled binary **9/9 tests passing**, because root-owned old consumer insists on exactly one test in whole binary. Do not call whole run green. Escalated to M0 in [issue #2](https://github.com/lly8666/wbd-next/issues/2), not a warrant for worker editing shared CI.
- Authenticated M3 adapter and M1 handle/send-result integration risk submitted to M0 in [issue #1](https://github.com/lly8666/wbd-next/issues/1).

The artifact receipt is docs/evidence/M2/R2-M2-RECEIPT-001.json; native scope is PASS and cross-module/product qualification remains NOT_RUN. No new feature is started.
