# PLAN027A H944｜精确SOURCE治理修复：不能混不同测试源码

恢复 H943 `96ead0c07d3bc0121116bc801617c7e32d9bf142` 主线治理：`41449003928` 和 `41449003884` FAILED，第一根因功能卡超过16KiB限制，第二根因为 M0 cursor 新 `last_tested_source=ae3e7e9f...` 却在 `evidence_refs` 混入 PLAN027 老 `6693910...` 七项证据，触发 `evidence is for a different SOURCE`。这些不是六场新真实业务失败。六场产品SOURCE `ae3e7e9f52c415b60d596b7e923ade07f463d4ed` 已全PASS功能范围，旧source失败不可改变。

仅把 cursor 的**本次SOURCE的 evidence_refs** 收为 H943 单一结果文件，历史 PLAN027 证据继续原路径保留不移动不删除，旧版完整历史 limitation 内容仍可通过 H943 父 commit 的功能卡与 dated devlogs/evidence 查看。Card 仅压缩重复的施工叙述，不删现有 verification 历史行，不删除旧功能的原始 FAIL、不变更产品或测试程序；仍记录 Game4FEC 10M loss0 RTT p99高及 DF0/DF1、分阶段弱网、3Mbps保护未验。这样严格遵循 <=16KiB 卡片上限，不能靠放宽治理过关。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Correct mixed-source cursor evidence refs to exact current-source H943 and compact feature-card redundant historical prose below 16KiB; preserve all historical verification and original dated evidence, no product modification."}
```
