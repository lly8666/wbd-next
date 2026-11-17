# PLAN029 H1976｜恢复最新真实失败状态与同源治理

最新真实系统测量为 H1974 SOURCE `bd611192c397220d467a8330defce4e0d494ac04`，[原 Action43808776053](https://github.com/lly8666/wbd-next/actions/runs/43808776053)：正式流程 **FAIL**，原因是 4 个真实同TCP序号重传使严格QPC一窗口1024B联合失败；另外有 5 次Direct RTT 61–63ms，不能报告任何优化PASS。Windows/WSL2应用各2048条1KiB+32预热原SHA/FIN和双方owned Stop确实PASS，但它们不足以替代性能验收。

此前H1975提交 `88e10fa15b6412dc020914356bd275d090580d38` 的治理 [Action43811673565](https://github.com/lly8666/wbd-next/actions/runs/43811673565) FAIL，因功能卡最后一行状态写成不存在的枚举 `PHYSICAL_FAIL_SCOPED`，且 M0 cursor 的 `evidence_refs` 同时列H1975 SOURCE bd611和H1971旧 SOURCE dc2d，而治理明确要求全部本次证据与 `last_tested_source` 一致。

本提交只把 H1975 功能卡末尾状态改成有效且**真实不掩盖失败**的 `FAIL`，并使 cursor 的 `evidence_refs` 只指向 bd611 正式失败证据；H1970 dc2d 的旧PASS完整保留在卡片第50行及其历史devlog中，不删除、不替换源，不修改任何真实实验或生产代码。精简当期cursor叙述，恢复固定32KiB hot-file预算。下一步只追 TX→RX mailbox / Wintun SendPacket / WinSock FD_READ 到inner recv是否贡献那60ms，仍禁止将同轮优化投入普通产品。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Correct unsupported H1975 last verification status to truthful FAIL and restrict live M0 evidence refs to exact last tested source; preserve original failed native proof and historical H1970 passing proof, no product changes."}
```
