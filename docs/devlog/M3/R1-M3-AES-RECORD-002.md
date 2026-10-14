# R1-M3-AES-RECORD-002 · Three genuine record suites

M3 current working atom adds actual AWS-LC AES-128-GCM/AES-256-GCM authenticated Seal/Open with lane-local separate RustCrypto AES HP block. Uses V3 authenticated Go suite IDs 1/2/3, 16B prefix key for AES128, all 32B for AES256. Preserves ChaCha default constructor and six original Go vectors; exact HP sample is first 16 ciphertext/tag bytes, encrypt once with independent hp key, use 8 output bytes. Caller supplies authenticated suite-separated keys; this atom never claims V4 exporter integration.

Independent Go1.23 AES-GCM/AES reference generator under crates/wbd-codec/oracles/aes_v3_go_reference.go implements pinned original Go suite_test.go and keys.go, without importing app tlsrecord code. Its 14 literal vectors are validated again via independent PyCA HKDF/AES-GCM/AES-ECB 14/14 matching before S. Rust adds differential byte equality, authentication tamper at each byte, wrong suite/IV/HP, 0/1/15/16/17/31/1024/full wire HP tag overlap/reordering and PN exhaustion. No fake cipher, no QUIC HP truncation, no shared Cargo/ABI changes.

Actions native PENDING at initial S; evidence and cursor H only after observed real workflow success. RX replay bitmap, transport framing, M1/M4 integrated Normal/off first business, V4 KDF, product/perf/physical all NOT_RUN.
