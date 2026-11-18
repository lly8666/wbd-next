# H2205｜H2204 V4v2 WinGUI驱动控制与ARM64同源交付、main集成

用户明确要求将已测新功能与修复合入main并维护项目记录。原main `c04d5eefd47b672b30e531b21da763bfcf7a91f9`；本次QA验收SOURCE `5ad409d1f5fe664a4030eec149a98882f88108f8`，产品协议Rust/TLS核心与main相同。此前旧GUI正例与测试器曾有重复字段、退役dns4/checkbox、异步WinExe自检退出错判：历史失败留存；已修复并用实际JSON PASS而非只看工作流绿色。

- [完整原生Action 44343862449](https://github.com/lly8666/wbd-next/actions/runs/44343862449) 两job SUCCESS：Windows2025 x64原Go/Rust ISA-L/WinForms/wintun官方签名pin；Linux原生aarch64 12场TLS V4扩展v2、TCP/UDP、AF_PACKET/TUN、Stop PASS_SCOPED。原ZIP artifacts Windows 14445671783、ARM64 14445087673。
- [WinForms独立409项自检 44343852130](https://github.com/lly8666/wbd-next/actions/runs/44343852130) PASS、进程exit0。UI增加“Npcap 官方下载”及“Npcap 安装（本地官方包）”，仅用户从官网取得原厂有签名安装器后才交互启动；Wintun“驱动安装”仅固定官方sha256且单独创建/撤销临时WBD-Setup网卡。CI测试的是可见按钮/拒绝场景，**并未真正调用驱动安装**。
- 旧QA SOURCE `74343dff94bfef321eda84306ea35c98f264146e`：Windows2025签名Npcap/Wintun↔Linux WSL2 Normal GUI重连 [44334462936](https://github.com/lly8666/wbd-next/actions/runs/44334462936)、Game2原生 [44334470304](https://github.com/lly8666/wbd-next/actions/runs/44334470304) 各自PASS_SCOPED，不是假装成最终GUI安装按钮同源双端联测。
- 发行脚本固定Wintun DLL SHA与源清单，Windows zip改严格白名单并排除CI自检测试用户/密钥资料、残留 profiles/data 与退役旧PowerShell网络脚本；Npcap Free安装包受分发许可约束绝不内置。
- 未覆盖：用户物理机Npcap安装、Wintun临时PnP按钮点击、Windows实体×独立ARM64实体、公众WAN/DPI/CPU/p99及PLAN029整体退出；分别保持NOT_RUN或OPEN。未改原始TLS first-flight或Steady Rust hot path、route-key线材与NAT语义，旧失败不销账。

证据记录：[H2205机读验收](../evidence/M0/PLAN029B-H2205-H2204-WIN-GUI-DRIVERS-ARM64-SCOPED-RELEASE-20261118.json)。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback"],"reason":"H2205 WinForms新增Npcap官方下载+校验签名交互安装、Wintun固定哈希owned临时PNP按钮、v2 fill全模式UI修复；H2204 x64 GUI 409真实检查与ARM64 native 12场各自独立验收，安装执行和实体跨ISA未验。"}
```
