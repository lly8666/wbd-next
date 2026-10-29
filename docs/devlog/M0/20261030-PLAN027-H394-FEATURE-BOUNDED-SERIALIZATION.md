# PLAN027 H394｜功能卡大小门实际失败修复
2026-10-30。H393 [governance Action 40936343297](https://github.com/lly8666/wbd-next/actions/runs/40936343297) 结构 job PASS，功能目录 job **FAIL**：`fec-auto.json` 全量缩进展开超过 feature card 有界 JSON 大小门。H393 新增的 sparse-close 限制内容没有问题，现仅改回单行紧凑序列化，保留全部原卡片字段、历史 PASS/FAIL 和新增限制，不改变产品行为。新 Action 待收；H393 native build/verify 在途，不重复派发。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Compact JSON serialization after bounded feature-card size CI failure while preserving the PLAN027 sparse-close limitation and all existing evidence."}
```
