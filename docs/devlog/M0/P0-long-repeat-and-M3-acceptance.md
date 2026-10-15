# M0 · P0-M0-REPEATED-NATIVE-PERF-017 and M3 acceptance · 2026-10-15

## Authority
Starting `main` HEAD `3f43bc086dbf89f790825a92a1a14c1f30a08f45`, M0 cursor sequence52 checkpoint `625994d0caa712f9a6f4cfb3e38b1c440aa9ac6a`, H Governance38677342941 SUCCESS. Registry revision2 epoch1. The pending M1 generation ready owner, M2 reverse grant ledger and M4 raw RX contract tasks remained untouched.

## M3 scoped acceptance, historical failures retained
M3 SOURCE `4787d94617afe72c511f3f2299d1b060c2930c6c` adds nine test-only real AEAD+PN multi-scope FEC isolation cases to the previous85, achieving native [94/94 run38674583861](https://github.com/lly8666/wbd-next/actions/runs/38674583861) PASS and final seven exact-source Actions SUCCESS. Covers 2 tunnels × 2 directions, BlockID wrap and retirement, peer memory pressure, rekey, old-Go 56B frame and negative absent origin. Positive FecOrigin constructor exists only inside `#[cfg(test)]`; no production FEC algorithm change or live session authentication.

Governance run38674583957 attempts1–2 **FAIL** from moving main control; attempt3 succeeded without changing code SOURCE. Evidence-only S `5387a4f7a3d0daa14ebc68495f894626623bd3d7` Governance38675260385 SUCCESS; cursor-only H `78003a198fd46ac8fa497f0255fe67e2c26b1d95` Governance38675514034 SUCCESS. M3 is accepted into the integration backlog, not already merged into main.

## Available work and next assignment
M1, M2, M4 have just-assigned wave4 work and unchanged active ownership. **M3 is the available role**. Formal M3 new assignment `R1-M3-POSTAUTH-FEC-P0-COST-013` on main SOURCE `7d67b6062f8ef48673cbb6df6ead392419befe0b` changes only registry's M3 goal/done_when and main-only decision `docs/decisions/M0-M3-postauth-fec-p0-cost-2026-10-15.md`. Governance38677811616 and G2 38677811629 SUCCESS. Task: post-auth real AEAD/unique PN gated FEC admission vs default-denied cost, scoped repeatable warmup/perf pressure, bounded heavy/compact, no production origin or Go/ABI/root edits. New registry remains rev2 epoch1. Assignment is not proof a worker process has started.

## Extended P0 native run and actual findings
CODE SOURCE **`407cc99aab2a86b792479e92b0b8e1ebed808c61`** changes only `crates/wbd-engine/tests/p0_native_components.rs` and `.github/workflows/p0-native-component-perf.yml`. On a single GitHub hosted Linux x86_64 AMD EPYC 7763 runner, Rust release binary compiled exactly once with binary/input SOURCE hashes and independently consumed for **three repetitions of each case**, interleaved on the same job. Every repetition has >1s measured dwell. Run [38677728260](https://github.com/lly8666/wbd-next/actions/runs/38677728260) SUCCESS and same CODE SOURCE **11/11 Actions SUCCESS**, including R1 kernel, R2, R0 ABI, Governance and cross ABI compile-only.

| Microbench | Three-run source-exact median | Three-run p99 median | Rate CV |
| --- | ---: | ---: | ---: |
| ChaCha20-Poly1305 seal + HP + AEAD open + verified unique PN replay, business payload1000B, 2,000,000 records/leg | **599.734 MB/s** | **1.683 µs/record** | **0.205%** |
| Actual Linux UDP `sendmmsg+recvmmsg` 32 × 256B per batch, 20,000 batches/leg | **55.604 MB/s** | **168.937 µs/32-datagram batch** | **0.192%** |

AEAD three rates 599.734/598.740/601.707 MB/s; p99 1.924/1.683/1.673µs. UDP three rates55.604/55.590/55.823 MB/s; batch p99 168.977/168.937/166.002µs. Child cumulative user+kernel CPU per leg, rss metadata and exact measurement artifact zip SHA are in `docs/evidence/M0/P0-long-repeat-and-M3-acceptance.json`. Build artifact11947655063 digest `sha256:0f6931bc14fdfe0eb6e816c9f81490fd4e173c327455e6fb1723556dfc00c41e`, result artifact11947710065 digest `sha256:63cdd6440b60d86cbf22b8bca17073e19c6008ab3dd0e4ec0cb88ed404b0f0b`.

**Limitations:** per-record crypto p99 ≠ 32-packet UDP batch p99 ≠ business first-delivery end-to-end p99. No actual raw AF_PACKET, authenticated production Go V4 cold→Rust owner installation, independent generator/host validation, traffic-loss injection or same-product old/new A/B. Three repeated legs on one hosted runner do not establish production stable CPU capacity or 500Mbps throughput. Product/physical/P1/P2/P3/WinARM native remain NOT_RUN.

## Next M0 atom
Prioritize Go V4 protected-session caller provenance + Rust owner generation and exact old Go PrepareTransition/DetachTransition/CommitAdmission RX/TX boundaries, then raw AF_PACKET product lane; or integrate already accepted worker code with source-exact native Actions. M3 independently carries new FEC cost scoped task; other workers stay on wave4.
