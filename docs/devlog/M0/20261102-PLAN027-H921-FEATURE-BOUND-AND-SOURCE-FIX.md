# PLAN027 H921｜修复 H920 功能卡与治理结构门

自动push [41430199762](https://github.com/lly8666/wbd-next/actions/runs/41430199762) 的治理/Feature catalog均FAIL；原因是H920功能卡超过既有16KiB预算，新结案证据缺治理按exact source核对所需的 `source_sha`。这不是产品功能失败。旧FAIL保留。

本次只从既有完整卡片恢复原始29条verification历史并追加1条SOURCE 6693910f879f9e55e77dd823c1b05d8942321929 限定验收索引，减少冗余doc_refs及历史limits热描述（原始证据文件和逐条资格不删）；补H920证据source_sha。默认ON/回退OFF登记、experimental/promotion null、旧GUI/physical/metrics限制不变。产品代码、真实网络、Action dispatch和MTU功能无修改。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Keep original source-specific verification history and one H920 summary in <=16KiB feature JSON; fix closeout evidence source_sha for governance contract, no runtime or test change."}
```
