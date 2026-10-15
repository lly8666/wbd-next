# M1 R1-M1-RX-READY-BATCH-005 — owner-local bounded RX batches

Control: main registry reservation revision 2, M1 assignment epoch 1, branch `work/m1-r1-runtime`, task `R1-M1-RX-READY-BATCH-005`. Prior M1 cursor seq5 checkpoint `ec3b264d16a56db9ff8157ba6654cdda5aa09cbc`; HEAD `4ca7d283c758390a4618a24d32b4e25e49dc17d1` contains exactly the prior cursor-only H, Governance #38667280279 SUCCESS. This is a separately assigned RX task, not an extension of TX004 or permission to edit M0 shared files.

## Owner-only design and preserved APIs

`RxOwner` retains its preexisting `offer(buffer,wire,MonoNs)` and `take_ready(MonoNs)` APIs. Untagged legacy ingress remains FIFO. New optional `offer_lane(buffer,wire,LaneKey,at)` carries a **pre-auth, untrusted scheduling hint** in a private queue entry, never in the public payload or auth claim. `RxPacket` stays unchanged (public `buffer` and validated `wire` slice); no new public cross-crate ABI or authentication. RX obtains its own bounded `VecDeque` through the existing `Bounded` type, with slot/byte/age admission and exact error returning the original unique buffer.

`runtime/rx_batch.rs` implements `drain_ready_batch` and `drain_ready_batch_where` with caller-provided Vec already possessing unused slots: at most min(32, capacity - len), never allocates/reserves/clones or copies payload. Also exports `take_ready_where` with a stable per-lane downstream-ready predicate; an obstructed lane's head cannot block an eligible other lane. From the oldest eligible arrival, select a different eligible lane than previous dispatch when available; otherwise serve oldest. Per-lane arrival ordering remains stable. The scheduler remembers previous lane across batch boundaries; fairness is a pure owner-local queue-index selection with fixed upper bound 8192, no global mutex or new per-lane allocations. Since fair extraction may remove middle records, expiry conservatively scans the fixed-capacity owner queue before selection, counting bytes/loans exactly, avoiding stale middle entries surviving behind active heads. This O(queue_slots) safe Rust scan is a bounded local model, **not a claim of production hotpath performance** or pinned rtrb SPSC.

RX stop releases only buffered undelivered loans; packets moved into the caller's batch remain uniquely owned by that batch and return when their final owner releases them. Prior arena return queue/backlog and stop quiescence remain intact.

## New scoped native r1_ cases

12 new tests verify empty/zero storage, one packet exact owned pointer, 32 and 33 capacity boundary, full caller storage, cross-lane FIFO/fair alternating, head obstructed with unrelated lane progress, byte/slot rejection and invalid range returning original owned slab, fake-MonoNs middle expiry and accounting, stop with outstanding delivered loan, return queue saturation/final thread release, and unscoped legacy FIFO. Historic M1 39 existing r1_ tests must remain passing.

## Explicit boundary

This task does not parse/decrypt/authenticate packets, validate lane identity, reorder network TCP streams, perform socket/AF_PACKET reads, cross-module driver integration, or claim business delivery. It does not alter `src/lib.rs`, shared `wbd-types`, Cargo/lock, workflows, or other roles. No high-rate performance, product, physical, Windows native, rtrb, loom, eventfd, or Go V4 proof. `OWNER_RUNTIME_READY=false`, `ARENA_READY=false`, Go V4 disabled, engine features0. The existing M1 request to M0 to synchronize branch-old R0 native ABI test selector remains open.

**Verification pending at initial code S**; only source-exact GitHub Actions native compile-once consumer plus inspected artifact may establish an R1 scoped PASS. S→evidence S→cursor-only H and final Governance are separate checkpoints.
