# M3 → M0 · R1 integration dependency and pinned Go native oracle request

Role/scope: M3 active revision2 epoch1 on `work/m3-r1-codec`. Request is coordination only. **M3 does not edit root Cargo, Cargo.lock, shared types/ABI, CI/workflows, or the old Go repository.**

## 1. Upcoming independent cryptography atom — required M0-owned dependency lock

M3 next priority: authentic Rust independent record `LaneTxCrypto`/`LaneRxCrypto` Seal/Open with protected PN8, ChaCha20-Poly1305/AES128-GCM/AES256-GCM eventually, and exact **8-byte** HP matching original Go. This R1-M3-BUDGET-001 scope has **no AEAD implementation and no three-cipher qualification**. Please have M0 own the root `Cargo.toml`/`Cargo.lock` adjustments and review whether `aws-lc-rs` (explicit-nonce, in-place AEAD) plus RustCrypto `chacha20` and `aes` (standalone ChaCha/AES HP mask generation, exactly 8B—not QUIC 5B API) can be pinned on Rust 1.85.1. M3 may edit its owned `crates/wbd-codec/Cargo.toml` after M0 agrees cross-crate dependency/version and lock. Do not silently substitute mock encryption or change cross-module ABI. Prioritize real Normal/FEC-off single packet seal/wire/open/return; do not wait for all three cipher suites to start integration. Public interfaces/engine wiring remain M0-owned.

Protocol nonnegotiable: record outer 5B + protected PN8 + cipher/tag16 + inner kind/marker2, fixed31B; AAD=5B outer+raw PN8; nonce=IV12 XOR (00000000 || PN_be64); ChaCha HP reads first16B ciphertext/tag, 4B LE counter +12B nonce, derives 8B; AES HP encrypts same16B sample, first8B mask. Failure PN is burned; same Seq repair reuses frozen ciphertext; never publish unauthenticated payload.

## 2. Go pathmtu native Actions gap

M3 SOURCE `3aa121e4c10a80c4175ccfb057f3e64b01e4b382` has native Rust compiled-once scoped tests 6/6 PASS (worker run 38538473699) using **literal pinned Go oracle** values extracted from `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984` `internal/pathmtu/{budget.go,budget_test.go}`; all seven same-SOURCE triggered workflows green, including old Go LINK/FEC wire tests. **Neither new M3 workflow nor existing R0 workflow runs native `go test ./internal/pathmtu`**. If native old-Go pathmtu execution is required for the full atomic done_when, please add M0-owned CI/workflow or overlay to execute the exact pinned Go package once, record old/new exact SOURCE provenance and result. This is an outstanding qualification gap, NOT a product regression. M3 keeps direct old-Go package execution as NOT_RUN until that evidence exists.

Integration guidance: consume `FrameBudget.link_frame_mtu` unchanged as complete LINK capacity; `FrameBudget.record_wire_mtu` unchanged as complete record wire ceiling. No second 31/56/20 deductions upstream; Game16 is added once before fragmentation. No configuration/CLI/GUI behavior added: this is an internal accounting module.

References: `docs/evidence/M3/R1-M3-BUDGET-001.json` and `docs/devlog/M3/R1-M3-BUDGET-001.md`. This request asks M0 for only shared ownership work and native Go oracle; M3 remains responsible for its own Rust codec implementation.
