# PLAN027 H395｜回收 H392/H393/H394 真正通过结果，继续产品阶段
2026-10-30。已回收 [H392 native Action 40936196353](https://github.com/lly8666/wbd-next/actions/runs/40936196353)：plan/build 与全部 codec/engine/platform/kernel/fec/recovery/receipt/normal verify SUCCESS；codec 114 PASS、1个已允许的 CPU diagnostic ignored，原非 required 长测不再占用240s功能门。此前 H388 codec FAIL 和 H389/H390 首错历史保留。

[H393 native Action 40936343251](https://github.com/lly8666/wbd-next/actions/runs/40936343251) 全部 jobs SUCCESS：recovery 89/89，新增 sparse receiver 必须显式 close 的反例实际执行 PASS；engine 134/134，codec114/114。SOURCE99c78aa 的 manifest `1aced604bbd97fdb0af0473bc10259bb60e77a384185d6e9e066876a5901db5`，其余二进制/日志 SHA256 和各 job ID 见 [H395 evidence](../evidence/M0/PLAN027-H395-NATIVE-QUALITY-AND-CI-RESULTS-20261030.json)。[H394 governance Action 40936503230](https://github.com/lly8666/wbd-next/actions/runs/40936503230) 结构及功能卡 SUCCESS，纠正 H393 大小门失败。

这些均为纯源/CI 功能证据；原 H387 Windows18cf 五模式 scoped PASS 也不能继承为本次 Quality 新 SOURCE 双端产品通过。**PLAN027 五项仍未完成**：线上逐record M2 仍LIVE，Windows/Linux 低频 Quality start/close/成熟反馈和 ACK/SACK 修复 owner、配置仍需接线，A/B/C 及长测未运行，最终交付未闭环。下一步继续 phase1 而非扩大旧 M2 矩阵。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Link exact-source H393 native PASS and source-only limitations to Auto feature card without upgrading Windows/Linux live quality, A/B/C or physical status."}
```
