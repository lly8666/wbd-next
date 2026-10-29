# PLAN026｜Windows Rust-only FEC/Game + 双端 Auto/Health 低成本整批施工契约

> 2026-10-30优先级更新：[PLAN027](M0-PLAN027-LOW-RATE-FEEDBACK-CLOSEOUT-20261030.md)已覆盖本文件的后续顺序、M2依赖、Auto验收及矩阵门。先去线上Receipt接替代低频反馈并做简化A，后补接线B/矩阵C；下方M2相关要求仅供历史，不再派活。其他成熟实现和旧证据保留。

**2026-10-29 / M0 / 用户新增明确授权。状态：DESIGN_APPROVED_FOR_M0_IMPLEMENTATION；产品接线、构建、功能、性能均不是本文件所证明的 PASS。** 继续在 `main` 实现既有 `R0-M0-PLAN026-WIN-RUST-NATIVE-IO`，不新建任务/epoch/实验分支。当前任务有效性仍以 main registry.goal、真实进度以 cursor、资格以精确 SOURCE/Actions 为准。本文替代前期 [阶段 B 研究](M0-PLAN026-FEC-GAME-RUST-STEADY-WIRING-RESEARCH-20261029.md) 的**实施顺序与 Auto/Health/测试契约**，原设计/负面历史保留，不复制到热入口。与 [Windows Option B](M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md) 不冲突；本决策最初提及的 Normal/off N0 未验已被后续真实 Windows signed-Npcap/Wintun 证据取代：SOURCE055 功能/Stop、SOURCEa123 N0 240s、SOURCE7fc 150Mbps 代表性性能已 PASS（均仅限精确SOURCE）。同VM CPU因果优化、历史波动/容量及物理不自动全绿，但**不得把 Normal/off 再施工或重跑当作后续 Fixed/Game/Auto 的硬前置依赖**；动态 lane 更换仍独立开放。

## 0. 一次性批次的最短依赖链 / 不做什么

`现行入口/OS借用复核 → Windows V2 typed NativeAttach + TX/RX/Stop → FixedStream/Fec2LiveRx + GameAdapter/2/4 lane → 统一 Rust M2/Health/Auto deadline + Linux 双端接线 → Go冷调用/有效配置/feature cards → 同一 SOURCE 的 V2场景/编排/测试/manifest → Actions 编译/core → Fixed/Game功能与必要性能 → 最后 Auto自然升降+Keepalive/idle/timeout → 同 VM A/B → cursor-only H`。

**把全部产品代码、调用方、有效参数/GUI或CLI映射、测试、夹具、Actions工作流及装配manifest先写齐，固定唯一 SOURCE 后集中跑 Actions；不要每修一个 helper 跑一遍真实业务，不拆出自证无效的半成品分支。** 开发中允许便宜静态检查。后续定位首个失败时只重跑原反例与受影响保护。没有必要不重写 Linux 成熟 raw/TUN、M2、RS16、GameAdapter、旧Go TLS/OS/WAL、FEC 类型或整套测试框架；不开发自造TLS/新wire/线程池/泛化防御包装。已有能力是否真实接通只读当前源和最新适用证据，不从旧分支存在推导待合并代码。

## 1. 可复用真实调用链（施工前只核相关模块）

