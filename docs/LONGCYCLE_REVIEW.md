# Longcycle 审阅与本仓库取舍

参考仓库：https://github.com/lly8666/longcycle-core

审阅固定提交：`1dda7509ec3f270be5248f786a78a9f244bff684`（2026-10-13 读取）。

主要依据：

- [AGENTS.md](https://github.com/lly8666/longcycle-core/blob/1dda7509ec3f270be5248f786a78a9f244bff684/AGENTS.md)
- [治理说明](https://github.com/lly8666/longcycle-core/blob/1dda7509ec3f270be5248f786a78a9f244bff684/docs/development/agent-governance-operating-manual.md)
- [远端 worker 接续](https://github.com/lly8666/longcycle-core/blob/1dda7509ec3f270be5248f786a78a9f244bff684/docs/development/remote-worker-continuity.md)
- [并行治理](https://github.com/lly8666/longcycle-core/blob/1dda7509ec3f270be5248f786a78a9f244bff684/docs/development/parallel-agent-development.md)
- [能力归属](https://github.com/lly8666/longcycle-core/blob/1dda7509ec3f270be5248f786a78a9f244bff684/docs/development/capability-governance.md)
- [全新聊天审计](https://github.com/lly8666/longcycle-core/blob/1dda7509ec3f270be5248f786a78a9f244bff684/docs/development/fresh-chat-handoff-audit.md)

## 直接借鉴的治理思想

固定 workstream / 可替换 agent；main reservation 与分支 cursor 分开；一条串行集成通道；S→H；远端事实优先；逐提交 delta 防 change-then-revert 遗漏；副作用 intent/receipt；热温冷分层；稀疏修复经验；任务向上对齐与 done_when 收口。

## 针对 WBD 增强与简化

| 设计 | 本仓库处理 |
|---|---|
| 交接与测试 | 三轴分离；checkpoint 可覆盖文档进展，last_tested_source 仍钉住真正测试对象 |
| 外部运行 | Actions 请求身份、run attempt、实际配置/夹具/源码、重复 dispatch 与过期证据成为一等事实 |
| 快速接手 | 32KiB/8 文件组合预算，不只限制单个全局 JSON |
| 多人写记录 | 普通 worker 不写总状态；当前结论不复制完整历史 |
| 治理成本 | 不创建独立数据库、长期 agent 服务、另一个任务平台或多套 owner registry |
| 权限机制 | 明确工程 fence 与实际 GitHub 分支保护不同，不夸大 JSON 的执行权限能力 |
| 治理验证 | 反例演练覆盖遗漏、回滚、错源码、伪 PASS、重复请求；机器演练与真实 fresh-chat 审计分开 |
| 产品阶段 | 现在只冻结治理与用户目的，不提前冻结 Rust 架构和数字 |

不搬运 Longcycle 的研究认识论、行业地图、数据库迁移、Drive 数据面与研究任务；不复制原业务代码。本仓库工具独立编写，治理词汇仅用于说明共同方法。

“增强”指更贴近当前工程风险，不代表已经证明比 Longcycle 普遍更好。后续应按实际接续成本、漏记恢复率、重复测试率、误认 PASS 和上下文成本评价。
