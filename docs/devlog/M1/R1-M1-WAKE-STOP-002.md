# R1-M1-WAKE-STOP-002 · owner std thread armed/stop/return

Role M1 revision2 epoch1 on `work/m1-r1-runtime`; assigned by main `docs/decisions/M0-R1-next-worker-atoms.md` (main registry goal/done_when), not by stale M1 cursor. Previous HEAD `e511f13359afa267a7ca7dc02f25892ef8f1d3ce` was a cursor-only H; its Governance run 38539033023 succeeded. This atom does NOT add third-party packages or edit M0 shared files.

## Source and bounded mechanisms
- `runtime::wake`: std-only preallocated `sync_channel` owner queues, one consumer OS thread bound through `OnceLock<Thread>`, SeqCst `armed`, stop + in-flight count. Fresh/repair separate fixed-capacity queues; `try_send` returns Full/original value rather than blocking or dropping. There is no per-record Arc clone and only a shared gate per owner.
- Consumer inspects ready fresh→repair, returns, stop, fake clock deadline; after queue exhaustion it sets armed SeqCst and **inspects them all again** before `park` or `park_timeout`. Producer publishes first, then `armed.swap(false, SeqCst)` and unparks. Stop has a single transition; no producer can publish after observing stop; already-running publishers are tracked until drained.
- `memory::ReturnPath` now optionally registers the same wake gate once and notifies on final slab return, including channel-full fallback backlog. `stop_step` nonblocking drops unconsumed handles and does not claim `quiesced` until no outstanding loan or in-flight publisher. `wait_return_once` can park at most one explicit deadline interval, then return Pending rather than falsely releasing driver loans. No spin polling and no `sleep` inserted in tests.
- Existing `TxOwner/RxOwner` and `UniqueSealable/FrozenRecordHandle` remain separate. Actual byte quota remains in `TxOwner`; the std wake layer's bounded channels represent queue slot/notification proof, NOT a new general scheduling/codec implementation.

## New deterministic r1_ tests (R01/R02/M01)
1. push-before-arm idle→single fresh ready;
2. publish during the armed second-check interval using barriers;
3. send at park boundary (token before/after park ordering);
4. full repair queue does not block fresh;
5. stop rejects late offers and makes queued work undeliverable;
6. concurrent stop, queued message and frozen clones with full return backlog;
7. stopped owner is awakened by final frozen loan release;
8. fake monotonic deadline advanced across armed recheck.

All tests are under M1-owned lib source and selected by the existing compile-once `r1_` worker Actions consumer. **Before new exact-source Actions verification these tests are NOT_RUN.**

## Explicit boundaries
This is real std OS-thread park/unpark synchronization, not `rtrb`, Loom-exhaustive interleavings, eventfd/mio Waker, timer wheel, raw socket, target Windows native testing, physical test or performance claim. `OWNER_RUNTIME_READY` and `ARENA_READY` remain false; ABI features0, Go V4 disabled. The existing G2 dependency request `.governance/workstreams/M1/requests/M1-R1-SPSC-DEPS.md` remains open for M0. No new public ABI, Cargo or root CI modifications.

## Review after initial source S
Initial worker SOURCE `203eac4afef8497e485f9b7e9ed5116e2b3b73a8` compiled once and ran 18/18 native R1 tests in Actions 38566785197 (verified result artifact 11895097567). Concurrency review exposed a stronger deterministic test: producer can enter `try_push` just before stop yet publish after the owner's first drain. A follow-on S adds an explicit in-flight counter barrier case and a second drain after all publishers exit, so stop cannot declare quiescence with a hidden queued item. This follow-on code must receive its OWN native Actions qualification; old 18/18 does not pass it.

Two unrelated exact initial-S CI failures must be retained, not concealed:
- Governance 38566785008 reported `control or source moved mid-audit` while M0 was committing to main. No M1 path violation was reported; must check final H Governance on its own SOURCE.
- R0 native ABI 38566785047 ran its Rust binary and found **21 passed**; its shared `tools/r0_abi_bundle.py` insists that stdout contain substring `3 passed`. Previously `13 passed` incidentally contained this string; adding 8 named R1 tests makes `21 passed` not match. The native R0 ABI workflow is **FAIL**, even though the Rust execution returned rc0. M1 cannot edit root tool. Shared test ownership request `.governance/workstreams/M1/requests/M1-R0-ABI-HARNESS.md` submitted to M0; root CI not declared passing.

## Final code SOURCE and verification boundary
Final code SOURCE `81cbc57ae97ea8664c70e3ade6ecc718cc08d5d2` adds a 9th new deterministic stop/inflight publication test. Native Actions run 38567433037 on the same SOURCE returned **19/19 PASS**, compiled binary once and consumed the exact SHA256-pinned build artifact. Exact action hashes and case names live in `docs/evidence/M1/R1-M1-WAKE-STOP-002-actions.json`.

Other exact SOURCE actions: Governance38567433171 SUCCESS, G2-boot38567433122 SUCCESS, static-audit38567433089 SUCCESS, cross-ABI38567433119 SUCCESS; native-ABI38567433175 **FAIL** on the shared string-marker bug (its Rust binary 22/22 actual PASS, but the workflow is legitimately failed). Root harness is outside M1 scope; it must not be marked all-green. Product/perf/physical NOT_RUN, V4 DISABLED.
