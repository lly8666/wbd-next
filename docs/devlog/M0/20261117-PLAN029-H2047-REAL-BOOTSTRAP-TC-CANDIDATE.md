# PLAN029 H2047｜独立物理服务器引导DNS TC→TCP候选

新增Linux WSL2内核 UDP53/TCP53 物理listener，同一dns.direct IPv4及真实Windows物理source；对vpn.edge.cn.example先回答单次有效TC=1，要求同source、同endpoint、同ID/QNAME的TCP53再给A=真实WSL peer。TLS原SNI不变，认证后复用原Normal CN Direct/Tunnel TCP/UDP与owned Stop。

仅新[plan029-real-dns-tc]真实一Action；不复跑H2041四lane、H2031填充或H2045 GUI。同源证据回收前本场NOT_RUN，DNS bootstrap重连/TTL/五类满压未据此验收。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"One independent original signed Windows physical DNS TC same-direct TCP53 scene with WSL2 kernel witness; awaiting source-locked Action."}
```
