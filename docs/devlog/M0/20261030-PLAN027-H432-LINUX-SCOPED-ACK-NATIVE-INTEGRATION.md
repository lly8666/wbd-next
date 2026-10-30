# PLAN027 H432｜Linux原生Raw M4外层纯ACK → 唯一Shadow缓存

恢复最新main并读PLAN027/registry/cursor；当前SOURCE 441618 native-functional/governance PASS，历史 41b14 Windows+Linux双端 Auto app-duplex FAIL、Fixed UDP/TCP/Stop PASS，失败完整日志 Artifact 12944291922 保留。Linux旧Raw RX完全扔掉纯TCP ACK（合法严格验证为InvalidDataFlags），因此Windows发的外观ACK无法退休Linux原密文Shadow。H432在现有Linux raw_carrier 32-slot batched原FD引入 `PureAck`（已核tuple/TTL/IP+TCP checksum/无SACK）与DATA的presentation_ack32；原Rust RX一批只提交一个hint，纯ACK绝不进入M3 AEAD、Health、业务或Auto丢包率。原M4 copied data PN/Seq/len登记本lane+epoch的有界 OuterAckIndex，ACK范围只能丢弃已有可选RepairShadow，不撤真实业务先发额度、无定时DATA PTO。未协商SACK继续拒绝不装作已经接通。这是双端真实线上ACK接线第一段，不足以解释全Auto UDP故障，仍须跑相同源码原生/双端 Action并修业务。

按PLAN027 §0：①部分（Fixed/off旧M2仍在线）②A未齐 ③B未齐/Auto双端FAIL ④C未跑 ⑤未齐；不宣称全部完成。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Connect strictly parsed Linux original raw-TCP ACK to lane/epoch M4 definite-send index and optional one-shot repair cache retirement; no liveness/Auto credit."}
```
