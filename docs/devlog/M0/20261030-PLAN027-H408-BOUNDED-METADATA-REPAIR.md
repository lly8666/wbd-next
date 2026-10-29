# PLAN027 H408｜治理容量失败的最小修复

2026-10-30。H407 SOURCE 361265256d58d18ea0b36badf04668c16fb19e1c 的 [governance Action40962693582](https://github.com/lly8666/wbd-next/actions/runs/40962693582) 真实 FAIL：feature card UTF-8 超过16KiB、cursor.context_refs=9 超过8。保留失败记录；去掉功能卡内重复的 H393 文字（原 devlog/evidence 不删）、缩短 H407 限制语句；cursor 删除旧 H404 context 引用，保留证据原文件及 H405/H406/H407。无产品行为修改。

H407 源码 native-functional40962693585、Windows owner40962693602、Linux Auto/Health40962693776、r0 ABI40962693614 当时仍在途，必须按精确 SOURCE 回收，不能由 H408 metadata 成功推断代码 PASS。PLAN027 五项仍未闭环。

```feature-impact
{"kind":"none","ids":[],"reason":"Governance-only metadata size and bounded reference repair; no product behavior or feature semantics changed."}
```
