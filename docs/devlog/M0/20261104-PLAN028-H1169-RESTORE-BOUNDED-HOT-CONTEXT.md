# PLAN028 H1169 — preserve bounded original M0 hot context

Governance [Action 41872756097](https://github.com/lly8666/wbd-next/actions/runs/41872756097) artifact13343909476: **Feature catalog check PASSED**, including retained 28 verification records and 13,822-byte bounded card. The same job then invoked `tools/governance.py validate` and failed only `unbounded context_refs`; independent role/scope audit reported the same explicit cause. H1168 incorrectly grew original M0 context list from 8 to 10 by adding H1160/H1165 historical references. Restore original eight, leave H1160/H1165 evidence files and prior devlogs intact. Current `evidence_refs` remains only H1166 source e568 matching `last_tested_source`; no stale evidence mixing. No product/fixture/workflow changes; do **not** retrigger native x86 already in-flight [Action 41872756479](https://github.com/lly8666/wbd-next/actions/runs/41872756479).

```feature-impact
{"kind":"none","ids":[],"reason":"Only existing cursor context refs bounded to prior scope; functional card/code unchanged."}
```
