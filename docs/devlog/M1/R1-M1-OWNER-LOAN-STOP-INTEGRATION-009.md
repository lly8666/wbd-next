# M1 · R1-M1-OWNER-LOAN-STOP-INTEGRATION-009 — owner loan/Stop lifetime

## Assignment and scope

Live main .governance/registry.json rev2, M1 epoch1 active, branch `work/m1-r1-runtime`. New task decision `docs/decisions/M0-next-wave-owner-repair-driver-2026-10-15.md` (main-only). Prior M1 cursor seq10 checkpoint `baae8e310995dfedb825922b478b88e7f54357a0`, previous H `08bacd9f16a5ee8c6d95082f43dee4a2fb456291` was cursor-only, Governance38683183557 SUCCESS. No role/root/shared/ABI/Cargo/dependency changes.

## Observed missing invariant and minimal fix

Existing `ScopedOwner` already prevents old-generation callback/reoffer, holds immutable FrozenRecord Arc bytes and UniqueBuffer slabs through bounded `LoanBatch`, and keeps old RetiredScope ledger while new generation can dispatch first fresh. `Arena` already has a fixed total-slot-capacity return backlog on saturated one-slot return channel. Its slot generation increments on final borrowed return. The existing 75 scoped `r1_` tests establish the 0/1/32/33, first fresh, age/stop, unchanged preallocated vector pointer, ABA and payload noncopy baselines; no generic new scheduler/driver pool is needed.

One actual defect: `ScopedOwner::stop(token)` used the liveness guard, so a repeat Stop with the *same* current generation returned `ScopeError::Stopped` rather than being an idempotent no-op with a stable cancellation report and valid retained ledger. This atom gives the owner a `stop_canceled` counter captured ONLY on initial `retire()`; repeated Stop on the same current scope returns the original cancellation count and same Arc ledger without re-drain, re-drop, or waking a stopped queue. The counter resets to zero when a new `ScopedOwner` generation is installed. Token identity is still Arc pointer identity, so retired/ABA tokens remain stale on a different generation. `checked_tx_ready`/`checked_rx_ready` and new offers remain blocked after Stop.

## Five smallest owner-local counterexample tests

File `runtime/loan_stop.rs` is included only `#[cfg(test)]`:
- `r1_owner_loan_stop_idempotent_cancels_only_undispatched_33_tail`: 33 TX + 33 RX, take 32+32, Stop twice reports identical two canceled queued tails, both caller-held batches/64 arena loans remain through STOP, no offers/re-dispatch, final bounded cross-thread return after arena stop
- `r1_owner_loan_stop_held_frozen_arc_last_clone_after_batch_fence`: one frozen record cloned to model an already-handed-off external/driver borrowed pointer, pointer equality confirms no payload copy, Stop never frees it; distinguishes RetiredScope **batch-count** fence from full Arena frozen-clone loan quiescence
- `r1_owner_loan_stop_old_generation_33_plus_new_first_fresh`: 33 TX+33 RX, 32+1 dispatch in both classes, retained oldest FrozenRecord pointer/clone; rotate two generations, old callback and wrong-lane reoffers refused, old batch forbidden under new token, new fresh ahead of repair while old loans remain, repeated Stop and concurrent old drop
- `r1_owner_loan_stop_bounded_full_return_backlog_two_generations`: 32+32 old and 16+16 new = all 96 slots loaned, return channel capacity one; owner stop + arena stop then two threads release both generations, total-slot bounded fallback returns exactly 96, no retired/extra frees
- `r1_owner_loan_stop_restart_aba_stale_token_cannot_reenter`: numeric-identical owner ID/serial after restart still rejects old token and retained old batch, while new fresh dispatches.

The test-specific stand-in for an external held driver lease is a cloned immutable `FrozenRecord` (Arc). It is NOT proof of actual kernel/UDP/AF_PACKET completion semantics, nor cryptographic authenticated admission, nor shared Go V4 origin. No production driver syscalls, new dependency, performance budget, physical/WinARM/product/500Mbps claim. `OWNER_RUNTIME_READY=false`, `ARENA_READY=false`.

Native test evidence must show all **previous 75/75 r1_** plus the five new cases in an exact-source compiled-once worker run, downloaded result artifact verified, followed by evidence S, cursor-only H and its own Governance. Historical branch-local R0 native ABI root script remains M0-owned and may fail despite the Rust binary reporting successful unit tests. No all-CI PASS claim.

## Source-exact Actions and retained limitations

SOURCE `39e6dfc0e3d7dfec12af0c28849b36d8f82b23ed`; worker-native Actions [38688812162](https://github.com/lly8666/wbd-next/actions/runs/38688812162) build job116269734244 consume116269826323 **SUCCESS**, compiled-once native test binary, **80/80 r1_** (75 preceding plus 5 new loan/Stop cases), 3 unrelated R0 ABI tests filtered. Downloaded result artifact11951250903, inspected exact `result.json` and `test.log` and SHA256:
- ZIP `f99ee64357e8db5b63412818e02da161807661ca1b023584595905e0964de6a1`
- result.json `8d1b09babdd252928f99f8d2a497958a295bc58643cc9b3a3e3426156aca37cb`
- test.log `99aa8a1b73212d4be8aa08111d2d0c3ae420520b6413b6c612ea7a71fe3293d3`
- debug binary `561dfe6a03999280f7a64181a56a790a699ba8a71b695dde3f283e33604ba928`.

Inherited Release benchmark additionally compiled exactly one source-locked Release native test executable in the consumer, digest `5ff2a77c6854bb14792a4ff786a61b8c883869932c00fae68a9d6a0a812cde6f`, three 1.10-second TX/RX scoped batch measurements passed. This is a *regression observation*, not a product or isolated CPU benchmark; no runner-to-runner performance improvement claim.

Same SOURCE Governance38688812067, G2 bootstrap38688812155, R0 qualification audit38688812043, R0 cross ABI38688812032 **SUCCESS**. Old branch-shared [R0 native ABI38688812106](https://github.com/lly8666/wbd-next/actions/runs/38688812106) **FAIL**, despite Rust test binary rc0 with 82 passed, 1 ignored (Release-only test); inherited M0-owned `tools/r0_abi_bundle.py` still expects literal `"3 passed"` in unfiltered output. This shared root CI issue remains open and prevents any all-CI PASS statement. The five added owner-local tests do not exercise a real driver borrow; their external held lease is a FrozenRecord Arc clone with real Arena-generation return accounting. Trusted Go admission/Go V4, AF_PACKET, Windows/ARM, physical, product throughput/500Mbps and end-to-end p99 **NOT_RUN**. Evidence S and cursor-only H Governance must separately pass before integration.
