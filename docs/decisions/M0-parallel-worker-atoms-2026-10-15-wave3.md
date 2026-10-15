# M0 · third independent worker atom assignments · 2026-10-15

## Exact authority
Main before assignment `bb21b388d6af256b5e4bc190901e7aa6459fb3a2`, M0 cursor sequence48, checkpoint `540bdcb8cd2a50f2d639800febbd7d9f8c5a390d`; H Governance 38671831389 SUCCESS. All four worker branches at prior individually verified cursor-only H and no additional unreviewed commits. Registry `reservation_revision=2`, `assignment_epoch=1`, roles remain active and **allowed paths unchanged**.

## Completed prior atoms (accepted only for scoped native evidence)
| Role | Code SOURCE | Native compiled-once | Cursor H and Governance |
|---|---|---|---|
| M1 bounded RX ready | `e0a9f64d5c17d8085c52f09a083b9689535f00d1` | run38669368706, 51/51 PASS | `fa518d65b53460346db710c3715076299ff140c6`, 38669632237 SUCCESS |
| M2 receipt epoch races | `06fe27ae516cdef6b144c736a2166a5f6d4b209f` | run38669519161, 33/33 PASS | `43c0e985a265c701e51354d7d05a0bb885d1457f`, 38669865546 SUCCESS |
| M3 post-auth FEC scope | `42382c60ee51689d49c480411af3df2acc9e9a7d` | run38669822925, 85/85 PASS | `f56a6720887bac7471a1e29b24b55b8d25bfb73d`, 38670975617 SUCCESS |
| M4 Linux RX recvmmsg | `2a4bc0e856f84042da292a4fae93d2a32d2d10db` | run38669449668, 42/42 PASS | `7bbd60d14bba82678fa68a0bc8edba3775f5f9eb`, 38669770858 SUCCESS |

M0 main SOURCE `f5dcb230804531c7dd558d3ef624f99faeca25d6`: 12/12 exact Actions SUCCESS, full sendmmsg/recvmmsg+IPv4/TCP+AEAD/PN scoped UDP fixture, native platform 42/42 and engine5/5, evidence S `540bdcb8cd2a50f2d639800febbd7d9f8c5a390d`. Historical worker CI count failures and main movement Governance retries remain failures; never relabel.

## Third-wave new tasks
### M1: R1-M1-STOP-LOAN-GENERATION-006

**Goal:** Within existing M1 runtime and owned tests, prove one owner-scoped generation transition safely drains preallocated <=32 TX and RX ready batches, old-generation callbacks cannot resubmit already-frozen ciphertext, first fresh on a new scope not blocked by late loan returns, and stop/borrow fences give exact last-loan ownership. No syscall, external dependency or source of authentication.

**Done when:** Own SOURCE compiled-once native r1_ tests of 0/1/32/33, two lane generations, mixed RX/TX loan returns, ABA/stale owner token, stop during ready and fake-clock expiry, no heap during hot drains and complete prior51/51 tests; own evidence S and cursor-only H Governance.

**Write ownership:** exactly the existing `.governance/registry.json` allowed prefix for M1; no root CI, ABI, Cargo.lock, cross-role files, or other worker branch.

### M2: R2-M2-RECEIPT-REVERSE-SCOPE-005

**Goal:** Add pure fail-closed receipt-route admission contract requiring caller-supplied trusted reverse direction, TunnelKey/generation/epoch/PN scope before AuthenticatedReceipt or process-global batch grant settlement; stale/forward/cross-lane input never refunds an old repair or advances ACK. No cryptographic admission constructor, driver syscall or peer delivery inference.

**Done when:** Own source compiled-once native r2_ deterministic MonoNs tests covering two tunnels both directions, stale epoch/rotation, ACK before grant, NotSent original epoch, Uncertain conservative debit, duplicate out-of-order receipt and 32/33 batch, retaining previous33/33 tests, own evidence S/H Governance.

**Write ownership:** exactly the existing `.governance/registry.json` allowed prefix for M2; no root CI, ABI, Cargo.lock, cross-role files, or other worker branch.

### M3: R1-M3-FEC-MULTISCOPE-012

**Goal:** Strengthen existing FecOrigin test-only typed post-AEAD gate with two concurrently isolated trusted scopes under fake time: per-tunnel and direction replay/BlockID floors and Heavy/Compact expiry cannot contaminate peers, even after rekey and old parity. NO production origin constructor; no Go handshake/ABI/root edits.

**Done when:** Own SOURCE compiled-once native r1_ tests for two tunnels both directions, 32-bit BlockID wrap, misrouted true AEAD ciphertext, replay and exhausted caps, PNs independent, deterministic timers and 56B oracle, retaining previous85/85, evidence S/cursor-only H Governance; live Go V4 provenance remains NOT_RUN.

**Write ownership:** exactly the existing `.governance/registry.json` allowed prefix for M3; no root CI, ABI, Cargo.lock, cross-role files, or other worker branch.

### M4: R1-M4-AF_PACKET-PREFLIGHT-006

**Goal:** Implement narrowly cfg-gated Linux AF_PACKET capability and FD ownership preflight within wbd-platform, retaining unprivileged UDP sendmmsg/recvmmsg fixtures unchanged. Validate interface index, protocol/packet_type, MTU and owned borrowing lifetimes; on missing CAP_NET_RAW return typed EPERM with no fake fallback, no live raw activation, no new Cargo dependency/root ABI.

**Done when:** Own SOURCE native tests and unprivileged Linux capability-negative cases with exact errno and rollback/close; classifier and lifecycle tests for bad iface/truncation/stop/generation, preserve42/42 previous native tests, evidence S/H Governance. Do not claim AF_PACKET data exchange or live TCP unless an exact privileged fixture is separately authorized and executed.

**Write ownership:** exactly the existing `.governance/registry.json` allowed prefix for M4; no root CI, ABI, Cargo.lock, cross-role files, or other worker branch.

## Handoff rules and highest product blockers
The assignment permits but **does not itself launch agents** or establish new worker SOURCE/tests. Each worker independently refreshes main registry and branch cursor, creates its own code SOURCE + compiled-once native proof, evidence S and cursor-only H, with source-exact Governance. Main-only decision document MUST NOT be added to worker branch cursor `context_refs` when it does not exist in the branch (historical M2 structure failure). M0 alone merges cross-crate integrations on main.

M0 concurrently owns separate next CODE atom `R1-M0-M3-POST-AUTH-FEC-MAIN-013`: integrate M3 85-case authenticated FEC admission with **test-only** sealed origin and prove missing trusted origin always blocks before replay/BlockID mutation, while preserving genuine AEAD+PN and old-Go 56B; no product V4 activation.

**Critical path:** actual legacy Go V4 authenticated cold-session export of tenant/lane/tunnel/direction/epoch/generation and keys to Rust, plus true AF_PACKET raw carrier and lifecycle. A test-only `FecOrigin` constructor is never a valid live exporter. Product, native Win/ARM, physical, sustained500Mbps/p99/CPU/RSS remain NOT_RUN.
