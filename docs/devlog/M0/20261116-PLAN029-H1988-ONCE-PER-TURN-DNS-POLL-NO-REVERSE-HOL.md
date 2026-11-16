# PLAN029 H1988｜按用户性能优先：DNS 同轮重复 WSAPoll 导致跨流开销

## 首个可以从产品源码直接证明的热路径
- H1974 真 61–63ms TCP 长尾及原4次重传仍 OPEN；H1978 同VM一源2048小流 Direct p50/p95/p99=521/620/682μs，而物理269/334/381μs，SHA/FIN/Stop scoped PASS、原QPC Action FAIL。不同SOURCE不能判定尾延迟已修。
- 原 `NativeSplitWorker::poll_udp_reverse` 在 TX 每轮最多32次 Direct 回包出队中，每碰到 DNS lane 且 `dns.has_work()`，就**重复**调用 `DirectDns::poll()`。即使同一个 DNS UDP 查询仍未完成，或只剩已完成 packet，也会重新做一次最多16项的 `WSAPoll(timeout=0)` 和临时 `Vec<PollFd>::with_capacity`；普通 Direct UDP 或 TCP 回包的公平轮转因此可能承担非本流 syscall/分配开销。最多32是上限，不是已测真实每轮调用数。
- 新代码只在原 `NativeSplitWorker::tick` 的**一个**原 Rust TX owner 调度轮次开头，在同轮 Journal 完成回执之后、Direct 返回出队之前，对确有 `inflight/awaiting` 的 DNS 状态调用一次 `poll`；`poll_udp_reverse` 的 DNS lane 只从已有完成 FIFO `pop`。保留三类 TCP/DNS/UDP 的公平逆向轮转、原 RX 唯一 Wintun writer、256 mailbox、UDP局部丢弃、TCP回包保序、单DNS endpoint/同endpoint UDP→TCP，不加线程、socket、WFP、时钟轮或跨flow等待。
- `DirectDns::poll` 改为固定栈上16槽 `PollFd`；零待处理时不造 heap。Windows Rust `cfg(test)` 只增加一个调用计数器，回归向原 DNS SERVFAIL 完成队列加入8条，不打开物理socket或触摸Wintun，`tick` 和8次出队后应仍是**0次不必要DNS poll**，并且8条本地DNS答复完整交付。这个测试是逻辑/CPU机制检验，不是实网性能签名。
- 本 SOURCE 编译/单测/真正 CPU每GiB和p99 **NOT_RUN**；首先收自动的 Win/Linux Rust 与治理 Actions，不重复 H1974/H1978 原2048诊断；后续只在有新有效假设时做一个正常业务混合测试。P2真实61ms和完整D1–D5/P1–P2、GUI/Game4/IPv6仍开放，但本轮不扩极端工况。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1988 normal-path CPU/HOL optimization: poll physical Direct DNS once per original TX owner turn, never inside 32-item reverse dequeue, use fixed stack WSAPoll array; Windows pure unit regression, source CI/performance NOT_RUN."}
```
