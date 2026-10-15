# M2 → M0 — stable main control interval for source-exact R2 Governance

**Status:** OPEN / BLOCKED
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
