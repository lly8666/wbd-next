# M2 → M0 — PACK-009 bounded read-only scope audit cannot complete (GitHub HTTP 403)

**Status:** OPEN / M0 shared-checker/API boundary
**Role:** M2, `work/m2-r2-recovery`, main registry revision2 / assignment_epoch1, task `R2-M2-RECEIPT-REPAIR-BOUNDED-WORKPACK-009`.

## Independently verified scoped code (not product)

Code S `660c4d392b78c8242dcf04e1d2634797959718f3` changes only `crates/wbd-recovery/src/receipt.rs` and M2 devlog; it paces unreported per-lane PTO, does not throttle 32 genuine RACK candidates, and indexes queued expiration independently. Worker-native [#39000122056](https://github.com/lly8666/wbd-next/actions/runs/39000122056) **64/64 PASS** compiled once; G2 [#39000122045](https://github.com/lly8666/wbd-next/actions/runs/39000122045) SUCCESS, R0 static [#39000122051](https://github.com/lly8666/wbd-next/actions/runs/39000122051) SUCCESS. ZIP digests verified and pinned in `docs/evidence/M2/R2-M2-WORKPACK-009-pto-tail-and-rack.json`. GoV4 live auth, M1 arena, driver, product performance and physical all NOT_RUN.

## Independent Governance failures, exact root symptom

- Code S Governance [#39000122062](https://github.com/lly8666/wbd-next/actions/runs/39000122062) attempt1 **FAIL**, job 117301084509, artifact 12088003964 `sha256:8b8e680f295e264f235aa312fa155957d15ce996e78572a9e652195ff99de701`: `ROLE_SCOPE_FAILED: GitHub read failed HTTP 403: compare/83bd720368b9be68b3c4c94d7462d20cf4d796db...660c4d392b78c8242dcf04e1d2634797959718f3`.
- Evidence S `692545ab06b5b02807d671ae2b1aa16e7c33d4b0` Governance [#39000303210](https://github.com/lly8666/wbd-next/actions/runs/39000303210) attempt1 **FAIL**, job 117301630083, artifact 12088429076 `sha256:aec3845ea3939b2f432759ad6312afca6da657e0da5cfca151d1c8bb7709e63d`: the **same HTTP403** for `compare/83bd7203...692545ab`.

A separate read-only GitHub Connector `compare_commits(83bd7203..., 692545ab...)` returned `ahead_by=100` and 97 changed files; this is NOT a substitute for Runner `ROLE_SCOPE_PASS` or a complete bounded per-commit history. The root cause may be API budget/secondary rate limit or checker pagination; do not guess a bypass. Earlier worker HEAD `e48516d` Governance38998789637 separately failed because main moved; all failures retained.

## Minimal requested M0 action

Diagnose the shared governance/API comparison 403 at the pinned baseline and the >99-commit audit boundary, then provide an authoritative **central** source-exact worker scope attestation via already-owned main workflow or a bounded checker/access remedy. Retain per-commit paths/epoch/role/identity, exclude no unauthorized path, and avoid another worker mirror or loosening shared controls. If any support tooling changes are needed, M0 owns them. M2 will continue only owned PACK-009 work, keeping cursor partial/unverified and exact-source native/G2 facts.

No product/real authentication/physical performance claim; no force-push, no repeated identical failing Governance dispatch.
