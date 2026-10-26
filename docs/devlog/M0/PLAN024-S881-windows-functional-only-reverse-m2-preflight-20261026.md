# M0 Windows functional-only original Rust/Go wiring (2026-10-26)

Source base main `7a6a289147d423c20b949697b0bcd4d8d70aaade`; isolated branch `fix/m0-windows-functional-wiring-20261026`. User directs: **do not integrate FEC experiment now**, only make original Go TLS Windows Npcap/Wintun ↔ Linux raw/TUN authenticate, exchange real business IPv4 both directions and Stop. No 10Mbps, loss, CPU or WL-N1/N5 work.

## Proven old failure
Original main SOURCE `f11b6e7a` WL-N0 Action [40295748769](https://github.com/lly8666/wbd-next/actions/runs/40295748769): Go/Rust TX +103-byte mismatch at ~11.875s into measurement; real credential TLS/Npcap/Wintun/Linux raw/TUN, real two-way UDP startup, cleanup passed, full 60s product FAIL.

## Distinct code risk and narrow fix
`v4_windows_owner.rs::m2_next_feedback_entry` previously sealed an original kind1 and advanced Rust PN/TCP sequence before inspecting C ABI output capacity. If `used>out.len()`, it returned `FULL`, which caller reinterpreted as `Ok(None)` (no reverse feedback); next normal DATA received Rust TX seq beyond Go `sendNext`. This is a real source-level silent-sequence-gap defect. The observed +103 bytes **may** fit a single lost kind1 but is not proven until source-locked Action.

Preflight exact TLV encoded size+31 fixed wire bytes **before** seal. A later size mismatch is a fatal `BAD_STAGE`, not silent optional feedback. Keep strict Go seq equality; no forged TCP ACK, no AEAD PN reuse, no M2 shadow bypass. Add native Windows Rust regression with short output buffer demonstrating no PN/SEQ loss.

## Test boundary
Branch-only real two-OS functional smoke workflow reuses exact-source Linux Go/Rust and Windows Go/Rust signed Npcap/Wintun, original credential TLS, authentic UDP first-delivery in both directions and owned Stop. Set `WBD_WL_RUN_N0=0` to avoid quantitative throughput/netem/60s tests while wiring; Action outcome must be read, **not assumed**. Main's original full N0 workflow remains untouched. After scoped PASS and further verified wiring, production main integration is a separate deliberate step; this branch is not an experimental FEC merge.

Outstanding: before Action, Rust and Go native ABI build, exact product duplex/Stop are `NOT_RUN` for this candidate. Fixed/Auto/Game/GUI/WFP physical remain separate; experiments continue independently.
