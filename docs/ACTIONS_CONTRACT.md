# Actions 契约

当前已有治理、组件构建/功能回归和专项性能夹具。能力按当前 workflow、精确源码证据和 `r0/qualification-manifest.json` 判断；任何组件 PASS 均不自动升级为产品 PASS。产品测试方案见 `docs/architecture/TEST_PLAN.md`。

## 请求

未来手动产品测量前，worker 在自己的 `requests/<request_id>.json` 推 intent：

`schema_version, request_id, role_id, task_id, assignment_epoch, reservation_revision, kind, source_sha, harness_sha, config_sha256, scenario, seed, workflow, dispatch_ref, measurement_jobs, samples, status, supersedes_request`

source/harness 必须完整40位SHA，config为实际最终生效配置的SHA-256。performance固定一个scenario/seed和一个measurement_job；默认`mode=single,samples=1`。**2026-10-14用户覆盖旧multi-leg禁令：新旧性能比较使用`mode=paired_ab,samples=2`，同一个job/VM顺序AB或BA，不同job不算同机。** 一次同配置预声明损伤波形可以，不允许矩阵装进一个性能实验。

paired请求增加有序`legs`两项，每项`label(A或B),source_sha,build_manifest_sha256`，A为父/旧基线、B为候选；顶层source_sha为B。构建产物提前生成可复用，每leg验证实际hash。共享config/scenario/seed/harness，不能两leg悄悄变工况。receipt逐leg记录上述字段及`job_id,start_monotonic_ns,end_monotonic_ns,result`；核GitHub jobs API实际run/attempt/job，时间不能重叠，失败/未跑不得聚成PASS。缺结果保留原失败且标缺失，不伪造leg。所有构建身份和运行日志仍须人工/夹具交叉核验，JSON一致不是来源证明。

status 为 PLANNED/DISPATCHED/RECORDED；没有读取 manifest 前不可 RECORDED。结果记录到 `docs/evidence/<role>/` 并在 cursor 引用。字段规范由工具校验，不允许使用 latest/HEAD 等浮动字符串替代来源。

## 准确识别 run

run-name 以 `role|request_id|` 开头，后面给人读的 scenario/source 缩写。正式身份以 run ID、attempt 和产物为准。同请求多个 run 标 DUPLICATE，找不全历史标 UNKNOWN；都不能默认为可再次触发。

Governance 手动验证 input `declared_source` 必须等于实际 checkout SHA。自动 push run 的请求号用 `event-<run_id>`；目前不启用 pull_request 事件，避免把 merge commit 与分支头混用。

**消除自引用：**先完成被测 S，把只读测试分支/标签 `qualification/<request_id>` 固定指向 S；随后在角色工作分支提交请求 I，文件名为 `<request_id>.json`，声明 source/harness=S。dispatch 使用 qualification ref，并传 `request_ref=I`、`declared_source=S`。请求所在 I 与被测 S 不必相同。workflow 从 I 读取请求、从 S 执行检查，并核 I 在当前角色工作分支上、实时分配未过期；不得要求请求文件填写包含它自己的提交 SHA。

当前 governance 的 source 与 harness 相同。未来产品夹具可以不同，但必须核验两个实际 checkout，并记录精确来源。跨 qualification ref 找同 request 的 run，不能只查 worker 分支。API 查询超过有界范围时需分页或人工缩小完整范围，不能声称未找到即未执行。

## 产物

每轮输出小的 receipt.json + manifest.json + 检查日志，失败也尽量上传。receipt.result 只是步骤观察，仍须核 GitHub 最终 conclusion；CANCELLED 或硬终止可能没有产物。

普通 push Governance 使用 `scenario=governance-push-checks` / `scope=governance_identity_and_structure`，每次执行角色/来源/权限/结构校验，完整工具 drills/model 标 NOT_RUN；receipt 内 checks 明列各步骤观察。手动请求仍使用 `governance-selftest`，必须实际完成完整 drills/model。相关工具/规则变更的自动全回归归 maintenance，不因进度 H 再跑一遍。轻检查通过不能替代规则改动的 maintenance 通过。

manifest 包含实际 SOURCE、workflow ref、run ID/attempt、平台与产物各文件 hash。**hash 证明一致性，不证明业务正确性。** artifact 过期时保留摘要和可用性状态，不声称凭 hash 能复验。

## 能力限制

共享workflow维护归M0，已分配工作包的调用/结果验收/修复归worker，不逐次审批。工位公共入口按[PLAN-009](decisions/M0-worker-selftest-entry-2026-10-19.md)实施：prepare先输出真实manifest/hash，paired再引用产物，避免请求预填尚不存在的build hash。固定control ref与candidate/harness/request SOURCE分别记账，不沿用Governance的source=harness假设。此为实施方案，入口未发布前不得宣称已可用。

现有校验器仍只接受single/paired_ab。PLAN-009允许M0实现有界paired_abba扩展并补正反例后使用；在此之前4腿不得冒充2腿请求通过。历史ABBA收据原样保留，不由文档更新自动获得新资格。

只有 GitHub 读写能力的聊天可直接读 workflow/run/artifact 接续；不能下载产物时保留 NEEDS_ARTIFACT_REVIEW，不把 job 绿灯转换成业务 PASS。没有 dispatch 权限时记录具体缺口，由有权限的集成流程接手。

## 阈值修改

实现和验收允许带不得暗中同时改。需要修正模型或夹具时记录旧结论、新证据和受影响资格，之后使用新请求与精确 helper SHA 验证。文档更正不触发无关性能重跑。

## 2026-10-15 功能 CI 合并

`native-regression.yml` 接替九个重复的 R1/R2 native workflow：按依赖选组，一次 Release 构建，八个功能组复用有 SOURCE/平台/工具链/选项/依赖/二进制 hash 的产物。组与历史 workflow 映射及必跑 ID 在 `.governance/native-suites.json`。消费者只认可同 run/attempt 的构建，不取 latest；缺用例、非零退出、意外 ignore、残缺日志必须失败。新增用例不因总数变化失败。关键 ID 删改需要独立说明。此矩阵仅为功能测试，不是性能实验。

旧新性能仍一场景、同 job/VM 顺序 AB/BA。不要以八组功能 CI 作为性能矩阵的先例。跨目标平台不共用二进制，跨源码不继承 PASS。旧结果保留原 workflow/run 身份。

## PLAN-009 已发布公共工位执行入口（2026-10-19）

workflow `.github/workflows/worker-component-validation.yml`，M0 固定 `qualification/worker-ci-v5` → `484861e5aff4eb9098a25a42f1522e19716f09e8`。M1/M3 的 `source_sha`、`harness_sha`、`baseline_sha`、`request_ref` 与公共 `control_sha` 必须分别精确锁定。提交各自分支请求 I 后，执行 `gh workflow run worker-component-validation.yml --ref qualification/worker-ci-v5 -f role_id=M1 -f stage=prepare -f request_id=<请求ID> -f request_ref=<完整40位I_SHA>`（M3 角色替换）；再以新的性能请求 I2 的 `stage=paired` 消费已验证的 `prepare_run_id/prepare_artifact_id/prepare_manifest_sha256`。**真实完整示例、M3 native 注意事项、ABBA 范围和 hash 复验**见 [v5 操作手册](devlog/M0/PLAN-009-worker-ci-v5-runbook-20261019.md)。入口静态合同通过，不代表 worker 实际 prepare/paired 或产品性能已通过；旧 v1-v4 不移，生产 FEC2 OFF。
