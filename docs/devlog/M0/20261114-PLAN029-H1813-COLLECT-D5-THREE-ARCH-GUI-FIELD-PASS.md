# PLAN029 H1813｜收同源码 D5 三架构 10k 规则和 WinForms 真实可见配置

- SOURCE `e2b73dd8062a8a0ead22d6d58b689e9f04875882` [Action43567997223](https://github.com/lly8666/wbd-next/actions/runs/43567997223) 三OS (Windows2025/x64, Ubuntu/x64, Ubuntu/ARM64) **SUCCESS**；各真实本机 Rust 1.85.1 读取当前 `crates/wbd-engine/src/v4_client_split.rs` 生产实现本身，10/10 单测含10k域名 exact/suffix、10k非合并IPv4区间、IP/域名并集、活动flow pin语义。上轮 SOURCE b6e [Action43567463629](https://github.com/lly8666/wbd-next/actions/runs/43567463629) 全三OS已原始10/10通过，但错误 `grep 2 passed` 造成 Action FAIL：未抹掉该历史失败。本批恢复 >=10 且具名两项正例，三个同-source jobs 真绿。纯计算无 Win32 大规模 route/WFP 或 RAM/perf qualification。
- 同 SOURCE [Windows2025 GUI Action43567997254](https://github.com/lly8666/wbd-next/actions/runs/43567997254) **SUCCESS**：从 pinned donor 派生的 MainForm/fields 仅更新 CN option/hint，不改 donor；真实 WinForms RouteMode ComboBox 显示“局域网、中国IP与域名并集直连”，提示QNAME/单DNS。Go/Rust 有效配置 readback：CN/all切换、两个DNS各一、Direct quota拒绝超限、Game4 config、外层1460/自动只读内层与存储重开。原始输出含 `CN_visible_dropdown_option_IP_domain_union`、`CN_route_mode_hint_explicit_single_dns_direction`。未点击 GUI 连接签名Wintun，不是实际 OS Applied。
- 两项 evidence 各自源码锁、限定 status（规则 BUILD_PASS、WinForms配置 FUNCTIONAL_PASS）；029验收仍需真实 GUI-origin 业务和 Stop、P1/P2、IPv6及 Game4 分流接线，不把一处绿说成全功能退出。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback"],"reason":"Collect two exact-source H1812 D5 Actions: genuine native three-architecture pure 10k classifier, and real WinForms visible CN IP+domain/QNAME plus current Go/Rust effective config; keep signed GUI and performance NOT_RUN."}
```
