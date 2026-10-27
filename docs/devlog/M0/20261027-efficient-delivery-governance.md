# 2026-10-27 高效能力批次：治理与CI节奏

用户授权减少磨蹭、重复验收和过细留痕。本次从最新隔离集成 SOURCE
e9506950a44d1a02e2e7878bafa0c6362c6404d7 开独立 experiment/windows-wiring-efficiency-20261027，
只改治理文档、CI及装配辅助工具，不修改产品算法、运行参数、M0权限/cursor或main。

## 已观察问题与意图

- 08:13–08:59多次完整原生Actions验证共同Normal通路，Game公开入口仍拒绝；
  既有模块新增回归有价值，但完整系统反复启动不能替代一项新增可用模式。
- Actions40430514115先遇装配清单遗漏；40432270310在Rust17项回归通过后，
  Go测试编译因旧p.blockID字段失败，真实网络NOT_RUN。源码/调用方测试/清单应一起改。
- 因此拆成静态与Windows Go编译预检在前、完整模式验收在后。
  普通集成push不再自动编Rust/装驱动/启动WSL；相关代码批次标记[wiring-full]或手动dispatch才完整验收。
  main原完整门不改，cleanup、真实SOURCE、原生断言均保留。预检PASS不等于产品PASS。
- 抽出现有同源装配为tools/prepare_windows_wiring.py供两层共用，保留原始Go固定SHA、Git blob验证、
  同一额外bridge集合和禁止覆盖已有owner的行为；不自动刷新hash骗过旧manifest。
- 一份批次intent覆盖正常修复；交付/暂停/恢复再H。任务仍从已有registry/decision发现，
  下阶段按功能目录缺口合批，不新增审批系统。旧设计中的早期基线示例不再当当前待办。

## 验证计划与已知基线

仅在Actions跑CI规则单测、语法/目录/结构和真实Windows编译预检。
当前基线已知p.blockID测试编译失败预期被前置捕获，留给正在开发的M0修；不在治理任务暗改产品。
旧maintenance的FEC冻结manifest差异同样保留。未运行完整产品或网络矩阵，不声明产品通过。
首轮结果在本日志追加。意外中断按Git/Actions恢复，不能伪造全绿。

```feature-impact
{"kind":"none","ids":[],"reason":"只改变开发批次/留痕频率和CI触发、共享现有精确源码装配，不改变运行时功能、默认值、平台资格或硬约束。"}
```
