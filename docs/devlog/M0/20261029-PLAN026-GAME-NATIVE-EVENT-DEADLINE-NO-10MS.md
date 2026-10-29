# M0 PLAN026 Game NativeOwner TX idle 10ms pulse → real Game4/FEC deadline

2026-10-29. Current M0 PLAN026 stage is Fixed/Game/Auto/Health, not Normal/off. Parent main acd6f9d9523b577defe5d39db9a644e15e26dd22. Source inspection found an unconditional `DELAY_POLL_MS=10` in Windows Rust Game2/4 TX's idle `wait_ready`, causing up to 100 idle wakeups/s even when no Game4 staggered copy or GameFec close is scheduled. This is actual code behavior contrary to the event-only steady-worker design; **no CPU reduction claimed before same-source Windows native evidence**.

Changes in one product batch:
- `v4_windows_game_owner.rs`: read the existing GameAdapter's genuine next Game4 copy and FEC partial close deadlines relative to its existing group monotonic clock. No new scheduler, protocol, FEC code, Go packet thread or native worker.
- `v4_windows_game_native_runtime.rs`: idle TX waits indefinitely if no due, otherwise ceil to the exact next due millisecond (minimum 1ms only for already due timestamp); Wintun ready, native RX→TX wake and Stop remain event signals. Enforce Game4 4/50/140ms sample deadlines and idle no-pulse via a pure Rust unit regression. No change to driver submit/PN/ledger, old ciphertext, 2/4 owned Stop or separate lane protection.
- Expand Windows original-owner test workflow file trigger coverage to Game code/Health and run prior added Fixed/Auto/Game/Health native Rust core + original Go/Windows WAL stage.

Pre-existing Normal/off validated sources SOURCE055 signed functional+Stop, SOURCEa123 N0 240s, SOURCE7fc 150Mbps are untouched. Windows full original Go signed-driver Game V2 true network and whole-process CPU remain separate NOT_RUN on this code until real Action proof; physical, FIN/Dormant/Wake also unchanged. Existing main Windows core/WAL Actions on preceding documentation SOURCE bade6e8f were in-flight at this write and are not qualification for this new changed Game SOURCE. No optional outer delivery/repair test gate is added.

## Exact-source Actions results (SOURCE b222744cc)

- Windows Rust original-owner ABI [40844243141](https://github.com/lly8666/wbd-next/actions/runs/40844243141): SUCCESS, 13 original Windows owner, **47 PLAN026 mode-native (including new event-wait Game4 test)**, and **9 authenticated Health** tests, no failures; native Rust DLL and original-Go build passed.
- Windows actual original Go credential TLS + signed Wintun/WAL [40844243066](https://github.com/lly8666/wbd-next/actions/runs/40844243066): SUCCESS 6/6 jobs (WAL, Normal impacted regression, Fixed, Auto, Game2, Game4). Scoped original Windows TLS Rust M3 signed Wintun kernel first App/reverse and Stop; Game2/Game4 lane1 blocked/healthy first app no HOL; Fixed/Auto RS16 actual recovered App scoped PASS. Each packet-scope test says global host WFP and Auto genuine M2 Applied NOT_RUN.
- Governance [40844243103](https://github.com/lly8666/wbd-next/actions/runs/40844243103), r0 native ABI [40844243049](https://github.com/lly8666/wbd-next/actions/runs/40844243049), cross ABI [40844243076](https://github.com/lly8666/wbd-next/actions/runs/40844243076), static audit [40844243053](https://github.com/lly8666/wbd-next/actions/runs/40844243053), g2 bootstrap [40844243221](https://github.com/lly8666/wbd-next/actions/runs/40844243221), native-functional [40844243044](https://github.com/lly8666/wbd-next/actions/runs/40844243044) SUCCESS.
- Exact evidence `docs/evidence/M0/PLAN026-WINDOWS-GAME-DEADLINE-SOURCEB222-20261029.json`. Windows↔Linux public preflight run 40844243101 remained in flight at evidence capture, not an inferred PASS. Product-code source is b222744cc, not this later evidence-only commit.

**Still NOT_RUN:** full Game4 idle CPU/wake improvement on real signed Windows NPF at sustained throughput; multi-lane Fixed/Game full V2 loss matrix, Auto organic Applied/downshift, bilateral FIN/Dormant/Wake, hot lane replacement and physical/GUI/global WFP. No Normal/off new-build requirement.

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Game2/4 Rust TX event-driven idle wait and original Game4/FEC deadline replaces unconditional 10ms poll; new exact-source test necessary, no Normal/off code change or invented network/CPU PASS."}
```
