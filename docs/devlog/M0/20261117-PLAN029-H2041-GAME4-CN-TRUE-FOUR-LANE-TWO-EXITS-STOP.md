# PLAN029 H2041｜Game4 CN 四lane真正两出口 TCP/UDP/双Stop原生 PASS_SCOPED

- H2037 SOURCE `99a621ca919183f8ed228feb1f2fd981be895892` [失败原Action43913748050](https://github.com/lly8666/wbd-next/actions/runs/43913748050)：四个TLS lane/真实CN物理DNS/FakeIP/Direct UDP与32KiB TCP/FIN/Tunnel UDP全有应用回执；但 Tunnel TCP 的 Linux `203.0.113.77`→Windows `10.66.0.2:45902` 连接超时，Windows→Linux echo正确，Action原样FAIL，Stop未验收，不能拿已通过子项冒充029全过。
- 准确边界是 **原Windows native测试自身的 owned Defender listener Allow** 漏了Game4 CN：它曾仅为Normal Direct/H1937 P1 ABBA选远端 `203.0.113.77`，Game4错误选 `10.66.0.1`，而Linux原内核应用显式source-bound `203.0.113.77`。H2038 **只**在原测试单条TCP`10.66.0.2:45902`、精确RemoteAddress选择加Game4分支，保留原readback与finally删除，不修改Go/Rust产品、WFP/其他防火墙或协议。不将此归因为内核已做Pktmon的严格因果证明。
- H2038 SOURCE `60e4cc57e42be083d2338ae570749331b0e8b4b1` [原签名Windows2025/WSL2 Action43942345347](https://github.com/lly8666/wbd-next/actions/runs/43942345347) **ALL JOBS SUCCESS**：原Go、Windows/Linux Rust、签名Npcap/Wintun、四TLS lane、真实业务与清理。CN DNS应用查展示8.8.8.8→原物理DNS实际`172.19.42.70`，原Windows收唯一FakeIP `198.18.0.1`，Linux真物理DNS和UDP业务看见 Windows来源`172.19.32.1`，原Windows app真正收到Direct UDP业务回包。
- 同 SOURCE CN Direct TCP **32768/32768真实kernel echo＋FIN半关闭**，Linux物理接收源`172.19.32.1`；Game4 Tunnel UDP双方 kernel/应用**PASS**；Tunnel TCP **Windows 10.66.0.2→Linux 203.0.113.77**与**Linux 203.0.113.77→Windows 10.66.0.2**真实双向独立连接，双方的server_received都为**40B**、client_echo都为true，消除了原Linux反向超时。
- 最后原`report.stop=PASS_BOTH_OWNED`、`plan029_game4_cn_real.stop=PASS_BOTH_OWNED`，单条测试 owned Windows Defender TCP45902规则原精确读回与删除日志通过，WSL2/管理网络恢复的原Workflow也全绿。**这是Game4四lane / FEC off / outer legacy1400的有限收件**，不声称Game4 fixed FEC、Game2 CN、默认外层1460、Game4 p99/CPU、029 D1–D5/P1–P2所有出口已完成。普通Normal Direct UDP p99与H2031 20–30record/2–3s、0–500B/真实MTU填充各自独立证据保留，不跨SOURCE混归因。共享CDN同IP双域名相反出口专项仍用户明确**NOT_REQUIRED**。
- 另H2039解开M0 cursor混SOURCE证据的G2治理失败，H2040将此前H2031真实padding归档加进功能卡验证行，两个文档治理原Action **SUCCESS**；原H2037失败保留不改写。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2041 archives source-locked real four-lane Game4 CN physical Direct TCP/UDP and Tunnel TCP/UDP plus original both owned Stop success, marks scoped limitations; no new product code or extreme scenarios."}
```
