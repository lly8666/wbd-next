# PLAN027 H738 — user's GameFEC ~8-minute hard-stop and real first-fault evidence priority

Task R0-M0-PLAN027-FEEDBACK-AND-NETWORK-CLOSEOUT remains PARTIAL; all non-GameFEC work PAUSED by user at H725. No physical test.

Latest genuine original Go TLS Windows NPF/Wintun↔WSL2 Linux Rust Game2FEC SOURCE 0264c2cfc91e05c7c4b8d518fa0efc6707a2ff6b, binary source build41280564979 artifacts Windows13072889005 sha256:b2ed3b6d2cd7712e36863d26e9fedee35a8b5c0a18c23db282d2dc9e586d67c8 / Linux13072973000 sha256:3a6593f40b411ca829588c9556aca3a644836e982de3027f1bc2b4b825512f11. H737 native run41283910551 was CANCELLED, separate watcher41283917268 logs showed timeout at 721s AFTER actual native step start, then five REST/CLI recovery retries BEFORE cancel, logging unavailable. Independent stage receipts 41284046361 PRE_NATIVE_STEP, 41284051831 STEP_ENTER, 41284081812 STEP_PREFLIGHT_COMPLETE, 41284084105 MODE_STARTED all SUCCESS; no BOTH_READY/FIRST_ERROR/MODE_TIMEOUT/Stop => actual product unresolved. Rust Windows GameFEC MTU unit repaired but no authentic native pass.

User explicitly allows final native GameFEC step to force stop at ~8min, no long 12+min run. H738 switches only game2-fec/game4-fec separate watcher native-step clock to 480s (other Game720, Normal1200), cancels original FIRST at limit via bounded API then short force cancel if needed. Native log REST/CLI salvage runs AFTER cancellation in independent watcher, never adds unbounded pre-cancel delay. Existing Windows guard 600 remains behind the 480s independent external stop, not a new watchdog.
H737 original one PID supervisor had synthetic 250s timeout, but no MODE_TIMEOUT receipt despite MODE_STARTED; plausible blocking synchronous GameFecProgress.poll (filesystem/gh). H738 moves file+dispatch sampler to daemon DIAGNOSTIC THREAD inside same PID, not new supervisor or product worker; main PID maintains 250s deadline and can print/dispatch MODE_TIMEOUT regardless of log reader. One bounded synthetic blocked-poll test is part of same-batch test assembly. Main supervisor sends bounded 20/60s progress receipts. No product change or protocol round. Source scope remains frozen original binaries for next one Game2FEC1M 25ms/0 loss 10s real native, not a new matrix.

Future work when this proves branch: fix actual GameFEC Rust/Go or fixture with minimal change, verify both original UDP/TCP and owned Stop; Game4FEC after Game2FEC sound. Other PLAN027 A/B/C remaining paused and preserved.

```feature-impact
{"kind":"none","ids":[],"reason":"GameFEC-only native test diagnostics/cancel scheduling: real 480s external deadline, cancel before log salvage, single supervisor nonblocking diagnostic sampler and one regression. No product data-plane change or user-facing PASS."}
```
