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

## 2026-10-24 后续授权：Linux Normal/off 默认启动 fq600，继续代表工况

用户明确同意把上一轮已通过**显式选项**的 Linux Normal/off owned TUN `fq maxrate 600Mbit`改为**默认启动**，保留 `--tun-fq-maxrate-mbps=0` 明确回退。产品其它 Fixed/Auto/Game 模式沿用当前0默认，不从Normal/off资格推导。实际生效以新 SOURCE、CLI省略参数、Go marker及内核 `tc -d` 双读回为准，验证启动、业务、Stop和CPU/资源硬门；旧 opt-in B PASS 不自动覆盖新默认 SOURCE。授权并未变更 v3 外层重传、R/C 6%、R/F 10%、UDP无残余下限及MTU合同。

本轮其他代表工况依次补：同机产品默认 fq600 对显式回退0的冷启动单TCP500/0损/RTT400（不复用旧A drop作CPU收益）；同SOURCE 50Mbps线路/30% IID/单程300ms高损UDP双向预算及早期交付回归；同SOURCE 500Mbps线路/2% IID/单程200ms近MTU UDP容量（业务Mbps与线路Mbps严格分开，一方向先验证，承载后再决定反向）。已有旧 SOURCE 的V3-A/B/D证明只复用未受改动的核心模块，不充当新默认全工况验证。每个Action单场景，一次构建复用，不改主线。具体执行收据只读 `status.json`。

### 本轮结果收口（2026-10-24）

上述事项已按精确SOURCE结算，**不是待重新dispatch清单**：原生 Linux ARM64 Normal/off 默认 fq600、新增有界 `flow_limit=256` 源码 `601eab251d4819ec82721d05c71e9cea20c11c0b`，单TCP500/0损/RTT400 Actions40056105730、500Mbps外层/2%线路/单向370Mbps近MTU UDP Actions40056093313 **PASS_SCOPED**，全程源TUN/根fq实际drop0、Go+kernel读回及Stop PASS；早先源 `8d5bbdbc` 的标准50Mbps线路/30%双向UDP预算Actions40055272532与15Mbps/向TCP70 UDP30混跑Actions40055680062 **PASS_SCOPED**，不将旧源资格扩展到新源码。原H500真实两次kernel `flows_plimit` drop已定位修复、原FAIL证据保留；两个后来的Action因夹具解析跨行readback在业务前失败，不算产品FAIL。当前 `status.json` 的 `open_requests=[]`，收口结果见既有 `final-report.md`。未做的高率双向/Windows/FEC/Game/实机明确保留 NOT_QUALIFIED，不合main、不额外重复运行。

## 2026-10-24 用户最新授权：Linux 全模式默认 fq600，继续剩余工况

**此条覆盖前文“Fixed/Auto/Game保持0默认”的旧范围决定。** 用户要求 fq600 在**所有工况**默认生效：本岗位实际接线为原生 Linux Go 公共V4支持的 `normal`、`fec-fixed`、`fec-auto`、`game2`、`game4` 五种模式，共用产品独占临时TUN上的 `fq maxrate 600mbit flow_limit 256`；不碰宿主物理口/全局/sysctl，不自造 Windows `tc` 能力。省略CLI自动=600，`--tun-fq-maxrate-mbps=0`为所有模式的明确回退；失败时拒绝虚假成功，完整 Stop/owned 清理。所有模式必须读回Go与真实内核设置；未实际通过原生Actions的模式不得冒充产品性能资格。

