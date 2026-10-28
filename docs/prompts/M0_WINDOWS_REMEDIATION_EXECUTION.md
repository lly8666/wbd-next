# 旧 Windows 整改提示词：入口已统一

> **当前提示词不是任务发派入口**：2026-10-28新用户选择方案 B，请按main registry.goal 执行 [PLAN026 Windows Rust NativeOwner](../decisions/M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md)，先Normal/off完整代码、集中功能/CPU A/B，后其它模式/Health/lane；本页旧整改内容仅保留历史审计和失败来源。

此提示词由 2026-10-28 主线收尾包接替，不再整单重做 S1–S61。
永久接手使用 [M0.md](M0.md)，当前任务从 main registry.goal 发现。
本轮具体范围见 [主线整改完工包](../decisions/M0-MAIN-CLOSEOUT-20261028.md)。

原 [2026-10-27施工方案](../decisions/M0-WINDOWS-EXTREME-REMEDIATION-20261027.md) 保留计算和审计依据；需先对照 main 已实现/证据，只有仍然成立的缺口继续做。源码和夹具在 main，整批代码完成后集中 Actions，不复活旧实验分支。
