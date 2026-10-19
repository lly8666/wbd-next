# PLAN-009 §5：主线中央 G2 → M1/M3 自助自动派发（v6）

M0 在 2026-10-19 发布。该流程不打开 worker 的 `.github/workflows`、共享 tools 或额外 token 权限；已有 worker requests 仍由原 worker 所有，不碰 cursor。参见 [Issue #14](https://github.com/lly8666/wbd-next/issues/14) 给 M1/M3 的精确迁移及 paired 指令。

## 实际闭环

1. Worker 只需在注册分支及授权路径 `.governance/workstreams/M1|M3/requests/*.json` 提交唯一 `PLANNED` JSON。已有 worker Governance push 触发中央 `scope-audit.yml`。
2. M0 单一工作流 `.github/workflows/worker-request-dispatch.yml` 由中央成功 `workflow_run` 自动触发；首次安装也会用 main push 自发补捞当前 HEAD，不要求手工点击。
3. 源锁为当前 worker 分支 exact HEAD + 中央 G2 完整原始 `scope-M1|M3.json` 工件，其 run ID、attempt、中央认证结果、权限/epoch/revision 与 HEAD 匹配；主线只读取，未 checkout 或执行 worker 自有脚本。旧审计起终期间 `main` 更新允许发生，但 role authority 不能更改。
4. 对每笔待派发请求从 GitHub commit path 精确定位最近改动的不可变 `I`，校验 request 文件与 HEAD 字节相同。使用现有 v6 `validate_context` 验证身份、task/epoch/revision/路径、fixture bytes SHA256、source/baseline/harness reachability、mode/samples及原始 `control_sha`。
5. 检查 **全部可查询** 的 v6 `workflow_dispatch` run-name 唯一键 `role|request_id|stage|control_sha`。发现既往任何运行（PASS/FAIL/in_progress）即跳过，不自动重复失败；首次才由 main job 的 `GITHUB_TOKEN` (`actions:write`，不暴露给 worker) `POST /actions/workflows/worker-component-validation.yml/dispatches`。执行前复核 worker HEAD/ref 未移动。
6. v6 `authorize` 还会独立再验一次同样的 I/ref/source，随后 `prepare` 先功能测试、按同一 Cargo.lock/ISA-L pin 构建并产 manifest。**paired 只接收新一笔 `kind=performance` 请求**：固定原 prepare run+attempt+artifact ID 与 manifest 原始字节 SHA256；M1 same-job old/new AB，M3 native ABBA（目前缺 per-leg 单调时间仍 INCONCLUSIVE）。未收到真实 prepare 成功工件绝不启动 paired。

## v5 旧流程及正式 v6 发布

- M0 真正首次成功触发 Action [39204817044](https://github.com/lly8666/wbd-next/actions/runs/39204817044) SUCCESS、artifact `12164389604`；其固定 M1 I=`26c9c57f090ebc1e97b74d359527caad4614f667`、M3 I=`857ac9c232383435ead4b9d02ef4eebdebc11cda`，分别派发原 v5 prepare [39204910923](https://github.com/lly8666/wbd-next/actions/runs/39204910923) 和 [39204914148](https://github.com/lly8666/wbd-next/actions/runs/39204914148)。
- **两次旧 v5 prepare 都未越过 `authorize`**：workflow 向 argparse 传 `--stage prepare`，旧固定 v5 Python 未接收参数。两次为 `AUTHORIZE_ARGUMENT_FAILURE`，无 Rust compile/native/paired 收据。旧 `qualification/worker-ci-v5` → `484861e5aff4eb9098a25a42f1522e19716f09e8` 永不修改，两个旧 request ID 不重复派发。
- 正式前向版本 `qualification/worker-ci-v6` → `fab2e1d7cbe12109ef9215c6caf358946ead522b`，现已从同一代码 SOURCE 完成 [contract-smoke 39205218653](https://github.com/lly8666/wbd-next/actions/runs/39205218653)、[maintenance 39205218741](https://github.com/lly8666/wbd-next/actions/runs/39205218741)、[Governance 39205218683](https://github.com/lly8666/wbd-next/actions/runs/39205218683) **3/3 PASS**。修复了 `--stage` 的必填枚举与正/反例，所有 worker 签名仍核精确 control_sha。
- M0 自动派发新版主线 SOURCE `05af40990b5d7c3095ee95f3637a968e1620ae7b`，[dispatcher 39205332501](https://github.com/lly8666/wbd-next/actions/runs/39205332501) **PASS**，工件 `12165945047` 正确返回 `decisions:[]`：旧请求仍锁 v5，新 v6 请求尚未由 worker 发布；不存在“迁移后已经跑性能”的说法。
- 两 worker 下一动作及唯一字段见 Issue #14；`M1-GAME015-AB-PREP-003` 与 `M3-018-NATIVE-E4-PREPARE-002` 必须由各自 worker 在独占请求路径新建，**M0 不代写**。发布后会自动触发，后续每个新请求无需另外批准、点击或个人 token。

## 边界

本轮 **AUTO_DISPATCH_RUNNING_PASS**；v6 M1/M3 **实际 prepare NOT_RUN / paired NOT_RUN / performance NOT_RUN**。M0-025 产品集成仍 partial/unverified，生产 FEC2 OFF。旧 M3 fixture ABBA 没有每腿绝对单调边界，不能当作正式 ABBA PASS。
