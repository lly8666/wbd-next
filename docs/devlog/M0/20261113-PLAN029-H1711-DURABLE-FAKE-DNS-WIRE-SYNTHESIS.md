# PLAN029 H1711｜收H1710 FakeIP纯测试；真实DNS客户端字节合成前的持久化门

- [H1710 Action43362102305](https://github.com/lly8666/wbd-next/actions/runs/43362102305) SOURCE `c58fc4768b0448f44ed1baebb20e32e1bf05788e` Windows321、Linux296 Rust library PASS，4项新FakePool CIDR/共享CDN/TTL0/10分钟隔离/活跃flow ref/容量/恢复测试PASS。Go编译子job也PASS，整个workflow因原旧公开产品链路独立FAIL，不能把子job扩大成完整产品PASS。
- 新 `v4_client_dns_wire.rs` 真正构造**客户端可见的DNS wire响应**，只用于CN且上游真正成功的A。逐条检查原始QNAME+可达CNAME链+真实A+policy/resolver revision 的**完全一致的持久化已确认FakeIP**；CNAME使用受限最短TTL，多A只包含各自的fake4，绝不从共享真实CDN IP反查生成域名，也不生成无关additional。已公告TTL过期但仍在隔离期的地址不可重新发布；新的QNAME或策略代不能借旧fake。未持久化/池满/字段冲突直接拒绝合成，不默默改走tunnel/其他resolver。DNSSEC AD必须清零。CN AAAA及HTTPS/SVCB明确NODATA，无ipv4hint或ipv6hint污染。
- FakeAllocator新增只用于DNS新答复的 `issued_for(key, now_unix_ms)` exact owner lookup，普通DATA仍用首次流PIN固定real IP，不逐包查域名或磁盘。单元夹具覆盖先未持久化拒绝→ack后可写真实DNS bytes→相同CDN另QNAME不可偷用；多A/TTL0/原海外IP不可出DNS报文；AAAA/HTTPS/SVCB NODATA。
- 此SOURCE的新增encoder/测试尚未实际Windows/Linux编译。**没有真正portable原子writer，更没有DNS UDP/TCP socket或正式 Rust Normal/Game4 装配**；虽然生成的报文是正确性所需代码，不能算D1/D3或产品Ready。后续将真实持久化回执连到分配器并以两可控DNS出口验收。不重跑028全矩阵或开030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect scoped H1710 cross-platform FakeIP pool unit PASS and implement guarded CN fake-DNS wire CNAME/multi-A response generation, without claiming live resolver or durable writer."}
```
