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

首轮SOURCE 2e24fe91b1aa244579f4e3e8b7d2769e98e48ac8：24项定向测试及Windows静态预检通过。
Governance 40434507538 的随后仓库结构检查失败：集成分支原M0 cursor把Markdown日志、异源历史证据、
功能卡放进 evidence_refs，JSON读取失败；该cursor在基线已如此，本次没有改写它或替M0确认进度。
补充诊断让结构错误直接报告具体路径，保留检查强度，M0下次交接把背景引用归context_refs/日志索引，
evidence_refs只放同源结构化收据即可。不要为此重跑产品网络测试。
Maintenance 40434507602 的229项还保留4条旧冻结blob子断言失败（含原adapter和FEC policy两文件）；
这些产品文件均未由本次改动修改。不会把新CI单测通过写成全仓库/产品通过。

最终工具SOURCE a46bab888b4fadd57572f31af8d67293eecfebae：
- Actions40434802474：25项定向治理/目录/交付节奏测试PASS；目录声明检查PASS，随后既有cursor结构错误仍FAIL。
- Actions40434804189静态/装配检查PASS、原生Windows同源装配PASS；编译预检在记录时仍运行。
- 首个完整预检Actions40434507724在源码2e24fe91已实测捕获同一个p.blockID测试编译错误，
  Linux完整构建及Windows原生功能job均SKIPPED，未编Rust/未装驱动/未启动WSL；证明前置拦截实际生效。
- 完整原生产品资格NOT_RUN；maintenance整体FAIL保持，原始记录不覆盖。
交付PR #31只合最新integration分支。M0接手按TEST_PLAN第0节执行，先修已知编译调用方和自身cursor引用分类，
再以完整Game/Fixed/Auto能力推进；不需要为读取这些规则重新建任务/epoch或重跑性能。

```feature-impact
{"kind":"none","ids":[],"reason":"只改变开发批次/留痕频率和CI触发、共享现有精确源码装配，不改变运行时功能、默认值、平台资格或硬约束。"}
```
