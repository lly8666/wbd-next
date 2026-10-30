# PLAN027 H438｜精确SOURCE状态恢复、Auto功能卡补齐

从main 7e700a32730bb989092650ed2de923d5c510be79 及其在途Actions恢复。H437 的 Go冷监测 1Hz 不再把单次Linux M4 source NotSent/Backpressure视为90s认证对端断线；原Rust HealthClock 90s timeout独立原子状态设置后才允许Go Stop→joined→TLS再授权。Go局部单测确认非致命计数不触发重连。真实跨Windows/Linux UDP质量仍须通过新的双端原生Actions，不能冒认；原Action40978386152 Auto失败归档完整保留。原6d2e1438 Linux native-functional、G2、Normal、ABI PASS，新7e700a native/WinLinux/real-Go in-flight，source不继承PASS。H437 governance feature-check Action40981761380 FAIL，原因是同commit `feature-impact` 同时声明 fec-auto 与 outer-opportunistic-repair，但仅修改后者功能卡。本批补fec-auto卡，不更改原协议；功能卡和cursor状态均明确PLAN027五项尚OPEN，尤其Fixed/off逐record M2退役、A/B/C和稳定长测。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Sync Auto feature catalog with already-landed native authenticated 90s Health terminal-only Go reconnect gate, correcting source-locked catalog failure."}
```
