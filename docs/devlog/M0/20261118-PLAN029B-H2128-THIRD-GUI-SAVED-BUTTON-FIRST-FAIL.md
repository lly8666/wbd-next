# PLAN029B H2128｜签名第三代 GUI 重复点击已保存且禁用的“保存配置”首错

- 旧 [Action44153223434](https://github.com/lly8666/wbd-next/actions/runs/44153223434)，SOURCE `cde9e7921737aad6f332a10fb738e2a4d764e9dd` 整体 **FAIL**；原始 ZIP `14359994122` SHA256 `b3062c96d61b154c36f111fa06db8246988ad5879e688bbb0f84cd1362b0fc64`，26成员CRC全部PASS，原装配源一致。cheap、Windows Go/Rust、Linux Rust、原 Go/Rust Release 构建均通过。
- 原始 WinForms 第1代高级 CN 与第2代普通 CN：各自真实 Windows OS Applied，物理 CN DNS、真业务 UDP、owned Stop/WAL恢复 PASS；第二代旧FakeIP应用无回复。第三代还**没有真实 Connect/OS Applied/业务/Stop**，首错是 `PLAN029B_B4_FIRST_FAILURE IOException ... real WinForms button unavailable 保存配置`。无 Rust/Go 热路径错误证据。
- 读调用链：第2/3代在 `form.LoadEditor/SetEditor/SaveEditor()` 完成原始本地持久化，且 `Effective(...)` 经同源原 Go `ValidateAsync` 严格检查后，`Connect()` 又无条件点击 `保存配置`。第三代 `all` 已保存无编辑待提交，按钮不可用，重复点击是夹具 bug。
- [H2129 SOURCE 43f988d](https://github.com/lly8666/wbd-next/commit/43f988d37edcb54e537b14d2f5a73aab4d6609fd) 仅修原 B4 C# 夹具和静态门：第一代继续真 Save 按钮，第二/三代沿原 `SaveEditor` + 实际原 Go effective，三代仍须真 `连接 / 切换` 和 `断开连接`、真实 Win2025/Wintun/DNS/业务/Stop，最多2.2s等异步原 WinForms button Enabled；禁用直接fail-closed，不造任何回执。不修改 Go/Rust、TCP/FEC/repair/wire。
- 新 [Action44195727026](https://github.com/lly8666/wbd-next/actions/runs/44195727026) 收集时 cheap **PASS**，native 不得提前晋升。后续仅收实际 SOURCE 43f、三代 original WinForms/MSS/Stop+Go/Rust hash/CRC 和整个 CI job 结果；如新事实继续针对首错，不重新跑 B0–B3。
- B4当前整体未通过，Game2/4与B5同VM≤10Mbps CPU/实际GiB/RSS/p99均 **NOT_RUN**，029/029B OPEN，030未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"H2129 strictly repairs test-only duplicate disabled original WinForms Save button in B4 cold GUI fixture, not a product runtime or published feature change."}
```
