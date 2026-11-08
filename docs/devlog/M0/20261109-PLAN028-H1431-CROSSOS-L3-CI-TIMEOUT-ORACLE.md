# PLAN028 H1431 | 修 Windows1800s 长测 CI 旧超时硬编码断言

原 H1430 Action42507562916 **在 Go/Rust/Npcap/Windows 产品构建之前**即被离线 CI 检查拦下，原语义 `HARNESS_OR_CI_FAILURE`，native 网络 `NOT_RUN`；非产品失败。旧 `tests/test_m0_wl_native_os_deadline.py` 强制 workflow 出现 `timeout-minutes: 24` 字面串，新的 source-frozen Win+Linux 1800s opt-in 正确地给普通24分钟、长测52分钟，所以老测试误报。同步更新该检查为精确条件表达式（仍要求普通24）和 `tests/test_m0_wl_native_step_runner.py`：原 Game600/Normal105 780/一般1020、旧默认PID320秒均保持，只有明确L3允许2600/2250秒。未改真实产品、协议、default MTU、Windows安装数量或原 Action 结果。推送仅派发这一已授权 Windows 长测源场景；ARM64 两场继续原在途，不重复网络。

```feature-impact
{"kind":"none","ids":[],"reason":"Only updates existing offline deadline-regression assertions to verify opt-in 1800s bounds and unchanged ordinary bounds; no product behavior changes."}
```

H1433: Action42507973848 又于测试 `tests/test_m0_wl_scoped_game2_trigger.py` 的第三处旧字面 `timeout-minutes: 24` 判断停在原生测试前；此次同步将旧 Game2 24 分钟限定与明确 Win/Lin L3 52 分钟一起核，保留原 Action FAIL／Windows native `NOT_RUN`。不改变长测产品与实际超时；若下次真实 Windows 1800s 未执行，绝不报 PASS。
