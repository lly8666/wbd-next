# PLAN028 H1507: H1506 五端初次自动构建只是 CI 原始旧回归接口 FAIL

第一次 Action42764980969 的 Cheap workflow 检查在 `tests.test_m0_wl_native_step_runner.test_h778_early_gamefec_local_artifact_precedes_separate_cleanup` 因 `ValueError: substring not found` 失败，原因是 H1506 将原工作流 `name: m0-wl-full-public-normal-direct` 改为表达式；保留旧GameFEC先上传、最后完整上传的先后顺序是合理的合同，不能为了五端削弱或改动断言。因此恢复原步骤与原产物名称，并新增仅 loss0/loss30 五端的唯一产物名称上传。第一次原生五端所有依赖任务 SKIPPED，**真实 Windows driver/600s UDP 均 NOT_RUN，绝不把 CI 错误标产品缺陷**。下一次带唯一 `[plan028-h1506-win5-600]` 的 push 触发两端0/30矩阵的真实原生构建与业务。Go/Rust全部冻结，PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Only preserve legacy CI artifact identity and separate new original native evidence names; no product change."}
```
