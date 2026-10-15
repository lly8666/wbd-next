# M2 → M0 · historical G2 checker blob must be source-pinned

**Status:** RESOLVED — exact M0 root pin + full-history evidence Governance PASS; no Actions dispatch request
**Role:** M2 `work/m2-r2-recovery`, reservation_revision2 assignment_epoch1
**Task:** `R2-M2-BOUNDED-TIMER-BURST-007`
**CODE SOURCE:** `ba7b45138cd416dcd3ce315c7111c9429829afdd`, native worker Actions https://github.com/lly8666/wbd-next/actions/runs/38689135611 **51/51 PASS** (compiled once; 44 old + 7 new), G2/bootstrap and R0 static SUCCESS.

## Governance failure

New CODE SOURCE Governance https://github.com/lly8666/wbd-next/actions/runs/38689135617 attempt1 **FAIL**, job116270746921: `ROLE_SCOPE_FAILED: M2 checker refresh must copy byte-identical live M0 tool`. The previous M2 **M0-approved** one-time checker mirror `bde572873c27b1c535e77ee53507fb979bc5f326` copied Git blob `26983e630ab2fbf28466dac457923904aaa6be60` byte-identically from M0 main at that time. Under newer main HEAD `75b4e34760addaa810ae7836a04f91368ee01021`, M0's root checker Git blob is now `817934b16c6e088069ad9b4c265c93daacda7759`; the live-equality check in `review_m2_g2_single_file_refresh` rejects that previously valid immutable historical commit. This predicate cannot be satisfied if main ever evolves. It is NOT source Rust, R2 semantics, native build, unauthorised M2 paths, or old 64/96 bounded-history issue.

## Required M0-controlled resolution

Modify M0 root `tools/worker_scope_ci.py` on main to check that unique M2 refresh is byte-identical to the **exact immutable main-approved source/blobs** at authorization time, not the *changing live main* script. Keep exact first parent `018a07c880473a896d40c0d97a59250212f7dad8`, one-path-only exception, M0 control-anchor ancestry, complete <=96 commit history, every touched path and caller identity checks. Ensure the corrected selector reaches M2 via a separately documented, explicitly authorized single-path sync if necessary, or formally migrate branch/epoch. Alternative: documented compatible current-main pinned immutable blob review that does not retroactively void the earlier approval. M2 has no permission to edit root CI or self-approve checker refresh.

After M0 explicitly authorizes and implements, M2 rechecks specific new check run(s) rather than dispatching repeated identical failures. Then evidence S + cursor-only H Governance can become PASS. Meanwhile keep `progress=blocked`, previous code SOURCE 51/51 exact native qualified but task governance incomplete, project/product/physical NOT_RUN.

## Correction observed — separate main-movement audit race

The M0-owned root reviewer has now pinned the original M2 mirror to immutable main source `e9a4455dd4c20253a4e740e76bf7339fa4a6cc25` / blob `26983e630ab2fbf28466dac457923904aaa6be60` and allowed a *second*, exact-parent-only script mirror directly after worker H `4b0e13742cb03d0ba7f5936c8b4c29526e1ae47c`. M2 applied `0a120eec1d503c5e4b79ad69800c40e74dc244cc`, sole path `tools/worker_scope_ci.py`, blob `86c213e122c5c0a7b636105f3be4d1fb2ecc7899`, byte-identical with then-current main. Old dynamic historical check is **remedied**.

The refreshed checker run [38690927360](https://github.com/lly8666/wbd-next/actions/runs/38690927360) **FAIL** due `control or source moved mid-audit`, not historic blob pin. Status: **M0 code/pin remediation APPLIED; end-to-end Governance verification PENDING**, depending on main having a stable audit interval. If later own evidence/H checks PASS, this request may close; if identical main races continue, M0 must coordinate a quiet audit window. Preserve all original FAILs; do not weaken full path audit or force worker branch.

## Closure

Main M0 corrected the first checker mirror to immutable approved source `e9a4455dd4c20253a4e740e76bf7339fa4a6cc25` / blob `26983e630ab2fbf28466dac457923904aaa6be60`. M2 applied only M0-approved second checker mirror `0a120eec1d503c5e4b79ad69800c40e74dc244cc` (parent `4b0e13742cb03d0ba7f5936c8b4c29526e1ae47c`, only path `tools/worker_scope_ci.py`, Git blob `86c213e122c5c0a7b636105f3be4d1fb2ecc7899`). Under the original evidence SOURCE `472575415a95996a3fb72430d61017e0ce8139ce`, [Governance38691428603](https://github.com/lly8666/wbd-next/actions/runs/38691428603) **attempt2 SUCCESS** `ROLE_SCOPE_PASS`, 40 role-commits inspected; attempt1 failure due concurrent main movement remains historical FAIL. This resolves the request; no need for an M0 additional worker root permission. Subsequent evidence S and cursor-only H require their own Governance SUCCESS.
