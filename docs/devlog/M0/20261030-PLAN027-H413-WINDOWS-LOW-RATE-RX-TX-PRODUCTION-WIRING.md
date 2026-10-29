# PLAN027 H413｜Windows 原 Rust owner 低频 Quality RX/TX 生产接线

2026-10-30，先重读 main 的 M0 prompt、入口、AGENTS、章程、registry.M0.goal、cursor、PLAN027 和最近 Actions；恢复 HEAD b4cd006c（在途为零），不重跑历史 SOURCE。当前仓库单 main writer，未覆盖未知改动。

H413 实际源码：Windows 原 Rust owner 的 M3 唯一认证 kind1 START/CLOSE → scoped `ReceiveWindows` 四窗口（lane/epoch/direction/PN）；Normal 以及 FEC2 RX 经原 AEAD replay 唯一 PN 验证后观察，未把 carrier ACK 或控制 PN 当成业务接收；CLOSE 的 F/完整性由授权发端声明且 3s 本机成熟后才产生 36B v2 Quality。候选优先于旧逐条 Receipt，透过同一密文 kind1、真实 MTU preflight 和原 Npcap send-result 提交；失败保留摘要、不消耗虚假确认，老 Health payload-idle 同包发送并复用 15s 调度。FEC2 已补接收调用。没有增加 per-record Go FFI、计时器或历史扫描。

**事实边界**：尚未接上 Windows TX START/CLOSE 生成、SendHistory→Auto、Linux 双端新反馈、ACK/SACK 修复与 M2 全面退役。低频摘要必须由未来对端真实 START/CLOSE 才会出现；不能把旧 M2 的通过冒充新机制通过。SOURCE 与功能回归在 Actions 进行中；本日志仅记录提交意图，不能声明 PASS。简化 A、接线 B、矩阵 C 及长测均未跑。此前 97c9 源治理 feature catalog FAIL（缺 feature-impact），本提交补齐。保留历史失败。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Wire authenticated low-rate START/CLOSE receiver and mature Quality kind1 sender into actual Windows Rust owner and FEC2 replay ingress; candidate unverified, old per-record M2 remains active."}
```
