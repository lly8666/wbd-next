# PLAN028 H1554 | governance SOURCE provenance correction (2026-11-11)

The original mixed loss0/loss30 Action 42860982489 ran under source `76d5319c12f614d072ca83a24d9c5578311f091d` and failed before TLS. Its first-error evidence H1553 originally omitted `source_sha`, while the cursor's `last_tested_source` was 76d and `evidence_refs` included an older 4388-scoped H1552 record. Existing `tools/governance.py validate_repo` requires **every** cursor evidence SOURCE to equal `last_tested_source`. This was a new clerical gate failure in governance Action 42938017973, not a native data-plane failure.

Correct the H1553 original-failure evidence `source_sha=76d...`, keep `candidate_fix_source_sha=fe5a8fa56a72cd41a35424e1ade5536f7afad6d8` separate and unverified, and point current cursor only to matching H1553 evidence. Preserve older 4388/H1552 evidence in its own file. Set checkpoint to fe5a8fa. No product or test runner source changed in this commit; no Windows network rerun / no new scenario dispatch.

In-flight true-source Action [42938018017](https://github.com/lly8666/wbd-next/actions/runs/42938018017) already passed cheap 6/6 mixed source tests including extracted LF-byte generator; native loss0/30 business/MTU/Stop still pending real logs. Remain PLAN028 IN_PROGRESS.
