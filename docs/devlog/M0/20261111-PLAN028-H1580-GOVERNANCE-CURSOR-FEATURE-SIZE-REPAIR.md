# M0 PLAN028 H1580｜治理卡大小与M0证据指针纠正（2026-11-11）

状态：**PLAN028 IN_PROGRESS**。修复的是本轮记录/格式失误，不改业务协议或降低 source/ownership 硬门。

- `ca5045543d2c0f8732f12a761153248cd9cbe7d4` 的治理运行 `42989647902` 功能目录失败：部分历史功能卡超过每卡 16 KiB 上限；`42989648015` 治理回归失败，因为 M0 cursor 的 `evidence_refs` 混入了非本次 SOURCE 的 H1577/H1579 证据及 Markdown 导航，导致 `evidence is for a different SOURCE`。这不是产品网络失败，却是不能忽略的主线合规失败，保留原始 Actions。
- 本提交只对七张受影响功能卡进行紧凑 JSON 序列化，部分旧的冗长历史 scope/limitations 改为短摘要并指向**原样保留**的完整 `evidence` 路径/旧 devlog；历史验证行的 status、source_sha、evidence 仍完整，新增新源码 NOT_RUN 仍明确。没有将旧结果合成为新源码 PASS。
- M0 `cursor.evidence_refs=[]` 是必要的真实状态：当前 `last_tested_source=813e4c5c71fe2a1f2442bfda0ce19c205a398d03` 的逐场真实 Actions 已收，但仓库尚无经过审定的同 SOURCE JSON evidence 归档。完整 H1577/H1579 和最新覆盖表改通过 `context_refs`/M0 devlog 引用，`unverified=true`。不绕过 `tools/governance.py` 同 SOURCE 校验。
- 正式配置/平台/测试范围见 `docs/testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md`；本轮 Windows 新 AutoLease/三 cipher 仍仅源码+build，真实 Windows signed Npcap/Wintun 和 Linux 多客户端异构协同未达到验收。
- 下一步只在主线治理恢复成功后触发**一个**原生 Windows 自动IP AES256 + Linux ChaCha/AES128/AES256 异构 150 秒 UDP/TCP/Stop 场景（H1581），失败也必须记录 first-fault 和完整 Action，不把夹具/产品误判。

```feature-impact
{"kind":"updated","ids":["record-crypto","windows-native-transport","gui-config-feedback","idle-rotation-keepalive","arm64-targets","normal-off","path-mtu-budget"],"reason":"Repair 16KiB bounded-card schema and maintain exact historical source/status/evidence rows; remove mismatched cursor evidence pointer without weakening source guard, retain true native qualification gaps."}
```
