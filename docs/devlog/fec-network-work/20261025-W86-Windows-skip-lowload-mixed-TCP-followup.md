# W86｜暂跳本工位 Windows、保留长 GE 交织负例、继续 Linux 低负载混合 TCP 恢复

2026-10-25，`experiment/fec-network-tuning`。GitHub 入口与本岗 `status.json` 和 Actions 已重新核对：入手 HEAD `ba94fc26681106d4b134fc6bdfa5d1489fdeca75`；没有缺记的新性能结果，W85 负结果和两处产品精确回撤、最终 [40203220219](https://github.com/lly8666/wbd-next/actions/runs/40203220219) 及 [40203220240](https://github.com/lly8666/wbd-next/actions/runs/40203220240) 成功仍有效。整个分支产品源码没有为 W86 再改 FEC 算法或外层恢复。

## 用户本轮 Windows 执行例外

Windows FEC2 native x64 SIMD/codec、Go/Rust FEC2 Windows ABI 与 Wintun 真实数据路径、GUI/配置/打包/Stop/MTU、Windows Game/FEC：**`TEMP_SKIPPED_USER_20261025 / NOT_RUN`**。是用户指定**本 FEC 工位的暂缓队列**，不是 PASS、永久取消、不是把 Linux 等效作 Windows。未编辑 .github/workflows 下任何 Windows/M0 文件、未取消既有 M0 Windows 测试、没有改 M0 Windows 源码或其交付状态。何时重测由用户恢复指令确定；其后必须取 M0 最新 exact source / 正式 Windows native Actions。

同步文件：`docs/testing/FEC_AUTONOMOUS_WORK.md`、`docs/architecture/FEC_V2_TEST_PLAN.md`、`docs/evidence/fec-network-work/status.json`、`docs/evidence/fec-network-work/final-report.md`，及 [本岗暂跳/问题收据](../../evidence/fec-network-work/20261025-W86-windows-temporarily-skipped-and-linux-priorities.json)。

## W85 长 GE 遗留问题并未修好

- 冻结 W83 Maximum6 长 GE 原业务 C→S/S→C ~1.32/1.30% 超 1% 参考门；短 GE 仅 ~0.21/0.20%，相同平均损伤率不同连续长度。
- W85 候选双组同已就绪交替 parity，四行 SIMD 数学编码、无额外 r，ARM64 正确性通过，但在真实 [40202359496](https://github.com/lly8666/wbd-next/actions/runs/40202359496) 同 VM A/B：A 1.3253%/1.1982%，B 1.3903%/1.1936%。实际交替的 parity 仅 1.22%/1.10%；新旧随机 GE trace 不固定，B host PSI 峰32.21%；**无明确收益**。
- 已精确回滚 `v4_fixed_stream.rs` blob `a57f5f4f...` 和 `v4_embedded_go.rs` blob `3cba62da...`；不加 r、不等待 peer、不升级四组、不再刷 seed，严格 1% 长 GE 失败原样保留。未来若有实测逐块可及时恢复却漏交付证据、或独立改动明确用户收益，才重新评估；现在不再把这当待修 encoder bug。

## 其他 Linux-only 遗留及本轮非加压验证

- **真实 FEC 65KiB TUN:** 核对 `crates/wbd-engine/src/v4_embedded_go.rs`：`original_fixed_stage_source` 受 native record payload 上界限制，非 small 的 `jumbo_queue` 在 Fixed/Auto 分支明确拒绝，不能逃逸到普通 kind1；公共 Normal/LINK 65KiB 32+16 两阶段 W57 单测通过**不等于 FEC 65KiB 支持**。标 OPEN / NOT_RUN / 现有 Fixed jumbo 不支持，不在本轮绕过 FEC 写普通 record 或扩 FEC 协议。
- **持续远端 RX 宿主容量质量信号**仍 OPEN，不把本地 W61–W76 自身过载实验当远端 receiver PASS。
- **真实外层 repair ON + FEC 最新统一源码组合**仍 OPEN，不修改他岗 outer RACK/PTO/shadow。
- **历史 W49/W50 100Mbps 混合 TCP 恢复回压**仍 inconclusive：W49 Fixed2 高损后两向 TCP 注入仍不足、W50 Balanced3 高损后恢复阶段业务 TCP 延迟明显。100Mbps 随宿主容量停止条件不继续重跑。

为进一步隔离高载主机/本地 FEC 的原因，仅补一个**低负载**固定档回归：`tests/network/fec-work/W86-balanced3-8m-TCP-recovery-original-arm64.json`。复用生产二进制 exact source `4322a811fd63e096458f202767faa2f097a587c0`，ARM64 build [40203220219](https://github.com/lly8666/wbd-next/actions/runs/40203220219)，artifact `12602931174` ZIP SHA256 `0ae0939bdd4c02932a6452260fa65f4e1851bf37bd79d7485c28e1895022f125`。与 W50 相同 Fixed Balanced3、双向 96% UDP/4% 两条 TCP、包型 64..1287B、300ms 单程、IID10% 30s→30% 60s→10% 30s、外层 DATA retransmits 实际 OFF；只把**每方向应用 offered 100→8Mbps**，不是升高容量。一个网络性能 Action 一个测量 job；明确 `netem_rng=unseeded_recorded`，不与跨 VM 历史数字做 CPU 因果比值。

Action [40204401717](https://github.com/lly8666/wbd-next/actions/runs/40204401717)，合同 [40204401670](https://github.com/lly8666/wbd-next/actions/runs/40204401670)。继续保持 10% baseline/recover 每方向 UDP 和小包 ≤1%，小包 p99≤500ms，M2 native authentic positive、所有源 TUN 根队列 drops 0，禁止外层 DATA retransmission。**若低负载通过，只能说明当前配置较低负载的恢复正常，不代表 W49/W50 100Mbps 已修复；若失败，保留确切失效阶段、TCP真实注入/backpressure 与宿主 PSI。** 本页写于测量执行期；最终以真实 Action、artifact、report/status 中的结论为准，不能预报结果。

## W86 真实结果：低负载不能消除 TCP 回压

[Action 40204401717](https://github.com/lly8666/wbd-next/actions/runs/40204401717)，唯一测量job失败，`result=INCONCLUSIVE`：两方向 Stable10%/recover10% UDP各 ≤1% 低损门，但 TCP high30% 期间两向目标0.320Mbps，实际注入0.1457/0.1547Mbps，主TCP p99 **21477/16942.8ms**，backpressure **2186/1233**；损伤解除后 C→S注入0.3095 Mbps、p99 7454.7ms（回压30），S→C注入**0.2770** Mbps、p99 2902.8ms（回压179）。原始 TCP missing-after-drain 两向均0，说明最终到达不等于速率/时效性合格。全部阶段原生M2 authentic positive 双向成立、Fixed3 requested1/applied1、outer DATA0、parity planned==sent（client 101972 / server102162）、TUN源/rx容量/root队列drop0、TUN failed0；**server RX conflicting/rejected source 1**，非0，尚无证据证明与长延迟因果相关。CPU PSI peak **0.42%** / mean0.10%，client/server 120s测量CPU 13.35/13.28s，RSS峰22.78/22.96 MB。netem真实高损29.94%/29.89%；正常 UDP约7.68Mbps，而高损 UDP约6.83/6.82 Mbps，Fixed3残余有条件解释内层TCP的大量 RTO/HOL，不是直接认定codec bug。

所有原始数据、分组阶段计数与SHA256在 [W86 原始收据](../../evidence/fec-network-work/20261025-W86-balanced3-8m-TCP-highloss-recovery-INCONCLUSIVE.json)。Action artifact 12603890171，ZIP SHA256 `785c061807f17df193121bed8c8621bf575614d8bdb45329f6f0465518721f3c`。与 W50 相比仅是较低业务负载的再现，**不能声称100Mbps宿主已通过或残余原因完全等同**。本岗位不加大负载。

为区分是 Balanced3 的有限 r 不足，还是最高档也有类似内层TCP恢复问题，仅授权一个相同业务/网参数的 Fixed Maximum6 低负载 [W87 请求](../../../tests/network/fec-work/W87-maximum6-8m-TCP-recovery-original-arm64.json)，Action [40204822076](https://github.com/lly8666/wbd-next/actions/runs/40204822076)，`seed=820087`、`netem_rng=unseeded_recorded`。两 Actions 不在同 VM，**只能作机制/功能定性参照，不能作可归因CPU AB**。结果未出之前，不预测通过或降低高损门槛；继续保持 Windows TEMP_SKIPPED/NOT_RUN。
