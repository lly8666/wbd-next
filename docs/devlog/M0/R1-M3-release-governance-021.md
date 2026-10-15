# M0 M3 release-and-governance scoped acceptance audit · 2026-10-15

## Why now
M0 seq56 H bbcf12ce Gov38683476593 SUCCESS and active main registry rev2 epoch1; user asked to inspect M3 first. M3 own source 88a12027 Debug98/98 run38682956912 PASS, while M3 CODE/S/H Governance failed due obsolete main-tool blob and Release >=1s repeated cost had NOT_RUN.

## Concrete main changes
CODE 6558aef0 adds exact worker-SOURCE Release compile-once and one same-VM test of 192/896B × fresh/steady × AEAD/FEC ×3 repeats (24 rows) with artifact SHA verification. Original run38684106420 compiled Rust1.85.1 Release binary SHA1d04c7c7... but measure CANCELLED at14min, result artifact real 21/24 rows; cannot claim success.

CODE0a53c441 authorizes a second *sole tools/worker_scope_ci.py exact-parent* M3 mirror after H5eaf and runs full M3 95-commit scope audit; main Gov38684596431/G2 audit38684596447 SUCCESS (95 total,68 worker,27 main). CODE93a3110c extends only measurement CI runner time14→22 minutes based on observed 21/24, launches independent run38685587150; no row-splicing across runs. CODE940498cc identifies per-batch CPU probe overhead and increases full bounded G2 cap to99 (100 fails), permitting EXACT four remaining M3 branch commits (tool mirror, test fix, evidence S, cursor H). Main Gov38685996632 and 95-commit audit38685996539 SUCCESS. Exact hashes, artifacts, results in sibling JSON.

## Unanticipated serious invalid CPU time measure
Downloaded cancelled result artifact test.log; 20/21 markers claim thread CPU > measured active wall. M3 test code measures CPU before wall start and after wall elapsed via expensive procfs read/parse for every64 records. Those CPU deltas contain probe overhead outside wall and vary with leg count. Consequently **no valid cpu_us/record nor fresh:steady CPU ratio**, even if delayed retry finishes. Wall p50/p99 are averages of 64-record batches, not individual packet latency, and are not product evidence.

## Worker and independent M2 boundary
M3 work HEAD remains5eaf at95 G2 commits. M0 tested exact 99-limit and one-time historical+new root exception; **M3 worker has not mirrored** byte-identical main tool blob817934b16c6e088069ad9b4c265c93daacda7759 nor passed own H Governance. Requires M3-owned corrected measurement and its own SOURCE evidence S/H. Old M3 H cannot be relabeled PASS.

M2 independently finished G2 recovery after earlier blocker: worker head901abe61 seq13, R2 native44/44, checker H Gov38683609942, evidence S Gov38683931339, H Gov38684127224 SUCCESS. Its scoped work qualifies for future M0 integration, but not product. Real Go→Rust trusted owner, FecOrigin, physical, AF_PACKET live, Windows/ARM native, P1–P3/500Mbps remain NOT_RUN.

## Done boundary
M0 scoped tasks deliver a real SOURCE-locked Release CI instrument (nonqualified CPU), exact governance continuation validated by main Actions, discovery and preserved raw evidence of CPU invalidity and time budget, plus one bounded M3 action card. Not M3 worker 014 completed. Track already-running retry38685587150 without redispatch. Next M0 independent atom remains real protected Go V4→Rust fresh owner Prepare/Detach/Commit B01–B04; don't enable production.
