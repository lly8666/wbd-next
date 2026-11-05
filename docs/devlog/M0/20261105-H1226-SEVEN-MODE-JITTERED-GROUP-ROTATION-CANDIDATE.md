# PLAN028 H1226 — 七模式较长浮动定时轮换 + Game4 四 lane 逐一核验（候选）

- **新用户任务** 2026-11-05：继续测各工况；间隔稍长并浮动，观察更久看到四个 lane。按完整 Linux 任务交替，此次 client x86_64 + server x86_64 双原生，接上前次 H1225 ARM64 双端 p99 PASS。
- 冷 Go `--rotation-interval 18s --rotation-jitter 3s`：每次完成真实 TLS/Rust M4 READY 后，在同一原始 path supervisor 里重抽 15–21 秒，正负浮动；最短5秒、上限24h、jitter≤interval/3，未设 jitter 行为完全沿用旧定值。日志记录每次实际 armed delay 而非事后推算。**默认关闭**，外层完整IPv4 MTU默认1460。
- 基于旧H1222真原生三设备共享单443业务夹具加七个独立job：Normal off/fixed6/auto、Game2 off/fixed6、Game4 off/fixed6。每 job 4 次独立定时触发、generation 1→2→3→4→5、旧 owner exact Stop1–4、3并发各自 no-app-retry UDP，NIC/IP/MTU不变；测试约 80–110 秒 + 完成Stop，CPU和RTT p99、原生租约读回。
- **严格区分**：本 SOURCE Game4 的 Rust 1 个 `GameAdapter` + 1 个FEC + 4个lane，server等齐原始 TLS 全 lane 才原子安装新的 M4 *组*。本测试要求每代四条lane各有不同客户端源port，客户端和服务端分别记录真正通过TLS验证与Rust M4 install 的4个lane身份；5代即4×5组内lane身份证据，证明“每条都换到新组里”。**它不证明四条 lane 可以不影响其他三条而在不同时间独立热替换**；该数据面 API 当前不存在，不能伪装pass。若用户目标是严格单lane热轮换，需后续补原Rust lane owner局部更换而非加第二控制器。
- H1225 的p99修复仍在源内，H998真实在线同 socket MTU 缩窄FAIL仍保留，ARM Game4历史FAIL/remote ICMP/CPU因果/Windows/Android不升级。
- 测试与feature状态：目前 **CODE_CANDIDATE / NOT_RUN**；等待同SOURCE原生Action真实产物才更新验证资格。

```feature-impact
{"kind":"added","ids":["original-lane-rotation-jitter"],"reason":"User explicitly wants longer randomized timer and seven authenticated mode tests, with real per-lane group identity evidence and honest independent single-lane limitation."}
```
