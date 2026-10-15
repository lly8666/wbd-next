# R1-M3-POSTAUTH-FEC-P0-COST-013

S source `0573798b27fa6fd6327ed1b997ee8cd50b0da526`: test-only `fec_p0_cost_tests.rs` beneath frozen R0 LINK namespace; no production origin, no Cargo/lock/Go/ABI/CI changes. Initial `f7ad0013` compile failed with E0282 untyped scratch `Vec`, superseded by `0573798b27fa6fd6327ed1b997ee8cd50b0da526` real fresh-PN retired-BlockID adversarial case. Historic failure is retained, not counted PASS.

## Exact native Actions

Compiled once Rust1.85.1 on Ubuntu24.04 x64 in debug `cargo test --locked -p wbd-codec --no-run`; worker native [#38678836564](https://github.com/lly8666/wbd-next/actions/runs/38678836564) build+consume passed **96/96 r1_** (2 new, 94 prior). Six other same SOURCE regressions + Governance all succeeded. `M3_P0_COST` source-tied rows in Actions test log and result artifact. P0 runs six groups × three rounds (18 samples): per group 150ms warmup, 1.125s monotonic measurement, CPU-seconds from Linux thread-specific utime+stime ticks, 64 records per batch. Fixed payload 192/896 bytes, actual encrypted wire 279/983 bytes each. Four distinct tunnel/direction key scopes, one new PN per record and bounded Heavy/Compact (4+4), test-only origins.

## Measured CPU debug P0 only

Mean CPU microseconds per record from each 1.125s repeat, rounded; **includes new owner setup every 64 records** and debug assertions. The controlled baseline does real AEAD+unique PN but does not enter FEC. The second performs real AEAD+PN+FEC admission, BlockID and Heavy/Compact. The third checks missing origin fail-closed before any AEAD, so **not** an equally authenticated comparison. Cross-source/cross-VM ratios are forbidden.

| shard bytes | AEAD+PN μs/record (r0,r1,r2) | AEAD+PN+FEC μs/record | Absent origin μs/record |
|---|---|---|---|
| 192 | 30.34, 30.18, 30.13 | 126.12, 125.00, 125.22 | 80.28, 81.74, 80.99 |
| 896 | 30.49, 30.39, 30.44 | 126.12, 124.11, 126.12 | 80.99, 82.55, 80.99 |

The measured difference is a **debug component total-path difference with receiver construction**, not isolated steady-state FEC per-packet overhead. Reported p50/p95/p99 are of repeated **batch-average wall ns/record**, not packet latency percentiles. Co-runner scheduling/cold cache/no release profile can perturb results. No product, real V4 authenticated origin, throughput, Windows/ARM, physical or native 500Mbps claims.

## Evidence and exit

Evidence `docs/evidence/M3/R1-M3-POSTAUTH-FEC-P0-COST-013.json` records exact 18 rows, binary/log/artifact hashes, all seven source-exact run IDs and historic failed compile. Next an evidence-only S Governance and cursor-only H, no new product work until M0 reassigns.
