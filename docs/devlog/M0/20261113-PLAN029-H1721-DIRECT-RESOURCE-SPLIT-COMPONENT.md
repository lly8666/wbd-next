# PLAN029 H1721｜并行批：Direct资源满正确退让及Windows UDP轮询CPU

- 同一批修改 `v4_client_direct_udp_actor` 的WSAPoll由最多16384全表每轮扫描为**每轮最多rx_quantum(默认≤64)个**轮转工作集，含无事件时游标推进；流socket按需分配、错误丢当前flow与回包构造不变。不加每flow线程，不持Wintun ring，未在正式产品激活此 actor。
- `FakeAllocator::prepare` 对新映射容量/字节压力仅按需最多处理64个到期隔离槽；仍保护未过隔离、已有flow引用及FakeIP写前durable状态，无容量不跨方向回退。
- `PacketIngress` 新Direct TCP 首包必须是SYN且非ACK，否则在占用Direct quota之前拒绝；既有pin可正常传输ACK/DATA，Tunnel不受Direct硬满影响。
- 新 [双OS同SOURCE Rust测试Action](../../.github/workflows/m0-plan029-h1721-native-split-capacity.yml) Windows/Linux不同job并行，纯Rust非网络场景，不多次dispatch；结果在收到后独立更新证据。正式原TLS NativeOwner真实两出口、双DNS、GUI连通/Stop、P1/P2和padding继续NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Bounded UDP readiness CPU and safe FakeIP/Direct TCP capacity handling on staged native split path; network integration remains NOT_RUN"}
```
