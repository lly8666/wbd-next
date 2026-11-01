# H784 — H783 Governance evidence SOURCE schema failure (not a product rollback)

H782 Windows original native runner [41307403459](https://github.com/lly8666/wbd-next/actions/runs/41307403459) 21/21 and actual ZIP13084260528 remain **SUCCESS** on workflow HEAD `b035d79f05913c41384227c0821fe4f2d9e68b57`; product FEC still NOT_RUN. H783 docs/evidence commit [1eb64a4b](https://github.com/lly8666/wbd-next/commit/1eb64a4b807cd74be02e335b8076e9c70c948588) triggered Governance [41308031500](https://github.com/lly8666/wbd-next/actions/runs/41308031500) **FAIL**. Downloaded actual governance ZIP id13083758644, `structure.json` says `BLOCKED: evidence is for a different SOURCE`. Root cause exact new H783 evidence used `frozen_product_source` but did not include mandatory `source_sha` matching cursor `last_tested_source`. This is a new documentation/evidence contract failure, not a regression in H782 Windows job or proof of product FEC failure.

Repair: add exact `source_sha=48ed7ffe82aafa17a125948068a2ca6ee6a1593e` to existing H783 evidence (do not promote its status); valid cursor refs <=8. Retain H783 Governance FAIL, wait for source-scoped current Governance result. User focus remains Actions infrastructure FIRST (now proven in H782), then one safe full product WAL recovery proof before GameFEC real two-OS run. Do not restore other PLAN027 matrices.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct exact SOURCE field in already verified test-infrastructure evidence, no product or feature change."}
```
