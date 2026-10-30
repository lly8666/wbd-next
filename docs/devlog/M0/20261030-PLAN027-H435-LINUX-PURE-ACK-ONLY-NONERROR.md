# PLAN027 H435｜真实Raw纯ACK批次合法但不刷新Health

回收 41b14fda Windows↔Linux真实 Auto FAIL：Linux记录12个严格 tuple 匹配的 40B flags0x10纯ACK为 InvalidDataFlags，RX链 `raw_observed=12 raw_tuple=1`，Linux端2s即进入Stop/Reauthorize，Windows TX仍继续、Auto实测 UDP 0/0。这是强相关的原生反馈接收路径失配，不把它当成已证唯一根因。H432现已解析raw纯ACK并退休可选原密文shadow，但 RX batch 尾仍会因“没有M3业务/控制”返回 INVALID，持续增加 `rx_error`。H435只对已通过真实 Linux raw carrier tuple/TTL/IP+TCP checksum/MTU/flags，且无SACK的纯 ACK 将该批归为合法无业务；它绝不增加 authenticated activity、Health/idle、业务交付、F、Auto质量或原AEAD PN。混合非法数据仍返回 INVALID；Fixed/off纯ACK同样不误记Native协议错误。仍需同SOURCE双端真业务A/B验证，无任何宣称Auto成功。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Keep strict pure TCP ACK-only Linux original raw receive turns nonfatal while never authenticating data, refreshing Health, or crediting Auto quality."}
```
