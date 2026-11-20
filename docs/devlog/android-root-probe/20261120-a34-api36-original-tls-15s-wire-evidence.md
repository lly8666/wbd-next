# A34｜API36真原FakeTCP已建立，TLS 14,997ms 后 OTHER

用户自主运行A33 SOURCE `f8031ef1cf2f15e2769208d76bf2b072275b6084` 的API36安全TXT（33事件）：`ORIGINAL_GO_ASSOC_ESTABLISHED`→`ORIGINAL_GO_COLD_PRODUCT_PREPARED`→`ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED`，14,997ms后 `ORIGINAL_GO_TLS_HANDSHAKE_FAILED_OTHER`、exit1；Go/TUN/RAW/SYN ACK等历史阶段保持。原Linux server RAW接包/SYNACK来源及ClientHello抵达、TLS验证/认证/32租约、Rust M4 TCP UDP和认证后owned Stop全部NOT_PROVEN。15s接近候选绝对预算，但OTHER不是确证Timeout。

A34在原ClientAssociation emitter成功调用原raw.WriteSegment之后，首次非空bootstrap Payload只记固定`TX_OK`；在原AF_PACKET真ReadSegment+原4元组`MatchesInbound`后，只记首次`RAW_PEER_PAYLOAD_RX`；返回失败时按本会话实际状态记未观察方向以及原已有重传是否发生。都不记录原payload/账号/IP/Key/证书/错误原文，不增加TLS前导、额外socket/发送器、强行重试或改变TCP/AEAD/Stop。原TLS错误分类只对确切`faketcp.ErrBootstrapTimeout`、OS deadline、context cancelled、bootstrap closed等固定类型追加分支；未分类OTHER且原15s预算确已耗尽时为`DEADLINE_ELAPSED_OTHER`（仅观测时钟）。Java原Service将原Go固定Marker转脱敏安全TXT，CI签名APK、双ABI、真实Linux Oracle、Go及Java Host正反例独立验证，禁止因绿色冒称手机或服务器PASS。

下一步唯一真实外部门：用户自行使用新SOURCE签名ARM64 APK导出一次固定TXT；若有原Bootstrap payload TX而原RAW对端RX未见，先查原服务端AF_PACKET ClientHello接收及传输回程，而非改TLS/证书/默认全App路由。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A34基于真实API36原FakeTCP Established后TLS 15s OTHER，对原Bootstrap收发及TLS实际截止时间作无敏感分层诊断，原协议不变。"}
```
