# PLAN027 H414｜Windows 原 Rust Auto 发端窗口与真实驱动 F 接线

继续恢复 H413 SOURCE 与 Actions；H413 native-functional/ABI/cross SUCCESS，Windows 原生后续验证仍需回收，旧 M2 实测不能移植。

仅 native mode2 Auto：读取**同一个**原 M3 PN 发生器下一序号，发加密 START 后经真实 Npcap 确认才开放本地 1024-PN 有界采样。原业务 DATA 的真实 driver accepted/not-sent/uncertain 回调记录 F 和 censor；等待本地所有已冻结发送结果后发加密 CLOSE；失败保留同一 F 进行 CLOSE 重试；仅 CLOSE 确认才入 16 槽 TX 历史并延时 1.5s 下一窗口。不在 Fixed/off/Game 采样；Auto 不再生成原 per-record M2 RX draft，但 TX quality-summary/Auto 成熟累计与 Linux 对端仍待接，旧 Fixed/off M2 未退役。禁用跨机时钟和虚构确认。

**验证**：本批 SOURCE 尚待 Actions；只有旧源码及上一批纯/ABI PASS，不能宣称 Windows/Linux 新质量、机会修复或矩阵完成。§0 ①仍 PARTIAL，②A NOT_RUN、③B OPEN、④C NOT_RUN、⑤OPEN。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Auto-only original Windows M3 TX START/CLOSE preannouncement and real NPF F census with 16 bounded sender history; pending native verification and peer/Auto wiring."}
```
