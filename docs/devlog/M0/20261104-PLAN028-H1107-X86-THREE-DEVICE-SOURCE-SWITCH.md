# PLAN028 H1107 — x86 双端，三设备真实切网期间持续业务

复用标准TLS、离线32B route-key、原 Go/Rust 已编译 x86_64 SOURCE `0e47d9c9532cbda9e655bd198348acf4ff4ddcd1` 的 [Action 41782228876](https://github.com/lly8666/wbd-next/actions/runs/41782228876) 工件，逐一核 ELF 和SHA256，不重编产品。仅新建一份独立扩展原五 netns 测试夹具（默认旧工具文件不修改），一Action一个场景。

原认证共享server443/Rust TUN的Alice设备A、Alice独立安装D、Bob三条 /32 同时工作。B/D各24个真实UDP回显须**贯穿**A真实kernel route/source IPv4 10.25.0.2→10.25.0.9与出口MTU1500→1280；A在新原TLS认证后保留 /32、内层TUN MTU自动缩小并OS读回、新代5个真实UDP、旧Rust精确Stop。B/D隧道MTU不改、用户账号/IP不串。留OS route JSON、首包阶段钟点和三端Rust Stop。时间只报告物理变化命令→新代READY与READY→完成5 echo，通知到TLS和CPU/p99暂无精确资格，不填假数。

仍为 SOURCE_CANDIDATE，新原生 Action 未过不能宣称完成。下个完整Linux任务按用户规定轮换原生ARM64双端；Windows真物理NIC/Npcap切网和Android独立未测。H998旧同连接热缩FAIL、旧ARM64 Game4FEC FAIL、remote ICMP、CPU因果未证保持原样。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1107 source-locked x86 original Go/Rust native physical source4 change while other Alice installation and Bob continuously send authentic UDP; proof pending."}
```
