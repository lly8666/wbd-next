# PLAN028 H1283 — randomized old-owner retirement, no new transport

2026-11-06 user explicitly authorized developer continuation, asked why Game4 one-at-a-time could still have multi-second gaps, and prioritized success over immediate old lane Stop. H1282 SOURCE `16ae6b79d61bc4c5ecf66dbd3e5817026fe63613` [Action42222907322](https://github.com/lly8666/wbd-next/actions/runs/42222907322) real ARM64 five-client 3×1800s: baseline PASS alerts0; heterogeneous FAIL alerts4; pressure FAIL alerts3. Artifacts 13506895665 / 13505419825 show Game4 one lane at a time (client 17/16 local M4 hot swaps; server 13/14 confirmations), three siblings never deliberately restarted. Erin Fixed6 real uplink gap7410ms heterogeneous, downlink6390ms pressure; not proof Game4 stopped all four lanes. Pressure Dave per-lease queue overflow330 remains a distinct issue.

Changes: in existing Linux original path supervisor ONLY after verified B READY and peer-Rust evidence, retain old A native generation for random 10–20s before exact cancellation/Stop. Do not delay explicit user Stop, or new NIC/IP path events; don't publish old route over new generation; bounded one current+one retiring; no extra sender. In same-path Game4 one-at-a-time, after native M4 slot replacement retain the retired **Go FakeTCP cold observer/association**, client and server, for random 10–20s and exclude its detached DATA until timed close. This is NOT two active Rust Game4 M4 slots; native old physical slot was replaced at commit. Keep protected TLS/PN/FEC/wire untouched.

New deterministic bound test checks 10–20s randomized interval. New SOURCE native build/30min is mandatory before any new qualification. No p99/CPU improvement or all-business continuity claimed. H998 same-socket live MTU FAIL, ARM64 H997 old Action FAIL, remote ICMP3/4 NOT_MEASURED and causal CPU NOT_PROVEN unchanged.

```feature-impact
{"kind":"updated","ids":["game-lanes","tls-auth-multiclient"],"reason":"H1283 bounded random 10–20s old authenticated full-generation Rust RX grace and old Game4 cold tuple retirement after actual M4 slot switch; no second M4 slot/data owner, exact Stop preserved."}
```
