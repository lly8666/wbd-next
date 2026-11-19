# H2138｜H2137文档校验首错修正，无产品/网络变更

- [H2137 docs Action44212060190](https://github.com/lly8666/wbd-next/actions/runs/44212060190) **FAIL_GOVERNANCE**：原DNS功能卡在新增一条验证后，UTF8实占 16,885B，超过16,384B硬上限（不是 JS字符数16,132）；将该冗余新验证摘要删除但**保留所有原有56条带历史Evidence的验证**，以更新的短summary/limitations及H2137独立证据承载最新状态。旧真实历史/FAIL一条不删。
- 原 M0 cursor `evidence_refs` 同时列了SOURCE `ec49461`（B4）、`5fc22a`（Game4）和SOURCE `d4ddd74`（B5），不满足 `last_tested_source=d4ddd74` 的单源治理契约，且新H2137聚合证据缺根 `source_sha`。仅将B4/Game4移入 `context_refs`，B5 H2137聚合标明根 `source_sha=d4ddd74` 和 `artifact_verified=true`；历史签名证据不变。
- 产品B5真实 [Action44201457211](https://github.com/lly8666/wbd-next/actions/runs/44201457211) SUCCESS/ZIP48CRC/原双端各60s+10Mbps、B4与Game4既往原 Action SUCCESS资格均不变。029/029B日常范围PASS_SCOPED；完整合同OPEN、Game2高级split不支持、TCP小请求p99/P-B2/全宿主IPv6不冒充完成。**本提交纯文档，不创建新的原生Action。**

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Reduce H2137 feature card UTF-8 bytes below strict 16KiB without deleting any historical verification, and keep latest scoped status in summary."}
```
