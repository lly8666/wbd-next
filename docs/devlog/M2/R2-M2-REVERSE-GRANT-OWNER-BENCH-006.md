# R2-M2-REVERSE-GRANT-OWNER-BENCH-006

## Formal authority and clean handoff

2026-10-15 main registry M2 active reservation_revision2 assignment_epoch1, task `R2-M2-REVERSE-GRANT-OWNER-BENCH-006`, owned write prefixes `crates/wbd-recovery/` and M2 role-only devlog/evidence/cursor. Decision is on main only: `docs/decisions/M0-parallel-worker-atoms-2026-10-15-wave4.md`; do not include absent decision in worker cursor. Prior M2 evidence checkpoint c4e69939903cbce3c204cf475750625a2d3bfe11 → H eb2b0ffa3720db1cffb2e1ae86f619ecc7275073 exactly cursor-only; seq10, Governance38675209267 SUCCESS. No open requests. M0 keeps GoV4, engine, driver, root/Cargo, platform and actual product integration.

## Scoped code

`GlobalRepairAllocator::reserve_scoped_if_still_missing` guards each candidate and requested grant against the previously owner-pinned `ReceiptRouteScope`: exact outbound lane/generation, TunnelKey, wire direction, DATA PN interval, then existing `ReceiptState::preflight`. A user or adapter cannot append arbitrary raw route bytes to a legacy grant and create a repair reservation: without an independent pinned session this function fails `WrongReceiptScope` before charging global cap. This is pure owner-local accounting, not proof of a cryptographic session: M0 must derive actual trusted reverse lane/direction/epoch/PN from successful AEAD+PN verification and cold-session authority.

No new ACK constructor, syscall, crypto, fresh queue, global mutex, or ciphertext cloning. Existing unscoped methods retained for old pure fixtures and must not be exposed to untrusted product inputs. Original-epoch NotSent refund, Uncertain conservative debit, expiry/retire failures, process max cap and <=32 id validation continue unchanged.

## Added exact R2 tests and component P0 measurement

Six new `r2_owner_*` native tests, retaining all previous **38**:
1. `r2_owner_zero_one_typed_scope_and_repeat_completion`: empty, one slot, cannot retrofit an active grant, duplicate callback remains stale.
2. `r2_owner_two_scopes_32_mixed_stale_and_33_no_false_refund`: 2 tunnels/opposite directions share a single 44,800B process cap, 32 reservations, proven NotSent suffix refunds only original grant; wrong 17th slot epoch fails whole batch atomically, 33 invalid, fresh not HOL.
3. `r2_owner_ack_before_grant_wrong_reverse_epoch_is_not_delivery`: wrong independently pinned reverse route cannot fake peer receipt; valid post-open *test-only* facts release shadow, then preflight fails and no charge.
4. `r2_owner_expired_grants_stale_epoch_unknown_suffix_keeps_debt`: 32 ids, old IO timeout, no late proof refund even if positive suffix asserted; expired grant, conservative debt and next epoch.
5. `r2_owner_epoch_cutover_uncertain_and_notsent_preserve_original_debt`: 2 differently epoch-pinned scopes and 1s rollover, uncertain remains charged in previous, proven NotSent refunds prior only, new epoch grant clean.
6. `r2_owner_component_p0_source_locked_repeated_ab_ba_cpu_rss`: **one SOURCE, one compiled-once native worker binary**, 3 AB/BA/AB pairs; each baseline `complete_batch` and scoped `complete_scoped_batch` leg builds the same 2-scope 32-reservation fixture for **128 iterations**, 4096 accepted slots per arm-leg. Measure wall nanos by `Instant`, process CPU jiffies from Linux procfs `/proc/self/stat`, VmRSS/VmData deltas from `/proc/self/status`, record bounded logical max slots32/bytes44800 and Vec preallocated exactly32. Logs use `R2_OWNER_COMPONENT_P0` prefix.

**Interpretation**: Wall time includes synthetic fixture construction, ReceiptState fake candidate, local and global budget reservation, and settlement; it does not isolate only callback CPU. Linux process CPU ticks are coarse process-wide ticks, not per-callback cycle counters; VmRSS/VmData only process memory footprint proxies and **not heap allocation counts**. The pure crate forbids unsafe global allocator instrumentation, so `dynamic_allocation_count=NOT_INSTRUMENTED` is explicit; neither zero allocations nor allocation-free hot path can be claimed. Test has no speed/CPU thresholds, no real AEAD, no packet TX/RX and zero driver calls. No 500Mbps/P99 product qualifications from these observations.

## SOURCE/CI/evidence

Only a real source-exact compiled-once GitHub worker-native Actions native binary may qualify `r2_` tests and cost logs. Preserve historical failed runs, do not rerun old source to claim PASS. Code S, evidence S and cursor-only H must each be immutable with separate Governance. All product/Go V4 authenticated exporter, real raw AF_PACKET, native Win/ARM, end-to-end 500Mbps, CPU/RSS product targets, physical remain **NOT_RUN**.
