# PLAN027 H577 — gate 4 loss tiers + 2 Game FEC on same frozen 0% product

Old exact SOURCE525 Game2FEC Action41170807537 and Game4FEC Action41170809210 were rescued by scoped separate one-shot Linux cancel Action41173524500 and now both GitHub conclusively say COMPLETED/CANCELLED, not functional PASS. The original same-workflow watcher had cancelled itself while Windows job lingered. New H576 independently dispatched Action41173804351 is genuinely running and watches original SOURCEd5e 0% Action41173614494; caller's cheap workflow Action41173804365 PASS. Indirect workflow_run triggered by GITHUB_TOKEN cannot be trusted; exact workflow_dispatch is the verified new mechanism.

New H577 guarded dispatcher waits for already existing 0% Action41173614494 to finish; no duplicate zero, if FAIL/timeout no peer dispatch. Requires sourceSHA d5e7e3eca7b4988419ca60e008f2644aea775629 and original native job SUCCESS plus signed Windows/Linux binary artifacts. Then exactly four independent 10Mbps/250ms/60s loss1/5/15/30 Normal/off and Game2/4 highest FEC functional Actions reusing the same immutable compiled binaries. Each Action has its own scenario test controller, and matching external watchdog in new workflow. Not a same-VM concurrent A/B; no new product commit since source d5e. No narrow p/2 target claim or false Game PASS. C200 source525 true strict first FAIL remains capacity-limited; further B/C/A5 still required. This dispatcher may remain in flight until the genuine source-zero result; do not repeat dispatch.

```feature-impact
{"kind":"none","ids":[],"reason":"Only source-locked CI Action dispatch gating, recovery cursor and true Game cancellation evidence. Frozen shared Rust/Go original product and feature configuration unchanged."}
```
