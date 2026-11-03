# PLAN028 H1075｜ARM64双端原生TLS首飞通过；x86 Game4真8条lane审计候选

[Action 41740841952](https://github.com/lly8666/wbd-next/actions/runs/41740841952) SUCCESS。已独立解包工件13281038936、核manifest和原Go/Rust Native ARM64二进制SHA256；两端均是ubuntu-24.04-arm原生 ARM64、不是QEMU。原Go TLS/FakeTCP443、Rust TUN、脱机生成/导入32B route-key、应用专属CA与账号密码，两个真实Linux netns TCP SLL2重组首载荷：ClientHello667B、ServerHello127B、兼容SessionID32B、服务端提前application data0B。真实内层UDP5/5、单Rust reader Stop。原Go Firefox120与四lane SessionID/缺key本地拒绝/错key/CA/密码负例单元通过。证据 `docs/evidence/M0/PLAN028-H1075-SOURCE1E7B-NATIVE-ARM64-TLS-REAL-TCP-20261104.json`，外观仅Normal first-flight限定PASS；不等于任意公网网站指纹、整个Finished transcript及其它模式资格。

**下一个 Linux完整任务按用户规则换回x86_64客户端+x86_64服务端**。复用先前已构建且核SHA的标准TLS原Go/Rust SOURCE `d7bd355389c1233c54eaa6a4553ebadcbe0eeb70`，一个 Game4FEC6 真实物理出口IP 10.25.0.2→10.25.0.3、MTU1500→1280 场景。新 `tools/m0_plan028_tls_game_lane_wire_audit.py` 从原TCP抓包分出旧4+新4组，不新增握手包：每真实SYN/SYNACK、先客户端TLS ClientHello、服务端无提前载荷、32B兼容SessionID逐lane不同、相同配置的uTLS extension布局一致。只留脱敏结构JSON，PCAP在runner内销毁。复用原Game4 M4 Stop/新认证/MTU readback、真实UDP5回显与FEC6 parity；当前Game客户端顺序old Stop→new TLS，不把健康lane overlap冒称PASS。

**新Game8 Action运行前为未测试候选。** 修复原夹具将单例server Game Stop误用在多group server的断言，准确要求server每group精准Stop和单个Rust sharedTUN ReaderJoin。H998在线热缩MTU旧FAIL、ARM64 Game4FEC旧FAIL、远端ICMP、CPU/p99及Win物理NIC仍未改写。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1075 independent original Go/Rust native ARM64+ARM64 TLS first flight, offline 32B key/CA, negative unit and real UDP/Stop PASS; x86 Game4 eight original TLS lane capture across physical IP generation candidate."}
```
