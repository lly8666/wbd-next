# PLAN027 H437｜Linux 提前重连真实阻断根因：TX错误不是认证死Peer

回收真实Windows↔Linux原TLS/Npcap/Wintun/Raw Action40978386152：Fixed真实UDP+TCP+Stop正例，Auto READY后源33、M4一次`source_m4_noncopy`，Linux在约2s就 `V4_PUBLIC_NATIVE_DEAD_RECONNECT_ARMED`、Go TLS重连，双向UDP 0；历史失败保留。按 `v4productcli/linux.go:314` 原Go冷control **任何** `TxErrors>0` 就认定对端认证死；`v4_embedded_go.rs::classify_tx_turn` 正确记录短发送/NotSent/Backpressure为诊断`tx_error`，从未声明业务/Health死。这是可代码审计的真实错误因果。

H437在原 Rust owner 中单次Health `unhealthy`（原15s Keepalive/90s死门）才设置`authenticated_peer_dead`原子旗号，接原 Go 1Hz status FFI/读回；仅此才执行Stop→joined→Go冷TLS重授权，仍保留本地TX错误、NotSent、F/容量/Drop计数，不把未知变零损或误认peer ACK。Go新unit确保各种本地误差不触发重连，真实native dead必须触发。原Rust worker, Stop, route与crypto未改，不增Go每包FFI/线程或第二生命时钟。

本SOURCE还必须走Linux构建及真实Windows↔Linux Auto UDP/Stop，Fixed/off M2线上尚待退役，A/B/C皆未闭环，不以这次正确性分析冒充已经实测成功。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair","fec-auto"],"reason":"Prevent early original-Go TLS reconnect on one local M4 partial/NotSent; expose distinct native authenticated Health 90s terminal bit with cold-only Go readback."}
```
