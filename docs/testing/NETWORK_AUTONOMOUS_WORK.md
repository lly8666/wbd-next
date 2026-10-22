# 独立网络矩阵任务：长期接班入口

## 授权、目标与边界

2026-10-22用户直接授权：复用PR #21网络夹具及已合入的PR #22矩阵/诊断方案，新agent在独立分支自主测试、记录、调参和修复；M0继续Windows接线，不需向M0或其他agent汇报、不等待派单或逐次批准。这覆盖旧方案的M0独占测试安排。不要添加正式工位、修改main registry/M0 cursor或另造治理系统。

任务唯一分支建议 `experiment/network-matrix-tuning`。仅首轮创建；后续接班查找并继续同一远端分支，不反复新开分支。分支内可修改真实Linux公共产品路径、必要配置/监测、夹具/Actions和文档；不可改动他人的工作分支、共享工作目录或直接推main。保持Windows现有改进，不重写Windows接线、不接管Android/OpenWrt。最终交付完整报告和可审核的修改，未经后续合并指令不自行合入main。

这包括问题实际落点的 Go 适配层及 Rust engine/recovery/codec/platform 的必要修复，不因目录另有正式工位归属就等待派单；只在本实验分支修改，保留原模块约束和最终集成审查。2026-10-22用户后续要求保留当前有效诊断/修复流程，只消除执行歧义；不重启任务、不重排正在验证的合理修复。另行讨论的旧功能集中补齐工作暂停，不扩大为全功能移植。

真实业务首次到达优先，其次低延迟/无跨业务HOL、低CPU成本；有界内存可换CPU。认证、完整性、地址/账号隔离、generation、固定密文重传、MTU、Stop/owned清理硬门保持。高损允许残余，不用可靠有序等待、无界重传或长队列刷零损。Game不新增auto。优化必须由实际瓶颈支持，不无限更换算法/库。

## 开工与意外中断后的恢复

1. 刷新远端main、任务分支及需要消费的ARM分支；读AGENTS/PROJECT_CHARTER和本页。读取任务分支 `docs/evidence/network-matrix-work/status.json`，不存在才创建。main其他角色状态只用于避冲突，不作为本任务等待条件。
2. 热状态仅保存：基线与当前产品SOURCE、夹具SOURCE、构建run/attempt/artifact/hash、当前阶段、未结束请求/run、重要OPEN及证据链接、下一项完整任务。控制在约100行；完整结果放 `docs/evidence/network-matrix-work/`，过程放 `docs/devlog/network-matrix-work/`。沿用现有devlog/evidence目录，不复制全库历史或另建审批层。
3. 核对状态记录后真实提交、Actions和未结束intent。上轮没来得及记录时，先按事实补recovered日志，再开发；未知写未知。查明同一请求是否已发出再dispatch，超时不等于未发出。已有测试结果直接复用。
4. 定向读 `NETWORK_HARNESS.md`、`NETWORK_MATRIX_20261022.md`、`NETWORK_TRIAGE.md`。旧Windows优先/等M0规则在本独立任务中由本页覆盖；网络数学、允许带、容量停止、故障诊断与硬门仍有效。遇到具体缺陷再复习对应模块的当前设计、真实调用链和最近修复。

## 基线与夹具复用：先解决真实的小缺口

首轮从 `feature/arm64-linux-android-openwrt-autoaccel` 的一个明确远端提交建立任务分支，记录精确SHA；将含PR #21/#22与本页的明确main提交合入任务分支，保留双方已完成改进。已有任务分支则先恢复，不重置。新main/ARM变化按需引入，不持续追浮动HEAD或覆盖正在跑的基线。

ARM现有产物可用于起步：历史产品SOURCE `9194e20f2f53cd4ac0b85d3e7f5aa136f164d2c3` 的Normal/Fixed/Auto有各自原生正向功能证据，Normal双向10Mbps/60s容量试验run `39755860617` 已完成。这些是恢复线索，开工应核最新记录、可下载产物、目标和hash，不将历史资格扩大到新源码、Game、弱网或p99。