任务分支独立完成最小修改及合同，冻结新的原生ARM64产品SOURCE后，**一个模式/网络波形一个Action**，独立先测 FEC Fixed/Auto 的真实Go→Rust→TUN，Game2/Game4 真实多lane+损伤；从成功的Frozen bundle复用，无需重复编译。按工况保留各自原生成功/失败结论、业务丢包/首次交付、每流fq与原TUN队列真实drop、产品CPU/内存、认证/Stop；高损预算仅在v3标准50Mbps线路/30%充分负载场景检验6%/10%，不能拿低负载FEC/Game测它。此前Normal/off TCP500/H500结果属于**旧SOURCE `601eab25`**，不自动升格为此次全模式源码。若产生已有产品安全或数据流FAIL，最小定位后修复及相关回归；不重复压力刷全绿、不合main、不部署实机。实际run/产物与下一动作以状态JSON为准。

## 2026-10-24 中断恢复后：高低损独立多业务无 HOL 真实结算

最新用户明确要求恢复中断继续，检测**高/低真实丢包下业务间无交付阻塞**。原有状态全部结清，且新原生产品源码保持 `1c43b69a15e4eb9cb38e5662e34c0b106c18981d`（所有Linux公共V4模式TUN默认fq600/flow_limit256，非Windows），没有重复编译。夹具新增**只在请求中显式打开**的独立两条TCP实际 socket+UDP 双向10ms 交付/注入收据，按损伤阶段跳过前2秒/尾1秒，严格以100ms受保护UDP和所有业务共同零交付为检查线；内层TCP自身单连接重传HOL不冒充隧道跨业务HOL。启动与稳态TUN/根fq本地drop必须0，Go/kernel fq readback、原生认证、Stop保持真验。三个损伤场景分别一份精确 SOURCE Actions，所有实际业务执行在 ARM64 Actions。

- [低损2%/单程200ms Action40065824207](https://github.com/lly8666/wbd-next/actions/runs/40065824207) 与 [高损30%/单程300ms Action40065834480](https://github.com/lly8666/wbd-next/actions/runs/40065834480)：**UDP和所有业务共同10ms交付空洞最大0ms**；双向均每5700个稳定内部10ms检查桶都有 UDP 真收包，且两条独立TCP socket有真收据。不过各自 TCP因内层传输拥塞/有序等待，无法注入/交付请求10.5Mbps、23.59Mbps/dir，故两个整个业务场景严格**INCONCLUSIVE**，不把UDP跨业务保护升级为全业务性能PASS。全程本地TUN/fq0、认证及Stop正常；高损R/F8.76%，R/C1.94%不满足原典型全UDP充分负载公式的前提，不宣称6%下限。
- [独立较低 RTT 校准 Action40066158628](https://github.com/lly8666/wbd-next/actions/runs/40066158628)：**PASS_SCOPED**，1% IID/单程25ms，双向每方向真实请求6Mbps（双TCP合计4.2+UDP1.8）。实际 TCP4.187/4.125Mbps/dir，双向四条TCP socket稳态57秒各真收超过12,000个独立应用帧，TCP无最终缺失，UDP实收1.789/1.792Mbps；UDP最大空洞10ms、所有业务共享最大空洞0/10ms；源TUN/根fq所有相位0，读回和Stop通过。业务范围限精确SRC、丢包率、RTT与速率，不把自流TCP重传延迟否认，也不宣称Windows、高损TCP跑满或定向阻断其它TCP全覆盖。

两次首次请求预热12s被原高精度TUN sampler在业务前拒绝（只支持10/15/20s），已按15s修正，保留红色原始收据但不当产品性能失败；通用 idle/2s socket 合同继承新60s HOL验收导致临时红灯，已隔离并在合同 PASS 后继续。**当前status.open_requests为空**。全部SHA/负载、各业务收发、每流10ms空桶和成本见 [最新证据](../evidence/network-matrix-work/V3-D-cross-business-HOL-2pct-30pct-20261024.json)、[1%通过收据](../evidence/network-matrix-work/V3-D-cross-business-HOL-low1-50ms-full-mixed-PASS-20261024.json)、[最终报告](../evidence/network-matrix-work/final-report.md)。不以追求全绿重复压测；不合并main、不部署实机，早先 FEC Auto/Fixed有损读回 OPEN 继续保留独立归因。
