# PLAN029 H2051｜仅用户指定的五类资源小额度组件退让 + 原物理 DNS TC 单场

- 原 NativeOwner 分流不添加新的 per DATA 轮询/锁/worker。追加 Rust 单元：`FlowPin` Direct hard1满只拒绝新Direct，原Direct和Tunnel pin与软件非缓存Tunnel继续；`DnsPending` 2 tickets/2 waiters满但原Direct与Tunnel票可独立abort/继续，另1 ticket硬满后释放可再次接纳；`DnsAnswerCache` max1 LRU逐出而不阻止新的独立查询，clear后继续；`FakeAllocator` 1个 durable 且已pin的FakeIP不能被新A劫持，释放后必须满足 quarantine 才重新分配。实际有文件 fsync 的 async8+第九拒绝已在 H2043 Win/Linux纯测PASS。
- Windows `TcpDirectRelay` 独立真实loopback内核socket，两条相互独立 relay：第一条一量子缓冲满且该流读门关闭，第二条仍传输完整应用字节；第一条原队列排空、恢复继续，没有替换 Socket、创建Tunnel fallback。
- **等级只能是PURE_COMPONENT，不能冒充原Windows/WSL2真实多类同时资源饱和业务**。历史 H1868 的 Direct hard8 是唯一真Wintun资源前置证据；其余原生满额到产品边界仍 OPEN。
- 此提交显式`[plan029-real-dns-tc]`再验证 H2050 精确 HyperV UDP53+TCP53(仅WSL guest+source地址)+原 Npcap/TLS/CN双出口/Stop，与H2050 GUI真按钮不同场景、不同 SOURCE。H2041 Game4/H2031 padding不重复。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add original Rust small-quota classified independent recovery proof and real physical same-endpoint bootstrap TC scene; native result pending."}
```
