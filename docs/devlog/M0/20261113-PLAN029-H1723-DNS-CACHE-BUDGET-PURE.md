# PLAN029 H1723｜H1722 双OS Rust scoped通过，DNS缓存独立并行施工

- H1722 `1e75226951a03bc10da573d508881ed20a8a3437` [Action43389255442](https://github.com/lly8666/wbd-next/actions/runs/43389255442) Windows2025 wbd-platform 46项+Rust PLAN029 41项PASS，Ubuntu24.04 platform 115项+Rust PLAN029 38项PASS，均同一SOURCE不同runner并行，结果**纯组件PASS**；H1721 原FAIL保留原日志。
- 本批新增一份 per-owner DNS-only TTL/LRU缓存：用完全相同的QueryKey绑定QNAME、QTYPE、方向、唯一resolver endpoint与policy revision；每hit只缩TTL不续期；默认4096项/8MiB，满时淘汰旧缓存，**不拒绝外部解析**；DNS transaction和FakeIP引用另有独立额度。NXDOMAIN/NoData缺SOA负TTL不缓存，TC/错误不缓存，无跨方向fallback。
- 新增Windows/Linux并行rust `plan029_`单SOURCE测试入口；本提交DNS缓存尚未实际跑，**PENDING**。所有Wintun/物理socket强制DNS、双出口、真实GUI Applied/Stop、D1–D5/P1–P2及padding **NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add bounded query-only TTL/LRU cache with independent capacity semantics and preserve H1722 real cross-platform scoped results; production DNS socket not yet wired"}
```
