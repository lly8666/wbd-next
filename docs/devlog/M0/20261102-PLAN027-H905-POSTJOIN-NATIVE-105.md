# PLAN027 H905｜认证 dead6 修复后，唯一真实双 OS 105s 再验

- H904 product change in Windows Rust `wbd_m0_win_native_v1_stop` accepts terminal authenticated-dead6 **only after both worker threads finished and joined**, so Go receives true owned Stop loan-drain and can restore WAL before new cold TLS; other failures retain original blocking contract. H904 cheap [governance Action41411947653](https://github.com/lly8666/wbd-next/actions/runs/41411947653), static qualification and native ABI Actions passed, not proof of Windows product readiness. H903 separate **old-source** [native diagnostic Action41410970576](https://github.com/lly8666/wbd-next/actions/runs/41410970576) running at preparation; no declared result or binary reuse with H905.
- H905 adds one discriminating Windows Rust actual-export test `plan027_joined_non_health_worker_error_remains_fatal`: real joined TX returns `INVALID`, native Stop still returns `INVALID` despite completed join, preserving fail-closed status for non-Health worker errors. Positive H904 test kept unchanged. No other product change, no new API or protocol.
- Commit carries existing explicit `[plan027-h899-native105-diag]` Action marker: one fresh exact SOURCE compile and genuine original Windows Go TLS + Rust NPF/Wintun to Linux WSL2 same-source original Go/Rust test, predeclared 105s unilateral Windows→Linux kernel IFB blackout, 120s actual UDP bidirectional wake, outer OFF effective and owned WAL/route/Stop. H905 native result **NOT_RUN at commit**; no hypothetical PASS. Strict source-specific outcome, no cross-VM performance AB inference. Refuse physical deployment.
- Previous H900 Game4 FEC6 four-lane OFF highloss PASS and historical H884 Normal OFF→ON30 same-VM cost remain separate; independent full network/ON matrix unfinished.

```feature-impact
{"kind":"none","ids":[],"reason":"Regression test for existing authenticated-dead6 Stop cleanup vs unexpected worker-error boundary; no settings, mode or feature behavior introduced."}
```
