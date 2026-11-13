# PLAN029 H1726｜单owner组件结果＋严格单DNS/Fake区间/失败回收

- [H1725 Windows/Linux Rust Action43392432186](https://github.com/lly8666/wbd-next/actions/runs/43392432186) 同SOURCE `2bb369f94421775e87aa2f3151821d9668fe86a1` 双job **SUCCESS_SCOPED**；仅新原Rust Wintun TX→物理UDP→原Rust RX TX 无第二reader、有界mailbox代码和纯组件测试，不是Go原TLS启用/正式业务双出口。
- 契约§1同一个DNS地址可用于两个方向，因此冷V3去错误的“dns.direct 必须不等于 dns.tunnel”；目的用途仍独立。FakeIP高级范围改为确切连续闭区间，不能只编译两个端点；All/BypassLan不创建停用FakeAllocator/domain trie。
- Direct UDP首次Socket bind/资源满/无效目标不能继续占Direct flow hard quota，调用Rust ingress精准取消未被后端接纳的pin；发送暂时WouldBlock只丢该UDP包，不回退Tunnel；用户态绝不扫全表。新`plan029_`测试在当前SOURCE Action待运行。
- DNS+TCP两后端及owned Defender/路由/崩溃恢复、原Go冷V3接线仍NOT_RUN；此包不能产生产品Ready。保留所有历史FAIL，不重派H1695等诊断。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Fix exact FakeIP pool interval and failed physical Direct admission rollback, allow equal DNS IP with lane-specific purposes, disable inactive fake tracking"}
```
