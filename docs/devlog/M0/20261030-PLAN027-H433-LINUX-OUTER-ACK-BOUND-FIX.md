# PLAN027 H433｜Linux ACK source ctor预检修复

审计 H432 SOURCE 419030c8：原有 R2 `OuterAckIndex` 最大24576条，Linux init 传65536会立即 InvalidConfig/BAD_STAGE，直接阻断真实新TLS启动；原 ReceiptRouteScope 也没有公开 epoch() getter。修为 MAX_ENTRIES=24576，单一 OriginalOuterRepair 保存经原Go保护TLS验证的不可变 epoch（既有 M3 owner 身份），所有ACK范围保持scope，不能把raw反馈当 AEAD/Health/业务；重用原24,576可选样本界，不放宽 R2安全上限。历史 H432 SOURCE 失败记录保留，不拿新SOURCE此前旧 PASS冒认。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Correct Linux scoped outer ACK index capacity to R2 24576 max and freeze original protected epoch for matching, fixing native startup regression."}
```
