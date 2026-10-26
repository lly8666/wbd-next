# FEC独立岗位：关闭外层重传后验证与修复

**W168 2026-10-26 新的最高优先用户指令（覆盖W167测试配置）：** 恢复GitHub HEAD并执行 **纯UDP业务、无外层tc速率限速** 的原生 ARM64/AMD64 ×7个公开Normal/Game组合×IID1/5/15/30%×20s×双向10Mbps，原Go TLS仍正常握手但不主动造应用TCP流。以前W167的CPU PSI/steal性能阈值不得使本W168矩阵提前停止：逐例独立VM、性能指标只记录，真实错误标红。原先独立250Mbps/每向Fixed6 IID30%用户请求本次也在独立VM各架构一例，历史全局capacity_stop=true不擦除，仅登记用户此次W168指定隔离测试例外；不得宣称资格通过直到实际跑出。记录CPU core%与Rust M4 RX+TX线程占进程CPU近似比例、其他CPU、每进程RSS MiB、FEC容量与外层DATA retry/全外层TX占比；M4 Game多lane复制不是DATA重传，Go/Rust内部内存无法真实分摊。报告和机器证据`docs/evidence/fec-network-work/20261026-W168-UDP-only-No-Rate-No-PerfStop-DualArch-20s-Matrix.json`；不得改原网络岗位next_action、不得合main。


**W167 2026-10-26新用户授权：** 先保存Normal RX 150→250ms、1024→2048的300Mbps缓存评估为**DESIGN ONLY**；外层DATA修复公共Go默认already ON但显式OFF保留，新增七公开组合单测和两个原生ARM64/AMD64×(Normal OFF/Fixed6/Auto、Game2 OFF/Fixed6、Game4 OFF/Fixed6)×IID1/5/15/30%×20s×双向10Mbps的隔离测试workflow，真实FEC最高档只选Fixed6，不进入Game Auto。必须如实记录Go+Rust共进程CPU/RSS无法直接拆分、Normal M2 DATA外层repair分母与全部链路不同、Game2/4无v3 DATA repair账本。250Mbps/dir FEC最高档30%压力子项虽然用户提出，但当前`capacity_stop=true`未撤销，必须明确NOT_RUN而不绕过高压保护。见`docs/evidence/fec-network-work/20261026-W167-Outer-ON-DualArch-Matrix-and-Deferred-RX-250ms.json`。所有未跑或失败必须留红，所有原网络岗位next_action不可改。


**2026-10-26 W166连续流量数学模型复核：** 用户指出仅凭全16源丢失极端模型无法选最低整体业务损失，W165对2即发+18迟发的无条件推荐已撤回。离线持续1/5/15Mbps、真实k≤16/r=ceil(5k/4)、2,300个两批/三批候选和真实netem逐包GE(3,17,100,0)、时间GE/50-100ms黑洞双重模型证明没有不依赖故障分布的普适最优。候选仅限手动Normal且不进Auto：A 4/6/10@0/40/100(按包GE)，B 1/3/16@0/60/110(时间长突发)；120ms尾批受现RX150ms与24ms成块期限挤压。还未实现产品或真实重测。详细证据 `docs/evidence/fec-network-work/20261026-W166-Normal-Continuous-LongLoss-MonteCarlo.json`。所有原容量停止、主线合并禁令和独立岗位边界继续成立。


**W165用户授权：** 原始 Linux Game4 `0/4/50/140ms` 改为默认，老 `0/4/20/60ms` 与 `immediate` 仅显式回退；Normal 特殊手动长突发修补档只先数学评估，不进入Auto、不立即改FEC实现。参见 `docs/evidence/fec-network-work/20261026-W165-Game4-default-Normal-delayed-Maximum-math.json`；保留原独立容量停止/外层DATA OFF测试策略。


