# FEC v2 验证：先正确与成本，再完整业务，不刷绿

本页随[FEC v2设计](FEC_V2_BALANCED.md)实施。沿用TEST_PLAN/ACTIONS_CONTRACT与现有请求/证据，不另建测试进度数据库。理论计算器`tools/fec_v2_model.py`只产出MODEL_ONLY；当前设计不是已实现功能。

## 1. 统一纪律与对比口径

- **每个性能Action只有一个预声明场景/配置/seed和一个测量job**；旧新必须在这个job/VM顺序AB或BA。一个配置可以有预声明的网络波形，但不能跑完后挑最优档。功能断言可合批。
- 固定SOURCE、harness、配置、工具链、native库、target和产物hash，Actions编译一次后消费。两端都运行相同scheme，不能让一端新头一端旧头后称新协议无效。
- 两种比较分开：I，同k/r/长度/负载的内核/内存实现成本；II，真实partial/期限/选档下的整体交付、CPU、wire、p99。配置标签相同但实际parity少发、target未实现、fallback或源包未注入，都不能记性能改善。
- baseline优先已冻结M3-016 `422a26127496560c0a52e6745ecc8f354e3f4f18`与已验Normal/off `fca4456313e59c0a67f4d8b98959a62d2af71b12`的**确切范围**；最新M0接线baseline由M0复核后固定。历史标量/ISA-L 26–45倍只是组件，不是旧Go整产品。
- 先测真实新链路10Mbps/方向、Game逻辑3Mbps/方向；通过再用50→100→200→500Mbps容量阶梯。某一级容量受限后停止更重档，按真实PPS、每包成本和线速开销推算，标PROJECTED_NOT_TESTED。

## 2. 功能批次（不拆成几十个首包任务）

| 批次 | 一次包含的关键断言 | 所属 |
|---|---|---|
| F2-MATH | GF、规范Cauchy、首行XOR、k1重复码；k1..16、r1..20有效集合；e0..min(k,r)，小k枚举、较大k固定seed；scalar/native独立实现相等 | M3 |
| F2-WIRE | source10/repair12+长度2；每个合法row、部分k、长度0/1/15/31/63/64/65/MTU边界；源立即交付、parity先到、全parity丢、恢复长度、错误k/L/flags、重复/冲突、跨epoch/方向 | M3 |
| F2-MEM | dirty pool零尾、直接输出、不别名、out of capacity、无新信息不重复decode、表cache命中/淘汰、heavy/compact/late与借用存活 | M3+M1各测自身边界 |
| F2-SCHED | 3class真实流量、首包绝对期限、deadline变化只影响新block、ready source立即服务、parity不饥饿/过期有计数、partial非满组、Game共享一次、慢lane不阻其他lane | M1 |
| F2-CONTROL | fixed/off无auto、7档/启动/激进、上下行独立、两client不同设置、revision/未知或旧能力拒绝、stale反馈、缺样本、host drop冻结、全组消失/反馈丢失不伪零loss、idle和报告分离 | M4（Go控制）/M0组合 |
| F2-PLATFORM | Linux x64/Linux ARM64/Windows x64 native向量、target ABI、运行时dispatch、fallback、打包加载/有效配置 | M3内核、M4装配，M0共用CI |
| F2-INTEGRATION | 真实Go认证→Rust→raw/TUN，off→fixed/auto切换，旧block drain、rotation A→A+B→B、Stop/lease、MTU±1/超MTU、源缺包后的其他业务继续到达 | M0 |

新头/模式只测试新规范；保留旧golden独立测试名，不再要求V2输出与Go V1相等。单位长度必须标明payload/LINK/数学symbol/record/外层IP，不能给一个MSS数字连减三次开销。

## 3. 有限性能集合与真实业务

首批只做下列有信息量的集合，不先把7档×所有RTT×所有损伤×所有平台做笛卡尔积。每一行需要的不同配置/方向独立Action，复用同一编译产物。