**PR #21合入时公共runner为ubuntu-24.04/x86_64，产物校验要求ELF machine=62及fixed-build/manifest格式；ARM分支产物为另一种manifest/SHA256SUMS布局。** 首轮缺口是给同一夹具补ARM原生runner与产物格式适配；接班先核任务分支已完成证据，已补好就直接复用，不再重做“首项工作”。校验ELF AArch64=183、实际runner架构、ZIP/各文件hash、产品SOURCE/run/attempt及加速features；旧x64验证保留。不得关闭来源/架构验证、用QEMU计原生性能、复制第二套业务/损伤/统计框架。优先归一到现有runner消费目录/manifest；不混装不同来源Go/Rust库。

夹具自检可复用 `.github/workflows/network-harness-check.yml`；测量用 `.github/workflows/network-harness.yml` 与提交的 `tests/network/` JSON。网络性能已有正向功能证据即可开展；实际native后端计数/已编入加速与回退能力可随相关业务验证，不等加速库专项全部收尾。普通cargo构建未启用 `native_fec_acceleration` 时仍可能是scalar；明确记录运行后端，不由包名猜测。

PR #21的Game+FEC、cipher/repair参数、生命周期等能力有明确未支持边界，按最新真实CLI/API/readback更新适配；不支持标UNSUPPORTED或补实际接线，禁止填了参数却当成生效。Game在ARM须有自己的小流量真实路径验证，可随首个对应场景完成，不阻挡已可测Normal/Fixed/Auto。

## 自主执行顺序与停止条件

用户新增要求与现有S030/S031修复的衔接见 [容量/MTU补充](NETWORK_CAPACITY_ENVELOPE.md) §3–4。先接续自己的唯一open request；已有MTU修复不重写、不重复dispatch。模型计算后对照产品实际构造参数；不能拿小规模80ms PTO/64KiB repair cap去判断500Mbps能力。源文件冲突保留本分支较新的观测/修复，只引入新增模型与必要边界验证。

1. 复用已通过的基础功能。先运行真实双向混合大小包持续基线，确认注入、交付、模式与Stop；低开销记录产品/注入器CPU、RSS、p99/未到/迟到、10ms首到桶、socket/qdisc drops。iperf进程CPU不能冒充产品CPU，最终applied不能代替auto全程曲线。
2. 按模型估算PPS、FEC/Game/修复膨胀、BDP和netem队列容量，再逐档发现机器容量。注入器不足、宿主争用、本地内核drop和产品单核瓶颈分开。容量不足停止更重负载并给有依据的PROJECTED_NOT_TESTED；不得以总CPU没到100%掩盖单核瓶颈。
3. 按NETWORK_MATRIX关键集合覆盖off低损/预算上限、固定FEC中高损、auto升降与不对称、Game独立/相关损失，混合UDP/TCP/小包探针、稀疏/大包兼容、换lane、单/双向黑洞、payload idle/keepalive/有数据重建。先代表组合再针对问题扩展，不跑全笛卡尔积。真正idle测试须关闭业务探针；有探针不能声称无payload。
4. 目标500Mbps/2%/单程200ms和50Mbps/30%/单程300ms均指每方向外层线路容量。FEC实际k/r及及时到达决定恢复允许带，最高档持续IID30%按方案业务残余≤1%；off高损不强求低损/零损。预算按实际修复字节/首发字节核验，稀疏比例豁免仍有资源边界；未知计数记NOT_OBSERVED。RTT、单程、已到p99与未到率分开。
5. **一个性能Action一个配置/seed/场景、一个测量job；不同场景可分开Actions并行。** 同一产品SOURCE编译一次后复用；修复或必要观测改变产品时，在独立构建Action产生新SOURCE产物并保留旧基线，不在测量job编译。新旧比较必须同job/同VM顺序AB或BA，记录每leg实际机器容量和背景争用。不同CPU架构/不同VM不能直接相除宣称优化；功能断言可合批。所有执行测试在Actions，不在本机或用户物理机跑。
6. 故障按下节和NETWORK_TRIAGE处理；保留有信息增益的拆分诊断，不要求发现FAIL立即改产品，也不为了达到某个样本数强制修复。无关已可测工况可有限并行，不能取代当前重要异常的定位或修复；完整性/生命周期硬缺陷影响范围暂停资格扩展。

### 发现异常后的下一步

