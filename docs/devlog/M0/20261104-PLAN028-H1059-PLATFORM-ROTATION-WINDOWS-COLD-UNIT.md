# PLAN028 H1059｜Linux 平台轮换口径修正、Windows 冷切网单测

2026-11-04 用户更正：所谓 Linux 交叉测试是**按完整任务轮换整套同架构 client+server**。本次 x86_64 双端，下一次 ARM64 双端，依此交替；Windows 任务独立，不计入该轮换。不要再做不必要的 ARM↔x86 异构强制矩阵；H1053–H1055 QEMU-user 历史 FAIL 保留，但不继续扩测。H1057 原生 ARM64 Normal 双端 PASS 仍为有效限定场景。

H1058 原 SOURCE `ec09e5178ca299fde4e3a746495e6e9583ee1bb1`：Windows/Go/Rust/Wintun/WAL [Action 41671643624](https://github.com/lly8666/wbd-next/actions/runs/41671643624) SUCCESS，Normal/Auto/Fixed/Game2/Game4 限定原生 PASS；Windows/Linux [Action 41671643589](https://github.com/lly8666/wbd-next/actions/runs/41671643589) SUCCESS；治理 [41671643759](https://github.com/lly8666/wbd-next/actions/runs/41671643759) SUCCESS。但 H1058 新增的三条 Windows pre-READY 切网、Stop、认证拒绝单元测试先前仅编译，原 Win WAL CI `-run` 只执行 PLAN023/025/026。H1059 只新加一个 Windows Go SOURCE 精确组装/五条冷控制 unit 的小 Action，不再跑原五模式驱动场景。单测 PASS 也不能冒充 Windows 实际 NIC/IP 改变和重认证首包 PASS。

旧 H998 在线MTU缩窄 FAIL、ARM64 Game4FEC Action FAIL、QEMU mixed UDP FAIL、远端ICMP未测、CPU因果未证均保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1059 user clarifies alternate whole Linux same-ISA client/server task x86 then ARM; exact Windows pre-READY change unit tests run instead of compile-only."}
```

## H1060 工具故障窄修

首个源锁 Windows Go 单测 Action [41675780906](https://github.com/lly8666/wbd-next/actions/runs/41675780906) 在原 Go assembly 前的 manifest JSON 读取中被 Windows Python 默认 cp1252 UnicodeDecodeError 阻断，五个 Go 测试未运行，不能报告 UNIT PASS。只更改测试 workflow 的 read_text(encoding="utf-8")，不碰产品 Rust/Go、源锁 bytes、不重启 Wintun 五模式。
