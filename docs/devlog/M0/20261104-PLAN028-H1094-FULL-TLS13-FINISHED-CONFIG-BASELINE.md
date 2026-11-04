# PLAN028 H1094 — x86_64 双端原 Go TLS13 Finished 与同配置 uTLS 基线

上一轮 H1093 native ARM64/ARM64 Game4 fixed6 八条真实ClientHello已核SOURCE收口；按用户轮换本次新的 Linux 测试任务使用 x86_64。此包**不改产品**。仅补一个独立原Go来源锁小场景，使用原 `newFirefox120Client`（带32B HMAC SessionID）与**同一** Firefox120 uTLS preset（其默认新随机32B SessionID）对比，共用完全相同的 `target.test`、自签测试证书/客户端根池、TLS1.3 server policy、ALPN为空等。绝不模拟私有前导，不绕过证书校验。

新增测试仅在真实回环TCP中运行原Go/uTLS与Go crypto/tls，`net.Conn.Write` 双向捕获**完整TLS字节流**，由本场景 server `KeyLogWriter` 写入内存中临时traffic secret。实现RFC8446 HKDF-Expand-Label并按实际协商TLS1.3 cipher (AES-GCM/ChaCha20Poly1305) 对每个加密handshake record独立AEAD解封，必须真实解出 server EncryptedExtensions→Certificate(含本证书DER)→CertificateVerify→Finished，以及客户端 Finished。原两侧 `HandshakeComplete` 且 `VerifiedChains` 非空。比较两次首条ClientHello长度、ServerHello长度、版本/cipher和规范化GREASE的同序扩展，只有HMAC 32B SessionID本身可不同；真实外层record长度随证书/签名变化，不硬编码包数/固定字节长度。

无原始 TLS stream、keylog、traffic secret、路由密钥或证书私钥输出工件；log仅打印长度/加密记录计数与成功标记。该场景本质是“真实loopback TCP上同原库的完整握手对照”，**不是**实际 netns 网卡 PCAP 解密或网站指纹相似性合格。独立的 H1092/H1093 真netns八lane PCAP仍只是首飞资格，两类证据不混。构建一次Go test，Rust产品及旧Game4吞吐矩阵不重建。

H1094 待x86 Action验证，绝不先标PASS。Windows真实物理NIC/IPv4转换、新路Npcap实际出口、MTU/首包CPU/p99，旧H998同连接热缩MTUFAIL、旧ARM64 Game4FEC旧SOURCE FAIL、远端ICMP和Android仍开放。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1094 one x86 original-Go TLS1.3 full Certificate/CertificateVerify/Finished authenticated decrypt in memory, configured Firefox120 baseline comparison, distinct from prior real netns ClientHello-only PCAP; Action pending."}
```
