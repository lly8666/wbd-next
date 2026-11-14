# PLAN029 H1780 | measured Direct8 pass, test supervision cutoff

- [Native Action 43544563417](https://github.com/lly8666/wbd-next/actions/runs/43544563417), source `506d4966afecda73e63f6c0afaa2c103249939d8`, failed at **generic nested Normal 165s** cutoff (`stage=stop`) five seconds after physical hard8 Direct + new Tunnel + existing Direct 127s + idle120s recovery **PASS_PRE_STOP** at 02:22:31 UTC. This cannot be credited as original owned Stop or subsequent DNS blackout PASS. Evidence `docs/evidence/M0/PLAN029-H1780-H1779-DIRECT8-PRESTOP-TIMER-20261114.json`.
- H1780 modifies only signed Normal V3 Direct8 runner time: child 270s, native parent 400s, enough for genuine 120s UDP expiry, blackout and owned cleanup. Guard refuses any Game/FEC/perf/unmarked run; ordinary Normal remains 165s. Unit regression forbids unauthorized extension. No data-plane, WFP or user GUI behavior changed. New signed Action pending.

```feature-impact
{"kind":"none","ids":[],"reason":"One source-locked native test supervision correction after real physical capacity success; no product readiness assertion."}
```
