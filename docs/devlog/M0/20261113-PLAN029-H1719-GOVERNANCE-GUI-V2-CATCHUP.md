# PLAN029 H1719｜真实治理失败与GUI只读预检v2阻断修复

- H1718 [Action43383231819](https://github.com/lly8666/wbd-next/actions/runs/43383231819) **FAIL**：两个旧 M4 `PINNED_FILES` preflight SHA 被错误当成新live SHA；实际应保留冻结旧M4，另在 `M0_PLAN029_REVIEWED_CURRENT` 登记两个独立派生。四条 M0 live manifest SHA已确认，不倒退。新增明确审定，不改旧donor。
- [Action43383231768](https://github.com/lly8666/wbd-next/actions/runs/43383231768) **FAIL**：cursor 同时引用了 H1716 旧SOURCE与 H1718 新SOURCE；将旧失败移至 context、只以 H1718 当前SOURCE证据为 evidence_refs，且补功能卡影响声明。不改变旧H1716事实与文件。
- GUI `ReadNativeProductPreflightAsync` 旧代码死查 `wfp_guard_and_authenticated_stop_not_qualified`，新 no-WFP v2 Go CLI只报 `authenticated_live_owner_and_applied_receipt_not_inspected`，会把合法只读结果错误当作WFP不合格并拒绝展示。manifest Go donor 40 个 patch 重新逐条精确复算，新 GUI blob `f514fd44b847ffd6a1e13e9ea8baeb94bd5cfb93`；READY文字变为四阶段真实读回，不凭进程/日志设Ready。
- H1663 WinForms harness 加一次**真实原Go CLI只读预检**，检查state absent、无WAL产生；此提交时CI尚未执行，不能称联网PASS。Rust单ingress真实Normal/Game4 Direct/Tunnel, forced DNS, FakeIP CDN反例, 全量Stop/GUI有效连接, startup-padding和D1–D5/P1–P2继续**NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"GUI v2 no-old-WFP preflight repair and live SOURCE provenance; actual product dual-exit tests remain unqualified"}
```
