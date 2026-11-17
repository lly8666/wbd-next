# PLAN029 H2055｜真实 GUI 修复源码并未触发原生验收，修正精确 trigger

- H2050 [原Windows/WSL2 Action43998891197](https://github.com/lly8666/wbd-next/actions/runs/43998891197) 的client.log已有原WinForms按钮connect、Go/Rust认证、outer1460/innerOS1389、OS Applied、两出口TCP+UDP与原生WAL Stop，唯一未通过边界是GUI父进程在final `Form.Dispose`/CreateHandle竞态崩溃，导致退出码1，Action保持FAIL。
- H2054修复了C# STA测试程序重复 Dispose，然而因为 `tools/m0_plan029_gui_real_network_harness.cs` **不在** 原M0-WIN-LINUX workflow`on.push.paths`，那次提交实际上只跑治理，没有跑实网。**绝不把H2054记为native重测**。
- 本源在现有原生工作流 paths 中精确追加GUI C#、GUI bridge.py、bootstrap TCP guest.py三文件；单场仍必须由明确`[plan029-real-gui-cn]`提交标记和`m0_native_ci_scope.py`保护。其他原生场景不自动开启。本源触发真实H2055 GUI Win2025/WSL2，检验真实子进程EXIT0、1460/1389、OS/两出口/Stop。
- H2051 DNS TC原生与H2053仅源码build仍不同SOURCE，不混合报PASS；不重测H2031 padding、H2041 Game4。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"Source-locked actual WinForms harness path was omitted from push paths; correct CI trigger and retain H2050 first failure until real post-Dispose-repair Action passes."}
```
