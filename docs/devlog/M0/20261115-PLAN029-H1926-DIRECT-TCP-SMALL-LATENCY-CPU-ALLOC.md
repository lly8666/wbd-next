# PLAN029 H1926｜Direct TCP小请求真实时延 + 一次真实CPU热路径减分配

## 先验已证
- H1922 signed source `b0fa293733cbd56a4e5df6add8dc5b474cc7cb15` Action43716329886 real Windows/WSL2: physical/Direct 10GiB 500/700Mbps full kernel SHA/FIN/Stop PASS；同机原Go+Rust CPU/GiB Direct-physical +12.281/+10.604s（只进程user/kernel，不是driver ISR/DPC）；Rust relay service `277318` turns、`184302` progress followup、`93016` zero-progress turns、`queued_copy=1039196`。
- 4MiB物理41.294ms vs Direct118.804ms +77.510ms是**大流全程时长差**，不可称固定每请求延迟。H1916/H1917真实4MiB失败说明不能再次把任何真实读写进展后续票据抑制掉。

## 产品热路径最小改动
- `v4_windows_native_tcp_direct.rs` 的 `tick()` 每轮`Vec<u16>::new()`、随后每次正进展`push(port)`导致常见1项堆分配/释放。原代码一轮最多 `MAX_QUANTUM=8` 条流，延后公平enqueue，所以改为栈内 `RelayFollowups{ports:[u16;8],len}`，越界显式失败，**不改ticket公平队列、event readiness、读写的原始any-progress继续语义、64KiB量子、owned Stop、现有缓冲/保护阈值**。理论可消除每个有续票据的turn上的小堆分配，但实际CPU减少幅度**未测，不预报百分比**。两条Rust纯回归覆盖全8项严格FIFO、不漏/不重、正进展仍续/无进展仍停、越界不会静默丢工作。
- 延迟专门补`tools/m0_plan029_h1926_small_tcp_latency.py`：同一原签名Win2025/WSL2、同原产品进程/owned Wintun及FakeIP，不开第二虚拟网卡；原4MiB全收件+FIN/UDP通过后使用已存在的WSL2物理TCP46112 grant，真实kernel listener sequential A-B-B-A `physical,Direct,Direct,physical`，每种64B/1KiB/16KiB，32组（每种每方向64连接，总384连接）。Windows `perf_counter_ns` 按真实connect→send→SHUT_WR→首个echo byte→完整echo→kernel FIN划段，输出真实分布p50/p95/p99而非将4MiB耗时当固定RTT；Linux同时严格核验序列、peer确实为物理source、原样echo、SHUT_WR/FIN，SHA聚合与Windows相等。仍由现有整段96B Tunnel UDP 流和两端original owner Stop兜底，无1ms空轮询、无每包日志、无自造协议数据平面。
- 原Windows/WSL2一条source锁Action使用`[plan029-v3-real-p2-bulk]`＋`[plan029-v3-real-p2-small-tcp-latency]`，先真4MiB通过，再384条小流+UDP/Stop。**不再同时运行10GiB**；先看首个p99/首错及Rust小缓冲调度是否能保持全量交付。H1926SOURCE新产品未签名PASS，不把旧H1922结果偷换成新CPU性能证据。
- 全PLAN029 D1–D5/P1–P2 GUI/Game4/IPv6/padding/压力和同VM旧新二进制CPU A/B均OPEN，028限域不重开，030未开始。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1926 bounded stack relay follow-up optimization and source-locked original small TCP physical/Direct A-B-B-A 384-session latency fixture, pending real Windows/WSL2 evidence."}
```
