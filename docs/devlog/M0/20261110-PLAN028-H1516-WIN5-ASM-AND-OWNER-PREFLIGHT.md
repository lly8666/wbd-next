# PLAN028 H1516｜新 Windows5 修复的装配哈希与真实 Windows OS 回归接线

- H1515 SOURCE `0d3fbec30095d949aa759725dd7dff5e88e51522` Action [42772317994](https://github.com/lly8666/wbd-next/actions/runs/42772317994)：cheap Python tests、检查 workflow 均通过，**仅** `prepare_windows_wiring.py --check-only` 在原 Go `m0_native_v4_windows.go` 精确 manifest result blob 处抛 ValueError。后续 Go/Rust/native 全部 SKIPPED；原始 Action FAIL，真实 M4/600s **NOT_RUN**。这不是产品功能被证明失败。
- H1515 已把五独立客户端准入限制在 CI+显式五客户端账户/alias/租约/本地 WAL 的原生 Windows named event，生产机器全局 GUI 单例未改变，WSL2 验证源/真实接口规则保持 fail-closed。现修 manifest `result_blob` 为 `099d2d811dad2805945e6074bf3802f79ef2d0a2`，并将新 Windows 五客户端 OS event 测试的唯一 blob `7b9f6bfe3e3a45bc916ec8e0e9ccf1a53bb15270` 纳入同一原 Go 装配。
- 同一 Windows 原 Go `client.test.exe` 在驱动/网络启动前**真正运行** `TestPLAN028H1515FiveOriginalWindowsNativeDeviceSlots`：五个独立命名事件各自成功，重复/错账户/错 /32/错误 WAL 拒绝，生产单例仍拒第二客户端。避免测试只在源树存在却没装配执行。
- 最小实验是一场当前 SOURCE 的 Windows2025 200ms/0% 丢包五客户端原生；须真实触发五账户 TLS、双端 M4、内 MTU、业务/轮换/Stop 才能判定。下一轮收 CI 原始最早错误；30% 不提前重跑。027/029/030 不扩大范围，028 保持 **IN_PROGRESS**。

```feature-impact
{"kind":"none","reason":"H1516 repairs only exact source assembly manifest and executes already-authored CI native-Windows owner-slot unit test; five-client product owner change and tls-auth-multiclient impact were recorded in H1515.","ids":[]}
```
