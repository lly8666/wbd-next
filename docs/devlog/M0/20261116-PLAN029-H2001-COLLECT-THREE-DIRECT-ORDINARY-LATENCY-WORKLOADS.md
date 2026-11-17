# PLAN029 H2001｜收齐三类普通 Direct 真性能：UDP p99 60–91×第一优先级

- H1997 SOURCE `e200061997839ef3697a826742c2eb4d1a34b41f` [签名 Action43855958211](https://github.com/lly8666/wbd-next/actions/runs/43855958211) 真 Win2025/WSL2 original Wintun/Go/Rust TCP、owned Stop **SUCCESS**：2048×1KiB 已建连接 Windows QPC physical p50/p95/p99/max **0.288/0.355/0.410/0.649ms**、Direct **0.544/0.647/0.699/0.878ms**；p99 比1.705×，绝对+0.289ms。这轮无61ms但历史H1974五次真长尾仍OPEN；同轮paced1MiB 305.854/304.072ms，Tunnel UDP120/120 p99 4.682ms。
- H1998 SOURCE `7c26f38c5baf253ccf4a9f5805ab6ba0ed214af0` [签名 Action43857978655](https://github.com/lly8666/wbd-next/actions/runs/43857978655) 原生 **SUCCESS**：4MiB无pace原kernel TCP物理 **51.970ms**、FakeIP Direct **97.260ms**（1.871×），两端同SHA/FIN，Direct比物理上传+23.938ms、下载+22.148ms，接连/首回包差均较小。120/120 Tunnel UDP p99 **6.359ms**、回包最大间隔32.311ms、双方Stop PASS。Rust真实TCP ready最长3ms、WinSock event error0，未证实全局HOL。4MiB总耗时不是单包p99。
- H1999 首个 SOURCE `412bef6a2431f882aea37a74bcef57e10ce43714` [Action43858589556](https://github.com/lly8666/wbd-next/actions/runs/43858589556) **FAIL**于廉价旧静态断言未接受显式guest mode3；真实业务、Stop当时NOT_RUN，原FAIL保留。H2000 SOURCE `839e161a90a8c8017848dab1327f60673e38e05d` [Action43858907438](https://github.com/lly8666/wbd-next/actions/runs/43858907438) 修准确mode3静态入口之后重新原生 **SUCCESS**；真CN DNS/FakeIP→Windows原应用→Rust physical UDP→WSL2 kernel→原Windows 应用回复、原双方owned Stop全部PASS。
- **H2000 Direct UDP真实应用RTT p99是本批绝对首要异常**，各120/120无丢、无重样本：96B physical/Direct **0.347/21.725ms**（62.608×）；512B **0.282/25.684ms**（91.078×）；1200B **0.350/24.974ms**（71.354×）。Direct p50各14.024/13.796/15.560ms，**360/360个Direct RTT≥8ms**；物理p50约0.2ms且360/360没有≥8ms。没有数据丢失不能冒称低延迟PASS。
- 第一代码机制：原 `v4_client_direct_udp_actor::poll_reverse_ready` 使用 `WSAPoll(...,0)`，`v4_windows_native_runtime::tx_loop` 对活动UDP只给旧 `needs_10ms_poll` **<=10ms timeout**，无物理UDP FD_READ 事件唤醒；这一结构与包长无关、全部>8ms的真测量高度吻合，**尚未做同SOURCE事件边界因果实测，保留OPEN**。应优先在现有单Rust TX/Stop及有界公平轮转接事件驱动UDP回包而不是1ms忙轮询、逐flow线程或极端容量开发。TCP目前已有WinSock shard事件；不得为UDP把Tunnel等其他流卡住。
- 不混不同比例的SOURCE/VM作精确因果、不拿Tunnel UDP p99冒充Direct UDP；本批没有Rust/Go产品逻辑改动，不改写旧H1974真实60ms失败，也不复活028/030/16k饱和测试。性能验收 **OPEN**，正常功能PASS与Direct延迟适合与否是不同判据。

```feature-impact
{"kind":"none","ids":[],"reason":"H2001 records three genuine source-locked Direct latency scenarios, prioritizing pathological UDP p99; no product code or feature changes, prior failed Action preserved."}
```
