# H2242 | 统一 Linux TUN → SharedTun → 唯一 M4 的有界公平流控因果试验

M0 独立 Draft 试验，继承 H2241 已拒绝独立短睡（不向main合入）；本分支**不改用户默认**，不偷用其他作者的活动worktree，不回写cursor。真实Source、Action和结果提交以后再评价。

## 首个故障和不可避免的队列守恒

原 H2241 Action `44847350573` 在同一 x86 Runner + GE1% + 200ms 单程延迟 4个TCP流做 A(原读) → B(仅当一个路由满则短睡reader) → A'。接收端真实 goodput 267.847/319.747/265.633Mbps；Rust SharedTun 丢25940/2185/50467包，**内核TUN驱动TX dropped=0/38670/0**，TUN 的 `tc fq` drops一直0。原M4 TX真实CPU/GiB 10.22/11.64/10.22s。候选产生的3.17秒累计等待和最长1.897ms真实睡眠说明只压Rust入口**不能消除**源端总量与消费能力之间失配；只是把丢包从 Rust 原8包小队列推入内核TUN `ptr_ring`。现有Linux TUN txqlen **2048**（内核可按dev->tx_queue_len缩放其ring），不等于 `fq` qdisc统计。盲目增加 TUN 2048→4096会增加内核隐藏排队/p99及跨流HOL风险，不能算完整修复。

只要应用内层TCP生成速率在一个持续窗口内超过原唯一M4的**实际**可消费速率，而系统不让发送TCP感知反馈，任意有限内存最终都会满，必然丢包。根因必须从**原始TCP公平生产/有界背压**与**原TX owner服务能力**联合解决，不可能通过把有界缓存从层A搬到层B而让容量守恒消失。

## 本轮正交交付：相同1%真实源+两ISA+多层丢包总账

同一VM/同一SOURCE/三真实Linux netns、真实Go TLS 1.3和Rust单数据owner、Linux原TUN AF_PACKET、真实BBR 4流iperf、GE目标1%额外单程200ms，四个独立TLS/Stop generation顺序：

| 阶段 | Linux自有TUN原qdisc | 原8包Rust队列 | Rust唯一SharedTun reader |
|---|---|---|---|
| A | 原 `fq maxrate600mbit flow_limit256` **每流** | 原样 | 原样 |
| B | **仅测试夹具** `cake bandwidth 450Mbit besteffort flows rtt100ms memlimit4Mb`，真实有界**整条TUN总速率**＋内层五元组公平与ECN/AQM | 原样 | 原样、无短睡 |
| C | 同B（不改变物理M4、内存与协议） | 原样 | 仅单活租约匹配原generation满8时的H2241短反馈 |
| A' | 新原client generation恢复原Go配置 `fq600` | 原样 | 原样 |

- B和C把不同TCP流的突发反馈提前到原内核生产端，不从Rust reader偷走别的租约的处理时间。使用已有可信Linux `tc`、只在**新建的当前WBD客户端自己拥有的 `wbdc0`** 操作；原始Go内核设置和配置参数/driver/MTU/代码不变，退出后回归原qdisc，无host/global sysctl。4MiB是明确的**试验期内核AQM总内存上限**，不是吞吐改善证明，也不是一个默认积压区。
- 原B/C受测试临时450Mbps总上限约束，而A是每流600Mbps。**绝不能用本轮结果证明“固定450Mbps应该写成用户默认”或高性能无损链路不受限**；后续若有价值需要设计基于实际M4 copied和queue占用的事件式服务率反馈，不能另起稳态控制器/Go逐包回调/每包动态tc。
- 每case原生收据同时记录：WBD receiver bytes/20s和原iperf TCP重传，路由器网络GE实际计数，原M4真实CPU ns/同步sendmmsg/批次，Rust SharedTun queue_full/age/bytes、最大200ms失速，**内核own TUN `tc fq或cake` qdisc真正drops/packets/bytes与`ip -s link tx_dropped`分别做差**。UNKNOWN不能填0。还需独立的单业务小UDP RTT p99 和新接入路由延迟，当前H2242 A/B/C/A网络四流阶段本身**不是**这两项最终验证。
- 双ISA x86/ARM各自真实同VM同Source做顺序A/B/C/A，**不跨VM用绝对CPU对比**。随机GE netem在Ubuntu24.04不支持可读回seed，是同参数但非同包损伤；前后Direct的实际接收Mbps作为容量守卫，差值只能解释为该测试的方向性证据。

## 可入选的完整设计

- 容量通路必须**按租约分隔 + 按内层流公平**；已有Rust原M4为唯一PN/AEAD/seal/实际sendmmsg/反馈owner，不能新增队列、双控制器，也不能把TCP-like outer变成可靠有序第二套TCP。
- 每一层都要证明总丢包（Rust SharedTun + 内核qdisc + TUN driver）不放大、**业务首到和p99不会被隐藏积压拖坏**。仅Rust drop趋近零而kernel丢大包无效；仅让Direct变慢或只提高WBD/Direct百分比无效；仅增CPU占用亦无效。
- 源率若长期高于M4消费者能力，有限缓冲必然耗尽：正式方案必须通过有界而公平的网络/内层TCP反馈来调节生产，配合原native owner真实处理进度测得服务率；不能靠扩大8/64/2048队列或临时1ms读停顿长期隐藏。
- C会重测原H2241的多租约路由反例，**但新租约在单次睡眠中的最多等待未被实际独立业务p99验收之前，不得宣称全局cross-flow无HOL**；如B能独立改善，优先在C中去掉门控，避免额外reader等待。
- 5%的Direct/WBD损伤粒度原H2239已实际双ISA证实不等价；要以禁用TSO/GSO/GRO后的真实同粒度底线/低档原FEC继续检测，和1%的本地丢包放大是不同问题。

生产底线：原标准TLS、TCP-like原位窗口/ACK外观、乱序**首到立即交付**、无HOL、原密文/原PN**机会式/表演式**仅一次外层repair、原FEC/Stop、Rust单DATA owner、原MTU/lease/generation/重放完整性。Windows/Normal Auto/Fixed/Game2/4尚未从此测试获得任何生产收益资格。
