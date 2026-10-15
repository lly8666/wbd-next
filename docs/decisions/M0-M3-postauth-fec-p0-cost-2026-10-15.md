# M0 · M3 next independent post-auth FEC cost atom · 2026-10-15

## Completed worker acceptance
M3 task `R1-M3-FEC-MULTISCOPE-012` on worker source `4787d94617afe72c511f3f2299d1b060c2930c6c` is formally **accepted in scoped test-only qualification**. Code changed only `crates/wbd-codec/src/fec_multiscope_tests.rs` and `link_fec_wire.rs` test mount. Independent compiled-once native [38674583861](https://github.com/lly8666/wbd-next/actions/runs/38674583861) 94/94 r1 tests PASS, nine newly added cases for two tunnels x both directions, true independently keyed AEAD+PN replay, BlockID wrap, scope mismatch, Heavy/Compact expiry, rekey and fake test-only FecOrigin; all seven same source Actions final SUCCESS. Historic code Governance38674583957 attempt1/2 moved-main FAIL; attempt3 SUCCESS. Evidence S `5387a4f7a3d0daa14ebc68495f894626623bd3d7` Governance38675260385 SUCCESS; cursor-only H `78003a198fd46ac8fa497f0255fe67e2c26b1d95` Governance38675514034 SUCCESS. This does NOT establish a live Go V4 trusted FecOrigin. No production algorithm changed in the completed task.

## Next M3 atom
**R1-M3-POSTAUTH-FEC-P0-COST-013**

R1-M3-POSTAUTH-FEC-P0-COST-013: Within M3-owned codec R1 paths, profile the bounded incremental cost of authenticated-input FEC admission and BlockID/Heavy/Compact bookkeeping after real AEAD+unique PN, comparing scoped test-only origin enabled vs absent-origin fail-closed. Use fixed-size reproducible records, explicit multi-tunnel/direction/key scope, no production FecOrigin constructor or Go exporter. Label any P0 result as component cost and never infer 500Mbps product throughput.

**Done when:** Retain prior94/94 r1_ native multiscope test cases; add bounded real AEAD/FEC adversarial correctness and repeated (>1s where runner permits) warmup+CPU-s, byte-cost and sample percentile experiments under existing M3-owned tests/tools. Own source-exact compiled-once native tests+artifact evidence and cursor-only H Governance, explicitly record runner, source, results and noise. No root CI/Cargo/go/ABI or production origin; no software feature flag.

Main registry revision2/epoch1 unchanged, M3 allowed paths unchanged; M1 `R1-M1-GENERATION-READY-OWNER-BENCH-007`, M2 `R2-M2-REVERSE-GRANT-OWNER-BENCH-006`, M4 `R1-M4-RAW-RECEIVE-CONTRACT-007` remain their independently assigned tasks, NOT reassigned. This assignment is permission to perform the task, not evidence an agent started or produced new results. M3 must independently fetch current main registry, work strictly on owned branch, deliver code SOURCE, own native proof, evidence S, cursor-only H with same-source Governance, retaining historical failures.

## M0 and performance
M0 already ran short P0 native component measurements SOURCE57e12d28 (actual AEAD HP PN and UDP sendmmsg+recvmmsg) and is now testing longer repeated P0 SOURCE `407cc99aab2a86b792479e92b0b8e1ebed808c61`. Neither qualifies end-to-end 500Mbps, raw AF_PACKET, production Rust cold owner/positive FecOrigin, Windows ARM native, product or physical.
