# PLAN027 H402｜H401 feature-impact schema 精确修复
2026-10-30。回收 [H401 governance40946233545](https://github.com/lly8666/wbd-next/actions/runs/40946233545)：Governance job SUCCESS，Feature catalog FAIL `invalid feature-impact IDs`。原因 H401 编译修复的 `kind:none` 声明漏了治理合约必需的空数组 `ids:[]`。仅修正 H401 devlog 的 JSON 块，保留失败记录；H401 源码 native40946233170 在途，不重复启动。产品实现及 PLAN027 五项状态不变。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct feature-impact metadata on prior devlog only; no product code or behavior changed."}
```
