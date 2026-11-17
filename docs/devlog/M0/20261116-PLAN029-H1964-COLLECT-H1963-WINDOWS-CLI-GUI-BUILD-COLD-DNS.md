# PLAN029 H1964｜收齐 H1963 Windows 原装配、Go 冷 DNS 单测、GUI build

- H1963 exact SOURCE `5e46a2a06c8292be049f57da5c15df4c534d7b79`，原 [Windows CLI Source Action43797131805](https://github.com/lly8666/wbd-next/actions/runs/43797131805) **SUCCESS**：原 pinned-Go assembly 校验、Windows source Go编译、原 Defender COM 一条规则 Add/readback/CAS 删除均通过（Defender不等于产品Connect）。
- 原 Action 的日志确实有 `=== RUN   TestPlan029H1963ColdDnsTwoSingleEndpointsRejectZeroAndBroadcast`、随后 `--- PASS`。**不是编译冒充单测**：原Windows Go runner `-run '^TestPlan029'` 已纳入本用例，覆盖 All/BypassLan/BypassLanCn三模式×0/broadcast两种非法DNS×Direct/Tunnel两方向，且同一合法IPv4用于两个DNS字段继续允许。H1961旧大小写 `TestPLAN029...` 未运行这一点依然保留，不修改旧Action。
- [原 Windows Go/Rust/Linux preflight43797131838](https://github.com/lly8666/wbd-next/actions/runs/43797131838) cheap、Win Rust、Linux Rust、Win Go四项均 SUCCESS；[GUI profile build43797131801](https://github.com/lly8666/wbd-next/actions/runs/43797131801) 真 WinForms+Go/Rust 原 source编译 SUCCESS，**不等于GUI按钮实际 Connect/Stop/Windows/DNS生效**；[治理43797131908](https://github.com/lly8666/wbd-next/actions/runs/43797131908) 双job PASS。
- H1963无新 P2原生流量 scene markers，未重复 H1958 WSL2 4MiB A/B。最后一次真Win2025+WSL2原 Wintun业务仍是 H1958 SOURCE `ab224ae...`（含 D1/D2限定收件、4x4MiB/384QPC、Tunnel UDP/Stop）。此批只把冷源拒绝无效单 DNS 与Windows GUI/CLI**build**推进到真实runner证据，D1–D5、P1–P2全部出口、共享CDN、IPv6、GUI按钮、Game4仍 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Collect signed original Windows Go compile and actually executed H1963 cold two-single-DNS test, current WinForms build and governance receipts; no product feature code or acceptance status edited."}
```