| 场景族 | 工况 | 目的与最少范围 |
|---|---|---|
| C | k16/r2、r8、r16；源64与1200B，另1个混合partial | 同机旧/新或scalar/native成本，优先r16/1200与混合partial，其他只在后端/缓存风险需要时补 |
| N0 | Normal/off，双向10M，原混合大小，RTT50ms，loss0 | 防止新架构污染off路径；一个同机AB，有歧义才BA |
| N1 | Normal固定mild/strong，双向10M，RTT50ms，IID5% | 低中档恢复、期限/字节/CPU；各配置一Action，不能同run跑两档 |
| N2 | Normal固定strong，10M，RTT150ms，IID20%；RTT600ms另风险样本 | 高延迟与状态寿命，不要求所有包零loss |
| N30/N50/N100 | Normal固定strong，业务30/50/100Mbps每方向、混合大小包、RTT150ms；容量允许后才下一级，各自独立Action | 用户常用速率；验证按class的包率/预测期限/满组比例/partial与恢复CDF。150或600ms已覆盖一次高RTT即可，不机械交叉重复 |
| S | 20pps/200pps 64B/小包预声明混合，背景大包流量独立；RTT10/50ms | 稀疏partial、第一包与恢复尾部；最高档也不强求理论不可达残余 |
| G | Game2、Game4，固定strong，逻辑3M/方向，RTT50ms；独立5/20%损伤与一lane慢/失效 | 共享编码/首到、CPU/副本账本；先Game4代表风险，Game2补函数/必要成本 |
| B | Normal或Game，预声明相关突发10/50/200ms，期间持续业务 | 检查损伤结束后新业务及时交付；不要求整组覆盖长黑洞 |
| A | 下一节auto曲线场景 | 选档适量、稳定、上下行不对称与容量识别 |
| M | 有效内层MTU−1/等于/+1、UDP大datagram、TCP多连接/持续stream并发小请求 | 分片兼容和真实交付；高损大包允许模型所解释的失败，不允许拖住普通包 |

混合包沿用已有夹具的固定分布并写manifest，不临时换成全1200B使数据更好看。负载包含有序TCP stream、独立TCP短请求、UDP序号流；不把TCP自身缺字节的HOL误判外层，也不只跑UDP echo证明完整业务。

RLC/64源长块不在这轮候选池。达到必要正确性、跨平台和主场景资格就集成；没有新回归风险不补几百组microbench。

30Mbps专项须包含大包class约一半/三分之一的功能回放（按明确包长分布换算实际PPS）；真实性能选一个代表混合分布即可，不要求每比例独立跑完整矩阵。检查低包率→30M突发→停流的包率估计/冻结deadline，无业务不维持250ms统计唤醒。对照初稿8/4ms用数学/确定性回放说明partial差异即可，不为已否决参数再新建一轮性能竞赛。生产参数以修正后按class速率+RTT公式为准。

## 4. 自动档曲线：理论允许带先声明

先用纯函数时钟/有效样本批量回放所有控制分支，再各跑有限真实netem场景。生产控制器只能看自身指标，分析器才能看注入真值/trace。每阶段记录p输入与validity、真实k直方图、模型最低档、实际档、升降原因、r_sent/r_planned和业务结果。

| ID | 单一配置中预声明波形 | 判断 |
|---|---|---|
| A01 | normal auto，RTT50ms，持续10M，1%60s→5%30s→20%30s→1%60s | 样本充分后升档不拖；恢复后按10s一级逐步降，不长期停maximum |
| A02 | 同A01的aggressive独立run | 除上限外通常比普通计算目标高一级，不叠加两种惩罚；不能跨不同runner直接比CPU绝对值 |
| A03 | C2S 1%/S2C 10%，60s后互换，RTT150ms | 两方向独立，不由server一套全局档覆盖 |
| A04 | 低均值但相关突发，RTT50ms，声明每次突发长度与间隔 | 不把IID拟合当硬门；突发加档有限期，不能不断扩大block等待 |
| A05 | 20pps、间歇停30s再来数据，反馈短时全丢/乱序 | 不把少样本/空闲当零loss，不把控制包当业务续idle；第一包无需等质量报告 |
| A06 | 故意限CPU/注入器或缩小宿主容量，网络损伤固定 | 明确HOST/CAPACITY_LIMITED、冻结盲目升档；不凭最终goodput宣称抗丢包失败 |

