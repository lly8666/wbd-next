# R1-M3-CPU-PROBE-SAME-WINDOW-015: M0 Release workflow request

Task 015 is formally assigned M3 in main registry rev2 epoch1. M3 owns only codec test code and its request/evidence. M0 owns shared CI and the exact release workflow.

New code replaces the old per-64 `/proc/thread-self/stat` ticks that were outside the timed wall window with Linux high-resolution thread schedstat (ns) and sched fallback (microsecond decimal-ms). Paired wall time now brackets both CPU probes per 128 x 64 authentic records, avoiding mismatched CPU and wall windows. Reused-source AEAD Seal stays outside both CPU and wall timing, with persistent two-tunnel x two-direction owners and new unique PN and BlockID per record.

After M3 Debug 99/99 regression passes at frozen SOURCE, M0 should create an exact-SOURCE Rust1.85.1 cargo --release --locked -p wbd-codec --lib --no-run compiled-once same-job native workflow. Verify real rust test exit 0 and 24 rows across 192/896, fresh/steady, AEAD/FEC, 3 reps, >=1.05s warmup and >=1.125s measured per leg. For each row: clock_status=OK, same_window_cpu_ns <= same_window_wall_ns * 1.02, clock_windows > 0, backend is schedstat_ns or sched_runtime_us. If no CPU clock: CPU_INCONCLUSIVE, ratios MUST be NOT_QUALIFIED, no invented gain.

Save source/commit/runner/test binary SHA/artifacts/full raw clock rows, CPU and wall and batch-average p99 semantics. Do not claim packet p99 or 500Mbps, genuine V4 authenticated session origin, production FEC or physical traffic.
