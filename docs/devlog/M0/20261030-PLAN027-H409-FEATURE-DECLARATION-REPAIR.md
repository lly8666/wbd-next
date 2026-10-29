# PLAN027 H409｜功能卡声明修复

2026-10-30。H408 [governance Action40962889507](https://github.com/lly8666/wbd-next/actions/runs/40962889507) role SUCCESS、feature catalog FAIL：当次修改了 fec-auto 卡片，却只声明 feature-impact none。按真实错误改正 H408 声明，并删掉卡内重复 H404 限制（原源码/历史证据不删），继续保留所有旧 FAIL。没有产品行为变化。

H407 Rust/native 和 Windows/Linux 原 M2 回归在途，未宣称通过；PLAN027 ①部分、A/B/C/交付未完成。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Correct prior changed-card declaration and remove duplicate limitation while preserving scope and historical evidence."}
```
