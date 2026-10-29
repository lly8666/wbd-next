# M0 PLAN026 H374 — current-source native Health M2 compiler first error corrected

SOURCE `6d6a17353b7b2b3d6b02b44452e664c6b0a2f58a` corrected first sourceACA build blocker by keeping the original immutable Cargo.lock and original wbd-engine one-way R1 graph; it reused the existing wbd-codec aws-lc crypto RNG via a one-call low-frequency control helper. Linux Health-core, source locked graph/ABI audit, basic R0 build and governance PASS; no new native driver product PASS was asserted.

The exact Windows ABI [run40909603172](https://github.com/lly8666/wbd-next/actions/runs/40909603172) revealed first **actual Rust compiler** error after deps restored: `v4_windows_owner.rs` M2 error branch `m.health.on_health_send_result(now.0,false)` missed a semicolon before the following `if err==FULL`. Commit `3967e61f487617b7307254cb3a5f042bc1688122` adds the semicolon and preserves all original Health timer, driver copy and M2 scope semantics; no weakening control codec, MTU or driver status. This was a source6d6 COMPILE FAIL, not a first kernel packet failure. User requested fix-first, test-affected then carry on; original SOURCE009d seven signed mode PASS remains separate.

Target: same-source Game2 only true Windows/WSL2 Action40910104098 and Windows ABI Action40910103907; initial M0 source396 at this note authored **in progress** and not claimed passed. New Game2/4 off transactional Wintun commit, single-lane RX isolation and shared Health/quality/jitter/padding source came in prior sourceACA; their new source functional results remain unknown.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Source396 exact Windows Rust M2 original Health error handling semicolon only; compiler first-error correction, no control or delivery semantic change, no unverified native PASS."}
```
