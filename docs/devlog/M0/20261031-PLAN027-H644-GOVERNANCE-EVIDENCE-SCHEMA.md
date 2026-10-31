# PLAN027 H644 — evidence schema repairs, no new product measurement

H643 main `f93a625a4c89d7f688f0e65f6b7cf3723bd739d0` actual Feature Catalog size gate now passes after retaining older Game card provenance in Git history. Remaining governance structure FAIL [41214455242](https://github.com/lly8666/wbd-next/actions/runs/41214455242): `unknown schema: docs/evidence/M0/PLAN027-H643-SOURCE11F-GAME2-AND-CANCEL-20261031.json`. Correct H643 and historical H640 evidence documents with `schema_version: 1`; current H643 `source_sha` explicitly fixed to original 11f1881ff68afa22c5b0ca957d6808420a878a06 to match the cursor's tested source, never the later evidence-only main HEAD. No data, real run conclusion or manifest altered.

Already-dispatched H643 parallel one-scene original native Actions [Auto A4](https://github.com/lly8666/wbd-next/actions/runs/41214482312), [Normal 300s long](https://github.com/lly8666/wbd-next/actions/runs/41214487018), [Fixed C50](https://github.com/lly8666/wbd-next/actions/runs/41214491798) remain **IN_FLIGHT**, source-locked to H641 build41210457594; no repeat dispatch. H641 FEC2/4 and B106 four canceled stages remain NOT_PASS. PLAN027 §0 still PARTIAL.

```feature-impact
{"kind":"none","ids":[],"reason":"Only make already recorded source-locked negative/positive evidence conform to governance schema and update recovery cursor; no feature, product or configuration changes."}
```
