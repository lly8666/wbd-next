# 开发治理协议 v2

## 1. 三种状态不能混为一谈

| 轴 | 权威 | 含义 |
|---|---|---|
| 交接完整性 | 刷新远端后按提交图和请求事实推导 | CLEAN / RECOVERY_REQUIRED / BLOCKED |
| 开发进度 | 工作分支 cursor | planned / in_progress / partial / verifying / ready_for_integration / blocked / paused / superseded |
| 验证资格 | 精确 SOURCE、夹具、配置、run/attempt/产物 | PASS / FAIL / INVALID / CAPACITY_LIMITED / UNSUPPORTED / NOT_RUN / INCONCLUSIVE |

格式检查只能证明结构符合规则，不证明产品正确。事实、判断、计划分开；“实现存在”“某场景通过”“全产品可交付”不是同一结论。

## 2. 目标、范围与复杂度

当前任务必须能解释：原子动作如何推进模块目标、阶段目标和项目主旨。只把这条关系的简洁结论留痕，不保存私人推理或每轮长篇自述。

每项任务有 task_id、why_now、done_when、一个 next_action。达到 done_when 就停止打磨；没有新证据，不重开历史方案比赛。需要新增接口或资源时记录目的、成本、所有者、失败行为、上界与删除条件。

“原子任务”按可验收能力划分，可包含多项实现和相关反例；不是每包、每断言、每个参数值或每轮聊天各立任务。next_action 表示下一项完整交付，可内含顺序步骤；授权范围内做完这些步骤无需反复等新分配。测试推进唯一细则见 `docs/architecture/TEST_PLAN.md` 第 0 节。不要另建逐断言审批表或治理计数门。

G1 在授权范围内自主执行。G2 接口/职责调整由 M0 合并影响与回归，避免两位作者各改一套语义。G3 才涉及改变用户原则/范围/未授权影响；已有用户授权不能被治理文件重复变成审批要求。

## 3. 一个控制面，多条工作线，一条集成通道

main 的 registry 是权限依据；worker 分支不能通过修改自己的 registry 扩权。worker 的 cursor 是当前工作事实，不是 main 上那份旧副本。

M0 登记 active role 的 branch、epoch、revision、写入前缀、语义归属、goal、done_when；工作分支从明确基线创建。不同 active worker 的写入范围不能重叠。共享接口、根依赖、CI、章程、全局目录交 M0 串行集成。

### 完整工作包与阶段集成（2026-10-17）

工作包就是现有`assigned_task`的一项完整可交付能力，不新增层级或状态机。它包含实现、必要功能测试、修复、适用成本验证和交付记录；不能拆成每完成一步就等M0重新派单。旧任务完成不自动扩权，由M0一次登记下一工作包；包内后续步骤均已授权。

- **一次明确边界**：复用registry和任务文档，列目标/停止条件、允许路径及排除文件、精确基线和公共接口、必要验证、暂缺真实接线的范围。先核已完成能力，不按工时或聊天次数划包。
- **工位自行推进**：在自己的分支连续实现、用既有Actions测试、定位修复、记录S/H。局部PASS、commit或H不是请求集成；包未完成时`next_action`写包内可执行工作，不默认写“等M0分配”。整包达到done_when才交付并停止无目标打磨；跨聊天沿固定提示词继续该包。
- **依赖不强迫逐步合并**：尽量使用冻结接口和已合入共享类型。必要接口确实缺失时，M0一次处理最小编译接口/夹具入口；worker继续包内独立内容。组件替身不能另造生产认证/数据链路。不跟踪另一工位浮动HEAD、私改其文件或自行拼组合资格；必须消费其产物时固定来源并由M0预先明确兼容范围。
- **模块负责测试**：已有workflow和权限可满足时，worker自行留intent、dispatch、验产物和修复，不等M0代跑或逐次批准。需改共享workflow时M0一次补入口，不建新CI审批队列。功能批量、性能一Action一场景、配对同job顺序和容量停止规则保留。
- **M0按事件集中集成**：完成当前安全可停的调优批次，或接下来的真实路径需要已交付模块时，核一批精确来源并做受影响组合验证。不等齐四个工位，也不因局部绿灯就中断调优；首次不稳定接口需要时做一次最小接线，不能把全部集成拖到产品末尾。
- **只升级真实阻塞**：公共wire/ABI/所有权契约需变、活动作者同文件冲突、无法独立解决的依赖、共享硬门/数据正确性缺陷，才需M0提前裁决。记录事实、最小复现、受阻范围和建议，独立工作继续；自己的普通编译/单测失败自行修复，不借阻塞越权。
- **等待集成仍保持有界**：交付精确SOURCE/基线、接口/配置变化、测试与NOT_RUN、未解决问题和接线说明。等待期间不刷同样测试、不不断追随main无关提交、不开展未分配功能。M0集成发现的问题仍属原包修复，无需重新派功能任务；交付/暂停及时H，未测新提交不能继承旧PASS。