| 模块 | 源码/现状 | M0最小修改 |
| --- | --- | --- |
| Windows两个原生 worker | `crates/wbd-engine/src/v4_windows_native_runtime.rs`、`crates/wbd-platform/src/windows_native_io.rs`：V1 Normal/off，TX Wintun→原认证 owner→NPF，RX NPF→唯一 opener→Wintun；事件/M2 deadline | 扩成 mode-aware V2；同 TunnelOwner 下 1 TX + 1 RX，两 worker 不因 lane 增长；事件公平轮询多 capture，单个共享 TX NPF/Wintun |
| Windows既有FEC | `v4_windows_fec2_owner.rs`、`v4_fixed_stream.rs`、`v4_fec2_live_rx.rs`；真正 source/partial-close/≤4行quantum、quiescent revision、M2首发成熟状态已有 | V2 TX对实际Wintun ready source立即offer/封 kind2；data优先、parity deadline无空轮询；RX一个M3 opener解 kind2/3→Fec2LiveRx→真实Wintun commit。NPF copied/uncertain/not attempted分别回执，不凭入队当发送 |
| Windows既有Game | `v4_windows_game_owner.rs`、`v4_game_lane.rs`、`v4_game_fec.rs`；共享逻辑ID、2/4每lane独立AEAD/PN/4tuple、错峰due/内层Fixed FEC | 复用同一GameAdapter；一 Wintun / 共用TX句柄，RX worker等待2/4个精确BPF事件并有界公平drain；一个lane错误/阻塞不耽误其它lane首次交付，Wintun成功后才最终逻辑commit |
| Linux真实客户端/服务端 | `bridge_v4_linux_{client,server,game}_product.go`、`bridge_v4_game_native_linux.go`、Rust `v4_embedded_go.rs` / `v4_game_public_kernel.rs`；原Go逐lane真实TLS认证→Rust raw/TUN和成熟M2 | 保留已有收发/生命周期和已有成功用例；复用Rust低频控制语义，尽量去掉 Linux Auto Go 200ms定时器，不先替换Linux Game现有每lane RX布局 |
| Go Windows旧热路径 | `cmd/wbd-client/m0_native_v4_windows.go`、`m0_native_v4_game_windows.go`、`m0_native_v4_*peer_windows.go`、`bridge_v4_windows_auto_controller.go` | 旧Go业务包pump只可作为明确的A/B对照；默认 Fixed/Auto/Game 业务0 Go每包Read/Write/FFI；Go留真实TLS/FakeTCP启动、OS/WAL、GUI/CLI、lane冷更换及Stop控制 |
| 老项目行为oracle | `lly8666/wobuzhidao@a7a82db3`：`internal/adaptivefec/controller.go`、`internal/runtimeowner/{control_policy,quality,health}.go`、`internal/runtimeentry/{lifecycle_health,lifecycle}.go` | **搬决策行为、Health/Quality合并、超时/休眠语义，不搬RS(20,R)、旧wire、Go循环或旧FEC包格式** |

Windows从原Go TLS逐lane认证、Npcap capture detach/early队列、签名Wintun OS lease，进入 Rust V2；Rust准备真实TX NPF句柄并持有借用，直到stop/join 完成Go才清理Wintun/WAL/Npcap。DLL生命周期覆盖原生worker。版本、尺寸、epoch、lane incarnation、PN/seq、4tuple、原始MSS/MTU/Persona在V2启动与换lane时一次核验；旧 lane 允许退役晚到，不允许旧代覆盖新active。更新lane走Go低频重建TLS、Rust Prepare/Commit/Abort/Retire；本批先满足当前模式必要的借用与Stop，不为动态lane额外发明线程、时钟、加密state。

## 2. 唯一 Rust 控制调度器 / 成本红线

- Windows稳态 **固定两个 Rust I/O worker**（这是设计目标，依真驱动结果核对），TX专有NPF sender，RX公平管理每个lane原生Npcap GetEvent；Go不承载业务包、不每5/20/200ms空轮询、不按PPS调FFI。Linux使用现有稳定 Rust native TX/RX 组织，不为追求数字“2线程”先改成熟路径。
- TX事件集合取 Wintun RX ready、RX→TX通知、Stop/lane-update、**同一单调时钟**上 M2反馈/修复、FEC partial、Game4错峰、Health/Auto策略最早真实deadline。没有due就阻塞。RX按已ready lane round-robin有界drain，不阻塞一个坏lane；NPF事件可用性与公平性须真Windows证据，失败时只补测得的最小替代，不退回Go轮询。
- 新source即时发，不等batch凑满、不等FEC block/重传/旧lane。先DATA后有预算的parity/control；共享owner不应在NPF syscall、Wintun写入或长FEC计算期间持有跨lane大锁；只有同源锁等待证据才拆状态。driver投递三态保持 `Accepted/Uncertain/NotAttempted`；unconfirmed不能伪装已复制，更不能重封已发原密文。
- 有界 slab/scratch、batch ready-only、一次性解析DLL入口和流元数据；生产关闭逐包日志、计时/昂贵RNG，诊断opt-in稀疏抽样。Go TLS、WFP/DNS/Route/MTU/WAL与唯一Wintun会话生命周期不变。真实Stop唤醒所有worker→join→释放capture/arena/driver借用→QUIESCED→Go EndSession/OS恢复；不得提前宣告已Stop。

