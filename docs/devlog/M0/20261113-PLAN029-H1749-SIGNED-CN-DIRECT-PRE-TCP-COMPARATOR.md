# PLAN029 H1749｜从真签名产物还原首错，先验CN物理Direct再验原TCP和Stop

- H1747 SOURCE bb3c6762 [Action43424294651](https://github.com/lly8666/wbd-next/actions/runs/43424294651) **FAIL**。下载artifact14037186783核查实际原Go认证Rust V3、官方签名Wintun、OS WAL/Ready、Windows与WSL2原Linux内核TUN双向UDP均真实PASS；Linux alias203.0.113.77→Windows10.66.0.2:45902 TCP入站未回显（Windows监听者收到0），但反向Windows→Linux TCP可以回显。旧双向TCP comparator先raise导致之后的CN QNAME/假IP/真实物理DNS53/UDP46111 **完全NOT_RUN**。
- H1748 并行更改已在HEAD `4ca9954283a13cf29aed1bdf6017a1111521ede8`：Rust两阶段TCP post-Apply PREPARE、Go ABI、Windows/Linux Rust及GNU Cross等source CI成功，仅准备资源未打开受控Defender/内核TCP。此变更仅调整同一个029签名实网fixture，不触产品TLS、Go、Rust DATA、WFP或四阶段OS WAL。
- 一次原签名Windows原Rust V3测试将CN DNS物理收据移到原Windows/Linux原生UDP通过之后、旧TCP入站比较器之前，要求真实Windows应用DNS8.8.8.8询CN域名→物理唯一resolver53收到→fsync FakeIP→原Windows应用FakeIP:46111收物理Direct逆回注→Linux guest源物理IP/端口证明，且GITHUB_SHA完全一致。仅打印 PRE_TCP_AND_STOP 中途阶段标识。旧双向TCP comparator和最终WAL/Stop仍独立运行，不通整条Action依然FAIL；仅其也成功后才更新tunnel_tcp并打印合并阶段证据。
- 新廉价unittest保护先后、来源、不能偷宣告两出口和Stop。commit仅单一显式 `[plan029-v3-real-direct-udp]` native Action，源码结果待CI。D1–D5/P1–P2、Defender原生Direct TCP、startup padding继续OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Reorder source-locked signed CN physical Direct DNS/FakeIP/UDP before historical failing inbound TCP comparator while preserving TCP and owned Stop as terminal gates; collect real first Direct failure"}
```
