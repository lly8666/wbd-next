# 历史索引

初始治理见 `docs/devlog/M0/GOV-001-complete.md`；2026-10-14 架构规划见 `docs/devlog/M0/PLAN-001-design.md`、当前设计入口 `docs/architecture/README.md`。旧“产品待讨论/禁止顺序A/B”已经显式被新方案与用户指令替代，历史原文保留，不重新导入当前 cursor。

整理触发：阶段完成、约 20–30 项变更或热上下文达到预算。整理不是删除失败；OPEN 风险不因年龄变成已解决。

PLAN-002逐模块细化见`docs/devlog/M0/PLAN-002-design.md`、`docs/architecture/modules/README.md`。receipt/桥接/计时和内存估算明确修订v1，PLAN-001当时的历史数字与证据不改写。日常接续只读cursor当前引用。

原日志、收据保持稳定路径，必要时用 supersedes/superseded_by 指向继任记录。大 artifact 会过期，hash 不能代替原内容；重要摘要与身份信息须留 Git。
