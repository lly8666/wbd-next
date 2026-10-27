# S56 M0 exact catalog limit repair — no product code modification

Parent frozen native original Windows↔Linux Auto source `49f816375a9e69bd1cde41df2543b15b58066313` triggered Action40556191100 (native RUNNING at documentation time). Same source Governance40556191268 **FAIL** at Feature catalog because fec-auto.json had **16,531 bytes**, exceeding current `tools/feature_catalog.py` exact 16KiB maximum. Every native original Go production/Windows Rust/Linux Rust preflight from S55 passed separately. No source qualification or 120s natural Auto/Stop verdict can be derived from this governance red.

This commit only replaces one verbose, historical S6707 preflight narrative within the existing fec-auto limitations list with a short exact-source pointer and adds this explicit failure note. The original multi-run facts and evidence remain in the prior S6707 M0 devlog/verification record; no PASS, FAIL or NOT_RUN card verification entry was removed or rewritten. New card size 16379 bytes is below 16KiB. No M2 controller quality policy, original Rust/Go ABI, test selector, assembly manifest, queued workload, user acceptance, or source SHA was changed. Do not trigger/repeat S55 native validation for documentation cleanup; only ordinary Governance/Feature catalog should run.

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Reduce repetitive historical verbose Auto card text below the enforced 16KiB size while preserving immutable SOURCE facts elsewhere; no product changes, no promotion and no native re-dispatch."}
```
