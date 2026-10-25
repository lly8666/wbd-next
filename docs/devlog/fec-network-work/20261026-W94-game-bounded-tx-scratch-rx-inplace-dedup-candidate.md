# W94 | Game OFF bounded scratch & authenticated RX duplicate precheck candidate

Parent `cd28a46ee9258657266f4ee530aa8dff0f8b47af`. W91 Game2/4 native real clean PASS; W92 exact Linux per-lane BPF kernel filtering independently verified on same VM in AB and reversed BA for Game4 (9–10% lower CPU at equal delivered packets). W93 RX independent owner native build Action40214123744 PASS and Game2/4 same-VM real clean AB Actions 40214330740/40214339875 PASS, Game2 CPU old/new 1.72/1.72→1.66/1.67; Game4 2.32/2.37→2.35/2.39; both clean TCP/UDP/Stop correct, Game4 minor CPU+RSS cost not concealed.

Stage D targeted:
- `GameAdapter::drain` stops allocating a per-lane `Vec<u8>` for wire, instead holds one bounded 2048B scratch for TX and reseals every lane separately. Max valid record length remains negotiated ≤2048. Synchronous `kernel_copy` callback owns/freezes copy before scratch reuse; no lifetime or shared ciphertext reuse. Readiness and source-first dispatch unchanged.
- `GameReceiveOwner::receive` authenticates directly **in the stack RX wire slice** from raw driver, saving the unconditional prior `wire[..len].to_vec()` per ingress; synchronous `GameAdapter::receive(Vec)` remains source-compatible for tests/other callers.
- After valid lane AEAD + decode, read-only `GameRx::first_delivery_candidate` checks shared bitmap/staleness BEFORE allocating/copying an arena slab for duplicate packets. It does **not** set any dedup bit nor evict the future window until allocation is successful; existing final `first_delivery` remains the only committer. Future/stale generation + authenticated lane checks unchanged.
- Unit covers alternating short/large packet sizes and four separate AEAD/PN seals under reused scratch with exactly one logical delivery, RX owner lock progress, true AEAD/malformed/replay.
- NOT a fix for unexpected real TUN write failure after `first_delivery` has already marked logical ID; must keep this as known semantics risk, do NOT claim fully transactional TUN commit.
- Strict validation: build and native regression exact source, then isolated Game2/Game4 FEC OFF 3Mbps UDP+real TCP same VM old W93 vs new W94 with identical traffic and wire; compare CPU/actual throughput/p99/RSS/Stop. If performance or correct first delivery regresses, undo this candidate alone; don't alter underlying FEC math or W90 withdrawn fixed6 product switch.

No outer recovery algorithm modification, Windows user TEMP_SKIPPED, no capacity increase, no merge_ready claim.
