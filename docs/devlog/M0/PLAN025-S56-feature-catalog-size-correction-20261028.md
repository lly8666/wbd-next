# S56 M0 exact catalog limit repair — no product code modification

Parent frozen native original Windows↔Linux Auto source `49f816375a9e69bd1cde41df2543b15b58066313` triggered Action40556191100 (native RUNNING at documentation time). Same source Governance40556191268 **FAIL** at Feature catalog because fec-auto.json had **16,531 bytes**, exceeding current `tools/feature_catalog.py` exact 16KiB maximum. Every native original Go production/Windows Rust/Linux Rust preflight from S55 passed separately. No source qualification or 120s natural Auto/Stop verdict can be derived from this governance red.

This commit only replaces one verbose, historical S6707 preflight narrative within the existing fec-auto limitations list with a short exact-source pointer and adds this explicit failure note. The original multi-run facts and evidence remain in the prior S6707 M0 devlog/verification record; no PASS, FAIL or NOT_RUN card verification entry was removed or rewritten. S56 counted JS UTF-16 code units (16,379), but actual UTF-8 byte size was 16,776 > 16,384; S56's claimed byte size was incorrect and governance failed. No M2 controller quality policy, original Rust/Go ABI, test selector, assembly manifest, queued workload, user acceptance, or source SHA was changed. Do not trigger/repeat S55 native validation for documentation cleanup; only ordinary Governance/Feature catalog should run.

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Reduce repetitive historical verbose Auto card text below the enforced 16KiB size while preserving immutable SOURCE facts elsewhere; no product changes, no promotion and no native re-dispatch."}
```

## S57 corrected byte-size governance recovery (2026-10-28)
- S56 source08223fff4681d2a0b4aa61d55ce685c2bc68b2df Governance Action40558013886/1 FAIL because fec-auto actual UTF-8 size was16,776 bytes, despite JS code-unit count16379. No native job from this documentation-only commit; S55 previous exact-source original native remains separate.
- S57 shortens repetitive text for older S a0c8eeb, S47/S48 and latest user 120s rule/S55 harness; source citations and immutable FULL prior evidence remain in verification entries and earlier devlog, no historic PASS/FAIL/NOT_RUN rewritten. Actual S57 file UTF-8 byte count 15358 (<16384). Product code/CLI/defaults/test harness untouched, and S55 native is not re-dispatched.

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Correct actual UTF-8 size of historical Auto catalog entry below unchanged enforced bound, retaining exact verification and source failures without product code changes."}
```
