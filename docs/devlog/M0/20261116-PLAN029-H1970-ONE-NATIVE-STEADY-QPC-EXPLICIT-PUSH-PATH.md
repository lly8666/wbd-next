# PLAN029 H1970｜一轮普通2048x1KiB稳态QPC真原生 push 路径修正
- H1969 `a46e5f119a9007e9a2d86f4199a87b7b363d092f` 包含原签名`[plan029-v3-real-p2-rebuild]`+`[plan029-v3-real-p2-steady-qpc]`，但只有 `docs/devlog` 与 cursor 文件；`.github/workflows/m0-wl-public-normal-full.yml` 的 `on.push.paths` 不包括这些文件，故原 Win/WSL2 Action **未启动**，仅治理Action。本提交前不能说H1969做了实网验证。
- H1970只在**该原生工作流文件顶部加注释**，作为source-locked push path 的精确更改，同样两签名标记（新SOURCE）发原Windows2025+WSL2唯一一轮。原H1968测试7/7，H1967 Win/Linux Rust component PASS；原场景正常模式旧1MiB paced功能后续仅1条已建立的Direct TCP46119 + 1条物理基线各2048×1KiB，32条预热，原Linux两socket bytes/SHA和Rust QPC在owned Stop后联合。
- 严禁本Action无证据PASS、重复发送高率/4MiB/early-connect A/B或极端共享CDN同IP；普通产品preconnect OFF。真实 Windows `on_packet`→分类/NAT与内核两腿读写等待不等于完整 Windows内核CPU，尚缺ReadPacket前与RX SendPacket实际内核消费时间；Full PLAN029 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Force the previously requested one-source ordinary steady QPC original Win/WSL2 trial through its actual on.push.paths using only a workflow comment; no product, test algorithm, legacy policy or feature promotion changes."}
```
