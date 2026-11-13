# PLAN029 H1739｜四阶段no-WFP WAL内可选synthetic TCP/32 route的精确CAS回收

- H1738 SOURCE `4bdc4283b5480ba48cb9171c1e7d30003b55ef4e` [两OS Rust43408223889](https://github.com/lly8666/wbd-next/actions/runs/43408223889)、[Go Windows43408224061](https://github.com/lly8666/wbd-next/actions/runs/43408224061)、[GNU cross43408223776](https://github.com/lly8666/wbd-next/actions/runs/43408223776)、治理43408224032与维护43408223830 全部**PASS_SCOPED**。证明编译/纯组件，不等于真实Windows双出口。
- 当前已有原认证Rust owner optional kernel TCP listener + NAT + physical `IP_UNICAST_IF` relay，但开关默认关，因为欠精确synthetic /32路由和Defender owned收据。现把可选 `198.19.x.y/32`（与默认198.18 FakeIP池分离）追加于**同一四阶段no-WFP v2 WAL的第4个routes阶段**，使用原`NativeRouteBackend`逐条intent/owned/回滚CAS，非第五旧WFP阶段，非逐域名/flow改路由。拒绝非预留段、DNS/lease/server/物理源IP、重复route以及无效端口reserved。
- 新纯测试包括一条辅助/32与原/1、server /32一起durable WAL记录并完全按拥有的键回收，旧四阶段默认路由原样不变。Windows OS实写行为和Defender尚未在此SOURCE跑实网，测试结论PENDING。
- 下一闭环必须同代原Go四阶段Apply内创建并读回一条精确owned Defender TCP Allow，再**post-Apply**开启Rust native kernel TCP；当前不会在无证据时启动，更不会宣布D1-D5/P1-P2完成。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add optional exactly owned synthetic TCP peer /32 to existing native no-WFP fourth routes stage via durable per-key WAL/CAS rather than unowned per-flow routes; preserve H1738 scoped test PASS"}
```
