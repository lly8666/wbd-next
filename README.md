# WBD Next

面向可替换聊天 agent 的下一代 WBD 开发仓库。**目前只建设开发治理，产品架构待讨论，尚无 Rust 数据面实现或产品性能资格。**

目标：真实业务首次到达效率优先，低延迟、无跨业务 HOL、低 CPU 与合理带宽成本；允许有界内存换 CPU。保留必要正确性与隔离边界。

## 从哪里开始

- 新聊天：[START_HERE.md](START_HERE.md)
- 项目主旨：[PROJECT_CHARTER.md](PROJECT_CHARTER.md)
- 当前阶段：[项目状态](.governance/project.json)
- 分工与唯一写入权：[模块登记](.governance/registry.json)
- 固定提示词：[M0 集成](docs/prompts/M0.md)、[M1 运行时](docs/prompts/M1.md)、[M2 恢复](docs/prompts/M2.md)、[M3 编码](docs/prompts/M3.md)、[M4 平台](docs/prompts/M4.md)
- 操作协议：[GOVERNANCE.md](docs/GOVERNANCE.md)
- 检查与演练：[Actions](https://github.com/lly8666/wbd-next/actions/workflows/governance.yml)

## 已搭建的治理能力

1. 主线 reservation 与工作分支 cursor 分开，固定角色可以由全新聊天接续。
2. 实质提交 S → 单独交接确认 H；中断后从逐提交差异发现遗漏，先补记录再开发。
3. 交接完整性、任务进度、测试资格分别表示，`CLEAN` 不等于产品 `PASS`。
4. Actions intent/receipt 使用唯一请求号、精确 SOURCE、夹具与配置身份；先查原 run 再重跑。
5. 当前状态有体积上限，历史与失败按需检索，不把开发年表塞进启动上下文。
6. 语义约束与可调整参数分开；不允许靠改验收题目制造通过。
7. 正常业务、稀疏业务重传比例的最新要求已经保留；具体算法参数没有冻结。

检查器与演练是 Python 标准库工具，**不是产品语言选择或运行时依赖**。所有执行验证在 GitHub Actions；聊天环境可读写文件、操作 GitHub，但不假定有本地终端或常驻协调进程。

## 当前边界

M0 负责治理初始化与下一阶段规划。M1–M4 只是可接手的候选角色，未分配开发权限、分支或具体任务。不应现在启动产品实现、性能测试或物理机部署。

治理设计参考 [Longcycle Core](https://github.com/lly8666/longcycle-core)。审阅版本、借鉴范围及差异见 [来源与设计取舍](docs/LONGCYCLE_REVIEW.md)。未复制其研究数据、业务代码或历史任务。

公开仓库不含旧项目凭据、用户业务正文、机器地址清单或大抓包。历史 WBD 测试不自动构成本仓库资格。