- 先核来源、真实配置、注入/损伤、计数单位与目标适用范围。FAIL可能来自夹具、模型前提、正常设计边界或产品；允许有证据地质疑指标，保留原结果与调整理由，不静默降门刷绿。
- 原因不明时保留OPEN，并写清下一项能区分假设的动作。聚合计数或缺字段挡住判断，就自行补最低必要的真实路径观测；`NOT_OBSERVED`是本次证据边界，不是永久等待M0的理由。不要求先建齐整套监控。
- 混合/纯UDP、负载/方向拆分只要有信息增益即可继续。两次同类失败无新信息时停止原样重跑，改观测或缩小复现；不是“两次失败必须改代码”。已定位可修缺陷优先修复；健康场景可并行，但不以扩矩阵代替这条主任务。
- 修复前回读设计、实际调用链和最近相关改动，做最小充分修改。新产物先复验失败条件及相关功能，再用默认诊断状态同job新旧性能锚点检查退化；诊断ON成绩不能冒充普通性能。完成后回到矩阵，不重跑无关已通过项。
- 本阶段处置结论写入已有status/devlog：已修且复验、有证据的设计/模型边界、宿主/注入器限制，或具体阻塞及下一动作。正在定位可保持OPEN；不能只列失败就称测试修复完成，也不为了清空OPEN无限开发。问题直接关乎首次交付、完整性或持续停顿时优先；不新增审批、固定重试配额或每bug提示词。

工作流和产物使用最小需要权限；已有workflow可用自己分支ref dispatch，缺入口可在本分支修正，不等待M0代跑。平台403/额度/环境缺失如实记录，只在需要用户操作时询问。不要向其他聊天、工位或他人发消息；GitHub文件提交就是持久记录。

## 留痕与有限收口

每次有实质代码/参数/请求/结论变化即提交并推本分支；外部试验前留intent，结果回来补run/attempt、精确产品/夹具SOURCE与配置hash、机器信息、通过/失败/缺测及解释。凭据、正文和大pcap不入库，清理自己的原始大文件保留摘要/hash。热状态压缩只保留重要OPEN和下一动作，旧日志按需引用，失败证据不删不改绿。

完成后写 `docs/evidence/network-matrix-work/final-report.md`：实测覆盖表、每模式适用范围、CPU/内存/外层开销/首次交付及尾延迟、默认参数建议、因果对比、机器上限、未关闭事项和未测范围、可合并提交。没有更多可区分的新问题就收口，不以全绿/所有极端工况/最大速率为无限任务。不宣称ARM或Linux结果代表Windows或物理机通过。

## 长期接班提示词

> 继续 lly8666/wbd-next 的独立网络测试与调优任务。先刷新远端，读取 main 的 AGENTS.md、PROJECT_CHARTER.md、docs/testing/NETWORK_AUTONOMOUS_WORK.md，以及实验分支 experiment/network-matrix-tuning 的 docs/evidence/network-matrix-work/status.json；核对增量提交、在途Actions与缺漏结果，按事实恢复，不重复dispatch。不存在分支时才按任务入口的首轮规则创建。
>
> 用户已授权你在自己的分支修改相关Go/Rust产品代码、必要观测、夹具和Actions，自主测试、修复并推送；不等M0派单、不向其他聊天发消息、不直接合main。M0的Windows接线和暂停中的旧功能集中补齐不属于本任务。矩阵、诊断手册按当前问题读取，保留已有有效诊断和正在验证的修复，不因新提示词重启任务。
>
> 首次交付、低延迟、无跨业务HOL、低CPU优先，原正确性与资源硬门不变。FAIL先核工况和目标；原因不明就做有区分力的观测，缺计数自行补最小观测，已定位缺陷自主修复。独立场景可并行，不用扩矩阵取代重要问题的处理，也不为凑修复次数盲改代码。每个产品SOURCE构建一次复用，产品改动重建并保留基线；所有执行测试在Actions，一个性能Action一个场景/测量job，新旧对比同job顺序跑。
>
> 修复前复习真实调用链与相关设计，修后复验失败条件、受影响功能及默认诊断状态性能锚点，然后回矩阵。宿主容量不足不加压，产品瓶颈不归咎宿主；未测/未知/失败如实留痕。沿用本分支简短status、devlog和evidence，完成代表覆盖与有依据的处置后交付报告，不新增治理或无限追求全绿。直接从最新next_action继续。
