# 独立网络测试：当前生效计划入口

做什么以本页决策为准，做到哪里只读任务分支 `docs/evidence/network-matrix-work/status.json`，长期职责与提示词见 [NETWORK_AUTONOMOUS_WORK](NETWORK_AUTONOMOUS_WORK.md)。计划不是实现收据，不重置已完成工作或重跑旧流程。

## 当前决策

1. [机会式外层重传、统一MTU与真实性能验收 v3](../decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md) 是最新授权。实施V3-A→B→C→D：取消低损快速恢复SLA及持续DATA RACK/PTO猜测；30%标准高负载R/C至少6%、R/F最多10%的分母约束、无损近零重传、UDP残余无下限、单流TCP500Mbps/200ms/0损、混跑无跨业务HOL、同机CPU与MTU闭环。具体数学、工程初值、边界和验收均在该决策，不在提示词复制参数。
2. [容量模型](NETWORK_CAPACITY_ENVELOPE.md)、[网络矩阵](NETWORK_MATRIX_20261022.md)、[夹具](NETWORK_HARNESS.md)、[诊断](NETWORK_TRIAGE.md)保留通用方法；旧v2数值/模型不得用于新v3产品，工具同步是新工作包的一部分。[旧一次修复](../decisions/NETWORK-ONE-REPAIR-20261023.md)仅解释历史源码和证据。
3. **历史交接说明（2026-10-23）**：当时仅方案交付，不改运行请求、不dispatch；该限制**不再描述当前已授权执行阶段**，不得覆盖用户随后明确授权的产品修改和 Actions。最新实际运行进度及动作以任务分支 `status.json` 和严格 Actions 证据为准；旧“不开始opportunistic”的建议已被v3授权覆盖。

## 并行边界

本岗位独立处理外层机会式重传、Normal/off TCP/UDP、共享MTU与容量修复。`experiment/fec-network-tuning`在关闭外层DATA重传下处理FEC固定/auto的恢复与成本，不重复它的矩阵、不修改其状态；共享预算接口改动保留独立可集成提交，后续做必要组合验收。M0继续自己的Windows接线，不必等它才测Linux，也不覆盖它的并行工作。

## 当前起点与收口

先从status和最新Git/Actions核准实际产品，保留已验证的M1源TUN丢包修复。旧0损10M通过不等于500M通过；旧有损TCP1未满速如实保留，不再围绕已取消的低损满速目标循环调窗口。旧run按旧标准结算，新run明确v3 readback。

每次推进一个完整能力：缺什么补什么，不从第一步重做。单性能Action单一配置/seed/预声明波形和一个测量job；A/B同VM顺序，独立场景可并行；容量不足停止更高资源测试并解释。源码修复后只测原反例、相关硬门和代表性能。已满足代表覆盖就交付，未跑/受限/需要平台接线的范围如实保留。

## 2026-10-24 实际执行收口（不是替代 v3 决策）

已回收并结算旧 QUEUED 的两条性能 Actions40047976746/40048710703，不重复dispatch；继续完成**一项**真实原生产品能力：Linux ARM64 Normal/off 显式 opt-in `--tun-fq-maxrate-mbps=600`（默认0不变），只配置拥有的临时 TUN fq 每流速率并严格核对内核 readback，非应用 socket 测试设定/全局 sysctl/Windows/FEC。新原生 build40053179394 SOURCE81881a1d 成功，夹具合同40053463038 PASS，同 VM 单流TCP500/RTT400/0损/线路700Mbps的 [Action40053396971](https://github.com/lly8666/wbd-next/actions/runs/40053396971) **整体FAIL因A默认路径启动 TUN 丢6613**；B产品-owned fq600 **PASS_SCOPED_OBSERVATION**，业务500.000Mbps、p99203.2ms、启动+稳态源TUN0、root fq qdisc0、Stop/认证正常。不能从 B 延伸至默认、FEC、Windows、其它端点/双向或CPU效率。既有v3-A高损/预算、v3-B部分MTU、v3-D混跑/idle继续复用；本轮代表覆盖已收口，未引入新恢复率/UDP下限。确切产物SHA和资源分母、尚未资格范围见 [任务状态](../evidence/network-matrix-work/status.json)、[原生B真实证据](../evidence/network-matrix-work/V3-C-owned-Linux-TUN-fq600-TCP500-real-AB-20261024.json) 和 [报告](../evidence/network-matrix-work/final-report.md)。默认冷启动仍OPEN，不自动合main或部署，不因失败全红反复追测。
