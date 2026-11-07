# PLAN028 H1289 — correct 64-stage M4 test to consume existing 32+32 R1 RX batches

H1288 source `cc70b1c0272d130b7dca91c17a4f6ba0aad50ab2` native ARM64 short workflow `42317762450` stopped in Build before live scenes. Source-locked original Go FakeTCP TLS, Rust M4 prep and ISA-L feature compile reached targeted tests; the static original Go/Rust 64-record FFI contract test PASSED. The new 64-slot `EarlyRxOwner` test reached Detach and then failed at `early_rx.rs:332`, `left:32,right:64`, because the test incorrectly assumed a 64-entry prepared queue must be consumed in one R1 M1 ready batch.

The existing `runtime/rx_batch.rs` establishes `RX_READY_BATCH_MAX=32` independently of the prior 64-entry prepared storage and a 64-slot per-session RX queue. The production 64-slot bounded Stage/Prepare/Commit implementation remains unchanged. Fix ONLY the test to drain two legitimate real `ScopedOwner::drain_rx` turns, check FIFO exactly bytes0..31 then32..63, preserve the 65th reject and verify 32 queued M1 loaned buffers after the first, zero after the second. Do not enlarge the actual M4 RX dispatch batch, schedule new worker or mask any real M4 rejection.

Re-run strict ARM64 native Rust unit `1 passed; 0 failed;` and original Go classified Prepare tests; then same three existing source-pinned 180s five-client native/scalar short scenarios. No 1800s runs until no server hot cohort missing, no `>=750ms` active business gaps and zero per-lease drops in all five clients. Previous H1286 180s FAIL9/12/12, H1287 0-loss Game4 fails native Prepare, H998 physical MTU and remote ICMP remain source-specific open.

```feature-impact
{"kind":"none","ids":[],"reason":"H1289 adjusts only a targeted Rust unit's expectation to preserve real original 32-record RX dispatch turn while verifying the 64-record protected early-stage queue and two full FIFO turns; product runtime unchanged."}
```