允许带：在VALID且样本门满足的时段，连续两次2s评价加控制传递时间后应应用升档；工程观察界为8s+一次有效报告往返。降档至少10s/级，从strong到light可能50s以上，初始阶段不能按稳态评价。平稳30s以后，候选档由实际k分布/p_design决定；普通允许理论需求+1级，aggressive允许普通目标+1级；启动/刚升损/滞回/模型不可达/容量异常分别解释，不伪装稳定超配。

0.1%是设计选择目标，不是A01所有阶段硬门。若观测算法偏差让无突发、容量足够的稳定5%流量长期最高档，判为需要修观测/控制，不得把这改成“更安全所以通过”。若理论就不可达，验证上限、低等待和可解释残余，不追零loss。

## 5. 如何判定质量与性能

硬门：payload错误/重复业务交付/跨client或epoch污染、越界/悬空引用、错误nonce/修复密文、MTU截断、无限阻塞、把未发当已发、把未知当零loss，任何一项FAIL。定向扔已知源包后，其他独立业务持续首次交付；不能靠只看幸存包p99掩盖missing。

随机恢复：以actual k、actual timely r、实际符号loss/相关trace建oracle。IID理论与均值比较按**block聚类**置信区间/固定seed模拟带，不能把同组所有source当独立Bernoulli套窄置信区间。多lane用联合擦除trace；碎片包用实际片数/依赖。保留模型、实测差值与原因，不要求现实精确等于公式。

必须报告：offered/accepted/first-delivered、missing/late及期限CDF；p50/p95/p99/p99.9与有输入时连续无交付；真实业务goodput；每方向CPU-s/GiB delivered和CPU-s/Mpacket（同时保留offered分母）、RSS/全局有界峰值、源/parity/副本/repair/control wire与PPS；实际backend、k/r/flush lateness、cache/allocation/copy、codec服务最长时间、queue age、host/kernel/socket drop。

低损健康满载的工程非退化参考：相对同机基线CPU≤+5%、幸存包p99增量≤max(1ms,基线p99的5%)，goodput相差≤2%；**只用于相同交付/冗余目标且宿主稳定的配对**。超过先解释同k实现成本还是策略主动多发，不机械刷绿。带宽下降伴随更多deadline miss不能算成功；降低T导致parity增加但显著减少恢复等待，可作为用户目标下合理取舍留痕，不强迫三指标同时严格下降。

这些5%/1ms/2%是测量噪声与回归调查线，不是数学定理。样本/runner噪声超过允许带就INCONCLUSIVE；有新修复或预声明BA才复跑，不能无限重复到好宿主。FEC核心已优化后不预承诺整体CPU下降百分比，按Amdahl与实际占比解释。

## 6. 容量、跨平台与完成

保存CPU型号/ISA/核数与cgroup quota、PSI/steal、频率可观测值、注入器占用、actual injected和drops。达到capacity后停止更大压力；分别说明计算、PPS/系统调用、发送线速或宿主争用。500Mbps/方向业务、strong已经约1Gbps/方向FEC数据，Game还乘lane数，不能把外层超线速当算法失败。以1200B源计Normal k16/r16原始GF主项约1.0e9字节乘加/s/方向，这是计算量不是CPU周期或实测吞吐。

Linux ARM64 native runner不可用时标NOT_RUN/UNSUPPORTED并交待其必要性；不能只用x86成绩发布“跨平台同样快”。Windows原生codec测试不要求先装Npcap，驱动/tunnel测试与codec区分；打包/实际加载和GUI配置须有自动化功能证据，物理机另列。

收口：一份精确组合SOURCE，功能批次、必要同机成本/真实场景、跨平台边界、配置落地、未解决问题齐全；证据进原devlog/evidence/cursor。停止本工作包，继续原023/产品门，不能把设计通过或某个microbenchmark当全项目发布许可。
