# PLAN027 H385｜Windows额度回归触发路径补全
2026-10-30。H382 Windows original-owner ABI Action40929275175 因预算读回 0 FAIL。H384 修复源码却不会触发该 workflow，因为 workflow 仅监听 engine 源码。此批将 `crates/wbd-recovery/src/{budget.rs,global_sparse.rs}` 纳入 Windows 原生 owner ABI 自动路径；不改测试内容、不复发旧性能矩阵。新 SOURCE 的 Windows 原生场景仍须以实际 Action 结果判断，不凭本次触发说明 PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"Only broaden exact native Windows source-locked regression workflow triggers to actual recovery accounting dependency; no further runtime behavior, product parameters or feature card changed."}
```
