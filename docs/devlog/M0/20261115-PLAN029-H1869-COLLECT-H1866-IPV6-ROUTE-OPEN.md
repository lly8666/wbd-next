# PLAN029 H1869｜签名IPv6路由边界：当前VM无默认v6，不伪称阻断

- [H1866 Action43647750349](https://github.com/lly8666/wbd-next/actions/runs/43647750349) SOURCE `eccafcd7` success：真正Windows2025 Go/Npcap/Wintun Rust Normal CN与Linux WSL2，真实Direct/Tunnel业务及两个owned Stop PASS。DNS/OS/WAL使用原生成源和精确清理。
- IPv6 `Get-NetRoute -PolicyStore ActiveStore` Before `[]`、真实Ready中 `[]`、Stop后 `[]`；签名Wintun IPv4 lease仅Ready时ifindex=23。原宿主无`::/0`，Wintun无`::/1`与`8000::/1`。IPv6应用发包`NOT_RUN`；不宣称实际泄漏，也不宣称IPv6防漏PASS；onlink、绑定物理和存在v6默认路由的其他网络均`OPEN`。
- 下一D4 IPv6必须基于**不同真实前提**有实际owned IPv6接口/真实路由和kernel app socket发包，检查出口/丢弃与精确owned恢复；不再重复空route读取，不恢复旧WFP或全局关闭IPv6。
- H1867独立P1 A/B与H1868 Direct hard8小容量压力场景在途，先收，不重复dispatch。P1 CPU/GiB +7.01%、P2 unpaced4MiB Direct4.091x物理仍性能OPEN，Game4 CN、GUI真Connect/Stop、D1–D5余项仍未退出。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect signed IPv6 route observation and owned Stop without falsely promoting IPv6 blocking; update stale START_HERE to latest P1/P2 evidence."}
```
