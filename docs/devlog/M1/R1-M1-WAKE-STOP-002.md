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
