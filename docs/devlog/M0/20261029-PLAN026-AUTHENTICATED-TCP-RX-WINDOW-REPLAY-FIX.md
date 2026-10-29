# PLAN026 M0｜原 Windows NPF 累计 ACK 高水位真实重放 bug

2026-10-29，Windows PLAN020 原 Go/TLS→Rust native source `a6a6985705de6a81de7d04ff6d0dd7019c3afb41` Actions40819133082 已走过原桥接装配和真实Go编译，失败在已有 `TestM0PLAN025WindowsNativeV4OutOfOrderFirstAndRealCumulativeACK`：`stale replay incorrectly admitted`。事实：`m0V4RxWindow.Copied` 只在原M3 AEAD唯一PN验证+真实 Wintun Copy之后调用，向前消除真first-arrival后更新 `cumulative`，却没有同步 `authenticatedHigh`；后续合法旧TCP重传的 Check 因不一致误走 `IndependentAEADCandidate` 并返回fatal，而不是正常忽略，可能让正常重复包导致客户断开。

本提交只在真实 `Copied` 成功按序推进后把 `authenticatedHigh` 更新为至少新的 `cumulative`；不从原始TCP ACK/未认证payload增加权力，不改变前瞻窗口、不额外缓存、不过度防御。两份见证源与 `manifest-plan020-m0.json` 当前Blob一致；保留原有两个严格越界/重放测试，不降低断言。新SOURCE编译/真实网络表现仍未验证，Game双Worker、FIN Dormant未实现。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"修改真实认证Wintun Copied之后的原Go TCP重传序号窗口，避免已实际拷贝的重复包误被判 fatal；不改变认证边界与验收状态。"}
```
