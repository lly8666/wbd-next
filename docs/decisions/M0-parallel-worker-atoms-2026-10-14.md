# M0 parallel idle-worker atomic assignments · 2026-10-14

## Decision: assign before M0's next atom
All four workers have already completed their previous atom at their own role SOURCE; their existing main registry goals were stale. They can proceed in parallel **now** in their existing allowed prefixes, after each refreshes remote role identity, branch ancestry, own cursor and latest main. No M0 overwrite of worker branches, no new G2 ownership, no revision or epoch bump (active roles remain reservation_revision=2 assignment_epoch=1). A role task assigned on main does not mean its agent is presently running; each agent must execute and report itself.

M0 source at decision `1a8a184f60b9eb08439d619ec7a85f92172ae0e2` (seq37 checkpoint b4da7bc0) [Governance38585845817](https://github.com/lly8666/wbd-next/actions/runs/38585845817) SUCCESS, cursor-only since checkpoint. Worker exact preflight refs:

| Role | HEAD | Cursor status | Relevant independently proven result |
|---|---|---|---|
| M1 | `49d886d639b7ba93aca00cfc0e305b23017d0cc8` | seq3 ready_for_integration | wake-stop compiled-once native19/19 SOURCE81cbc57; M0 already imported and shared R0 ABI filter fixed on main |
| M2 | `be5e722e1e0b6f875571304b67852977d69f391a` | seq5 partial but own pure atom closed | receipt+1s repair budget native15/15 SOURCE4f485269; M0 already composed into actual repair path |
| M3 | `d81c4afef2a9d70a36ca2727f4640d3bc30171f1` | seq11 partial, prior checker mirror done | historical G2 fixed: own H [38589331920](https://github.com/lly8666/wbd-next/actions/runs/38589331920) SUCCESS; exact separate codec native55/55 SOURCEab7ef93, M0 FEC-on2/2 at SOURCE6096b44 |
| M4 | `ad5eea274cbc81e09caf757491a482a3ef1ab8fa` | seq5 ready_for_integration | actual IPv4/TCP bytes native12/12 SOURCE46a38c; M0 already packages and budgets actual bytes |

**Assignment as next atom; no worker implementation/new-source test result is claimed:**

### M1: R1-M1-FEC-PARITY-READY-003
- **Within role allowed paths:** `crates/wbd-engine/src/runtime/` and its role-specific docs/evidence/cursor/requests only; no main-root manifest/ABI/CI edits.
- **Goal:** R1-M1-FEC-PARITY-READY-003: integrate an owned, strictly bounded, independent parity-ready queue and absolute-deadline wake/stop into existing std TX owner; never HOL-block fresh systematic or ordinary fresh; no FEC encoding, root deps or driver edit.
- **Done when:** Exact worker native compiled-once Rust r1_ tests cover first fresh before 32ms parity, parity-only wake at an absolute fake MonoNs deadline, repair/parity/fresh queue full+stop+return races, bounded parity service/fairness and no wrong early wake. Keep existing M1 tests passing, own S/evidence/H and Governance; real rtrb/loom/eventfd remains separate M0 dependency pin.
- **Anchor and counterexamples:** 02-RUNTIME 03-MEMORY; R01/R02/M01; 07-FEC is READ_ONLY
- **Important limiter:** fresh-source priority, parity-ready only after FecTxOwner separately returns eligible work; cap slots/bytes/age and no system sleep per packet

### M2: R2-M2-GLOBAL-SPARSE-002
- **Within role allowed paths:** `crates/wbd-recovery/` and its role-specific docs/evidence/cursor/requests only; no main-root manifest/ABI/CI edits.
- **Goal:** R2-M2-GLOBAL-SPARSE-002: implement purely in wbd-recovery a bounded process-wide multi-client/direction repair byte allocator with per-tunnel grants and aggregate hard ceilings, preserving existing per-direction 1s max(F/10,32768) semantics and sparse traffic never blocked merely by zero F.
- **Done when:** Own fake MonoNs r2_ native proofs over >=2 TunnelKeys, both directions, >=2 epochs, global limits, grant/expiry, double-completion, NotSent old-epoch refund, Uncertain conservative debit, client departure and no fresh HOL; source S/evidence/H and own Governance. No socket, Cargo/root or per-packet global mutex; M0 later composes actual submit path.
- **Anchor and counterexamples:** 08-RECOVERY 03-MEMORY; R02 plus global sparse capacity
- **Important limiter:** global hard cap separate from client 32KiB sparse floor; no global per-client free quota multiplication

### M3: R1-M3-FEC-BLOCKID-SCOPE-009
- **Within role allowed paths:** `crates/wbd-codec/` and its role-specific docs/evidence/cursor/requests only; no main-root manifest/ABI/CI edits.
- **Goal:** R1-M3-FEC-BLOCKID-SCOPE-009: add a strictly bounded authenticated-input 32-bit FEC wire BlockID to 64-bit extended-ID reconstruction/retirement helper, preserving trusted epoch+direction identity and fail-closed half-space ambiguity, without changing AEAD/PN uniqueness or inventing a Go session exporter.
- **Done when:** Old-Go 56B metadata oracle and Rust native r1_ tests for ID 0/reserved, 0xffffffff→1 wrap, zero-length jumps, >halfspace ambiguity, 3s/10s expiration, retired floors, adversarial old delayed parity and wrong generation/direction; prove rejected or duplicate input cannot resurrect FEC delivered state. Own S/evidence/H; no root/G2 checker changes; full live V4 binding NOT_RUN.
- **Anchor and counterexamples:** 07-FEC 00-CONTRACTS; existing FecRxOwner Scope id_ext supplied by trusted caller
- **Important limiter:** helper only called AFTER AEAD/PN replay, no trust in unauthenticated wire alone

### M4: R1-M4-LINUX-BATCH-TX-003
- **Within role allowed paths:** `crates/wbd-platform/` and its role-specific docs/evidence/cursor/requests only; no main-root manifest/ABI/CI edits.
- **Goal:** R1-M4-LINUX-BATCH-TX-003: implement bounded Linux nonblocking ready-only batch kernel transmit semantics (sendmmsg MSG_DONTWAIT up to32), borrowed immutable full packet slices, accurately classify definite accepted prefix/NotSent vs uncertain, stop/borrow fence; prove using unprivileged Linux UDP loopback as a syscall fixture, NOT claim AF_PACKET live raw TCP.
- **Done when:** Native Linux Actions tests compile once and actually invoke kernel nonblocking sendmmsg on loopback where supported, verify 0/n/all accepted prefix, EAGAIN definite NotSent, interrupted/short ambiguous, immutable frozen payload, batch cap and stop/loan safety. If libc ABI declarations or pinned dependency cannot be audited inside owned crate, file exact root dependency request to M0 and do not fake syscall PASS. Own S/evidence/H; no raw AF_PACKET/Windows/cold admission/product claim.
- **Anchor and counterexamples:** 04-CARRIER-IO 03-MEMORY; I01/I03 + Linux sendmmsg return rules
- **Important limiter:** production OS raw socket, Npcap and Wintun remain NOT_RUN


## M0 own simultaneous task
M0 next independent **R1-M0-FEC-OUTER-FIRST-002**: join existing main-native authenticated FEC-on first systematic and actual RS20 recovery to existing byte-exact M4 IPv4/TCP DATA envelope as a full-packet send and receipt/MTU provenance check. M0 owns cross-crate test and root CI, not new M1 parity scheduler, M2 global allocator, M3 BlockID-ext helper or M4 batch syscall. Validate exact same source: Crypto AEAD+PN replay first, no FEC waiting for first business, immutable record reused for repair, TCP/IP checksum and whole-packet MTU including FEC options. Only after worker atoms qualify does M0 integrate their new code and scheduler. Keep production Go V4 and real raw carrier disabled/unqualified.

## Gates and nonclaims
Worker tests use existing `worker-native-tests.yml` / `worker_native_bundle.py` dynamic r1_/r2_ selection and real compiled-once artifact hash. On a newly failing historic root ABI test, M0 must repair the shared harness; worker must not silently edit root files. Independent exact worker SOURCE + evidence S + cursor-only H Governance required before M0 considers integration. No implicit new M1–M4 process starts from this assignment. No feature0 activation, Go exporter/auth session, AF_PACKET product, native Win/Arm, p99 or physical qualification.

## Exact assignment SOURCE verification

Main assignment SOURCE [`6f5c891d349062c7206b07a0f916a5f2a8de6ea4`](https://github.com/lly8666/wbd-next/commit/6f5c891d349062c7206b07a0f916a5f2a8de6ea4) passed both same-source registration/governance [#38592016440](https://github.com/lly8666/wbd-next/actions/runs/38592016440) and scoped five-crate G2 native bootstrap [#38592016227](https://github.com/lly8666/wbd-next/actions/runs/38592016227), all **2/2 SUCCESS**. No new M1/M2/M3/M4 implementation, new worker native result, performance, or product qualification is implied. Record `docs/evidence/M0/R1-parallel-worker-assignments.json`.
