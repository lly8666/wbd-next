# M0 PLAN026 H321｜Windows 原 Go EXE / Rust DLL 的线程级 CPU 归属（2026-10-28）

仅统计 Go 进程CPU会把Rust DLL和内核调用一起算给Go，不能据此断言Go热层没有退场。给本轮原NativeOwner固定两个运行中Rust线程名称 `wbd-native-tx`、`wbd-native-rx`，所有Windows业务包仍在原相同线程/owner里处理，不改变调度线程数、线协议或Go冷层生命周期。

现有每秒一次 `tools/m0_wl_native_resource_sampler.py` 除原 GetProcessTimes+WorkingSet/PrivateBytes 外，从同一PID只读 Toolhelp32Snapshot + GetThreadTimes + GetThreadDescription，得到Rust TX/RX各CPU增量、其他线程CPU增量及最高CPU线程。**这不是语言级perf flamegraph，也不包含内核整体CPU归因；未标识出的线程不归咎Go。** 额外API仅在独立测试Python线程运行，每秒一次；Rust业务线程没有任何每包CPU采样开销。

`m0-wl-public-normal-full.yml` 明确 `[plan026-normal-only]` 源码签名只跑Normal功能及owned Stop，避免为这一源代码诊断变更重测全部七模式。原有P200、N0保持完全独立。若同机有性能差异，再用采样统计真实锁等待，确定是否分拆TX/RX owner。不能因为线程名或CPU数字就声称Rust吞吐达250Mbps。

```feature-impact
{"kind":"none","ids":[],"reason":"Windows Rust线程命名和测试侧1Hz只读线程CPU采样，未改变产品功能、默认配置、wire、路由或控制面调用；保留完整Win32签名系统验收。"}
```
