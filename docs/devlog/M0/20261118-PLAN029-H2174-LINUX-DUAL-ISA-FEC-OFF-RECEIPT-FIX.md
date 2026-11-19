# H2174｜Linux双原生ISA Normal业务已真PASS，汇总模式空值首错

[H2173 Action44255699692](https://github.com/lly8666/wbd-next/actions/runs/44255699692)两独立Ubuntu原生x86_64及aarch64作业真实构建Go TLS客户端/服务端+Rust/ISA-L+原TUN；Normal 的原脚本exit0，原始客户端→服务端、服务端→客户端**普通内核UDP与TCP socket echo均通过**，双方TUN双向ICMP、物理外层1460及内层MTU/DF边界、仅两自建TUN的disable_ipv6=1、真实owned Stop/namespace clean均PASS；不是模拟包。原产物x86 artifact `14406001830`，ARM artifact `14405314056`，同SOURCE `8442d1c7253d235549f6f0f706346f839594edf9`。

然而两Action整体FAIL：真实原`arm64_linux_netns_smoke.sh`在没有Game FEC时返回`"game_fec_profile":""`，新Python suite校验器却误将非FEC预期写成`"off"`。对照两份真实`receipt.json`确认所有其它条件满足且两脚本实际exit0；此为测试汇总假阴性，不是产品FEC错误。H2174只将汇总器预期改为`(fec or "")`，仍对Game4 fixed6严格要求`"6"`，不忽略字段、不放松网络/TCP/UDP/MTU/Stop门槛；在静态单测中加同一严约束避免回归。失败历史保留，不能把Normal-only H2173视为其它4模式PASS。

执行两个原生ISA各五短模式，不重跑历史Win/028/性能矩阵；原Go/Rust产品源码和CI内核网络条款不变。完整029/029B技术OPEN，030未启动。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix source-locked native Linux suite exact FEC-off JSON selector from invented 'off' to actual empty string, retain explicit fixed6 enforcement and add regression assertion; no product changes."}
```
