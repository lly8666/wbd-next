# W25 FEC Maximum150 same-M4 batch two-quanta A/B intent

Source baseline new B=cf00a47c9564d67b15409d50178a956416227a8a. Old product build Action40105262367 artifact12564910143 ZIP sha256 39809b55b380b4a161f47b367f734c2e45efa526efc36817e3ac6eb500c21d03. W24 same-VM Action40105506052 returned FAIL on both legs, new B residual1.642/1.826%, Parity gap8.04/9.06% and CPU client23.98/server24.32s/30s. Capacity stop remains true.

Mathematically 150Mbps/1287B ~14569 packets/s, k16/r20 Maximum means ~910 full jobs/s and 5 native <=4-row quanta per job. Product previously does one M3 quantum per M4 staged syscall even when current 32-record M4 batch contains headroom. This causes 5 separate M4 sync settlements per full block and raises probability that parity exceeds its 10ms post-close TTL in host PSI>20% (all samples W24). Before changing expiry, allow at most **two** consecutive <=4-row quanta of the same job, only after original DATA source staging and when >=8 current M4 packet slots remain. A single M4 definite-prefix settlement resolves 8 distinct parity PNs in order. No duplicate/partial reuse, no source waiting, no extra shared queue, no change to 10ms life or outer recovery. Existing unbounded capacity-higher load STOP continues.

Build/test exact ARM64 source first, then single fixed150Mbps outerOFF 30%IID 300ms original fq600 owned static neighbor same VM sequential A=cf00a47c and B=new source. Business <=1% both, original DATA source M4 copies, parity rplanned/rsent, expiry, RSS CPU and p99 are gates. If both fail, stop and instrument narrower phase timestamps (no fake success or seed retries). Full Auto dynamic remains OPEN; no main merge.

## W25 outcome observed

## 2026-10-24 W25：Parity 两个4行量子共用一次M4，150Mbps新源码限域通过

针对 W24 150Mbps 每侧失发 Parity 8–11% 和每秒910+个满块的 5 次 sendmmsg/结算，FEC-only 原生修复在一次 owner turn 先密封所有新 DATA，再只在空余≥8个M4 record槽时将**同一个** ParityJob 的两个≤4行原生M3量子一起密封，原生 M4 同一 syscall 按PN顺序归责；否则仍使用旧的≤4行单量子。代码 commit [aab45f7c](https://github.com/lly8666/wbd-next/commit/aab45f7cc304c09065e3614d0b5c61cff2097b56) + [ab7ea894](https://github.com/lly8666/wbd-next/commit/ab7ea894100f245d6a510137282736781bd017ce)（首个编译尝试原 Rust 二重可变借用失败，修复保留证据）；新精确SOURCE `ab7ea894100f245d6a510137282736781bd017ce` ARM64 build [40108972702](https://github.com/lly8666/wbd-next/actions/runs/40108972702) 成功，产物12565424535 ZIP SHA256 `9bf5b07eee3e90a37a69844b23fb08834c38a9d5781f0f1635c27543bbba7067`。包括 native staged prefix确证、不复发 PN、新 DATA 无阻塞、真实ISA-L和固定/Auto真正内核恢复回归 PASS；Maximum20 行合同40108972687 PASS。

[W25 Action40109234114](https://github.com/lly8666/wbd-next/actions/runs/40109234114) 同 VM **一个场景一个测量 job、A→B顺序**，旧A `cf00a47c`（构建40105262367）/新B `ab7ea894`（构建40108972702）均复用ARTIFACT，不在测量 job 编译。150Mbps **每方向**，原始fq600、Static owned veth邻居，30% IID实际netem 29.98–30.06%，单程300ms、最大档Fixed6 applied、外层真实DATA重传0包0B（parity另算），15秒warmup+30秒measure+30秒drain，双方Stop owned清理，源TUN/root drop0，RX pressure/decoder reject0。结果artifact12565917569 SHA256 `6dae0f82569e28a8c72785c126c1d18a3c6d322538a250b1f287d6f331705683`。

| 指标 | A旧源码（业务FAIL） | B双量子同M4（业务PASS） |
|---|---:|---:|
| C→S净业务/残余 |147.123 Mbps / **1.951%** | **149.938 Mbps / 0.0542%** |
| S→C净业务/残余 |147.379 Mbps / **1.774%** | **149.953 Mbps / 0.0485%** |
| 首次交付 p99 C2S/S2C |311.3/311.2ms | **303.3/303.2ms** |
| client parity rplanned→rsent |830066→745874（缺10.14%） | **830367→829702（缺0.080%）** |
| server parity rplanned→rsent |830066→753112（缺9.27%） | **830361→829936（缺0.051%）** |
| queued_expired jobs C/S |985 / 848 | **15 / 8** |
| unknown_capacity C/S |8049 / 7399 | **51 / 31** |
| 30秒进程CPU-s C/S |24.24 / 24.06 | **24.85 / 24.58**（无CPU节省声明） |
| RSS peak C/S MB |49.84 / 49.62 |50.12 / 49.78 |
| 30秒真实veth outer TX C/S Mbps |244.85 / 246.52 | **259.68 / 259.85**（包括更多真实Parity） |
| host CPU PSI peak |27.42% |29.61% |

**结论：** 新 B 150Mbps FEC-only 满足≤1%残余交付且 p99 相比 A低8ms；性能成果是 Parity按时发送与首次交付改善，**不是更低总CPU/总外层带宽**。B 发出了更多真实 Parity，故 CPU-s、外层 TX Mbps略升是合理成本，不能把少发 parity 的 A当作节能资格。整个 Action 按用户验收脚本判 *FAIL（A旧腿失败）*，但 B 腿原生产物 `PASS_SCOPED_OBSERVATION`；与W23孤立通过不同，本次是在旧版同机失败的情形下 B 正向通过，不过仍为一次未固定netem随机序列的AB而不是 BA/持续压测/物理保证。

**容量停止继续：** W25新B宿主CPU PSI峰29.61%、30秒持续高压力，175–350Mbps 继续 NOT_RUN；RX低占用、外层DATA retrans 0不代表宿主CPU可继续加压。Auto真实动态升降档、反馈RTT真实性以及 Windows 和整体合并仍未过；`merge_ready=false`，只改独立FEC分支与自身状态，不接管原network工作包。
