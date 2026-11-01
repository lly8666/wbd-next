# H805 — H804 evidence file schema corrected, real Game2FEC performance in flight

[H804 Governance41325197123](https://github.com/lly8666/wbd-next/actions/runs/41325197123) FAIL: downloaded actual governance artifact13091280293 `structure.json` says `evidence is for a different SOURCE`; H804 verified new real 43-file native artifact and updated cursor `last_tested_source=21ae892f...`, but new JSON accidentally used `product_source_sha` without required `source_sha`. Add `source_sha=21ae892fddd6a8d6338fb74a73e8e45380f1631a` to that same H804 artifact-bound evidence (plus truthful scoped verified status); no change to source/run, 1Mbps first, 3226 parity, owned Stop or unverified abnormal crash. Keep cursor `unverified=true` because 10Mbps performance, abnormal WAL and other PLAN027 are outstanding. No product code changed.

H804 [performance controller41325197048](https://github.com/lly8666/wbd-next/actions/runs/41325197048) SUCCESS dispatch-only, real new [Game2FEC6 native41325214203](https://github.com/lly8666/wbd-next/actions/runs/41325214203) and independent timeout watcher41325223158 in flight at this evidence repair. 23 previous helpers removed but canonical original driver/full artifact + ONE safety watcher retained.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct a required source_sha key in existing genuine H803 native artifact-bound evidence and hot M0 cursor; no feature or executable product modification."}
```
