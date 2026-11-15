# PLAN029 H1882｜Direct TCP 热路径：无积压直送对向内核，背压才入有界FIFO

- H1877 [同VM真P2](https://github.com/lly8666/wbd-next/actions/runs/43663127990) 4MiB无pace，物理50.606ms / Direct141.030ms(+90.424ms,2.787x)，下载额外61.822ms，Tunnel UDP120/120及owned Stop PASS。H1880 Win2025真实128 loopback同分片双活事件测试PASS但不是128个Wintun业务flow。性能出口OPEN。
- 原实现每次kernel TCP read都先进入Rust TX单64KiB scratch、再**复制进入每flow VecDeque**，然后写向另一条TCP kernel socket。H1882改为没有任何旧pending字节时先从现有scratch直接write到对向Socket；只将部分发送未完成后缀/WouldBlock/Interrupted或存在旧pending时拷贝入同一个64KiB有界队列。绝不允许新数据超越旧队列（真实TCP FIFO），短写和wouldblock后同service quantum不反复进行同一Socket syscall，等待FD_WRITE/进展事件。
- 两方向完全对称。保留每向64KiB和8MiB的真实allocated预算、单64KiB复用scratch、单Rust TX worker、WinSock16分片/8flow额度、DNS/Tunnel/Go/OS lease、半关闭、FakeIP精确NAT及owned Stop。冷环境变量`WBD_PLAN029_P2_RELAY_DIAG=1`时在既有1Hz聚合加`direct_forwarded`与`queued_copy`字节计数，不将指标当CPU或性能证据。
- 新单测覆盖精确short write, WouldBlock, old pending FIFO不可越序，以及两条真实loopback TCP legs双向4KiB可写不分配queue、双FIN完成。需收新的Win2025/Linux platform组件、Rust actor编译/业务和同SOURCE签名NormalCN 4MiB+持续Tunnel小UDP+Stop。H1882本批全部**NOT_RUN**，失败按首错修复，旧H1877性能基线保留，不把跨VM old/new称A/B；Game4CN/GUI真实ConnectStop/IPv6 socket与D1-D5资源满仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1882 no-backlog bounded Direct TCP scratch-to-kernel fast forwarding; preserve short/blocked FIFO/halfclose and add low-rate byte counters, performance NOT_RUN until signed tests."}
```
