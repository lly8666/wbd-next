# PLAN027 H845 | SOURCE-honest cursor and feature-impact enum

- Governance on prior main failed structure because H844 cursor had last_tested_source fdc but evidence_refs mixed f5 and fdc. Evidence remains unchanged under each SOURCE. Cursor now points only to exact fdc H844 native evidence reporting business 82.4% and p99~21.3s FAIL; old f5 evidence remains in its JSON/devlogs and Git history.
- Feature catalog prior main failed because feature-impact.kind update is unsupported; canonical kind updated now used in H844 devlog. Card remains <=16KiB.
- No product/runtime/workflow edit in H845. SameVM R100 Action41366111073 already running; no duplicate dispatch.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct governance SOURCE-scoped cursor refs and metadata enum, no product changes."}
```
