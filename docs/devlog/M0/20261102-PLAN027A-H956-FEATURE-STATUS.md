# PLAN027A H956｜功能目录状态修正

H955的新Game十场景真实双系统 **10/10 PASS**仍有效；[H955治理41459947652](https://github.com/lly8666/wbd-next/actions/runs/41459947652) 的feature catalog因新卡项写了不合法的`PASS`而失败。此次只替换为规范`FUNCTIONAL_PASS`及`PERFORMANCE_PASS`，不改Go/Rust产品、编译、以前FAIL或未测。下一步按剩余退出条件继续实测。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Repair two invalid H955 feature-verification status enum values without promoting any new untested capability."}
```
