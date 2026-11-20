# H2234｜低丢包高负载 TX 失速的因果定位与完整优化验收

状态：**DIAGNOSTIC SOURCE ONLY / PRODUCT OPTIMIZATION NOT YET PROVEN**。
接续 H2233，在它的独立 PR 分支之上工作，不覆盖主线 M0、PR #55 与旧 029 的证据。

## 不能变的执行契约

Go 原生 TLS 1.3、冷认证/lease/generation/OS/GUI 与 Rust 原生 long-lived owner 保留。真实 DATA 首到、乱序即交付，绝无跨流 HOL。外层 FakeTCP 的 ACK10/SACK/window 只负责 TCP-like 外观；机会式 repair 仅原密文、有预算、有次数与年龄上限，不能改成可靠有序流，不等外层 ACK 才送 fresh。AEAD/PN、租约/重放、MTU、FEC 现有门限、Stop 的 owned join 全保留。任何调优都不能用 Go per-packet 回调或隐式新线程/新 FIFO 换数字。

## H2233 已确认的两个不同损伤

1. 高速固定200ms无额外jitter，Action44764736732（SOURCE 6c1996c）：12/12 真TCP应用成功，但无损直连上行612.631 <800 Mbps，**不可称产品高速因果 PASS**。原生客户端 1% connection-generation `SharedTunReader queue_full_drops=49529`、`backpressure=75625`，5%分别9209/16262；每个 generation 累计3s上行、20s上行、20s下行，不能分配至单项。对应 1% TX worker CPU 累计12.63s（会话约65s），证明真实本地拥塞却尚不能定性为 CPU 算力不足、慢唤醒或 raw socket 拒发。
2. 15ms jitter 的 Action44768861776（SOURCE413c7ed）：容量约21Mbps（DERP/relay），相同丢包档无本地队列溢出，但有很深的 `lagged32` 乱序计数。不同 VM/source/吞吐，**不是固定vs抖动因果 A/B**。原始 iperf `-M1037` 只是 requested；7/8 有效分组从真实 `ss -tinm` 回读到四流各1025B，另一个 UNKNOWN。
3. direct 的 netem `drops/(emitted+drops)` 与 WBD 不可当作 TCP segment loss 比率：GSO skb/接口 TX包计数粒度不同。所有来源必须保留原始计数、不同维度、前后快照，不按目标1%/5%冒充真实字节损失。

## 当前代码因果图（每次不同阶段独立账户）

| 边界 | 实际唯一Owner/界限 | 必需的定位证据 |
|---|---|---|
| 内层TCP / kernel TUN | Linux TCP BBR / wbdc0队列 | 实际内层 negotiated MSS、socket RTT/cwnd/retrans/GiB、TUN rx/tx/drops |
| SharedTunReader | 同一Go进程**唯一 Rust** TUN物理读取者、每次最多8帧 | read→route计数、每路pending当前/峰值/年龄/溢出、线程CPU/runqueue wait、停顿 |
| per-route pending→M4 inbox | 每路8个待处理、64KiB、100ms及每路64-slot sync inbox | `backpressure`/实际 `queue_full_drops`/oldest age；不能扩大为跨路缓冲/等待 |
| 原 M4 TX | 单线程消费每转最多32条、原始M1 loan、AEAD/PN、FEC有界调度 | TX thread CPU/wait、source_queued→M4 copied、M4 `tx_backpressure`、原有诊断计数 |
| raw kernel socket | sendmmsg 在 Entry 锁外，真实 copied prefix | EAGAIN/outq/内核拒发、actual first-send、local queue_age；无第二次PN reseal |
| 对端原M3/RX/TUN | 原 Rust owner；乱序即成功交付 | raw_observed→unique→TUN-delivered、replay/AEAD错误与真实业务 RTT P99 |

## 本批具体诊断方式（opt-in、无逐包日志）

- Linux 线程名的 `comm` 最多15字节；历史 `wbd-original-m4-tx` 与 `-rx` 被截成同名，外部难以区分。将**现有同一线程**稳定标识成 `wbd-m4-tx` / `wbd-m4-rx` / `wbd-tun-reader` 等短名，绝不生成新 owner，不变 ABI/wire。
- `WBD_H2234_TRACE=1` 时，独立于 Rust/Go 数据面的 root Python observer 按**200ms**读真实 `/proc/<native_pid>/task/<tid>/schedstat`（CPU执行ns、runqueue等待ns、调度切片）、wchan/上下文切换以及该进程 network namespace 的 `/proc/<pid>/net/dev`（wan0/wbdc0 tx/rx/drop）。每20s case至多400个样本且不超过100秒，停止信号由该测试拥有，保存 monotonic_ns 和完整source/run。任何缺失显示 UNKNOWN，不能硬算零、不能据一个采样宣称逐包p99。
- 同case标 iperf 客端单调起止ns、实际接收goodput、MSS真实在途 `ss`、TCP重传和ARM qdisc skb/readback。原始外层 repair计数和 Rust shared-TUN Stop 继续归属于原session，不能造每case队列丢包。
- **仅本分支**的有源性能实验使用 Normal/off、GE1/5%、额外单程200ms、零额外jitter、同VM顺序 Direct/WBD。先跑两方向12s8p clean Direct；任何方向低于500Mbps则立即完整记录 `NOT_RUN_LOW_LOSS`并结束（节约Runner），至少500才做定向瓶颈观察；项目原两方向**>=800Mbps**产品因果准入资格保持不变。低于800的诊断数据真实，但不能作为高速优化效果。
- H2231 的UDP RTT/CPU/RSS另有活动PR；无需并行重新做全损伤矩阵、FEC、Windows/ARM跨平台全部重扫。不同source不做CPU改善因果比较。

## 后续「完整优化」选择树

A. **TX runnable wait持续突增而CPU并不忙**，与TUN溢出前的时间桶一致：查线程执行权、`recv_timeout`唤醒事件和轮转公平。修原唤醒/处理量子，按路新DATA无需等旧路，最老等待时间与空转唤醒一同验收。

B. **TX CPU持续接近单核上限、runqueue wait不高**：按原 M1 owner锁/AEAD/数据副本/计数索引分类CPU开销，消除可证明的重复工作并合理复用批量，保留低包速即时首发及FEC/feedback独立期限，不能直接补队列。

C. **kernel raw EAGAIN/outq持续增长**：只在原sendmmsg owner处理有界机会与额度、free fresh而不重封密文、不对外层等待确认。产品接线与真实driver回执成对施工，不能根据MBps随意上调系统全局缓冲。

D. **共享锁竞争**：减少不必要的持锁批工作或改为锁外只读不可变结构；不得复制第二套 crypto/control/packet routing 状态机。

E. **网络/测试对照本身不足**：先修真实segmentation/MSS与容量可比性，停止改产品，不把基础设施低容量或 netem skb分母当产品算法失败。

任何整改都要同时完成 Rust 双端受影响路径、caller/配置/夹具/旧功能卡、最小针对性单测与原反例；同VM冻结源码做前后 A/B，按 receiver GiB/CPU-s、小TCP/UDP实际p99、memory/wakeups/Stop和no-HOL通过。改善只转移到别处或拉长发送排队则判 FAIL。修完整原因而不是为了某条报错贴补丁。

**当前实现边界**：此文对应线程可辨认＋外部只读诊断，不代表 A–D 中任何产品优化已经完成或真实高带宽复验PASS。
