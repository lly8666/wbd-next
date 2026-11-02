# PLAN027A H954｜H953派发器在前序编译尚运行时误判空结论

[41457351564](https://github.com/lly8666/wbd-next/actions/runs/41457351564) H953派发器首错 `H953_H952_BUILD_OR_NATIVE_FAILED `：`gh api --jq .conclusion` 对进行中的GitHub run JSON null打印**空字符串**，原脚本只当文字 `null` 才等待，导致还未有新 Game Action 时提前FAIL。H952 [41456643128](https://github.com/lly8666/wbd-next/actions/runs/41456643128) 在此期间 cheap、Windows Go/Rust、Linux Rust、Linux product 构建成功，原生 job仍未结束；不可编造前序失败/成功。

仅在原H953 workflow把空串或 `null` 都当“仍在运行，继续有界轮询”。非空非success仍终止，不降低 SOURCE/产物 SHA/单模式守卫。通过 H954 同一个on-push once标记重新启动调度；**不更改任何Go/Rust源、不再编译，前次失败保留**。

```feature-impact
{"kind":"none","ids":[],"reason":"Only fix GitHub CLI pending JSON null handling in prebuilt-only H953 Game native orchestrator; no product change or qualification promotion."}
```
