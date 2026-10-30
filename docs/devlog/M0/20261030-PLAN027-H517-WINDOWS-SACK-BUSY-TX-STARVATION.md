# PLAN027 H517 — Windows real negotiated SACK under sustained TX backpressure

H515 restored true Go SYN/SYN-ACK negotiated SACK into native Windows and Linux, but source audit found an important independent path starvation: Windows `v4_windows_native_runtime::tx_loop` performs up to 4×8 real TUN firstsend batches and control, then returned immediately whenever `work>0 || control || parity`. Only **after** that early return did it check RX's newly authenticated future-range SACK version; under sustained 10–100Mbps duplex, SACK never left Windows as pure ACK-only, eliminating loss-correlated Linux sender repair even with original cold negotiation.

H517 uses a pure `native_ack_only_due` gate to allow a pending *new RX SACK revision* to transmit **once after the bounded real DATA/control work** even when TUN remains nonempty. RX already coalesces and publishes at most once per 20ms; TX consumes that revision and cannot create per-DATA polling, re-AEAD, PTO, extra original sequence or a false application receipt. Pure cumulative ACK (no new SACK) is still piggybacked on real DATA under sustained work; no-loss does not suddenly accumulate periodic ACK-only bytes. A full-TUN regression exercises pending negotiated SACK, no new SACK, unnegotiated hint and idle cumulative progress.

This is a new source relative to H516 `6f5cd` and requires its own build and source-locked true zero-loss gate before the repaired 1/5/10/30% window. H516 Windows Go/Rust and Linux Rust eligible tests PASS; the true two-OS native run is separately in progress and cannot be reused as H517. No fabricated R/F promotion. H514 old-source Game2/Fixed50 PASS, GameFEC pending and A5 original Go AB baseline FAIL stay separately reported.

```feature-impact
{"kind":"none","reason":"H517 is a source-only Windows Rust TX fairness correction with a focused unit test, not a new feature readiness or policy change."}
```
