# PLAN028 H1527｜双端 Linux 200ms / 100–150 Mbps 真实 600 秒验收

- Native source `9b2605538d9e05af5b0c2a93bc7a7bc8495ed8da`，两个原 Go/Rust 原生 Linux x86 独立 Runner 六 netns，5 模式、TLS443、真双向 TCP/UDP、200ms/方向、0%/30%，真实 `tc` 10 秒完整外层两方向合计速率。原生程序/10s内核读数/容量守护均退出码0，六个独立 owned Stop 确认，未发生秒级活跃收件空洞。原始 ZIP 永存，不抹掉原 Action FAIL。
- loss0 原 Action [42781585712](https://github.com/lly8666/wbd-next/actions/runs/42781585712) ZIP13747485465，实际外层 **185.352 Mbps**，目标 **FAIL_OVERSHOOT**；双向业务、无无效/重复、Normal、Game、旧代及最终 Stop **PASS_SCOPED**，源负载35 Mbps/方向过高。
- loss30 原 Action [42781585834](https://github.com/lly8666/wbd-next/actions/runs/42781585834) ZIP13746917073，外层**136.511 Mbps**，41+有效窗中39/42个落在100–150 Mbps，全部业务、交接、Stop **PASS_SCOPED**。原 `RECOVERY_DELIVERY_BELOW_95PCT` 在全程保持30% netem 的窗口不能解释为撤损恢复 FAIL。
- 原 H1274 reporter 误只算服务端首次 `V4_PUBLIC_MIXED_NORMAL_READY`，漏掉 B 的 `V4_PUBLIC_MIXED_NORMAL_B_PENDING`→经过真实认证 Health→`V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY`。独立 [H1525 原始 ZIP 离线验证](https://github.com/lly8666/wbd-next/actions/runs/42784346466) 逐个按唯一真实 TCP源端口核对、无 B_REJECT：loss0 Alice6/Bob5/Erin5；loss30 Alice6/Bob5/Erin4。两个离线 jobs均 success，原始两个 FAIL 保留但这些错因属 reporter，不是产品失败。不重跑30%。
- 容量标定下一 0% 一场建议内层每方向从35Mbps降为26Mbps，按原实际外层185.352×26/35≈137.7Mbps。该档尚 **NOT_RUN**，必须用内核字节回读决定，不保证理论目标。
- Windows [42782566007](https://github.com/lly8666/wbd-next/actions/runs/42782566007) ZIP13747736171，已修复诊断 cp1252 首错丢失，真实新首错发生在 TLS前：父级 Action 已凭收据 `plan028-owned-alias.json` Prepare WSL host源198.19.254.1，H1506五客户端夹具拿不同的 `h1506-owned-alias.json` 再次 Prepare，被正确拒绝 `owned source already in use`；且原别名清理收据失败。这是明确的测试所有权重复接线缺口，Windows 业务 **NOT_RUN**、清理 **UNVERIFIED**，不可因 Linux PASS 判 Windows PASS。下一步只允许复用已有真实来源/收据、精确 Stop/OS清理，不移除第三方路由保护。
- Android/物理WAN **NOT_RUN**；028 **IN_PROGRESS**。

```feature-impact
{"kind":"none","reason":"Only records native Linux substantive scoped PASS after exact immutable original log replay and separates current Windows pre-TLS harness alias owner failure; no protocol or feature changes.","ids":[]}
```
