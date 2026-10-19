# PLAN-009 §5：已发布的 M1/M3 公共测试入口（M0-025 短前置）

2026-10-19，M0 独立验证源锁定。此页记录**已存在**的入口，不是 PLAN-009 PR #12 的实现承诺。M1/M3 负责在自己的分支按当前任务发布请求、触发和验收；M0 不代提交工位 cursor、不代测模块成本。工位不必再次申请修改共享 workflow。

## 冻结控制身份与验收边界

- 仓库：`lly8666/wbd-next`，公共 workflow：`.github/workflows/worker-component-validation.yml`。
- **唯一当前推荐调度 ref**：`qualification/worker-ci-v3`；精确 commit：`3f87d3ec9c06f7362c95c301437116d53be14c4f`。旧 `qualification/worker-ci-v1` `fd8296e81ba2c89a8779813d0072c58fd92266c7` 和 v2 `4307a39a661b6a0b227cdcc117f16010779de00f` 不移动、不混用。
- CI 入口回归：Action [39197303106](https://github.com/lly8666/wbd-next/actions/runs/39197303106) attempt1 contract-smoke PASS；[39197303104](https://github.com/lly8666/wbd-next/actions/runs/39197303104) maintenance PASS；[39197303044](https://github.com/lly8666/wbd-next/actions/runs/39197303044) Governance PASS。三者 HEAD **均为 v3 原 SHA**。各项的 provider artifact SHA256 在本轮证据 JSON。
- 功能交付范围：`Linux/x86_64`；M1 `wbd-engine` 默认 Release，**分别构建** frozen baseline / candidate 两个相同 fixture；M3 `wbd-codec` `native-isal` Release + 固定 ISA-L `c387163fcbca62701d646149564c550c78a4f985`，一个测试二进制内含已冻结 old snapshot 和 candidate。同一 control `Cargo.lock`/wrapper/target/features；manifest 对其身份负责，**不是原始完整工位树构建**。
- 中央请求和 receipt 校验新增 `paired_abba`：ABBA/BAAB 四 leg 的 A/B 同 SOURCE 和 manifest、同 job、同工况、不重叠与残缺负例；原本 `paired_ab` 两腿规则保持不变。
- M3 **当前现成** `fec2_plan008_abba.rs` 只输出每 leg CPU ticks/wall 和顺序，不输出绝对单调 start/end；公共入口如实产出 `INCONCLUSIVE`（`absolute_window=NOT_INSTRUMENTED`），**不准冒充经过正式四 leg 区间校验的 PASS**。若 M3 想升级为完整 ABBA PASS，须在自己的允许路径内补足绝对 per-leg 时间戳、保留真正 NativeIsaL / 匹配总工作量，然后新 SOURCE/新请求重新驗證。M0 不代改 fixture。
- 至此 **实际公共入口 static/contract PASS；M1 和 M3 的真实 prepare 和 paired Actions：尚未由此收据触发/验收（NOT_RUN）**。优化收益、Windows/ARM、两物理端、产品 D10/p99 均无资格，产品 FEC2 仍 OFF。

## M1 Game015：最小独立 prepare 请求示例

在**已经 checkout 对应 worker 分支** `work/m1-r1-runtime` 的本地 Git 仓库执行。请先确保 S（源码及 fixture）已在远端 worker 分支上、工作树干净；不要更改共享控制代码：

```bash
set -euo pipefail
ROLE=M1
TASK=R5-M1-PLAN008-GAME-DEDUP-015
REQUEST_ID=M1-GAME015-PREPARE-001
CONTROL_REF=qualification/worker-ci-v3
CONTROL_SHA=3f87d3ec9c06f7362c95c301437116d53be14c4f
BASELINE=c80ff6a52ee58860f7c108307fe25d74438703e2
CANDIDATE=64102db5e101df1f678e17919169927ad19bad06
HARNESS=d512f932ef1b3a4ad50b680211cde2ec8c133021
FIXTURE=crates/wbd-engine/tests/m1_game015_same_vm_cost.rs
CONFIG_SHA=$(git show "$HARNESS:$FIXTURE" | sha256sum | awk '{print $1}')
REQUEST=.governance/workstreams/M1/requests/$REQUEST_ID.json
mkdir -p "$(dirname "$REQUEST")"
jq -n --arg id "$REQUEST_ID" --arg task "$TASK" --arg s "$CANDIDATE" --arg h "$HARNESS"   --arg old "$BASELINE" --arg fixture "$FIXTURE" --arg digest "$CONFIG_SHA"   --arg cref "$CONTROL_REF" --arg csha "$CONTROL_SHA"   '{schema_version:1,request_id:$id,role_id:"M1",task_id:$task,
    assignment_epoch:1,reservation_revision:2,kind:"functional",
    source_sha:$s,harness_sha:$h,baseline_sha:$old,config_path:$fixture,
    config_sha256:$digest,scenario:"game015-receive",seed:631,
    workflow:".github/workflows/worker-component-validation.yml",
    dispatch_ref:$cref,control_sha:$csha,measurement_jobs:1,samples:1,
    status:"PLANNED",supersedes_request:null}' > "$REQUEST"
git add "$REQUEST"
git commit -m "M1 I: exact Game015 public prepare intent $REQUEST_ID"
git push origin work/m1-r1-runtime
I=$(git rev-parse HEAD)
gh workflow run worker-component-validation.yml --ref "$CONTROL_REF"   -f role_id="$ROLE" -f stage=prepare -f request_id="$REQUEST_ID" -f request_ref="$I"
```

M1 可用后续修复过的 candidate/harness **精确** SHA 替换示例中的历史 S；不要假设上面的历史 133 项功能通过即证明新代码/fixture 的任何增量。prepare 只产工件、实际函数断言和 hash，**不报告性能收益**。

## M3 FEC2-018：最小独立 prepare 请求示例

只替换上例的角色、任务、源码与固定 fixture；发布单独的 `M3-FEC2-018-PREPARE-001` intent I：

```bash
ROLE=M3
TASK=R5-M3-PLAN008-FEC2-RECOVERY-WORKSPACE-018
REQUEST_ID=M3-FEC2-018-PREPARE-001
BASELINE=8cc5b06d6832565a80b60402a5fe2e1078e9ab2e
CANDIDATE=437cc721d1009c835cb900384dadbdbf3ebea800
HARNESS=705acbf3b25569761a35d5937e14725bcc2dc149
FIXTURE=crates/wbd-codec/tests/fec2_plan008_abba.rs
# CONTROL_REF, CONTROL_SHA 与 M1 完全相同；不能将 M3 HEAD 当 control。
# 使用上例的 jq 请求结构，但设置 role_id="M3"、
# scenario="fec2-018-native-e4"、M3 task、config_sha256=fixture bytes 的真实 hash。
# M3 需要在 prepare 日志中亲验 cfg
# r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact：
# native-isal 必须实际调用 ISA-L，缺库/旧旧快照不符/回退 scalar 为 FAIL。
```

## 派生 paired 请求（两工位同一方法，一次 Action 仅一个 scenario）

1. 等待准备 job **实际 completed/success**，从 GitHub Actions run 中获取唯一 `PREPARE_RUN_ID` 和 `PREPARE_RUN_ATTEMPT`（不取 latest），再查询该次 `worker-prepare-<run>-<attempt>` 的 **真实 artifact ID**。
2. 下载对应工件，校验 `prepare-manifest.json` 字节的 `sha256sum`；选择确切 `control_sha`、source、harness、platform/features、Cargo.lock/native library/binary SHA。严禁提前编造 manifest hash。
3. 在各自原 worker 分支另提交独立 `kind:"performance"` 请求 I2：相同 `role_id/task_id/epoch/revision/source_sha/harness_sha/baseline_sha/config_path/config_sha256/scenario/seed/workflow/dispatch_ref/control_sha`；外加 `prepare_run_id`、`prepare_run_attempt`、`prepare_artifact_id`、`prepare_manifest_sha256`。M1：`mode:"paired_ab",samples:2,legs:[A,B]`；M3：`mode:"paired_abba",samples:4,legs:[A,B,B,A]`。各 leg 含 `{label,source_sha,build_manifest_sha256}`，source A=baseline、B=candidate，所有 manifest hash 相同（单次 prepare 固定产物）。
4. `git push` 请求 I2 后，`gh workflow run worker-component-validation.yml --ref qualification/worker-ci-v3 -f role_id=M1 -f stage=paired -f request_id=<I2请求ID> -f request_ref=<I2完整commit_SHA>`（M3 修改 role_id 即可）。**一个 paired job，同一 VM 顺序消费已经校验的二进制；测量 job 内不编译、下载或安装**（下载在计时窗口之前）。
5. 按 run ID + attempt + GitHub job + artifact + 二进制 hash 和日志核结果。失败或原生容量不够，保留 FAIL/INCONCLUSIVE。工位更新自己的 evidence、请求和 H，M0 不改 worker cursor；新源码重新 prepare，新 performance I2 必须显式引用新工件。不可把单独 Release build 或相邻旧 SOURCE 的 PASS 移植为当前收益。

获取准确 build manifest 的示例（在 `PREPARE_RUN_ID`、`PREPARE_ATTEMPT` 均为实际 Action 数字后）：

```bash
gh api "repos/lly8666/wbd-next/actions/runs/$PREPARE_RUN_ID/artifacts?per_page=100"   --jq '.artifacts[] | select(.name == "worker-prepare-" + (env.PREPARE_RUN_ID) + "-" + (env.PREPARE_ATTEMPT)) | {id,name,digest,expired}'
gh run download "$PREPARE_RUN_ID" -R lly8666/wbd-next   -n "worker-prepare-$PREPARE_RUN_ID-$PREPARE_ATTEMPT" --dir "./prepared-$PREPARE_RUN_ID"
sha256sum "./prepared-$PREPARE_RUN_ID/prepare-manifest.json"
```

**状态边界**：这是 workflow + adapter + negative unit-test 的“公共入口已发布”收据，不是新模块性能 PASS。实际权限阻塞需区分 GitHub dispatch 403/认证/配额和 worker 内容范围；勿因此开放 worker 对 `.github/` 或 `tools/` 的写权限。
