# 2026-10-26 W168 / Windows 集成：原始历史导航与正反证据

这是 **检索地图**，不是再生成一份开发状态。原件仍在固定 Git 路径；失败、不确定与当前 PASS 不可互相覆盖。

| 需要追溯 | 精确原始入口与关键 SOURCE / Run |
|---|---|
| 实验最终代码 | `freeze/fec-linux-w168-20261026` → `254cf4110c1df3878c7bd0e782145fc381189b8f`；开发原日志 `docs/devlog/fec-network-work/` |
| 实验历史自述与逐项实验依据 | `docs/evidence/fec-network-work/final-report.md`（很长，只搜索 W编号段落，不作热读）和 `docs/evidence/fec-network-work/status.json`（有容量停止/merge false 历史真值） |
| W168 双架构56样本 / 250Mbps正负 | `docs/evidence/fec-network-work/20261026-W168-56case-UDP-ARM64-AMD64-Matrix-Completed.json`、`20261026-W168-250Mbps-UDP30-Fixed6-ARM64-AMD64-Native-Results.json`；[Run 40345202316](https://github.com/lly8666/wbd-next/actions/runs/40345202316)。56/56为 scoped observations，AMD64高压 INCONCLUSIVE。 |
| W160–W166 Game/Normal 更改和反例 | `docs/evidence/fec-network-work/20261026-W159-W163-Jumbo-Game4-Wide-Stagger-results.json`、W164/165/166同目录；Game4 0/4/50/140默认，Normal 分批模式仍只模型。 |
| Windows 原始 TCP/UDP/Stop PASS | `docs/evidence/M0/PLAN024-S881-WIN-LINUX-ORIGINAL-FUNCTIONAL-TCP-UDP-PASS-20261026.json`；源码 `0dc7b58d`；[Run 40311271021](https://github.com/lly8666/wbd-next/actions/runs/40311271021)。独立 Windows branch `fix/m0-windows-functional-wiring-20261026`；PR #27。 |
| Windows 历史红灯 +103B | `docs/evidence/M0/PLAN024-S880-WL-N0-exact-original-failure-20261026.json`；[Run 40295748769](https://github.com/lly8666/wbd-next/actions/runs/40295748769)。S869–S880 M0 历史文档在 `docs/devlog/M0/` 原路径全保留。 |
| 第一轮错误的 copied-tree 评审 | PR #26、`docs/integration/M0-FEC-GAME-TUN-ROLLING-MERGE-CONTRACT-20261026.md`；不能作为真实 merge ancestry。 |
| 当前真实 Git merge + 接线计划 | [Draft PR #28](https://github.com/lly8666/wbd-next/pull/28)；双亲提交 `fea9cd94`；`docs/integration/M0-W168-FROZEN-ARCH-WINDOWS-ADAPTER-STAGED-INTEGRATION-20261026.md`。该候选原生 Normal/off 同源功能现已通过，更多模式仍未获得 Windows 资格。 |

**原件存放规则**：不迁移既有 URL/文件（避免 SHA/链接断裂）；阶段结束时只在本索引追加 1 段近期汇总，不向 `START_HERE.md` 搬运全文；最新原生 Actions 记录写 `docs/evidence/M0/` 并引用准确 SOURCE；中性旧工位上下文原文放 `docs/history/handoff/`，新任务文档只链接。负面数据保持其原文件和判定。

## 最新验证与失败查找（2026-10-26）

- 真双亲候选 Normal/off [40361251070](https://github.com/lly8666/wbd-next/actions/runs/40361251070)，SOURCE `fbb281c7c8531a1e242c8368c0b11ca9545be730`，真实 TLS/Npcap/Wintun+Linux TUN 双向 UDP/TCP/Stop PASS；前一版 [40360805219](https://github.com/lly8666/wbd-next/actions/runs/40360805219) SOURCE `1b037131` 也 PASS。独立具体收据 [W168/Windows Normal 功能](../evidence/M0/PLAN024-W168-INTEGRATION-WINDOWS-NORMAL-FUNCTIONAL-20261026.json)。
- [40357841232](https://github.com/lly8666/wbd-next/actions/runs/40357841232) SOURCE `9137f27` 真实 Linux 反向 UDP 失败：Rust raw观察到546帧但tuple完成0；[40360124961](https://github.com/lly8666/wbd-next/actions/runs/40360124961) SOURCE `6e271c1` 原始限制12次的 Rust帧拒绝诊断 `WrongPersona`，原始 Action artifact ID 12667403997，合并时丢失了Windows11 TTL128与Legacy TTL64的TLS范围区分。原始红灯永久可查，不算 Game/FEC 产品错误。
