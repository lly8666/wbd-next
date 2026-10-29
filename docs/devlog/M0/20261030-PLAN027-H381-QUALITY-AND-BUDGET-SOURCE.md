# PLAN027 H381｜低频窗口质量合约与外层额度上限
2026-10-30，恢复 HEAD764ee4bef59d、M0 cursor H380 与自动 Actions。未启动任何新矩阵，旧 SOURCE009d/302d 证据不升级为本源码 PASS。

- 低频质量：新增 `crates/wbd-recovery/src/quality_window.rs`，v2 36B bounded Quality 控制体，1024 PN 窗口；lane/epoch/direction/window-id/范围匹配，明确 definite-first-send、unique、repaired 上下界。未成熟/缺失/过期/容量/未覆盖均 UNKNOWN，拒绝重复错格式，不产生逐 record bitmap；3 个纯源回归列入 required。
- 机会重传：v3 额度 hard cap 从 9%F 改为 `R<=0.10F`，平滑发放仍为 9%F/s 以避免抖动，32KiB sparse 及全局绝对上限不变；新增 1 项纯源回归，区分 F、R 和假设 C 的真实总量分母。
- 自动 Actions 40926882272 的 recovery 测试组 PASS，codec 组由于忽略的性能诊断/exit124 FAIL。旧 Windows WAL40915929426 Game2 Stop rc5/8m timeout 仍 OPEN；没有篡改 FAIL。
- 本提交尚未连接 Windows/Linux 生产层，不说明 M2 Receipt 线上已移除或 Auto 正式生效。接下来先完成双向生产接线/参数/功能卡再冻结 SOURCE 跑 A，继而 B、C、必要修复回归交付。物理 NOT_RUN。

```feature-impact
{"kind":"update","ids":["fec-auto","outer-opportunistic-repair"],"reason":"Add source-only PLAN027 low-rate Quality wire/sample bounds and change v3 exact local F repair ceiling to 10%, with required native regressions; live production verification remains NOT_RUN."}
```
