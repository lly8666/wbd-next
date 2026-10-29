# PLAN027 H389｜回收真实 Actions 与 codec 功能门分离
2026-10-30。按 main registry/PLAN027/cursor 恢复并取回 H387/H388 结果，未重派相同 SOURCE。H387 原 Go Windows WAL [Action 40932953430](https://github.com/lly8666/wbd-next/actions/runs/40932953430) 在 SOURCE18cf：Windows WAL 主 job 与 normal/fixed/auto/Game2/Game4 五个独立模式 job 均 SUCCESS；Game2 真实 Wintun app 双向和 Stop 通过。保留旧 SOURCE 的失败历史；不外推为 PLAN027 新反馈代码的 B 验收或物理全绿。

H388 [native Action 40933554887](https://github.com/lly8666/wbd-next/actions/runs/40933554887) SOURCE9105：recovery 88/88 PASS、engine 134/134 PASS；codec **FAIL**，原因是非 required 的 `r1_steady_release_same_source_fresh_vs_reused_owner_cost` CPU 测量在 240s 功能门超时（exit124），同时现有 `r1_tx_cooperative_release_cpu_wall_diagnostic` ignored 不在允许清单。其余 native group PASS；具体 SOURCE/manifest/binary/log hash 写入独立 evidence。

本次最小修复：codec 功能门仅跳过前述非 required 长 CPU 测量（保留独立性能测量的源测试），并将现有 ignored CPU diagnostic 精确加入允许清单；所有 required codec 功能测试原样保留。新 SOURCE Actions 待收，不假称 PASS。生产逐 record M2 Receipt 仍在线、低频 Quality 和 ACK/SACK 双端 owner 尚未接通；A/B/C 与交付继续 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Recover exact-source Windows/native CI results and exclude only a nonmandatory long CPU probe from the codec functional gate; no product behavior or user-facing configuration changed."}
```
