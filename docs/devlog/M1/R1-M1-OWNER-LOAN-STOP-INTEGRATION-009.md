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
