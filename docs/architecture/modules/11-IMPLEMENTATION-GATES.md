# 11 实施顺序、反例与交付

本说明是施工约束，不是已经通过的测试清单。R0完成前不要让四个模块各写自己的Buffer/Clock/LaneKey/ABI。

## 原子任务顺序

1. **R0/M0+M4**：锁旧SOURCE/依赖/toolchain，00的类型/编码/golden、C ABI、fake clock、platform假驱动，构建产物manifest和消费job；原Go TLS保护的V4能力协商适配。依赖选择已定，不重新办库性能比赛。
2. **R1/M1+M3+M4**：先Normal/off一包贯通，再ready batch、双owner、内存池、三cipher；所有权/关闭先过，之后测旧新同job。这一步不加FEC/repair掩盖裸路径问题。
3. **R2/M2**：真实receipt→shadow释放→第一次repair→第二次→epoch预算/稀疏→PTO/压力。每一小步有fake-clock反例，不一次写完再靠120s网络测试找错。
4. **R3/M3**：旧generator/scalar oracle→ISA-L Encode→缺源e维Decode→streaming/final/退役→profile切换。数学模型测试不是unsafe wrapper/实际CPU测试，两类都要。
5. **R4/M1**：共同logical ID/LINK/FEC→独立lane crypto→RX合流去重→慢lane/rotation。禁止用“能跑4个对象”替代4lane真实首到和共享计算证据。
6. **R5/M0**：沿TEST_PLAN风险组合补全业务、配置、MTU、弱网和容量。已达容量上限停止更重工况，保留profile及推算。
7. **R6/M4+M0**：原控制层剩余补丁导入、退出/崩溃恢复/整包、80s专项与长测，明确物理NOT_RUN。没有用户授权不去改机器。

每个角色只按正式registry路径开发。公共接口变更M0统一；有明确反例时允许改本文，但须写旧设计错在哪里、影响哪些测试，不能靠多种fallback让行为失去唯一解释。

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
