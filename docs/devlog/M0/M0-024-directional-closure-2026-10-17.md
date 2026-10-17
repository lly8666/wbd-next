# M0-024 方向所有权优化恢复及收口（2026-10-17）

恢复时 main 为 54e67a20，M0 cursor 停在 H121；从 checkpoint 逐提交核对九个 S/H 与全部完成 Actions。中断前未推送的 RX 拆分没有计为交付。随后代码 S 9032476c 将原 Go 认证后的 **同一个** AEAD/PN replay opener 和 LINK 表移交 RX 独占线程，RX 用独立有界 M1 arena 直接接 M4 真实 recvmmsg；TX 继续独占原 PN/seq64、route revision 和最大 32 ready 的 sendmmsg。内核 I/O 之外没有再为 RX 每包持有 TX 的 Entry mutex；Stop 先通知、join 再归还驱动。没有增加配置/CLI/GUI 项，也没有伪造另一套认证或加密链。

SOURCE 9032476c 原 Go TLS→Rust→raw/TUN native 39032599398 成功，双向 8/8、真实 MTU 缩小及 netlink 失效、PN0 失去后 PN1 首到均经原调用链验证；同 SOURCE native functional 39032599453、G2/ABI/cross 成功。

同机 Rust A=9249115c，B=9032476c（测量 workflow SOURCE=48c6f6dc）：P10 AB 39032851848 成功，B CPU-s/GiB 低 14.50%；P10 BA 39032851741 成功，低 10.94%；两边双向 10Mbps 全交付、无非法包，没有需要修复的可重复 p99 退化。20pps 稀疏 39032851781 成功，CPU 百分比不具统计资格。实际收益只适用于该原真实开发路径/负载，不是整体产品或高压性能宣称。

D10 新 workflow 初次 39032851796 因错误 B hash guard 失败，纠正后 39032995995 两个 trace leg 退出码为零、取得 syscall 摘要，但 A 在 tracer-on 下 C2S 缺 14569 包、B 为零；诊断最终 FAIL/INCONCLUSIVE，不能把 traced CPU 或可能宿主瓶颈认作产品收益。历史同类 D10 不重复碰运气。C50 暂不加压，未来高压另按明确场景验证；M1 SPSC 在本原始内核 RX 独占路径没有引入冗余跨线程队列。

**本任务结构改造与必要 native/AB/BA/稀疏回归收口；D10 不通过的外部诊断边界明确保留。** 原 023、B01–B04 余项、超 MTU、Game/FEC/repair 整合、标准 features=0、物理与产品资格不因本结果自动通过。详细 SOURCE/产物/hash 在 docs/evidence/M0/M0-024-directional-closure-dfe54df144450f22f5144fd3b43335635e01eb90.json。
