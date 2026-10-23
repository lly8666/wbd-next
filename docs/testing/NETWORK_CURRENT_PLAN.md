# 独立网络测试：当前生效计划入口

做什么以本页决策为准，做到哪里只读任务分支 `docs/evidence/network-matrix-work/status.json`，长期职责与提示词见 [NETWORK_AUTONOMOUS_WORK](NETWORK_AUTONOMOUS_WORK.md)。计划不是实现收据，不重置已完成工作或重跑旧流程。

## 当前决策

1. [机会式外层重传、统一MTU与真实性能验收 v3](../decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md) 是最新授权。实施V3-A→B→C→D：取消低损快速恢复SLA及持续DATA RACK/PTO猜测；30%标准高负载R/C至少6%、R/F最多10%的分母约束、无损近零重传、UDP残余无下限、单流TCP500Mbps/200ms/0损、混跑无跨业务HOL、同机CPU与MTU闭环。具体数学、工程初值、边界和验收均在该决策，不在提示词复制参数。
2. [容量模型](NETWORK_CAPACITY_ENVELOPE.md)、[网络矩阵](NETWORK_MATRIX_20261022.md)、[夹具](NETWORK_HARNESS.md)、[诊断](NETWORK_TRIAGE.md)保留通用方法；旧v2数值/模型不得用于新v3产品，工具同步是新工作包的一部分。[旧一次修复](../decisions/NETWORK-ONE-REPAIR-20261023.md)仅解释历史源码和证据。
3. 本次是方案交付，不改运行请求、不dispatch、不宣称产品或工具已经支持v3。接手者先处理在途结果并留旧policy事实，再开发；status中“不开始opportunistic”的旧建议已被本次用户授权覆盖。

## 并行边界

本岗位独立处理外层机会式重传、Normal/off TCP/UDP、共享MTU与容量修复。`experiment/fec-network-tuning`在关闭外层DATA重传下处理FEC固定/auto的恢复与成本，不重复它的矩阵、不修改其状态；共享预算接口改动保留独立可集成提交，后续做必要组合验收。M0继续自己的Windows接线，不必等它才测Linux，也不覆盖它的并行工作。

## 当前起点与收口

先从status和最新Git/Actions核准实际产品，保留已验证的M1源TUN丢包修复。旧0损10M通过不等于500M通过；旧有损TCP1未满速如实保留，不再围绕已取消的低损满速目标循环调窗口。旧run按旧标准结算，新run明确v3 readback。

每次推进一个完整能力：缺什么补什么，不从第一步重做。单性能Action单一配置/seed/预声明波形和一个测量job；A/B同VM顺序，独立场景可并行；容量不足停止更高资源测试并解释。源码修复后只测原反例、相关硬门和代表性能。已满足代表覆盖就交付，未跑/受限/需要平台接线的范围如实保留。
