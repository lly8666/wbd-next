# 2026-10-23 P1 residual: pre-first-repair burst pacing isolated

Diagnostic Action 39894058072 reproduced Normal 2%/200ms with Stop PASS, no host-pressure warning, coherent learned timing (SRTT~404–406ms, recent RTT~400.18ms, PTO~443–459ms, cache~936–968ms) and zero driver-uncertain sends.

The earliest bottleneck is before a first actual repair: 840/832 first candidates, only710/706 actual immutable retransmits, blocked267/264, and expired-before-any-repair108/110. UDP missing155/132 is the same order. The old local burst is exactly8×1500=12,000B while one indexed timer turn may surface<=32 candidates. A capacity NotSent waits a full PTO, so genuine loss can consume most of its cache lifetime before the first actual repair.

Change is deliberately narrow: the **instantaneous** local burst now has a 32KiB minimum equal to the already-authorized sparse per-epoch floor, capped by max_repair_bytes_per_epoch. Epoch quota and long-run pace are unchanged; no extra retries, queues, ordering wait, crypto/replay scope, or fresh HOL. At MTU1500 this permits21 full repair frames rather than8 in a burst, still under the 32-candidate timer cap.

CI path also now includes `crates/wbd-recovery/**`; the earlier behavior commit did not auto-run because that path was missing. No old-SHA rerun was used. Unique native build is 39895511143 on SOURCE `dce9d23009b8803ac67484df9b6d0608b3641801`.
