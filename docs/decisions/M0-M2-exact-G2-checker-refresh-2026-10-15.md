# M0 · one-time M2 G2 checker ancestry continuation · 2026-10-15

## Reproduced independent blocker
M2 task `R2-M2-REVERSE-GRANT-OWNER-BENCH-006` code SOURCE `25642589f0feb12b44304fd21842c507a9314d35`: real compiled-once native [38678654629](https://github.com/lly8666/wbd-next/actions/runs/38678654629) **44/44 SUCCESS**, G2 bootstrap38678654565 and R0 static38678654572 SUCCESS. **Governance38678654568 FAIL**, evidence-only S `1228a11158a02e53e377ad3bb3cade5b83f1daba` Governance38679005438 FAIL, blocked cursor H `018a07c880473a896d40c0d97a59250212f7dad8` Governance38679115636 FAIL. This is NOT a qualified worker handoff. Preserve all three historical failures, never waive them.

Cause: checked-out M2 `tools/worker_scope_ci.py` blob `2e19d8aa1dd5eca1f27390b56b66776d08df36db` has G2_BASE `83bd720368b9be68b3c4c94d7462d20cf4d796db` and complete ancestry max64. Previous verified H exactly64; new code SOURCE65, so a structural bounded audit fails despite all affected code lying in M2-owned paths. Current M0 main tool already uses max96 and demands a **complete unique per-commit page** with exact path/parent audit, never truncated. An M2-controlled extension, force push, deleting evidence, changing registry ownership, generic root allowlist, or simply rerunning broken H is NOT approved.

## M0 audited exact-parent escape hatch, not generic worker root permission
This main-only change authorizes exactly ONE M2 branch single-parent commit:
- Parent **exactly** `018a07c880473a896d40c0d97a59250212f7dad8`.
- Sole changed path **exactly** `tools/worker_scope_ci.py`.
- New file blob **byte identical to the live authoritative M0 main tool** on the same validation run; ordinary tools, Cargo, registry and worker source edits forbidden in that commit.
- M0 control anchor `af8a8b40853845b6e876224d579bfb567df48e6c` must remain ancestor of live main; worker role ID must be M2, active branch, registry rev2 epoch1, same G2_BASE and complete <=96/100 ancestry and every commit/path checked.
- New refreshed M2 checkout must run full source-exact Governance; afterward create new evidence-only S explaining the repaired tool transport and preserving 44/44 code SOURCE plus original failures, verify S Governance, then cursor-only H (with new checkpoint=S) and H Governance. New H must be independently verified before marking accepted.

The checker exception was adapted from the pre-existing similarly exact-parent M3 checker refresh, without altering role path grants or bypassing per-commit source checks. **M0 does not write the M2 branch or claim the worker has performed the refresh.** If the live main blob moves before worker refresh, the validator rejects the attempt and M0 must review anew. No new M2 task is assigned while the current one is blocked.

## Other current acceptance
M1 fourth-wave native 71/71 SOURCE `0979314cacf8931a90840ad312dd50e9e2777d04` worker S `c8506836` Governance38679110643 and H `6ad61c34` Governance38679184618 SUCCESS; historical root R0 ABI count failure retained.
M3 native 96/96 SOURCE `0573798b27fa6fd6327ed1b997ee8cd50b0da526`, S `55a1248c` Governance38679104152 H `f198eb0c` Governance38679326550 SUCCESS, debug P0 measurements not release steady owner.
M4 raw RX classifier + inert AF_PACKET FD native 60/60 SOURCE `ae0b63b011512805f28f0cebff957cc662b0fb3c`, S `f7fc373e` Governance38679059068 H `bd413690` Governance38679197418 SUCCESS; no real raw live packet or product.

Main M3-012 nine test-only independent AEAD PN/FEC cases imported as exact worker blob with 94-case native selectors in source `46ff7c2d064df120822cc4aacb56806b7f9892f4`. The initial P0 run38679677311 **FAIL** only because its fast UDP measurement elapsed 0.916s below strict >=1s gate, not a Rust failure. M0 raised fixed loop count 20k→120k in new CODE SOURCE `404d37028a4c0d9949c379647dd1299609822cc7`, preserving gate; final exact CODE same-source checks must still complete. Physical, real GoV4 owner, live raw, 500Mbps, product remain NOT_RUN.
