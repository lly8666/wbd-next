# PLAN028 H1275 — 3×1800s ARM64 原生结果与最窄验收修正

2026-11-06 用户授权长测后的继续开发。**没有重跑 H1274**：原 Action [42162179000](https://github.com/lly8666/wbd-next/actions/runs/42162179000)，严格 SOURCE `d04ace6ce8781f5afea96e3ff76a53ac617b771e`，build 成功，三个 1800 秒场景全部完成真实原始 Go TLS/Rust 网络业务、上传产物，但三个 scene job 最终均 FAIL。原始失败和新发现的真实数据面故障均保留。

## 证据，不是 banner

| 原生 ARM64 双端场景 | 成功整组换代 Alice/Bob/Carol/Erin | Game4 单 lane 本地成功/尝试；服务端匹配 | Game2 客户端 READY 但服务端未完整提交 | 最长双向缺业务 | 服务器 CPU | 表演式 R 已接受字节；Mbps；R/(F+R) |
|---|---|---|---|---|---|---|
| baseline | 27/25/21/16 | 19/19；19 | Gen18 | Carol 83.5s，Bob 72.8s | 62.269% 单核 | 184,510,709 B；0.82005；0.69662% |
| heterogeneous | 23/20/16/10 | 4/15；3 | Gen6/17 | Carol 106.3s，Erin 9.5s | 81.127% 单核 | 337,685,552 B；1.50082；0.85756% |
| pressure | 25/22/16/10 | 5/15；3 | Gen18/30 | Carol 99.2s，Alice 69.8s | 104.943% 单核 | 623,471,252 B；2.77098；0.83192% |

完整原始 artifacts SHA256 和观测边界在 [H1275 evidence](../evidence/M0/PLAN028-H1275-SOURCED04A-THREE-1800S-ARM64-POSTHOC-20261106.json)。所有 5 个客户端在 3 场中真实 TLS /32 租约均稳定、已观察到原生 Stop。Game4 逐 lane 轮换应按 `V4_PUBLIC_GAME_SINGLE_LANE_ROTATION_READY` 加服务端 `V4_PUBLIC_GAME_SINGLE_LANE_READY` 对应客户端本地源端口来验；整组 generation 保持 1 **正确**，旧 H1274 reporter 错判零换代。其他模式成功换代 generation 可因失败候选跳号，必须验证单调递增和每个实际旧 owner 精确 Stop，不能要求数字连续。

**更严重而独立的故障**：Game2 中若干新组已在 client 端打印 READY 并回收旧组，但 server 端没有同两条真实 TCP 源端口的 `V4_PUBLIC_GAME_GROUP_LANE_READY`，随后长达 83–106s 无双向用户 UDP 交付，下一次组换代后恢复。高损下 Game4 也存在 local-ready/server-not-confirmed 及十余次 cold deferred。此为产品层需修的 server cohort commit/客户端交接竞态，不能把修验收器称为修复。服务端源端口匹配只用于离线证据，不更改新 TLS 身份或 wire。H1275 已将报告器更新为真正 Game4 逐 lane 统计、成功编号允许跳号、Game2 server M4 双 lane 匹配，**尚未对新报告器另跑长测**。

基于 10ms 的活跃发送无接收时间统计是应用交付缺口证据；p99 仅针对已成功交付包，不涵盖缺失包。CPU/RSS 不代表优化因果。原始 qdisc 实际损伤在 1/5/15/30% 配置点附近；服务器每租约 TUN pending overflow 在 baseline Bob=52、pressure Alice=87、Dave=2461，其他无相应正值。Normal、FEC、Game 模式的 first/replay record byte 会按来源隔离；Game 复制仅是表演式冻结原 PN/SEQ 加密 record 重发，不能算新增业务恢复。R/(F+R) **不包含**控制 C、FEC 冗余或 IPv4/TCP/L2 头，R/(F+R+C) 仍 NOT_MEASURED。

**下一步的唯一关键产品目标**：精确追 server Game2 新 TLS cohort staging 和 commit 缺口，避免 client 单端 READY 后回收仍实际能用的旧 lane；不加第二恢复器、不改 FEC/PN/密码/稳态 wire、不重复 3×30min。找出能直接验证的最窄修复后，按 SOURCE 冻结先做小型真实回归，再决定是否需扩大资格。旧 H998 同连接热 MTU FAIL、H1259/H1268 间歇 S2C 缺口、Android/物理外网未测均保留。

```feature-impact
{"kind":"none","ids":[],"reason":"Only narrow original-source forensic report oracle and immutable evidence, no production codec, TLS handshake, FEC, PN, mode, MTU or wire change."}
```
