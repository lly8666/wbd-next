# H2318 — PLAN029 P0 Windows first-send copy removal

Baseline: 7222b4739443dbb7ff9b322f186dcf651b54490f. H2312 and H2313 both reject a stable TX16-only improvement at fixed NPF64. H2292 combined profile did not isolate batch size. Do not repeat the batch-size sweep as the next increment.

Remove the intermediate ciphertext slab on the original Windows native TX path. Reuse the two owner-local source/final-frame slabs across ready-only turns. M1 still freezes and stages the exact same record, directly at Ethernet+IPv4+TCP offset 54. Complete the header/checksum around those bytes using the shared carrier header routine; retain NPF copied-prefix settlement, original PN/Seq, MTU, fresh scheduling and Stop. No new worker, wait, wire format, allocator, protection or telemetry. Fixed source staging follows the same path; parity and repair scheduling are unchanged.

Expected: one fewer full ciphertext copy and no three full slab clears per source batch. With BATCH=8 the old three arrays total 51200 bytes per stage call; with BATCH=16 they total 102400 bytes. These are source-level buffer extents, not measured memory traffic. At 400Mbps source payload the eliminated copy is approximately 50 MB/s payload movement plus record overhead. This is a CPU-path simplification, not evidence that the NPF/kernel bottleneck is removed or that 600–800Mbps is attained.

Validation: existing native Windows source-locked unit/check workflow is triggered by the runtime file change. Added byte-for-byte carrier equivalence test covering odd/even lengths, maximum default MTU, and scratch reuse. Real throughput NOT_RUN. For paired real product tests compile current DLLs and ARM baseline, rather than reuse frozen H2292 older DLLs; compare same batch/NPF settings before/after, not TX8 vs TX16. Main remains unchanged.

```feature-impact
{"kind":"none","ids":[],"reason":"Internal Windows native TX scratch lifetime and redundant ciphertext copy only. Existing feature behavior and protocol unchanged; no new performance qualification or default feature promotion."}
```
