# M2 → M0 — immutable source-pin the second approved checker mirror

**Status:** REMEDIATED / handoff evidence S and H pending (2026-10-15)
**Role:** M2, `work/m2-r2-recovery`, main registry revision2 assignment_epoch1, `R2-M2-RACK-POSITIVE-WITNESS-INDEX-008`.
**Code SOURCE:** `7875137949f61fead1374d2933798c61814adb92`; native [#38706944249](https://github.com/lly8666/wbd-next/actions/runs/38706944249) **55/55 PASS** compiled-once; G2 scoped bootstrap38706944163 SUCCESS, static38706944248 SUCCESS.
**Trigger:** evidence S4 `28aa619ad31d61891a479ea4743db2b55f232c59`, [Governance #38712108247](https://github.com/lly8666/wbd-next/actions/runs/38712108247) attempt1 **FAIL**, job116345754702, artifact11960752841 sha256:383aa1dbf1229fa5000004b1ba349022885c488af0df1dfe16bb5289f19aff7e.

## Reproducible, root-owned deterministic policy defect

The second **M0-explicitly-approved, first-parent and one-file-only** M2 checker mirror was commit `0a120eec1d503c5e4b79ad69800c40e74dc244cc` directly on H `4b0e13742cb03d0ba7f5936c8b4c29526e1ae47c`, changing only `tools/worker_scope_ci.py`. At the historical M0 authorizing main source `d902842a31fd6b032a5f1bab515b93c21f28b0aa` the root script Git blob was `86c213e122c5c0a7b636105f3be4d1fb2ecc7899`, **exactly identical** to the frozen M2 second mirror Git blob. That main source remains an ancestor of observed main `529af37f710d09426f8f1422e8dbcf29157548ad`.

After M0 legitimately changed the root script again, current main Git blob became `cf46d814142b09aeaa10053d4c7b8ac581d08d33`. The current `review_m2_g2_second_single_file_refresh` compares `contents/tools/worker_scope_ci.py?ref=<live_control_sha>` against that **historical** immutable worker commit, causing `ROLE_SCOPE_FAILED: second M2 checker mirror must copy byte-identical current main tool`. This is the same retroactive live-script bug previously fixed for the FIRST approved checker mirror, now in the SECOND mirror. Unlike intermittent `control or source moved mid-audit`, this remains reproducible even if main stops moving.

## Requested M0 action and exit

1. M0 change root-owned checker v2 reviewer to compare ONLY the exact previously approved immutable main source and known blob (e.g. `d902842a31fd6b032a5f1bab515b93c21f28b0aa` / `86c213e122c5c0a7b636105f3be4d1fb2ecc7899`), after independently verifying that source is an ancestor of current main. Keep the exact permitted parent `4b0e137...`, sole path `tools/worker_scope_ci.py`, no generalized tool/write rights, and full bounded per-commit path, SHA, role and live-ref checks.
2. If the worker checkout must run the corrected checker too, issue a **new** formally reviewed, exact-parent one-path sync, or a safe authorized branch/epoch migration. The current bounded G2 ancestry may approach 99 commits and must not be silently waived or made unbounded.
3. Provide an auditable stable-ref window / strict pinned-control equivalent so M2 can obtain own evidence S and final cursor-only H Governance PASS. Retain all earlier FAIL attempts unchanged; do not force-push or attribute product/authentication success to pure tests.

M2 will remain `progress=blocked` until this M0 policy defect is repaired and independent role-scope checks PASS. Real Go V4 protected authority, driver, ABI, 500Mbps/p99 and physical remain **NOT_RUN**.

## 2026-10-15 observed remediation

M0 granted a strict one-time exact-parent checker mirror in `main:.governance/exceptions/M2-G2-008-checker.json`; the only worker mirror commit is [`5bfacc7814183fc631a827725ee432c1c42b029d`](https://github.com/lly8666/wbd-next/commit/5bfacc7814183fc631a827725ee432c1c42b029d), direct parent `35c45f2`, changing only `tools/worker_scope_ci.py`, matching Git blob `69bebb966c60623c3b0a96c6915bf75540eb406b`. [Governance #38721567164](https://github.com/lly8666/wbd-next/actions/runs/38721567164) attempt1 SUCCESS, `ROLE_SCOPE_PASS` for 51 scoped commits. Independent, non-gating continuity drill returned BLOCKED due a JSON parse error; no product/physical proof. Code-source native 55/55 remains unchanged. New evidence S and cursor-only H still require their own observed Governance checks; earlier FAILs remain unchanged.
