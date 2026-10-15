# GOV-002 增量审计与 CI 减负

用户明确授权实施 2026-10-15 治理审查建议。本任务使用独立 `governance/incremental-ci-20261015` 分支；不占用 M0 当前产品任务、不修改四个 worker 分支或产品源码。此隔离维护授权来自用户，集成仍核精确主线头，拒绝 force push。

原问题：固定 G2 起点导致 M3 已 98/99 个提交，工具同步多次特批；总测试数增长与 PASS 正则造成误报；相同源码五分支触发十套旧流程；project/registry/cursor 重复及“只有 governance”陈述过期。

改动：M0 已验收检查点后的逐提交审计；主线 workflow_run 只读中央检查器；权限不变的主线前进不作废结果；旧工具保留历史兼容。九套 R1/R2 功能流程合并为一次按依赖构建/八组消费，冻结原关键用例 ID、防空跑/意外忽略/坏日志/来源篡改，新增用例允许。R0 集成 CI 限主线，worker 保留自己的 native。语法检查先验 YAML/Python。任务细节移到既有决策，稳定入口同步。

硬门：精确 SOURCE/hash/run/attempt、隔离/所有权/generation/MTU、真实业务首次到达/无 HOL、性能一 Action 一工况同机 AB/BA 全部不变。功能构建合并不宣布运行时性能提升。旧失败不删除。所有执行验证仅 Actions；本地仅编辑与 Git 差异检查。

验证状态：固定候选 SOURCE 的 Actions 已通过，精确结果见 `docs/evidence/M0/GOV-002-qualification.json`；尚未合入 main。完成条件：治理正反例+真实四分支中央审计+候选整合主线后的八组 native 验证通过，文档与接手路径一致；不扩展为产品验收。回退使用本次变更前版本的 workflow/tools，保留新结果为历史；检查点不能凭回退动作重新解释为产品 PASS。

首轮 SOURCE `1b4be2e84c08e2bcdf36d12b6ae08857fc373df9`：治理回归 38700748281、四角色中央审计 38700748390、Go TLS 38700748219 全成功。native 38700748266 四个集成组成功、四个库组判 FAIL，但二进制退出均为 0：`--nocapture` 将成功用例的诊断输出插入 libtest 名称与 `ok` 之间，严格解析器因此误报缺用例。修复为普通功能验证采用 libtest 默认捕获成功输出；不删除必跑 ID、不放宽匹配、不改产品代码。旧 FAIL 保留。当前证据不是运行时性能结论。

第二轮中央审计 38701120518 发现 M1 的 open_requests 包含既有 G2 Markdown 协调请求；不能把它当 JSON Actions intent。修复仅区分协调文档与 dispatch JSON，二者都核存在性，JSON 继续核角色/epoch/格式；协调文档不冒充已 dispatch。另保留 registry 的简短 assigned_task 字段，避免详细任务归档后旧 worker cursor 覆盖最新分配。

集成刷新：主线在维护期间前进至 `3f1b458de2c66cbfa5567c147909c9b2b22d06f5`。完整保留新增 Go/Rust TEST-ONLY probe、M1 early RX、M4 burst、M3 clock 及其证据；不回退任何产品文件。合并替换的旧工作流新增必跑 ID 一并纳入：codec98、platform75、engine87、recovery51、四个集成组3/3/11/6；Go普通TLS12。四个新检查点分别下载当前 Governance 精确 attempt artifact 核 role-identity/receipt/hash/conclusion，记录 `GOV-002-checkpoints.json`；未将 M3 CODE 源码称作已完成 H。

## 固定版本验收与并行开发交接

实测 SOURCE `444c51e48de0063bb91c354e45078fcc158cee06`，四个 run 均 attempt 1 / SUCCESS：

- `38736284748`：治理工具与历史兼容正反例 163 项，结构与既有 R0 ledger 通过。
- `38736284616`：一次 Release 构建，八组共 334 个必跑功能用例通过；两个已明确排除的性能基准保持 ignored，不计功能 PASS，不用功能矩阵生成性能结论。
- `38736284582`：真实 Go TLS 的 12 个必跑用例通过；不等于生产 Rust admission 或产品资格。
- `38736284708`：M1–M4 真实远端 SOURCE 范围审计通过。本次四个头恰好均等于已核验检查点，增量非空与拒绝路径由 Actions 正反例覆盖；默认分支上的 `workflow_run` 事件接入要等合并后生效，不冒称已在 main 验证。

已下载 13 份结果/构建 artifact，逐份核 GitHub digest；核两份构建 manifest、九个测试二进制的 size/hash、结果 SOURCE/run/attempt 与测试日志 hash，0 mismatch。本地只读解析这些 Actions 产物，没有执行测试程序。上述两个早期 FAIL 保留。随后收口提交仅补证据/文档并删除章程“当前未开始”的过期描述，不把文档 HEAD 当实测 SOURCE。

用户确认其他 agent 仍在开发，故本维护采用 **独立 PR #4，由 M0 在当前任务安全交接点统一集成**。不追逐 main 每个新提交、不改 worker 分支、不接管或覆盖 M0 cursor。状态为 `READY_FOR_M0_SAFE_BOUNDARY_MERGE`，不是 `MERGED`。

M0 最小接入步骤：

1. 完成当前原子任务的 S/H，再读取 PR #4 与上述 evidence。保留接入时 main 最新产品代码、任务分配、cursor、权限及资格记录；遇到 registry/project 文本冲突，保留当前进度并吸收治理简化，不能用本分支快照回退它们。
2. 正常合并 PR，不 reset/force push。如果 main 在 `3f1b458` 后又向被替换的旧流程增加了必须测试的场景，将对应 ID 纳入 `.governance/native-suites.json`；没有对应覆盖时先保留那条旧流程。不要为消红删用例或降门槛。
3. 核合并 SOURCE 自动触发的维护/受影响功能 CI，以及中央范围审计。现有证据只对应 `444c51e`；合并后尚未跑的范围如实记 NOT_RUN。worker 无须立刻同步检查器；旧分支 workflow 触发方式在其后正常同步时更新，不为切治理打断产品任务。
4. 按已有 devlog/evidence/cursor 规则记录集成；不另造交接系统。非本次回归范围的性能、Windows/ARM 实机、生产端到端资格仍以原任务证据为准。
