# PLAN029 H1761｜收H1760签名原生失败：旧ProductApplied常假阻断冷TCP

- [H1760 Action43448922365](https://github.com/lly8666/wbd-next/actions/runs/43448922365) [日志产物](https://github.com/lly8666/wbd-next/actions/runs/43448922365/artifacts/14050277121)：Go/Rust构建、签名Npcap/Wintun、真实TLS、Rust RX/TX、MTU1329成功。首错在Ready之前：`PLAN029 post-Apply TCP PREPARE: original-Go private Windows Rust owner refused`。Stop打印旧原生`wal_kernel_crypto PASS`，但Direct TCP/DNS/UDP应用并未跑；不得当作029实网PASS。
- 根因源可静态证实：`bridge_v4_windows_scoped_client.go`的`OriginalOwnerReadback`把旧设备`ProductApplied`恒置`false`。H1759新增PREPARE与ENABLE却要求它`true`。真实新产品OS证明实际来自`product.Apply`和`product.LiveReceipt`，已由外层同次会话读回，不能为绕过死锁伪造旧状态。
- H1761在两处冷控制采用原鉴权活跃、当前Wintun已绑定、未quiesce、非server检查；原Rust epoch/LUID/generation、Defender精确owned Allow后ENABLE、失败owned Stop不变。加Go纯回归及manifest双Git blob源锁；一签名Normal既有工作流自动运行，SOURCE结果待证。保留H1760 FAIL，D1-D5/P1-P2/padding/GUI未完成。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1760 real pre-Ready failed legacy Applied gate; H1761 narrowly corrects with N4 real receipt unchanged"}
```
