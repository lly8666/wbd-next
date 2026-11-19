# PLAN029B H2124｜原签名 B4 首个 Linux DNS 非预期票据，单点有界诊断

- H2123 [Action 44138696793](https://github.com/lly8666/wbd-next/actions/runs/44138696793)，SOURCE `7269b71ec2421868b5a45c0af4f1d1475a262c04` **FAIL**。原始 ZIP `14354147838` SHA256 `8b9dea0dcaf736deab8c81c527a57fb5c743f1e0acf7596e35851b18c1f7793e`。实际 WinForms 首代原 Go/Rust TLS/Wintun OS Applied/Ready、内核 UDP 正常交换；Windows 首次 CN A 收 `SERVFAIL/RCODE2/ANCOUNT0`。新的 WSL2 原 guest 日志第一次确证 `B4 unexpected DNS ticket or physical fallback` 后退出；Linux server 和 Windows Rust owned Stop/WAL 恢复真实通过。**第二、三代未执行**。
- 原因未确认是不同 DNS 票据/原 OS 流量/物理出口错误，不能靠忽略任意物理 DNS 帧修“绿灯”。本 SOURCE 仅改原 B4 Linux guest 的一个失败分支：打印一次 `PLAN029B_B4_FIRST_UNEXPECTED_DNS`，包含真实物理/TUN、端口、DNS ID/flags/qdcount、匹配预期CN问题的布尔值、问题 SHA256 截断值（无原QNAME/报文）、已接收代际；随后仍失败关闭。允许的外来 OS Tunnel 查询仍须真实 TUN 源、有效单问题、非本次 CN 问题、最多 12 次；物理异常不容忍。补廉价静态回归门，产品 TCP/FIN/FEC/wire、FakeIP、Go/Rust 不改。
- [新签名 Action 44144504089](https://github.com/lly8666/wbd-next/actions/runs/44144504089) SOURCE `c0f5cdf2610cbfb6c103bc1cf51bf1c949f47314`：收集时廉价检查 PASS，其余原生产组件/真实签名 **IN_PROGRESS/NOT_RUN_TO_COMPLETION**，不得提前晋级。若同失败两轮且没有新资料，停止刷验，定位此首上游包。B4、Game、B5 和 029/029B 均 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"H2124 only bounds first genuine WSL2 B4 DNS ticket fault and static guard; no runtime or product release qualification."}
```
