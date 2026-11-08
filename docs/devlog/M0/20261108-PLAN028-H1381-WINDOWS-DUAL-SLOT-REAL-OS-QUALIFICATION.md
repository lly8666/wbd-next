# PLAN028 H1381：Windows 双真实产品所需的独立 OS owner 锁先行门禁

2026-11-08。两套 Linux/x86、ARM64 真账号、真实手动 /32 TLS443/Rust M4 已在 H1379 同源码实际通过；Windows 两原 TLS 产品进程、两签名 Wintun + WFP/route/WAL 并存依然 NOT_RUN。

本次修改仅加**严格 Windows CI-only 的命名内核 event** 设备级隔离：需要同时 `GITHUB_ACTIONS=true`、`WBD_PLAN028_TWO_REAL_CLIENTS=1`；限定别名 `WBDWLCLIENTA` / `WBDWLCLIENTB`，账号 `alice` / `bob`，服务端认证给定手动 `/32` `10.66.0.2/32` / `.3/32`，WAL 文件名包含精确别名。未知别名、跨账号、IP错配、WAL错配均拒绝，重复同设备 OS event 按原 CreateEvent 失败；环境不开启时保留原 Windows 整机唯一客户端锁。这不表示 WFP/默认路由已经能多设备共存，更不代表两原 Go TLS/Rust 真实 Windows 客户端已成功。

新增 Windows2025 runner，依旧 pinned donor Go 和完整 manifest source lock，实际 Windows CreateEvent 内核测试与旧全局唯一锁测试并行验证。真实两产品同时 TCP443 + Npcap + 签名 Wintun + Rust M4 A Stop B 仍待运行；H998 原 same-socket 热 MTU FAIL 不被覆盖。其它 x86/ARM Linux 真实业务 H1379 继续 PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"H1381 strictly test-only CI per-alias Windows native OS named event ownership qualification guard, and Windows2025 kernel-event test; production default remains legacy single-instance, so no existing feature verification claimed and Windows dual authenticated product stays NOT_RUN."}
```
