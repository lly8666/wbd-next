# M0 PLAN029 / H2301 — Linux Normal client M1 shared-TUN inbox 64→128 as default

2026-11-22. Main source before integration `84e48fad3369c3bd0c096ded44e601f6ec575d00`. This is the user's explicit default-promotion choice, **not** a claim that loss1/loss5 improves.

## Actual cause and original paired source
- Original bounded native Linux Normal client `wbd_m0_embedded_go_shared_tun_bind` constructed `sync_channel::<OriginalTunIngress>(64)`; under zero added loss/RTT high source load, true local shared-TUN full drops and TCP retransmission occurred on the client. This is source burst admission, distinct from RTT~400ms+1/5% outer kernel loss and inner TCP congestion collapse.
- Original same-ISA ARM64 true GoTLS+Rust AF_PACKET/TUN x3 netns, 4×20s kernel TCP+160 UDP/TCP, cold true original A64/B128/A′64 on source `4490c09a97b2df18482c33c9300d0dae4716a529`, [Action 44869556627](https://github.com/lly8666/wbd-next/actions/runs/44869556627), real ARM receiver **988.068 / 1064.356 / 988.495 Mbps**, B vs mean baseline **+7.6977%**; Windows not involved. Client CPU seconds/GiB **12.699/12.495/12.898**, B vs mean **-2.3703%**; real client pending-full **737746 / 698798 / 778176**. All true Go TLS/Rust Stop; 160 pipelined small TCP replies but survivor-only p99 **619/293/699ms**, UDP missing **39/28/30**, so not a zero tail QoS proof. Original evidence: `docs/evidence/M0/PLAN029-ARM64-ZERO-CLIENT-INBOX64-128-64-20261121.json`.
- Older 256-slot zero-loss original true A/B/A' and reverse also improved but can reserve ~12MiB extra per client; 128 is the user's bounded compromise: at worst 64 additional 65535-byte jumbo payloads, **~4MiB per authenticated Normal client generation** (actual common MTU far smaller).
- 400ms/GE1% original ARM scenarios had **no local M1 full drops**, so 128 would not fix inner TCP cwnd/RTO bottleneck in that scenario. Do not claim 5% throughput recovery, host-wide P99 gain or CPU-only winning all modes.

## Selective implementation

- `crates/wbd-engine/src/v4_embedded_go.rs` now computes `normal_shared_tun_product_inbox_slots(e.server_side)` once on original Normal fresh cold bind. Returns **128 client, 64 server**; original separate Game shared-TUN bind explicitly remains **64**. No per-packet Go callback, second reader, pacing timer, reliable TCP-on-TCP, FEC ON algorithm or ACK/PN/AEAD changes. Per-generation strict bounded queue and existing fail-closed admission retained.
- Exactly one original cold `M0_PLAN029_NATIVE_INBOX_BOUND role=client|server generation=... slots=128|64 probe_only=0` receipt helps validate the true default on native 3Runner client.
- Rust native targeted [Action 44971752273](https://github.com/lly8666/wbd-next/actions/runs/44971752273), source `5c83c388264bdfa1c3902ba3e9aa5aa12c6c4695` (same Rust code; later integration feature card metadata only), x86_64/ARM64 code compiled and **both exact Normal capacity tests and shared-route no-HOL test PASS**; static client128/server64/Game64 check PASS; 3/3 CI jobs success. These tests are compile/unit evidence, NOT this main source's full native product A/B/A'.

## Release gate and followup

User-authorized default promotion on main is scoped to Linux Normal client. Complete Linux ARM/x86 native GoTLS/Rust original product regression and weak-loss A/B/A' must still be assessed on main's exact code; original old Actions are historical evidence. Any observed new multi-tenant unfairness, delivered-first TCP P99 regression or dynamic memory pressure should prompt precise rollback to 64 rather than unrelated global queue modification.

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"User-requested default change: only Linux Normal client per-authenticated-generation shared-TUN M1 bounded 64→128, server and Game stay64. Native Rust x86/ARM unit+static PASS; original ARM product A/B/A' scoped throughput source retained; full new-main product 3Runner pending."}
```
