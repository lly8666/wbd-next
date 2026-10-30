# PLAN027 H431｜Windows 原 Rust NPF ACK、真实firstsend与可选密文shadow接线

原Go TLS 真实lane/epoch、M1原Seq64与实际Npcap pcap_sendpacket成功的DATA进入有界OuterAckIndex；纯ACK经完整TCP/IPv4校验与身份tuple/MTU过滤，携带数据的外观ack只有在M3 AEAD/唯一PN开封成功后才作外层提示；每个RX就绪批最多一次owner ACK索引锁。只能释放可选原密文shadow或设置一发机会缺口，仍受全局F/R与原NPF真实结果，不能当业务交付、Health或Auto损失。SACK只允许原Go冷授权，现h​​andoff尚无能力位，故未协商的SACK拒绝；本次只接累积ACK。Fixed/off旧逐record M2及Linux ACK仍待退役。精确SOURCE原生Actions尚未PASS，A/B/C未完成。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Connect strict Windows native NPF cumulative ACK and definite first-send sequence index to bounded optional immutable shadow hints without granting delivery or liveness."}
```
