# R2-M2-RECEIPT-REPAIR-BOUNDED-WORKPACK-009

Role M2 / main registry rev2 epoch1, branch work/m2-r2-recovery.
Task assignment: main docs/decisions/M0-full-module-workpackages-2026-10-17.md / PACK-006. Previous 008 source 7875137949f61fead1374d2933798c61814adb92 native 55/55 PASS; H c74a4fd Governance38735393188 PASS. No source qualification transferred to this task.

## First independent capability batch: bounded receiver-side feedback

New owner-local pure RxFeedbackState accepts only caller-declared authenticated DATA events, stores bounded 256-PN received pages, produces at most eight dirty-first receipt payload pages. It never opens AEAD or trusts raw bytes. Initial+one repeat are controlled by fake monotonic clock, steady deadline 10ms, gap deadline 2ms. A duplicate DATA after both reports may elicit exactly one additional reassertion (no ACK-of-ACK storm); control does nothing. Max retained pages, expiry and retired floor prevent historical resurrection. Full batch may be Accepted/Uncertain/NotSent; NotSent retains dirty, concurrent changed bits cannot be cleared by an old send completion. Sent or uncertain is NOT proof that peer received feedback. Report sequence is u32-wrapping and only local draft content (M3 owns control seal/PN).

Rust unit tests r2_rx_feedback_* cover 10ms, 2ms gap, max8 pages & 33-page backlog, dirty/new-bit race, duplicate after two feedback losses, NotSent, retirement, seq rollover. No codec, Go, engine, platform, socket, shared Cargo edit. Scope is component-only; real authenticated V4 and M1 frozen-handle M0 integration NOT_RUN. Other PACK-006 boundaries (A01-A06/R01-R04, frozen handles, uncertain debt, repair fairness) need independent end-to-end harness verification before final handoff.

This code S is not yet qualified. Worker-native CI and central scope audit must be read using exact new SOURCE, then remaining workpack tests added rather than promoting a partial pass to product PASS.

## Controlled-driver cross-component follow-up

The next functional batch uses a FrozenRecordHandle backed by a single Arc<[u8]> and reads exactly the same immutable bytes through wbd-types driver_read while a simulated reverse control channel loses both initial and repeated receipt. Injected MonoNs drives a PTO tail, one Uncertain repair debit, one RX duplicate-triggered reassertion and a late positive receipt that releases the same frozen handle exactly once. A second test verifies pinned lane/epoch/control range before scope release and deliberately leaves a shadow in an unreported PN page. This remains a *synthetic* authenticated-open fixture, never a real Go/M3 ciphertext proof or product load test. No socket or engine imports. Tests use existing worker-native compile-once consumer.

## 2026-10-17 compiled-once native and scope evidence

CODE source 269fd8f88ba6df97ebb8fe1f3e29cc58b1ca90c2 worker-native #38998072121 SUCCESS 63/63 (55 retained+8 new), build+consume; G2 #38998072124 SUCCESS, static #38998072111 SUCCESS, Governance #38998072117 SUCCESS ROLE_SCOPE_PASS 58 commits. Native/G2/Governance result ZIP SHA256 compared with Actions digests. Details in docs/evidence/M2/R2-M2-WORKPACK-009-receiver-feedback-and-handle.json.

Pending PACK-009: existing ReceiptState::on_timer may nominate 32 no-witness PTO tail candidates per lane poll despite module 08 one-tail-per-timer requirement; add a failure-reproducing fake-mono stress test and correct without compromising 32 RACK cap, expiry or fresh fairness. Real M0 authenticated Go V4/driver and M1 arena product integration NOT_RUN. Do not claim entire workpack PASS.

## PACK-009 next capability: one lane PTO tail probe per PTO period (source pending Actions)

Prior 63/63 SOURCE269fd8f contained 10k unreported shadows emitted 32 PTO candidates per identical fake-clock owner poll. This contradicted module08's single tail candidate/lane timer behavior and made owner repeat-poll capable of a burst. This bounded R2 change introduces a lane-wide injected-mono PTO gate; every unreported PTO candidate advances it by PTO. RACK with three distinct authenticated later-data witnesses still emits up to 32 candidates per poll. Queued expiry has a separate ordered index to avoid starvation behind an overdue, gated PTO prefix. Exact expiry always releases once, and late queue tokens remain invalid; neither path sees a new PN or seal. Previous old unit tests that expected 32 unsignaled PTO tails are corrected, not silently reclassified as RACK. New fake-mono test exercises one initial tail followed by 32 valid RACK witnesses while the tail gate is active. Code work requires a fresh worker-native CI and G2/static audit on the new source; no product Go/M1/M3 driver or 500Mbps claim.
