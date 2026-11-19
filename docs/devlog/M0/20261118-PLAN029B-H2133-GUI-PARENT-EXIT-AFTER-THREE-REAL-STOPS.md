# PLAN029B H2133｜真三代 GUI 三次 Stop 全完成，原 WinForms 父进程退出仍为硬门

- H2129 原 [Action44195727026](https://github.com/lly8666/wbd-next/actions/runs/44195727026)，SOURCE `43f988d37edcb54e537b14d2f5a73aab4d6609fd` 整体 **FAIL**，原生 ZIP `14379488033` SHA256 `c9fc9d6fa4a44151ad57c76d5336bcf994ccf87c150c8e2aee5dfc6ec688cc53`、28成员CRC全PASS、原产品/夹具来源同源。
- 与H2128不同，现已三次真正 WinForms按钮 Connect、系统 Applied、DNS、应用UDP echo，首代高级物理CN+FakeIP Direct、二代普通物理CN+真A Tunnel、三代 all Tunnel DNS+真A Tunnel；三代原 Go/Rust TLS 41031/41032/41033、内层OS MTU1389/外层1460/MSS1420，Linux真内核DNS+业务6项、旧FakeIP出包0。三次 `M0_PLAN027_NATIVE_STOP_RESULT ... PASS` + `WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1` + `PLAN029B_B4_REAL_GUI_OWNED_STOP_WAL_CLEAN`，最后显示 `PLAN029B_B4_THREE_REAL_GUI_GENERATIONS_AND_STOPS_COMPLETE`。真实 Win→Linux TCP 与原UDP业务亦PASS，原Linux共享TUN最后已Drain。
- **仍不能称整轮PASS**：原 Python supervisor `stop_windows(w)` 后因 `w.returncode !=0` 或未能取得最终母进程自然退出而落入通用 `Windows native owned WAL Stop missing`；虽然源端已有全部Stop/WAL标记，外层 `report.stop` 仍 NOT_RUN。原因未由当前原始日志区分父进程非零退出/超时强终止，不能伪造0退出。
- [H2133 SOURCE ec49461](https://github.com/lly8666/wbd-next/commit/ec49461fc40fd2816ef90ee04c6060ea41c9c984) 在三次真实 Stop 后、最终成功回执前，在 GUI 原主线程核 `client.Active=false` 与 `state=未连接`，排队事件处理后真正 `form.Close()`，必须 `IsDisposed`，不能通过跳过退出硬门。只改签名B4 C#夹具+廉价断言，原 Rust/Go/Wintun/Stop、Game/FEC/repair不改。新 [Action44198794225](https://github.com/lly8666/wbd-next/actions/runs/44198794225) 收集时尚在运行，不能算PASS。
- Game4 独立 [Action44197717052](https://github.com/lly8666/wbd-next/actions/runs/44197717052) 源 `5fc22aef30aa4440e81257e67fded501fece3080` 仍独立执行；Game2分流真入口明确拒绝，无真业务PASS。B5同VM≤10Mbps CPU/GiB/RSS/p99 **NOT_RUN**，029/029B OPEN，030未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"H2133 only closes genuine original WinForms form after all authenticated owned Stops, before emitting B4 final receipt; no production runtime/feature semantics modified."}
```
