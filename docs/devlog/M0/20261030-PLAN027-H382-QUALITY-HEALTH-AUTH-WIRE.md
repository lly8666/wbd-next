# PLAN027 H382｜质量v2接既有认证Health信封
2026-10-30。从 H381 源码继续，未重复发起旧 Actions。
- Rust `v4_native_health` 的 authenticated WBC4 kind1 LegacyQuality 现在能校验并解析 v2 固定 36B 质量摘要；保留既有 legacy opaque 诊断与 Health idle，拒绝 v2 非法 reserved bytes/范围/数量。
- 新 `encode_authenticated_low_rate_quality_live` 将质量摘要和 payload-idle 合并到原加密控制 record；不新增第二密钥/逐包控制/ACK 回环。
- 定向的认证信封编码、解码、短 MTU 拒绝与 malformed 反例已加入 native engine required 测试。
- **尚非完整产品生效**：Windows/Linux 实际 worker 未生产/消费成熟窗口，Auto 仍沿旧 M2，逐 record Receipt 尚未移除；A/B/C/Stop 与物理仍未结案。

```feature-impact
{"kind":"update","ids":["fec-auto"],"reason":"PLAN027 authenticated Health/Quality-v2 Rust control seam and required source-native test; no changes to deployed public CLI/GUI defaults or live quality scheduling yet."}
```
