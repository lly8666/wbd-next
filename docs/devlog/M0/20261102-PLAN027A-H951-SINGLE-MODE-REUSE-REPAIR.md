# PLAN027A H951｜不放宽原生重用门，按单模式拆分补齐

H950 派发器 [41455490155](https://github.com/lly8666/wbd-next/actions/runs/41455490155) 与治理 [41455490122](https://github.com/lly8666/wbd-next/actions/runs/41455490122) 均 PASS，四个单模式默认1460场景的 cheap preflight 已通过并在跑原生程序；但是两条 `public_mode=all` + `perf_reuse_run_id` 的测试请求触发既有 `WL_SOURCE_REUSE_REQUIRES_ONE_MODE_NO_N0` 安全约束，在原生测试之前 FAIL。保留 [41455534980](https://github.com/lly8666/wbd-next/actions/runs/41455534980) 和 [41455549489](https://github.com/lly8666/wbd-next/actions/runs/41455549489)，**不是原生产品的失败，也不得标PASS**。

按现有每Action一模式硬门，补 4 个默认1460 模式 + 7 个显式1500 模式。所有原生测试继续复用 H948 SOURCE `adc63a8b8af209dbe589d072403b7bceae8e038b` 同一 EXE/DLL/Linux 程序，校验 GitHub run 来源、相同编译源码和 SHA256，跳过编译。避免重复已发四个场景，不移除原守卫。实际结果均仍 NOT_RUN，按每个 run 的首错/回执收口。

```feature-impact
{"kind":"none","ids":[],"reason":"Only add one-shot H951 single-mode dispatcher and a source-scoped failure/recovery record; product code, ABI, old failures, user MTU default unchanged."}
```
