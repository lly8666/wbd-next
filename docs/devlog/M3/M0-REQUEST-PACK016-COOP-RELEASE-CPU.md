# M3 PACK016 → M0: exact SOURCE Release cooperative FEC CPU service probe

Frozen worker code SOURCE: `e2a0a60fd512bedbcd136dd03e9be655ab2cf7c7`. Authored on `work/m3-r1-codec`, role M3 task016. Rust1.85.1 native functional Actions [39003330821](https://github.com/lly8666/wbd-next/actions/runs/39003330821): **109/109 PASS, 1 ignored**; own worker Governance [39003330841](https://github.com/lly8666/wbd-next/actions/runs/39003330841) SUCCESS and M0 central source scope [39003440040](https://github.com/lly8666/wbd-next/actions/runs/39003440040) SUCCESS. The ignored Release probe has not run and must not be marked CPU-qualified.

## M0-owned action (no M3 shared-path edit)

Create or dispatch an M0-owned Linux runner Rust **1.85.1** job that checks out the exact SOURCE above, compiles the codec Release test binary ONCE and records the binary SHA256 before executing the SAME binary.

```bash
cargo test -p wbd-codec --release --lib r1_tx_cooperative_release_cpu_wall_diagnostic -- --ignored --nocapture --test-threads=1
```

Preserve raw stdout/log and test manifest: three payload lengths 256/512/1200, each with three alternating pair repetitions and both old synchronous and new cooperative modes = **18 scoped leg summaries**; each >=1.05s warmup and >=1.125s active, multiple >=250ms measured windows, actual thread schedstat/sched CPU probe and paired wall; each window must have `CPU <= wall*1.02` with no rewrites/clamps. If clock unsupported or any invalid window then leg = `CPU_INCONCLUSIVE`, with NO CPU ratio. Verify 20 real systematic and 20 real parity rows per full 20:20 block and matching source per report. Distinguish `p99_four_row_WALL_ns` (wall observation for 4-row batch, subject to scheduling) from **per-packet latency p99** or a certified worst 100µs CPU service limit. No automated `100us PASS` or 500Mbps claims.

Artifacts: pinned tested-source SHA, Linux runner/version/cpu-target, compiler version/flags, artifact digest, executable SHA256, raw line counts/times, exact test stdout and SHA256, pass/invalid counts, no cross-run ratios. Please place a receipt under M0's evidence or use M0-owned workflow Actions artifact. Keep root CI and ISA-L dependency changes M0-owned. This request is not permission for M3 to modify shared CI.

Related ISA-L native prerequisite remains in `docs/devlog/M3/M0-REQUEST-PACK016-NATIVE-ISA-L.md`.
