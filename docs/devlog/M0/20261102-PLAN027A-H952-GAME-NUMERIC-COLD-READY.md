# PLAN027A H952｜Game真实数值OS MTU遗漏：单一冷路径修复

H950 [41455568369](https://github.com/lly8666/wbd-next/actions/runs/41455568369) 用已编译 H948 原生程序测试 Game4FEC 3Mbps 0% 时，独立 Game 的 Windows TLS 和 OS Applied 已进入 READY，却在夹具首个真实数值回执门 FAIL：`missing/duplicate live Windows numeric OS MTU receipt`。这不是吞吐失败证明；没有测到3Mbps应用交付/Stop。

根因：H946 只给 Normal 冷路径加了数值 OS/WAL 检查。Game 旧冷路径在 `LiveReceipt` 之后直接输出 READY，而已有 `RuntimeMTU` 仅在之后 1Hz 运行检查。H952 在 Game 同样调用旧 `N4RealWindowsProduct.RuntimeMTU` 当前代 MTU CAS，在 READY 前和 Rust 内层派生值比对并发同格式回执；错误走原有 Stop。不添加逐包计算/新的MTU输入，不修改默认外层1460或显式1500上限。唯一 Game overlay result_blob 精确重钉。

需新 source 一次构建、一次原生复核；H950/H951旧binary测试仍只属于旧产品source，失败不得删除。DF0/DF1等仍开放。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Observed actual Game native cold receipt FAIL; add current-generation Windows Game OS numeric readback before READY and preserve old source failure."}
```
