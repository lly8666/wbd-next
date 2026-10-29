# PLAN027 H406｜回收 S404 旧 M2 生产路径回归

2026-10-30。源 `9a2af725ab0dd498dd7960e4e91d1ca23a0683cb` 的在途 [Linux Auto/Health Action40953849208](https://github.com/lly8666/wbd-next/actions/runs/40953849208)、[Windows Rust owner Action40953849191](https://github.com/lly8666/wbd-next/actions/runs/40953849191) 均已 SUCCESS；r0-native-abi40953849214 也 SUCCESS。Linux 真实原 Go TLS+Rust 双 netns 旧 M2 正例含 1% netem offered512/首到507、Fixed/Auto各64个应用首到、Game2/4、Stop；Windows 签名 Wintun+Rust owner scoped TLS/UDP、篡改/重放和 owned Stop。精确 job/artifact/digest 与未覆盖项见 [H406 evidence](../../evidence/M0/PLAN027-H406-S404-OWNER-LEGACY-PATH-REGRESSION-20261030.json)。

**不得误判**：这些 job 仍使用逐 record M2；Windows scoped native 不等于全 WFP/route 产品 APPLIED，均未执行新 Quality START/CLOSE 的实际 owner 收发。S404 strict wire 已由 H405 native 证明；PLAN027 ①仍 PARTIAL、A/B/C 仍 OPEN/NOT_RUN。新 SOURCE 不能以旧 M2 绿灯冒充新反馈验收。下步接双端真实回调/能力门/ACK/SACK 修复并移除 M2，再启动简化 A。

```feature-impact
{"kind":"none","ids":[],"reason":"Evidence-only collection of already-running exact-source legacy owner Actions; no product code, mode, config, default or feature behavior changed."}
```
