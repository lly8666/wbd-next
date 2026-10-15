# M1 R1-M1-READY-BATCH-004 · bounded ready-only dispatch batches

Authority: M0 `main` registry revision2 epoch1 M1 active unchanged branch `work/m1-r1-runtime`; exact assignment in `docs/decisions/M0-parallel-worker-atoms-2026-10-15.md` (main only). Previous M1 HEAD `dceb2a7c12b76483c0d4d83ed71cb1ea2d5e348b`, cursor seq4 checkpoint `206d60192f21116220fb5709d9469c7f86623363`. Continuity checkpoint→HEAD is exactly one prior cursor-only H; Governance38599017708 attempt2 SUCCESS.

## Scope and mechanism

`runtime/batch.rs` adds `READY_BATCH_MAX=32` and `TxOwner::drain_ready_batch(now, &mut Vec<TxDispatch>) -> usize`. Caller must preallocate output; the owner appends at most min(32, `capacity-len`) and **never** grows/replaces caller storage. Existing output entries are untouched. Each `FrozenRecord` is **moved** into the batch, not cloned, re-sealed or copied; borrowed kernel lifetime remains the caller's responsibility. Empty queues, no spare storage, or future parity return immediately with zero; no batch-size wait, clock read, syscall, wake thread or per-batch heap allocation.

The batch reuses the already proven owner `next_ready(now)` for priority, deadlines, age, quotas, and strict fairness. Thus first systematic fresh wins against both due and not-yet-due parity; repair and parity occupy their own capacity independent of fresh; under persistent fresh, a secondary class gets a turn after at most ten consecutive fresh, and both repair/parity alternate progress. The consecutive-fresh / secondary state is preserved across 32-element batch boundaries. Normal/off `TxOwner::new` still creates no parity queue.

Stop cancels only unsubmitted/queued frozen records; already moved batches hold their original frozen leases until the platform/drop releases them. A full arena return channel uses the earlier bounded fallback and cannot incorrectly mark arena quiesced while the last clone remains. `MonoNs` deadlines are checked per dispatch without sleeping; actual platform blocking, M4 sendmmsg, M3 FEC encoding and root orchestration remain out of scope.

## Planned new deterministic native r1_ regressions

- Zero preallocated capacity and empty queue return zero/no allocation.
- One freshly ready record delivered immediately, same immutable payload pointer.
- Exactly 32 records in a capacity32 output; no reallocation.
- 33 records split 32+1 in capacity64 across two calls, no tail loss.
- Full independent repair/parity with fresh ready first, parity not early before 32ms.
- Already-due parity remains behind first fresh systematic.
- Repair/parity bounded service under sustained fresh, including crossing 32-cap boundaries.
- Prefilled output respects only spare slots and does not overwrite earlier handles.
- Stop after a dispatched batch retains the last frozen clone/loan; only final drop quiesces.
- Three classes and full return queue/backlog drain across stop.

The tests are unit tests under M1 owned runtime source and selected by existing `worker-native-tests.yml` real compiled-once `r1_` runner. Do not mark PASS until exact worker-source Actions and artifact verify. No new Cargo dependencies, shared harness, driver or ABI writes. rtrb/loom/eventfd/network/Windows/native-product/performance/physical remain NOT_RUN, Go V4 disabled, engine feature flags0.
