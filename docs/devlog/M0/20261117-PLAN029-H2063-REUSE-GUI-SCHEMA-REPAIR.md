# PLAN029 H2063｜复用原生二进制的 GUI schema 缺席，定向修复

- H2062 同一 fixture SOURCE `31a9d2a8` 三条独立原生 Action 均完成真实 Windows driver、原 Go/Rust Windows/WSL Linux 两侧二进制 SHA 核验及 Ubuntu WSL2 TUN；**真 GUI Connect 尚未执行**，所以不声称用户产品联网失败。
- 第一条一模一样的边界：`tools/m0_plan029_gui_real_bridge.py:59 original Go client flag absent from real GUI schema route-key-hex-file`。下载各自原始 ZIP 确认：GUI [44013733723](https://github.com/lly8666/wbd-next/actions/runs/44013733723) artifact14297727935、domain [44013739000](https://github.com/lly8666/wbd-next/actions/runs/44013739000) artifact14298585486、TTL [44013744250](https://github.com/lly8666/wbd-next/actions/runs/44013744250) artifact14297977678，`report.json.mode_public=FAIL_TRUE_PUBLIC_EXECUTION` 但 `windows_ready/linux_ready/app_duplex/tcp_duplex/stop=NOT_RUN`。
- 原 H2059 成功源码当时执行了 `python tools/prepare_windows_wiring.py`；本 H2062 为复用已编译 Go/Rust 产品跳过构建时，把同时负责**旧 donor WinForms 字段目录组装**的步骤也跳过。此次在重用分支单独执行现有精确源校验 assembler，只恢复 `legacy/windows/gui/fields.json` 等 GUI donor 输入；不重编产品、不改变旧 EXE/DLL/Linux SO 字节，留原架构保护。此为测试夹具修复，非 WFP/Direct/DNS 产品修复。
- 一次修正提交触发 3 个不同 Runner 原生场景；旧 31a9 三条失败保留，已排除压力/强制中断/慢盘，不能因为 Action 名称和 manifest 绿而称通过。完整双出口/Stop 和第二代 DNS/TTL 均须真业务收据，若下次失败仅定位新边界。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","client-domain-bootstrap","dns-split-ipv6"],"reason":"H2062 original signed first three native fail at prestart GUI schema with reused binary, no product business; scoped exact donor assembler correction"}
```
