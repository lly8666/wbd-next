# PLAN027 H902｜修复 H901 SOURCE 证据引用合同

- [H901 governance Action41409840487](https://github.com/lly8666/wbd-next/actions/runs/41409840487) structure **FAIL**, not PASS: collected `structure.json` has `state=BLOCKED, reason=evidence is for a different SOURCE`. Feature catalog's own `feature-check.json` actually **PASS** (`NO_PRODUCT_OR_FEATURE_CHANGE`); its composite job failed when the same governance validator returned rc2. No affected product binary was executed in this Action.
- Cause: original H901 cursor `evidence_refs` held previous `c85b...` Normal100, `33e1...` failed unilateral105 and current `f3f4...` Game4. `tools/governance.py validate_repo` requires **all** referenced evidence `source_sha == cursor.last_tested_source`, even when `unverified=true`. New H900 evidence initially had only `source` key, without the required `source_sha`.
- H902 makes `evidence_refs` **current H900 SOURCE only**, adds explicit `source_sha` to H899/H900 standalone evidence records and retains old source results in their own exact files/devlogs. No source qualification promoted, no product code or fixture change, no new native action. The current cursor checkpoint advances to H901; original H899 product/lifecycle FAIL and H900 exact Game4 OFF PASS unchanged.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct current-SOURCE evidence reference schema after observed governance FAIL; no product, feature or settings change."}
```
