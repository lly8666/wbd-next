# PLAN029 H1727｜原Go冷策略和原认证Rust私有V3 ABI

- H1726 `ac052e5f415511872551f02f95ab5c0245c48e5a` [Win/Linux Rust scoped 43393030348](https://github.com/lly8666/wbd-next/actions/runs/43393030348) 双job成功，覆盖单Wintun原Rust NativeOwner物理Direct UDP/非阻塞回包队列、DNS可同地址、Fake区间及失败pin回收的源码组件，**不是**真实Go产品双出口。
- 原 Go `route-mode` 现透传 native options；新增冷构造 LAN＋中国IPv4并集、direct4、物理源/ifindex、真实Wintun租约/内层MTU、`dns.direct`/`dns.tunnel` 仅单值；外层original TLS/AEAD不变，规则不生出几千OS路由。Go同步probe V3原owner先查同代认证Device再构造C ABI，Rust cold copy前保留slice，绝不Go逐包泵。
- CN域名冷Exact/Suffix支持ASCII/IDNA规范化；目前`include`、keyword、regexp和属性无法完整展开，**明确拒绝**，不偷改成suffix、没生成完整v2fly离线默认集合。Rust域名冷预算1MiB/2万条，普通DATA不查trie。
- 正式产品依然调用原V2；V3 Rust symbol只在`m0_v4_probe`特性导出，DNS/TCP未实现时拒绝而不冒充Ready。本批Windows原Go/WinLinux Rust编译与测试待同SOURCE CI，D1–D5/P1–P2/GUI有效/padding仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Source-locked original Go cold mode/IP/domain/single-DNS policy and private authenticated Rust V3 ABI; product not enabled"}
```
