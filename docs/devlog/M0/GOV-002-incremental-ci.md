# GOV-002 增量审计与 CI 减负

用户明确授权实施 2026-10-15 治理审查建议。本任务使用独立 `governance/incremental-ci-20261015` 分支；不占用 M0 当前产品任务、不修改四个 worker 分支或产品源码。此隔离维护授权来自用户，集成仍核精确主线头，拒绝 force push。

原问题：固定 G2 起点导致 M3 已 98/99 个提交，工具同步多次特批；总测试数增长与 PASS 正则造成误报；相同源码五分支触发十套旧流程；project/registry/cursor 重复及“只有 governance”陈述过期。

改动：M0 已验收检查点后的逐提交审计；主线 workflow_run 只读中央检查器；权限不变的主线前进不作废结果；旧工具保留历史兼容。九套 R1/R2 功能流程合并为一次按依赖构建/八组消费，冻结原关键用例 ID、防空跑/意外忽略/坏日志/来源篡改，新增用例允许。R0 集成 CI 限主线，worker 保留自己的 native。语法检查先验 YAML/Python。任务细节移到既有决策，稳定入口同步。

硬门：精确 SOURCE/hash/run/attempt、隔离/所有权/generation/MTU、真实业务首次到达/无 HOL、性能一 Action 一工况同机 AB/BA 全部不变。功能构建合并不宣布运行时性能提升。旧失败不删除。所有执行验证仅 Actions；本地仅编辑与 Git 差异检查。

验证状态：待 Actions；最终结果另附 evidence。完成条件：治理正反例+真实四分支中央审计+合并后八组 native 验证通过，文档与接手路径一致；不扩展为产品验收。回退使用本次变更前版本的 workflow/tools，保留新结果为历史；检查点不能凭回退动作重新解释为产品 PASS。

首轮 SOURCE `1b4be2e84c08e2bcdf36d12b6ae08857fc373df9`：治理回归 38700748281、四角色中央审计 38700748390、Go TLS 38700748219 全成功。native 38700748266 四个集成组成功、四个库组判 FAIL，但二进制退出均为 0：`--nocapture` 将成功用例的诊断输出插入 libtest 名称与 `ok` 之间，严格解析器因此误报缺用例。修复为普通功能验证采用 libtest 默认捕获成功输出；不删除必跑 ID、不放宽匹配、不改产品代码。旧 FAIL 保留。当前证据不是运行时性能结论。

第二轮中央审计 38701120518 发现 M1 的 open_requests 包含既有 G2 Markdown 协调请求；不能把它当 JSON Actions intent。修复仅区分协调文档与 dispatch JSON，二者都核存在性，JSON 继续核角色/epoch/格式；协调文档不冒充已 dispatch。另保留 registry 的简短 assigned_task 字段，避免详细任务归档后旧 worker cursor 覆盖最新分配。
