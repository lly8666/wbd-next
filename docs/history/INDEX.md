# 历史索引

初始治理见 `docs/devlog/M0/GOV-001-complete.md`；2026-10-14 架构规划见 `docs/devlog/M0/PLAN-001-design.md`、当前设计入口 `docs/architecture/README.md`。旧“产品待讨论/禁止顺序A/B”已经显式被新方案与用户指令替代，历史原文保留，不重新导入当前 cursor。

整理触发：阶段完成、约 20–30 项变更或热上下文达到预算。整理不是删除失败；OPEN 风险不因年龄变成已解决。

PLAN-002逐模块细化及51项检查见`docs/devlog/M0/PLAN-002-complete.md`、`docs/architecture/modules/README.md`。receipt/桥接/计时和内存估算明确修订v1，PLAN-001当时的历史数字与证据不改写。日常接续只读cursor当前引用。

原日志、收据保持稳定路径，必要时用 supersedes/superseded_by 指向继任记录。大 artifact 会过期，hash 不能代替原内容；重要摘要与身份信息须留 Git。

## 2026-10-14～15 实现与治理阶段摘要

R0 来源/ABI/兼容向量建立后激活 M1 runtime、M2 recovery、M3 codec、M4 platform。四模块经历若干独立 native 验证并由 M0 集成；真实 Go protected TLS rollback/commit 已有组件证据。准确来源与未测范围集中见 `docs/evidence/M0/R0-M0-V4-owner-wave-integration-033.json`。

当时 OPEN：真实 Go→Rust authenticated owner / B01–B04；M3 CPU 计时窗口修复；产品、500Mbps、packet p99、物理机资格。随后 M3 精确 SOURCE 的新时钟验证已由 M0 留证于 `docs/evidence/M0/R1-M0-M3-015-0ecb-exact-release-049.json`；旧 M3 Release 24 行中 22 行计时不一致仍为 INVALID，不能覆盖原失败或外推产品 CPU/p99。其余资格按最新 cursor/evidence 判断，历史 OPEN 不能单独充当当前待办。

治理 v2：用户授权减少机械性返工，改主线增量审计、共享功能构建与必跑用例清单；不改产品协议或验收硬门。决策及迁移见 `docs/devlog/M0/GOV-002-incremental-ci.md`。当前任务取角色分支 cursor，不重复初始 R0/G2 初始化。

## 2026-10-18｜全角色交接瘦身（旧档完整保留）

原 `START_HERE.md` 与 M0–M4 五份固定提示词在 `docs/history/handoff/2026-10-18-pre-slim/` 保留当时全文，用于定位旧 H/任务/Actions 语境；**不再作为当前接手指令**。现行入口 `START_HERE.md` → `docs/handoff/README.md` → 最新 main registry 与各角色分支 cursor → 永久 `docs/prompts/<role>.md`。历史 devlog、evidence、决策和 Action 原件原路径保留；「旧失败」不得因此被覆盖或改判。该简化只改变阅读与交接导航，不改变任何工位权限/任务、产品功能或 CODE 验收。

## 2026-10-26｜W168 冻结 + Windows 真实功能集成

[按日期、来源、红灯查找](2026-10-26-W168-WINDOWS-INTEGRATION-INDEX.md)。完整原始 devlog/evidence 和旧 [handoff 快照](handoff/2026-10-26-pre-W168/README.md) 不动/不删；日常热读取改为 `docs/handoff/CURRENT_INTEGRATION.md`，不会复制过去上百条实验逐测结果到新 agent 的工作上下文。
