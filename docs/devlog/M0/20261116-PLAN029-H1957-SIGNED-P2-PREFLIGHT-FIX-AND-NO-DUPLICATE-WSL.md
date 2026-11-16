# PLAN029 H1957｜H1956 原生前门失败，只有两处测试夹具修复

- 固定 SOURCE `5aa5f66340f61b4fb001986e06642bf32d920b97` 的 [Action43792019825](https://github.com/lly8666/wbd-next/actions/runs/43792019825) **原 Windows/WSL2 native-public-two-os 未执行**，没有真实 QPC/4MiB/Stop 结果；cheap Python 的 H1849 静态保护测试拒绝把原 WSL `"p2abba" if ABBA else "p2ordinary"` 源码表达式替换成新混合三元条件。原服务端、底层 TCP、GUI 均无新原生 FAIL 证据。
- 同 SOURCE [governance Action43792019812](https://github.com/lly8666/wbd-next/actions/runs/43792019812) Governance 主 job PASS，但 Feature catalog 独立 job 的 H1956 positive new Python test ERROR：H1945/H1955 **合成**夹具只有384条 small QPC，H1956 误认为已有额外两条 cold/bulk，增加3条后写死 count389。应在384前新造 **1条冷 Direct +4条大 Direct**，真实旧384条 synthetic small 流不动；总389，ON 195；不能修改实网报告来掩盖错误。
- 本 H1957 修复：`mode_argv=["p2abba" if ABBA else "p2ordinary"]` 是真实旧原逻辑；只有准确 `PRECON_BULK` 显式门才覆写为 `p2preconnect4`，WSL argv6 仍严格比对，且原 Windows full assembly 单 SOURCE。新 fixture 显式追加5条独立虚拟冷/大流时间戳，不与30000..30383 原合成小流重叠。补丁**不改 Rust 的物理连接策略，不改 OS/WAL、入口和产品默认**。
- H1956 原始失败 devlog/Action 留存，不拿 green cheap 当网络通过；只允许修好后的 H1957 一个源锁原 4x4MiB ON/OFF/OFF/ON+384小流+Tunnel UDP+owned Stop，结果再决策是否产品开启早连。
- 功能卡原 H1955 真原生证据、P1 CPU、H1953 QPC、D1–D5/GUI/Game4/IPv6 退出状态不修改。

```feature-impact
{"kind":"none","reason":"Only restore pre-existing source-locked P2 workload argv contract and correct a pure synthetic H1956 unit fixture after cheap gates; original product runtime and feature verification state remain unchanged."}
```
