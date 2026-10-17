# 11 实施顺序、反例与交付

本说明是施工约束，不是已经通过的测试清单。R0完成前不要让四个模块各写自己的Buffer/Clock/LaneKey/ABI。

## 能力交付顺序

以下是能力与依赖顺序，不是要求每个包、断言或参数值单独提交/跑 Action/交接。实现可小步提交，相关功能验证批量完成；任务粒度、开发基线与正式资格的区分以 `../TEST_PLAN.md` 第 0 节为准。

1. **R0/M0+M4**：锁旧SOURCE/依赖/toolchain，00的类型/编码/golden、C ABI、fake clock、platform假驱动，构建产物manifest和消费job；原Go TLS保护的V4能力协商适配。依赖选择已定，不重新办库性能比赛。
2. **R1/M1+M3+M4**：先Normal/off一包贯通，再ready batch、双owner、内存池、三cipher；所有权/关闭先过，之后测旧新同job。这一步不加FEC/repair掩盖裸路径问题。
3. **R2/M2**：真实receipt→shadow释放→第一次repair→第二次→epoch预算/稀疏→PTO/压力。每一小步有fake-clock反例，不一次写完再靠120s网络测试找错。
4. **R3/M3**：旧generator/scalar oracle→ISA-L Encode→缺源e维Decode→streaming/final/退役→profile切换。数学模型测试不是unsafe wrapper/实际CPU测试，两类都要。
5. **R4/M1**：共同logical ID/LINK/FEC→独立lane crypto→RX合流去重→慢lane/rotation。禁止用“能跑4个对象”替代4lane真实首到和共享计算证据。
6. **R5/M0**：沿TEST_PLAN风险组合补全业务、配置、MTU、弱网和容量。已达容量上限停止更重工况，保留profile及推算。
7. **R6/M4+M0**：原控制层剩余补丁导入、退出/崩溃恢复/整包、80s专项与长测，明确物理NOT_RUN。没有用户授权不去改机器。

每个角色只按正式registry路径开发。公共接口变更M0统一；有明确反例时允许改本文，但须写旧设计错在哪里、影响哪些测试，不能靠多种fallback让行为失去唯一解释。

上述是集成资格的依赖顺序，不要求组件开发全串行。按GOVERNANCE第3节，M0一次分配完整模块工作包；各工位包内自主实现/测试/修复，已冻结接口上的FEC/Game/恢复组件可并行，真实路径资格按阶段补齐。M0在安全批次边界集中接线，不能每个子步骤都“合入→重新派单”，也不能临时开放生产能力来替代组合验收。

## 当前 M0 的真实路径交付顺序

2026-10-16的 [R1-M0-HOTPATH-COST-024](../../decisions/M0-hotpath-cost-first-2026-10-16.md) 曾要求先修真实热路径并做同Actions A/B，再继续后续分配；接手按最新授权、registry和交付事实判断，不把这条历史顺序当作永久重开优化的指令。以下023是原正式资格依赖，保留未验项；优化收口不会自动开放capability，也不抹去后续超MTU等集成缺口。

这是既有任务 `R0-M0-V4-PROTECTED-OWNER-COMMIT-023` 的施工细化，不重置阶段、不重新分配 worker、不把下列事项预标完成。先核远端 evidence；已有精确证据满足的步骤直接复用，不重做实验。

1. **真实认证接入**：沿 01 唯一切换顺序，把已有 Go V4 可信调用点接到实际 Rust scoped owner 的 AEAD/PN 处理。沿用现有类型、arena、driver lease 与私有认证来源；拒绝外部自拼 cold bundle。测试必须穿过将来生产实际调用的函数；可替换时钟/设备边界以稳定复现，不另写一条更简单的 TEST-ONLY activation、crypto 或 delivery 链。保留当前生产 capability 关闭状态，不能为让测试通过提前广告尚未实现能力。
2. **Normal/off 首到与关闭**：两端真实握手后，真实业务经 owner、record、实际平台 I/O 到业务出口，至少观察双向合法 payload、乱序先到即时交付、重复零重复交付、损坏不交付，以及 Stop/重新建连/旧 generation 迟到。把 B01–B04 接在同一条路径：Detach 前零交付、半安装不激活、真实 driver loan 未归还时 STOP_INCOMPLETE、归还后释放、旧 lane 退休不挡新 lane。保留已有功能，不用 FEC、repair 或额外排队掩盖裸路径缺陷。
3. **Linux Actions 真实 I/O 锚点**：在独立 namespace/有界 owned 资源中接真实 TUN/raw 收发；无法使用真实驱动时写 UNSUPPORTED/NOT_RUN，unprivileged UDP、mock、native 编译均不能替代此项。先覆盖小包、当前有效 MTU 内最大包和超 MTU 兼容处置，禁止靠改 MTU/包型/业务率让坏样本变绿。功能断言尽量秒级，timer 反例用 fake clock，不机械地每项跑 120s。
4. **第一份开发性能基线**：对所测路径先保证必要正确性和安全关闭；无需等待全部外部建连、未使用的 driver 分支、FEC/Game或正式产品资格完成。依 `../TEST_PLAN.md` 第 0 节完成持续 owner 循环和独立业务收发，再测 Normal 单 lane/FEC off、诊断默认 off、双向各 10Mbps 大小包混合。逐包手动驱动的 smoke 不能扩大包数充当吞吐测试。记录实际注入、首到/missing、RTT/每流空洞、CPU-s/业务字节/包率与各层 drop/queue age；缺口继续 NOT_RUN，生产 capability 不提前开放。正式资格仍需前述全部适用锚点。旧新对比同 job 顺序 AB/BA；宿主容量不足停止更重负载，产品瓶颈留 profile，不先要求 500Mbps 或固定“省 25%”。

