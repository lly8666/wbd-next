# M0 PLAN026 H354 — real netem accounting without outer recovery guarantee

2026-10-29. Recovered H353 checkpoint e16f0436 → 8d8c6bc5 (14 main commits), cursor H354 2ed111fc. Same-source original Windows WAL Action 40836280628 SUCCESS, combined Linux Action 40836280631 FAIL: original Go TLS real 1% veth netem dropped 10/9, all 512 UDP offered but fewer than 512 unique app echoes; authentic M2 and native Stop, not a guaranteed reliable UDP transport. Independently, Fixed 64 real app responses arrived but requested=1/applied=0 at Stop after 3s.

Shortest dependency: original Go public source → original Rust M4 true first copy and M2 → real tc loss → complete offered/first-unique/missing accounting → true Stop; for Fixed, original 2s M2 maturity → next 2s Go policy tick → genuine Rust Applied. User explicitly allows ignoring outer retransmission's data recovery ability. Modify only the existing Actions fixture and source-manifest-included workflow. No product source, retransmission mechanism, crypto, byte budgets, extra Go pump, seed, queue, or arbitrary buffer change. Require 512 offered, real per-direction tc drops, actual driver first copies, authenticated reverse M2, nonzero first application deliveries and both owned Stop; report all missing and observed optional original-frozen repair attempts without pretending they deliver anything. Remove invalid >=1024 copied assumption when real loss means a missing C2S source cannot create S2C echo. A 3s post-burst wait can precede the 4s policy tick; let Fixed/Auto observe 5s while retaining all Rust Applied conditions. No blanket waiver of Fixed/Auto product failure.

Original full 7-profile V2 matrix, real Windows physical driver, same-host old Go/Rust cost A/B, FIN/Dormant/Wake and lane replacement are not newly proven. This batch SOURCE/Actions remain NOT_RUN before the commit and workflow verdict.

```feature-impact
{"kind":"none","ids":[],"reason":"Existing original public Linux Actions fixture and verification contract only; no user-facing product feature/configuration or runtime behavior changed."}
```
