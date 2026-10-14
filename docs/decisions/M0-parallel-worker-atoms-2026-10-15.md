# M0 · parallel role assignments after M2 integration · 2026-10-15

## Authority and execution boundary
Main preflight HEAD `a911e945673f73c09d79655eb85629f0375a3c88`, M0 cursor sequence43 checkpoint `ba5749bb7e9efede91f81da43796985212af570f`; Governance [38635139983](https://github.com/lly8666/wbd-next/actions/runs/38635139983) SUCCESS. Registry reservation_revision **2**, assignment_epoch **1**, all four workers active and ownership prefixes unchanged. The previous four task atoms have scoped code/evidence/cursor H and no pending Actions. Every role must refresh its own branch and cursor before starting. These are **permissions to work**, NOT evidence that worker sessions already started, new code was pushed or tests passed. Never copy this main-only decision document into a worker branch cursor `context_refs` unless that file exists there (M2 prior H structure failure).

## Observed worker HEADs and previous qualifications

| Role | Head at assignment | cursor sequence | Previous main-native state | Prior own H Governance |
|---|---|---|---|---|
| M1 | `dceb2a7c12b76483c0d4d83ed71cb1ea2d5e348b` | 4 | M0 parity main already integrated, old worker CODE `20809638` | 38599017708 SUCCESS |
| M2 | `2ebd475956d65ab1ae05a46cff223c9970755e34` | 7 | M0 global sparse main integrated, original worker H recovered, old worker CODE `fb916f24` | 38602789109 SUCCESS |
| M3 | `faa018944f0981aa8835c2766cf33c021faa4fa1` | 12 | M0 post-auth BlockID main already integrated, old worker CODE `dcee7e85` | 38599242646 SUCCESS |
| M4 | `47eb4107a53facc5de6b0c2ea48fb90a19eea68a` | 6 | M4 Linux sendmmsg code still separate on worker branch, old worker CODE `6e72152f` | 38598800683 SUCCESS |

## New independent atoms (one per worker)

### M1 — R1-M1-READY-BATCH-004
**Goal:** Add an owner-local bounded ready-only <=32 batch drain to existing TxOwner, preserving Fresh first on first dispatch and alternating fair repair/parity progress; reuse caller-provided preallocated output storage, no per-batch ciphertext clone, and maintain absolute MonoNs deadlines/stop/return ownership. Must not implement syscalls or modify root dependency/driver.
**Done when:** Exact own SOURCE compiled-once native r1_ tests: empty/1/32/33 packet batch capacity, full independent repair/parity vs fresh, first systematic ahead of due/undue parity, bounded secondary progress under persistent fresh, stop and last frozen loan/return. Keep all preceding M1 tests and own evidence S/H/Governance; no production SPSC/loom/eventfd claim.
**Allowed code:** `crates/wbd-engine/src/runtime/`, `crates/wbd-engine/src/memory/`, `crates/wbd-engine/tests/`; and only the role's existing docs/devlog, docs/evidence, cursor and requests prefixes.
**Anchors:** 02-RUNTIME,03-MEMORY; R01/R02/M01; M4 kernel batch READ_ONLY.
**Critical limiter:** Do not allocate per batch in hot path; M0 owns platform/CI/ABI. Existing M1 request for rtrb/loom/eventfd remains OPEN, do not treat it as pinned.

### M2 — R2-M2-GLOBAL-BATCH-COMPLETION-003
**Goal:** Extend pure wbd-recovery global allocator for bounded batch completion bookkeeping over independently reserved repair candidates from multiple TunnelKey/directions. Accept a platform-agnostic validated result representation (accepted prefix, at most one uncertain slot, suffix definitely NotAttempted only with evidence), never depend on platform crate. Preserve original-epoch NotSent refunds, Uncertain debit, duplicate/old callbacks fail closed and process hard quota; do not touch M0 engine sender.
**Done when:** Exact own SOURCE compiled-once native r2_ fake-MonoNs tests for 0/1/32/33 mapping, accepted prefix vs ambiguous index and not-attempted suffix, two tunnels/both directions, epoch cutover, double completion, expired/departed grants and fresh not HOL. Preserve 22 previous r2_ tests; S/evidence/H and Governance. No raw sendmmsg product/driver or root Cargo changes.
**Allowed code:** `crates/wbd-recovery/`; and only the role's existing docs/devlog, docs/evidence, cursor and requests prefixes.
**Anchors:** 08-RECOVERY,00-CONTRACTS,04-CARRIER-IO READ_ONLY; A05/I01.
**Critical limiter:** No mutex or per-packet global lock, no arbitrary uncertain suffix refunded as definitely NotSent, never synthesize peer ACK.

### M3 — R1-M3-FEC-RETIRE-PRESSURE-010
**Goal:** Strengthen bounded FecRxOwner and FecBlockIdOwner heavy→compact→retired under capacity and timer pressure, including authenticated-input multi-block out-of-order systematic/final parity, no duplicate business resurrection and valid first-source delivery. Only codec own files; do not invent a trusted Go V4 exporter or modify authenticated input provenance.
**Done when:** Exact SOURCE compiled-once native r1_ deterministic fake-MonoNs tests: 3s heavy/10s compact, late callbacks, small heavy/compact byte caps, BlockID wrap across trusted explicit generation, wrong epoch/direction/half-space, old parity and malformed final conflict, 20:R parity profile and known Go 56B oracle; rejected/late never reopen retired data. Retain earlier 67 r1_ tests and own S/evidence/H/Governance. New implementation only if failing counterexample proves necessary.
**Allowed code:** `crates/wbd-codec/`; and only the role's existing docs/devlog, docs/evidence, cursor and requests prefixes.
**Anchors:** 07-FEC,00-CONTRACTS,05-RECORD-CRYPTO read-only; F01–F06/C03.
**Critical limiter:** Only authenticated-input pure ownership, no live V4 generation source, no ISA-L SIMD/runtime performance claims.

### M4 — R1-M4-IPV4-TCP-RX-PARSE-004
**Goal:** Add strict, bounded IPv4/TCP one-full-DATA-packet byte parser for incoming carrier packets with trusted tuple/MTU/length/flags/options and independent IP/TCP pseudoheader checksum validation. Provide caller-anchored seq32→u64 nearest extension with fail-closed half-space ambiguity; do not implement arbitrary TCP stream reassembly or real AF_PACKET live reader.
**Done when:** Exact own SOURCE compiled-once platform r1_ tests on byte-exact existing IPv4/TCP writer outputs, checksums independently, version/IHL/options/total length/data offset truncation, fragments, malformed flags, wrong tuple/source or checksum, MTU±1 and seq32 wrap/half-space ambiguity, back-to-back unrelated packet not HOL; no pre-auth payload ever treated as verified business. Own S/evidence/H/Governance. Kernel raw RX/Windows/physical NOT_RUN.
**Allowed code:** `crates/wbd-platform/`; and only the role's existing docs/devlog, docs/evidence, cursor and requests prefixes.
**Anchors:** 04-CARRIER-IO,00-CONTRACTS; I02/I04, L01.
**Critical limiter:** Parser only: no socket opening, no Go V4 production activation, no implicit receive stream coalescing or packet fabrication.

## Coordination, test and nonclaims
1. No revision/epoch bump; neither M0 nor another worker writes the four worker implementation branches. Workers independently push code S → GitHub native Actions/artifact hashes → evidence S → cursor-only H with Governance, and preserve failed runs by exact SHA.
2. M1 batch scheduler, M2 pure reservation completion, M3 FEC retired-identity proofs, M4 carrier RX parser own different semantics; do not merge or use a new helper from another worker until M0 independently qualifies it on main.
3. M0 owns shared root Cargo/lock ABI, existing R0 exact-filter repairs, CI and cross-crate tests; M1 rtrb/loom/eventfd request remains unpinned; M4 batch Linux code remains independent until M0 imports.
4. Next M0 independent atom, after this assignment is committed and verified: select M4 already scoped Linux sendmmsg batch kernel fixture for main integration with bounded M1 ready frames, or another more urgent authenticated V4 session prerequisite after verifying remote evidence. Do not claim AF_PACKET live raw from UDP socket fixture.
5. Product Go V4 generation binding, real AF_PACKET, native Windows/ARM execution, 500Mbps/p99/CPU and physical remain NOT_RUN. Design/worker/governance success is not product PASS.
