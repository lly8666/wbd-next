# R1-M3-FEC-TX-006 — bounded source-first TX owner

Uses pinned old Go a7a82db3 internal/fec/fastblock_encoder.go and size_class_encoder.go semantics, and proven Rust fec_math.rs scalar real parity.

submit(source,mono_ms,profile,wire_limit,large_fragment_hint) produces two distinct queues: systematic now, parity separate. Owner must give ready systematic priority before parity. No driver success claim.

One open block per class, max three classes (256/512/MTU only profile20); profiles4/8/10/12/16 one block. Globally shared extended block ID reserved on first source, low32 wire avoids reserved zero. One owned copy of each source within configured bytes <= 3*20*65535.

First-source+32ms absolute deadline never renewed; full20 closes without waiting. Partial r_sent=min(k,R), wire header configured R, authoritative final source lengths and Go GF0x11d parity. Large LINK fragment hint stays in largest class.

Profile or wire_limit change closes old before new; memory pressure closes oldest deterministically; explicit owner-supplied monotonic clock, no OS background timer.

CODE SOURCE Actions PENDING. SIMD ISA-L, heavy/compact RX, M0 first FEC-on payload, scheduling CPU p99, Windows/ARM native/product/perf NOT_RUN. Root Cargo/ABI unchanged.
