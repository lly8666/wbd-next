# PLAN029B H2139｜Game2/4共用 Rust V4 业务分流，off/all/LAN/CN 冷策略
- 依用户2026-11-18新授权，扩展此前029/029B**日常限域收口之外**的Game2/Game4全分流模式；不重新跑旧已通过的Normal B0–B5。
- 原Game2 `SplitEnable` 冷启动提前拒绝删去，**仍须原Game2双TLS车道、同原GameAdapter/FEC、独立AEAD与MTU/WAL**；接入已经支持2/4成员的原Go `StartNativeGameIOWithColdSplit` 和 Rust `wbd_m0_win_game_native_v4_start`。Game4同样使用共享源。只在原TLS验证epoch后注入 cold policy、单Rust `NativeSplitWorker`；无新增Go逐包泵、无wire/FEC/repair变更。
- 显式区分业务 effective split 与请求字段：`split-enable=false` 和 `route-mode=all` **均不创建业务Direct/Bypass/FakeIP/旧journal**，真实OS BuildCompactNetworkPlan不再无条件带Direct/Bypass CIDR。保留原Rust V4 DNS-only /32 TCP53/Defender 及公共Tunnel；`bypass-lan` 是IP Direct；`bypass-lan-cn` 普通CN real A+物理DNS/海外Tunnel、高级CN选择FakeIP Direct且stop owned。
- Game专属 TLS `startup-padding tls/flows` 尚无原M1 LINK，显式拒绝而非静默忽略。Game2/Game4 FEC off/fixed、外层MTU和原协商路径未修改；原Game2/4启动、TCP Prepare/Defender/Enable仅在真实OS Applied+MTU readback后，且即使all/off也保留公共DNS TCP。
- **当前该产品源是候选、原生Windows网络未签名验收**；必须独立验证 Game2/4各route与 off/fixed、真正原DNS/Direct/Tunnel UDP/TCP/Stop，不能因原Game4 H2134成功借证宣称所有模式PASS。冻结安装器manifest只更新3个确切原Go blob pin，不改原上游Go仓库，不动Rust ABI或热路径。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Game2 and Game4 now share the original cold Rust V4 DNS/business split wiring across disabled/all/LAN/CN; product changes require new original native evidence and do not promote untested Game2."}
```
