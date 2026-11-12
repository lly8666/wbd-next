# PLAN029 H1691｜修复 no-WFP v2 独立 OS receipt 的 v1 顺序硬编码

- 当前 `N4NativeUnifiedTxn` 已有独立 v2 `lease→mtu→dns→routes` WAL，但 `VerifyLiveOSApplied` 仍拿 v1 固定 `guard→lease→mtu→dns→routes` 比较。即使四个真实阶段未来全部 owned，其首个 lease 也会错判为 guard。此为确定的源码缺陷，不应以 WFP no-op guard 掩盖。
- 最小修改：从已校验的 `j.Schema` 调用现有 `n4UnifiedOrderForSchema`，验证精确阶段数并按对应顺序核对；v1 五阶段保持旧契约；v2 无第五 guard、`GuardOwned=false`、其他 OS stage 必须独立 Inspect Owned。
- 新 `TestPlan029NoWFPV2LiveReceiptChecksFourStagesAndPreservesHardGate` 用软件 owner/stage fixtures 检查 v2 真实 schema顺序、缺失或 foreign DNS 不能伪造 Applied、`assemblyOnly` 拒绝、四阶段逆序 Recover 与 Disconnected。**这不是签名 Windows Wintun 系统 Apply/Stop 的功能验收**，不解除 v2 assembler `assemblyOnly=true`。
- 先等一次已有自动 CI 的 Windows Go 编译与纯测试结果，记录真实 SOURCE；不在每个 helper 后启动同一网络场景。H1690 注入 UDP 与 TCP 的 signed kernel 失败继续为 FAIL，029 持续 IN_PROGRESS。

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Repair v2 no-WFP four-stage receipt name matching which still checked fixed legacy v1 guard-first array; preserve hard product/OS readiness gate."}
```
