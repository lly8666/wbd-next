# PLAN029 · 原生吞吐与交付效率

2026-11-21，M0 当前施工包。先 Linux ARM64 Normal/off，再 Linux x86_64、Windows Wintun/Npcap 和受影响模式。本文发布设计，产品资格待测。029/029B 的其他出口继续开放，030 未启动。


## 2026-11-22 用户追加授权：分三关施工（本节覆盖下面的旧“先 ARM 公平”优先顺序）

**唯一实际顺序：P0 无损完整产品 → P1 FEC OFF、机会式重传 OFF/ON/OFF 的 1% 后 5% → P2 固定最高 FEC maximum。** 这是对 PLAN029 吞吐分支的追加执行指令，不宣称 029B/其他既有出口已完成；原下文 ARM 调度及旧负结果保留作背景和必要跨平台回归。只授权方案、测试与后续受约束的施工；本文档提交本身**不是**新增代码实现、跑测或默认晋级。执行入口：[M0 永久提示词](../prompts/M0.md) 与 [PLAN029 任务提示词](../prompts/M0-PLAN029.md)，原始实验账本 [11/21–22 TCP审计](../evidence/M0/PLAN029-TCP-PERFORMANCE-EXPERIMENT-AUDIT-20261121-20261122.md)。

### 不可偷换的事实、目标、成本与不变量

