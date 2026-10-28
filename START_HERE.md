# WBD Next｜从 main 接续

**M0 在 main 连续开发；独立 FEC 历史工位已完成。** 不再寻找“最新实验分支”。任务/进度/证据分别有唯一落点，旧工作提示词不自动派活。

## 最小启动读取
1. AGENTS.md 与 PROJECT_CHARTER.md：目标、硬门、开发方法。
2. main 的 .governance/project.json 与 .governance/registry.json：阶段和权限/当前包。
3. docs/prompts/M0.md 与 main 的 .governance/workstreams/M0/cursor.json：长期职责、当前事实/在途 run。
4. docs/features/README.md：功能目录，用只读 `python tools/feature_catalog.py list --query <主题>` 或 GitHub entries 按需查卡。
本页加上述七项合计八文件；不要再一次性载入旧 devlog。非 M0 的明确授权角色读取自身 prompt/cursor。

## 当前新任务
M0 最新授权是 [PLAN026 Windows Rust NativeOwner](docs/decisions/M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md)，任务有效性仍按 main registry.goal。**文档尚未代表产品实现或测试**；先结算旧cursor所载在途N0 Actions事实，再 Normal/off整批编码/测试/同机性能，达标迁其它模式/动态lane。

## 开工
刷新 origin/main，检查本地未提交工作的归属。核对 cursor.checkpoint_sha 后实际增量、最新相关 Actions 和未写结果；必要时补 recovered 日志。不要扫全部历史或从旧分支 cursor 续错任务。registry.goal 给出当前施工方案，进度不从方案推断。

M0 的 source、夹具和结果均进 main；编译产物固定 SOURCE 可跨 Actions 复用。旧分支已经有独有在途工作时，先结算和选择性带回 main，一次收敛即可，不重跑已完成矩阵来“证明合并”。源码与 harness/binary 来源不同必须分列。

整批写完再测试；功能合批，性能单 Action 单场景/测量 job，同机顺序 A/B。容量不足停止更重同族并报告实测边界，不冒充极限 PASS。

## 只在需要时打开
- [当前逻辑/问题导航](docs/handoff/CURRENT_INTEGRATION.md)，数字仍以最新 cursor/证据为准。
- [历史怎么找](docs/history/2026-10-28-M0-MAIN-HANDOFF.md)：旧 FEC、Windows 接线、故障、性能和方案索引。
- [模块设计](docs/architecture/modules/README.md)、[网络诊断](docs/testing/NETWORK_TRIAGE.md)：修哪个模块再读哪个。
main 存在、代码已集成、功能通过、性能/物理通过是不同结论。历史失败保留但不重新生成已经关闭的待办。