**2026-10-26 最新独立授权 W159–W163：** 用户要求简单验证真实 UDP/TCP 大包交付，不对该大包场景增加丢包率硬门；Game4 4lane 长丢包真实双向业务最终残余必须 **严格低于千分之一（<0.1%）**，必要时增加 lane3/4 延迟并同步核实队列、到期与配置 readback。新独立 Game4 可选档 `--game4-copy-schedule=stagger-4-50-140` 已在原生 Linux ARM64 SOURCE `8f85e0ba` 完整构建 SUCCESS、同一 Action 一个场景实际验证：旧默认 `0/4/20/60ms` 在 W161R 三次实测 102–107ms 共用黑洞下受损期 UDP 24/5888、23/5888 缺失（FAIL）；可选新 `0/4/50/140ms` W162 同类黑洞双向 5888/5888 UDP 真首达成功（0%）；W163 新可选档共享长 GE15% 45秒双向 8280/8280 与 8279/8280（0%/0.0121%），<0.1% PASS。旧 W160 默认档 GE 45秒双方零缺失。**这是指定 Linux ARM64 1Mbps/方向/给定损伤的限域资格，不是所有长黑洞的普适保证；不同 Actions VM 不构成严格 CPU 配对。** 真实 Normal fixed6 大包1370B、4/16/60KiB真 UDP 分片及 TCP frame W159 全交付但旧不适用小包验收产生 Action FAIL，保留原反例；去掉不存在的“小 UDP 队列”门、降低到1Mbps 后 W159R 真交付 Action PASS。默认仍是 `stagger-4-20-60`、`immediate` 回退保留，不影响 Game2/Normal；**外层 DATA retry 仍实际OFF、FEC parity独立、真实反馈仍在**。Game4 25Mbps 旧宿主 PSI 容量 STOP 不解除，80Mbps/新宽档高负载/Windows 不宣称测试通过，不强刷seed、不可合main。完整 [W159–W163收据](../evidence/fec-network-work/20261026-W159-W163-Jumbo-Game4-Wide-Stagger-results.json) 和 [合并报告](../evidence/fec-network-work/final-report.md)。


**2026-10-26 新用户授权覆盖旧“Game4错时仅可选、暂不接Game+FEC”：** 原 Linux Go TLS `game4` 4-lane 的 0/4/20/60ms（相对每个业务包 T0）现正式成为 **Game4 CLI 默认**，`--game4-copy-schedule=immediate` 可显式回退；Game2、Normal 调度不变。用户新增要求**重新接通 Game 固定 FEC 最高档 fixed6**，优先用真实 UDP 大小包混合、30% 每 lane 独立随机丢包、双向各20Mbps的 Game2 与 Game4 分别跑 ARM64 Action，每次一个真实工况。仅当20Mbps实测业务、CPU、宿主与队列容量通过，才每次+10Mbps逐档压测、目标设计80Mbps；首次资源瓶颈停止加压、先定向优化，不刷seed。此授权不是 Game Auto，亦不是先恢复所有旧失败的Game+FEC变体；**必须与 Game4错时联合验证**且记录精确SOURCE。上次 Game4 OFF 可选结论仅是历史。2026-10-26 新范围/容量模型与留痕见 [W125–W126计划](../devlog/fec-network-work/20261026-Game4-default-fixed6-Game2-Game4-IID30-20-to-80-capacity.md)；旧固定6/错时证据只在其各自旧源码范围内成立。尚未经 Actions 通过的新版不得标为PASS，不自动合main，Windows和UI仍暂不在本FEC岗位范围内。


