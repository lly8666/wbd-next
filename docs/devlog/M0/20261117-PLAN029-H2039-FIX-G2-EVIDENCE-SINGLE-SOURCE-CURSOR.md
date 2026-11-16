# PLAN029 H2039｜G2 cursor只放同SOURCE直接证据，保留旧真实记录

- H2037 [治理Action43913747609](https://github.com/lly8666/wbd-next/actions/runs/43913747609) 和回归门 **FAIL** 首个边界是 `evidence is for a different SOURCE`，不是Game4网络、功能卡大小或授权缺失。
- `tools/governance.py` 原结构严格检查 `for path in cursor.evidence_refs: evidence.source_sha == cursor.last_tested_source`。旧cursor `last_tested_source=5e6a8f3...` (H2005 Direct UDP p99)，却混放 `H2036/H2031` source `b76240b...` 与 `H2007/H2005` source `5e6a8f3...`。**真实不同SOURCE不能同列**。
- 本轮只将直接证据指向最新已真实归档 H2036/H2031 Normal Tunnel 20–30条 / 2–3秒 / 0..500B/MTU抓包及双owned Stop（`last_tested_source=b76240bedb04237780bd13377bfe7aae38785018`），把早期H2005 UDP延迟证据保存在历史context引用。源记录内容不改，不降治理规则门、不将FAIL重写PASS。
- H2038 [原Game4 CN独立真实Action43942345347](https://github.com/lly8666/wbd-next/actions/runs/43942345347) 在途，其源/编译/业务不因本次docs-only提交被替换、不重复dispatch。共享CDN双域名专项仍NOT_REQUIRED，填充不重跑。
```feature-impact
{"kind":"none","ids":[],"reason":"H2039 repair only G2 governance cursor SOURCE integrity: latest archived H2031 pcap proof is sole direct evidence; prior genuine H2005 direct UDP proof remains available separately."}
```
