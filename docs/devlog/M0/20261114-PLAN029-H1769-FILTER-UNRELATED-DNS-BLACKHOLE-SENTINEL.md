# PLAN029 H1769｜H1768已跑真实DNS黑洞，但物理零回退尚未证明

- [H1768签名 Action43526475121](https://github.com/lly8666/wbd-next/actions/runs/43526475121) 来源`9f4b2488e77274a8e2124a13fbbd4877f2142cc4` 原始Go/TLS/Rust Windows Wintun↔Linux TUN：CN DNS/FakeIP/物理Direct UDP、32KiB双腿Direct TCP+FIN、Tunnel TCP/UDP、非CN单Tunnel DNS正向均在新D1反例之前打印真实PASS；随后独立Linux黑洞脚本已在1.1.1.1:53(TUN)及peer:53(物理)绑定/Ready，却因 **收到不属于指定测试QNAME的DNS包** 按过严的`query[12:]==expected`立即报`RuntimeError: blackhole fixture received unexpected query ID/QNAME/shape`。Windows真Wintun原生应用发3个`no-backup.globalx.example`请求、未收到回应。当前**DNS物理零回退不可判定**：7秒物理哨兵观察未完成。整个Action原判FAIL、不补假PASS、Stop未到达正常签名阶段。
- H1769修复**夹具**：保持Linux物理/Tunnel双socket及整7秒窗口，按DNS message原QNAME+QTYPE+QCLASS在offset12精准筛选指定`no-backup.globalx.example`；EDNS附加字段可存在。其他原始Go bootstrap/CN/系统DNS包单独计`unrelated_query_count`，不得提前终止或算作目标回退。**指定QNAME落在物理端哪怕一个就FAIL**，Tunnel需至少2个、来源须原lease4，Windows不得意外收到响应，双OS Stop必须继续通过。不引新resolver、不增加线程或WFP。
- [H1768 Windows 原始owner ABI Action43526475111](https://github.com/lly8666/wbd-next/actions/runs/43526475111)另有旧pinned Go/M4装配`exact pinned old-Go/M4 assembly already owns this file`归属断言FAIL，同类错误已存在于 **H1766** [Action43524163017](https://github.com/lly8666/wbd-next/actions/runs/43524163017)。与本次签名产品DNS首错不同，不能随意放开装配覆盖断言；该独立legacy来源冲突仍OPEN。
- H1769只锁新SOURCE运行**一**个已有签名Normal场景。H1768 Rust Windows/Linux、Go和治理已PASS；其原M1可选AEAD-padding仍未有CLI/GUI/实际Tunnel调用，D1 TCP53、D2–D5/P1–P2保持OPEN，PLAN030未启动。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1768 signed negative D1 fixture observed unrelated DNS and prematurely failed, target-only filter staged without weakening zero Direct fallback; old pinned Go/M4 owner ABI remains independently unresolved"}
```