**2026-10-26 新 Game4 FEC OFF 独立副本错时工作包：** 用户只授权原 Go TLS Game4、`game_fec=off` 配置 `--game4-copy-schedule=immediate|stagger-4-20-60`，默认仍为 0/0/0/0ms 立即发送，可选相对每包 T0 固定 0/4/20/60ms 分配给物理 lane1–4。保持接收 BPF/TX-RX分离/复用/TUN成功后真实确认去重；不接管 Normal/Game2、不做 Game Auto、不恢复旧失败的 Game+FEC、不加外层 DATA retry、不改 crypto/protocol/main。完整代码原生 `88ecda8b348eb319a0eb4cb282da2a6a01649a90`、build [40273336095](https://github.com/lly8666/wbd-next/actions/runs/40273336095)，以及真正同二进制同VM顺序A/B、单工况每Action记录，见 [实施日志](../devlog/fec-network-work/20261026-Game4-FECoff-copy-stagger-candidate-W114-W120.md) 与 [W114–W120机器收据](../evidence/fec-network-work/20261026-W114-W120-Game4-FECOFF-stagger-single-candidate-AB.json)。旧 `205c5578` W114 虽 Action 绿，但因为 lane cursor 轮转造成到期顺序倒置、3个位置大量过期，是**失败候选**，不得当PASS。当前 W115 clean、W116 IID5、W117 packet-GE、W118/119/120墙钟黑洞均按各自边界留痕：W117共享GE损失8.56/8.46%→0.089/0.056%；真实约20/50ms共同黑洞样本B无缺失，100ms仍有残余；无损/IID CPU成本约+18%/+26%。因此**保留错时为可选抗突发模式，默认立即、不自动启用**。W123 故意 lane1 故障中主动放弃被旧通用98%门误分类，原 Action红灯保留，W123R按仅失效lane例外严格重新检查。Windows本岗位继续NOT_RUN/TEMP_SKIPPED，其他架构/100Mbps小包PPS未资格；`capacity_stop=true`、`merge_ready=false`。不刷seed、不扩大重载。


**2026-10-26 用户最新确认：GameMode 不需要 Auto FEC 档。** Game2/Game4 仅保持当前公开 FEC OFF 与 fixed0–fixed6 的功能、损伤、成本和首发验证；**不要把 Game Auto 作为待办、验收缺口或新开发工作**。Normal FEC 的现有 Auto 义务/证据不变。W111 Game4 fixed6 静默恢复成功；W112/W113 最新精确 `e8b41fb` fixed6 在共享长 GE 严格1%业务门出现真实 FAIL（Game2 双向4.533%/4.316%；Game4 上/下0.888%/1.051%），详细产物 [W111–W113 收据](../evidence/fec-network-work/20261026-W111-W113-original-Game-fixed6-outeroff-bounded-ARM64-results.json)。依既有容量停机条件不加压、不刷seed，不把残余业务丢包自动归咎 codec，也不能用旧文档的“Game Auto未测”继续派生实现工作。

**2026-10-25 最新测试执行例外（用户明确要求）：本 FEC 独立工位 Windows 相关测试暂时跳过 `TEMP_SKIPPED_USER_20261025`。** 包括 Windows x64 native ISA-L/codec、Go/Rust FEC Windows ABI/构建、Wintun/GUI/配置、Windows Game 或 Windows 真实端到端产品验证；均记 `NOT_RUN/TEMP_SKIPPED`，不是 PASS/FAIL、不是永久移除。**仅此岗位的计划/验收队列**，不修改或禁用 M0 Windows 所有权、工作流、任务与状态；已存在其他岗位的历史 Windows 结果不应删除或重标。用户明确恢复后，先核对 M0 独立提交和最新真实 Windows CI，再定向补验证；Linux ARM64、外层 OFF、FEC fixed/auto 和未覆盖风险继续处理。同步状态见 [本岗位 Windows 暂跳记录](../evidence/fec-network-work/20261025-W86-windows-temporarily-skipped-and-linux-priorities.json) 及 [FEC 测试计划](../architecture/FEC_V2_TEST_PLAN.md)。

**2026-10-24 V3 共享代码同步优先规则**：已授权把网络冻结点 `040741820b2f917b5868c285c438d4cc21c6193a` 合入自身分支并保留双亲历史；本独立岗位仅使用最新 V3 opportunistic repair ON，不能因本文旧版 v2 引用回退统计、半量独立缓存、批量预算、统一 MTU、TUN 和 owned fq600/flow256。OFF 是一个不可伪造的真实数据重传禁止政策，同时继续真实首发质量/反馈/FEC parity。此前旧7ad7产物 Actions 下载失败是历史事实，**不能复用为 V3 合并后产品资格**。优先处理上游 Fixed 损伤/Auto 无损 pending 的原生双端策略收敛，不将其未经证明归咎 fq。

2026-10-23用户直接授权新分支和新agent，随后澄清：**先完全关闭外层数据重传，只靠FEC把整套功能、恢复和成本修好。** 不等Normal外层重传岗位收口，不重做另一岗位的恢复调优；本授权覆盖本岗位自主修改、Actions dispatch和留痕，不需M0派单。

工作分支 `experiment/fec-network-tuning`，独立目录 `D:\codex\wbd\wbd-fec-network-tuning`。本岗位进度只写 `docs/evidence/fec-network-work/status.json`，证据/日志分别写同名evidence子目录与 `docs/devlog/fec-network-work/`。从上游网络实验分支45325c9c冻结起步；不能把它或旧组件PASS称为FEC-only已通过。上游后续修复按相关性在安全点引入，不追浮动HEAD，不改上游分支/状态/请求。

**2026-10-25 W88–W89 真实 Linux GameMode 限域收口（用户追加要求）：** 当前公开仅 `game2`、`game4`，均按原 Go TLS 认证多 lane 复制/首交去重，**不是 Game+FEC**：现有公开配置强制 `game_fec=off`，Game 的 `--outer-repair=off`/V3单lane DATA ledger 不具备可宣称的支持资格。复用精确 Linux ARM64 产品 `4322a811`，四个 Actions 各自一场景/一个 job：[W88 Game2](https://github.com/lly8666/wbd-next/actions/runs/40206528368)、[W88 Game4](https://github.com/lly8666/wbd-next/actions/runs/40206531539) 的每lane独立20%丢包、1 lane 黑洞、clean恢复均通过 native/Stop/事先clean门；独立20%下 Game2 C→S/S→C UDP **3.98%/4.13%**残余、Game4 **0.194%/0.139%**，不能把 Game2 受损期称1% PASS；Game2 宿主PSI短峰35%。[W89 Game2](https://github.com/lly8666/wbd-next/actions/runs/40206930859) 与 [W89 Game4](https://github.com/lly8666/wbd-next/actions/runs/40206935735) 共享长 GE 15%下实际业务残余 **13.35%/13.15%** vs **8.31%/8.57%**，**均不满足受损期1%业务线**，Green Action 只覆盖其预声明clean和原生链路门；恢复无损均成功。不同VM、非固定GE轨迹，不得跨VM作严格CPU收益。原始证据 [W88](../evidence/fec-network-work/20261025-W88-original-Linux-Game2-Game4-independent20-lane1-blackhole-PASS-SCOPED.json) / [W89](../evidence/fec-network-work/20261025-W89-original-Linux-Game2-Game4-shared-GE15Long-SCOPED-HIGHLOSS.json)。无需重测现有四例、不得升级宿主负载或擅自补 Game+FEC/修改M0 Windows。**Windows 本工位继续暂跳、`merge_ready=false`、`capacity_stop=true`。**

**2026-10-25 W85 长相关丢包负例永久留痕：** Normal Fixed Maximum 在约15%长 GE 下 1% 门未通过（W80/W83及W85旧A）；已经按用户授权尝试最多两个已就绪修复组 4-row SIMD 编码后的 A/B 交错，精确源 `7cb64bfc` 原生 Actions 成功、真实 W85b 同 VM AB [40202359496](https://github.com/lly8666/wbd-next/actions/runs/40202359496) 未改善（旧A C→S/S→C 1.325%/1.198%，新B 1.390%/1.194%，仅约1.1%–1.2% parity行实际发生交替）；额外工作区成本不值得，原始源码双文件完全回撤至前置 blob，回撤 Action [40203220219](https://github.com/lly8666/wbd-next/actions/runs/40203220219) 成功。**保留严格门和全部失败，不因理论相关损伤强追≤1%，不等待第二组、不加冗余、不开新线程、不堆更多组/缓存、不刷随机种子**。未来要重启需新的 per-block timely erasure/成本证据及明确用户收益目标。结构化结论见 [W85 收据](../evidence/fec-network-work/20261025-W85-two-ready-parity-interleave-sameVM-AB-NEGATIVE-ROLLBACK.json)。非 Windows 剩余问题继续有限验证，Windows 仍本岗位 `TEMP_SKIPPED`。

**2026-10-25 用户补充的 Auto 速度/安全验收（优先于旧计划的 180s 对照等待）**：升档在真实认证反馈 VALID 且样本足够时尽量快速，升档过渡有丢包可以接受，但不允许借此遗漏可恢复的 FEC 源包或延迟新源首次交付。降档应逐级、缓慢平滑，在持续低损、容量健康且真实样本充足后，**以约 30–60 秒完成有意义的恢复降档为期望**，最终收敛到模型与真实 k/反馈所支持的较低档，不能无限留在 Maximum。这里不是无论网络怎样都强制降至 Light；UNKNOWN、过期/污染反馈、CENSORED 和 HOST_CAPACITY 一律不当作零损或触发无证据降档。不同样本窗口恢复延迟要报告，不为了读数改变 parity、ACK 或 outer DATA OFF 语义。W54 的 180 秒只是旧源码诊断波形，不是理想降档时长；W55 定向同 VM 配对验证及事实留在本岗位证据目录。

## 长期职责与边界

真实业务首次到达、低延迟/无HOL、低CPU优先，有界内存可以换CPU。原认证、完整性、账号/地址隔离、generation、固定密文、MTU和Stop/owned清理保持。大容量按需使用、增量有界回收；不逐包分配/日志、全表扫描、全局锁覆盖I/O、空闲忙轮询。不得用改弱校验、丢更多包、延长源包等待来优化表面数据。

可在本分支自主修FEC数学/ISA-L或其他现有native后端、FEC wire/收发状态、组关闭/partial/class、FEC bridge、固定/auto控制及其配置/必要观测和测试。主要路径包括 `crates/wbd-codec/src/fec*`、`crates/wbd-engine/src/v4_fixed_stream.rs`、`v4_fec2_live_rx.rs`、`fec2_staged.rs`、`runtime/fec2_owner*`，Go `fec_v2_policy*`/`fec_v2_runtime_controller*`及对应FEC适配。不受旧M3/M1角色派单限制；Windows原生codec可测，现有Windows产品接线工程不接管。

外层loss判断、RACK/PTO、repair预算、公用shadow扩容/淘汰仍由原网络岗位主修。本岗位只允许为真正的开关接线做最小改动，不同时重写外层重传算法。共用owner/FFI有必要触及就保持小补丁并单独记录；若发现共性缺陷，给精确SOURCE/复现和最小补丁，标COMMON_PATH，不把它算FEC算法缺陷，也不因此停掉所有可独立的FEC工作。两边有文件交集并不等于同一语义都能并行重写，最终组合必须定向复验。

## 第一项能力：真实关闭外层数据重传

起步源码的夹具识别 `repair_enabled` 字段却会将其判UNSUPPORTED，公开产品未确认有生效开关。因此先检查最新代码，已有能力则复用；没有就补最小端到端配置，推荐公开语义 `--outer-repair=off|on`，默认保留上游on的一次修复政策。FEC请求明确 `repair_enabled:false`，夹具映射两端实际配置并严格readback；不能只在分析器写off、设很低预算、删除报告或用网卡丢重传来伪装关闭。

- off禁止所有外层数据record重发，包括快速修复和PTO数据副本。**FEC parity是首次冗余发送，不属于外层重传，不能被一起关掉。** 握手、必要控制、keepalive和黑洞恢复不误改。
- 保留真实receipt、RTT、FEC applied和auto质量观测，不停止反向确认、不用伪ACK代替。off路径不创建无用的payload修复保留/候选timer，确需的已发送/成熟质量小元数据独立保留；若当前结构耦合，做最小拆分并验证，不能因为关repair导致auto永远pending。
- 无真实runtime off/readback、无外层重传计数时，结果只能是NOT_OBSERVED/未具备FEC-only资格。注入已知原包缺失及持续loss，双向证明外层实际data重传为0；FEC on时parity实际发出且恢复可观测。必要用有界header/PN观测交叉核实，无大pcap。
- on默认的一次修复及Normal/off无损仅做相关保护，不能把任务扩成另一次外层优化。新开关同步配置目录/CLI帮助和运行日志；未接线UI/平台明确列出，不假称全部支持。

## 当前工作包（已完成项不重复做）

1. 开关/feedback保留/真实零外层重传能力，以及一个无损与确定性缺源恢复的产品正例。
2. Normal固定档FEC：各档合法配置和真实applied、不同k/partial/class/长度、source立即交付、parity迟到/丢失、codec恢复与TUN首次交付、重排/重复、过期和有界内存。已有数学/native正例按精确源码及影响范围复用，不重新跑一轮库选型。
3. 在可承受负载下做低中档代表和maximum/30%/单程300ms主场景；核实际k/r_sent、到达trace、decoder计数、业务序号收支、CPU和p99。正常大流量以近有效MTU的大包为主，少量小包单列；超MTU兼容单测，不能要求高损多片大包也低残余。
4. auto普通/激进：正常模式上下行独立、实际观测→选档→applied、低→高→低和一个非对称代表；fixed/off不偷偷auto。缺样本/主机drop/稀疏/休眠不伪零loss，不拿netem真值驱动生产控制。沿用现有理论允许带，优先修明显超配或不升档，不追唯一精确曲线。
5. 已接线Game的共享FEC与健康lane首次交付作有限保护；Game+FEC若未公开支持就如实标边界，不为本任务新造Game接线，不加Game auto。跨平台复用native/scalar向量和构建能力，ARM原生业务是主场景；不宣称Linux代表Windows整机通过。
6. 一份可合并的FEC-only功能/性能报告及剩余共性边界。外层重传重新开启后的组合资格由后续集成限定验证，不是当前FEC独立收口前提。

设计定向读取 `docs/architecture/FEC_V2_BALANCED.md`、`FEC_V2_TEST_PLAN.md`，容量/MTU和场景读 `NETWORK_CAPACITY_ENVELOPE.md`/`NETWORK_MATRIX_20261022.md`。旧FEC计划里的固定历史baseline、逐档完整容量梯子、必须等M0和旧两次outer策略不适用；本页及用户最新授权优先。不要为了兼容旧Go wire保留无必要开销，也不无证据更换现有已加速算法。

## 验收与执行效率

FEC-only理论按每类实际k和发出的r计算：系统性MDS码、独立同分布丢包且幸存分片及时到达时，单源残余为 `p*P[Bin(k+r-1,p)>=r]`。不能把“收到的r”再代入该式重复计算丢包；实际迟到、相关损伤或非MDS后端按到达trace/可恢复条件单列。partial按源包数量加权，不把组内源当独立样本。最高档持续IID30%的代表业务目标仍为残余≤1%，小k稀疏/相关长黑洞不强套该门。FEC off且outer repair off的对照残余接近实际线路损失是正常基线，**不能套外层一次修复0.15/0.25/0.75%门**。双向统计、字节/包数、未到/迟到、纯FEC与组合结果必须分开。

实际可恢复且及时齐备的确定性样本漏交付是缺陷；已经到达的新业务不得等旧缺口。p99结合实际组关闭/传播/排队以及未到率解释，不追零损或不合理几毫秒尾部。优化同机比较保持k/r、外层开关、业务包型、负载和后端一致；主动少发parity导致更差交付不能算CPU优化。

所有执行测试在Actions。复用现有 `.github/workflows/network-harness.yml` 和ARM构建流程，不复制第二套夹具。**每个性能Action一个场景/测量job，独立场景可用不同Action并行；同一源码只构建一次，新旧同VM顺序A/B或BA。** 本分支workflow有显式 `target_arch` 输入，ARM测试填写arm64并核产物架构。请求各用唯一文件 `tests/network/fec-work/<case-id>.json`，不能覆盖上游 `tests/network/request.json` 或重复dispatch上游请求。

先数学和实际参数核对，再做代表点；机器容量不足停止更重负载，给有依据的估算，不能把产品单核瓶颈甩给VM。便宜功能合批；同因两次失败无新信息就换观测/缩小复现，不刷seed。缺字段自己补最低开销观测，已定位问题自己修，修后原反例+必要保护，不每次重刷MTU九组合。基础产品/TUN收支若有共性歧义先标相应资格未定，FEC局部证据仍可推进，不能把总丢包都算codec错误。

## 接班、留痕与永久提示词

每次开工刷新远端自身分支，读AGENTS/PROJECT_CHARTER、本页和自己的status；只定向读上游共性问题，不能执行上游next_action。核实际提交与Actions，先补遗漏事实，已有请求不重复发。精确SOURCE、policy、外层off readback、config/hash、run/attempt/artifact、结果和重要OPEN进入自己的既有目录。status只留热状态和下一完整能力，历史链接存devlog/evidence，不另造角色registry或审批系统。

有实质进展提交推送自己分支；不用向其他聊天发消息或等批准。最终报告写 `docs/evidence/fec-network-work/final-report.md`，区分实测/推算/未测和共享补丁，必要时创建PR但不自行合main。实现/验证达到约定代表覆盖即可收口，不能无限追理论极限或扩散平台任务。清理owned大原始文件，保留摘要/hash和失败，不公开凭据或业务正文。

> 继续wbd-next独立FEC任务。只在experiment/fec-network-tuning和独立目录工作。先读docs/testing/FEC_AUTONOMOUS_WORK.md及docs/evidence/fec-network-work/status.json，核Git/Actions并补遗漏，不接管原网络岗位的next_action。用户要求外层数据重传完全关闭、保留必要真实反馈，先把FEC固定/auto的功能、恢复、CPU/内存和首次交付修好。你可自主改相关FEC与最小开关接线、夹具/Actions并验证留痕，不等待M0。不得重写外层恢复算法或覆盖他人状态。配置必须实际生效，FEC parity与outer retransmit分开；一个性能Action一个场景，产物复用，独立场景可并行，新旧同VM顺序比较。先计算定位再最小修复，容量不足停止加压，已验证直接复用，完成代表覆盖后交付可合并报告。
