# PLAN029 H1706 | 真Windows应用 TCP SYN 通过Rust NAT到内核listener、独立Linux双向半关闭场景

H1705 SOURCE 006b31a48a991928edfaa8dc6006f5c8c4b19844 original Rust source-locked Windows309/Linux284 unit PASS，含3项 PLAN029 TCP NAT checksum、反向四元组、Direct满额测试。纯测试不代表实际 SYN。

新增单个签名 Windows2025 Wintun 真实网络场景：Go原应用自己的 DialTCP 发往固定 FakeIP，一条owned FakeIP/32和一条synthetic peer/32；Rust唯一 Wintun RX按NAT重写发给 Windows kernel listener46101，内核原生 SYNACK 逆向由Rust重写后送回原应用。Windows仅临时精确owned Defender Allow（本次测试exe/leaseIP/syntheticIP/TCP46101），Linux WSL2独立guest TCP46099用一个精确owned HyperV Allow，finally分别卸除，不借旧WFP。

Rust phys-src + ifindex绑定的非阻塞 TCP socket到guest真实TCP listener，TcpDirectRelay读写原kernelTCP和物理TCP两腿、FIN/半关闭、最大每腿4KiB/turn，Linux回显后原Windows TCP app必须读到。只有在Rust worker join、借用Wintun归还及精确owned Stop通过后，单Action可记诊断PASS。这不是正式TLS/Normal/Game4和产品Ready。

完整DNS53/FakeIP、配置GUI/padding、生产NativeOwner唯一入口与D1-D5/P1-P2仍未完成；不复活028旧矩阵或启动030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","windows-native-transport"],"reason":"Collect H1705 cross-platform kernel TCP NAT Rust unit PASS and author one test-only real signed Windows application/kernel listener/physical Rust TCP independent Linux guest and owned Stop scene."}
```
