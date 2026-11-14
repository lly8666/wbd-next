# PLAN029 H1861｜当前纯Tunnel CPU +18.04%；All非DNS普通业务跳过每flow pin

- [H1859 P1 Action43615436423](https://github.com/lly8666/wbd-next/actions/runs/43615436423) 真签名同VM A原V4/off、B V3/all各50Mbps 60s/25ms0loss：两者0.6984GiB、Win p99 47ms、最长空洞47ms、owned Stop PASS；A Go+Rust CPU/GiB=19.3522s，B=22.8424s，**+18.04%**，比5%调查线高。Action绿是网络有效，**P1 CPU失败仍OPEN**，不能把全部18%直接归给分类器/驱动。
- 确认V3/All每个非DNS TCP/UDP数据包都在 `PacketIngress` 解析后构造FlowKey/查FlowPin，而All模式下没有Direct出口可选。只对**租约/IPv4总长已校验、非分片、非FakeIP、非53、且TCP/UDP头/长度合法**的普通业务直接Tunnel；绕开FlowPin 哈希、new-pin分配。CN/LAN/Direct4模式、DNS QNAME、TCP53、未知FakeIP、分片身份及畸形帧仍走原路径。纯测试512 TCP+UDP flow + DNS/fake/foreign/malformed/fragment，当前SOURCE P1未实测；本提交只带`[plan029-v3-real-p1-tunnel-ab]`，单Action顺序A/B。
- [H1860 P2 bulk Action43615797731](https://github.com/lly8666/wbd-next/actions/runs/43615797731) SOURCE `b6f87cee` Win/Linux编译与WSL2准备PASS，但Linux子进程由于新第四`p2bulk`参数被旧`len(sys.argv)!=4`拒绝，业务TCP/UDP **NOT_RUN**，仅exact owned finally资源恢复PASS。已修只接受可选`p2bulk/p2paced`且检查Windows/WSL两侧工作量一致，不把夹具FAIL当产品吞吐FAIL。
- H1856的0.0ms UDP p99来自Windows `time.monotonic()`日志显示约16ms量化，本批将P2夹具换成同Windows QPC高分辨率`time.perf_counter()`，保证今后读数可解释；P2本批**不派**，留下一SOURCE单场4MiB。
- 不恢复旧WFP/028矩阵，不调TCP buffers/Nagle，不把编译当Ready。Game4 CN/GUI真Connect/Stop/IPv6/D1–D5和压力测试仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record real H1859 P1 CPU/GiB +18.04% negative despite both network/Stop PASS and H1860 pre-network argv FAIL; fix only all-mode Tunnel flow-pin hot path and test timing/argv."}
```
