# PLAN028 H1440｜补齐旧 Native105 静态守门回归

H1439 `d3bd3b47` 自动触发的 [Action42532599409](https://github.com/lly8666/wbd-next/actions/runs/42532599409) 在廉价预检第31步 FAIL、原生任务 SKIPPED/NOT_RUN。新 L3 作用域离线用例和 workflow 检查 PASS；失败来自 `tests/test_m0_plan027_managed_unilateral.py` 仍要求旧的 **双分支** PowerShell 原样守门字符串；当前实际新增只有 `$crossOsL3` 明确限定的第三分支。原 ASSERT 0!=1，不能算原生缺陷也不能算网络 PASS。

本轮仅更新旧断言为 **GameFEC/Normal105/显式跨 OS 1800s** 三分支的准确 fail-closed 表达式，同时检查 L3、双独立客户端、Normal 模式、独立租约文件全部约束。旧 H888 参数/产品没有放宽，保留原 FAIL；无需为这个静态错误重刷业务 seed。详情：`docs/evidence/M0/PLAN028-H1440-CHEAP-PREFLIGHT-GUARD-STRING-FAIL-20261109.json`。下次只接一次真正完成预检的 native Windows+Linux L3，按原 1800s/UDP/TCP/资源/owned Stop 规则裁决。

```feature-impact
{"kind":"none","ids":[],"reason":"Test oracle only: existing managed route guard gained explicitly restricted PLAN028 L3 branch; keep legacy safety checks exact, no product behavior changed."}
```
