# M0/H2305 — Overall acceptance: original inner TCP 2 / 8 / 16 MiB, 400ms, 0 / 1 / 5% loss

Date: **2026-11-22**. Result: **PRODUCT / MAIN PROMOTION NOT APPROVED (FAIL)**. Narrow test evidence only: **0% kernel-netem original Win→ARM signed Go TLS/Rust A/B/A′ workflows pass; 1%/5% original TCP workloads fail in A before any B/A′ comparison.**

This report is an acceptance **decision**, not a release assertion or a runtime change. It preserves H2304 raw per-job evidence; failure is not transformed into NOT_RUN or PASS.

## Source and evidence lock

- Experiment source: `ac03b42143357059995bd51291c109ffb6d66641`; 0%-loss static isolation fix: `5a29cd2934ff4066ba48e1f56ba1a6892e1cf30c`; H2304 devlog: `4c1ae6d9f42637677ff8a81da8ff9b171e3e9040`.
- Main **unchanged**, at review `04bcd74fb8c8aa2567e10c8db806d92f703a88ed`, protected. Experimental PR #68 remains **draft**, **not merged**, with merge conflict (mergeable_state=dirty).
- **Original archived product binaries**: Windows original Go exe from source `c5066db61fc51bafd7c2ad2def3029e615efa777`, Windows Rust DLLs from `dc2da4b98ecc419a67e3e2ee6530f944b78d88ef`, original ARM Go/Rust product from `97db898f3a1fbebcdeea7f2a1b9d9c3dfcd32573`. Exact archive hashes and same DLL SHA across three legs validated by the workflow. The test code intentionally **does not claim product compilation matches current branch**.
- Scope: original signed Windows2025 Npcap/Wintun + Go TLS/Rust → real ARM Linux kernel relay with two egress netem directions (200ms per way) → original ARM Linux Go TLS/Rust TUN native kernel TCP. Four parallel sustained bulk TCP flows and 160 sparse echo samples per leg. OS per-test socket buffer set/readback on Windows, actual ARM accepted TCP socket readback, per-leg original Stop. FEC OFF and single-copy outer presentation repair OFF, no default change.
- The `SO_SNDBUF`/`SO_RCVBUF` setting is a test application's real kernel socket option, not a universal production OS TCP autotuning policy, not a demonstration of effective `cwnd`, and not the outer FakeTCP advertised window.

## All 6 workflows — acceptance status

