# Windows v2 recovery: removed Wintun and stale interface index

User physical report: active four owned stages, original ifIndex 27 and lease 10.66.0.198/32, original adapter/capture routes absent; native state v2, no Defender receipt. Binary reports dev/unknown; exact source and Win32 failure stage unknown. Legacy inspector treats unrelated IPv4/IPv6 index/LUID collisions as foreign before testing original GUID absence. For v2 persisted recovery only, use the original GUID to distinguish absence; do not touch a replacement adapter. When absent, skip its local interface writes and keep the existing actual physical route cleanup. No new steady-path code or security layer. Add native stale-GUID/occupied-index case and full Apply followed by actual Wintun removal before WAL retirement; qualification pending, not a physical PASS.

```feature-impact
{"kind":"updated","ids":["windows-network-wal"],"reason":"v2恢复按原GUID识别消失的网卡，保留物理路由恢复；增加真实网卡索引复用及网卡消失测试。"}
```
