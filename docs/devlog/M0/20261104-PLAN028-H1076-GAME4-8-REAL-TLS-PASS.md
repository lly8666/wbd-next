# PLAN028 H1076 — 八条原生Game4 TLS 首载荷与切网业务 PASS

[Action 41742013361](https://github.com/lly8666/wbd-next/actions/runs/41742013361) SUCCESS；已独立解包7份工件的SHA256。预先已构建原 Go/Rust SOURCE `d7bd355389c1233c54eaa6a4553ebadcbe0eeb70`、x86_64 client+server双原生 netns，Game4 fixed6 TLS/证书/口令/单443 + 真实 Rust M4。旧源IPv4 10.25.0.2四个源端口41031–41034，新源10.25.0.3四个56881–56884。真实TCP SLL2抓包各lane均有SYN/SYNACK，客户端首ClientHello667B、服务端首ServerHello127B、服务端无提前应用载荷、每lane有各自不同的32B SessionID和相同原uTLS扩展布局，无WB-R1。两代原M4 parity copied非零，旧Game原owner Stop→新TLS后应用业务5+5 UDP成功，同安装租约未变，出口物理MTU1280后TUN内层OS MTU读回1178。仅保留脱敏PCAP审计JSON，原始pcap在job中销毁。见 `docs/evidence/M0/PLAN028-H1076-SOURCED7BD-GAME4-EIGHT-TLS-LANES-20261104.json`。

**不能外推**：旧Game先Stop再新TLS是已断后冷恢复，未验证健康lane A→A+B→B同时并存/内层TCP不断；当前首飞记录不等于整站浏览器指纹或Finished独立解析，Windows真实网卡切换未测。H998在线MTU热缩FAIL、旧ARM64 Game4FEC Action FAIL、远端ICMP/CPU因果未证保持。下一独立Linux任务按轮换ARM64/ARM64。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1076 real x86 Game4 FEC6 source d7bd 8 old/new TLS ClientHello first-flights across source-IP change, verified 32B unique SessionID, 10 UDP, MTU1178 and old Rust owner Stop scoped PASS."}
```
