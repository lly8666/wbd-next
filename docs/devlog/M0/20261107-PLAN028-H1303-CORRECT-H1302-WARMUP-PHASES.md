# PLAN028 H1303 — correct H1302 phase accounting before capacity decision

H1302 [native ARM64 Action 42340313642](https://github.com/lly8666/wbd-next/actions/runs/42340313642), exact SOURCE `d7830f84400e5e3162ab81b5d50218252c640c11`, artifact 13561233518 (zip SHA-256 `faa8f79af6aa1a2bf6e1bb45daf9791e3d7bbc812aea0c8a0eb859a7caad6a2d`) remains **PASS**: 0 application alerts, five authenticated replacement/owned Stop success, and all server per-/32 shared TUN queues overflow0. This was a 180s scalar backend run with actual Game4 scalar quanta 138959 and ISA-L linked, not a causal fix for prior weak-net interruptions.

**Reporting correction, offline only.** Original `traffic.py` always runs `warmup_s=10` first. The H1302 inline report created four windows at application t=0/30/90/120, mistakenly counting warmup t=0–10 as the first 0.6x phase and shifting all subsequent phase windows. Using the same 10ms packet bins and independent 500ms host/qdisc monotonic samples from the already uploaded Action zip, `tools/m0-plan028-h1303-capacity-offline.py` applies the configured 10s offset and corrects windows to t=10–40/40–100/100–130/130–180. The original H1302 ledger is **retained as historically reported**, not silently overwritten.

| Actual phase | Host mean busy | Host mean softirq | Erin true UDP UL offered / received Mbps | Erin netem peak qlen |
|---|---:|---:|---:|---:|
| 0.6x t10–40 | 92.50% | 13.44% | 9.60 / 9.58 | 358 |
| 0.85x t40–100 | 98.21% | 15.42% | 13.60 / 13.588 | 499 |
| 1.0x t100–130 | 99.01% | 15.94% | 16.00 / 15.862 | 567 |
| recovery0.85x t130–180 | 98.47% | 15.62% | 13.60 / 13.60 | 491 |

Even 0.6x is near VM total CPU saturation; 0.85x is clearly not a headroom qualification. Do not add 1.3x or 1800s on the same four-vCPU VM merely to retry lucky PASS. This is **host capacity evidence**, not proof of kernel TX stall causality and not a general product max.

**Independent x86 lifecycle blocker:** prior x86 Game4 Action [42338102273](https://github.com/lly8666/wbd-next/actions/runs/42338102273) had protected new-group TLS/Rust local start but `V4_PUBLIC_GAME_REMOTE_M4_UNPROVEN` with client native raw0/no reverse inner IP while old route was preserved; later server admission rejected retries. The current Game code waits for `KernelCounters.Delivered>0` as the *only* new-path proof, yet no-business/pure-uplink must work. It remains **FAIL/OPEN** under exact old SOURCE; do not replace it with optimistic local READY, an unconditional 5-second sleep, or a probe. Next work should establish minimum authenticated cold server Commit evidence independent of user reverse data, with precise old/new Stop fences and a single real x86_64/x86_64 short test (next Linux platform per user 2026-11-04 correction).

```feature-impact
{"kind":"none","ids":[],"reason":"Offline source-locked capacity correction/reporting only; no product algorithm, default, wire, buffers, TLS, owner or user configuration change."}
```
