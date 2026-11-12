# PLAN029 H1674｜单DNS真实物理出口选择修正

- 继 H1673 审查已有 `ResolveServerAFromOriginalPhysical`：此前尽管只向 `dns.direct` 发送查询，仍用硬编码 9.9.9.9 先选路/ARP 后二次按 `dns.direct` 比较。这会使差异化物理路由/切网下的控制DNS错误拒绝正确出口。
- 本批移除 9.9.9.9 路由探测和无用网卡DNS去重，唯一物理路由查询目标即显式配置 `dns.direct`，排除本机 Wintun，直接使用这个物理出口身份/MAC发送原NPF DNS A，源回执持有同一物理接口；空A明确失败，不切NIC/系统/隧道DNS。SNI/预共享route-key/TLS不变。
- 新Windows纯负例覆盖缺少dns.direct、loopback/multicast/link-local/IPv6，不做任何真实网络I/O；新SOURCE必须等H1661 Windows Go装配/编译及H1663 GUI Action后再判 BUILD_PASS；实机D1/D4仍NOT_RUN。
- 保留H1672 SIGNED Wintun SYN-ACK FAIL 原始证据，不为次要微调再启动它。没有选择smoltcp；下批推进无WFP正式四stage txn与原始Rust分流，不复活GO逐包热泵。

```feature-impact
{"kind":"updated","ids":["client-domain-bootstrap"],"reason":"H1674 remove hard-coded third physical DNS route probe and redundant underlay call, keep physical single dns.direct and negative Windows test."}
```
