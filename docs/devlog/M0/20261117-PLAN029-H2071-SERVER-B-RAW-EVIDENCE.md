# H2071｜H2070 真实服务端 B RAW RX 已到达，未发现经认证 Health

源锁：产品二进制 `2fca1a93b4f9f7d3e7c5985adc356ade13332e86`，H2070 仅读测试 fixture `195a93aa09e877ed8ee31c7c32516773bb38f01e`；[原生 Action 44025145100](https://github.com/lly8666/wbd-next/actions/runs/44025145100)，原始失败 ZIP artifact `14303017093`。旧 Action 历史 FAIL 与 NOT_RUN 均不改 PASS。

**已证实**：原 Linux shared manual /32 server 的同一 AF_PACKET TCP443 监听仍活；二次 GUI 真实触发 `41032 → 443` 的 SYNACK/TLS。第二个 Rust M4 RAW RX per-port 冷启 5s 读取现场依次达到 `kernel_raw_observed=2 → 3 → 6 → 13`、`tuple_candidates=0 → 3 → 10`、`tun_delivered=0 → 3 → 10`，`rx_err=0`。原 eth0 见第二次真实 TCP PSH；client B 实际 Rust `source_wire_bytes=34448`、`control_wire_bytes=320`。所以服务端 B 的 RAW socket **有真实收包且解出了可写 TUN 的数据**，并非“旧 A 占了监听、B 被全量 BPF 丢弃”，不能再用重复端口/旧单会话 guard 解释此次故障。

**仍未通过**：服务端 B 在候选期没有 `has_verified_peer_health`，原共享路由 **保留旧 A**，日志 `V4_PUBLIC_MULTI_SERVER_B_CLIENT_UNPROVEN port=41032 old_route_preserved=1`；没有第二次 Windows OS Applied 与联网业务收据，GUI 真实二次联网 FAIL。服务端安全路线不能靠“10个 TUN 包”替代 B 的加密身份 Health：这个业务计数不代表原 `LegacyHealth` TLV 被解析成功。真实 server Rust Stop 与 SharedTun Stop 有回执。

静态逐行核查：Windows `v4_windows_owner.rs::m2_next_feedback_entry` 在 Health 到期时调用 `encode_authenticated_health_live` 并以原 M3 kind15 AEAD 密封；`v4_windows_native_runtime.rs::send_control` 以真实 NPF copy 结算。Linux `v4_owner_crypto.rs::ProtectedBackgroundRx.consume_original` 只有在 AEAD/PN unique 开启 kind0，并经 `parse_authenticated_control` 验证后写 `authenticated_health_hint`；`v4_embedded_go.rs::background_raw_once` 进 `AuthenticatedActivity.record_batch`，供 `has_verified_peer_health` 控制 B 路由交接。

根因现在缩小到 **B 的规范化 Health 记录实际到达/解密/解析/登记链**，但仍不足以断言是单一哪一级丢失；下一最小观测应针对 M3 已验密 kind0 与 TLV 成功/失败的**数字计数**，同时对齐 Windows kind0 NPF copy，不记录 payload/密钥、不新增接收泵、不放宽 5 秒授权。首次 GUI OS/Stop、域名二次原始 TC/TCP53、TTL2 首次/到期后 FakeIP 有现存真收据；**第二代 Direct/Tunnel、TTL 重启第三问继续 NOT_RUN**。

```feature-impact
{"kind":"none","reason":"H2071 archives real H2070 server RAW RX numeric evidence and narrows remaining authenticated Health acceptance boundary; no product or feature semantics changed"}
```