用户已允许M0调优与其他模块包并行，覆盖旧024“只允许其他工位收尾/结束后才派下一波”的限制。M0优化目标、各角色权限和产品硬门保留，不因此开放生产capability。M0不得同时修改已交给worker的文件，必要接管先明确单一写入者；无需新增总管或另一套进度数据库。

每个分支只有一位活动写入者。普通全新聊天接续同一已释放角色不增加 epoch；发生撤销或重新分配时由 M0 增加 epoch，必要时换 producer 分支。不要仅凭多久没提交就断言另一聊天死亡。

操作前刷新精确 ref；采用 fast-forward/expected-parent 写入，拒绝 force push。GitHub Connect 多文件提交优先创建一个 tree/commit；若只能逐文件操作，保持 WIP，最终 H 前逐提交核对。推送冲突必须重新核对，不能静默覆盖。

epoch/检查器是工程约束，不是恶意同账号写入者的安全隔离。仓库权限和 required checks 是另一层；分支保护实际是否启用必须单独记事实。

## 4. S → H 与中断恢复

S：代码、文档、请求、结果等实质工作提交。H：单独一次只更新本角色 cursor 的提交。

S→H 是事实恢复边界，不是强制每个内部小步骤停工交接。一个能力批次可以有多个必要代码提交，结果尽量汇总为一份日志/证据并做一次 H；实际暂停、交付或中断恢复仍及时 H，外部动作前仍先留 intent。不得为省记录隐瞒失败或长时间积攒未推送工作。

H.checkpoint_sha 指向已核对的 S，避免试图把一个提交自己的 SHA 写进自己。H 的 diff 只能包含登记的 cursor 文件。

checkpoint_sha 与 last_tested_source 独立：前者表示交接覆盖到哪里，后者表示具体检查跑在哪个提交。后续文档提交不能自动继承为“新 SOURCE 全通过”；同时，文档收据的出现也不应抹掉先前精确源码的真实证据。

恢复步骤：

1. 刷新 main registry 与 worker HEAD；校验 epoch/revision/branch。
2. 验证 checkpoint 是 HEAD 的祖先，逐提交检查路径。净 diff 为空不等于没有遗漏工作。
3. 只读取差异涉及的模块规则、修复经验和收据。
4. 有遗漏时新增 recovered 日志，记恢复者、原提交、实际观察、未知项与验证范围。不得伪造原作者理由。
5. 已结束未登记的 Actions 先读 run/attempt/manifest；只有 intent 时先找实际外部对象。
6. 推恢复 S，然后推 cursor-only H；重新查询远端确认。
7. CLEAN 后才开始新的原子任务。CLEAN 且任务 blocked 是合法组合。

缺失祖先、分叉、错误 epoch、非预期作者或超出有界检查范围时不猜 CLEAN，输出 BLOCKED 和具体修复动作。无推送、无保留环境的内容不能恢复；从上个远端动作重做，并承认这个边界。

本工具自动检查明确的元数据/提交/请求一致性；开发意图、语义正确性、真实因果仍需 agent 阅读与判断。

## 5. Actions 身份与副作用

所有执行验证在 Actions。聊天只依靠 GitHub 也能开工，不需要本地 git、常驻进程或 agent 间消息。

每次外部动作前先推 intent。Actions 使用稳定 request_id、role_id、task_id、source_sha、harness_sha、config_sha256、scenario、seed、kind。只有明确没有同一请求的已有 run，才能 dispatch；网络超时不是“没执行”的证明。

