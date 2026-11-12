# PLAN029 H1665｜物理 DNS A 查询兼容 CNAME 且不接受无关 A

- 复用原始 Npcap 小包 `pcap_setmintocopy(1)`，将 DNS 回包及时从物理 NPF ring 交到冷查询，无等待线程/系统 DNS；保持物理源/MAC、53端口和准确 BPF/UDP校验。修复旧解析器接受同事务中无关联A answer的缺陷。
- 被验证的 QNAME 可以沿至多 8 步 CNAME 链追随附属 A，最多读取16条应答、8候选IP。无关 A 不可成为主机endpoint，仍须标准TLS hostname证书认证。测试补真实 wire-framed UDP ACK checksum/CNAME/非法A，**单测不代替真实 DNS/WFP/签名网络证明**。
- PLAN029 §2A native Wintun post-capture CN/LAN/custom TCP/UDP 出口仍OPEN；本批不碰原生Rust/ABI/路由/WAL，复用已编译Rust DLL SOURCE527供GUI配置验证。CPU/RTT受限会另测，不能把本次 parser 绿灯称完整DNS。

```feature-impact
{"kind":"updated","ids":["client-domain-bootstrap"],"reason":"PLAN029 source DNS physical NPF small packet wake and bounded CNAME-linked A validation fixed; keep Windows signed WFP/DNS end-to-end NOT_RUN."}
```
