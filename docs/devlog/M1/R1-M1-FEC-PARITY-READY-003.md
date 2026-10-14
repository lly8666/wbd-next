# M1 R1-M1-FEC-PARITY-READY-003 — bounded owner-local parity-ready integration

Authority: main registry rev2 / M1 epoch1 / work/m1-r1-runtime unchanged, from `docs/decisions/M0-parallel-worker-atoms-2026-10-14.md`. Previous cursor seq3 checkpoint `0a1d51546073d9ea32c3ef9bc8900377131beb33`, HEAD `49d886d639b7ba93aca00cfc0e305b23017d0cc8` contains only prior cursor-only H, Governance 38568033254 SUCCESS. No worker pending actions/intent.

## First scoped implementation

- `runtime/parity.rs`: independent bounded owner-local `ParityReady` queue using immutable `FrozenRecord` handles; fixed slot capacity, byte budget, max age and strict absolute `MonoNs` eligibility, separate from fresh and repair quotas. `VecDeque` is preallocated and ordered by deadline; only handle metadata is moved (no payload copying). Expired handles release back to the original arena via its existing bounded returns.
- `runtime::TxOwner`: `with_parity` opt-in; normal `new` remains FEC/off short-circuited without parity allocation. `offer_parity(record,now,eligible_at)` accepts ONLY already-eligible FEC work on a declared due time; no encoder, source group or parity generation here. TX scheduling checks due before serving parity, never withholds the first fresh for a parity timer, and allows one competing repair or parity after at most ten fresh when backlog exists; when both competing classes ready their service turns alternate.
- `runtime::wake::WakeGate`: shares the existing SeqCst armed/store/recheck/park protocol through `wait_scheduled`; `TxOwner::wait_ready` computes the exact eligible monotonic parity deadline rather than a fixed 32ms batching sleep, and observes owner stop and returned loans. The OS only parks while idle, no per-packet thread or timer allocated.

## Scoped test expectations (new `r1_` worker-native tests)

1. First business fresh before a 32ms parity, and parity cannot send one nanosecond before due;
2. parity-only owner fake-MonoNs absolute timer + shared wake token, no early dispatch;
3. out-of-order parity deadlines do not cause parity-only HOL;
4. independent fresh, repair, parity limits under pressure;
5. bounded parity and repair fairness with sustained fresh;
6. parity hard-age and budget boundary, and no stale wire handle;
7. full three queues + stop + retained frozen clone + return backlog race;
8. parity-only wait after stop must never emit delayed wire;
9. preserve one slab allocation without additional whole-wire copying.

All tests compile as unit tests in existing `wbd-engine` library under current `worker-native-tests.yml` (no dependency/workflow modifications). **This devlog is a code intent, not a PASS:** promote only after exact-source Actions compile-once consumer and artifact verification, then evidence S and separate H.

## Boundary

No FEC encoding, actual M3 pipeline hookup, NIC send, timer wheel, real rtrb SPSC, loom, mio/eventfd, Windows, production V4, ABI/Cargo/root CI changes. Existing M1 std-only wake+stop proof and `wbd-types::buffer_contract` are consumed, not altered. Owner and arena READY remain false. Product/performance/physical all NOT_RUN.

## First native result and bounded hot-path refinement

SOURCE `cfaf19e705d1b7295ccb3bee95baa799ce1052b3` compiled once and ran actual 28/28 `r1_` tests (prior 19 plus 9 new parity) in GitHub Actions38598099985, artifact11910732275 SHA verified; Governance38598099977, G2-boot38598100135, static-audit38598100038, cross-ABI38598100441 SUCCESS. R0-native-ABI38598099978 **FAIL**: actual Rust binary executed 31/31 tests with rc0; old branch-local `tools/r0_abi_bundle.py` erroneously checks unfiltered output for literal `"3 passed"`, as recorded in the pre-existing M0 request. Main already contains a correct `r0_abi_` test selector but the M1 work branch does not; M1 may not cherry-pick shared files itself.

Review found `ParityReady::expire` scanned all pending optional parity records on each fresh dispatch, even with no due parity. The second S changes the hot-ready path to an O(1) head check; the (bounded) expiry sweep occurs on admission pressure, and due stale entries are dropped on dispatch. Admission invariant `ready_at <= expiry` and deadline sorting prove later expiry cannot require an earlier wake than the head ready time. New targeted test exercises expiry behind a nonexpired ready head. First 28/28 does **not** qualify this changed second source; wait for its exact own native Actions.