记录 run_id、run_attempt、workflow、job、实际 checkout SOURCE、配置 hash、产物 hash 与环境。相同 request_id 出现两条 run 时标记重复，不能挑更好的一条；重跑用新的 request_id 并引用 supersedes_request。

性能：一个 Action 一个场景/配置/seed、一个测量 job。2026-10-14 用户要求已覆盖旧顺序AB禁令：旧新性能必须在同 job/VM 顺序AB或BA，声明两份完整SOURCE和构建hash，按 ACTIONS_CONTRACT 校验两leg时间/身份。禁止并发争用、跨job冒充同机、隐含多配置矩阵。预声明同配置损伤波形允许。不同模块独立Actions可并行，功能/unit批量执行不等于性能资格。

run-name 供人路由，manifest 和 GitHub API 才用于核验。正常分支 CI 使用 event + SHA + run_id 的身份；手动请求将 request_id 放入 run-name。禁止只凭“最近绿色”认领结果。

正式测量不因普通 push 自动取消；concurrency 分组包含 workflow/role/request，不能全仓共用取消组。当前 workflow 包含治理、native 组件回归和专项性能；范围以本次实际产物为准。

只读审计无法保证外部副作用 exactly-once。intent + 唯一编号 + 先查后发是可恢复的去重机制，出现竞争或查询不完整时停止重复触发。

## 6. 证据与验收

每份 PASS 附精确范围，不使用无限范围的 `all_passed`。关键证据摘要进 Git；原始大数据放有界 artifact，保留到期信息。secret 与业务正文不上传。

runner CPU/ISA、架构、配额、PSI/steal、注入与内核/队列 drop 是性能条件。容量不够不能冒充协议 FAIL 或 PASS；不同 CPU 不直接比较单次 CPU-s。诊断 ON 与默认 OFF 分开，p99 同时报告 missing/goodput，禁止丢掉慢包改善数字。

产品方案未定时不编造阈值。后续验收先声明工况、理论参考与合理允许带，硬门和经验阈值分开。需要改阈值时另记原因、影响和旧结果，不能同一变更悄悄修改题目与答案。

## 7. 有界记忆

热：root 启动集 + 角色 prompt/cursor，总计最多 8 文件、32KiB；cursor 最多 8KiB、每类引用最多 8。

温：当前差异、未结束 intent、近期失败、有关决策，按需读取。

冷：完整 Git、旧 devlog、历史方案与原始 artifact，按明确问题检索。每角色最多 12 个活跃测试请求；完成请求移到归档索引而非持续增加热 cursor。

阶段完成、约 20–30 项变更或接近预算时整理。旧结果稳定路径保留，摘要以 precise refs 指向原件；不能删除失败、吞掉 OPEN 或把历史 next_action 搬回热状态。

修复经验只记录容易复发的非显然行为，不给每个 helper 创建卡片。功能语义归属只在 registry 维护，不再建立第二套能力登记。

## 8. 完成与集成

worker ready_for_integration 前：接口行为、正确性证据、适用配置/CLI/GUI/catalog、资源成本、未验范围、回退方式齐全。M0 重新核实际 SOURCE，集成后跑必要组合回归；模块通过不等于产品通过。

没有新改动、反例或必需集成影响时不反复跑同一测试。两次同失败无新信息就做更小定位。工具演练不能冒充真正全新聊天验收；二者分别留状态。

## 9. 当前工具

- `validate`：当前仓库结构、边界、热上下文、请求/证据字段检查。
- `audit --role M0`：只读刷新 GitHub，核 main 权限、精确分支、checkpoint 逐提交差异与待确认请求。
- `receipt --result PASS|FAIL ...`：Actions 输出具体 run 身份和文件清单，不能自行证明该 run 结论。
- `python -m unittest discover -s tests -v`：中断、反例和身份契约演练，仅在 Actions 运行。

GitHub API 不可读、权限不足、结果分页超限都明确报出，不回退到猜测旧缓存。

## 10. v2 增量审计与共享工具（覆盖 v1 G2 固定起点审计）

