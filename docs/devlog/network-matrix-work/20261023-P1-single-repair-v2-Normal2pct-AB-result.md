# 2026-10-23 P1 single-repair-v2 2% Normal same-VM AB — measured FAIL

**Frozen source**: request commit 5890776f85a34373bc0c71ebdea43df97f59e52a. One and only one automatically triggered real business Action [39907046412](https://github.com/lly8666/wbd-next/actions/runs/39907046412), run attempt1, artifact **12481288207**, artifact ZIP SHA256 `0c7aec24ca52b6d8fb7e60943d08eebcfb69755d1634f90a316cf56cd8d06b41`. [Harness contracts 39907046737](https://github.com/lly8666/wbd-next/actions/runs/39907046737) passed. Two frozen native bundles verified before same-VM sequential AB: A=f8b29e legacy two repair (native39902074456 artifact12479730545); B=e430951c v2 one repair (native39906119466 artifact12480718285, 75/75 recovery and MTU9 PASS). No product rebuild in performance run.

**Actual request**: original Normal 2% loss bidirectional, 200ms one-way, 60s steady seed5205, 2Mbps each direction, UDP/TCP 50/50 with 99% 1287B + 1% 64B UDP packet count, 4 TCP streams, outer1500, no fragmentation, 10s warmup/30s drain, unseeded recorded netem, fixed 32768 netem queue. *Strict v2 UDP residual gate <=0.25%.* A is a baseline under the current v2 gate and is not requalified as new policy.

| Cohort (each direction 5884 offered UDP packets) | A legacy | B one-repair |
|:--|--:|--:|
| C→S UDP missing | 156 (2.651%) | 146 (2.481%) |
| S→C UDP missing | 175 (2.974%) | 149 (2.532%) |
| C→S TCP delivered/missing | 5884 / 0 | 5884 / 0 |
| S→C TCP delivered/missing | 5781 / 0 | 5808 / 0 |
| C→S TCP p99 | 5322.7ms | 4489.8ms |
| S→C TCP p99 | 5609.8ms | 5962.4ms |
| Client CPU over 60s | 1.84s | 1.75s |
| Server CPU over 60s | 1.86s | 1.77s |

B real output authenticated policy readback on both endpoints: `outer-single-repair-v2`, exactly 1 repair, shadow logical slots131072, retain cap1500000us. No injection-rate failure, send error, EMSGSIZE, kernel UDP error, duplicate delivery, or orphan owned network namespace. Both process Stop readbacks PASS. B client owner: first candidates682, repair accepted513, quota retired169, capacity blocks0, max repair queue age153us, uncertainty0. B server: candidates682, accepted510, quota retired172, capacity0, max age120us, uncertainty0. The user-mandated hard single-repair retirement holds, but **does not imply successful business recovery**.

B observed netem loss about 1.970%/1.934%, A ~2.155%/1.856% (not exactly same per-packet impairment); B CPU PSI some peak41.15% with no steal, A had none. This is a caution against causal CPU claims, **not** grounds to excuse the product's 2.5% UDP loss. One-run CPU cost improvement ~5% is descriptive only. B UDP first-arrival p50 200.2ms but p99 ~639–642ms; TCP p99 remains multi-second. No low-latency, cross-business HOL, 500Mbps, or production capacity qualification.

**Disposition (failure actively investigated, not a green report):** 341 quota-abandoned candidates across B endpoints imply hard quota denies a meaningful subset (about25%) of 1364 candidate events. They cannot alone be equated to UDP application losses: some candidates may be false positives from lost auth receipts; observed actual useful repairs, spurious repairs, per-epoch quota timing and RX delivered-after-repair are **NOT_OBSERVED**. A blind increase to the 10% cap, PTO retuning, or second-repair rearm violates the evidence/decision constraints. Do not repeat exact seed5205 or blame VM. The next *information-gaining* option is bounded, authenticated M2 metadata + owner quota-epoch accounting (no per-packet logging, new hot allocator/lock/poller) correlated with M4 actual completion and real RX/TUN first delivery, then only a causal minimum fix and independent Action. Current product remains a native/MTU functional PASS but business FAIL.

Structured facts: `docs/evidence/network-matrix-work/P1-single-repair-v2-Normal2pct-AB-FAIL-20261023.json`. Archived raw evidence: GitHub Actions artifact12481288207. Historical model's `two_retry_ideal_at_5pct` in result.json is NOT current v2 qualification; actual readback + loss gate govern.
