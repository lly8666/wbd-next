# PLAN027A: independent MTU review and scheduled implementation plan

User supplied another agent's H915/1d220ec1 MTU audit and requests an independent revision between PLAN027 and PLAN028, plus a reusable M0 prompt. Read current main through H916/9947ac4a and the actual codec/budget/Linux/Windows/native paths. This commit is plans/governance routing only: no product code, runtime default change, dispatch or current cursor alteration.

Confirmed record31, FEC2 source10/repair12+symbol length2, Game16 and typed GameFEC+1. Current generic FrameBudget/tests still expect1399 at1500 but actual GameFecTx and Go reserve1398. This is a model discrepancy, not proof current wire is oversized. Additional review corrected MSS with actual IP/TCP options (especially smaller peer MSS), separate TX/RX and known local ceiling vs measured PMTU, complete record vs body, snapshot vs OS applied, actual implementation buffer caps, and historical 1400/1280/V1 budgets. Public <=1500 target avoids pretending existing 9000 parsing proves jumbo runtime support.

Added docs/architecture/MTU_CONTRACT.md as the single normative target, PLAN027A execution plan and M0-PLAN027A prompt. Prefer one pure Rust budget used by Go cold ABI and Rust owner; no per-packet FFI/global lock. Oversize behavior: ordinary TCP OS segmentation, legal DF0 IPv4 fragments with a shared bounded exception path only where needed, DF1 correct MTU feedback, retain actual Normal LINK compatibility without silently enabling all modes. Correct packet-local error vs fatal owner handling; padding has no advance reservation. Existing generation/immutable repair/FEC lifecycle retained. Standards linked to official RFC6691/1191/1812/8200.

Finite codec/negotiation/native seven-mode boundary matrix, ARM64 representative execution, supported LINK jumbo cases, two capacity-aware weak-network waves and same-VM protection A/B. No full repeated 027 speed matrix or high-loss jumbo zero-loss/1s SLA. Source-specific prior passes/failures remain intact.

Startup/architecture/legacy sequence and registry goal point to 027 -> 027A -> 028 without changing active assigned_task or cursor; downstream GUI/padding reuse the contract. Existing path-mtu-budget card gets PLANNED follow-up only. Validation is documentation/catalog/governance; implementation, product Actions and physical qualification for PLAN027A remain NOT_RUN.

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Schedule PLAN027A unified MTU and IP oversize behavior; add sole normative target and cold-ABI plan without promoting existing runtime or test qualification."}
```
