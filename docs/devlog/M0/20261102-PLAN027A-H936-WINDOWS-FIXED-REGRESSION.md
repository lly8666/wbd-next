# PLAN027A H936｜Windows真实Rust owner v5 几何收窄与 RX 独立单测

接 H935 `2b2ad98eb47b6d8eadca656f02bdcec03007d90f` 的唯一 Rust receive预算修复：以 original-Go 真实 M3 Prepare/Commit/Win32身份绑定 fixture，固定 `outer=1400` / 本地计划Wintun `1273` / 认证peer record `1400`，Feature7模式核 `wire1318`、返回完整业务1273、RX认证窗口仍独立、后续相同generation拒重复绑定、原Stop/Release完成。Normal `outer1460` / 计划内层1250→wire1281同测。无硬改历史性能、无跨lane PN重用。

此乃 Windows Rust owner 模块/真实加密边界单测，不是真实 Windows+WSL 业务端到端 OS applied；旧 SOURCE `adc18d75` Run41437214958 Fixed rc=1 FAIL 保留。所有实际 native MTU/DF/弱网仍需精确SOURCE验证。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Add original Windows Rust authenticated owner v5 budget regression for reported Fixed1273 wire1318 pre-READY refusal; verify independent RX limit, single bind and owned Stop, without a new owner or formula."}
```
