# PLAN027 H387｜恢复Windows回归与Game2 Stop实际生命周期问题
2026-10-30。按 `docs/prompts/M0.md` 恢复 main H386、registry、PLAN027及在途 Actions，不重复启动旧 SOURCE 构建。

- **已回收成功**：Windows 原生 ABI Action [40930106841](https://github.com/lly8666/wbd-next/actions/runs/40930106841) 在 SOURCE `33d1a383c52412877ab8f5d48045f894e0a4bff4` 成功，覆盖之前因 Rust 除法 `.max` 优先级引起的 `direction_epoch_limit==0` 回归，未扩大为产品 A/B/C 通过。
- **保留失败证据**：独立 Windows WAL 原 [Action 40915929426](https://github.com/lly8666/wbd-next/actions/runs/40915929426) Game2 原方向与反向 ciphertext kernel UDP app 实收，但 `StopCryptoAfterDriverDrain()` 返回 C ABI rc5，之后 `TUN.Close()` 等待并在 8m 超时。
- **定位与源码修复**：测试中的 *client-side reverse* `OpenGameRecord()` 是 Rust Game/off 的 `prepare_off`，会留下 `off_pending`。真实 Wintun/UDP app 只收到了外层加密包，解密后的内层 `got` 并未真正写入 Wintun；原测试漏掉对应真实结果反馈，Stop 正确拒绝。现在调用 `clientGroup.CompleteGameOff(ctx,lane.Lane,0)` 明确报告内层 `DefinitelyNotSent`、断言重复回报拒绝，并在 Stop 前清空准确 pending 状态；不造成功驱动凭据。失败路径先取消 ctx 再关闭 TUN，避免旧 t.Fatal 清理顺序导致的等待。
- **验证边界**：新增测试修复刚提交时只具备源码证据；必须看该 SOURCE Windows WAL Action 真实 Game2 Stop 后再结案。其余 PLAN027 去线上逐 record Receipt/双方 Quality/ACK/Health、A/B/C、交付仍 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct a source-locked Windows Game2 Stop integration test's missing negative native Wintun completion and fatal cleanup ordering; no product runtime/config behavior or feature card changed."}
```
