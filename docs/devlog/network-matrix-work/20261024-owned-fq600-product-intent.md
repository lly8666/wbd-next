# 2026-10-24 — V3-C native Linux owned TUN fq600, scoped cold-start repair intent

## Recovery before changes
Latest remote main d8ba2cf270ff6ca5cadae6dab778c49c32636ef6, branch initially 396d7f7f50abb0500e08d597f5466358fd91b9dd, 427 commits ahead/0 behind. No new plan PR supplied. Read AGENTS, PROJECT_CHARTER, NETWORK_AUTONOMOUS_WORK, NETWORK_CURRENT_PLAN, v3 decision and actual Go/Rust TUN ownership chain. Previously queued runs were completed and must not be redispatched:
- [Action 40047976746](https://github.com/lly8666/wbd-next/actions/runs/40047976746), request 31d5a2d1c5cfe5b21b8cbb5b94a679d81d53ed32; artifact12542740290 digest sha256:545e32ba8b7bb9618f3f5b0e364c7d90d259c1aee7c715088e78e63975ee7dd0. A unpaced source TUN warmup local drop6131, 500Mbps steady; B real test socket SO_MAX_PACING_RATE 75000000B/s (600Mbps) readback, kernel TUN warmup+steady drops0, app500.005Mbps, p99203ms, Stop pass. Overall Action FAIL because A FAIL; B scoped test-only PASS, not product.
- [Action 40048710703](https://github.com/lly8666/wbd-next/actions/runs/40048710703), request 396d7f7f50abb0500e08d597f5466358fd91b9dd; artifact12542646899 digest sha256:5614971ff10e87132a8fe60da09114ef9296d97bb74e7fb5f8d6137b0d36143a. A test TUN fq unlimited warmup local drop6249; B kernel test-only per-flow fq maxrate600Mbit root readback, local warmup+steady drops0, actual TCP499.996Mbps, p99202.9ms, original raw/TLS/TUN/Stop pass. Overall FAIL because A FAIL; no default production claim.
- Action40047401954: 6629 TUN startup drops clustered at t~6-7.5s despite 500Mbps steady; CUBIC cwnd~50.75MB vs 25MB BDP, consistent with startup microbursts. More blind TUN queue growth and ingress reader not justified.

## Causal scope and implementation
Design: docs/decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md §5.2. Actual path `r0/go_overlay/internal/v4productcli/linux.go::parse->Run->openTun->NewV4Linux(Client/Server)Product`, with original Go owning /dev/net/tun and transferring its FD to Rust `crates/wbd-platform/src/linux_tun_sink.rs`. Rust nonblocking original source TUN reader and unchanged authenticated M3/M4 are not an app socket pacing controller. Source  a0a1285e73584a99c94eb573e7278ce5716fa2a5 native Go/Rust artifact12540624073 SHA256 f52f3c67749b399fa6778e9031e83a0f93f1fe4780d6836d7d120928b9fed763 already verifies dedicated 512-buffer TUN reader 10Mbps 0loss and v3 highloss 30% budget, while full500 startup strict fails.

Scoped fix: new explicit Linux public CLI `--tun-fq-maxrate-mbps=600` only for Normal/off (default 0 unchanged). Use `tc qdisc replace dev <newly owned TUN> root fq maxrate 600mbit` before product owner transfer; read back actual kernel qdisc and fail closed if unavailable/mismatched; no global sysctl, no arbitrary app socket modification, ephemeral owned TUN cleanup on Stop. Product source commit cf7800bf, automatic exact-native build initially Actions40053171857 / 40053179394 (source81881a after workflow trigger change). Harness new `network.product_tun_fq_maxrate_mbps_profiles` must be different from test-only `tun_fq_maxrate_mbps_profiles`; Go startup marker and separate kernel readback mandatory. Do not relabel older test-only B as product qualification.

A sameVM product A(default) vs B(opt-in) real 500Mbps inner single TCP, 700Mbps outer line per direction, 200ms one-way 0loss/RTT400, window nominal up to64MiB, full 20s warmup+60s steady, 30s drain, qlen1024, one native bundle/source. Strict full-run kernel source-TUN and root-qdisc drops0, actual offered/delivered>=475Mbps and p99<=400ms, auth v3 readback and Stop clean. A may FAIL: whole AB Action FAIL while configured B can be scoped PASS. CPU compare meaningful only at matched real delivered load; never count failed A local drop as lower-CPU success. Native product build is not an end-to-end PASS.

An intermediate harness contract Action 40053188967 failed **only** because a pre-existing qdisc-name test inherited old request's B test-only fq600 maxrate when replacing A with fq_codel. Tests were isolated (commit38ba0f3) and require fresh Actions result. No duplicate pressure run or unbounded queue.

## Actions and status checkpoint (recovered and not redispatched)
- Product native exact frozen source 81881a1df69e6bf0b5fd3f3076e2433bfb442d96, [build40053179394](https://github.com/lly8666/wbd-next/actions/runs/40053179394) completed success, artifact12543904263 ZIP digest sha256:5564a28f4016caba002a38130393cc0e7c13862b631980a8ce7d4eb8611ce749. Another automatic build40053171857 was already in progress from Go file push; it was not redispatched or used for scenario.
- Strict native one scenario request source4cecde55daf10d2213d25e4af77ba5377395b174, [Action40053396971](https://github.com/lly8666/wbd-next/actions/runs/40053396971) attempt1 started (sameVM A/B only, external A fq root unbounded, product B owned fq600 readback, no B external tc override; identical bundle/hash both). Entire Action verdict pending; **no qualification recorded yet**.
- Contract run40053396949 failed because generic preset and old test-only fq contracts inherited request's now product-owned Normal/off B fq600 config. Isolated those tests in source92ea70abb34c99fe6ea789a9d500b7db8da6f380; [contracts40053463038](https://github.com/lly8666/wbd-next/actions/runs/40053463038) completed **SUCCESS**, leaving real measurement untouched. This is a harness fixture scoping fix, not a change to acceptance threshold or product behavior.

## Final real native product A/B — completed Action40053396971 attempt1

Downloaded full Actions artifact12543608967 ZIP and independently verified sha256:e94d703d1d699ae3d5a4b5224aa2fbeeeebbb23010ba2ffdc62a7ae5b8c94375. A/B both verified exact native source81881a1df69e6bf0b5fd3f3076e2433bfb442d96 from successful native build40053179394 artifact12543904263; same VM, same one-way200ms, 0% artificial loss, outer configured700Mbps/dir, one true inner TCP500Mbps C2S, app write32KiB segmented at inner MSS1377, TUN MTU1429, root fq, qlen1024, 20s startup +60s steady +30s drain each leg. Real TLS/Go raw/TUN -> Rust v3 auth, Stop and owned cleanup both good.

| Actual | A unbounded test-selected fq / product default0 | B true product-owned fq600 |
|---|---:|---:|
| TCP application injected/delivered Mbps in 60s | 500.0003584 / 500.0003584 | 500.0003584 / 500.0003584 |
| TCP p99 ms | 203.0 | 203.2 |
| Source TUN kernel startup drop client/server | **6613/0 FAIL** | **0/0 PASS** |
| Steady kernel source TUN drop | 0/0 | 0/0 |
| Full-run TUN fq root drop samples | all0 | all0 |
| Product Go->kernel per-flow fq maxrate readback | product default0 / test-selected fq unlimited | both **75000000 B/s** / product600 |
| Socket SO_MAX_PACING_RATE | NOT_SET | NOT_SET |
| DATA repairs / netem drops / kernel TCP steady retrans | 0 / 0 / 0 | 0 / 0 / 0 |
| CPU seconds per endpoint (steady 60s) | client47.48/server64.29 | client48.66/server64.33 |
| Server CPU seconds / actual received GiB | 18.408 | 18.420 |
| Real v3 policy, TUN M1 2048-slot, Stop | PASS | PASS |
| Qualifier | strict FAIL because source warmup drop | **PASS_SCOPED_OBSERVATION** |

Whole Action marked failure on **A**, not an issue with B. B app 114441 32KiB cohorts sent and uniquely delivered, zero missing after drain. Both observed actual TCP send/receive buffer4194304B; peer advertised snd_wnd median40,108,032B, over 25MB RTT400 BDP; no hidden socket pacing. A is a cold-loss-failed path and must not be taken as a valid cheaper CPU comparison. B client+server112.99 vs A111.77 CPU-s/60s, host CPU PSI some peak30.13%, steal0.0; no standalone low-CPU optimization claim; capacity is real application and not 700Mbps L1. B namespace/policy/kernel qdisc telemetry is present even though raw Go fq marker is privacy-filtered in shipped product-marker subset; harness explicitly verified actual Go ready marker AND kernel live qdisc, result `effective-config.json` records both.

This closes **one complete native Linux ARM64 Normal/off product-owned fq600 opt-in TCP500 scoped capability**, without setting fq600 default and without claiming physical/Windows/FEC, Game, mixed500, dual TCP500, broad MTU and shared endpoint resources. Previously v3-A highloss30% standard R/F8.878/8.870 R/C6.457/6.451 and zero source TUN, native Normal/off 1500/1280 MTU and scoped mixed/idle results retained. Default unpaced source TCP slowstart still has6613 real startup TUN drops; explicit OPEN and no additional blind queue pressure, tuning or repeated dispatch. All new tests ran Actions, no main merge.

Exact evidence: `docs/evidence/network-matrix-work/V3-C-owned-Linux-TUN-fq600-TCP500-real-AB-20261024.json`; compact `status.json`; existing `final-report.md`. Current next action is scoped delivery, not another test. Source commit and native runtime qualified only under opt-in.
