# PLAN027 H590 — correct cheap test contract, resume exact scoped diagnostics

H588 Game4 native 60s diagnostic Action41180233235 was a **cheap CI failure**, not a second genuine Game product test. Error: `tests.test_m0_wl_native_step_runner::test_game_process_group_rolls_back_first_hanging_a8_launcher_flag` asserted old source text `mode_seconds=1200 if slow else 165` although intentional GameV2-only nested deadline now uses 360s; other V2 remains 1200s. H589 A5 Action41180331471 failed the same cheap gate after one-source dispatch, so no same-VM product measurement was executed. Old genuine Game10 Action41178602168 remains cancelled/NOT_PASS; old Go A result remains FAIL. H590 updates the regression test to verify the **new explicit bounded contract**: GameV2 mode360s < source-file parent440s < external1200s, NormalV2 unchanged970s parent/1200s mode, ordinary Game functional320s parent; retain original process creationflags=0/regular file/tail. Re-triggers precisely H588 Game10 and H589 original GoA/RustB once each via their existing source-locked push-only workflows, in independent Actions, same frozen cb475 product binaries; no full build, no loss-rate reruns, no 20M dispatch.

```feature-impact
{"kind":"none","ids":[],"reason":"Tests/workflow-only retry after assertion update; no product feature or protocol change."}
```
