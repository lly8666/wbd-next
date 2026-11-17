# PLAN029 H1965｜用户指定回到真实稳态性能，不追极端共享CDN

2026-11-16用户明确指示：不要继续搞极端工况；同一真实IP对应CN/非CN域名的共享CDN反例**不再深究、不作为下一项性能阻断**；优先定位 Windows 系统＋Rust Direct/Tunnel 实际额外增加的延迟。未测场景仍标 NOT_RUN，禁止伪造 D2 全PASS。

## 现有真实源锁证据与必要区别
- 原 Win2025/WSL2 H1958 SOURCE `ab224ae03cd362f758f98fb59fd097285e436ca6` Action43792684618：384条小TCP first-write QPC 和四条各4MiB ON/OFF/OFF/ON。ON 首包显著更早；大流 Direct 仍约物理基线2x。四条 bulk 仅2条/臂，运行波动过大，不能归因为提前建连的稳定性能损失。产品 early preconnect 始终 OFF。
- 既有 `v4_windows_native_tcp_direct.rs` 采 FD_READ/FD_WRITE/TCP ready-ticket 与首回包QPC，缺的是**已建立的同一个TCP流**普通数据到内核两腿的逐阶段等待；首包QPC、应用全事务总耗时本身都不能回答纯Rust转发、Windows栈调度和连接建立各占多少。

## 下一项唯一优先测：同SOURCE、同Windows Wintun、单个已建立TCP流的 steady-state QPC
1. **正常负载**：原 Windows应用→原Rust Wintun/NAT→Windows内核listener→物理绑定TCP socket→同WSL2 Linux普通echo；先完全建连并预热，后执行固定1KiB（可再4KiB）有序请求/回应约2,000–4,000次。不重连、不高并发、不大内存、不造极端DNS/CDN。同原SOURCE/VM 顺序测物理socket基线及Direct；保留默认产品preconnect OFF。
2. **唯一 Windows 同频QPC**：应用send/recv；原Wintun ReadPacket已拿到数据→分类后→NAT完成→转交原reverse mailbox→实际RX owner Wintun SendPacket 返回；native inner TCP read→外部physical write；physical read→inner write；反向Wintun Read/分类/NAT/SendPacket→Windows应用recv。所有标签、线程及对应 TCP 序列/应用请求编号要源锁匹配，**不能以SendPacket返回冒充内核已接收或app交付**。
3. **分帐**：Rust调用内CPU样执行span、跨owner mailbox队列年龄、FD就绪/调度ticket等待、socket WouldBlock/short-write/排队、OS 内核TCP两腿间隙分别给p50/p95/p99/max及样本数。跨Windows QPC可相减，**不同Linux/Windows时钟绝不能直接相减**，等待≠Rust CPU。TCP是byte-stream，按app request ID/序列区间匹配，不能假定一个应用小包等于一个内核TCP packet。
4. **尾延迟与不扰动**：应用完整往返每次采QPC p50/p95/p99/max；Rust scoped采样+预分配有界环，最终Stop一次汇总而非逐包eprintln/锁/文件。无trace对照确保观测扰动不掩盖微秒级差异；先stop-and-wait看单消息首到，再小批连续发送看queue/吞吐，但不增加重型压力。成功还要同一Linux核socket SHA/bytes、当前Rust/Tunnel独立进展、双端owned Stop。
5. **严格结论**：可报告用户态可见的分流耗时及等待占比；同VM物理/Direct差值仅为**端到端额外延迟估计**，不强行全部归因Rust（额外Windows内核TCP腿、线程唤醒、loopback/WSL2传输均参与）。测得第一大p99耗时段再优化，再做一次对应复测；不重复刷H1958四臂。

原 PLAN029 D1–D5/P1–P2未完全退出，不因本优先级变化声称它们PASS；未要求研发立即扩大原生 Action 矩阵。GUI/Game4/IPv6等照原证据保留 OPEN，不为它们先发网络矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"Record user-prioritized ordinary steady-state Direct TCP QPC performance work and explicitly deprioritize exotic same-real-CDN reverse-case; cursor/devlog only, no production code or acceptance claim."}
```
