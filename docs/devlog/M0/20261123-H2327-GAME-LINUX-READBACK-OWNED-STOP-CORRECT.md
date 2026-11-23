# H2327 · Linux 原生 Game 外层反馈模式化审计修正

- Linux 隔离矩阵 source `d5c64d29b9e25333dcfe36e24b16dd71815f079f` 的 Game2 5% 原生 run 实际完成 `PASS_SCOPED_OBSERVATION`、双向 offered 10Mbps、双方 client/server original GoTLS+Rust Stop 和 netns 清理，tc netem client/server 各 drop 8451/8426。
- 真 Rust M4 两侧 Game 原生 `V4_PUBLIC_GAME_OUTER` readback `repair_enabled=1`，各 `outer_data_retransmitted=388`，parity separate=1，CPU client 2.66s/server 2.82s。原 `outer_repair_native_verified=True`，但 Game 没有 Normal 的 `recovery_policy_verified` 字段，所以 H2326 新审计器误标 `OUTER_ON_NOT_AUTHENTIC`。这是只读证据字段混淆，不能反推产品 Game 外层未启用。
- 此次只对 Game 用 `outer_repair_native_verified` 检查，并继续逐 client/server 验证 `game_outer_policy` 实计数、fc parity、netem、Stop；Normal 保持更强 `recovery_policy_verified`。**对旧 in-flight d5c64d2 artifact 不自动追授 PASS**，各场景的现有 Workflow status/审核错误保留，用离线重新解读原证据，不重复实验。
- H2325 Windows Game 汇总器另有 Linux Go/Rust Game STOP 标记解析错误，原生 Windows→Linux Game2 5/30% 均已实际 true native PASS；需要从原 `server.log` 的 `V4_PUBLIC_GAME_OUTER` / `WBD_GAME_OFF_LINUX_NORMAL_OUTER_STOP` 逐项判别，绝不把审计绿灯替代真实双方 R/F。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Correct mode-specific Linux original Game outer-repair native evidence gating; no changes to Go TLS, Rust owner, frozen ciphertext, FEC or policy budgets. Preserve original native receipts with exact source."}
```
