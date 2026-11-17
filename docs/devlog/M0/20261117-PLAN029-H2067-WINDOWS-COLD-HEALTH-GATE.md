# PLAN029 H2067｜原 Windows M4 冷启动缺少 Health，服务端 B 保留 A 的 /32 路由

H2066 三条**真实** Windows2025/WSL2 Action 及原始 ZIP（GUI [44020809932](https://github.com/lly8666/wbd-next/actions/runs/44020809932) artifact14301231995；domain [44020814338](https://github.com/lly8666/wbd-next/actions/runs/44020814338) artifact14300937695；TTL [44020818591](https://github.com/lly8666/wbd-next/actions/runs/44020818591) artifact14300698642）均通过了精确原产品 SHA、原服务器共享手动 /32 AF_PACKET 监听、两次独立 `41031/41032→443` 的真实 SYN/SYNACK、两次 TLS 认证。域名场在第二次连接前重新走真实物理 UDP TC→同端点 TCP53，TTL 场在第一次连接期经 2s 过期完成两个真实 FakeIP A/CNAME 回复 `198.18.0.1`。但这**不是第二代通过**。

三份服务器日志相同：旧 Rust owner 已用 `10.66.0.2/32` 并仍活；第二代 TLS/本地 M4 后 `V4_PUBLIC_NORMAL_TUN_CANDIDATE_DEFERRED role=server generation=2 old_route_preserved=1`；服务端 5s 后 `V4_PUBLIC_MULTI_SERVER_B_CLIENT_UNPROVEN port=41032`。Windows B 的 Rust TXCopied≈232–248，RXDelivered=0；原服务器 A 持续持有路由、无认证 B Health，按安全门槛拒绝 B。两个独立 Rust server session 均最后被服务端精确 joined Stop，shared TUN Stop 见于服务器日志。Windows B 只有冷 TLS，却没有第二次 OS Applied，后续真实 Direct/Tunnel、TTL 第三问都 NOT_RUN。

源码比对：Linux `v4_embedded_go.rs::start_loop` 在真实 M4 worker 就绪后调用 `HealthClock.arm_client_cold_ready()`，复用已加密且需 PN/replay 成功的 **5 次 kind0 Health**；原 Windows `v4_windows_native_runtime.rs::start_native` 尚未 arm，仍依赖默认 15s Health，晚于共享服务器 B 候选的 5s 验证 deadline。此为对本次根因的**高置信诊断**，仍须下一编译 SOURCE 真业务验证。

本次仅在 Windows Rust *现有* M4 worker 起点，在原 TLS 认证和真实 Wintun/NPF 两端验证后、启动实际 TX/RX worker 前 arm 同一个 HealthClock 已存在的冷启动五次 kind0；无新定时器/线程、无新报文/ABI、无 Go 逐包热泵、无假 OS Applied、未放宽服务端必须经过 AEAD/PN 的安全路由切换门槛。保留原失败。新源码运行三条 bounded 真 Action 后才能收口。

```feature-impact
{"kind":"updated","ids":["windows-native-transport","dns-split-ipv6","client-domain-bootstrap","gui-config-feedback"],"reason":"H2067 real H2066 second TLS success but first native M4 reverse Health 5s fails; Windows existing canonical cold Health startup arm added, physical re-test pending"}
```
