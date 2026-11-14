# PLAN029 H1796 | signed H1795 TCP/53 and owned Stop recovered

- [Action 43556105215](https://github.com/lly8666/wbd-next/actions/runs/43556105215), SOURCE `1efb3cec6b9f90714b32c78e0318a57720d0e1f1`, native job `132330572307`, SUCCESS true original Go TLS/Rust signed Windows Wintun + Linux TUN. Two original Windows app TCP/53 connections: CN `www.cn.example` over real physical Linux eth0:53 and selective FakeIP back; nonCN `www.globalx.example` over original Tunnel to Linux TUN 1.1.1.1:53 and exact real `203.0.113.77` to app. TCP/UDP Direct/Tunnel, DNS blackhole no fallback and both owner Stop PASS; exact test-owned guest HyperV TCP53 Allow removed by always finally. Evidence `docs/evidence/M0/PLAN029-H1796-H1795-SIGNED-REAL-APP-TCP53-BOTH-EXITS-STOP-20261114.json`.
- Prior [H1794 Action 43555931814](https://github.com/lly8666/wbd-next/actions/runs/43555931814) cheap legacy finally tuple assertion FAIL before network, retained independently. This H1795 real run uses legacy1400, not H1791 independently proven default1460/inner1389.
- Still OPEN D1 TC=1 same-endpoint UDP→TCP fallback, D3 resource-full tables, D4 IPv6/lifecycle/partial Apply, D5 live GUI/10k rules, P1/P2 off-on p99/CPU/RSS and bounded startup-padding actual M1 wiring. Original pinned Go `RootCAs` ABI failure remains separate; no TLS trust relaxation.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Record source-locked real original Windows app TCP53 Direct/Tunnel and owned Stop; maintain prior evidence and feature card hard size cap."}
```
