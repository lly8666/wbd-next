## PLAN028 H1333 — fix only the governance evidence SOURCE attribution

H1332 Action42382999546 passed preflight and is running native x86 180-second original TLS/Rust M4 zero-loss business unchanged. Separate governance Action42382999582 recorded FAILURE `BLOCKED: evidence is for a different SOURCE`, because H1332 test-only *preflight* evidence JSON lacked required top-level `source_sha`; `cursor.last_tested_source` remains prior H1331 `65b07f829478a6c4a4f6f2da6112417fa761f9c1`. Add that exact value, explicitly `result=PARTIAL`, `artifact_verified=false`. The frozen original x86 executable **still has distinct SHA 6c5fd909...** and is recorded separately. Do not alter or rerun H1332 workflow or any product. Await raw actual original app/CPU results for source-scoped capacity classification. Maintain H1317/H998 failures and L3 NOT_RUN.

```feature-impact
{"kind":"none","ids":[],"reason":"Governance/source attribution metadata repair only; no product or running native x86 fixture change."}
```
