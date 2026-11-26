# pktkit TCP source provenance

Pinned upstream: https://github.com/KarpelesLab/pktkit-rs/tree/836ae122e150de50a309c7f1703adb364e13d4c9 (v0.1.12, MIT; LICENSE retained).

Only the vtcp state machine and its macro, clock, random and atomic budget dependencies are included. No pktkit TUN, socket drivers, runtime, NAT, TLS or extra thread. The upstream crate requires Rust 1.89/edition 2024; this port retains WBD Rust 1.85.1 and its Cargo dependency graph. Local edits: namespace/Result paths, equivalent pre-let-chain syntax, extraction of stats::add_within, local module declarations, Conn::send_available for direct single-owner flow-control transfer. Upstream algorithm behavior is intended to remain unchanged; not yet validated. No zero-copy or performance claim.
