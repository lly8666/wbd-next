# PLAN029 H1692｜新会话真实入口不再构造旧 WFP，v2 仍保留硬门

- H1691a 源码 `354f0d156ca263c871a6481675875bed3e6f2311` 的 [Windows H1661 Action 43246996766](https://github.com/lly8666/wbd-next/actions/runs/43246996766) 已实编原 Go 及运行 `-run '^TestPlan029'`，其中新增 `TestPlan029NoWFPV2LiveReceiptChecksFourStagesAndPreservesHardGate` **PASS**；[M0-WIN-LINUX 43246996655](https://github.com/lly8666/wbd-next/actions/runs/43246996655) Cheap/Windows Go/Linux+Windows Rust compile also PASS。严格区分**纯测试**与真实 Win32 网络收发。
- H1692 依用户最新 no-old-WFP 决定，`N4PrepareRealWindowsProduct` 不再构造 `n4WindowsPersistentWFPGuard`、不调用 `n4AssembleWindowsQualifiedFullTxn`，而是在 claim Wintun ring **以前**只装配当前四阶段 `n4AssembleWindowsNoWFPNativeTxn`；当前 `assemblyOnly=true` 明确 fail-closed，不隐藏成无操作 guard / 不返回 Applied。v1 私有恢复代码仍留给**已经存在的精确 owned 旧 WFP 对象**，但新入口不会 Arm。
- 新 v2 controller 将 Connect rollback 和 Stop 选择 `txn.Recover(ctx)`，而不是调用旧 v1 `n4RecoverQualifiedGuardOnlyIntent`。保留 legacy v1 原精确-owned guard intent 修复只用于历史路径。新增纯四阶段 controller 夹具验证无 `apply:guard` / `undo:guard`、guard receipt 为 false、Stop 逆序和 assemblyOnly 硬门。
- `N4ReadOnlyProductPreflight` 去掉 `N4NativeWFPReader.VerifyLayers()` 查询与 `wfp_layer_read_unavailable` 阻断，旧 JSON 字段显式 false 保持向后兼容；新阻断为 `no_wfp_four_stage_and_authenticated_stop_not_qualified`。`N4NativeNetworkReady` 错误改为真实 v2 OS+Rust ingress/Stop 未验证，不再误称旧 WFP 是所需业务路径。对应无 OS 修改的纯测试随源更新。
- 六个 Go overlay `result_blob` 使用实际 Git blob SHA 写入同一版 `manifest-plan020-m0.json`；旧 donor 源码与 legacy 五阶段历史回收不重写。**当前这批仅设计+已写源，真正 Windows CI/系统起网不得先行标 PASS。** H1690 的 signed Wintun UDP/TCP ingress FAIL 保留，D1–D5/P1–P2 未运行。

```feature-impact
{"kind":"updated","ids":["windows-network-wal","gui-config-feedback"],"reason":"Prevent new product sessions from constructing old WFP guard; use no-WFP v2 assembler with assemblyOnly barrier and schema-specific Recover; remove obsolete WFP read blocker from real Windows/GUI readiness preflight, source-manifest-locked."}
```
