# PLAN026 — Rust 150Mbps no-injected-loss gap and faster native CI (2026-10-28)

## Actual read-only artifact reanalysis

Source `0543b805ca25d804ccd131be6686b0b99f61f80f`; run [40668581343](https://github.com/lly8666/wbd-next/actions/runs/40668581343); artifact ID 12806629533, ZIP digest `sha256:421de570c82e3e84ad563c208762518995cf96f11e65bf963e9a66313ce79a06`.

User requested Rust-only focus; legacy Go A short-run evidence retained as immutable history but NO longer in scope for performance fixes.

Whole-run Rust 60s packets: Windows sent 1,225,076; Linux first received 1,210,880 (14,196 missing). Linux sent 1,235,180; Windows first received 1,226,476 (8,704 missing). Duplicate/invalid 0. 10ms userspace-loop arrival histogram: **Windows 5.01–5.51s has 50 consecutive empty bins**; Linux 5.30–5.81s has 51 consecutive empty bins. The offset of ~0.29s resembles the configured 0.3s one-way impairment but their monotonic clocks were NOT calibrated, and loop time is not kernel arrival. Windows sender averaged 148.7723Mbps, a 73.662Mbit nominal budget shortfall equivalent to 0.49108s at 150Mbps; Linux sender 149.9995Mbps. Both actual tc netem qdiscs drops, overlimits and requeues were zero, with 1.2458M/1.2521M packets observed. Npcap approximate local drop delta zero; Rust product CPU 13.4531s/59.25 sampled wall, not near a full core. Whole process kernel CPU 8.5625s and user 4.8906s; Windows Python generator CPU 52.5938s and Linux Python 39.4369s over 65s. Both owned Stop PASS. The residual first-delivery fractions are 98.8412% and 99.2953%, below 99.9% target. **Do not claim a root cause from these aggregates.**

Hypothesis order: (1) Windows half-second source/read scheduling/backpressure event, affecting both traffic directions at related observed times; (2) Python combined sender/receiver single loop and local socket receive buffer overrun during a stall; (3) Wintun/NativeOwner/driver queue/CPU capacity or delivery deadline. There is no Rust-only proof of (2) versus (3), and absence of tc drops rules out *only* those qdiscs. The scene field `warmup_s=5` was never consumed by the V2 rate generator and therefore cannot be called an intentional warmup gap.

## Safe diagnostic changes

Add source-locked two-sided 10ms *send* packet/byte buckets, max userspace generator loop stall and bounded >=20ms events, plus a bounded sequence-hole summary. Keep old N0/P200 profile and product wire untouched. Add historical artifact read-only longest-gap audit and regression tests. V2 single Rust-only job fails closed if app unique first-delivery under 99.9%, rather than letting functional PASS mask measured loss.

## Efficiency

Run 40668581343 had source compile stages 135s parallel preflight, 100s Linux build, native Windows 340s including 41s redundant Go and 88s release Rust build. Add explicit source+run pinned *prebuilt* Rust-only mode to skip compile layers while verifying GitHub run identity, manifest SHA and no changes under compiled product/Cargo.lock. Never reuse old EXE/DLL when any compiled product source changed. Each Windows GitHub-hosted runner still installs signed drivers and the WSL2 guest and verifies true Stop; do not turn source-only fixture qualification into product PASS.

```feature-impact
{"kind":"none","ids":[],"reason":"Only source-qualified Python fixture send/receive telemetry, read-only retrospective audit, Rust-only qualification gate and prebuilt artifacts reuse workflow; no Rust product hot path, wire, Windows OS/WAL or Linux product change."}
```
