# M1 PACK-013 · R4-M1-GAME-SHARED-PIPELINE-WORKPACK-013

## Authority and scope

Main registry rev2 epoch1 M1 active assigns 013; decision `docs/decisions/M0-game-recovery-parallel-workpacks-2026-10-17.md` explicitly overrides old M1-012 cursor next_action. Prior M1 worker H `9d4f68aab2bb1f57bfb96dd8a472bc7eec43f556`, S `baadb74630b99359a5262e0d79b57484196a36d3`, H Governance39017421562 SUCCESS. Source restriction ONLY runtime/memory/tests and M1 docs/cursor/requests. **DO NOT EDIT** existing stable `directional.rs`, `directional_rtrb.rs`, `directional_compat.rs`, `wake.rs`, M0 engine/Go TLS, codec/recovery/platform, root Cargo/lock/workflows. Production flags off.

## Newly frozen owner-local APIs

New `runtime::game_shared` contains caller-prequalified `ActiveLaneSnapshot{GameScope,sorted QualifiedLane{LaneKey,mss}}`, `GameTx`, `GameRx`, `GameLimits`, `RxLimits`, and error/dispatch callback types. A caller-supplied NONZERO `epoch:[u8;16]` and `TunnelKey` are a Rust component scope key ONLY; **neither constructor authenticates a lane or reconstructs Go V4 credentials**. External M0 controls snapshot admission and injects M3 verified results.

TX accepts exactly ONE `UniqueBuffer` (original shared common/pre-seal source), a verified wire range, explicit Game/Normal mode, caller-declared conservative per-lane predicted seal wire bytes, and caller-supplied optional block ID. A bounded slot table owns each logical source ONCE, and per-lane queues contain only integer indices plus charge metadata. No pre-encryption clone, per-lane ciphertext clone, per-packet `Arc`, or new mutex. For Game, one monotonically increasing LogicalPacketId remains within same tunnel epoch through lane rotation; for Normal, no Game envelope/ID assigned, exactly one eligible lane selected and rotated. `drain_ready(now,<=32,closure)` borrows the original slice for immediate per-lane seal/dispatch; **M0/M3 must independently seal with lane-unique PN/seq/AEAD**, this component never creates ciphertext. Slow/over-budget lane copies are dropped/accounted independently, never HOL another lane. Queue slot, byte, age, shared owned source and active/draining lane count have explicit caps. Stop drops remaining pending queues and logical source, never claims externally handed-off driver loan released.

A rotation installs new externally qualified snapshot without mutating already queued old-MSS jobs or pushing them into a smaller-MSS lane. The old lane drains with bounded scope/age, and new eligible Normal/Game jobs can use new B immediately. Old logical epoch cannot install on new GameTx.

RX `offer_piece` collects bounded, full-ownership already-authenticated shards across lanes using a shared (scope,BlockIdExt,LogicalPacketId) owner slot, returns a fully owned `CompletedBlock` for M3 decode; this collector itself **does not decode/FEC or deliver an incomplete Game frame**. `first_delivery` accepts only M0/M3 already-authenticated and decoded/reassembled candidate `UniqueBuffer`, checks shared tunnel epoch, admitted lane and bounded sliding LogicalPacketId bitmap, and accepts first source OR recovered candidate only once regardless of source lane. Duplicate/too-old/stale/capacity errors return original handle. This is an owner-local proof, NOT evidence that raw packet headers/lanes were authenticated by this module.

## Functional counterexamples

New `r4_game_*` scoped tests cover four-lane same shared source pointer/one logical ID and no Normal frame clone; Normal round-robin during overlap; all 24 four-lane first-arrival permutations with exact once output; all 24 complementary shard orderings and completed bundle handoff; recovered-first/source-late dedup and stale window; slow lane independent pressure drops; 0/1/32/33 ready/stop quota, global slot+byte rejection retaining original UniqueBuffer; old large MSS A vs smaller new B; old epoch rejection; consistent stop reclaim and frozen parity first-send independent of repair. Prior 104 scoped R1 tests remain mandatory, including Wake retry, rtrb inner6 source checks, Stop and arena returns. No fresh reimplementation of stable queue/codec/AEAD.

