# PLAN028 H1564 | use governance PASS enum for scoped real source qualification

[Action42954586580](https://github.com/lly8666/wbd-next/actions/runs/42954586580) finished a documentation-only structure failure: `verified cursor lacks reviewed PASS evidence`. The audited source8302 original-Go+native-Rust [Action42953971625](https://github.com/lly8666/wbd-next/actions/runs/42953971625) and [artifact13825963487](https://github.com/lly8666/wbd-next/actions/runs/42953971625/artifacts/13825963487) had ACTUAL PASS of 3 credential TLS handshakes, Alice static10.66.0.2, Bob auto10.66.0.144, 59/59 unique app UDP and exact owned Stops. However H1563 evidence wrote `result=PASS_SCOPED` which is not in repository `governance.RESULTS`. For verified cursor, `result` must be **PASS** and `artifact_verified=true`. Correct only the receipt's result enum, keep separate `qualified_scope` and `result_classification=PASS_SCOPED`, leave `plan_status=IN_PROGRESS`; source SHA and original records identical. Cursor is now verified for this exact scoped source, not global PLAN028. Old failed governance Action preserved, no product/fixture code change, no new network dispatch.

```feature-impact
{"kind":"none","ids":[],"reason":"Only normalize evidence PASS enum for previously proven scoped real Linux original native test, no product change, no feature qualification broadening."}
```
