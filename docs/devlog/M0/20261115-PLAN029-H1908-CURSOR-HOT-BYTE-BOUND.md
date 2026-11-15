# PLAN029 H1908｜热读预算界内收缩游标（不改变长测或产品）

- [H1907](https://github.com/lly8666/wbd-next/commit/a4cfa1d354b7e3b2043ec0f6d35ac0defc7e8f4b) 的高率源已由独立签名Windows/WSL2 Action 开始。原 `tools/governance.py validate` 守卫查明热读源文件之和 `32777` B，超过硬门槛 `32768` B 9字节，导致本Source的Governance / Feature catalog失败；**原失败留历史**。
- 将M0 Cursor原 `current_task/why_now/next_action/partial_summary` 纯文本描述缩短数百字节，保留 `sequence`、`checkpoint_sha`、`last_tested_source`、所有证据源锁及8条以内context refs；不放大任何policy、不删源证据、不修改原Go/Rust/Tunnel/P2测试。
- H1907真实长量原源 **仍未有正式PASS**，另一个动作在同源跑全10GiB与6段UDP、CPU、SHA/FIN、owned Stop。H1908仅治理读预算合格性修复，不触发带`[plan029-v3-real-p2-long-ab]`的重复10GiB行动。

```feature-impact
{"kind":"none","ids":[],"reason":"H1908 cursor text compaction to satisfy unchanged original 32768-byte governance hot-read gate, no product/runtime/performance test behavior change."}
```
