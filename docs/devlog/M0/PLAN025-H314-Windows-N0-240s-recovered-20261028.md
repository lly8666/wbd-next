# PLAN025 H314 — Windows N0 bounded long-run measurement, Linux as reference

Intent: current main 70654a3/H313; no recovered uncommitted product source nor live Actions. User confirmed Linux original-Go/Rust client/server have many successful functional tests: prioritize Windows Npcap/Wintun owner path and use Linux for parity/contrast, not redo mature FEC/Game.

Source: first Windows N0 failure aa93183, Actions40557095692, artifact12756749498; after genuine two-way UDP/TCP, Windows original M1/M3 open refusal after ~29s with client Npcap drop17 cumulative; Linux server still progressing. Typed classification source dd0767, Actions40561743731 later passed N0 60s with drop137 cumulative, not a recovered root cause.

Batch dependency: existing main original-Go/Rust assembly + 1Hz owner telemetry -> N0 60/240s bounded arg/CLI fixture -> measurement-period Npcap drop delta (unknown != zero), per-side 10ms buckets and RTT/first arrival -> one main-source Windows/Linux 240s N0 Actions. Pass requires real Windows Wintun/Npcap ↔ Linux raw/TUN, both UDP/TCP warmup, no native premature exit, bounded 10M/dir, real Stop and kernel tc readback. One performance Action/one measurement job, no Linux FEC/Game rerun. All original SHA/manifest produced by existing workflow; Linux untouched.

Outcome pending exact Actions. Does not assert old 29s error repaired; a 240s PASS would be a new scoped stability sample only. Capacity/full Windows behavior, physical and one-way cross-clock p99 remain NOT_RUN until measured.

```feature-impact
{"kind":"none","ids":[],"reason":"Windows-only N0 test harness duration and exact measurement-period diagnostic, no product-facing functionality, settings, defaults, or platform wiring change."}
```
