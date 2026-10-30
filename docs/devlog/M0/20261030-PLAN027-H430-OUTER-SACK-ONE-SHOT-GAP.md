# PLAN027 H430｜接已有原密文shadow的一次ACK/SACK缺口机会，免逐record M2

在本 main 的 H429 双端来源隔离后，纯R2现增加 `ReceiptState::on_outer_gap_hint`：只有 M0 真实首发/受限ACK Index 已经确认窗口、lane、epoch、reorder guard 的记录才能调用；不存在缓存、已排队、已修一次、过期立即无动作。仅设置现有一次机会的wake索引，仍在同一M4原密文冻结句柄、原GlobalRepairAllocator容量和最多一次策略下向真实驱动执行。该无认证外层hint不改变Health、Auto质量、业务交付、RTT证据或M4首发字节额度。纯测试覆盖无盲PTO/幂等/同一候选限时；当前未在Windows/Linux真实outer入口和SACK接线，不能宣称替换线上M2或矩阵PASS。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Add bounded one-shot outer ACK/SACK gap nomination to immutable ciphertext repair state, with pure regression; native ACK index wiring pending."}
```
