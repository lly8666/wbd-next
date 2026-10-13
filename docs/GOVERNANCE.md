# 开发治理协议 v1

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

G1 在授权范围内自主执行。G2 接口/职责调整由 M0 合并影响与回归，避免两位作者各改一套语义。G3 才涉及改变用户原则/范围/未授权影响；已有用户授权不能被治理文件重复变成审批要求。

## 3. 一个控制面，多条工作线，一条集成通道

main 的 registry 是权限依据；worker 分支不能通过修改自己的 registry 扩权。worker 的 cursor 是当前工作事实，不是 main 上那份旧副本。

M0 登记 active role 的 branch、epoch、revision、写入前缀、语义归属、goal、done_when；工作分支从明确基线创建。不同 active worker 的写入范围不能重叠。共享接口、根依赖、CI、章程、全局目录交 M0 串行集成。

每个分支只有一位活动写入者。普通全新聊天接续同一已释放角色不增加 epoch；发生撤销或重新分配时由 M0 增加 epoch，必要时换 producer 分支。不要仅凭多久没提交就断言另一聊天死亡。

操作前刷新精确 ref；采用 fast-forward/expected-parent 写入，拒绝 force push。GitHub Connect 多文件提交优先创建一个 tree/commit；若只能逐文件操作，保持 WIP，最终 H 前逐提交核对。推送冲突必须重新核对，不能静默覆盖。

epoch/检查器是工程约束，不是恶意同账号写入者的安全隔离。仓库权限和 required checks 是另一层；分支保护实际是否启用必须单独记事实。

## 4. S → H 与中断恢复

S：代码、文档、请求、结果等实质工作提交。H：单独一次只更新本角色 cursor 的提交。

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

性能：一个 Action 一条测量，禁止 matrix、同 runner 顺序 AB、多配置腿或隐含第二负载。预声明的同配置损伤波形允许。不同模块独立 Actions 可并行。功能/unit 多 job 不等于性能资格。

run-name 供人路由，manifest 和 GitHub API 才用于核验。正常分支 CI 使用 event + SHA + run_id 的身份；手动请求将 request_id 放入 run-name。禁止只凭“最近绿色”认领结果。

正式测量不因普通 push 自动取消；concurrency 分组包含 workflow/role/request，不能全仓共用取消组。当前只启用 governance workflow，未配置任何产品性能夹具。

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
