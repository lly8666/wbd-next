# PLAN029 H2042｜缩减范围首批代码，尚未原生验收

- 用户明确缩减后仅做 GUI 真起网/有效值/Stop、同端点 DNS TC/物理 bootstrap/TTL 与 writer、资源分型满额、最终证据归档。IPv6/旧 P1/P2/共享 CDN 等不在此次施工。
- 经原源检查，`faketcp.LookupPhysicalServerA` 的真实 Npcap UDP 收到合法 TC=1 过去会忽略并超时。现用精确 UDP 物理源/端口/校验和/QNAME/ID 校验触发同一个 `dns.direct:53` 的 TCP fallback；Winsock TCP 指定已验证物理 source 和 IP_UNICAST_IF（网络字节序），3.5s 后备预算，无系统 DNS/NIC 备选/Tunnel 交叉。TCP 帧重新验证同 ID/QNAME/CNAME/A。物理接口号从冷 `DiscoverPhysicalUnderlay` 传递；不拓展 Go 逐包路径。
- 新加小预算真实文件系统异步 writer 测试：八个未回执 job 饱和时第九个明确拒绝但不提前发布 FakeIP，同期独立 Tunnel DNS 事务可完成，完成后恢复排队并关闭/重启读取九个 durable 映射。加受污染来源、ID、QNAME 的 TC 反例单测。
- **证据等级：IMPLEMENTED_NOT_TESTED**。此 SOURCE Windows Go/Rust 原生编译和 TC TCP 实网暂时 NOT_RUN；旧 H2041 与 H2031 的已验 SOURCE 不变。不得由代码/单测冒称 GUI Origin OS Applied、真实 Bootstrap TC、DNS/资源压力全面 PASS。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Scoped PLAN029 TC/bootstrap and async writer pressure implementation pending native verification; old signed receipts remain source-scoped."}
```
