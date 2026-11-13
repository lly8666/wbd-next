# PLAN029 H1699｜唯一 Rust Wintun 入口的包策略边界：先纯单测，不冒充Direct

- 基于 H1694 真正签名 Windows 内核 TCP A/B/C 接入资格，以及 H1698 真正四阶段 Win32 no-old-WFP OS Apply/Stop PASS，新增 Rust 模块 crates/wbd-engine/src/v4_client_split_wire.rs；单 PacketIngress 持有只读 Arc<SplitPolicy>、Arc<DomainIndex>、同一代 FlowPin，普通DATA只解析固定IPv4/ports并读pin，不遍历CN表、不解析DNS名字、不走Go per-packet/全局注册锁。Linux test及Windows普通native编译资格由本批SOURCE Action决定，当前未有真实 packet owner 接线。
- UDP53先识别业务用途而非IP分类：严格解析单question的非压缩QNAME、ID、QTYPE，由现有唯一DomainIndex trie判CN后调用 SplitPolicy.dns_egress。CN模式的CN QNAME标记Direct resolver/FakeIP候选A，非CN名称无论目标DNS服务器IP是否属于CN都标记Tunnel resolver，All和BypassLan不强开CN。TCP53标记NeedsQuestion等待后续有界DNS TCP组帧，不假装使用IP方向。普通非CN真实共享CDN IP不会被同真实IP映射污染；已宣布本地FakeIP Direct，未知FakeIP丢弃。拒绝从TLS/DoH/QUIC推SNI身份。
- 普通IPv4 first-flow按Core Ranges + Fake map 决策并走资源独立 FlowPin：Direct硬满只拒新Direct，Tunnel机会性pin满仍继续原Tunnel，绝不跨方向回退。有限fragment (src,dst,protocol,IPID) 缓存仅挂已确认首片关联，后续片无记录明确拒绝；DNS分片明确NeedsReassembly、**暂不冒充已支持**，下一步需有界128 datagram/8MiB/2s真正重组；fragment过期只由worker粗tick回收，不在DATA上取系统时间。当前框架只返回动作，不拦截、修改、注入真实Wintun包。
- 修复一个冷语义边界：只有 BypassLanCn 能宣布选择性FakeIP，其它route-mode拒绝宣布并把Fake池地址视为未知FakeIP，避免模式转换后偷偷开启中国域名规则。新增多项纯包级测试：域名→海外Fake直连、非CN同CDN真实IP仍Tunnel、非CN DNS目标CN IP但DNS方向Tunnel而业务CN IP直连、其它mode、缓存容量、unknown fake、碎片关联/到期、恶意压缩查询、明文TCP53/加密443显式未知。
- **设计/已实现/实际验收严格分开**：已有OS四阶段和内核listener真实PASS与本次Rust纯Wire模块是两个资格。PacketIngress还未被Normal/Game4 Wintun worker调用，更没有Rust physical TCP/UDP或异步DNS、FakeIP allocator/TTL；普通碎片DNS还没有重组。不可据此写PRODUCT PASS。后续以同一个TX ingress真正串接，保证Wintun RX borrowed buffer不跨await、TX Allocate后立即Send，再做完整D1-D5/P1-P2。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Introduce typed single-Rust-ingress IPv4/DNS purpose-first packet decisions, test fake CDN isolation, direct capacity independence and fragment pin boundaries; not yet native Wintun/Direct wire."}
```
