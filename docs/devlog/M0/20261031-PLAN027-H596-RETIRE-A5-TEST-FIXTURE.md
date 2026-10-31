# PLAN027 H596 — remove last deleted A5 witness test

H595 actual main governance PASS. Native cheap check failed only because tests.test_m0_wl_perf_v2_config.V2ABFailureWitness still opened retired/deleted `tools/m0_wl_perf_v2_ab.py`, a test exclusively of the old Go A vs Rust B comparison user cancelled. Delete its obsolete runner assertions, preserve the adjacent generic native-exit SHA-only diagnostic safety regression. No product change, no A5 re-dispatch. Other PLAN027 B/C continue.

```feature-impact
{"kind":"none","ids":[],"reason":"Delete test-only orphan for retired old A5 runner; preserve current native error sanitization test."}
```
