# PLAN027 H595 — final test tuple from A5 retirement

H594 returned one cheap delivery CI failure: `test_windows_npf_borrowed_rx_rebuilds_source_and_keeps_full_150_gate` still checked that true live normal-mode source selector lacked the historical tag. That negative check used to target removed old A5-only `WBD_WL_PERF_AB`. Delete only that stale tuple element. Original full source/hash/driver/Stop assertions still stand. No product or legacy work and no new A5 Action.

```feature-impact
{"kind":"none","ids":[],"reason":"Remove a test-only orphaned negative assertion from retired A5 variable."}
```
