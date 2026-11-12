# PLAN029 H1693｜收回 H1692 新入口无 WFP 纯测试成功，系统起网仍硬拒绝

- [SOURCE `9b64ef8055c9416c1c32d192e8db4caf41d660fa` 的 Windows 原 Go H1661 Action 43248552998](https://github.com/lly8666/wbd-next/actions/runs/43248552998) **SUCCESS**；[artifact 13957622378](https://github.com/lly8666/wbd-next/actions/runs/43248552998/artifacts/13957622378) ZIP sha256 `9b0547e0f592ccd8c65e7f7c00635ebe637545e654b1df57e111f4320c26f868`。严格 manifest/overlay 同SOURCE，通过编译，并实际运行 `TestPlan029NoWFPV2LiveReceiptChecksFourStagesAndPreservesHardGate` 及 `TestPlan029NoWFPControllerUsesFourOwnedStagesWithoutLegacyGuard` **PASS**。这两项均为 pure mocked stage/owner 测试，不涉及签名 Wintun 网络/系统 Applied。
- [Governance 43248553518](https://github.com/lly8666/wbd-next/actions/runs/43248553518) Governance/Feature catalog 均 SUCCESS。M0-WIN-LINUX [43248553062](https://github.com/lly8666/wbd-next/actions/runs/43248553062) Cheap、Windows Go、Windows Rust、Linux Rust source jobs 成功，其余任务于收据时在途；M0|PLAN020-WIN-WAL [43248552878](https://github.com/lly8666/wbd-next/actions/runs/43248552878) 仍在途；无手动重派且不以 in-flight 宣称完整绿色。
- H1692 新会话调用 `n4AssembleWindowsNoWFPNativeTxn`、`assemblyOnly` 检查发生在 Wintun ring claim 前，**不会走旧持久 WFP Arm 或把 no-op guard 当 Applied**；四阶段 v2 Stop 通过 schema-specific `Recover`，legacy v1 私有精确-owned 回收保持独立。读只预检移除了过时的 WFP layer 依赖、保留旧输出字段 false。
- H1690 **真实签名 Wintun 注入 UDP、TCP SYNACK 均失败** 与 H1686 GUI DLL FAIL 均不改写。059.. GUI/配置和这次 source Build/unit PASS 不能替代业务双出口、系统 DNS 实测、Direct TCP 能力门、FakeIP、 padding 或 D1–D5/P1–P2。029 仍 `IN_PROGRESS`，不得关闭或启动 030。

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Actual current-source Windows Go manifest and no-old-WFP v2 controller/receipt pure tests PASS, scope-limited; signed OS Apply/Stop and Direct remain NOT_RUN."}
```