## 3. Normal Fixed/Auto 决策：复用FEC2，继承旧项目快升慢降

**编码与档位仍是FEC2**：`light,mild,medium,balanced,high,strong,maximum`，每个真实闭块按`k≤16`定相应r；不用老项目`R=0,4,8,10,12,16,20`当FEC2 wire/codec。Game只有Off或Fixed，**绝无Auto或隐式Auto actor**。Normal Auto默认Strong，aggressive只高一档并有上限；独立客户端、方向、epoch/generation和revision。启动与操作员真实Applied均须明确区分。

- 使用当前已验证的 **2s fast、8s mature slow、16s actual-k histogram**（来源：Rust M4首次copy+认证的反向M2；非外层TCP ACK或修复后的残余率）。旧项目`2s/15s EWMA`只是平滑行为oracle，不再并行运行第二采样器。覆盖不足、样本<512、样本重叠/过期、host掉包/队列积压、UNKNOWN/CENSORED、counter reset、乱代次时保持而非假零丢包，稀疏可信损伤仍可有界上升。
- 快升：保持现有`FecV2Step`连续有效快速窗口触发、可信持续burst可上额外一级；不要拿数据量不足的两个tick当两条确认证据。目标档可以越级上升，但不跳到无凭据档。
- 缓降：复用老项目 **30s连续有资格低损稳定** 的行为，向Off比普通下一级更谨慎（参考旧60s及更强置信度）。一次只降一级；必须经过真实有效窗口/足够first-send样本与实际k模型，前一次降档已APPLIED且未处于burst/拥塞。用户接受**通常正常持续业务120s内降一档**，不是在低PPS、失联、测量不足时强行降；若60–120s仍无法降，报告具体 blocker/有效来源，不改判或刷seed。不要为了追求更快下降重写成熟RS/FEC。
- 修改policy时仅**一个 Rust actor**拥有状态和deadline，Windows/Linux双方复用同一决策核心；原Go `FecV2Step`保留回放oracle与CLI config解析，但真实稳态不再由Go每200ms ticker/2s Poll驱动。操作者变更低频传 `requested`，Rust真正合法block quiescent和认证反向M2给 `applied`；down一步允许保留真实成熟历史，其余切档/reset按现有source-scoped规则。

## 4. Keepalive/Quality/M2 合并，服务器“没收到包”的边界（双端都接）

老项目事实：`runtimeentry/lifecycle_health.go` 默认 Keepalive **15s**、客户端 `dead-after 90s`，验证 `dead-after ≥ 3×keepalive`；`runtimeowner/control_policy.go` 的一次 `tickControl`优先Quality+idle，若没有新quality则按真实Health期限发送，成功才顺延、失败≥1s backoff。控制包不会ACK-of-ACK。老服务端 `lifecycle.go::tunnelInactiveAt` 的 `max(90s,3×keepalive)` 是**租约/后续admission清理**的无认证记录判断，不能当作正常无业务立刻断线；`LifecycleServer` 的常规DORMANT还要求**客户端FIN/PeerWriteClosed + 本地payload idle**。不能声称这些已经在新V4产品生效。

本批把同一个 `ControlTlv::Receipt/LegacyHealth/LegacyQuality` 由 Rust native kind1/现有AEAD唯一PN编码，按已认证、同epoch/代次解码；M2/质量/Health到期能装一条则合并，不增加另一套协议、独立每lane timer线程或多余无业务探测。若控制MTU不足，必须有有界优先级和下一到期，不能截断校验/丢失仍称成功。仅新质量/反馈事实更新质量窗口，Health可带真实业务 idle；成功的已有Quality发送可以刷新Health due；静默不新质量时保活到期独立发送。可有界抖动但只在真正控制发包时调用RNG，非生产包日志。**保活包属于认证活性，不属于业务payload活跃；无认证/仅原始TCP ACK不等于alive，缺Health只是UNKNOWN而非强制idle。**

