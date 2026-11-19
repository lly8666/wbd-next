# PLAN029B H2108｜真实IPv6 /128发送与Wintun原生源锁复验（入场）

**准入源：**`5a80e0ea8e027f5b7649042ef988ef9bb2c51838`。H2107 [Action44101072122](https://github.com/lly8666/wbd-next/actions/runs/44101072122) 的 Windows Rust 单元416 PASS / R2集成11 PASS、Windows Go、Linux Rust、原Go/Linux Rust source build均PASS；关键是新增 **Windows release `m0_v4_probe` feature** `cargo check` PASS，堵住 H2106 release E0004 的三处PLAN029旧诊断接线遗漏。原签名诊断 [UDP44101072346](https://github.com/lly8666/wbd-next/actions/runs/44101072346)、[TCP44101072126](https://github.com/lly8666/wbd-next/actions/runs/44101072126)、[CN DNS44101072359](https://github.com/lly8666/wbd-next/actions/runs/44101072359) 独立Action结论 SUCCESS，非B3新IPv6实包资格。真实原Windows/Rust release并行Normal/off Action44101072122中的原生job在捕获时仍运行，保留真实终结结果，不跨SOURCE/VM归功。

本次携带 **唯一** `[plan029b-b3-ipv6-real]` 的 B3 Windows2025 真签名Normal/off场景请求。测试契约再次锁定 16 个真实Windows `AF_INET6` UDP sendto至仅测试自有`fd73:29b:2026::1/128`Wintun精准路由、原Rust同owner首字节IPv6 drop总数≥16、穿插12个真实IPv4 Windows→Linux TUN UDP echo、必需的原TLS/WAL/Stop；测试finally严格清理本SOURCE/ifindex拥有的目的路线与源IPv6地址。若无实际IPv6绑定、路由、发送、Wintun计数或Stop，报告真实首错FAIL或NOT_RUN。普通AAAA NOERROR/NODATA已有旧SOURCE回执，不可替代B3真包。**这只证明测试own /128受管路径，不涵盖physical-bound/onlink与全主机IPv6安全**。H2108只补一条测试静态反误报断言，不改产品Rust/Go/IPv6行为；签名真结论待Action原ZIP核验。

029B B4高级→普通→all多代真实GUI/Stop、B5配对同VM<=10Mbps CPU/GiB/尾延迟均未完成；不重开028或030。

```feature-impact
{"kind":"none","ids":[],"reason":"H2108 only freezes one actual B3 signed scoped /128 IPv6 original Wintun test with extra global-host nonclaim assertion; native result NOT_RUN before Action"}
```