- 主线 `.governance/scope-checkpoints.json` 是 M0 已验收范围检查点，不是 worker 可自行移动的交接 cursor。首次基线来自已留痕的四个 worker H / Governance 证据。
- `Central worker scope audit` 从主线快照运行 `tools/scope_audit.py`，只读 GitHub 元数据，绝不执行 worker 代码。worker 每次 Governance 完成会触发中央审计；不需要复制新工具或改工作分支。每份结果含 SOURCE、checker/control SHA、权限快照与 run 身份。
- 每轮只审检查点后的完整提交；路径改后又撤回仍检查。64 是单轮增量预算，不是分支终身提交上限。达到约 20–30 个新增提交或模块集成完成，M0 读取最新中央 PASS artifact / GitHub conclusion 后将该角色检查点推进到实际验过的 SOURCE，同时附 evidence_ref。只改检查点不授予产品资格，不能根据 worker 自报 PASS 推进。
- 权限仅采用 main 的 branch/state/epoch/revision/paths/语义；目标文字变化不会废除旧证据。审计开始固定快照，结束重新核权限和 SOURCE 祖先。分支继续前进允许返回 is_current_head=false，不能拿旧 SOURCE 当新 HEAD PASS。权限变化/历史被移除仍拒绝。
- 旧 G2 检查器和反例保留用于解释历史，不再增加特定父 SHA 的同步例外。旧分支 Governance 若仅因旧 scope 上限/工具同步失败，中央精确 SOURCE PASS 可替代该范围检查；未执行的结构/恢复测试不得因此冒充通过，worker native 资格仍独立。
- 新 worker merge、权限变更仍由 M0 审核，不把普通主线同步泛化成任意写根文件权限。任何新 epoch 必须重新建立范围检查点。

## 11. 控制信息减重

registry 只保留稳定职责、权限与任务入口；cursor 保留本角色当前任务、停止条件、下一步及证据链接。详细 run/hash 放 evidence 一处维护，不在 project/registry/cursor 多次抄写。现有 S→H 不变；一个原子任务尽量一次汇总日志+证据 S、一次 cursor H，不为重复复述结论制造多个文档提交。

写作归属固定：project.next_decision 只写阶段目标/当前入口；registry.assigned_task 是分配依据，goal/done_when 只说明职责和任务入口；cursor.current_task 写当前工作，why_now 写实际缺口，done_when 写本次停止条件，next_action 写一个动作，partial_summary 只补未完成/未验边界。证据中已存在的 run/完整 SHA/统计数字不要抄到多个 prose 字段，正式 checkpoint_sha/last_tested_source 字段仍保留。建议 cursor 约 2–3KiB，8KiB 仍为既有硬上限，不因建议值新增误报门。证据换源码时更新 evidence_refs，历史不同 SOURCE 放 context_refs，不混成同源 PASS。

M0 集中处理共享接口、依赖和真实路径集成。普通模块内测试新增无需申请精确计数修改；必跑用例与特殊 ignore 清单变更仍须解释。达到 done_when 即收口，不因治理升级顺便扩大功能范围。

每轮集成明确一个真实路径目标；当前优先真实 Go 认证会话到 Rust owner，保留 B01–B04、无 HOL、所有权/generation/MTU 等硬门。整理历史时把已完成、仍 OPEN、被替代结论分清；不删除原始失败。

## 12. 日常检查与工具自测分层

普通 push 的 Governance 每次仍核角色/来源、权限范围、请求身份、仓库结构、证据引用；连续性交接另报。其 receipt scope 为 `governance_identity_and_structure`，drills/model 明确 NOT_RUN，不冒充全工具测试或产品资格。worker 的历史 scope 检查器兼容与中央精确 SOURCE 审计仍按第 10 节处理，不静默绕过失败。

完整工具回归、工作流语法和模型计算由 `governance-maintenance.yml` 在 tools/tests/workflow/policy/必跑清单/检查点或共同规则变化时运行。仅 project、registry、cursor、请求或证据数据变化不重复启动完整自测，但普通 Governance 的数据验证仍执行。显式手动 `governance-selftest` 保持完整 drills/model，缺失或失败不能生成 PASS。遇规则改动必须验 maintenance 的同源结论，不能只拿轻检查绿灯合入；无关功能/性能测试不为治理文字重跑。
