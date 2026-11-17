# PLAN029 H1969｜唯一一轮普通已建立TCP QPC实测（原 Wintun Rust / 真WSL2）
- 用户明确要求回归正常性能归因，不继续极端共享CDN同IP测试。当前原程序已编译同一 Win32 QPC 的 Rust owner及原Windows应用时间，2,048×1KiB/连接，32预热、一条先物理再Wintun Direct，真实Linux独立内核TCP46119，保留原Normal Tun/UDP、owned Stop。Linux时钟绝不与Windows相减。
- H1967 [Action43804163798](https://github.com/lly8666/wbd-next/actions/runs/43804163798) Windows/Linux Rust native pure component均 **PASS**；H1968 [Action43804399615](https://github.com/lly8666/wbd-next/actions/runs/43804399615) cheap语法及原分析器7条合成回归 PASS；H1968治理和Feature双PASS，满足发一轮网络实验的前置条件。
- 此commit仅作单场签名触发：`[plan029-v3-real-p2-rebuild]` 启动原 Go/Rust Wintun V3+WSL2内核场景，`[plan029-v3-real-p2-steady-qpc]` 单独使能 :46119的稳态QPC。**不含** bulk4MiB/ABBA/early-preconnect/small-first-SYN/128/high-rate等标记。正常产品提前建连OFF。
- H1969 Action和实测数值在本commit创建时 **NOT_RUN**；只从原 Action真实双 OS app回声、源锁Linux SHA、原Rust两腿QPC、原Windows客户端本地QPC及Stop联合验证后才报告p50/p95/p99。任何语法、缺1024B窗口、溢出、时钟频率/端口不一致必须FAIL，不得补造。
- 当前仪器化点是原Wintun owner `on_packet` 开始，尚未包括最初`ReadPacket`及RX owner`SendPacket`完成，不得将这一部分误称整个 Windows 内核收发开销；物理对照差值包含系统线程、TCP内核与不同路径。完整PLAN029仍IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Explicitly dispatch one source-locked signed original 2048x1KiB established-stream QPC Windows Wintun/Rust and WSL2 normal-load experiment after pure preflight passed; no new product or feature card change."}
```
