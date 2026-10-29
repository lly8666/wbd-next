# M0 PLAN026: native signed Wintun two-symbol FEC2 source/repair test under real 150ms cache

2026-10-29, exact parent `2bb8828c`. Latest real Windows WAL `40824784554` compiled, original-Go credential TLS and signed Wintun first/reverse passed, then both Fixed and Auto authentic RS16 missing-source assertions failed `rc=INVALID`. The previous test now closes Rust owners on failure and returns promptly instead of masking the real failure as a six-minute test hang.

**Isolated test-fixture design flaw:** Genuine `Fec2LiveRx::MAX_BLOCK_AGE_NS` is 150,000,000ns and its `retire(now)` occurs on each authenticated symbol. The former Windows original-Go kernel helper created/removed a real /32 lease, waited for DAD, created a UDP socket and installed/removed a Defender rule separately for `knownWire` and `repairWire`. These two expensive network-device preparations happen between the authenticated source M3 open and the parity M3 open, far beyond 150ms. The decoder rightly retires the incomplete block and rejects late repair. The test was not a valid real-time RS16 experiment.

Fix **only** the same-source Windows Go original TLS test helper and FEC2 positive test. Add `m0RealOriginalTLSRustAEADToSignedWintunKernelAppBatch` retaining one genuine signed Wintun /32 + Defender + UDP socket and validating every packet's exact source/bytes after real kernel app receive. Pre-seal source and parity using the existing original-Go TLS Rust M1 and transmit both with the same OS fixture, then open the two consecutive unique authenticated M3 records without OS lease changes in between. Preserve all positive original Wintun and Rust RS16 recovered-missing/source-replay/fixed/auto/Stop assertions. **Do not** relax 150ms cache, extend peer-replay, bypass the real Wintun, forge an M2 or applied receipt, or disable failed tests.

Status: `NOT_RUN` for new exact-source signed Wintun batch until the newly triggered real Windows WAL Action completes. This is a test timing correction, NOT a product PASS or a claim the actual 2/4 Game native workers have passed OS/CPU qualification.

```feature-impact
{"kind":"none","ids":[],"reason":"Original Windows signed Wintun FEC2 real OS batch test keeps source+parity within the genuine native Rust 150ms expiry without changing production code or weakening any assertions."}
```
