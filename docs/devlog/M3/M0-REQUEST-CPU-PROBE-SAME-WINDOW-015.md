# R1-M3-CPU-PROBE-SAME-WINDOW-015: M0 Release workflow request

Task 015 is formally assigned M3 in main registry rev2 epoch1. M3 owns only codec test code and its request/evidence. M0 owns shared CI and the exact release workflow.

New code replaces the old per-64 `/proc/thread-self/stat` ticks that were outside the timed wall window with Linux high-resolution thread schedstat (ns) and sched fallback (microsecond decimal-ms). Paired wall time now brackets both CPU probes per 128 x 64 authentic records, avoiding mismatched CPU and wall windows. Reused-source AEAD Seal stays outside both CPU and wall timing, with persistent two-tunnel x two-direction owners and new unique PN and BlockID per record.

After M3 Debug 99/99 regression passes at frozen SOURCE, M0 should create an exact-SOURCE Rust1.85.1 cargo --release --locked -p wbd-codec --lib --no-run compiled-once same-job native workflow. Verify real rust test exit 0 and 24 rows across 192/896, fresh/steady, AEAD/FEC, 3 reps, >=1.05s warmup and >=1.125s measured per leg. For each row: clock_status=OK, same_window_cpu_ns <= same_window_wall_ns * 1.02, clock_windows > 0, backend is schedstat_ns or sched_runtime_us. If no CPU clock: CPU_INCONCLUSIVE, ratios MUST be NOT_QUALIFIED, no invented gain.

Save source/commit/runner/test binary SHA/artifacts/full raw clock rows, CPU and wall and batch-average p99 semantics. Do not claim packet p99 or 500Mbps, genuine V4 authenticated session origin, production FEC or physical traffic.

The corrected final SOURCE additionally emits M3_CLOCK_WINDOW for every paired observed window (raw wall_ns/cpu_ns and backend) and M3_BATCH_SAMPLE with up to 2048 unaltered batch-average elapsed times per leg, both outside the observed timing. It also logs actual M3_CLOCK_WARMUP active ns per mode. The M0 Release checker should ensure aggregated raw windows match each row exactly and verify CPU<=wall*1.02 in every window, not only the aggregate.

Governance coordination: prior M3 test SHA 30016fa0 Governance run38706745738 attempt1 failed due main tool drift; main control has since pinned the second checker mirror to immutable historical source 940498cc and old main blob 817934b, which should remove that historical cause. A second audit of original SOURCE was requested, outcome must be tracked before completion.
