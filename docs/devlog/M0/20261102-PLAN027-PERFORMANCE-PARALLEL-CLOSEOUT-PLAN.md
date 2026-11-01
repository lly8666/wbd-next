# PLAN027 performance closeout and parallel execution plan

User authorized a docs/governance update on 2026-11-02: compress completed work, detail large network testing and measured performance optimization, simplify M0's reusable prompt. Two explicit follow-ups: optimize Normal outer retransmission once and reuse in other modes; run repair-OFF network/FEC/Game tests and independent optimizations in parallel.

Read-only product review baseline: `6a343f4c6c32fbcc3ed1c36a997c0666f644e3f9`. H815's actual Game2/FEC6 Windows NPF retransmission/normal Stop scope is preserved; Normal rate acceptance is not reopened. No product code, workflow, scenario, feature implementation or qualification changed. No manual dispatch/cancellation, physical deployment or messages to other chats. Active M0 cursor is intentionally untouched; registry/plan explicitly supersede its prior temporary pause, and M0 recovers latest incremental progress itself.

Changed the existing PLAN027 rather than adding a second execution plan. Completed history is linked to the exact previous revision; current focus is R (Normal shared cosmetic repair cost), N (repair-OFF matrix/other hotspots), and limited integrated ON regression. CPU ownership includes Rust DLL inside the Go process; same-VM OFF/ON and new/old pairs are distinguished, no double-counting host/guest CPU. Theory covers actual-k FEC, Game loss correlation, packet size/PPS/BDP, TCP windows, sparse probes, sampling uncertainty and host capacity stops. Approximate rate targets are not narrow hard gates; first-arrival/no-HOL/integrity/immutable-once/owned Stop remain.

Static optimization candidates, not measured diagnoses: `outer_ack.rs` temporary vectors/ordered index and bulk retirement; `receipt.rs` multiple ordered indexes (timer already bounded to 32 events); `v4_windows_owner.rs` and `v4_windows_game_outer.rs` shared budget locks, optional ciphertext copy, 1536-entry Game retention and 80ms per-lane limiter. The latter caps repairs to12.5pps/lane and may explain a low high-PPS ratio. Do not separately optimize Game or claim a CPU saving from source inspection. Normal's optimized common path must be reused with mode-specific scope/IO adapters.

Updated AGENTS/START_HERE/M0 prompt/project/registry and added a current-policy banner to the historical WL harness guide. No permissions/epochs/worker tasks are reassigned. M0 prompt is a short reusable recovery/decision/execution contract, with live parameters only in the current plan.

Validation: local documentation diff/JSON/feature/governance structure checks only; product tests NOT_RUN for this docs-only change. Push-triggered Governance and maintenance own executable verification; no product PASS inferred. No cursor-only H is forged on behalf of active M0.

```feature-impact
{"kind":"none","ids":[],"reason":"User-authorized documentation and M0 task/prompt refinement only; no product feature, default, implementation or qualification changed."}
```
