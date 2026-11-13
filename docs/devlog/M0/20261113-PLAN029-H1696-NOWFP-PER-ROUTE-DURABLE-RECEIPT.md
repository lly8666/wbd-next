# PLAN029 H1696｜无旧 WFP 的 v2 routes 单独持久归属收据

H1695 [Action 43338614004](https://github.com/lly8666/wbd-next/actions/runs/43338614004) 的签名 Windows A/B/C 已实际通过：A 无 Defender Allow 无 UDP/TCP 内核接入；B 两条精确owned临时Allow使UDP及TCP完整SYN→Accept→DATA→反向DATA→FIN通过；C规则准确删除并恢复不达。此验收**只限本机内核接入**，物理Direct socket/Rust尚未运行。只选 Windows 内核 TCP，不同时开发 smoltcp。

修复 no-WFP `N4NativeUnifiedTxn/v2` 最后 routes Stage 的真实崩溃正确性缺口：旧代码 parent 只写一个批量 `routes:intent`，写入部分后不能分清哪些是确证owned，无法可靠停止/恢复。新增父同安装ID/generation 的 `<wal>.routes` SHA、有界≤9项 `intent→owned` 逐条持久收据。写前持久intent，真实Win32 Create后独立 Lookup exact 再写 owned。清理前完整只读预检，只有确认owned的key才可按CAS逆序删除；**存在但未确认的intent、陌生匹配/外来修改、hash/身份冲突一律保留并拒绝猜删除**。最后一项已从OS消失时 parent 仍需检查并清理尚存child，不能仅凭当前表空跳过。

纯夹具 `TestPlan029NoWFPV2RouteSidecarFullAndPartialOwnedRecovery` / `TestPlan029NoWFPV2RouteUnconfirmedAndForeignNeverGuessedOwned` 覆盖完整Stop、O_EXCL、第二项写前中断、第一项写后收据前中断、foreign-first预检不部分删除、跨generation拒绝。测试完全不触系统Firewall/路由，**当前是已写源码，Windows编译与真实系统Apply/Stop未宣称PASS**。更新三个真实文件的 exact Git blob `result_blob`，其中旧 `native_unified_network_transaction.go` 是 `replace` 操作，完整保留 original/donor baseline/blob，不改验证门。不重复派发H1694或重跑028全矩阵。

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"Add no-old-WFP v2 per-route durable confirmed-ownership sidecar, crash/foreign fail-closed cleanup, and exact SOURCE-locked manifest for modified route transaction and pure tests."}
```