| True inner kernel TCP A/B/A′ (MiB) | 0% per way | 1% per way | 5% per way |
|---|---|---|---|
| **8 → 2 → 8** | [44984376649](https://github.com/lly8666/wbd-next/actions/runs/44984376649) **PASS** (9/9 jobs) | [44984321085](https://github.com/lly8666/wbd-next/actions/runs/44984321085) **FAIL** (A timeout) | [44984321166](https://github.com/lly8666/wbd-next/actions/runs/44984321166) **FAIL** (A timeout) |
| **16 → 8 → 16** | [44984376588](https://github.com/lly8666/wbd-next/actions/runs/44984376588) **PASS** (9/9 jobs) | [44984321079](https://github.com/lly8666/wbd-next/actions/runs/44984321079) **FAIL** (A timeout) | [44984321196](https://github.com/lly8666/wbd-next/actions/runs/44984321196) **FAIL** (A timeout) |

Both 0%-loss jobs use commit `5a29cd2934ff4066ba48e1f56ba1a6892e1cf30c`; the four failing loss jobs use `ac03b42143357059995bd51291c109ffb6d66641`. The 0%-only fix isolates historical static-unit FEC environment; actual FEC runtime is OFF for all stages and the actual kernel netem remains **200ms per way even at 0% loss**.

## Real 0% loss data (actual receiver goodput Mbps / valid sparse echo P99 ms)

| Contrast | Independent group | A | B | A′ | B throughput vs mean(A,A′) | B P99 minus mean(A,A′) |
|---|---|---|---|---|---:|---:|
| 8/2/8 MiB | a | 162.452 / 579 | 113.180 / 532 | 134.798 / 563 | −23.85% | −39 ms |
| 8/2/8 MiB | b | 157.088 / 547 | 121.689 / 485 | 147.650 / 516 | −20.14% | −46.5 ms |
| 16/8/16 MiB | a | 84.458 / 547 | 160.471 / 562 | 155.303 / 531 | +33.86% | +23 ms |
| 16/8/16 MiB | b | 110.279 / 641 | 94.589 / 547 | 99.099 / 734 | −9.65% | −140.5 ms |

**Direct original Windows job log links** (each contains all three `H2293_REAL_WINDOWS_FEC2_LEG_PASS` JSON receipts): [8/2/8 a](https://github.com/lly8666/wbd-next/actions/runs/44984376649/job/137092945189), [8/2/8 b](https://github.com/lly8666/wbd-next/actions/runs/44984376649/job/137092945128), [16/8/16 a](https://github.com/lly8666/wbd-next/actions/runs/44984376588/job/137092919033), [16/8/16 b](https://github.com/lly8666/wbd-next/actions/runs/44984376588/job/137092919011). The corresponding run artifacts include `h2276-{a,b}-client-result`, `h2276-{a,b}-arm-evidence` and `h2290-{a,b}-original-windows-hotpath-raw-evidence` with stage JSON and raw logs. All 12 legs read back the requested actual Windows TCP bulk socket byte capacity (2, 8 or 16 MiB), exact bidirectional kernel netem **zero injected drops**, FEC OFF, zero original frozen ciphertext outer repair packets, valid 160 echoes, real receiver byte count, and original WAL Stop PASS; all jobs, including ARM-side accepted socket readback and owned cleanup, passed.

Interpretation: at zero injected loss, shrinking 8→2 MiB improves measured sparse P99 in **both** independent groups but costs **20–24% actual bulk goodput**; 16→8 MiB A/B/A′ effect is **inconsistent across groups**, and P99 also trades off differently. The dataset cannot recommend a single global 2/8/16 MiB default. Best measured 0%-loss leg is **162.452 Mbps**, not 400 Mbps; the user 400 Mbps target is specifically at **5% loss** and remains unqualified.

## 1% and 5% loss: failed in A, no B/A′ evidence

All **eight Windows client jobs** (2 independent groups × 2 contrasts × 2 loss levels) report exact original product start and native signed drivers, qualified DIRECT underlay preflight, then first-leg `H2286_CLIENT_ACTUAL_WINDOWS_ORIGINAL_RESULT FAIL_H2286_ORIGINAL_PRODUCT_OR_HARNESS_EXACT_FIRST_STAGE` with `H2271_REAL_TCP_CLIENT_INCOMPLETE ['TimeoutError:timed out', ...]`. 3–4 TCP worker timeouts per job. Direct log links: [8/2/8 1% a](https://github.com/lly8666/wbd-next/actions/runs/44984321085/job/137091556138), [1% b](https://github.com/lly8666/wbd-next/actions/runs/44984321085/job/137091556142), [8/2/8 5% a](https://github.com/lly8666/wbd-next/actions/runs/44984321166/job/137091563413), [5% b](https://github.com/lly8666/wbd-next/actions/runs/44984321166/job/137091563378), [16/8/16 1% a](https://github.com/lly8666/wbd-next/actions/runs/44984321079/job/137091551220), [1% b](https://github.com/lly8666/wbd-next/actions/runs/44984321079/job/137091551203), [16/8/16 5% a](https://github.com/lly8666/wbd-next/actions/runs/44984321196/job/137091632205), [5% b](https://github.com/lly8666/wbd-next/actions/runs/44984321196/job/137091632197). The true ARM servers failed to complete the triplet while the original Windows clients timed out.

**Do not** substitute sparse echo survivor-only P99, socket setsockopt readback, outgoing enqueued bytes, previous zero-loss goodput, or kernel netem configuration for completed 1/5% receiver data. The 1/5% A baseline is **FAIL** and B/A′ are **NOT RUN**, so there is no valid window-comparison goodput or P99 at loss. Correlation does not yet prove loss location/root cause (inner OS cwnd/RTO, outer packet drops, queue overflow, Rust TX pacing, or CI fixture) — collect trace before changing architecture.

## Overall acceptance gates

| Gate | Status | Basis |
|---|---|---|
| Six workflows source/static, original archive SHA check | **PASS** | All 6 static jobs pass; both 0% workflows all 9/9 jobs |
| 400ms / 0% original Win→ARM kernel TCP; FEC OFF; repair OFF | **PASS — SCOPED TEST** | 2 workflow triplets ×2 independent groups, all 12 legs, 160/160 sparse echo and owned Stop |
| 400ms / 1% real original TCP finished | **FAIL** | 4 independent first-leg A timeouts; B/A′ not run |
| 400ms / 5% real original TCP finished | **FAIL** | 4 independent first-leg A timeouts; B/A′ not run |
| 5% loss ≥ 400Mbps receiver goodput | **FAIL / NOT DEMONSTRATED** | TCP A incomplete, no qualifying delivered bit-rate |
| 20% loss ≥ 150Mbps receiver goodput | **NOT RUN** | No qualified H2304 20% case |
| TCP P99 improved without throughput regression at loss, including missing echoes | **NOT QUALIFIED** | No completed lossy echo denominator; 0% gains trade off against throughput |
| Actual per-flow OS window configuration in **production** Linux/Windows app-owned sockets | **NOT IMPLEMENTED / NOT QUALIFIED** | H2304 tweaks explicit test app socket; real Linux/Windows user programs own inner TCP |
| Normal FEC ON / Game / Windows as server / Linux as client / x86 + ARM matrix | **NOT RUN** | H2304 qualified only Windows client and ARM Linux server, FEC OFF |
| Main promotion and PR merge | **BLOCKED** | Main unchanged and protected; PR #68 draft with merge conflict |
| Owned Stop at 0% | **PASS, scoped** | Each 0%-loss job succeeds through clean Stop/readback |
| Owned Stop after lossy first-stage failures | **NOT FULLY QUALIFIED** | Workflow cleanup runs, but no complete three-leg owned Stop receipts; do not conflate test cleanup with successful authenticated product Stop |

### Required closure before promoting to main

1. Under single archived signed Win→ARM original product at 400ms, **1%** loss first, capture true inner `TCP_INFO` on Linux accepted socket (cwnd, retransmissions, RTO, RTT, rwnd/sndbuf), actual Windows TCP socket telemetry, TUN ingress/egress and Rust TX queue/drop/readback, and both relay netem drops. Never replace inner kernel TCP with fake outer reliability.
2. Determine why A stalls before testing windows B/A′. Fix actual per-flow cause with explicit resource budget/owner and reversible Stop; preserve Go TLS cold bootstrap, Rust steady-state and opportunistic-only FakeTCP outer.
3. Re-run matched original product 0/1/5% 400ms A/B/A′, including **missing echo timeout count** (not only survivor P99), CPU/GiB, 160 expected echo denominator and zero-loss negative control.
4. Separately qualify **20%/150Mbps**, Normal FEC ON/OFF, Game and Linux/Windows client/server x86/ARM; qualify production OS TCP autotuning per owned socket or isolated namespace, **not** a global change.
5. Only after positive full current-source independent product evidence, prepare merge to protected main with audit/rollback. No main changes in this report.

**Do not treat this H2305 acceptance report as release PASS.**