明确有效配置/回读，Windows与Linux client/server一致：`keepalive_interval`（建议初始继承15s）、`dead_after`（建议90s，且≥3×interval）、`idle_dormant`（用户可选，**默认0禁用**），同时显式区分`server_inactive_lease_reclaim`与`server_dormant_after_fin`；不发明新的“收到任意TCP包即存活”开关。已有旧Go CLI名字 `--keepalive-interval`、`--dead-after`、`--idle-dormant` 仅为映射oracle；当前V4的实际参数请在已有CLI/config schema和GUI设置上接线，readback输出有效值，禁止只解析不生效。留出不会把Health当业务刷新idle的计数。

用户需要验证**三种不同结论**：
1. `interval=15s,dead_after=90s,idle_dormant=0`：无payload但收到认证Health/Quality的空闲隧道持续活着（例如≥180s），健康不误判为断线，Go及Rust空闲CPU/唤醒接近事件等待；双端Stop仍可主动关闭。
2. `15s/90s/idle_dormant=60s`：实际业务安静，客户端及服务端确认对方idle才允许客户端 orderly FIN；服务端只有观察到 in-order FIN 且payload idle才DORMANT；随后新真实业务触发客户端WakeDemand/有界重建且首包不冒充已送达。若V4的Dormant/Wake尚未产品接线，要明确UNWIRED，**不得拿keepalive将连接超时替代休眠**。
3. 保活/反馈按真实netem或有界夹具阻断，超过`dead_after`确实没有任何已认证记录时，客户端判断不健康并有界重建；服务端仅在原有租约清理条件满足时可回收，不可因短暂丢Health/业务静默抢先清理。Game一条lane失联只影响该lane，其它healthy lane继续业务。核对Stop/WAL/lease无泄漏。

## 5. 真实夹具/网络矩阵：先Fixed与Game，Auto永远最后

**基座**：昨天已开发的 [Windows-Linux V2](../testing/WL_PERF_HARNESS_V2.md)，`scenarios/*.json` 及 `wl-outer-repair-manifest.json`。在既有schema/校验与Actions上最小扩展 mode/effectiveFEC/Health/idle/timeout/laneCount，不复制生成器或新一套统计学；两端真实signed Windows Wintun/Npcap＋Linux raw/TUN（Linux↔Linux场景同样复用现有真实network namespaces/netem）。同一个SOURCE唯一构建、产物manifest hash校验；性能**一个 Action=一个场景=一个测量job**，新旧若A/B在同runner按顺序Stop/清理后运行，不跨VM比CPU%。独立场景才并行。拒绝假稳定seed、盲增buffer、只统计幸存报文。

**历史matrix oracle**：`docs/evidence/fec-network-work/20261026-W168-56case-UDP-ARM64-AMD64-Matrix-Completed.json` 是 7模式×4损伤×ARM64/AMD64、10Mbps每向、75ms单程、20s/场，共56个 scoped observation，不是56个低残余保证；`...W168-250Mbps-UDP30-Fixed6-ARM64-AMD64-Native-Results.json` ARM64 PASS、AMD64容量INCONCLUSIVE；`...W103-Game2-Game4-fixed6-outerDATAoff-real-clean-PASS.json` 是3Mbps+少量TCP清洁环境证明。**矩阵借模式/损伤/指标，不继承旧SOURCE资格、绝不强加所有受限宿主250Mbps。**

