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

## Observed SOURCE code-native and governance 2026-10-15

- Code SOURCE [25642589](https://github.com/lly8666/wbd-next/commit/25642589f0feb12b44304fd21842c507a9314d35) native [38678654629](https://github.com/lly8666/wbd-next/actions/runs/38678654629) attempt1 **SUCCESS** 44/44 `r2_` unit tests (previous38 + new6), source-exact compiled-once binary. Build job116237929742 / consume116238017948. Binary SHA256 `756ca9054680bce83b1d4b215fb4c6866aab7b58762296392e9b14ee486a1eaa`, log SHA256 `c7d8438c8c66778786de8fc4f47ced8a1c3716fbf2218e48dbccddda712bcebd`. Build artifact11947306930 digest sha256:a1928ea859267454e15b9c7fd0519a44cf5719f7ab6a13d35ae0876fca1da20e, result11947096537 digest sha256:647f21f3049ba03c14892eaf0f977271bd98f88acdc2a0b982d5112ba7e33ef4.
- Same code source historic G2 [38678654565](https://github.com/lly8666/wbd-next/actions/runs/38678654565) **SUCCESS** build116237929829 consume116238094798, result11947066657 digest sha256:71759194bcde86f95f9d58927f8808941199fe416bde8b9042b5e12c8a944539.
- Same source R0 static [38678654572](https://github.com/lly8666/wbd-next/actions/runs/38678654572) **SUCCESS** job116237929797, artifact11947696516 sha256:161ad3595a066719d4b13763907bc4794aca58496de42964cb471833c02a07e1.
- Same source Governance [38678654568](https://github.com/lly8666/wbd-next/actions/runs/38678654568) attempt1 **FAIL** job116237929734: `ROLE_SCOPE_FAILED: incomplete or diverged bounded G2 activation ancestry`, artifact11947701588 digest sha256:cd7a3e775a773fc0bfb584be3ab2f3148539cf75c2c690c9bc04df41261d0f71. Investigation of immutable branch verifier `tools/worker_scope_ci.py` finds hard `total_commits<=64` from G2_BASE `83bd720368b9be68b3c4c94d7462d20cf4d796db`; GitHub compare previous cursor H `eb2b0ffa` exactly64, current SOURCE `25642589` **65**. This is deterministic structural gate exhaustion, not concurrent main movement and NOT a Rust test failure. No M2 authority to change root CI, reset baseline or rewrite non-force branch history. Therefore this worker atom is **BLOCKED in governance**, not completed / qualified ready for integration. Fresh evidence and cursor Governance will likely fail the same cap until M0 intervenes. Preserve all historical results.

### Actual measured P0 component results (synthetic, 1 native job)

`R2_OWNER_COMPONENT_P0` in the native log emitted per arm, same exact SOURCE, same runner and binary: 3 sequential comparison pairs AB/BA/AB, each arm 128 cycles ×32 slots = 4096 accepted synthetic reservations. Units: elapsed wall ns per entire 128-cycle scenario, CPU ticks process-wide, procfs VmRSS/VmData **growth** KiB (not actual heap allocation counters). All 6 arms reported `dynamic_allocation_count=NOT_INSTRUMENTED`, `bounded_pending_slots=32`, `bounded_pending_bytes=44800`, `actual_wire_bytes=0`, `driver_calls=0`, `authenticated_go_v4=NOT_RUN`.

| Pair | Order | Arm | Wall ns | Process CPU ticks | VmRSS +KiB | VmData +KiB |
|---|---|---|---:|---:|---:|---:|
| 1 | AB | legacy | 54110699 | 5 | 48 | 0 |
| 1 | AB | scoped | 58344291 | 6 | 8 | 0 |
| 2 | BA | scoped | 69644079 | 7 | 4 | 0 |
| 2 | BA | legacy | 53341996 | 6 | 4 | 0 |
| 3 | AB | legacy | 52213861 | 5 | 0 | 0 |
| 3 | AB | scoped | 55401550 | 5 | 0 | 0 |

Host tick granularity and shared process memory, plus sub-second leg durations, prevent rigorous CPU-s / heap allocation or product-performance claims. `Instant` wraps construction of fake frozen repair candidates, owner budgets and completion; no pure callback isolation. No crypto/network/p99/500Mbps product verdict.

## M0-controlled governance unblock request
See `.governance/workstreams/M2/requests/M2-G2-ANCESTRY-BOUND-006.md`. Request: M0 design a fresh bounded and auditable worker role-scope ancestry approach for >64 accumulated M2 commits (including safe workflow propagation to the worker branch), or formally reassign a new worker branch/epoch. Do not force rewrite, silently increase unbounded limits, or exempt path auditing. Until corrected, M2 records `progress=blocked`; exact source 44/44 test result is valid but Governance is FAIL.

## Recovery update · M0 exact one-time checker exception

At live main control `088b8860051bbf2de2c3c7e5afd03198620e182f` and subsequent main ancestry, M0 amended its own trusted `tools/worker_scope_ci.py` with `G2_ACTIVATION_MAX_COMMITS=96` and an **exact M2-only one-time exception**: parent `018a07c880473a896d40c0d97a59250212f7dad8`, sole changed path `tools/worker_scope_ci.py`, blob byte-identical to live main Git blob `26983e630ab2fbf28466dac457923904aaa6be60`, control anchor `af8a8b40853845b6e876224d579bfb567df48e6c` on main. M2 independently verified current ref, role revision2/epoch1, anchor ancestor status, exact parent and hash. M2 made the one-time single-parent Git commit `bde572873c27b1c535e77ee53507fb979bc5f326`; compare to previous H only the authorized checker path. This is not general authorization to change root scripts.

The native compiled-once `44/44` code result remains SOURCE `25642589f0feb12b44304fd21842c507a9314d35`. Checker refresh doesn't modify code or data paths and does **not** qualify a new native binary.

Refresh SOURCE Governance [38683108958](https://github.com/lly8666/wbd-next/actions/runs/38683108958) attempt1 **FAIL**, job116251837128, evidence artifact11949395232 sha256:aea02e32da2a7b68fc761c882fa054a2b9a52e82a35d791f5f90139f2296f2a6. Exact error: `ROLE_SCOPE_FAILED: control or source moved mid-audit`; no longer the old `<=64` gate. Concurrent M0 main moved while bounded per-commit checker was running. Historic failure preserved. Additional evidence-S Governance is required; no source-native or product claims made from a moving-main audit.

M2 original request for the bounded G2 checker has an **M0-authored remedy implemented**; formal Governance verification is still outstanding due to a distinct control-movement race. M0 needs to coordinate a stable main audit interval if repeated runs fail this dynamic check, not waive identity/path validation.
