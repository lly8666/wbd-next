# M2 → M0 — stable main control interval for source-exact R2 Governance

**Status:** SUPERSEDED — moving-main race documented; current deterministic blocker is second historic checker blob mismatch in M2-SECOND-CHECKER-IMMUTABLE-BLOB-008.md
**Worker:** M2 `work/m2-r2-recovery`, registry rev2 epoch1, task `R2-M2-RACK-POSITIVE-WITNESS-INDEX-008`
**CODE SOURCE:** `7875137949f61fead1374d2933798c61814adb92`; exact compiled-once worker-native [#38706944249](https://github.com/lly8666/wbd-next/actions/runs/38706944249) **55/55 PASS**, G2 [#38706944163](https://github.com/lly8666/wbd-next/actions/runs/38706944163) PASS, R0 static [#38706944248](https://github.com/lly8666/wbd-next/actions/runs/38706944248) PASS.

## What is blocking source and handoff governance

The worker G2 checker traverses all ~80 worker/main commits from the immutable G2 base with a strict per-commit scope/parent and live main head identity audit. Its configured bound is <=99 and checker blob `86c213e122c5c0a7b636105f3be4d1fb2ecc7899` matched current main and worker, so no new checker fix/role expansion is requested. However M0 concurrently updates main faster than a full worker audit can complete:

- Code SOURCE Governance [#38706944070](https://github.com/lly8666/wbd-next/actions/runs/38706944070) attempt1 **FAIL** GitHub REST `RemoteDisconnected`; attempt2 **FAIL** `control or source moved mid-audit`.
- Evidence S `a46dee2cce988357df9d5157ccd0184d3dac7fd1` [#38707876126](https://github.com/lly8666/wbd-next/actions/runs/38707876126) attempt1 and attempt2 **FAIL** `control or source moved mid-audit`; job IDs116331695778 and116332701705.

There are **no failing R2 native unit tests** or demonstrated M2 path/role violations. Historic FAIL artifacts and true attempts are preserved in `docs/evidence/M2/R2-M2-RACK-POSITIVE-WITNESS-INDEX-008.json`. Do not mark this worker ready for main acceptance yet.

## M0 action requested

Coordinate a quiet main ref/control window for one complete M2 evidence and H-only Governance run (audit requires many GitHub REST calls), with all live role/ref and changed-path validations intact. Alternatively explicitly approve a source-pinned immutable M0 registry/control attestation mechanism of equivalent strength, implemented by M0 alone. No generic `tools/` edit privilege, force-push, unbounded ancestry, suppressed failure, or scope waiver. When a stable window is available, M2 can re-run exact current immutable evidence/H qualification and close this request if independent Governance reports SUCCESS.

This is not a request to enable real Go V4, Rust owner/ABI, kernel driver, p99/500Mbps or physical testing; these remain M0 owned and NOT_RUN. The bounded R2 algorithm and test evidence remain available without alteration.

## Verified role-scope success and precise cleanup

The previously blocked cursor H `0c8f3bb68adcaf417aae737e1cdf981d936ab145` (cursor-only after evidence S2) passed full-history [Governance #38709247413](https://github.com/lly8666/wbd-next/actions/runs/38709247413) attempt1 **SUCCESS**, `ROLE_SCOPE_PASS`, 46 role-scope commits. A main-only quiet period is therefore not intrinsically required as a governance implementation change; the independent H check demonstrably succeeded.

An attempt2 re-run of OLD evidence S2 `1e54d80134a121068099e72c3a8ed30db436d51b`, run #38708744888, was **FAIL** due `branch ref changed while checking identity`, since H was already the real branch HEAD. This **must not** be retried, waived or called PASS. Issue a NEW M2-only evidence commit **from H**, hold that exact commit at live HEAD for its own Governance, then issue the final cursor-only H. Once both succeed, no M0 work request remains. This file records the precise path to closure, retains all historical FAIL evidence, and does not authorize changes outside M2 paths.

## Live-HEAD S3 still blocked
M2 created evidence S3 `9f4c3574caf49afdbfb38a5dbd9fdba7c8d13a85` on already audited cursor H `0c8f3bb68adcaf417aae737e1cdf981d936ab145`. S3 **remained actual HEAD** throughout [Governance #38711507683](https://github.com/lly8666/wbd-next/actions/runs/38711507683) attempt1, which **FAILED** with `ROLE_SCOPE_FAILED: control or source moved mid-audit`, job116343744144, artifact11960592215 sha256:57fe0d746d5f7ba9d936252c41e66a38ffe346f4c214a494aa5b56c3334c29d3. Unlike old S2 rerun, there was no stale branch-ref issue. Thus M0 still needs a stable main-control audit interval or strict approved pinned-control alternative. Native R2 55/55 and G2/static PASS; product NOT_RUN. No source/path/governance failures erased or relabeled.

## Superseding root cause confirmed

Evidence S4 `28aa619ad31d61891a479ea4743db2b55f232c59` [Governance #38712108247](https://github.com/lly8666/wbd-next/actions/runs/38712108247) **FAIL** `ROLE_SCOPE_FAILED: second M2 checker mirror must copy byte-identical current main tool`. The current deterministic blocker is no longer solely main moving; the live equality predicate can never remain stable after M0 changes its root script. See the **open** request `M2-SECOND-CHECKER-IMMUTABLE-BLOB-008.md`. Earlier scope-run and moving-main failures remain historical FAIL.
