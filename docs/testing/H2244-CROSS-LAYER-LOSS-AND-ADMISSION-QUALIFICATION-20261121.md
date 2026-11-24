# M0 H2244｜跨层丢包转移可接受条件与统一服务率闭环：可执行判定门

**2026-11-21，独立干净 main 分支的第一项 TEST_ONLY 工作；没有更改产品配置、Go/Rust DATA、TLS、外层重传或 Linux qdisc。** 关联先行 [H2244 设计契约](https://github.com/lly8666/wbd-next/blob/59e48baf37edbeab7a9fe028fe3d6112db421d43/docs/decisions/M0-H2244-UNIFIED-INGRESS-FAIR-SERVICE-DESIGN-20261121.md) 在 H2243 Draft PR #64 上，尚未合 main。当前文件只将关键错误判断转为可测试的、拒绝假改善的跨层判定。不能据此宣称实际吞吐优化完成。

## 1. 先把“丢包下移是否还能修掉”回答精确

**可以，而且是值得保留的工程方向，前提是下层有机制把过载变成对源头有意义的信号，并且实际内层业务能因此减少拥塞/重传。** 合理的移动包括：通过按租约/五元组公平的有界入口调度、ECN/AQM，在数据进入单一 Rust M4 之前促使内层 TCP 发送端降低 *offered load*，让 M4 继续按 ready 批量执行。UDP 不能靠 ECN 发送端配合时，只能有界区分、丢弃并诚实报告；不能强制所有内层 UDP 等内层 TCP 窗口。**外层 tcp-like ACK 与机会式最多一次原密文重传都不是容量反馈闭环，也不能承担可靠恢复这些内层失包。**

反例：H2241 Rust full 25,940→2,185，Linux TUN link tx_dropped 0→38,670，实际 M4 CPU/有效 GiB 10.22→11.64：这是从能观察的 Rust 队列丢弃转移到 TUN 驱动 ptr_ring，不能称整体消失。TUN qdisc 与 TUN 驱动 drop 计数是不同层，qdisc=0 不能推断 TUN 无丢失。

另一反例：H2242 CAKE 虽使本地丢包显著减少，却令 M4 copied/sendmmsg batch 从 14–17 降到 2–4，CPU/有效 GiB 增加约 70–100%，同时交付下降。ECN/AQM 正确并不表示逐包调度粒度适合原 M4。

支持机制的候选：H2243 bench-only 总量 TBF450+fq_codel、48KiB 突发在两种 ISA 上恢复较大的 M4 batch、使 Rust 丢包下降而 kernel link 保持0；但 x86 CPU/GiB 仍约 +14%、小流并发 P99/0% 1Gbps/真实 Windows NOT_RUN。**保留机制，拒绝“直接把450 Mbps写为产品配置”。**

## 2. 一个权威、三个预算、两类反馈

- **入口公平预算**：Linux OS 当前自有 TUN 由 Go 冷 owner 安装/卸载；新生产政策若需要动态更改 qdisc，只能受源锁的 Rust M4 owner 批结算后生成低频状态事件，Go 既有 OS owner 去重、验证 generation/ifindex/确属 owned TUN 后应用并读回。禁止因 apply 阻塞 Rust 热锁。Windows 不照搬 `tc`，需要在当前 Wintun/Npcap 唯一 Rust owner 内具有等价的有界 per-lease/inner-flow 服务与 ECN/公平逻辑，不能给 Go 逐包回调。
- **SharedTun 租约预算**：原一个 TUN reader，现有每租约最多8包/64KiB/100ms pending 与64-slot M4 下游，队列满是预算信息而不是扩容理由。任何“反压”不能 sleep 整个 reader、不能让某租约阻塞另一租约，禁止失活 generation 恢复旧路由。未验证跨租约 p99 前不可动产品调度默认。
- **M4 服务预算**：只认实际同步 sendmmsg copied prefix、ready batch、线程 CPU、真实积压和真实接收 goodput，不把本地内核接收冒充对端成功。Rust owner 在自己的 TX batch settlement 中统计服务量（按约200–500ms *聚合事件*），保留 16–48KiB 作为待验证的合法“批次量纲”而非产品硬常量。No DATA、Stop、route 变化时不虚增业务、不发探针 record。
- **内层 TCP 反馈**：在可 ECN 的内层 IP/TCP 会话，公平 AQM 的 CE 由真正内层 TCP 交互反馈，以便源头减少 offered；未 ECN 或 UDP 的有界丢弃仍须被计入包损与应用 p99。不要伪造外层 TCP ACK/SACK 来“加速”内层 TCP。
- **服务能力自适应**：若连续 epoch 有真实队列年龄增长/下层丢弃，就渐减 aggregate admission rate；若仍有真实待发需求、各层无过载则受约束向上探测并快速回退，不能把受自己限速后的 copied/sec 当可用容量上限而永远卡在低速。跨 flow/lease 分配必须共享 **一个总预算**，不能每流各领600Mbps；不基于旧PN/外层ACK授权新业务。
- **0% 极限单核瓶颈独立处理**：H2236 原生 M4 TX 在极端本地供给下接近单核满载，sendmmsg 同步经过时间大头与内核 CPU 归因仍有边界。可沿独立 PR #59 的 AF_PACKET/RAW 源锁对照探索提高真实服务 `μ`；不可直接切绕路绕过原 PMTU/route/Netfilter/租约/Stop。全局 ingress cap 不能替代真正高容量下的服务能力改善。

物理守恒：若某时间窗持续 `offered_bytes > actually_served_bytes`，有限的 queue 必会增长；要让尾延迟与丢失受控，只能提高服务能力、减少提供负载（TCP 反馈/公平限速）或诚实丢弃低优先/已超预算 packet。队列搬家并不改变这一事实，`0 Rust drops` 绝非最终目标。

## 3. 真实证据的判定边界

新 `tools/m0_h2244_cross_layer_gate.py`、`tests/test_m0_h2244_cross_layer_gate.py` 接受带同一 SHA/RunID 的真实 source-scoped 数据，给出结构化 **拒绝生产默认 / 值得继续验证机制**。其覆盖：

1. **分母**：使用实际 iperf *接收端* Mbps × 同次观察秒数推导 delivered GiB；绝不使用 sender figures、跨 VM CPU、缺失字段=0、run FAIL 冒充 PASS。其它业务规模差异与真实 TCP retrans/GiB 应在报告并列，原始 dropped packet 不是同一业务字节的丢失率。
2. **层级**：内核 root/child qdisc drop 可能重复，必须给出本地落点总量的**保守上下界**，不能把 parent 与 child 无条件相加。TUN link tx_dropped 与 Rust SharedTun full 分开；只有候选的下界/交付 GiB 仍超过原始的上界并有足够余量，才可宣布“本地转移没有修掉”。反向只有候选的上界低于原始的下界，才说“本地层级丢包边界显著改善”，不推断 WAN 丢包消失。
3. **真正生产负门**：M4 copied/batch 骤降、CPU/GiB 显著上升、receiver goodput 实降即拒绝默认；受限回环和 source-aligned 负例只是诊断，不改变当前 main。任何候选无真正并发小 TCP/UDP p99、missing 包、Stop、多租约/新连接、Game/Fixed/Auto、Windows 物理验证，都只能判为 **机制研究，不是产品 PASS**。
4. **H2241/H2242/H2243 冻结示例**：同 SOURCE 内重现 reader-gate 迁移丢包、CAKE batch collapse、48KiB ARM 有改善但 p99 未验、48KiB x86 CPU/GiB 退化；未知指标、SHA 不一致、跨 run、无真实 owned Stop 直接报错。

这里的数值阈值仅用于**快速否决明显退化**，不是通过便宜静态判定宣布产品优化：8% CPU、60% batch、5% receiver-goodput 与 5%局部丢包上下界余量为当前诊断门，不取代同 VM 原始 A/B/A 噪声允许带与后续真实 p99 资格。

## 4. 后续必须从同 source、真实网络获得的闭环验收

先同 runner/client-router-server 三原生 netns、真 Go TLS 1.3/Rust TUN/AF_PACKET、真实 Linux BBR TCP 四流，把 A 原始、B 公平批次、A' 原始的同 VM 顺序对比放在0%高线和 GE1%/GE5%（netem GSO/skb 可比口径）不同源锁 Action 中。一条独立小 TCP 与 UDP Echo 必须真正与 bulk 同时进行，记录首包/p95/p99/未回、TCP cwnd/MSS/retx、root与child AQM/ECN、TUN ring drops、Rust full/age、M4 copied/batch、native+host CPU/交付 GiB、真实 Stop。GE seed 在既有 Ubuntu `tc` 不受支持，明确 UNSEEDED；不能跨不同业务 offload/GSO 做“同5%”归因。

若无损 >=1Gbps 基线但新机制固定450Mbps，则当场拒绝**产品**方案，即使 GE1% 的绝对Mbps上升。只有真正自适应的 aggregate rate、能证明源端反馈且小业务尾时延不变差、一个 owner/原PN原密文最多一次表演重传、真实新租约/Stop 安全，才允许在 clean main 派生**正式候选**；接下来分别核 Linux ARM 与 Windows Wintun/Npcap、Normal Off/Fixed/Auto/Game2/4、实体 Windows 上行3秒问题。不要合入携带已否决 H2241 reader gate 的 #62→#63→#64 测试栈。

**本分支产物边界**：SOURCE 原始 Action 结果不重写、不模拟新物理 PASS；main 和其它作者保留完整 ownership。仅开发真正可使用的证据判定工具与负例，生产实现和真实网络资格仍 OPEN。

## 5. 后续真正原生实测的判定（2026-11-21；不可覆盖旧 SOURCE）

为避免在静态 oracle 合格后误把测试机制直接放入产品，记录**两个 SOURCE 独立**的完整真实业务 A/B/A：

- **GE1%，200ms one-way x86+ARM**：源 `03bebcb1a5ef38825293894ba2b5f21459d12474`，Action [44858024963](https://github.com/lly8666/wbd-next/actions/runs/44858024963)，artifact x86 `14688383542`、ARM `14688507919`；[完整保留证据](https://github.com/lly8666/wbd-next/blob/28f6659cefb0e72db98d75a66bc1d1baac4b2b9b/docs/evidence/M0/PLAN029-H2244-GE1-CONCURRENT-SMALL-UDP-TCP-TWO-ISA-20261121.json)。真正 Go TLS/Rust 三原生 netns，四流 BBR TCP 20s 每阶段，加160 UDP/160 TCP nonce echo 并发，全部原 owner Stop PASS。相同架构 A / TEST_TBF450_48KiB / A'：x86 goodput **290.455 / 290.867 / 353.359Mbps**，SharedTun full **9,028 / 411 / 37,565**，原生 CPU/receivedGiB **7.623 / 7.448 / 7.310**；ARM goodput **333.885 / 313.479 / 358.341Mbps**，Rust full **99,450 / 396 / 77,001**，CPU/receivedGiB **9.998 / 10.907 / 9.983**。候选两架构内层 TCP retrans 极大减少，真正 TUN driver/qdisc drops 都是0，但**没有端到端吞吐收益**；ARM true CPU/GiB 退化。x86/ARM small UDP p99 约401ms（有2–7/160未收到），small TCP p99 在 x86 1712/2248/2368ms、ARM1701/1146/1225ms：有漂移而不能单从候选下降宣称完整小流功能升级。
- **0%高容量 x86**：源 `ffb2262b5d69e89b4ffdc6e4a063776476eadfc2`，Action [44858243522](https://github.com/lly8666/wbd-next/actions/runs/44858243522)，artifact `14689265232`，[完整保留证据](https://github.com/lly8666/wbd-next/blob/9aff153df08f4fca9690993fc771611f64e52469/docs/evidence/M0/PLAN029-H2244-ZERO-HIGHLINE-TBF1200-BURST48-20261121.json)。真实原生 Direct 参考 **59.844 / 61.917Gbps** 只是同VM内核veth而非独立WAN。A / TEST_TBF1200_48KiB / A' 接收交付 **1255.70 / 990.69 / 1247.14Mbps**，M4真实 copied/sendmmsg batch **27.72 / 15.86 / 26.17**，CPU/交付GiB **6.844 / 7.749 / 6.909**，Rust full **1,055,762 / 353,553 / 996,152**。候选内核 TUN driver drop0、parent/child fq_codel分别记录154,920（**同一事件可能重合**）；小 TCP p99 **3215 / 293 / 695ms** 大幅受益，但小 UDP p99 **4.05 / 6.43 / 5.36ms** 倒退，每次160个 UDP probe仍缺27–33个。**不能用少Rust drops或小TCP尾快当作+吞吐，真实bulk掉约20–21%、CPU/GiB升约12–13%。**

以上两个 Action 是**原生完整业务与Stop通过、生产吞吐方案拒绝**的不同结果；都使用真实A/B/A不同客户端代际，netem损伤不能重放相同 packet 序列，不可把 x86 与 ARM 绝对CPU作跨VM因果比较。曾有一轮源 `fa539e7...`/ `318af9b...` 因 `sudo ip netns exec` 没传 SHA/RunID，探针拒绝后完整 Action FAIL；真实记录保留，不逆向冒充早期PASS。

### 5.1 单一自适应权威的明确实施入口（只作为产品候选设计，不是本分支已实现）

**不再安排固定 250/450/1200Mbps TBF 的参数矩阵。** 要解决的是可测服务能力 `μ` + 源头公平反馈 `λ` 的闭环，同时独立处理不同业务的首响应：

1. **Rust原始M4已完成内核接受前缀是唯一 `μ` 事实源**：每个已有原owner TX turn 仅批量结算成功 copied/真实 wire bytes、原 `sendmmsg` batch size、实际 CPU/working-time，并读原唯一 SharedTun route 的 generation/队列年龄/满丢/lease 数。接收端真实成功另外报告，不将 kernel accepted 等于应用 goodput。不能从 `μ` 独自推导真实 WAN 可用带宽，也不能以源端被自己限速后的 copied/s 当最大 `μ`。
2. **事件驱动容量估计**：仅有真实业务时在已有原 M4 owner 聚合例如200–500ms的量，只有连续超额积压/实际丢包、batch和CPU证据足够时对总入口预算减速并保留至少原M4已证实的短突发；若仍有需求而掉包消退，使用有界增量向上试探，超额压力后快速撤回。没有DATA、Stop、stale generation时无 event/no fake packet。实测 batch从27跌到16、CPU/GiB升到7.75时宁可拒绝该整形配置，不将降吞吐粉饰为恢复丢包。
3. **OS只按原冷Owner应用低频有效变化**：Linux Go现有 owned TUN/ifindex/generation读回，阈值变化去重后由原OS配置路径执行，不能锁住Rust AEAD或再建一个持续DATA sender；按TCP五元组或真实租约公平、短有界token burst/ECN AQM，父/子 qdisc drops分开计。**注意实验中仅启用了 fq_codel 的 ECN 标志，没有 source-qualified 的真实 ECN marks/TCP ECN negotiation 证据；不能据此称 ECN 已有效减少源发送。** Windows使用等价 native Wintun/Npcap有界公平机制而非调用 Linux `tc`。多租约不能按每流数量获取多份总容量。
4. **0%真正 M4 满核与1%非满核突发是两类瓶颈**：服务能力根本提升应继续独立已存在的 [PR #59](https://github.com/lly8666/wbd-next/pull/59) 原生 Linux rawIPv4 vs AF_PACKET 内核发送 primitive 研究，不能把它的纯合成帧 ABBA（x86 paced100kpps CPU/receivedGiB raw2.890 vs packet2.659、ARM raw2.791 vs packet2.615）称为真实GoTLS/Rust产品提速，也不能由此绕过 Netfilter/PMTU/邻居、原密文/lease/Stop。先证真实端到端收益再提取干净的 opt-in 原owner后端。
5. **准入退出**：必须同时证明0% clean高容量不被限速、GE1%/5% TUN root/child driver/Rust不只是迁移掉包、四流吞吐与CPU/realGiB不退化、小UDP/TCP first/p99与miss真值、多租约公平、0-HOL新generation/Stop、Linux x86/ARM及受影响 Windows/Normal Off/Fixed/Auto/Game2/4。技术指标不达就保留原已合格主线而非重构外层 FakeTCP ACK/密文修复栈。

**结论：当前 H2244 只批准一种后续研发方向：原Rust唯一M4服务状态与公平入口的跨层反馈，按需动态调速、保持大批次与独立小流；不批准任何固定速率 TBF、整reader暂停、永久内核global调参或有序可靠外层重传。**
