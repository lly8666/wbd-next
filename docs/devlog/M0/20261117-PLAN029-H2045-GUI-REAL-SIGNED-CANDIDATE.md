# PLAN029 H2045｜原 GUI 真按钮 + 正式 Go/Rust 原生双出口候选（实网待验）

- 新 C# STA 夹具**直接驱动当前源编译的原 WinForms**“保存配置/连接/断开”按钮，`ClientSession` 非假对象；实际子进程是同 SOURCE 原 Go EXE＋Rust DLL，真实 Npcap/Wintun 与 Linux WSL2 内核流量沿用原场景。真实 Go --check-config 读回默认外层1460/自动内层1389/单 DNS/CN，然后只有 `WBD_WINDOWS_OS_APPLIED`、真实 OS MTU readback、Go/Rust Ready 和 GUI 状态同时有回执才宣称连接。
- 由原 Windows/WSL2 应用证实真正的 Direct/Tunnel TCP/UDP 业务与双方 owned Stop；外部单场向 GUI stdin 发一次 stop，WinForms 按钮执行原 `ClientSession.StopAsync`，检查 WAL/路由/Defender sidecar 仅精确自身资源。仍不得把GUI父进程 CPU 统计写成 Go+Rust CPU。
- 单原生场景标记 `[plan029-real-gui-cn]`，同 VM/source 编译一次、严格独立于已通过的 H2041 Game4 和 H2031 padding。小额度具体资源满场景与 TC 物理联网仍另行核验。
- 之前 H2044 [Windows Go build](https://github.com/lly8666/wbd-next/actions/runs/43992993306) SUCCESS；H2044 功能卡 pretty JSON 超16KiB 造成纯治理FAIL，这批恢复 bounded compact JSON。**本批新增 GUI 真实场景 NOT_RUN，直到对应 SOURCE 原签名 Action 完成。**

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"Original actual WinForms GUI button and ClientSession signed Normal CN product scene, not fake GUI; future real receipts source scoped."}
```
