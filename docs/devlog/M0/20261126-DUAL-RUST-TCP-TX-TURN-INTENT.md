# M0 ready ingress turn accounting candidate

Profile docs/evidence/M0/20261126-DUAL-RUST-TCP-CLIENT-PROFILE.json, exact old B binary: 2427 samples, no loss, kernel RAW/TUN wake and task switches dominate named self samples; not a per-thread profile attribution. Previous x86 ABBA shows 55% more TUN reverse packets, TX thread CPU +124%, client CPU/GiB +29%. Do not alter middle TCP BBR or ACK semantics before evidence.

One small structural experiment: charge the original ready-ingress cap to actual dequeues, not draining native TCP output into original M1 slabs. Existing code counts both against a shared 32-item loop; under bidirectional TCP it can end early, also miss the full-input wake condition when last turn is output staging. Candidate retains 32 actual ingress items and 32 total staged M1/jumbo cap, original fairness/ownership, no waiting to fill or new queues, no default config or wire change. This is a batching candidate, not a claim that it reduces TCP ACK count or all kernel costs. Original path unchanged when native owner absent. Actual performance must decide.

Separate x86 clean ABBA (A exact 86e3ec30010a59cbb60539b902cb96dc21e04d6a, reused artifact15113365713 run45810506381; B exact push SOURCE), both Rust 1.85.1. Same previous paired native TCP config, 25s single reverse download, origin fq600, same VM; compare actual bytes/CPU/GiB and native worker/queue logs. Existing dual-native functional CI triggered for B. Compiler ABBA run45813155937 remains independent on bbbe025, not rerun or mixed into this candidate. No old splice retirement or promotion.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Ready-only native TCP ingress/staging accounting candidate; original M1 cap unchanged; exact new source functional and CPU qualification pending."}
```
