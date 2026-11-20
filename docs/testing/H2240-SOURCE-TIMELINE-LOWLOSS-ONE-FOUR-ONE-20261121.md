# H2240｜GE1% Shared TUN→M4 失速的时间桶归因

**仅诊断。** 依 H2239 已证明的 5% netem/GSO 对照不公平（真实 x86+ARM 6/6 真 Go TLS/Rust 业务、Stop 双平台均通过），本工作转向 1% 已记录的**真实 Rust Shared TUN 入口满队列丢包**。Main、正式M0 cursor、活动 PR55/59 和用户物理 Windows 均不覆盖。

## 为什么要做

H2237 x86 在同一1%源 GE200ms 四TCP流下有队列满 **118,281 / 52,138 / 118,167**（600→250→600，仅测试），而实际receiver goodput **242.6 /253.8 /268.2 Mbps**，未证明通过降低流上限增加吞吐；H2238仅变小 `fq quantum` 保留600上限，同VM A/B/A x86/ARM也未稳定改善。5%有时本地几乎不满但吞吐明显低，H2239 双架构真网络已证明Direct GSO计数粒度与WBD外层包不匹配，不能误判为同5%损伤。这些都不授权扩队列、外层可靠TCP、修改用户默认fq。

**原缺口**：单个完整connection的 `queue_full_drops` 不足以知道哪个200ms最先溢出、TX CPU等待当时有没有同步停顿、4条流是否才触发本地局部超供给。平均CPU没满，也不意味着每个200ms TUN/TX负荷没有失衡。

## 本轮实现

- 只在**既有原Rust唯一SharedTunReader线程**中，`WBD_H2240_TUN_TIMELINE=1` 冷诊断时最多 **240个200ms时间桶**，读**已经存在的**路由分发原子计数器（delivered、backpressure、queue-full/age/bytes/retired），并只在时间桶读每路小队列累计占用量及最老包已等待ns。额外`tun_batches/tun_observed`仅每**真实TUN批次**追加两次计数，不逐包、不读密文/身份/PN、不创建线程、buffer/等待、mutex/网络协议、无Go逐包回调。默认完全关闭。Stop只输出一条收口。
- 同时复用**已有** `WBD_PLAN028_EXTERNAL_STAGE_DIAG=1` 单独只读原M4 observer 500ms出包/CPU/反馈stage原子快照，不在原TX每包写日志；原有H2234外部/proc真实TID CPU/runnable wait诊断继续。
- Rust使用已存在的原生 `clock_gettime(CLOCK_MONOTONIC)` 与原应用 `iperf3` 启止时钟完全同源；夹具按真实20s业务区间过滤、检查每个窗口/线程源、单generation、确保递增的原子计数器；缺日志/失真/时钟不对明确FAIL/UNKNOWN。只写时间桶累计计数与差分，不输出任何载荷/明文、原密钥和业务IP。
- 同一个x86 Linux Runner中仍真实Go TLS/Rust TUN+AF_PACKET、三隔离 Linux netns + L3 veth router、GE目标1%/+200ms固定，依次原生原配置 `**一条内层TCP→四条TCP→一条TCP**` 各20s。每次独立client TLS/lease generation、真实Rust SharedTun Stop，Direct四流20s前后容量守卫，源锁hash和原始 iperf receiver bytes/内层TCP retrans/MSS、路由器 qdisc/interface计数、原stage/proc。此处 **GE随机实际轨迹不锁seed**，每阶段真实tc损伤可有所不同，不允许把差距当严格因果性能百分比。此实验只判断是否随竞争流量上升出现时间相关的local overflow，不用于多VM/物理Windows速度认证。
- 分析目标：定位最早的 200ms `queue_full` 增量、最大突发、`pending_packets/oldest_pending`、`tun_observed`与500ms `m4_copied`和线程CPU/runnable wait之间的时间关系。若多流集中于本地读入短时溢出且TX正有剩余能力，才继续拆现有TX进度和唤醒；若流量已超过原处理能力应以真实系统有界公平反馈设计缓解，但不能固定250或靠缓冲堆积；若无真实local overflow而网络TCP仍低速则回查同损伤粒度与拥塞恢复/FEC。须保持初包/P99和四流之间公平。
- 完整**产品修复**暂未开始。任何后续有源改变都需同VM修前修后receiver goodput/实际GiB CPU、真实丢包/ACK/低速p99、Small TCP/UDP、独立Stop、Normal Fixed/Auto/Game2/4及跨平台的受影响路径验收，不能仅凭几个窗口减少给产品标PASS。

**永不改**：标准 TLS/TCP-like表现、原加密和签名、乱序首到立即交付/无HOL、原单owner、机会式**表演型**有限原密文外层重传（无持续DATA PTO/不按序等旧ACK）、FEC独立期限、MTU、generation/重放、owned Stop。
