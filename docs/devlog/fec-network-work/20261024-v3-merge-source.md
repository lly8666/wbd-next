# FEC independent V3 merge decision / conflict inventory (2026-10-24)

Merge parents, no force: first FEC `9cfd72968e21a63834f455a96afc71a5d35737db`, second frozen network `040741820b2f917b5868c285c438d4cc21c6193a`, common ancestor `45325c9c965e56080f2035bafcf235aa02a1a6c0`. Both histories retained. Status belongs only to `docs/evidence/fec-network-work/status.json`; upstream network status is immutable snapshot from parent.

Conflict resolution:
- V3 wins intact for Rust data plane, TUN ingress, sourced frozen repair **separate copies**, half-PN admission, 9% credit/10% cap batch budgeting, byte ledger and reset/Stop. Overlay FEC-only per-owner boolean gate, FFI set/read: on=original V3, off=no repair-only frozen copy or candidate, preserve first copy F bytes and genuine authenticated M2/RTT, plus independent FEC parity TX. Shadow remains an empty bounded native metadata owner for numeric readback.
- Linux product bridge/client/server/CLI: latest unified MTU and owned TUN fq600 flow-limit256 unchanged. Reapply FEC `--outer-repair` before original feedback arm / worker start; fail closed unsupported Game OFF.
- Harness config/tests/runner: latest network V3 mode, fq, startup/capacity, classification, telemetry and defaults unchanged; merge typed per-bundle `repair_enabled` for exact old/new on SAME VM, only pass CLI flag when declared. Strict dual endpoint readback and zero wire/parity separation. Existing `tests/network/fec-work/` preserved, no upstream request overwrite.
- Build and workflow: FEC branch ARM64 build trigger and one-scenario manual request architecture retained; new shared ARM bundle utility `tools/arm64_public_go_rust_bundle.sh` consumed from V3. No duplicate harness.
- START_HERE preserves both independent task notices; FEC entry updated with V3 precedence.

Evidence from original network frozen V3 (NOT the merged source): `docs/evidence/network-matrix-work/V3-all-Linux-modes-owned-fq600-20261024.json` shows Fixed5/5% one side pending, Auto/0% two sides pending; `V3-Auto-FEC-fq0-vs-default600-sameVM-20261024.json` still one side pending with fq0. Treat as control admission/real-receipt hypothesis, not qdisc root cause without evidence.

Old FEC build (7ad7) pass with legacy transfer errors 39915604295 / 39915779256 / 39916080164 retained in prior evidence. **No merged ARM64 build or FEC-only product run yet.** No Windows or Game off claim, no full performance pass. Next: exact merged build/cheap Actions before issuing new large cases.