**先实现全部代码和V2夹具再集中跑**：
- **便宜门**：Rust/Go编译+编码/owner/代次/MTU/partial NPF copy/uncertain/stop/0Go包循环静态和单元回放；V2 schema/有效CLI/manifest/原W103/W168相关反例。模块测试不是产品PASS。
- **Fixed功能与受控网络（先于Game）**：两端真实固定 `light/balanced/maximum` 的有效读回及真实M4源/冗余/恢复；其余4档用共享codec/配置/边界与必要代表性native正例，别为单helper跑7遍全链路。两方向以原W168为主：10Mbps×75ms×1/5/15/30%真实tc；另代表性50Mbps×150/300ms×1/10/30%（若宿主足够）；混合UDP96/288/1060/1200和独立TCP流、真实p99/outer字节/Stop。能恢复的损伤场显示真正RecoveredCandidate→Wintun首次交付，不要求不可实现的“30%零残余”。
- **Game2/Game4（仍早于Auto）**：Off和Fixed6为主，同样10Mbps、75ms、1/5/15/30%，少量混合TCP；Game4普通与已有错峰due代表性测试。原W103 `outer DATA off` 与 Fixed6 组合只在明确设定的场景验收；独立lane的原生capture/PN/去重与坏lane情况下其它lane首次交付，FEC源/奇偶/logic packet仅计一次，Stop后2/4句柄释放。不要把Game逻辑副本计作Normal DATA重传。高流量从能力可承受的一档递增，容量截止停止更重同族。
- **Auto最后**：完成上述Fixed/Game+Health基础后，再做Normal Auto初始Strong、真实网络升档/缓降、双向独立direction/revision/Applied、慢变恢复和真实Wintun/NPF+Rust M2质量。用固定好scenario与业务量，不因为短样本<512强迫降档；正常有效业务预期≤120s降一级；高损1/5/15/30%下快升、capacity/UNKNOWN冻结、失联不变零损。最后合并第4节 Keepalive/Timeout/Dormant 场景，给出临界时间、有效配置读回、真实服务端动作与主动Stop。
- **同机成本A/B**：旧Go steady vs Rust NativeOwner同Windows host/VM/driver/NIC、同模式与流量，完整进程含Go+Rust+kernel线程CPU秒及/GB/百万包、首发p99、offered/delivered、tc实际丢包、Npcap drops、RSS/handle、idle wakes和Stop；不能以“Go线程几乎0”代替整个产品CPU下降。旧Go仅供真实基线，不保留为最终生产packets路径。连续压测容量或runner CPU/PSI瓶颈须标CAPACITY_LIMITED；产品单核/锁瓶颈不能甩给宿主。

**观测口径必须齐**：每向 `offered, first_unique_delivered, late/duplicate, p50/p95/p99, true tc drop delta, NPF send accepted/uncertain/not-attempted, TUN/Wintun write/drop, F/R/control/outer byte, FEC actual k/r/planned/sent/recovered/expired/pressure, M2 quality valid/unknown/censored/revision requested/applied, Game per-lane first copy/logical duplicate, Health sent/received/merged/suppressed/last_authenticated/payload_idle, timeout/FIN/Dormant/Wake, worker and whole EXE CPU/RSS/wakes, Stop handle/ring/loans`。生产只保留低开销聚合，测试诊断显式opt-in抽样；记录来源以区分产品、夹具、容量与错误判断。

## 6. 验收不过度收紧 / 文档与收口

Hard：原Go TLS真正认证/代次与地址隔离、AEAD/PN、原密文重传、MTU、真实驱动前缀、首次源包无跨业务HOL、Ready独立、owned Stop/WAL、参数读回、Go稳态0包泵。Soft：同源CPU有可测的净改善且不显著劣化p99，真实负载下Auto快升慢降、合理残余与内存有界；**不新增任意99.99%或所有损伤“必须0丢包”的门**。若达到host knee，正直报告环境上界并停止高载；不得拿容量问题掩盖产品锁/单核瓶颈。未测物理、GUI、lane rotation如实NOT_RUN/UNWIRED，旧FAIL保留。

每个有产品改动的批次新建短devlog记录意图/来源/原因/精确SOURCE/Actions结果/未验及feature-impact，并更新 `docs/features/entries/{fec-fixed,fec-auto,game-lanes,game-fixed-fec,idle-rotation-keepalive,windows-native-transport,linux-raw-tun}.json` **实际受影响项**；不无谓向旧长日志追加。阶段/暂停/交付边界做一次 cursor-only H，保留在途run和精确证据；main抢先更新刷新合并，不force/整树覆盖。**该文档入库本身不构成产品代码、测试或平台/性能/物理PASS。**

```feature-impact
{"kind":"none","ids":[],"reason":"本提交是获授权的M0施工契约/热提示词压缩；产品FEC/Game/Health参数和运行实现未在本批变动。M0实施批应按实际产品变化更新对应feature cards。"}
```
