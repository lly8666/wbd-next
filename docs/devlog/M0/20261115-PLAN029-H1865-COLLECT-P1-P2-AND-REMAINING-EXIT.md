# PLAN029 H1865｜收齐真实P1/P2，同步cursor和功能卡，不重复网络测试

- main SOURCE `88a263086613fdb0231f5fc608be7f6d13a313ce`。 [H1863 P1 真Win/WSL2 Action43617979644](https://github.com/lly8666/wbd-next/actions/runs/43617979644)：同VM、同EXE/DLL SHA、顺序A=V4 original Tunnel/off与B=V3 all Tunnel/on，各60秒/50Mbps/约0.6984GiB独特交付，两个真实owned Stop PASS。A CPU/GiB21.0525、B22.5293，增**7.01%**（CPU时间差1.0313秒/60秒约0.0172核）；Windows UDP p99 47→62ms、最长空洞47→46ms，RSS峰42.36→41.48MB。P1业务PASS_SCOPED、性能OPEN：V4/V3后端不同，驱动CPU和最老用户队列年龄未单独测，不能宣称额外CPU全来自分流。证据 docs/evidence/M0/PLAN029-H1865-H1863-SIGNED-P1-20261115.json（该文件绑定当次H1863 SOURCE `b940e538`，不混入current cursor evidence_refs）。
- [H1864 P2 真Win/WSL2 Action43618374849](https://github.com/lly8666/wbd-next/actions/runs/43618374849)：原16KiB分块但无人工发送sleep的4MiB完整SHA/FIN，物理基线32.155ms、FakeIP Direct131.544ms（+99.389ms，4.091倍），小Tunnel UDP120/120、完整覆盖Direct、p99 RTT2.14ms、最大空洞34.371ms，两个真实owned Stop PASS。P2业务和跨流进展PASS_SCOPED，额外延迟/CPU归因及峰值仍OPEN。证据 docs/evidence/M0/PLAN029-H1865-H1864-SIGNED-UNPACED-P2-20261115.json，当前cursor source lock H1864。
- H1850/H1851 38秒超时、H1862 `FragmentKey`编译失败、H1859旧P1 CPU+18.04%均历史保留；H1856修Npcap后节奏1MiB Direct328ms/物理281ms亦保留，**不同负载/VM不是精确算法A/B**。
- 检查当前纯Tunnel V3逻辑：`v4_client_split_wire.rs`已具`plain_all_tunnel`普通DATA快路，不调用FlowPin；不能把P1 +7.01%直接归因逐包DNS/trie或重复增加同一种fast path。
- 本批只更新证据/功能卡/cursor，未重新dispatch P1/P2、未开启030、未扩大028。下一批独立D4 IPv6真实OS覆盖/owned恢复、GUI真Connect/Stop、Game4 CN、DNS残项及资源压力继续OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect current-source H1864 unpaced real 4MiB P2 and separate H1863 same-VM Tunnel P1 with real performance limits; preserve earlier FAIL and untested product exits."}
```
