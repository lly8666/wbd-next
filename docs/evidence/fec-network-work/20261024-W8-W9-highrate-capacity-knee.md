# Maximum FEC 50/75 Mbps native ARM64 capacity knee (2026-10-24)

Branch `experiment/fec-network-tuning`; **product SOURCE `b601f2e546bf5f071eb33a80a01beec71d91c5cf`**, successful build run [40078403217](https://github.com/lly8666/wbd-next/actions/runs/40078403217), artifact 12554277143. Later Auto-source ARM64 build actions were not completely green; do **not** attribute these results to new source. Independent test requests [W8](../../../tests/network/fec-work/W8-capacity-p050-fixedmax30-300ms-arm64.json) and [W9](../../../tests/network/fec-work/W9-capacity-p075-fixedmax30-300ms-arm64.json), one performance Action per test. No original networking `next_action` or status changed.

Config both directions: fixed Maximum profile6 requested=applied1, outer data repair OFF verified, actual repaired DATA=0, real parity and TUN recovery; 30% IID netem, one-way300ms, 99% 1287B/1% 64B UDP by packet counts; ARM64, MTU1500, queue32768, warmup15s + **measured30s** + drain30s. Outer netem rate per direction 200Mbps on W8 / 300Mbps on W9, to avoid artificially limiting large parity traffic.

| Metric | W8 50Mbps client→server / server→client | W9 75Mbps client→server / server→client |
|---|---:|---:|
| Action | [40082173102](https://github.com/lly8666/wbd-next/actions/runs/40082173102) | [40082494664](https://github.com/lly8666/wbd-next/actions/runs/40082494664) |
| Result artifact | 12555543008 | 12555971940 |
| Injected business Mbps | 50.000 / 49.999 | 75.000 / 75.000 |
| Delivered cohort Mbps | 47.817 / 48.041 | 66.30 / 67.13 |
| Residual loss | **4.360% / 3.905%** | **11.52% / 10.42%** |
| Delivered-only first p99 ms | 304.7 / 304.7 | 303.6 / 303.7 |
| CPU seconds per process during30s, client/server | 12.31 / 12.29 | 15.37 / 15.42 |
| Peak process RSS MB, client/server | 29.18 / 28.66 | 32.77 / 32.63 |
| Outer veth TX Mbps *after* netem, client/server | 86.86 / 87.02 | 130.19 / 129.94 |
| Native first-wire Mbps *before* netem, average whole45s | 122.48 / 122.47 | 183.61 / 183.61 |
| Netem actual loss %, client/server | 30.079 / 29.926 | 30.004 / 30.088 |
| FEC decoder rejected, client/server (whole run) | **18,766 / 19,038** | **71,229 / 71,196** |
| FEC recovered-to-TUN client/server | 65,655 / 65,704 | 91,952 / 93,079 |
| Tun source drop / outer DATA repair | 0 / 0 | 0 / 0 |

Both **FAIL** the stated ≤1% FEC-only business residual, despite accurate injection, no TUN/qdisc source drops, zero external DATA retransmits, no host steal and CPU PSI below20. Historical W5 12Mbps same product/30%/300ms [40079244149](https://github.com/lly8666/wbd-next/actions/runs/40079244149) had decoder rejected=0 and residual 0.081/0.064% (duration60s; not a strict equal-window A/B).

Strong static-capacity suspect: `crates/wbd-engine/src/v4_fec2_live_rx.rs` contains `MAX_ACTIVE=32`, `MAX_STORED_BYTES=1MiB`, `MAX_BLOCK_AGE_NS=150ms`, and `BLOCK_REORDER_SPAN=128`. On a new block when >=32 active it evicts the oldest incomplete block; `ReceiveError` total is currently not classified by error reason. Approximate candidate k16 arrival rates: 50Mbps 306 groups/s → 46 potentially within150ms; 75Mbps 460 groups/s → 69 potentially within150ms. This predicts RX pressure, not proof each rejected symbol was caused by MAX_ACTIVE. CPU/RSS not first saturated.

**STOP CAPACITY EXPANSION:** 100,125,150,175,200Mbps **NOT RUN**, no fabricated CPU/memory/wire data. Before resuming, instrument low-frequency RX error reasons (`Capacity/Invalid/ConflictingBlock/Codec`), active/stored high-water and evicted ages, minimally correct RX bounded capacity on original 50Mbps counterexample, perform new successful exact-source ARM64 build, then step upward while usable. Do not rewrite outer retransmit, do not mask FEC parity, do not alter other role status.
