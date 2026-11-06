# PLAN028 H1262 — Game2 OFF outer appearance must be real; isolate Fixed6 30% tail without long rerun

## Why this exact scope

User requested continuing the unfinished 30%-loss Normal Fixed6 recovery-downlink issue **and checking each client's outer “performative” retransmission**. Do not turn an outer replay into real delivery or advertise all-modes performance PASS. Source `af2dc107fb9edce01db8a143295b678af6c91bcf`, original Go TLS+Rust H1259 authentic five-client 430s native Action42137210217, complete original logs and offline replay Action42141025302, offered the following **CLIENT-owned original native M4** evidence (last Stop/readback):

| Mode/client | Physical netem | Outer ON | Actual original raw ciphertext presentation |
|---|---:|---|---|
| A Normal Off | 0% | yes | `V4_PUBLIC_M2_OUTER repair_accepted_wire_bytes=0` is correct for clean no-gap traffic, NOT a disabled producer |
| B Normal Auto | 1% | yes | `repair_accepted_wire_bytes=13956072` real immutable raw repeats |
| C Game2 FEC Off | 5% | yes | `V4_PUBLIC_GAME_OUTER outer_data_retransmitted=0` **FAIL/BUG of optional appearance**, despite real original two TLS lanes |
| D Game4 Fixed6 | 15% | yes | `outer_data_retransmitted=5176`, independent `WBD_GAME_FEC_LINUX_NORMAL_OUTER_STOP copied_appearance=5176` |
| E Normal Fixed6 | 30% | yes | `repair_accepted_wire_bytes=147529144` real immutable raw repeats |

This is only client-direction and observed SOURCE, not full bidirectional same-SOURCE attribution of Normal server per-client outer repeats. Original Linux Normal uses authentic M2 mature ACK gaps and limited frozen copies, no unconditional per-DATA PTO; zero on 0% is expected. Game presentation is separate from FEC and does **not** improve the UDP delivery count just because the same ciphertext reappears.

The `GameKernelOwner` already has `CosmeticOuter` with a bounded **1 sampled original per 16 copied records, at most one pending per physical lane, fallback250ms, min80ms spacing**, and only the original PN/SEQ + immutable ciphertext. However the Linux Game TX/RX hooks were incorrectly gated by `fec_enabled && outer_repair_enabled`, suppressing appearance in **Game2 OFF** while its published `--outer-repair on` default reported ON. Change only this predicate to `outer_repair_enabled` for original first-copy registration, reverse authenticated Game DATA ACK hints, health SEQ advance, timed replay and owned Stop reporting. If outer repair OFF, no snapshot/replay path is entered. FEC2 parity, RX replay/AEAD, game logical ID, packet budget, raw driver, timeout and lane count are untouched. No ciphertext reseal, second PN, business/FEC/Health credit or speculative ACK. FEC mode OFF now reports `WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP copied_appearance=N` while the existing Game FEC STOP marker remains compatible.

## Real H1262 native test (not a five-client 430s repeat)

One source-frozen original Go TLS/Rust x86_64 native **4 network namespaces** scenario with authenticated separate A (NormalOff/0%/12Mbps), C (Game2Off/5%/18Mbps/50ms one-way), E (NormalFixed6/30%/16Mbps/125ms one-way/outer1280) on one shared TLS443 and Rust TUN. Real physically installed both-direction tc netem limit10000 and true raw/TUN UDP; 3 pairs start at the same Linux monotonic timestamp. 180s actual business:10 warmup+45 steady+35 overload1.3x+90 rate-down recovery, then10 drain. No application retransmission in benchmark. Source/current product and original-Go donor+hashes pinned; ISA-L v2.31.1 built into native release, although only E uses normal FEC2 in this narrowed scene.

New reporter requires actual Game2 OFF client **and server** copied-appearance counters >0 under true 5% loss, Go policy `repair_enabled=1`, one-shot original frozen wire/PN/SEQ unit, original independent A/E M2 outer readback, true physical loss counters, all six 180s app endpoints and per-lease bounded TUN Stop. On E original client RX worker enable existing `WBD_FEC_EGRESS_DIAG=1` (one line/500ms) to align genuine source/parity/recovered/RX-error/TUN-fail deltas with **nine 10s rate-down windows**; capture Stop FEC2 age/reorder/invalid, TX stage and partial send counters, full business sender vs receiver. The prior H1259 Erin 30% downlink unique delivery `87.6436%` in last60s with last20s 10s receive rates8.17/11.99Mbps vs actual16Mbps TX and zero server TUN overflow remains a **separate unresolved residual**. This test may fail to reproduce a late intermittent symptom; do not adjust global FEC2 cache aging, profile6 parity or loss model without an observed stage reason.

The test must differentiate: infrastructure complete means original app runs+Stop and diagnostic artifacts, **not** all clients' goodput PASS. Preserve previous H1259 original Action FAIL (Stop receipt race), H1260 posthoc-only replay PASS, H998 historical same-socket MTU shrink FAIL and non-x86/physical NOT_RUN.

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"H1262 fixes Linux Game2 FEC-OFF cosine-only original frozen TCP outer appearance incorrectly gated on FEC and records pending SOURCE-bound short native validation. Normal Fixed6 30% tail remains diagnostic and not a performance PASS."}
```
