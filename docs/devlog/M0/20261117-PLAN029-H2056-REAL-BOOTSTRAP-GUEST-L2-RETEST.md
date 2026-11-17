# PLAN029 H2056｜同一物理dns.direct TC=1修复后再验

- [H2051原Win2025/WSL2物理DNS Action43999380296](https://github.com/lly8666/wbd-next/actions/runs/43999380296) 在guest精确`UDP53/TCP53`双HyperV规则创建/readback后，原Go`vpn.edge.cn.example`物理Npcap UDP A查询仍超时；没有任何原生TC/TCP证明。原规则随后CAS精确移除。该源早于H2053，经原Go源码查证，冷DNS当时没有把实际Windows host-self SendARP MAC改为先前OS读回的Linux eth0 guest MAC（普通FakeTCP已有这段校正）。
- H2053 加入受同ifindex/源IP/单resolver/实际MAC约束的物理DNS下一跳修正，Win2025源码构建[Action43999939754](https://github.com/lly8666/wbd-next/actions/runs/43999939754)成功但仅BUILD_PASS。H2056新增Linux guest收到一包物理UDP及同ID/QNAME物理TCP的真实阶段stdout，限初始TC场景。**只有本SOURCE original Go DNS_SELECTED、真实TLS/双出口/双方Stop与独立guest接包同时齐全才算成功**。不允许外部system DNS、Tunnel fallback、借用旧SOURCE成功。
- 显式标记`[plan029-real-dns-tc]`仅本次触发一个原物理TC测试，H2055 GUI与H2031/H2041独立不重复。不对用户未点名旧性能/IPv6扩容。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Re-evaluate corrected H2053 attested original Windows physical L2 MAC on the same-direct-endpoint real UDP TC and TCP53 guest, with independent exact first-hop evidence."}
```
