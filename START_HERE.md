# WBD Next｜新 agent 唯一启动入口

仓库 `lly8666/wbd-next`；控制分支 `main`，其他工位分支由 main 的 `.governance/registry.json` 授权。**先刷新远端，不相信聊天、旧提示词、目录中的某个日期或本地缓存。**

## 最小热读取（不超过 8 文件）

**用户直接授权的独立网络测试任务例外**：按 [NETWORK_AUTONOMOUS_WORK](docs/testing/NETWORK_AUTONOMOUS_WORK.md)读取任务分支的当前计划与 `docs/evidence/network-matrix-work/status.json`，不领取M0–M4身份、不创建正式角色cursor、不等待registry派单。下列正式角色流程仅用于避冲突，不覆盖该独立任务已有的自主修复与Actions授权。

1. `AGENTS.md`、`PROJECT_CHARTER.md`。
2. main 的 `.governance/project.json`、`.governance/registry.json`。
3. **`docs/handoff/README.md`**：五工位概览、产品硬门与证据导航（这是带日期的索引，非实时权威）。
4. main 的 `docs/prompts/<role>.md`：永不过期的角色责任与停止条件；**在 registry 指定的角色分支**读取 `.governance/workstreams/<role>/cursor.json`。

## 开工/恢复（同一 agent 与全新 agent 完全一致）

先确认 role/active/branch/task_id、reservation_revision、assignment_epoch；核对 cursor.checkpoint_sha 是远端 HEAD 的祖先，**逐个提交**检查 changed paths。检查 cursor 中 open_requests 与已提交 Actions 的精确 run/attempt/artifact；失败、403、超时或未跑均不能隐去。判 `CLEAN`（事实交接完整，非产品 PASS）、`RECOVERY_REQUIRED`（先补事实）或 `BLOCKED`（身份/证据/权限冲突）。

CLEAN 后依 main registry 的 **assigned_task** 与角色 cursor.next_action 推进一项完整能力批次（可同时跑许多便宜功能断言）；M0 的共享集成不需要等所有工位齐活。必要时按角色只读 `docs/architecture/modules/README.md`、`docs/architecture/TEST_PLAN.md` 和冻结 FEC2 规范，勿一次加载历史文档。

**任务发现**：registry的`goal`应引用当前任务决策文件和本角色章节，详细验收读那里；`docs/prompts/<role>.md`仅是长期启动说明，不发布具体任务。新包由M0一次更新registry+决策发布，工位补旧事实后自行接续；不需要每轮给用户换初始提示词。缺引用由M0补入口，禁止从历史日期猜任务。详见GOVERNANCE第3节。

写入：先 S（代码/收据/文档），精确 SOURCE Actions 验证，后 H（**只修改自己的 cursor**）；再次刷新远端确认。工作分支不得修改 main 的登记权限，不 force push，不擅自开展下一包。每个性能 Action 单一场景；AB/BA 必须同 job/VM。无新增信息的重复失败先缩小复现，不刷 seed。

**产品保守默认**：FEC2 **OFF**；只有测试专用的真正内核 FEC2 链路与组件组合部分通过。缺少的 M1 正式调度、M2 反向认证收据、Go applied CLI/GUI、跨端及遗留 Stop/MTU/150ms/大 UDP/p99 均需读取最新证据，不以热索引自动判关。旧提示词/历史归档与原 evidence 永久可查：`docs/history/INDEX.md`。

说明：若 main registry 和 worker cursor 记录的任务不同，**权限/本轮任务以 main registry 为准**，从决策/证据理解变更，不让旧 cursor 抢权限。治理细则 `docs/GOVERNANCE.md`；中央 Scope 唯一 G2 完整分页来源，旧64规则只用于独立恢复诊断。

**PLAN021 用户新硬门**：精确 SOURCE Actions 正向功能 PASS 可开放该已接线模式供显式网络试验，无须先跑物理/全矩阵；未接线不冒充 PASS，认证、WFP、owned WAL、Stop 仍强制。见 [PLAN021](docs/decisions/M0-PLAN021-Actions-functional-pass-opens-network-trial-20261021.md)。
