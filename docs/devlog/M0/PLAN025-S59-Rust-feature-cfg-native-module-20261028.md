# M0 S59 optional Rust Go build feature-gating repair, 2026-10-28

Frozen base main b6b964afa7ffec5795f2c11c6e0620f223e684ac imported S55 verified original Windows product. Exact main NORMAL-COMMON Actions40560287464/1 FAIL under m0_v4_probe,m0_v4_embedded_go with FEC2 off: Rust errors E0412 OriginalRepairBlockReason, E0433 v4_game_public_kernel cfg module, E0689 read_cap numeric ambiguity. Main PLAN012 Actions40560287380/1 separately FAIL during rustup component sync, no source compilation proven; preserve that different red.

Pre-fix review: docs/architecture/modules/10-LIFECYCLE-QUALITY.md and 08-RECOVERY.md, actual crates/wbd-engine/src/v4_embedded_go.rs FEC2 repair declarations/GameGroupNative/tx_turn; crates/wbd-engine/src/lib.rs gating on native Game kernel; .github/workflows/m0-normal-product-smoke.yml exact no-FEC cargo invocation. Recent related source changes S25 9758d0ff telemetry and S24 79d561eb Rust original M1 batch. S55 signed Windows native Auto/Stop PASS is independent; do not change its enabled feature bodies.

Repair gates the FEC2-only constants, classifier, struct and impl exactly like the prior enum; gates GameGroupNative on FEC2 feature; fixes untyped ordinary fallback to usize. No original wire, crypto, owner/epoch/M2, code path behavior or ABI changes. One new cheap Actions workflow checks exact SOURCE and Linux plain, FEC2-enabled and ordinary base cargo variants. Module test only, no native product/performance promotion. The old FAILs remain historical.

```feature-impact
{"kind":"none","ids":[],"reason":"Repair Rust optional compilation feature/cfg compatibility only, preserving verified FEC2-enabled product and all safety/default behavior; no feature promotion."}
```