## Gate and limitation policy

First CODE exact source must pass compiled-once worker-native Actions and downloaded artifact hashes. Make functional tests green BEFORE optional optimization. No 500Mbps, end-to-end latency, full original Go/Rust Game throughput or multi-lane authenticated crypto claim. If a verified hotspot is found and optimization authorized, benchmark at equal lane count, identical offered logical business bytes/FEC/config on SAME hosted runner/VM, sequential A→B with B→A reversal; otherwise **NO speedup or performance-ratio assertion**. Real Go auth/codec/systematic FEC/driver, Windows/ARM, physical, product all NOT_RUN. Evidence S then cursor-only H separate after exact-source success; H must pass Governance.

## Final exact-source Actions and owner-level qualification (2026-10-17)

CODE SOURCE `e2050aec593bd692974510fd9d64ae1ff7bb7c00` [worker-native 39045913408](https://github.com/lly8666/wbd-next/actions/runs/39045913408) attempt1 **117/117 `r1_` PASS**, original 104 retained, 13 new scoped Game tests. Build job117434475635 and consume job117434533622 both SUCCESS. The Game tests carry the `r1_game_r4_*` prefix because the existing M1 worker-native selector ONLY chooses `r1_`; first source `9d028b6009243d00c680c0b521d673cec3c1e2d8` had 104/104 existing r1_ PASS but its `r4_game_*` names were filtered (not 013 qualification). Source `31d1ee9ade49688f24c8a6ace42974352a3372b4` 115/115 PASS with first 11 newly named tests; final source adds 2 verified lifetime/slow-lane-full tests, yielding 117/117.

Independently downloaded result artifact 12105399239 and verified exact SOURCE, run, role, attempt, 117 unique names and 13 actually executed Game tests. ZIP SHA256 `faecf238d74dfdda77156ef9a7172fff2f7e9d7e2ee37883d4f31086a64b6bf5`, `result.json` SHA256 `c6eb60f59114826257e1a2613bc64cbe6af7b1e0524d9a0f4f8b3ef67fa09b4d`, `test.log` SHA256 `a2848682aae0c068e45e33f9a5467787ffa7c08c00867854e07b33b4e5baefe1`, compiled-once outer test executable SHA256 `d1c9ceb3787fa9d5f5f94c72b3a8df74b953a7a05bfef659711e9a3e4e42009b`. Existing rtrb M1-012 overlay six-case attestation also PASS on same source; **not Game rtrb throughput evidence**. Same SOURCE G2 bootstrap39045913344, R0 qualification audit39045913548, R0 cross ABI39045913382 SUCCESS. CODE Governance39045913340 **FAIL** because main changed mid attestation (`ROLE_SCOPE_FAILED control or source moved mid-audit`), not an observed M1 out-of-scope file edit. Final evidence S and cursor-only H must obtain independent H Governance SUCCESS. Historical worker R0 native ABI39045913350 FAIL on inherited M0-owned `"3 passed"` selector although real Rust unit binary rc0 **119 passed, 1 ignored**; do not claim all workflows green.

### Frozen M0 one-stage interface and ownership flow

Owner-scoped integration example (pseudocode, Rust types real, real M0/M3 calls left as integration work):

```rust
let snapshot = ActiveLaneSnapshot::new(authenticated_scope, m0_admitted_lanes)?;
let mut tx = GameTx::new(snapshot, game_limits)?;
let packet_id = tx.offer(original_unique_preseal_frame, logical_wire_range,
                         Mode::Game, m3_conservative_seal_wire_bytes,
                         Some(externally_assigned_block), now)?;
// Option<LogicalPacketId> is Some for Game, None for Normal.
tx.drain_ready(now, 32, |view| {
    // M3: reserve unique lane PN/seq and seal into its OWN output slab,
    // M4: attempt nonblocking driver dispatch with proper completion lease.
    // Treat any full/failed lane independently; never wait for lane #4.
    // Return DispatchOutcome::Accepted or DispatchOutcome::PressureDrop.
});
let mut rx = GameRx::new(rx_snapshot, rx_limits)?;
let pieces = rx.offer_piece(rx_scope, verified_lane, block_id, packet_id,
                             shard_index, needed, unique_opened_piece, wire)?;
 // If Complete, M3 decodes/reassembles the OWNED completed pieces;
 // no Game business is released directly from an incomplete block.
let first = rx.first_delivery(rx_scope, verified_lane, packet_id,
                              authenticated_decoded_unique_frame)?;
 // First accepted candidate goes to original business delivery;
 // second/old candidate returns original buffer as Duplicate/Stale.
```

`GameTx::offer` owns one original UniqueBuffer and charges its logical wire range once; per-lane ready queues hold only `usize` job indices, predicted wire charge and timestamp. Limits: <=8192 logical job slots, <=8 active+draining lanes, <=8192 ready slots **per lane**, caller set logical/predicted lane byte quotas and max age. The slab Arena's actual physical allocation/headroom and any external driver loans remain separate charges, not magically eliminated by logical wire accounting. Pressure on a single lane drops only that lane's copy with `lane_copy_drop`; callback does NOT keep a loan of the original preseal source after it returns (real per-lane seal must separately own its frozen output). `stop()` frees only undelivered owner-held jobs; already returned `CompletedBlock` owns actual RX UniqueBuffer pieces until downstream M3 drops them. No shared TX encryption output, no untrusted lane eligibility signal promoted to authenticated identity.

`GameRx::first_delivery` uses one per-logical-epoch bit window (max65536) and returns original `UniqueBuffer` on Duplicate/Stale/Scope. `offer_piece` keeps <=8192 bounded incomplete blocks of <=4 owned pieces each subject to caller set aggregate `open_bytes`. Distinct valid shard indices from different admitted lanes are complementary; four-lane arrival permutations all 24 and the decoded source/recovered duplicate race are covered. Full Game FEC and fragment decode are M3, not implemented/qualified here. Old large-MSS A jobs remain on original A during qualified B smaller-MSS addition; newly offered Normal business selects **one** eligible lane at rotation turn, never seals two Normal copies. Old logical epoch cannot be rotated into new epoch snapshot.

### Verification gates, performance, remaining ownership

No new hotspot confirmed after consolidated correctness pass; therefore **no speculative optimization and no Game performance A/B or speedup claim**. The inherited Release owner p99 probe does not measure Game 2/4-lane flow; mixing different hosted runner/actions, fanout, bytes or FEC profiles is forbidden. Any future Game optimization must hold lane count, logical payload bytes, FEC profile, candidate workload and configuration constant, run baseline/candidate A→B and B→A sequentially in the SAME hosted VM/Action, independently record CPU time/counters/p99, and preserve 117 functional cases.

M0 sole authority for real Go V4 authenticated tunnel/lane admission, embedding `WBG4` envelope and shared LINK/FEC encode **once** before M3 per-lane seal/PN/seq/AEAD and M4 driver lease. M1 test scope supplies explicit authenticated caller facts; it cannot claim real Go/driver provenance. Native OS wake, Loom, physical, Windows/ARM, end-to-end Game2/4 at logical 3Mbps+FEC20:20, product throughput/500Mbps all **NOT_RUN**. Production flags remain false. Rollback: leave `runtime::game_shared` unused and retain existing Normal-off TxOwner/RxOwner/ReadyTurn plus M1-012 directional SPSC unchanged. No root, M0, M2, M3 or M4 paths changed.
