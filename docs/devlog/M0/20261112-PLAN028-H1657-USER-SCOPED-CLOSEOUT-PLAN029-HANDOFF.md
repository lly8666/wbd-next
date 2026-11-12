# PLAN028 H1657｜用户授权限定范围收口，留 PLAN029 独立新 agent 入口

2026-11-12 本次用户明确允许按最新测试快速收口 028 并准备另起新 agent 做 029。**结论：028 已有产品核心功能按已测范围交付，状态 USER_AUTHORIZED_SCOPED_CLOSED；不等于完整 L0–L3、Windows 全机接管或生产发布 PASS。** 028 不再无限重跑已验矩阵，也不擅自启动 029。

正式 SOURCE `52767d183b61eaf2621d967b16e85e644b1de428` 的 [七模式签名 Windows/Linux 实网](https://github.com/lly8666/wbd-next/actions/runs/43161652596) PASS_SCOPED；[GUI 正式相同 Go/Rust 构件](https://github.com/lly8666/wbd-next/actions/runs/43167444547) 实际编译、配置/字段与 WinForms 按钮 VM PASS，但真正 GUI 点击建立签名网络仍 NOT_RUN。最后 [H1656 真 native Auto 有损](https://github.com/lly8666/wbd-next/actions/runs/43171331954) **SUCCESS**：正式 Go SHA edbb9715…f582、ISA-L DLL SHA3973…9357，与 GUI 正式打包匹配；双向真实30%/250ms、10Mbps、60s、outer1460/两端内层1375、Windows/Linux首次交付99.7268%/99.7779%，真 TLS/Rust UDP/TCP/Stop PASS_SCOPED。H1654/H1655 旧 manifest/ISA-L DLL预检失败照留；后续 H1656 是新真实执行，不洗旧失败。

异构每客户端 MTU 不是缺口：H1601 单 Windows+四 Linux 同服（前四1460、Erin1280）150s 真 UDP/TCP/Stop；H1644 Linux五客户端1460×4/1280×1原始真180s严格离线复判；H1386 ARM64 五客户端中 Alice 物理MTU1500→1280 冷重认证并有业务恢复，均 SOURCE 限定有效。近内层MTU**边界包型**另属用户已跳过范围。

**收口但不冒称合格的边界**：ACK/FakeTCP反馈仍独立 OPEN；真实 GUI 人机发起完整签名 OS Applied 与 Stop NOT_RUN；独立 Windows A/B/C 1800s L3 ENVIRONMENT_BLOCKED；失败包包含的一向 p99/极端 L2 容量及恢复未全面验；同 Win 双 Wintun 旧 H1587 FAIL 用户不跑，近MTU用户不跑；物理WAN/Android、完整 host-global Windows 路由/WFP/IPv6不得宣布生产资格。原 FAIL、NOT_RUN 保留。关键安全硬门（TLS标准外观/认证/完整性/generation/MTU/owned Stop）没有因收口被放宽。

原始结构化结论：[H1657 收口证据](../evidence/M0/PLAN028-H1657-USER-AUTHORIZED-SCOPED-CLOSEOUT-20261112.json)。029 仅可在新 agent 明确启动时由 M0 单写者切换 cursor/registry；不得为了029重派028整套网络场，也不把未解 ACK转写为029通过。

```feature-impact
{"kind":"none","ids":[],"reason":"Test evidence and user-authorized scoped delivery closeout/handoff only; no product/config/default/schema change."}
```
