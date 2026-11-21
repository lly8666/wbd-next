# 2026-11-21 · 029 吞吐施工分配与接班规则

原 main [ad6bef6](https://github.com/lly8666/wbd-next/commit/ad6bef638faf0075e1923d2a97849dc255e6877a) 的[旧提示词](https://github.com/lly8666/wbd-next/blob/ad6bef638faf0075e1923d2a97849dc255e6877a/docs/prompts/M0.md)混入已过期任务。H2230 main 游标仍指向重跑三机，H2244 已在实验分支排除固定整形。旧 main [治理 run 44736847698](https://github.com/lly8666/wbd-next/actions/runs/44736847698) FAIL 保留，游标原 evidence_refs 跨 SOURCE。新包从 NOT_RUN 起，以旧结果作背景。

本次将永久提示词、独立研究原文和[当前施工](../../decisions/M0-PLAN029-THROUGHPUT.md)分开；main 登记，产品按已登记短分支验证后合入。可验证的行为是新 agent 只从 main 找到唯一分配、基线、活动分支、待收 run 及一步操作；更换任务无需再改提示词。Git 保留旧基线，若回退恢复受影响规则与任务入口。新 agent 非预告中断实演、产品原生性能与物理验证均 NOT_RUN。没有改运行时代码或默认参数。

```feature-impact
{"kind":"none","reason":"M0 operating instructions, task assignment and throughput design only; no runtime/default change."}
```
