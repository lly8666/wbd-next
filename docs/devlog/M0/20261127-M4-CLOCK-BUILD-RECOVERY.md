# M0 M4 clock build recovery — unverified

User authorized handoff of M0; original Draft PR80 and registered branch retained. Parent 75c47a5df4e58787b2bb9ee15228638932ae4be0. Both native ISAs failed build in run 45926991269 (E0308 at v4_embedded_go.rs:7225, seal returns u64, receipt expects RecordPn). ARM 45926991260 prepare failed waiting for exact native qualification; no performance legs ran. Main H2476 remains historical handoff, prior 9ede62e native scoped PASS and unqualified ABBA retained.

Convert the existing returned PN to RecordPn at the receipt boundary. Select the existing copied-prefix test explicitly with product features on both native ISAs; require one executed passing test. No new wire field, payload copy, crypto operation, queue or protocol change. This commit is a compile/test recovery, not evidence of throughput or full actual-send parity. Existing normal/FEC/LINK/retransmission scope limits unchanged.

Static audit against the registered 26b11e2 base: dual TCP RX callback is downstream of original unique AEAD open and authenticated source admission; normal TX still uses the original seal and ready batch. NativeM4Clock header/len/time remain local metadata. This is not a packet-capture result; packet sizes, counts and timings may change with inner TCP behavior. No claim of traffic indistinguishability or full historical wire equivalence.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Correct PN type at local M4 clock boundary and select existing native unit; previous build failure recorded, new SOURCE unverified."}
```
