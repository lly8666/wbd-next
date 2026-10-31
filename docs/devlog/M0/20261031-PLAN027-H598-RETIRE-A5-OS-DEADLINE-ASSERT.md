# PLAN027 H598 — delete last old Go A5 watchdog assertion

H597 Action cheap original WL runner gate failed on test_m0_wl_native_os_deadline hardcoded requirement that the now-retired `tools/m0_wl_perf_v2_ab.py` be invoked. Replace with meaningful live contract: no A5 runner in workflow; Windows real Game/Rust native modes use file-backed `m0_wl_native_step_runner.py tools/m0_wl_public_modes_e2e.py` with independent native timeout and bounded WSL execution. No runtime change; H597 Game authenticated Health core unit/native compile still unverified.

```feature-impact
{"kind":"none","ids":[],"reason":"Retire obsolete A5 watchdog test assertion, keep actual live native deadline and Stop invariants."}
```
