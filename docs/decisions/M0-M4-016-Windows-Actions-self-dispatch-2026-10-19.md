# PLAN-010 M4-016：固定控制、真实Windows Actions自主请求示例

**权威**：用户合并[PR #15](https://github.com/lly8666/wbd-next/pull/15)的PLAN-010之后，main `.governance/registry.json`登记M4 `R5-M4-NATIVE-WINDOWS-NETWORK-016`（原writer branch `work/m4-r1-platform`、epoch=1、revision=2不变）及唯一新增 `r0/go_overlay/internal/windowsclient/`。本文件不是worker cursor，不替worker创建请求或认定已开始。旧M4-015的中途worker Governance FAIL与原Go CLI/GUI Linux/ARM/Windows原生[39225427878](https://github.com/lly8666/wbd-next/actions/runs/39225427878)独立成功须分别结算，不重测已成功矩阵，不冒充016。

## 已生效的测试入口与作用域

**现有workflow** [`.github/workflows/m0-m4-product-assembly.yml`](../../.github/workflows/m0-m4-product-assembly.yml)，不是M1/M3的冻结v7运行器。M0冻结控制分支 **`qualification/m4-product-windows-v1`** HEAD **`17263ad85a41639a569af914b4157520daf84ecb`**。场景 `windows-native-product-runtime-016`，target `windows-amd64`，Windows runner `windows-2022`，原Go冷层SHA **`a7a82db31fe736ffedee330795a3234d358f1984`**；本包附加donor SHA **`6ec6b5836c2b70a85f2ef89c2f5ea4525c6ed340`**，按[12文件差异表](../evidence/M0/PLAN-010-windows-native-migration.json)由M4精准导入而非全库升级。原Rust热路径和root source lock不变。

控制权限：M4仅在自身分支创建实际产品代码、清单、夹具、evidence及一次性 `M4-016-*.json` 请求；M0只负责本workflow、[中央调度器](../../tools/worker_request_dispatch.py)、共享Stop接口和最终产品集成。M0不代写M4 cursor。**自动触发方法**：M4写入完整合法请求作为独立单文件commit I，随自身S/H按治理提交；等同分支最新SOURCE取得中央G2 `ROLE_SCOPE_PASS` 后，现有主线唯一授权调度器自动核对I、当前HEAD、scope artifact、config SHA、任务、权限、冻结control和此前重复run，再调用现有M4 workflow固定Windows `workflow_dispatch`。worker只需提交自己有权限的文件，**无需Actions写token或让M0每次代跑**。调度器[Action 39234078787](https://github.com/lly8666/wbd-next/actions/runs/39234078787)自测执行SUCCESS（无真实016 request，故未发布产品PASS）。

**示例请求**：M4先完成015准确结算，在授权路径实现/提交待测代码，记录该次代码提交完整SHA为 `<SOURCE>`；在该SOURCE上固定 `r0/go_overlay/assembly/manifest.json` 的**原始字节**SHA-256为 `<CONFIG_SHA256>`，不得复制本文件里的占位符。然后在M4分支创建 **只包含以下JSON的单文件提交I**，路径 `.governance/workstreams/M4/requests/M4-016-WIN-NATIVE-001.json`：

```json
{
  "schema_version": 1,
  "request_id": "M4-016-WIN-NATIVE-001",
  "role_id": "M4",
  "task_id": "R5-M4-NATIVE-WINDOWS-NETWORK-016",
  "assignment_epoch": 1,
  "reservation_revision": 2,
  "kind": "functional",
  "status": "PLANNED",
  "workflow": ".github/workflows/m0-m4-product-assembly.yml",
  "dispatch_ref": "qualification/m4-product-windows-v1",
  "control_sha": "17263ad85a41639a569af914b4157520daf84ecb",
  "source_sha": "<SOURCE>",
  "harness_sha": "<SOURCE>",
  "baseline_sha": "a7a82db31fe736ffedee330795a3234d358f1984",
  "config_path": "r0/go_overlay/assembly/manifest.json",
  "config_sha256": "<CONFIG_SHA256>",
  "scenario": "windows-native-product-runtime-016",
  "seed": 1,
  "samples": 1,
  "measurement_jobs": 1,
  "target": "windows-amd64"
}
```

创建I后继续由M4提交其cursor H（先S后H）；取得当前M4 HEAD对应的新主线G2 SUCCESS run ID `<G2_RUN_ID>`。不要使用老015的G2 `39225046360` 给新task背书。若之前已经有相同request_id派发，不得重复；失败须用新request_id并关联历史。

**手动兜底，亦为真实可执行示例（提交I/G2后才执行）**：M4可在GitHub Actions的 *Run workflow* 选择 `qualification/m4-product-windows-v1` 并填写六字段；有已连接 `gh` 的环境也可执行下列命令。M4已有中央自动派发成功时**不再手动执行**，因为同一ID第二次会触发重复拒绝。

```bash
gh workflow run m0-m4-product-assembly.yml --repo lly8666/wbd-next \
  --ref qualification/m4-product-windows-v1 \
  -f role_id=M4 \
  -f request_id=M4-016-WIN-NATIVE-001 \
  -f request_ref="<REQUEST_I_40_HEX>" \
  -f worker_source_sha="<SOURCE_40_HEX>" \
  -f control_sha="17263ad85a41639a569af914b4157520daf84ecb" \
  -f scope_run_id="<G2_RUN_ID>"
```

入口fail-closed核：当前M4任务、role/epoch/rev、冻结control SHA/branch、同SOURCE及manifest、仅一个新增request文件的commit I、I在当前G2 HEAD祖先内、当前live main授权与G2完整authority匹配、已有同请求run去重。**权限和触发不是产品资格**。Windows job结果分离原始Go GUI native smoke与实际script-free网络运行：后者、真实Windows 2025/物理/真Wintun-owned WFP和Rust applied ACK除非另有精确SOURCE测试仍为NOT_RUN。正向手动工作请求须由M4首个实际I发起，本次M0不得制造假M4请求来取得绿灯。

## Stop 与连接边界（M0共享契约，M4产品实现）

唯一网络实例：在原始Go Windows客户端的machine-scoped已存租约与锁之下串行native `Prepare/Apply/Recover/Cleanup`，重复启动明确拒绝，GUI只代理同一客户端接口。实际断开次序由M0 Rust桥返回**真Stop完成**才可清理：拒新业务/停止配置更新 → 原Rust RX/TX worker停止并join → M4内核借用/异步发送完成且generation的driver/TUN同步Drain/release → M4原生owned网络Cleanup/回读 → CLI/GUI显示 `disconnected`。错误/取消/中断保留有界独立cleanup context、WAL未完成标记，重启时只Recover owned对象；若Rust Stop失败必须显示partially-stopped及可恢复状态，绝不虚构完成ACK。**本共享次序合同不声称M4/原客户端已调用Rust Stop、或本包网络脚本已移除**；二者是M4功能包加M0后续产品集成的实证缺口。

批量功能验收但不要求多代理仲裁、异常全局第三方并网卡仲裁或极端PnP ghost自愈。构建/Actions内部PowerShell允许，**运行时网络管理不得再调用powershell/pwsh/cmd/netsh/route脚本路径**。保留原WAL单实例、DNS IPv6 bypass/分流和原Parameters catalog，无整库旧源升级或Rust热路径更改。唯一下一动作由M4读当前registry/自身H，结算015并创建016的实际代码+请求；M0继续R0-025认证回执与产品集成。
