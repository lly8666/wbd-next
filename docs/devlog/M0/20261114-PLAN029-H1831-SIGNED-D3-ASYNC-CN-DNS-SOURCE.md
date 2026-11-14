# PLAN029 H1831｜同SOURCE组件绿后，只触发一次真签名CN D3

- H1830源码 `d358374e58f7c22c34e82d585bba26d64d3a45a2`：Rust native component [Action43584886137](https://github.com/lly8666/wbd-next/actions/runs/43584886137) Windows与Ubuntu均success；governance/feature [43584886136](https://github.com/lly8666/wbd-next/actions/runs/43584886136) success；native-functional [43584886151](https://github.com/lly8666/wbd-next/actions/runs/43584886151) success。H1829旧失败保留在H1830 evidence和devlog。**这些均不是签名真实DNS联网验收**。
- 新独立D3源码候选：复用现有真Windows+WSL2原始Go/Rust、一Npcap+Wintun的`[plan029-v3-real-d3-multia]` **单网络场景**（同一Action内owned Stop）；不恢复028多模式矩阵/旧WFP，不重新派发H1825或旧网络。该标记选择一个D3 multiA+CNAME、FakeIP、Direct UDP回包链，真实成功后才能提升D3至此SOURCE PASS。
- 仅为这次真实验证，在`tools/m0_plan029_h1745_win_client_dns_direct.py`增加应用层第一次CN DNS答复的耗时及重试次数读数。它包含真实网络/可能磁盘持久化，**不把该总耗时归因于classifier或fsync本身**，也不伪造专用慢磁盘证据；数据、回包ID与多A FakeIP原负测保持不变。
- 仍需独立真实TCP53 CN新FakeIP延迟回执、slow-fsync时Tunnel小UDP p99与最长空洞、后台compaction跨进程重开/崩溃与Stop恢复。FakeJournal Drop join若OS fsync长时间卡住仍待代表性Stop检验；代码构造并不等于系统绝不会HOL。
- H1827/H1828新的完整时间线P2与容量RSS、Game4 CN、GUI签名控制、IPv6原有政策、P1入口A/B CPU归因均OPEN；029不交付。H1831签名D3在提交时**NOT_RUN**，待Action真实结果，失败定位首个边界，不重复dispatch。

```feature-impact
{"kind":"none","ids":[],"reason":"Only precise D3 signed fixture metadata counters and source-scoped observation; no DNS routing or product code behavior change beyond already committed H1829/H1830."}
```
