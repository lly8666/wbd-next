# M0 主线整改与验收完工包

2026-10-28 用户授权：M0 在 main 连续开发，精简接手入口，独立 FEC 历史工位结束。本包接续 PLAN025，不改变任务 epoch，不新增工位/审批/状态系统。已实现项先查证再跳过，旧 Windows A–E 清单不是重新开发命令。

## 1. 实际起点与尚未证明的事情

审阅 main `1bbd2426125bbaeceeb3a16f3a46d5335b198313` / M0 H313。以下是有来源的快照，不替代滚动 cursor；本轮查过 GitHub 六条 run 的 job 终态及握手失败 job 日志，详细数值来自已提交机器证据，未重复下载全部原始产物。

| 已有证据 | 正确解释 / 后续动作 |
|---|---|
| main 产品 `33ed20b4`、[40562809565](https://github.com/lly8666/wbd-next/actions/runs/40562809565)：七模式 UDP/TCP/Stop | 接线已有同源正例，不再重复造 Windows owner/重做整套入口。证据 `docs/evidence/M0/PLAN025-H309-main-S61-33ed-seven-modes-20261028.json` |
| `49f81637`、[40556191100](https://github.com/lly8666/wbd-next/actions/runs/40556191100)：自然 Auto 健康降档 | 双端业务/Stop，Windows 120s 内真实降档成立；升档/弱网曲线不自动通过。证据 `PLAN025-S55-Auto-natural-source49f81637-full-native-pass-20261028.json` |
| `dd0767ab`、[40561743731](https://github.com/lly8666/wbd-next/actions/runs/40561743731)：N0 双向约10M，单程300ms | 单样本正例；累计 Npcap drop137，之前29s owner拒绝仍未解释，不能宣称长期稳定。证据 `PLAN025-H309-WL-N0-dd0767-PASS-previous-FAIL-20261028.json` |
| `33ed20b4`、[40587653027](https://github.com/lly8666/wbd-next/actions/runs/40587653027)：512 UDP、508 echo、1%损伤 | 诊断正例，旧 stop-and-wait 夹具不适合作连续损伤。不是大吞吐、单向丢包或 p99 证明。证据 `PLAN025-H312-source33ed-linux-loss1-512-genuine-20261028.json` |
| 旧 ARM64 binary `f7ee097e`、[40613432085](https://github.com/lly8666/wbd-next/actions/runs/40613432085)：Fixed6 50M业务、30%损伤、单程200ms | 约49.65M、残余约0.03%、FEC真实恢复；150M是损后幸存包限速，不是150M物理线路资格。ICMP RTT p99约411ms，不是业务单向p99 |
| 同旧 ARM64 binary、[40613090033](https://github.com/lly8666/wbd-next/actions/runs/40613090033)：Game4 off 3M业务 | 残余0.78–0.83%、RTT p99约546ms；20M亦是损后限速；不证明当前Windows/Game+FEC/相关黑洞 |
| [40613090176](https://github.com/lly8666/wbd-next/actions/runs/40613090176) | 加netem和负载之前 Go FakeTCP 建连等待20s失败，随后带追踪复跑成功；不是30%损伤/FEC/CPU过载失败，仍须定位 |

最后三项完整收据：`docs/evidence/M0/PLAN025-H313-ARM64-30pct-200ms-FEC6-Game4-20261028.json`。后续引用必须分开 harness SHA、binary SOURCE、原Go SHA和平台；旧包成功不能写成新 main 已验证。

## 2. 本包完成边界与执行顺序

范围：已接线产品的稳定性、反馈/机会式修复协调、控制流量外观、可信夹具与代表性能。单公共端口、认证简化、多客户端全量迁移、全局GUI/DNS/分流等新功能另包；已有对应能力只做受影响保护，不删已有硬门。

先只读结算在途测试并定位首错。必要时至多一条小型区分诊断，禁止用整套压测代替定位。然后连续写齐下述 A/B/C 的本批代码、调用方、测试用例、装配/有效参数读回和夹具；冻结 main SOURCE 后一次编译/core→功能→代表性能。已修/证据充分项不重复实现，未知根因不假装已写好修复。测试失败只回归反例与影响面。

### A. 可靠建连与持续发送（先修）

- 建连：对照同配置失败/成功的 SYN→SYNACK→ACK→TLS→owner handoff 状态；记录实际tuple、关联/去重、超时/取消和读者交接，不记凭据/业务内容。检查 listener ready barrier、旧tuple/旧generation、raw reader竞争、handoff丢失已读控制包和计时起点。当前只是检查方向，不是已认定根因。
- 首错须保留 exact stage/OS错误。不得只把20s改成更长、无限重连或多刷seed来掩盖。已发控制包丢失的重试沿用成熟建连策略，不启用持续DATA PTO。
- Windows N0：给 owner拒绝精确原因链，分别统计 arena/待发送/driver/代次/时钟错误；对 Npcap drop取测量期差值，分开启动和关闭，核是否映射到实际业务缺失。已有 `%w`/clock修复先审差异，不再重复。错误packet仍与fatal owner错误分开，不能把所有 INVALID 当致命或把所有错误当普通丢包。
- 最小功能门：Linux、Windows各一个顺序20次建连→真实双向小UDP/TCP→Stop的功能批次；20/20目标是捕获此次偶发故障的工程回归，不声称99.99%可靠。首次异常保留现场、停止盲刷；另做单个代表建连控制包丢失/取消反例。

### B. 高RTT修复状态寿命：先核真实原因，再最小修正

当前旧ARM样本反馈约404ms，诊断cache约130ms，outer repair=0。**不能据两个平均值就断言所有shadow均超时**：查同一个候选的首次发送、实际expires、淘汰理由、有效负反馈到达、预算及发送结果；正反馈平均延迟不等于该缺口触发时刻。

若确为寿命/RTT估计错误：反馈测量沿用可信单调时钟、明确RTT是否扣减ACK延迟及单位；启动保守RTT只作先验，不能被单个短反馈误缩成130ms。采用 `T = clamp(RTT + 4*RTTvar + Dfeedback + Ddispatch, 250ms, 2s)` 的初始容量模型，Ddispatch先取50ms，Dfeedback使用当前反馈实际允许的最迟发送时间（不是永远10ms）；最终常量必须按源码语义及观测读回。最大单程300ms/RTT600ms，RTTvar50ms、反馈20ms时约870ms。不是把每个包都固定保留2s。

- 仅选中的不可变密文引用进入机会式shadow，一次机会完成/ACK/淘汰立即回收；新业务不等缓存，反馈元数据与payload寿命分离。沿用有界批量/时间索引，不全表扫描，不重建密文。
- 容量估算：500Mbps、1401B UDP业务约44.6kpps；若只缓存一半，870ms约19.4k条，原密文约28MB/方向；2s约44.6k条、约64MB/方向（按约1430B密文，尚未计metadata/双端/其他模块）。不能只看65536槽而忽略全局128MiB shadow/512MiB总上界；按实际帧长/候选比例重新计算。按需分配，非极限流量不占满上限；allocator回收可复用不要求RSS立刻回落。
- 满额只放弃可选shadow，不阻塞fresh、不伪造ACK。保留外层只一次、低CPU、0损近零、持续高损预算上限；不恢复“5%内必须救回”的SLA。Game副本/FEC parity/控制包不能算成外层DATA repair。
- 30%标准高负载下R/C约6%下限只在可行工况检查。定义F=实际首发DATA线上字节，R=实际外层修复；R/F<=10%，并另报R/(F+R+control+ACK)和R/C。F/C<0.6时不强求R/C>=6%。不能为了补比例制造假缺口或重传无损包。

### C. 控制流量外观与测试夹具（本批同步完成）

用户明确这里优先关注协议特征。当前Rust DATA receipt通常按10ms/缺口2ms到期，Auto本地2s决策并不是2s线上包；旧Go质量报告1.5–2s抖动、无新信息抑制、与keepalive共用调度。**不能把代码加密或CPU低当作TLS-like通过。**

- 一个方向一个控制出口，合并已经ready的receipt/质量/IdleHint/health；成功发送后按内容满足相应keepalive义务。不为等捎带阻塞业务，不等待无关流/慢lane；复用现有control TLV，确实缺字段才做最小显式版本/能力更新，不能把未实现字段假装已支持。
- GUI/Auto的2s本地读取不直接触发固定周期线上包；无新观察抑制重复质量报告。空闲只保留必要保活和有限反馈尾巴，休眠后停止；控制流量不刷新payload idle，丢keepalive不冒充“没有业务”。只收到反馈不能生成反馈ACK循环。
- 收敛节奏/长度而不是单纯追加随机噪声。复用旧控制包受MTU约束的加密内部padding、低频控制抖动/合并，测实际分布后保留必要部分；不承诺“随机到MTU就不可识别”。不得抖动真实DATA/FEC救援deadline或改变重传密文；feedback截止改变须同步B的寿命、质量窗口和测试。
- 观测正常业务、双向、单向下载、稀疏、空闲的record长度/方向/间隔/与对向DATA关联、TCP seq/ack及重传一致性。区分TCP分段包长与重组record长度。记录有限首尾trace或摘要/hash，不长期保存大pcap。正常HTTPS/WSS样本只作描述性对照；无固定样本量支持时不能宣称“99%不可识别”。
- 限速夹具明确 `shaper -> loss/delay` 两阶段，使之后丢弃的包已经消耗瓶颈服务时间；报告qdisc层次、前后包字节和backlog，避免netem先丢包后对幸存者rate限制。动态损伤更新不得清空延迟队列制造额外丢包。500M/1500B/200ms仅传播flight约8334包，300ms约12500包；预留约25%+控制裕量，delay队列正常占用不直接判拥堵。
- 持续发包按绝对时钟，接收独立按ID统计首次交付；损伤测试不能丢一包就停止下一包的stop-and-wait。记录应用、IP、外层各自大小；大流量以接近有效MTU大包为主，保留小包探针，纯64B极端PPS另标容量实验。
- 1Hz CPU/RSS、实际buffer/drop、各阶段queue age/high-water、首次交付10ms桶、repair淘汰原因即可；短ETW/perf栈采样独立于正式测量。Go EXE含Rust DLL和内核时间，不能凭进程名字归因。每模式独立日志/报告，不覆盖前一模式。

## 3. 最小充分的验收矩阵

源码冻结：同一main SOURCE构建Windows/amd64、Linux/amd64、原生Linux/arm64配套包，manifest/hash固定。修补后旧f7ee/33ed包只作比较，不能继续承担新版本资格。可保留旧平台专用测试排除声明，不冒充跑过。

| 顺序 | 场景 / 预声明判定 |
|---|---|
| 1 | core/receipt/回绕/期限/有界清理/控制合并/MTU单测 + 编译装配；A的建连循环；七模式真实UDP/TCP/Stop一次。只改文档不触发这些产品验证 |
| 2 | Windows↔Linux Normal off，10M每向/单程300ms/0损，60s校准后一个240s稳定性样本；无fatal、无停发，业务/NPF测量期drop和RTT完整报告。与父版本同VM顺序AB，不按一条正例宣布历史29s根因关闭 |
| 3 | Normal off 1/5/15/30% IID、每向10M；每个独立Action，方向对称和一项0/5非对称。UDP残余无需低于线路损伤，超出应先校正双路径echo/MTU分片/本地drop；外层repair计数/比例按B，不强求p² |
| 4 | Fixed最高档，外层50M每向、单程300ms/30% IID；按实测总放大率A设置业务 `B<=0.8*C/A`，不是50M业务塞50M线路。修复前150M损后样本仅作历史。分相同条件Normal固定档/必要Game保护，不全档笛卡尔积 |
| 5 | Game2/4 off与最高FEC：起步逻辑3M每向，独立逐包IID和共享100ms黑洞分开；延迟副本默认不撤。并行TCP大流+UDP小包的首次交付没有跨业务停顿；小流只能按同配置lossless基线比较，不要求0额外时延 |
| 6 | Normal Auto：真实低→高→低波形，至少一方向不对称；升档允许过渡损失，健康充分样本下120s内至少一次真实Applied降档即可。无需强降最低档；UNKNOWN不当零损、不降阈值刷绿 |
| 7 | 外层500M每向/单程200ms/2% IID；Normal off按线上开销折算业务。另单内层TCP应用500M/200ms/0损需要>=700M外层余量；BDP25MB，读回有效socket窗口并考虑64MiB初值。容量不足停止，不能用多TCP流冒充单流 |
| 8 | 1280/1400/1500外层配置推导各层MTU，边界±1、超限UDP/TCP兼容；现已接线的rotation/idle+keepalive/恢复/Stop做功能保护。未接线旧功能列下一包，不悄悄删掉也不阻塞本包到无限 |

每性能Action一个预声明场景/一个测量job；同场景AB同VM顺序，独立场景可并行；功能可合批。先校准注入/主机/PSI/softirq/内核drop，任一架构首次明确容量瓶颈停止更重同族，报告上下界与PROJECTED_NOT_TESTED。共享CI VM的两端+发生器开销不是部署单端成本。

## 4. 数学护栏：防止“修好正确行为”

- Game4 off独立丢包p=0.3时，四份都丢概率p⁴=0.81%，当前0.78–0.83%符合该参考；Game2为9%。共同黑洞不能用p⁴。
- Game4发送时点0/4/50/140ms，在独立丢包下首份幸存概率依次0.7/0.21/0.063/0.0189，未交付0.0081。成功样本单向p99可能落在140ms副本；若往返独立同样调度，离散模型成功RTT的p99额外约144ms，因此400ms底座+约146ms实测并不自动证明HOL。要查无关流停发和queue年龄，不能为了压p99撤掉抗突发副本；始终一起报告未到达和late。
- 满组Systematic RS k16/r20、独立30%时，未恢复源比例参考 `p*P[Binomial(35,p)>=20]` 约0.0228%；当前约0.03%不构成算法异常。实际k/r、分片、超时、相关损伤、local drop改变结果，<1%业务门只在声明的可行条件成立；不把FEC parity当业务重复交付。
- 无损仍有本地drop应定位，不拿理论随机损失覆盖；有损无需追求所有包必达。p99必须标明RTT或单向、时钟校准、缺失/截止和样本数，ICMP RTT不能更名业务单向p99。

## 5. 如何完工而不无止境测试

交付一个短表：缺陷→实际修复/未复现及保留风险→精确SOURCE与原反例/保护证据→CPU/内存/吞吐/延迟/容量边界。强度大于runner能力的格子允许CAPACITY_LIMITED，不伪造通过；可执行格子不能只写NOT_RUN就宣称本包完成。

本包完成要求：A的已知可重复故障修好并过保护；B说明零repair原因、满足适用预算且fresh不被门控；C控制/idle语义和夹具真实生效，外观有数据审阅结论；代表矩阵跑到实际能力边界，剩余旧功能单列。无法重现的历史80s/29s问题保留风险及观测，不无限刷到“证明不存在”。不再继续竞赛微优化或为旧Go/Rust兼容扩大范围。

## 6. main 与历史治理落实

主线写代码不代表直接发布：experimental/formal、源码/平台资格继续分开。M0当前task id/epoch不变，registry.goal指本文件；cursor只留当下事实，不复制本方案。老FEC status只归档，不从其next_action续跑；原始失败、日志、hash不删。

已有临时分支一次检查main祖先/独有差异：必要源码与可复用夹具增量合回main，旧SOURCE产物可测对照；不用旧树覆盖main，不必为了“同分支”重跑已完成来源证据。以后正式dispatch从main且manifest固定SOURCE；若现有workflow只认临时分支，由M0本批一次修入口/参数，不能每轮复制workflow或新建preflight分支。

历史地图 `docs/history/2026-10-28-M0-MAIN-HANDOFF.md`。新批次用新的短devlog，避免在带历史feature-impact的大长日志上反复追加导致治理要求重写无关卡。治理所需read-only解析/静态diff可本地，所有执行测试仍仅Actions。
