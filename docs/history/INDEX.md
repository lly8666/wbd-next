# 历史索引

初始治理见 `docs/devlog/M0/GOV-001-complete.md`；2026-10-14 架构规划见 `docs/devlog/M0/PLAN-001-design.md`、当前设计入口 `docs/architecture/README.md`。旧“产品待讨论/禁止顺序A/B”已经显式被新方案与用户指令替代，历史原文保留，不重新导入当前 cursor。

整理触发：阶段完成、约 20–30 项变更或热上下文达到预算。整理不是删除失败；OPEN 风险不因年龄变成已解决。

PLAN-002逐模块细化及51项检查见`docs/devlog/M0/PLAN-002-complete.md`、`docs/architecture/modules/README.md`。receipt/桥接/计时和内存估算明确修订v1，PLAN-001当时的历史数字与证据不改写。日常接续只读cursor当前引用。

原日志、收据保持稳定路径，必要时用 supersedes/superseded_by 指向继任记录。大 artifact 会过期，hash 不能代替原内容；重要摘要与身份信息须留 Git。

## 2026-10-14～15 实现与治理阶段摘要

R0 来源/ABI/兼容向量建立后激活 M1 runtime、M2 recovery、M3 codec、M4 platform。四模块经历若干独立 native 验证并由 M0 集成；真实 Go protected TLS rollback/commit 已有组件证据。准确来源与未测范围集中见 `docs/evidence/M0/R0-M0-V4-owner-wave-integration-033.json`。

仍 OPEN：真实 Go→Rust authenticated owner / B01–B04；M3 CPU 计时窗口修复；产品、500Mbps、packet p99、物理机资格。旧 M3 Release 24 行中 22 行计时不一致为 INVALID，不能被功能绿灯覆盖。既有失败保留。

治理 v2：用户授权减少机械性返工，改主线增量审计、共享功能构建与必跑用例清单；不改产品协议或验收硬门。决策及迁移见 `docs/devlog/M0/GOV-002-incremental-ci.md`。当前任务取角色分支 cursor，不重复初始 R0/G2 初始化。