每步源码、用例入口、实际路径、剩余缺口落到既有 `r0/qualification-manifest.json` 与 devlog/evidence；不要新增另一套验收数据库。未实现能力只留 NOT_RUN，不无限补同义反例。Normal/off 可解释后再按 R2/R3/R4 接恢复、FEC、Game；现有成熟模块和有效组件证据保留。完成本次原子任务后按 S→H 交接，下一动作只写一个。

开发入口与交付入口的边界须在对应阶段收口：private/test feature可用于观察原真实热路径，不自动证明标准release入口、外部TLS建连或目标平台已经接通。R1正式资格补齐实际所用路径，R6核普通发布配置的Go加载Rust库、协商/配置/停止及配套包；不得到交付才发现只有测试feature能工作，也不得拿这些后续门重开已经完成的开发性能任务。新增集成反例按TEST_PLAN第4节并入既有ID，不增加逐断言任务树。

## 模块级必测向量

| ID | 关键反例 | 证明什么 |
|---|---|---|
| B01–B04 | Prepare/reply/early/Detach交错、stop时driver借用 | 不丢建连边界、不提前free |
| R01–R04 | empty/armed/push/wait交错、10万timer到期、时钟前跳 | 无漏唤醒、无到期全表风暴 |
| M01–M04 | pool exhaustion、跨arena旧key、满return queue、ring两代 | 有界不泄漏、不把缓存压力变fresh门控 |
| I01–I04 | send prefix/半packet/uncertain、截断/VLAN、seq32 wrap | 真发送计数正确、平台不猜成功 |
| C01–C04 | 三cipher原向量、失败PN、重复乱序、极短HP sample | wire/密钥/nonce正确 |
| L01–L04 | MTU±1、magic escape、乱片冲突、重组满时小包 | 大包兼容不影响正常业务 |
| F01–F06 | 全k/r、dirty零尾、e维与20维一致、先到source、final冲突、时间退役 | 算法/生命周期均正确 |
| A01–A06 | 反馈洞/跳号、旧报告、ACK双丢、旧证据双重试、预算epoch、pressure | 有限真实恢复且无假ACK |
| G01–G04 | 慢lane、跨lane互补、24种先后、rotation小MSS | 共享计算与首到，不串行等待 |
| P01–P04 | keepalive丢失、Suspend竞态、自动档方向、配置生效 | 原产品能力没有倒退 |

R0实现这些ID到测试路径的真实映射，只维护一处manifest，不靠文档勾选作为PASS。支持test过滤和预编译执行，编译一次多工况复用。模块unit可同job批量；性能只一个case，旧新顺序两leg同job。

## 什么时候可以说优化成功

先保证同业务/同source目标配置/同seed/同job，记录两leg背景；业务首到/丢失/p99与CPU-s、内存、实际wire一起看。Normal/off目标15–25%是初始愿望，必须用profile的可消除占比解释可达性；真实噪声大于差异记INCONCLUSIVE。Game用公共工作f的Amdahl上限，不强求4lane省75%总CPU。

每一步只跑足以证明该步的锚点和受影响反例，完整矩阵留R5。NoCapacity即使workflow绿也不能全标PASS。跨架构不直接比CPU-s；SIMD是否启用、native还是cross-build、普通/诊断模式明确区分。Rust语法/单测/模型通过不等于产品快。

## 完成时交给下一agent的内容

精确SOURCE、具体模块状态、公共接口版本、实际生效参数/使用方法、真实Actions run/attempt/build artifact/hash、通过与未跑范围、失败摘要、一个next_action。沿原S/H交接机制，意外中断先补事实。模块说明只在决策变化时改；每日进度写devlog/cursor，避免施工说明膨胀成聊天年表。

停止条件：接口和必要测试满足、同机数据可解释、无硬门回归即收口。发现性能上限由系统/driver主导，不能无目标继续重写上层；需要新复杂度时先用占比和成本证明收益。
