# PLAN026 M0 — Windows Rust NativeOwner Health 15s 事件触发真实M1/NPF发送

2026-10-29：在前一 SOURCE 的双方 M3 严格WBC4 Health+Receipt合包接收之后，复用 `v4_native_health.rs` HealthClock，Windows唯一 Rust TX worker 的 `m2_wake_timeout_ms` 加入一个真实 Health deadline（默认15s）；不新增worker、Go ticker、独立加密器或每包时间采集。

真实原 M2 `m2_next_feedback_entry` 使用同一原M1/AEAD/PN封包：若原 RxFeedbackState 到期，则Receipt+Health只发一条；若业务静默并无Receipt，才发独立Health；实际 `pcap_sendpacket` confirmed 才推迟下一个Health15s，失败推迟1s后恢复，未确认/失联不冒充对端Alive，Health无M2清账权。TX已ready新Wintun源在一个batch只更新一次payload idle。对端90s不健康不会触发0ms超时空转；真正强制断开/休眠留给后续验证后的lifecycle owner。

现状：Linux已经有M3认证Health RX，但Linux TX保活尚未施工完成。CLI/GUI有效读回、Game多lane、server FIN/Dormant/Wake、真实同源弱网/容量/Idle CPU仍为UNWIRED/NOT_RUN。本提交属于产品候选不是验收；网络矩阵仍先Fixed→Game→最后Auto+Health。

```feature-impact
{"kind":"updated","ids":["idle-rotation-keepalive","windows-native-transport"],"reason":"Windows Rust native TX发送真实AEAD Health/同包Receipt并按真实Npcap copied结果管理到期，Linux RX已接；双端配置及服务端Dormant/超时尚未接。"}
```
