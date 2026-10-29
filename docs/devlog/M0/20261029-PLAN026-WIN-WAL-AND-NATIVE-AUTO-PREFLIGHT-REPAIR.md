# M0 PLAN026｜同源可编译收口：Windows WAL 装配与 NativeAuto 热循环

2026-10-29，SOURCE d41bb1b9 后的真实 Actions 只允许精确结论：

- Windows/Linux native/library 编译与单元预检 Action 40817969236 **SUCCESS**；原 Go NORMAL-COMMON 40817969118 **SUCCESS**；main governance 40817969168 **SUCCESS**。
- 原 Windows WAL 联编 Action 40817969186 **FAIL**：装配 `manifest-plan020-m0.json` 漏了一份已存在的 `bridge_v4_windows_fixed_stream.go`，使旧 Go auto_controller 中 `RequestBoundOriginalFEC2Revision`、`ReadBoundOriginalFixedMature` 未定义。本次只补精确原文件 Git blob 的 `create`，不发明新 Go API 或覆盖上游。
- Windows 原 M2专项 Action 40817969290 **FAIL**：`m0_windows_m2_v3_no_unsolicited_pto_repair_and_owned_stop` 的真实注册结果从布尔改为精确 `assert_eq!(...,Ok(()))`，**不放宽要求**，供本SOURCE区分生产 bug、共享测试状态或 runner 干扰。12/13旧专项 PASS，不能称专项全绿。
- Rust NativeAuto 只在到期2s的现有TX工作线程采样原成熟 M2；之前的写法在高PPS下会额外锁一次Owner，即使没有到期，现将 next_auto_check 存在该Rust TX线程栈，每2s才尝试一次，Fixed和Normal完全不执行Auto锁。协议、k证据及 30s缓降不动。
- PLAN012 Fixed Rust构建 Action 40817969144 在 `rustup 1.85.1` 下载阶段退出，**未到代码编译**，不能归因于产品或算该SOURCE Fixed PASS。

仍有 Windows Game2/Game4 的双worker多Npcap Rust-native接线、服务器 FIN 承诺和可配 Dormant/Wake、Linux Rust Auto替代Go控制及最终V2弱网/CPU A/B 未完成。本提交只修源码候选，所有新产品运行资格NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"只修复原Go装配manifest漏入既有固定流桥、NativeAuto 2s非热锁时序和Rust专项断言错误详情；不变更行为门槛、配置、对外功能或资格。"}
```
