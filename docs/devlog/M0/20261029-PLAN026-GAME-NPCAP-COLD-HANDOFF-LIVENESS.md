# M0 PLAN026 — Windows Game NPF cold capture hangs before Rust owner

2026-10-29, main-only source-corrective batch.

## First source-established liveness fault
Original frozen Go `wobuzhidao` SHA `a7a82db31fe736ffedee330795a3234d358f1984` `internal/faketcp/npcap_windows.go::ReadSegment` lines 248–317 performs an unconditional internal retry on `pcap_next_ex` zero-frame timeout, never checking outer `handoff`. Current Game2/4 caller `runM0NativeV4WindowsGame` closes `handoff` only from `m0WinRustGamePeer.BindNativeRing`, immediately `p.readers.Wait()` and only afterward borrows the live NPF handles. With an idle Go reader the closed signal cannot be observed, so real Rust native game startup may deadlock before the Rust worker and NPF first send. A full bounded 256 cold inbound channel could also block a reader indefinitely. This is a product-source defect, separate from the earlier PowerShell/WSL PIPE CI defect.

Historical Windows source4c6 Action40847146468 and sourceadc Action40848387586: original Normal/Fixed/Auto functional PASS, Game2/4 native rc3 / NPF EOF FAIL; neither is today's new proof. Live sourcea13 Action40874802357 started true signed Windows WSL2 native step at 2026-10-29 12:47:12Z, remained `in_progress` >35 minutes at 13:22Z despite 24-minute step timeout and 1020-second watchdog; GitHub live logs API 404. This code defect is causally grounded but is NOT asserted as the confirmed first error of that source run.

## One complete fixed-source change and protections
- Implement *cold-only* `NpcapEndpoint.ReadSegmentUntil(generation,handoff)` alongside the immutable pinned original. Same real NPF call, generation gate, original BPF decoder/diagnostic counters; recheck handoff after each genuine 50ms NPF no-packet timeout. Never call `pcap_breakloop`, which can leave pending -2 EOF for the borrowed Rust RX handle. Genuine -2 remains an error.
- Change only the original Go Game2/4 TLS cold reader caller to use this stop-aware read, and make full bounded early ciphertext queue fail explicitly without blocking the join; preserve already received protected ciphertext for native Rust M3 to authenticate. No new per-packet Go steady-state pump.
- Native Rust two workers, GameAdapter/FEC/M2, NPF actual-copy receipts, OS/WAL/Stop and Linux stable path unchanged.
- Exact original Go overlay and new Windows Go tests included with blob SHA in `r0/go_overlay/assembly/manifest-plan020-m0.json`; existing Windows compile preflight executes idle/EOF/generation and queue-full/order tests. Feature catalog Game and Windows native cards changed without formal promotion.
- Next real step after cheap Go/Rust green is source-locked signed Windows Game2-only / two-OS first/reverse UDP+TCP/owned Stop, then affected Game4/Auto/Health and necessary CPU A/B. No repeat Normal/FEC broad old matrix, no fabricated host capacity or physical PASS.

```feature-impact
{"kind":"changed","ids":["game-lanes","windows-native-transport"],"reason":"Game2/4 cold NPF read now yields after genuine no-packet timeout so Rust can borrow the signed capture; bounded ciphertext backlog cannot hang the handoff, with real EOF, generation and owned Stop contracts preserved. No change to default mode or formal stage."}
```
