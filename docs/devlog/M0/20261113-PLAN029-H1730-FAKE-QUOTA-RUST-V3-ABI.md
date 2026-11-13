# PLAN029 H1730｜DNS映射身份额度与独立Rust V3 ABI测试

- 同SOURCE H1729 `c090f9100081afdb74c5a3e4d0876bca455e285b` 原Go Windows source编译 [Action43396403923](https://github.com/lly8666/wbd-next/actions/runs/43396403923)、Windows/Linux Rust PLAN029组件 [Action43396403828](https://github.com/lly8666/wbd-next/actions/runs/43396403828)均**PASS_SCOPED**，无真实029出口。
- FakeIP身份表不属于Direct活跃flow配额：原代码以 `min(4096,direct_hard)` 给DNS候选设置硬上限，测试Hard=1会导致最多一个FakeIP。现改按需增长最多60000身份且16MiB字节预算；独立测试Direct hard=1仍能预留17个未公告DNS映射，不fsync就绝不宣布。
- Windows Rust V3 private probe冷ABI对照Go已有测试核对CIDR 8B、split 104B、V1 192B、V2 208B、V3 320B和指针偏移；本Action在Windows明确执行`m0_v4_probe plan029_`测试再编译DLL。Linux维持纯029测试；结果待本SOURCE Action。
- 仅probe编译，尚未将V3挂正式原Go；实际双DNS、kernel TCP、Defender、Stop、GUI Applied、padding、D1–D5/P1–P2仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Separate FakeIP identity quota from Direct flow count; validate Rust exact 64-bit V3 Go cold ABI in Windows probe scoped tests"}
```
