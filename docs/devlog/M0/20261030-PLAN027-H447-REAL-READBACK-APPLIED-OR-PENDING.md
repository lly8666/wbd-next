# PLAN027 H447｜Linux真实新v2确认已出现，短测试必须接受自洽的实际readback

[H445 parallel40987887943](https://github.com/lly8666/wbd-next/actions/runs/40987887943) 两个独立原Go真实netns源码64 UDP首到已PASS，但脚本仍断言Fixed与Auto必须 `applied=0 pending=true`，实际 client Fixed `applied=1 profile=1 pending=false`、Auto `applied=1 profile=5 pending=false`（与H444新Rust认证 v2 FEC Applied候选一致）。之前H443 Pending硬断言只适用于旧源；拒绝为了绿而错杀真实读回或把短首到误当120秒降档。H447改独立脚本要求 **client和server两端** 原FEC authenticated readback存在、revision1/profile有效、Applied与Pending布尔自洽；允许根据真实证据落在 Pending/Applied任一态。CI标记只称“真实首到+Stop+配置readback”，`product_qualified=false`直到matched v2报表和Auto动态长窗、真实2OS通过。其他真实512 1%损伤/Stop验证不放宽。

```feature-impact
{"kind":"none","ids":[],"reason":"Assertion fix for source-authentic new Fixed/Auto config readback; no product capability promotion."}
```
