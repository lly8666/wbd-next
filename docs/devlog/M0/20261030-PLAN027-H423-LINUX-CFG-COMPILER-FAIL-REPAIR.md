# PLAN027 H423｜真实 Linux Actions 失败回收并修复源码 cfg

H421 source3c1f186 NORMAL-COMMON40975508627 和 Linux-AUTO-HEALTH40975508702 FAIL：Rust cfg attribute 6 处少一个闭括号（mismatched closing delimiter `]`）。本批精确修复6处守护括号，不更改第一交付和线路语义，保留历史失败。H422/H423新的原生 Actions 必须按 SOURCE 重新取结果。M2 Fixed/off 退役、ACK/SACK、Auto读回、A/B/C 尚未完成。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Fix six Linux optional Auto cfg parsing errors surfaced by source-locked CI; no protocol behavior change."}
```
