# H2241｜1% 下游瞬时饱和的单租约内核反馈 A/B/A（仅候选）

**不是产品默认修复；只在独立Draft PR验证候选。** 接续H2240真x86单流→四流→单流：单流源队列满为0/14包，四流增至20,064包，最严重相邻200ms窗口共丢6,231包；对应M4 TX 500ms CPU约74%，之前另一次2,749包/200ms附近约40%。源SHA `8c9272f8126b140d3f62b90c84da8b781b43be3b`，Action `44839906785`，独立签收 JSON `docs/evidence/M0/PLAN029-H2240-GE1-SHARED-TUN-200MS-TWO-FLOWCOUNTS-20261121.json`。**这证明发生短时局部反压，不证明某个Rust指令是坏的。**

## 针对已经确证的边界作受控实验

原Rust物理 SharedTunReader **仍只有一个**；原认证租约和内层路由规则、原路由队列8包/64KiB/100ms及M4 64项 channel **完全不变**。当前源reader收到下游 Full 时会把等待包留在原小队列，之后继续读 TUN，原队列满则实丢新包；4条内层TCP造成短时供给超过M4消费。

测试候选仅 `WBD_H2241_ONE_ROUTE_PRESSURE_GATE=1` 冷启用：reader每轮原无等待的 `flush_shared_tun` 后，取得即时、**不持有到休眠中的**路由表 try_lock；必须同时满足：

- **恰好一个仍活着的经过认证的 SharedTunRoute**；pending也恰好是**同一租约同一generation + Arc alive**，且原8个包小队列确实满；
- 此时最多短睡125→250→500→1000µs，以便原M4消费/原TCP内核TUN生产端得到真实队列反馈；每次醒来立即flush原最老包，未等任何外层PN/ACK/损失修复/FEC；
- 其他租约入场、当前路由更换或分发队列可用则**立即按原逻辑继续读**。绝不将一个满租约的等待强加给**同时存在**的别的租约；不额外创建thread/mpsc/有状态transport，停止时原Stop仍必须关闭真实Linux TUN和所有worker。默认完全关闭，不能给Windows凭此直接套用。

这只是一种有界的内核反馈可行性原型：**从Rust转移到TUN qdisc丢包、或让新业务p99变差时也必须否决**，即使Rust local queue-full下降。不允许将这一方案在已有多租约场景偷偷激活，也不得称其已证明全业务无HOL；附Rust负例分别检验第二租约、旧generation、失活、未满拒绝。若证据显示性能改善，仍需要明确新路由入场延迟/公平性、Linux TUN qdisc backlog年龄、Windows Wintun等价分发机制、Normal/Fixed/Auto/Game2/4及小TCP/UDP p99的完整受影响路径之后才可配置产品默认。

## 真实收据与验收

同一Linux x86 VM/同一SOURCE、GE目标1%+单程200ms，先后独立原Go TLS/Rust 4TCP流 **原reader→冷启候选→原reader** 各20秒，前后真实Direct容量引用。每代独立真实TUN、AEAD/PN、原修复机会策略、原Rust Stop。跟踪 `H2240` reader200ms、M4 TX500ms真实CPU/出包、TUN qdisc/link before/after、receiver-goodput、重传/GiB、本地queue-full和pending age、候选总阻塞微秒/次数及触发条件。两次原baseline离散、随机损伤未锁seed，任何吞吐收益只能称有条件，不支持跨VM百分比。

产品的永恒红线：标准 TLS/TCP-like、乱序 DATA 立即交付、没有按序等内层/外层旧包造成的跨flow HOL、单个native Rust数据 owner、FEC截止不等、原密文PN最多一次机会式表演重传、原MTU/认证/重放/Stop。**本轮未动外层wire和生产默认。**
