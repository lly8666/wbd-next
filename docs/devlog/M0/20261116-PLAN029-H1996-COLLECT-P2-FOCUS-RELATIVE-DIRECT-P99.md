# PLAN029 H1996｜收 H1995 真 P2，聚焦 Direct 相对 p99 大差距（停止极端工况开发）

- **M0 接续 / 保留原失败**：原 H1993 SOURCE `34e87006` [Action43840543096](https://github.com/lly8666/wbd-next/actions/runs/43840543096) 原 native **FAIL**，严格下载 `recv` 128KiB 精确对齐断言错误、Stop NOT_RUN；H1995 在 SOURCE `5add3e6903faa8ed2f9116350067b9fa2563d5be` 只修 Python 越界跨桶检验，不改 Rust/Go/协议。此处不把原失败改成 PASS。
- **已完成签名在途回收**：[H1995 Action43844626304](https://github.com/lly8666/wbd-next/actions/runs/43844626304) Windows/Linux Rust、Windows Go、Linux peer 及真实 `native-public-two-os` job133224228145 **SUCCESS**。原 Windows2025 ↔ WSL2 Linux 真 Npcap/Wintun/内核 TCP 1MiB、同 SHA/FIN、并发 96B Tunnel UDP 120/120，双端 owned Stop PASS。原生 artifact 14214519541；不重复 dispatch。
- **同 VM 有界普通 1MiB**（相同 16KiB/4ms 人工 pace，*不是峰值或 RTT p99*）：物理 **295.366ms**，Direct **301.871ms**，比值 **1.022×**；真实下载最大 128KiB 进度空洞物理 **1.171ms**、Direct **1.732ms**；Tunnel UDP RTT p99 **2.823ms**、最长回包间隔 **20.829ms**，120/120。此差距不值得继续调 socket/buffer/Nagle。
- **Direct 真 p99 的大相对差距仍 OPEN**：H1974 原失败 Action43808776053 中物理/Direct 1KiB 已建连 RTT p99 **0.3558/0.7411ms（2.08×）**，5 次 Direct **61–63ms**、4 次真实同 SEQ 重传、约 60ms `NAT first queued→inner kernel read`，其诊断因严格 QPC join FAIL，应用 SHA/FIN/Stop 是独立有限 PASS。H1978 原失败 Action43817058020 另一 VM 物理/Direct RTT p99 **0.381/0.682ms（1.79×）**，未复现 >8ms；经离线 QPC 修正的 NAT→inner read p99 139.3μs **不能**跨 VM 宣称根因消除。H1995 没测同 SOURCE Direct 1KiB RTT p99/CPU GiB。
- **执行取舍（新用户指令优先）**：停止继续极端容量压力、长时 2048 重刷/调种子/盲目 1ms 空轮询，不为 1MiB 2.2% 差异做大改。下一阶段只针对正常 Direct 小包的 **1.8–2.1× p99** 与偶发 60ms 真实停顿：复用原 H1977/H1979 时间偏序和已有 owner 计数找第一次异常的 TX mailbox→RX `WintunSendPacket`→`FD_READ` 真实边界；只有证据指向一个可反证的丢唤醒/跨流 HOL 实现缺陷时才做定向单修复＋同 VM 物理/Direct 原生对照。现有 WinSock shard 轮转、DNS/UDP 空扫抑制已经代码落地，未证实因果，不再复制优化。**没有新假设，不派 Action。**
- 029 仍 **IN_PROGRESS**；原 D1–D5/P1–P2 未全出齐，GUI/Game4/IPv6 等开放项不因这轮签名绿灯而升级。028 限定结论、030 未开工；保留 TLS、MTU1460、generation、owned Stop。新 Rust/Go 产品改动 **NONE**。

- **自动治理失败原样保留并修复**：H1996 首个 docs-only commit `92eafb0c` 的 [Action43849096878](https://github.com/lly8666/wbd-next/actions/runs/43849096878) **FAIL** 于治理 `unbounded context_refs`（M0 cursor 9 条超过既有 `max_refs=8`），121 项既有功能单测单独 PASS；修复仅保留最新 8 条上下文引用，不修改历史性能事实、Rust/Go、原签名网络测试或脚本限制。此修复的新治理结果以 Action 实际结论为准。

- **第二个失败原样保留、已定位**：[Action43849517151](https://github.com/lly8666/wbd-next/actions/runs/43849517151) `scope_audit` 已 PASS，但 `governance validate` 检验当前 M0 `evidence_refs` 时要求**每条 evidence.source_sha 与 `last_tested_source` 一致**；H1996 首次把新 SOURCE `5add3e` 与历史 H1992 SOURCE `8ed70b` 混在当前正式引用。只保留 H1996 新证据于 `evidence_refs`，H1992 历史文件仍原样留仓及旧 devlog，不能冒作 H1995 同源测试。未修改产品/性能结果。

```feature-impact
{"kind":"none","ids":[],"reason":"H1996 collects one existing original H1995 signed normal P2 without code/feature changes; user reprioritizes large relative Direct RTT p99 and real 60ms stalls, avoids extreme feature development and duplicate dispatch."}
```
