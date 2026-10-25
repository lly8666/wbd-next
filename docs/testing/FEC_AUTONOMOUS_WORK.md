# FEC独立岗位：关闭外层重传后验证与修复

**2026-10-25 最新测试执行例外（用户明确要求）：本 FEC 独立工位 Windows 相关测试暂时跳过 `TEMP_SKIPPED_USER_20261025`。** 包括 Windows x64 native ISA-L/codec、Go/Rust FEC Windows ABI/构建、Wintun/GUI/配置、Windows Game 或 Windows 真实端到端产品验证；均记 `NOT_RUN/TEMP_SKIPPED`，不是 PASS/FAIL、不是永久移除。**仅此岗位的计划/验收队列**，不修改或禁用 M0 Windows 所有权、工作流、任务与状态；已存在其他岗位的历史 Windows 结果不应删除或重标。用户明确恢复后，先核对 M0 独立提交和最新真实 Windows CI，再定向补验证；Linux ARM64、外层 OFF、FEC fixed/auto 和未覆盖风险继续处理。同步状态见 [本岗位 Windows 暂跳记录](../evidence/fec-network-work/20261025-W86-windows-temporarily-skipped-and-linux-priorities.json) 及 [FEC 测试计划](../architecture/FEC_V2_TEST_PLAN.md)。

**2026-10-24 V3 共享代码同步优先规则**：已授权把网络冻结点 `040741820b2f917b5868c285c438d4cc21c6193a` 合入自身分支并保留双亲历史；本独立岗位仅使用最新 V3 opportunistic repair ON，不能因本文旧版 v2 引用回退统计、半量独立缓存、批量预算、统一 MTU、TUN 和 owned fq600/flow256。OFF 是一个不可伪造的真实数据重传禁止政策，同时继续真实首发质量/反馈/FEC parity。此前旧7ad7产物 Actions 下载失败是历史事实，**不能复用为 V3 合并后产品资格**。优先处理上游 Fixed 损伤/Auto 无损 pending 的原生双端策略收敛，不将其未经证明归咎 fq。

2026-10-23用户直接授权新分支和新agent，随后澄清：**先完全关闭外层数据重传，只靠FEC把整套功能、恢复和成本修好。** 不等Normal外层重传岗位收口，不重做另一岗位的恢复调优；本授权覆盖本岗位自主修改、Actions dispatch和留痕，不需M0派单。

工作分支 `experiment/fec-network-tuning`，独立目录 `D:\codex\wbd\wbd-fec-network-tuning`。本岗位进度只写 `docs/evidence/fec-network-work/status.json`，证据/日志分别写同名evidence子目录与 `docs/devlog/fec-network-work/`。从上游网络实验分支45325c9c冻结起步；不能把它或旧组件PASS称为FEC-only已通过。上游后续修复按相关性在安全点引入，不追浮动HEAD，不改上游分支/状态/请求。

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
