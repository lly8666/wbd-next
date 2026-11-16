# PLAN029 H1972｜只追几十微秒的冗余调度，旧差异微小不重做

## 已有真实业务基线：没有任何新跑出来的数值
原真实 Windows2025/Wintun/Rust TX+RX→WSL2 Linux kernel TCP46119，SOURCE `dc2d1904ee3e487b9ac307086be189a8ba053a83`，[Action 43804841097](https://github.com/lly8666/wbd-next/actions/runs/43804841097) Artifact 14197958732，**2048×1024字节已建连请求，物理/Direct原应用SHA/FIN/owned Stop PASS**。本任务将原Log `PLAN029_H1966_STEADY_INGRESS_QPC_FINAL`（2080个含预热）与 `PLAN029_H1966_STEADY_LEGS_QPC_FINAL`（4160个）以及原Windows app send/recv QPC按端口/时钟/每窗口1024字节严格重连，得到下表。它是**原SOURCE的离线深读**，不是“新性能提升”。

| 真Direct同Windows QPC阶段 | p50 | p95 | p99 | 属于 |
|---|---:|---:|---:|---|
| 原Windows app send前→原Wintun `on_packet`开始 | 15.9μs | 20.5μs | 30.4μs | WinSock/Wintun/kernel（未测ReadPacket时间） |
| NAT完入列→内核inner socket真正读到 | **34.4μs** | **45.4μs** | **59.8μs** | 原TX→原RX→Wintun写入→TCP内核回送→TX读取，含无谓轮次 |
| inner已读→physical完成写 | 10.0μs | 17.2μs | 27.3μs | WinSock/Rust服务，非纯Rust CPU |
| physical写出→physical读回 | 104.5μs | 140.7μs | 163.6μs | 真实Linux guest+物理TCP，不是分流器净开销 |
| physical读回→inner完成写 | 2.2μs | 3.7μs | 4.8μs | 双腿返程小阶段 |
| inner完成写→原Windows app读完回声 | **47.9μs** | **61.5μs** | **75.1μs** | Windows内核TCP+Wintun回环（缺RX SendPacket时间戳） |
| 原 app 总RTT | 218.8μs | 277.6μs | 318.0μs | 单机顺序原Direct臂 |

上表可按每窗口时间顺序作为进度观察；分位数不可相加当同一个请求。上两个突出延迟中位数是约34μs和48μs，远超分类/NAT的0.2/0.3μs，所以此阶段**不再优化规则分类，也不追共享CDN同真实IP极端用例**。

## 最小源码动作和安全边界
- 在**唯一原Rust TX`tx_loop`**保留旧32条Reverse包先转原`direct_return` FIFO；之后本轮`stage_sources`刚收到真实Wintun Direct TCP DATA/ACK时，**可选第二遍最多8条**交给**同一原RX worker**的既有256有界channel并`direct_notify`唤醒。这是新入队包第一次真实出队，而不是新线程/另外的Wintun reader/writer或TCP协议伪造。
- 源锁强签名五重条件 `m0_v4_probe/GITHUB_ACTIONS/WBD_PLAN029_NATIVE_V3_TRIAL/WBD_PLAN029_P2_MIXED_SCENE/WBD_PLAN029_P2_STEADY_QPC_SCENE`，再加明确的 `WBD_PLAN029_P2_POST_INGRESS_FLUSH_SCENE=1`；**正常产品OFF**。旧先发32条、原队列超限时对TCP`requeue_tcp_reverse`回原头、UDP可丢/Disconnected fail closed，原Stop/WAL全原样。
- 新原Rust owned Stop打印唯一 `PLAN029_H1972_POST_INGRESS_DIRECT_FINAL delivered=N max_per_turn=8 sole_original_rx_owner=1 joined=true`（不用每包IO日志）；正数必须来自原Windows signed Action，不能拿合成测试填数字。
- `tools/m0_plan029_h1972_gap_attribution.py`真源码结束后读取Windows同一QPC的`on_packet`/NAT/inner/physical/app阶段，逐条2048个请求按1024字节检验，Stop不全、来源不一致、任何负延迟均FAIL；工作流先跑合成5例和Win/Linux原Rust编译。
- **成败标准**：若新SOURCE正常已建立Direct p50相对H1970没出现**至少约20微秒量级**改善，或 `NAT→inner read`没有明显下降，不能将本变更宣称为性能修复；前后不同VM/Action之间仍只能说观察，不能宣称同VM因果。若确实大降，再考虑同一Windows SOURCE的ABBA重测及产品默认。
- 不更改早期物理preconnect OFF，不改Game4/GUI/D1–D5/P1高率，不重复4MiB重载；保留用户要求的“忽略微差、只搞明显差”。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add gated bounded same-TX-turn Direct reverse mailbox fast handoff to target original 34us queued-to-kernel-read delay; strict 2048-message QPC gap analyzer; product default remains OFF and true speed improvement unverified."}
```
