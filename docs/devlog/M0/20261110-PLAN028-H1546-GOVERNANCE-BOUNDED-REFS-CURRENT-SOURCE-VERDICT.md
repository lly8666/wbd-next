# PLAN028 H1546 — 构建实证与有限治理游标

现役源码 `ed965f2d` 的 [ARM64 Action42825317709](https://github.com/lly8666/wbd-next/actions/runs/42825317709) 在 Ubuntu ARM64 上实际编译当前原 Go 双端＋Rust/ISA-L 和 SHA256/ELF183：**PASS_SCOPED_BUILD_ONLY**；应用网络、Stop NOT_RUN。[Windows/Linux Action42825317732](https://github.com/lly8666/wbd-next/actions/runs/42825317732) 的 Windows Go native ownerlease/windowsclient测试编译、旧双账号与五账号具名内核事件单测以及双 OS Rust单测均 **PASS_SCOPED**。Windows五设备实际共享WFP路由冲突仍FAIL。Linux 30% / 300–350Mbps 当前完整原生600s [Action42825317650](https://github.com/lly8666/wbd-next/actions/runs/42825317650) 进行中，最终业务尚无成绩。

本轮治理 FAIL 根因 `feature-catalog/structure.json` 的 `unbounded evidence_refs`：游标累积12个， `.governance/policy.json` 限8个；不删除历史证据，仅保留最近H1545实际当前源SHA匹配的1个游标引用。历史 Git 证据与 H1537–1544 devlog 保持完整。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct cursor evidence reference cardinality only and record actual BUILD_ONLY source checks; no product behavior or settings changes."}
```