- H2292 [44951274107](https://github.com/lly8666/wbd-next/actions/runs/44951274107)：真实两组各3 runner，原 Win2025 signed Npcap1.88/Wintun0.14.1 → Go TLS/Rust → ARM relay → ARM Go TLS/Rust/AF_PACKET/TUN，0ms/0% 同机 A默认TX8/NPF16KiB → B TX16/64KiB → A′，组a 129.189/189.617/125.835 Mbps、组b 119.277/139.332/110.180 Mbps，CPU/GiB均下降，160/160 echo 和 Stop PASS；**B opt-in，未默认晋级**。H2290 [44940140123](https://github.com/lly8666/wbd-next/actions/runs/44940140123)：Windows 进程 kernel CPU占约82%，TX明显重要，但**未证明 Npcap 某个 syscall 是唯一瓶颈**。
- H2309 1% [44991491013](https://github.com/lly8666/wbd-next/actions/runs/44991491013)／5% [44991490836](https://github.com/lly8666/wbd-next/actions/runs/44991490836)：Windows BBR2 内层真实 SIO_TCP_INFO；5%本机 Cwnd常 5–12KiB、对端 SndWnd约8.45MiB、4/4 bulk 未完整 receipt；H2310 [44991706281](https://github.com/lly8666/wbd-next/actions/runs/44991706281) **无 WBD 的裸 Win BBR2** 5%也塌窗，不能承诺把隧道修好就能让 FEC OFF 跑 400Mbps。
- H2294 [1%](https://github.com/lly8666/wbd-next/actions/runs/44967314404)/[5%](https://github.com/lly8666/wbd-next/actions/runs/44967314336) 原 Win FEC OFF repair ON 实测原密文重发可为0；H2270 [44918335232](https://github.com/lly8666/wbd-next/actions/runs/44918335232) Linux 真 ACK/SACK 联动 R>0，仍**没有 P99/吞吐胜利**。H2307 [1%](https://github.com/lly8666/wbd-next/actions/runs/44988210204)/[5%](https://github.com/lly8666/wbd-next/actions/runs/44988771435) 固定 FEC light/mild 的跨机反转实验有真收益，**不是 maximum 的性能资格**。
- 实际代码核对：crates/wbd-engine/src/v4_windows_native_runtime.rs 的 在 PR #68 的实际在用源码中，外层一轮调用 (RX_WAKE_BATCH/BATCH) 次 stage_sources()，RX_WAKE_BATCH=32，因此 TX16时是2×16=32源（TX8时4×8=32）；send_fixed_parity() 一次最多4个parity，且每轮当前仅调用一次（约行1074–1145、652–705）。**持续源包每轮都满32时，4/32=12.5% 是该轮 parity/source 调用额度的推导上界，非已测 r_sent；实际欠账仍要看期限和已发送计数**。FEC v2 maximum 为 k=16、r=20、名义125%冗余；真实partial用 ceil(k×1.25)，编码/driver/timeout都可能进一步限制实际产出。
- 预算：400Mbps **有效源**、maximum125%名义冗余的理想外层净载至少 900Mbps，另有IP/TCP/TLS-like/AEAD头、回传、机会式修复与其他业务；**600–800Mbps 只能是无损阶段进度目标，不能称 maximum 400Mbps 的出口资格**。TCP 400ms、400Mbps BDP约20MB聚合，不是 SharedTun 排队预算。
- **不得突破**：原 Go 标准TLS/OS冷控制、Rust长期 native owner、TLS-like/TCP-like appearance、原始业务已认证 DATA 立即独立首发/交付、无跨租约/流 HOL；原 Seq/PN 冻结密文最多一次机会重传、R/F高负载约≤10%、无持续DATA PTO/新可靠TCP栈/伪造内层ACK/逐record M2；bounded各队列、真实 M4 driver accepted-prefix 不冒充远端交付、有效 AEAD、真实MTU/Stop/WAL、不得逐包Go FFI/常驻busy-spin。用户可以固定 FEC maximum，不以 Auto 调档作为本任务前提；现有固定档 wire 契约不偷偷改变。

### 统一复用夹具与一次性测试门（不得另造第二套长流程）

1. **先收在途与预检**。M0刷新 main/registry/cursor/PR #68（Draft）/实际 HEAD，核对当前源代码是否已合入。原实验主要在 PR #68 的 experiment/m0-029-throughput-arm-fair 上；**main 只有部分选择性 H2292/H2301/原记录，不能在 main 上假定 H2292–H2310 所有脚本已存在**。分支中复用 tools/m0_h2276_three_runner_tcp.py、m0_h2285_windows_wsl_route.py、m0_h2286_{full_windows_product,arm_product}.py、m0_h2292_true_product_ab.py、m0_h2293_true_product_fec_loss.py、m0_h2290_windows_hotpath_cpu.py、m0_h2309_win_tcp_info.py、m0_wl_loss_tcp_probe.py 和各已有 tests；禁止复制一整套新 Go/Win/TUN runner。既有 workflows：qa-h2292-true-windows-rust-aba.yml、qa-h2294-win-arm-fecoff-repair-loss1/5.yml、qa-h2307-fixed-first-loss1/5.yml、qa-h2308/09/10（裸TCP/窗口对照），只在**必要参数或测量确实缺失**时给现有脚本/工作流加小分支并升级 exact tests。若当前分支缺某脚本，先 fetch 相应精确源 SHA 及依赖，不能凭本计划捏造入口。
2. **先小后大、必要复测不设人为次数上限**：T0 离线 Rust 单元＋Python 测试、静态 source/manifest/hash、Windows/ARM cross-compile，目标不到一次完整跨机网测；T1 现成 Linux ARM 三 netns 或同机 Win 真 Wintun/Npcap 原 owner 短验证、1个真实宿主，测正确性与局部服务；T2 **先一套3 runner** preflight，Tailscale最终真正 public endpoint直连（拒DERP）、真实两向 qdisc readback、原产品 GoTLS成功、WSL keeper PID/bootID/iptables生存、签名驱动、source/manifest一致；clean relay/直连能否达到独立≥800Mbps标作容量资格（不足停止**吞吐归因**，可保留功能证据）。T2通过才在**该组三台** A/B/A′25s×4bulk＋160稀疏TCP echo，保留远端 receiver unique bytes/receipt、CPU s/GiB、P50/P99/迟回、driver copied prefix、线字节/F/R、队列年龄/丢包、Stop。首次单组三腿确认环境、指标与机制有效后启动第二套独立3 runner复现；对真实故障的源码修正可根据新证据继续测试，不设“一次失败就停止”的硬限制；若同机A/A′漂移覆盖B改变，标 INCONCLUSIVE 只精修首个因果差异，不做无限重跑。尽可能复用已存 H2292/H2307 的原始A/B/A′档、编译产物；**只要产品编译源改变，旧 DLL 不可冒充新 candidate**。构建一次，两个候选 DLL 或配置唯一差异，hash/功能要素逐项读回。
3. **真实测试行程**：只跑当关必要条件；0%下先验驱动/Goodput，1%/5%分开的 Action，不能一个长连续窗口串到下个丢包率；loss5可先做短25s供给＋有界远端receipt截止（建议相同夹具已有180/205s超时前加更短的只读诊断截止/阶段行），不让一个 FEC-OFF 5%已知 RTO 将两组三腿拖到多分钟；截断必须显式标 INCOMPLETE，不能填0/业务PASS。首先修 WSL keeper 停止断言/Windows AppliedSetting 数字0→Internet错误解析/历史汇总KeyError的**测试专用**逻辑；原红仍保留，只保证新测试有可信阶段和 cleanup。所有失败仍上载首个错误和现有artifact，不反复开“全工作流绿”的试验。
4. **三种独立判定**：功能/安全门（业务字节、checksum/AEAD、Stop、配置信息、真实回执）、机制门（指定变量实际生效：copied/TCP info/R/F/parity）、性能门（同机 A/B/A′ goodput、CPU/GiB、P99、小UDP及时率，不把吞吐转嫁给另一个租约）；**任一性能不合格不能伪称产品胜利，功能通过也不能伪称性能通过**。有效样本不必须达到假定600/800/400Mbps才能标某局部功能PASS；“达到高线”单设绝对门，环境<800/DERP则该门NOT_QUALIFIED。

### P0：零丢包先做大原生 Windows 真服务（不改 TCP/重传/FEC）

**固定条件**：原产品 Normal/off，outer repair OFF，0ms/0%和400ms/0%分别独立验证；Windows真实内层4×25s TCP＋160 sparse、实际 Socket buffer/MSS/CC、两端原GoTLS/Rust、相同物理公网路径和Stop。不要把 H2284 裸 OS TCP 8流1000Mbps 当成产品上限/直接可比 A/B。

- **P0.0 先拆问题**：在原有 H2292 工作流增强原 Windows CPU collector 的分阶段计数（仅每批／外部1Hz采样、Stop读回；不逐包QPC），Windows Wintun ingress可读取pps/bytes、M3 seal耗时/ready数、NPF send_batch呼叫次数/实际copied帧数/短前缀/uncertain、TX与RX用户/内核CPU、ARM真TUN receipt、relay tailscaled CPU/返向ACK量。检测4流供给是否真的持续；窗口/ACK不足时不能把服务能力低判为M4饱和。采用同一个 source 长度/pps、相同 Socket CC/buf/MSS，只在相邻A/B/A′改**一个**因素。
- **P0.1 首个已知低风险正改动**：从 H2292 原版 A TX8/NPF16KiB vs opt-in B TX16/NPF64KiB 开始；若源码不同，重新编译同源A/B而不是套旧DLL。接着把两变量拆开：A TX8/NPF16KiB、B TX8/NPF64KiB、A′、再另一独立配对 A TX8/NPF64KiB、B TX16/NPF64KiB、A′（分开的短试验，非每个候选都花6runner）。保留ready-only、不凑批、不加固定sleep；不盲加到64，也不改系统TCP模板。
- **P0.2 如果 TX 增大后没再增长**：沿 ingress→M3→NPF TX→relay→ARM RAW RX→M3 open→ARM TUN及反向 Windows 内层ACK 查**第一条**压力/空洞。若真正是NPF syscall/queue成本，减拷贝/锁/多次driver提交、合理批发；若ARM RX或返ACK限制，去修那个具体阶段；若4流供给/cwnd不足，先增加同OS已有供给流数做**诊断**（H2284 8流是容量控制），不把“开更多流”计为产品优化；先不引入需新签名NDIS驱动或AF_XDP大工程。CPU/GiB、尾延迟跟踪防止纯速率幻觉。
- **P0 现实可验收**：T0 owner/no-lost-wakeup/短driver prefix/Stop 单元通过；T1真实系统路径正常；T2同机 A/B/A′ 二独立组以 H2292 已证明的**≥10% goodput 增益且 CPU/GiB 不上升**为首个可达的增量验收（或明确若测得漂移不确定而不晋级）；160 echo仍真实、不得新增>1s迟回/跨流首到损害；两端Stop无残留。将绝对达标单列 **先稳定≥200、再≥400、最后在合格出口争取600–800Mbps**，每级只有客观达到才晋级，不因赶进度放宽或无限发机；**不把这些愿景作为前一小增量代码正确性的假门**。P0关通过后保留产物给P1/P2使用。

### P1：固定 FEC OFF，先1%再5%，保留“表演式”最多一次机会修复

**固定条件**：P0冻结的真产品TX服务版、同一内层TCP CC（优先对照原系统与明确选定 BBR2模板的隔离实验，不能强制用户系统）、实际SO_SNDBUF/RCVBUF固定/读回、MSS/GSO/GRO/双向qdisc损伤单位可比，真实400ms RTT（各方向200ms）；每个loss率单独运行原 H2294 的 **A:repair OFF → B:repair ON → A′:OFF**。FEC确实 OFF，不混入固定parity；先1%，仅1%机制/稳定成立再试5%。不要求外层变可靠TCP。

- **P1.0 便宜的必要条件**：复用 H2270 Linux 旧成功反馈参考，在现有 Rust M2/OuterAckIndex/Windows native owner 上增加严谨的**确定性单个丢记录**夹具单元：原first NPF accepted、真实已认证SACK gap、shadow仍有效→恰好一次复制旧Seq/PN/密文；无 gap/过期/超额度/未已发/重复/伪反馈→0；ACK外观不能当远端业务交付；正常0% R≈0。只在gap确实存在并且及时的条件下要求R>0，不能因为概率随机 1%/5%一次没触发就说代码错误。修 Windows ON 实际R=0的原因前，先分开记录：source是否通过、反馈是否形成、是否可覆盖缺口、预算/期限和driver是否复制；一次只改首个确证断点。保留10%高负载上限与低频稀疏绝对上限，不恢复逐record M2。
- **P1.1 真网1%**：已有 qa-h2294-win-arm-fecoff-repair-loss1.yml 的真实两向 netem、原始 A/B/A′与 WSL/Stop，优先先跑单组短 A/B/A′＋真实 receipt。强制两个方向独立统计 F、R copied（含uncertain单列）/R/F、SACK成熟覆盖、首次包损位置及小 TCP P99；若ON没有 R 仍能证明条件无 eligible gaps，记 NO_OP，不假称修复。能看到真实旧密文copy且基线恢复后不飘才算**机制PASS**；性能PASS另要求两组 B 有可复现有效receiver goodput或迟回/P99收益、CPU/GiB与UDP无实质退化，不能仅“复制1753条”晋级。
- **P1.2 真网5%**：复用 qa-h2294-win-arm-fecoff-repair-loss5.yml，仅当1%完成机制门；FEC OFF+5%已知Windows BBR2常出现 cwnd 5–12KiB、长RTO/0/4 remote receipt，**不设置“不可能保证的4流25s全部成功/400Mbps”为此关的功能门**。对相同供给窗口统计真接收独立字节／4流完成数／不足与终止原因；允许阶段 status DATA_INCOMPLETE 并以真实cwnd/TimeoutEpisodes/与裸H2310归因；若保护机制与有界Stop安全通过，可判“机会修复实现PASS；5%性能FAIL/OPEN”并推进P2，不因FEC OFF物理能力不满足而无止境跑测试。若 B较A/A′反而P99/CPU显著恶化，reject该策略，保留旧默认。
- **P1 静态/真实出口**：单机模拟的一次精确损失应观测0/1（不应2）复制；真实ON必须在有合格候选gap时确认相同密文copied；R/F ≤0.10 高负载、绝对稀疏预算、过期处理、无持续PTO、不妨碍新DATA与其它租约、两端Stop；5% TCP 本身仍塌窗是客观边界，**不能把“某种重传开启”包装为能匹敌裸BBR吞吐**。只有同源双组实际性能正增量才改默认（原则上仍可保持OFF），没有则停止该策略调优直接下一关。

### P2：固定最高 FEC maximum（125%），先解决应发/实发，再验损伤与成本

**固定条件**：沿用P0冻结TX路径与P1的修复状态（整个 P2 A/B/A′ **repair ON 保持相同**，若要单独区分FEC与outer修复需额外同机独立OFF对照，但非默认全矩阵）；**不研调Auto**。固定档由 Go 冷控制请求、ARM/Win双方真实 accepted/applied readback，旧wire合法，Normal/off不会带FEC状态。FEC v2 k≤16、maximum r=ceil(1.25k)≤20，partial k也必须计入，不能用“名义125%”冒充实际发送125%。

- **P2.0 第一枪只能是0%**：先 T0/单runner验证 fixed maximum 真 installed 且非偷用light/mild：k/r分布、source accepted、expected parity rows、actual scheduled、NPF copied、uncertain/not-sent、parity expired/host-capacity、RX recovered/unique delivered、wire bytes/CPU/GiB。Windows native runtime 当前每轮最多32 fresh后仅一次4-parity send_batch可能在持续满载产生**服务份额欠账**；证明或否证之前不能一边加大输入batch一边指望maximum达到设计比例。隔离高/中/稀疏源率，控制本机driver复制数；没有真实capacity时不强求已到期的parity被神奇补发。
- **P2.1 若证实饿死，实现有界工作守恒 parity service**：在既有TX owner上以 **parity欠账/按实际r目标计的deficit** 给准备好的parity有足够send轮次，随新source有入队机会则先即时首发且逐轮限CPU/待发送字节；随后按非空ready与deadline服务parity，可多次调用现有4-row batch但无“每循环只给4而源能拿64”的固定比限制；别用全局锁霸占或一次编码20行挡后续source，分片step且经source-ready再次检查；若 source+parity实际需求 > driver/出口能力，优先 fresh 与独立小包，按现有 Normal10ms/Game5ms parity队龄届满丢**过期辅助**，出报host_capacity/expired，不积压秒级队列、不回补过期不保活。所有 FEC 输出使用同一个driver真实settle，复制、uncertain、不发送分列；不新增FEC worker/逐包FFI/第二可靠层。优先改调度/短批节奏，**只有分析显示是真编码CPU瓶颈才改 ISA-L/AEAD 后端**。
- **P2.2 三段真网**：先0ms/0%固定maximum与原FEC OFF做同机短A/B/A′能力/成本对照；再400ms/0%读真实inflight/CPU、确认不因125%冗余自己造本机drop；再 **1%**、之后 **5%** 两向 netem，复用 qa-h2307-fixed-first-loss1/5.yml 和 H2293 true-product-fec-loss.py，把模式明确改为 **maximum → OFF → maximum**，repair ON三腿不变，不能把已有 H2307 的light/mild结果当最高档PASS。回传每流 send/unique receipt、TCP_INFO cwnd/TimeoutEpisodes、160小TCP P99/超时与可行的UDP小包、F/R、payload/parity/repair全部wire amplification、Windows/ARM CPU/GiB、parity deadline和Stop。任一组清洁链路<所需wire能力，则 performance标CAPACITY_LIMITED而非代码失败；不得因“高冗余会被物理链路丢弃”而无限加缓存。
- **P2 验收两层**：（a）可在短T0/T1中真正PASS的功能门：合法k/r，非0有效需求时 parity 到期前按可用capacity尽可能发全、source不等FEC、不会因parity挤掉早到小TCP/UDP、批次结算一致、无负内存/无重复ACK、stop/恢复、0%无莫名缺源/积压；（b）性能门：高线绝对分阶段记录，真实两套3runner A/B/A′ 在1%/5%至少展现相对OFF的TCP receiver goodput与尾时延保护，而非盲求5% 400Mbps。**逐级闸**：0%先证当前真实200Mbps以上是否可维持、再400Mbps；在确证外层>=900Mbps及安全CPU空间之前绝不声称 maximum下400Mbps业务可达。若理想FEC不解决TCP RTO，则回看反向ACK/残余、所有packet实际loss/CPU/队龄，不单纯把maximum加倍或无限跑级别。

### 人力/Actions 支出硬规则与交付

每个关口**推荐首轮配置为一轮静态/廉价native T0/T1，再一套合格三runner A/B/A′，必要时第二套独立三runner复核；这不是测试次数上限**。为查明第一确证损失边界、解决源码/驱动/恢复错误、验证不同独立反例或完成跨平台资格，可以投入所需agent工作量及追加真实Actions，不以节省成本为由省掉安全、正确性、双组复现和回归。每次追加都必须附可改变决定的新假设、精确源码及失败阶段，修正后定向复测；不得无新信息地刷seed或并行起1/5/maximum所有6 runner；任何DERP/WSL keeper重置/clean relay <800 的环境只允许记录环境，**立即停止该工况的性能收费**。已经验证的 H2292/H2307源码/完整artifact不因旧Action红重复消费；更改compiled product必须重新证明新源。变更默认前再独立复核受影响的 Normal/off、fixed maximum、Game2/4与原 Stop/MTU/GUI冷设置，以最小代表而非全笛卡尔积。

每关完成提供**一个短 devlog + 原artifact/源SHA + 表格**：操作系统、runner/CPU、direct最后状态、netem真实两向计数/packet粒度、MSS/offload/CC实际读回、真实OS sock buf、P99/160及late、4流好吞吐与completion、驱动copied/uncertain、F/R/parity和两端CPU/GiB、exact Stop；列按「功能门/机制门/性能门/物理资格/默认是否改变」逐格给 PASS/FAIL/INCONCLUSIVE/NOT_RUN。自动化仅在确认已具备且未在途后手动dispatch；成功即收束，失败先读第一异常、用旧artifact离线复判。**不调低测试期望去让红变绿、不制造probe流量、不冒充Windows BBR2实际应用或remote receipt**。

---

## 目的与已有证据

以接收端唯一有效业务字节为分母。提高可持续 goodput，同时降低两端 CPU 秒/GiB 和线上字节/有效字节，保护稀疏流首响应、及时交付率及空闲开销。原 Go 标准 TLS 1.3/OS 与 Rust 长寿命 owner 继续分工。独立已认证 DATA 首到即交付；新业务不等旧 PN、另一个租约、坏 lane、ACK 或 FEC 缺口。TCP-like ACK/SACK/window 和 TLS-like 外观、表演式机会修复沿用[章程](../../PROJECT_CHARTER.md)，只用原 Seq/PN 冻结密文、最多一次、已有总量与寿命边界，无持续 DATA PTO。认证/完整性、隔离、generation、防重放、真实驱动回执、[MTU 契约](../architecture/MTU_CONTRACT.md)和 owned Stop 是业务正确性边界。

| 已观测 | 改变哪个决定 |
|---|---|
| [H2236](https://github.com/lly8666/wbd-next/actions/runs/44787582885) 无损高包速时原 M4 TX 接近一核。raw 发送段中同步 syscall 占经过时间约 96%，含等待。 | 单独提高服务能力。先分清内核 CPU、调度等待与批量摊销。 |
| [H2240](https://github.com/lly8666/wbd-next/actions/runs/44839906785) GE1% 同机一流/四流/一流，Rust full 为 0/20064/14。四流 20 秒仅用 5.19 TX CPU 秒。 | 局部突发可先于平均 CPU 饱和。[整 reader 暂停](https://github.com/lly8666/wbd-next/pull/62)会把丢包搬到 TUN。 |
| [H2244 GE1%](https://github.com/lly8666/wbd-next/actions/runs/44858024963) 固定 450 降低 ARM 本地丢包，但吞吐和 CPU/GiB 都退化。[无损 x86](https://github.com/lly8666/wbd-next/actions/runs/44858243522) 固定 1200 使接收 1256→991→1247 Mbps、每批约 28→16→26，小 TCP 尾时延反而改善。 | 把服务顺序、批次和总准入分别试验。保留原版和已否决结果。 |
| [H2239](https://github.com/lly8666/wbd-next/actions/runs/44838335306) GE5% 直连与 WBD 的 netem skb 分段粒度不同，关闭测试卸载后两者比值大幅变化。 | 核实际 MSS、GSO/GRO 与双向损伤，再解释剩余差距；绝对 goodput 同报。 |

## 施工顺序与改判条件

1. **ARM64 第一增量，隔离公平调度。** 基于最新干净 main，在一条已登记短分支复用 [H2244 夹具与小流回显](https://github.com/lly8666/wbd-next/pull/66) 所需最小部分，先核原路径与旧实验差异。拒绝过的 reader gate、固定 cap 不随测试栈带入产品。原生三 netns、原 Go/Rust、真实 TUN/raw、Normal/off。在同 VM 做原 A → 候选 B → 恢复 A′。B 只改变已就绪业务的服务顺序，保留原既有速率设置、预算和 driver；租约之间公平，租约内流公平，空闲份额可借用。单包即发，有多包才批发，有界轮转；不等凑批、不停共享 reader。复用原 owner、队列与唤醒点，确需分类才增加有界状态。先 GE1% 四流叠一条稀疏 UDP 和新建小 TCP，再独立做 0% 高供给反例。若仍伤高线或 CPU，拆分定位分类成本、批次破碎与排队年龄；若公平本身足够，跳过额外调速器。
2. **独立提高服务能力。** 在入口固定时比较相同包长/PPS 下的每批已就绪数、实际 copied prefix、调用数、用户/内核 CPU 与调度等待。优化实测大头，优先去重工作、复用缓冲与原生批次。[#59](https://github.com/lly8666/wbd-next/pull/59) 的合成后端对照仅作线索，保留路由/PMTU/接口与 Stop 语义并经真实产品 A/B 后才采纳。若 TX 提速但应用无收益，沿反向内层 ACK、对端 RX/认证/TUN、应用读速找下一个饱和点；测上传和下载。每项先独测，再与公平候选组合以发现抵消。
3. **确有持续过载才加入总准入。** 原 M4 每批结算的 kernel accepted prefix、wire bytes、有效批量、活跃时间是本机服务量；每路需求、积压年龄与满丢指示入口压力。区分需求不足、本机服务饱和及下游受限。总预算按实际共享出口分配，多开流不多领租约份额。压力持续才收紧；需求仍在而积压退去，用真实流量小步向上探测，过载快速回撤。突发量由服务批次字节、MTU 和延迟预算推导，低速首包即时发。只在状态实变时用既有冷 OS owner 应用、核 generation/ifindex 和读回；无逐包 Go FFI、假探针或空闲轮询。内层 TCP ECN 要看到协商、真实标记和发送方响应；不响应的 UDP 在本租约内有界丢弃。验高→低→高和空闲→首包，能解除自身限速才采用。
4. **移植与出口。** ARM 可复现收益后，Linux x86 用本机旧新对照检查 ISA/内核差异。Windows 复用公平、批次、计账和反馈语义，使用原 Rust Wintun/Npcap 读写与唤醒、原 Go 冷管理。单 Wintun 同宿主顺序验证；按同一代际对齐实体 80–200 Mbps 与上行约 3 秒中断的 socket、TX/RX、Health/Stop。实体权限或机器缺失则保留 OPEN，先做可做阶段。验证慢/快双租约、丢旧包时另一租约新包、换代/Stop，以及受影响的 Normal Fixed/Auto、Game2/4，冗余与 FEC 独立计线上成本。跨机归因沿用无损双向 Direct ≥800 Mbps 的现有门；DERP/容量不足只作诊断。成功增量尽快集成，未验平台保持原默认。

## 参数可改，按量纲决定

可直接调大计算上不足的内部批次、缓冲或预算，可删重复的热路径检查、分配、复制与轮询。写明现值、负载假设、预计收益、最坏等待/内存与回退值；复用在入口、每批或代际已证明的条件。参数同步双方、平台、配置/文档及老配置行为。举例按 1000 B/包、1 Gbit/s 约为 125 kpps；若输入短时比服务量高 300 Mbit/s、持续 2 ms，积压约 75 kB。若出口仅 400 Mbit/s、排队目标 1 ms，可容约 50 kB，这股突发仅靠扩队列无法兼顾目标。若实际时间预算容得下且内存有界，可直接试算出的更大值。往返 400 ms、1 Gbit/s 的在途量约 50 MB，属于端到端窗口，不能直接用作 SharedTun 队列。以上是算例；产品值由真实包长/成本、租约数和尾延迟确定。

## 如何验收与停止

- 每次同一 runner/job 内顺序旧新，按项目契约分 leg/请求，保留恢复原版和短直连参考。记录准确的产品、夹具、配置、构件哈希及 run/attempt；ARM、x86、Windows 各算各自配对变化。保存机型/核与配额、内核/驱动、offload、实际 MSS、丢包注入单位与争用。原版前后漂移足以覆盖增益则记 INCONCLUSIVE，查条件；跨 runner 只比结论是否复现。冻结二进制复用，容量不足停同族重测。
- 同一观察窗记录接收有效字节、两端整机及 TX/RX CPU 秒/GiB、线上放大、每批成功前缀、队列年龄、RSS/唤醒。内核 qdisc 父子重合丢包给上下界，TUN 驱动与 Rust full 分列。小流同时报新连接首响应、已有连接 RTT、UDP 截止前到达数/全部请求、分位数和未回。160 次 echo 供筛选。分开租约 A 受损与 B 新流首到，确认 B 能独立交付。
- 测前写明本增量首要指标、旧版漂移带及可接受代价。无损高线、低损竞争各有绝对接收吞吐和单位成本。只改善一个计数、把损失挪层或以慢流饥饿换峰值则拒绝默认；有真实成本取舍按用户的性能优先级报告。每个增量只补受影响场景，累计完整资格后再推进默认。收到否证即保留旧路径和失败依据；完整出口还包括合格跨机、真实 Windows、独立小流和精确 Stop。合理候选均被配对反例否决且没有可区分的新假设时，交付约束点、负结果、可重开条件并结束该研究增量。

历史第一动作是登记并恢复 ARM64 公平候选的单工作线；**当前优先级现由上方2026-11-22用户三关追加授权覆盖**。历史测试证据与工具见 [H2244 汇总](https://github.com/lly8666/wbd-next/pull/65)。本文件和旧 PR 均不构成新产品 PASS。
