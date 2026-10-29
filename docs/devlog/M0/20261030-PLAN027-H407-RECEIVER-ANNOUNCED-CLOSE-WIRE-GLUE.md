# PLAN027 H407｜RX CLOSE 绑定 F 与低频 wire 回传候选

2026-10-30。恢复 main bdf4d246，registry.M0.goal、PLAN027、cursor、最新 Actions；H406 checkpoint 后无新源码提交或在途测试。未重启旧 M2 验证。

补齐纯 Rust 接收闭环的一段必要逻辑：RX 4 窗 START 前已见认证 DATA 时用单个 untracked-PN 高水位保守降为 UNKNOWN；认证 CLOSE 绑定首发 F/完整性/容量标志，3s 本地成熟后才可输出匹配的 36B v2 summary。错误 CLOSE 不推进成熟，丢 CLOSE 不生成可误认为零损的回报；16 窗本地 TX 历史仍校验 F 与 epoch/lane。v4_native_health 新增 scoped START/CLOSE→ReceiveWindows helper，回归包含 Health+Quality 封装→RX→summary→SendHistory，不发送逐 record Receipt。

**验证状态**：本批仅提交源码与强制 Rust 单测，Actions 尚待按 SOURCE 回收；不能把旧 H405 PASS 移植到本 SOURCE。Windows/Linux 真实 owner 未调用 helper，旧逐 record M2 仍 LIVE；PLAN027 ① PARTIAL、② A NOT_RUN、③ B OPEN、④ C NOT_RUN、⑤ OPEN。下一步先接生产 owner/能力门/机会重传，再 A→B→C 和必要修复。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Add scoped low-rate receiver START/CLOSE-to-summary candidate, conservative pre-START data censor, and unit coverage; live owner behavior remains NOT_RUN."}
```
