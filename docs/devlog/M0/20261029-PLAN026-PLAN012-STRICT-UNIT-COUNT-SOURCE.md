# M0 PLAN026 original PLAN012 true Rust test count gate after code growth

Exact source `64ead9e3` Action `40831544743` failed at the initial strict log grep, **not** while compiling or executing any of those specific tests. Archived log shows original `m0_fec2_live_rx` now has **4 passed, 0 failed** (all four exact test names) and original `m0_fixed_stream_` now **5 passed, 0 failed** (all five exact test names). The historic PLAN012 combined source workflow still hardcoded `3 passed` for each, so its shell exited 1 before compiling protected Go/test functional downstream. It already checks `release_record 1/1` and Game2/4 `2/2`, both correct. Update ONLY the two strict source-exact counts to `4/4` and `5/5`; no skip, no `|| true`, no weaker regex or policy change. The downstream native Linux/Go combined functional and full suite remain NOT_RUN on this fresh exact source until the new workflow finishes.

WIN evidence: source `883e215d`, Action `40829519945`, real original Go credential TLS+signed Wintun Fixed/Auto shared Rust RS16 missing-source and Game2/4 first+reverse/Stop all **PASS_SCOPED**. This is NOT Windows 2/4 Npcap actual worker product CPU/WFP proof. LINUX evidence: source `64ead9e3`, Action `40831544826`, real original Go TLS 3 ciphers × 3 Fixed frozen M4 sendto/mixed-prefix/sendmmsg modes, actual kernel RS16 missing recovery, original M2 shadow and 2s/8s censored maturity **PASS_SCOPED**. Neither implies fully integrated FIN/Wake nor Auto LAST matrix.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix two stale exact Rust unit test PASS counts in historical PLAN012 combined workflow: 3->4 and 3->5, both all green on archived original test evidence; retain every strict test."}
```
