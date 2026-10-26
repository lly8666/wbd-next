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

## Recovered 2026-10-26 (exact Git/Actions)
- `fb65d8136c32e3e2182a09425f517cd7b98162ce` native [40214830539](https://github.com/lly8666/wbd-next/actions/runs/40214830539) **SUCCESS**; artifact 12607335802 SHA256 `1e5afba4a73968228ebf1d7085a7b5e0ca874c5dd77c22cc9f0ec42b6b7cc310`.
- Game2 [40215055396](https://github.com/lly8666/wbd-next/actions/runs/40215055396) same-VM A=W93/B=W94 both **PASS_SCOPED**, real 3Mbps UDP+TCP full delivery, CPU C/S A 1.52/1.53s B 1.57/1.59s; p99 max 77.7ms, no source TUN drop/backpressure, Stop clean.
- Game4 [40215059452](https://github.com/lly8666/wbd-next/actions/runs/40215059452) same-VM A/B both **PASS_SCOPED**, CPU C/S A 2.51/2.53s B 2.44/2.49s, p99 max 77.6ms, all delivery/Stop correct.
- Minor CPU changes conflict in direction; no performance win claimed. Keep candidate for bounded allocations provisionally. W90 fixed6 public candidate **still withdrawn**. Windows TEMP_SKIPPED; capacity_stop=true; merge_ready=false.
