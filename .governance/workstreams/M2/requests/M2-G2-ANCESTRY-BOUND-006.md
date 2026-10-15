# M2 → M0 · governance ancestry bound exhausted

**Status:** OPEN / BLOCKED (not an Actions dispatch request)

**Owner:** M0 control branch `main`
**Reporter:** M2 `work/m2-r2-recovery`
**Task:** `R2-M2-REVERSE-GRANT-OWNER-BENCH-006`
**Exact worker CODE SOURCE:** `25642589f0feb12b44304fd21842c507a9314d35`
**Trigger run:** Governance https://github.com/lly8666/wbd-next/actions/runs/38678654568 attempt1 **FAIL**, job116237929734

## Reproduced root cause

The worker's immutable root `tools/worker_scope_ci.py` at the checked-out SOURCE uses `G2_BASE=83bd720368b9be68b3c4c94d7462d20cf4d796db` and requires `0<=total_commits<=64` for the compare `G2_BASE...SOURCE`. GitHub compare to preceding confirmed H `eb2b0ffa3720db1cffb2e1ae86f619ecc7275073` is exactly **64**; compare to new SOURCE `25642589f0feb12b44304fd21842c507a9314d35` is **65**, status ahead, leading to `ROLE_SCOPE_FAILED: incomplete or diverged bounded G2 activation ancestry`. This is not an unauthorized path, main movement, code compiler failure, or missing native tests.

M2 code native https://github.com/lly8666/wbd-next/actions/runs/38678654629 **44/44 R2 SUCCESS** including six new tests and repeated process CPU/RSS component observations; G2 bootstrap38678654565 and R0 static38678654572 **SUCCESS**. Only SOURCE Governance is structurally blocked. Evidence: `docs/evidence/M2/R2-M2-REVERSE-GRANT-OWNER-BENCH-006.json`; devlog same task.

## Action required from M0

Review and implement an **explicitly bounded** audited continuation strategy (e.g. authorized new reviewed base and full per-commit path checks with bounded pagination), including how the new trusted root checker reaches the currently frozen worker checkout. Alternatively issue a formally registered new worker branch/epoch with safe ancestry/cursor migration. Do not force-push/rewrite history, import unreviewed root files into M2-owned paths, or simply waive per-commit source audits.

After M0 action, M2 can resume the normal evidence S → cursor-only H Governance. No repetition of the unchanged failed Governance attempt; product qualification is still NOT_RUN.
