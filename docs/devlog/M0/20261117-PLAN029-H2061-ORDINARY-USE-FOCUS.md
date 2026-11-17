# PLAN029 H2061｜用户限定日常工况：真实GUI两代普通Disconnect→Connect

- **已通过**：H2059原Win2025/WSL2 [Action44005631732](https://github.com/lly8666/wbd-next/actions/runs/44005631732) SOURCE `ccf0cb22d469bd4fd2fc07234d87ff5c339321df`，manifest`exit_code=0 product_pass=true`；原WinForms`startup-padding=flows`经原Go `--check-config`effective，再由原Rust M1/Npcap发`copied_records=41 copied_bytes=11466`真实回执；默认1460外层/OS1389内层、CN物理Direct UDP/TCP32KiB、非CN Tunnel UDP/TCP、双方owned Stop。独立H2031物理加密录包没有重跑；原GUI off H2055也已通过。单侧Go/Rust进程CPU RSS未采样，不冒充AB证据。
- **本源码新增唯一普通回归**：同一 WinForms 用户按钮先Connect并见原Go/Rust OS Applied，直接按“断开连接”，等待第一个原Go child真实退出、原owned WAL/route/Defender sidecar全无，然后再按“连接 / 切换”，**第二个**独立Go/Rust原TLS/Wintun/OS Applied读回外层1460内层1389；现有双系统原生应用继续测第二代CN Direct TCP/UDP、Tunnel TCP/UDP与最后Stop。明确2次 READY/OS Applied/MTU、2次`M0_PLAN027_NATIVE_STOP_RESULT PASS`与2次`WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1`，双方Stop相同SOURCE。无人工灾难注入、无慢盘、无线索系统DNS备选。
- 新场景只在workflow commit同时含`[plan029-real-gui-cn]`和`[plan029-h2061-normal-reconnect]`启用，仍旧**只发一个独立原生Normal场**。与H2059 flows仅一场不能混跑；默认off。原LINUX/Windows两个内核普通UDP生成器在两个UI会话间继续运行，为等待第二次READY适度延长其**总测试存活上限**而不增加每秒负载，原程序各类超时不修改。产品业务探针仍只在第二个原OS READY之后验收。
- **未承诺**：二代服务器域名物理DNS TC专项不是本次IP字面值普通GUI重连的测试目标；H2056第一代TC已有实网PASS。用户排除高强度压力、突然崩溃、长CPU-RSS AB/IPv6旧矩阵，单项历史状态保留`NOT_RUN`。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","startup-flow-padding"],"reason":"Source-locked H2059 real GUI flows effective M1 NPF PASS; focus one ordinary WinForms Disconnect->Connect OS Applied/real direct+tunnel Stop, no extreme testing."}
```
