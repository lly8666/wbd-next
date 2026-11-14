# PLAN029 H1858｜压缩FakeIP日志重编码离开共享TX，单场未限速P2真实容量探针

- H1856签名P2 `c110a982` 1MiB/4ms人工节奏：Direct328ms、同VM物理281ms、120条持续Tunnel UDP（最大间隔16ms）、真Stop PASS_SCOPED。该场**非峰值吞吐**，并未覆盖高压下跨流HOL。
- H1857 Action43613384092 **在途**：单VM顺序原V4/off与V3/all-Tunnel/on的50Mbps各60s，独立P1；绝不重复dispatch。H1858只打开一个独立SOURCE的`[plan029-v3-real-p2-bulk]`新场景，使用4MiB unpaced，两条WinSock测试socket同负载；原1MiB/4ms默认不变。Linux WSL2 guest无法默认继承Windows任意环境变量，故bulk标识显式作为固定argv传给两个平台子进程；避免伪造两腿相同测试。
- 原`FakeJournal::maybe_compact_after`虽已实现一个有界async writer和durable receipt，但高水位时多MiB`encode+load_journal`验证仍在共享Rust TX粗tick执行。H1858把这一重编码/CRC完整读回挪到同一**既有**磁盘worker；TX仅每≥60s且≥12MiB时clone受保护pool snapshot并验证无pending，仍不在DATA逐包扫表、不增线程、不修改FakeIP key/TTL/ref/隔离、fsync/rename纪律。生产Stop继续join原writer。
- 纯Rust已有`async_compact_keeps_quarantine_and_only_latest_mapping`测试验证数据和重启恢复，下一SOURCE的Windows/Linux Rust测试在提交时**NOT_RUN**；实际慢盘Stop、directory fsync可用性及高压最老队列年龄仍OPEN，不夸大已验收。
- P2 bulk场景仍测SHA/FIN/同VM普通socket、全程Tunnel小UDP唯一交付/p99/最长空洞/Stop；CPU归因不是本场新完成。整个029继续IN_PROGRESS、028限定、030未开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Move FakeIP journal multi-MiB compact encoding and verification off shared TX onto existing bounded disk writer, add one explicit unpaced 4MiB native P2 scenario after 1MiB low-latency recovery; P1 separate in flight."}
```
