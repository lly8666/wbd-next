# PLAN028 H1430 | 原生 Windows 单实例＋独立 Linux 同服 1800s L3

2026-11-09，用户追加要求：Win–Linux 平台的 1800s L3 与现行 ARM64 2×1800s **并行执行**。理由是 H1420 严重失败属于 Windows11 和 Linux Legacy 不同会话在同一 Go TLS443/Rust server 的真实 DATA 上行隔离，原 ARM64 五客户端两场并不能覆盖签名 Npcap/Wintun 长期客户端持有/Stop。

复用 H1423 原 signed Windows2025 Npcap/Wintun **一个** VPN 客户端 Alice + WSL2 中独立 netns/Go TLS/Rust TUN 客户端 Bob、原共享服务端和真实每会话冷 persona；不添加第二个 Wintun Windows 客户端，不更动协议、FEC 或产品。现行 `.github/workflows/m0-wl-public-normal-full.yml` 主入口由特定 commit 标记 `[plan028-win-linux-co-client] [plan028-win-linux-1800]` 唯一选择。所有 Runner/job/独立 step watchdog/Python PID 限制仅对该 L3 模式延长，其他模式旧门槛不变。

H1415 旧短夹具仅新增长测 opt-in：实测两个客户端保护 TLS/Rust M4、内层路由、Windows11/Legacy RX 后，真实 UDP echo/reverse 每个约10Hz 连续1800s，全部真实 IP 用户态 socket；每5s采原始唯一 UDP 交付，任一 Echo 或 reverse 最近/历史无 RX ≥1500ms 即 FAIL；1800s 两侧各发≥12500、echo交付≥97%、reverse收到≥12500；每60s真实 TCP 双向应用复测至少28次、每120s分进程本机 RSS/CPU 抽样≥12次。时间基于一个 host 的单调时间，不在跨OS时钟之间计算假端到端时差。原始应用日志、数字样本 SHA、manifest保留；任何错误持有真实失败原因，不拿 p99 成功包掩盖秒级 gap。

最后**必须**原 Windows A owned Stop、独立 Linux B 真 UDP/TCP继续交付，再 B 和 server exact Stop、Windows WAL 归零、WSL2 bridge/veth/IP/route 原状恢复，才能令原 workflow 记 `PASS_SCOPED_REAL_1800S_BOTH_CLIENTS`。保留未在此场测试的网络切换和跨物理 WAN、旧 H998 HOT MTU 原失败、Android未跑；不能只凭构建/超时延长写 PASS。此项仅1条 Windows L3 平台独有补充，既有 ARM64 baseline/hetero 独立两条仍在运行。PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Only test-only bounded real Windows+Linux 1800s L3 data/Stop oracle and workflow deadlines; original Go/Rust product and public settings/wire unchanged."}
```
