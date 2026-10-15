# R1-M1-BOUNDED-EARLY-RX-BOUNDARY-010 · owner-local staged early RX

## Authority and prior checkpoint

M0 main registry rev2 epoch1 active M1 `work/m1-r1-runtime`, owner paths unchanged. Task from `docs/decisions/M0-V4-bridge-next-wave-2026-10-15.md`. Previous task009 cursor seq11 checkpoint `da48b585a7bbce48f5de7fbbc8b4c27bfff82c12`, cursor-only H `5399ca365a07e44843f5156716331b8415542c2a`, Governance38689191231 SUCCESS and no other worker delta. Prior compiled-once native 80/80 `r1_` PASS. No root workflow/shared C ABI/M0 Go auth/other worker modifications.

## Owner-local API and explicit non-authenticated Prepare boundary

`runtime::early_rx::EarlyRxOwner` wraps an existing generation-scoped `ScopedOwner` and a bounded `VecDeque<Staged>` preallocated on the control path (slots 1..=32, explicit byte cap). It takes a **caller-supplied exact absolute RX boundary** via `prepare(token, boundary)`, not raw bytes, Go cold string, session authentication or record PN. Only the authenticated M0 composition path may later determine whether this external caller fact is trusted. Current public Rust owner API is an R1 scaffold; production readiness flags remain FALSE.

An ingress specifies `UniqueBuffer`, checked wire `Range<usize>`, absolute segment start `u64`, token and fake `MonoNs`. Exact interval is `[start, start + wire.len())`; checked addition rejects overflow. End <= boundary is `BeforeBoundary`: caller retains buffer, never staged. Start < boundary < end is `Overlap`: **reject entire segment**, never split or silently admit suffix. Start >= boundary is eligible: staged until externally signaled `detach(token)`, then flushed into the generation-scoped `RxOwner` for `drain_rx`/LoanBatch; post-Detach eligible new ingress goes directly to current RxOwner. No early packet is dispatchable until complete Detach; `prepare` cannot silently change a pinned boundary. Return of rejected/overlapping input preserves original `UniqueBuffer` ownership.

At constructor, stage cap is required to fit the **already preallocated** underlying RX capacity; Detach preflights slots/bytes before flushing, so partial Detach cannot expose ready packets or strand a staged tail behind an inner full queue. Owner-exclusive single-threaded control path, no hot-path allocator/copy. `stop(token)` drops only undetached staged packets and unloaned scoped queue items, preserving idempotent canceled count; old ready LoanBatch and external frozen/unique driver-held handles survive Stop until their actual last owner release. `rotate` cancels old staged packets **only after valid generation rotation**, resets exact boundary so caller must Prepare anew, and never forwards old owned bytes into new scope; new ready RX is independent of retired held loans. Stop on a stale or ABA token cannot affect a restarted owner.

This is **not** a real TCP/UDP/AF_PACKET segment decoder, M0 Prepare/Detach implementation, ABI admission, Go V4 authenticated provenance, OS driver syscall, cryptographic source or product ready assertion. RX lane remains preauth scheduling hint.

## Native counterexamples (additive to prior 80)

Eight new `r1_early_rx_*` tests exercise: missing/conflicting Prepare boundary, wholly before (including exact end), exact start, crossing overlap and offset/window overflow; zero early and one after Detach; 32-slot cap with 33rd returned unfreed; staging byte cap and failed over-reservation; Stop before Detach twice with last external frozen clone returning late; 32 old RX borrowed while new lane immediately serves first post-Detach packet; Stop after Detach with borrowed loan/ABA reused IDs; rotation discarding old undetached 4-item tail with new boundary independent. Arena full loan report and retired batch fence remain distinct.

No Go auth, real driver or end-to-end product tests are claimed. Require exact SOURCE compiled-once native Actions PASS with previous80/80 retained, independently inspected artifact and SHA256, role evidence S then cursor-only H Governance PASS before claiming completion. M0 owns root R0 native ABI historical unfiltered `"3 passed"` harness issue; M1 will record failure rather than changing shared tooling.
