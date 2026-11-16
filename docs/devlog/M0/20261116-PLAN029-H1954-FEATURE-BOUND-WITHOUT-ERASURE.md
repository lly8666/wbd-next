# PLAN029 H1954｜功能卡 16KiB 预算修复（不删除验证历史）

- [H1953 治理 Action43785820641](https://github.com/lly8666/wbd-next/actions/runs/43785820641) 中 `governance` 成功，`feature-catalog` 单独失败：DNS/分流功能卡已有 16,851 bytes，硬上限 16,384 bytes。此 FAIL 属于**仓库元数据预算**，不是 Windows 原生业务/首到失败，历史 Action 仍保留。
- 本次仅压缩 feature summary 和三个历史 verification 的冗长 scope 叙述，所有 **46 条验证状态、SOURCE SHA、evidence 路径和原 FAIL/NOT_RUN** 不变；功能卡新字节数 16384。原始具体证据和 devlog 完全保留。
- 此提交无任何 P1/P2 网络标记、不改 Rust、Go、Python 场景，**不派新昂贵 Action**。原 H1952 [P1 Action43785063606](https://github.com/lly8666/wbd-next/actions/runs/43785063606) 与 H1953 [P2 Action43785820738](https://github.com/lly8666/wbd-next/actions/runs/43785820738) 各自 SHA 仍在途，需原独立回执。
- H1949 384/384 真 QPC 首物理写前尾延迟 p99 14.546ms，下一次六阶段 H1953 不等于已有优化；P1 CPU、D1–D5、Game4/GUI/IPv6/padding/压力依然 OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Compress only feature card narrative to <=16KiB after H1953 catalog failure; preserve all 46 verification rows, source hashes, FAIL/NOT_RUN statuses and evidence, do not launch native scenes."}
```
