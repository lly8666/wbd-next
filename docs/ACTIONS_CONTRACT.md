# Actions 契约

当前唯一可执行流程是 `.github/workflows/governance.yml`，scope 为 `governance`。没有产品构建或性能夹具，任何产品 PASS 都属于错误声明。

## 请求

未来手动产品测量前，worker 在自己的 `requests/<request_id>.json` 推 intent：

`schema_version, request_id, role_id, task_id, assignment_epoch, reservation_revision, kind, source_sha, harness_sha, config_sha256, scenario, seed, workflow, dispatch_ref, measurement_jobs, samples, status, supersedes_request`

source/harness 必须完整 40 位 SHA，config 是实际最终生效配置的 SHA-256。performance 的 measurement_jobs 和 samples 均为 1。数组场景与 multi-leg 不允许；一次同配置预声明损伤波形可以。

status 为 PLANNED/DISPATCHED/RECORDED；没有读取 manifest 前不可 RECORDED。结果记录到 `docs/evidence/<role>/` 并在 cursor 引用。字段规范由工具校验，不允许使用 latest/HEAD 等浮动字符串替代来源。

## 准确识别 run

run-name 以 `role|request_id|` 开头，后面给人读的 scenario/source 缩写。正式身份以 run ID、attempt 和产物为准。同请求多个 run 标 DUPLICATE，找不全历史标 UNKNOWN；都不能默认为可再次触发。

Governance 手动验证 input `declared_source` 必须等于实际 checkout SHA。自动 push run 的请求号用 `event-<run_id>`；目前不启用 pull_request 事件，避免把 merge commit 与分支头混用。

**消除自引用：**先完成被测 S，把只读测试分支/标签 `qualification/<request_id>` 固定指向 S；随后在角色工作分支提交请求 I，文件名为 `<request_id>.json`，声明 source/harness=S。dispatch 使用 qualification ref，并传 `request_ref=I`、`declared_source=S`。请求所在 I 与被测 S 不必相同。workflow 从 I 读取请求、从 S 执行检查，并核 I 在当前角色工作分支上、实时分配未过期；不得要求请求文件填写包含它自己的提交 SHA。

当前 governance 的 source 与 harness 相同。未来产品夹具可以不同，但必须核验两个实际 checkout，并记录精确来源。跨 qualification ref 找同 request 的 run，不能只查 worker 分支。API 查询超过有界范围时需分页或人工缩小完整范围，不能声称未找到即未执行。

## 产物

每轮输出小的 receipt.json + manifest.json + 检查日志，失败也尽量上传。receipt.result 只是步骤观察，仍须核 GitHub 最终 conclusion；CANCELLED 或硬终止可能没有产物。

manifest 包含实际 SOURCE、workflow ref、run ID/attempt、平台与产物各文件 hash。**hash 证明一致性，不证明业务正确性。** artifact 过期时保留摘要和可用性状态，不声称凭 hash 能复验。

## 能力限制

只有 GitHub 读写能力的聊天可直接读 workflow/run/artifact 接续；不能下载产物时保留 NEEDS_ARTIFACT_REVIEW，不把 job 绿灯转换成业务 PASS。没有 dispatch 权限时记录具体缺口，由有权限的集成流程接手。

## 阈值修改

实现和验收允许带不得暗中同时改。需要修正模型或夹具时记录旧结论、新证据和受影响资格，之后使用新请求与精确 helper SHA 验证。文档更正不触发无关性能重跑。
