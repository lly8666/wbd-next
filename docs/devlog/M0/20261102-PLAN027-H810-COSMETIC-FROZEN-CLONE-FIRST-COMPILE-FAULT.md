# H810 — exact H809 FrozenRecordHandle:Clone type contract first fault, no behavior change

User reprioritized to lowest-CPU Game FEC **cosmetic outer TCP replay**, not functional retransmission or throughput optimization. H809 new candidate `6e74752d7676e369ef7023b7334494a4e4b2d2b5` adds shared sparse 1/256 copied original ciphertext + same PN/SEQ, 120ms due, max4/s/lane, Windows original signed NPF and Linux original raw, no AEAD/PN/FEC first credit/Health/ACK feedback. Game/off and all Normal/Fixed/Auto unchanged. User explicitly deferred other performance work.

H809 [Governance41330472518](https://github.com/lly8666/wbd-next/actions/runs/41330472518) SUCCESS and Maintenance41330472389 SUCCESS. Main original Linux Rust source-locked Action41330472536 Rust job124919409849 and original combined Action41330472585 job124919301802 **FAILED before native product**. Exact Rust error E0277 at `crates/wbd-engine/src/v4_game_cosmetic_outer.rs:35`: `CosmeticFrozen` implemented `FrozenRecordHandle` but missed its `Clone + Send + Sync + 'static` trait superbound. `Arc<[u8]>`, `FrozenMetadata` and `BufferOrigin` themselves support `Clone`; add precisely `#[derive(Clone)]` to `CosmeticFrozen`. No change to on-wire bytes, original copy selection, timer, driver receipt, FEC codec or owned Stop. The original H809 SOURCE remains **compile FAIL**, no fake native first/reverse PASS.

New H810 source reuses existing source-scoped Game2FEC6 1Mbps/25ms/0%10s actual test marker in the canonical native Windows/WSL2 Action. Must receive Linux and Windows Rust unit PASS then genuine driver first UDP/TCP and Stop/WAL. Do not dispatch other performance scenarios or satellite helpers.

```feature-impact
{"kind":"none","ids":[],"reason":"Single missing Clone trait bound on H809 newly introduced Arc-backed immutable Game FEC appearance record, no protocol/behavior/card change."}
```
