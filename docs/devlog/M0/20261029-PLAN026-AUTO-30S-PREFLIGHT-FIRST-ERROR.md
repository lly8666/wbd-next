# M0｜PLAN026 编译与 feature-impact 首错修复

2026-10-29；本轮当前 main 产品源码尚未冻结/验证。源425a929 动态 Auto 30s 源码候选，自动 Go preflight [40808663297](https://github.com/lly8666/wbd-next/actions/runs/40808663297) 首错为 `fec_v2_policy_test.go:264:62 illegal character U+005C`，原因是自动写入把多行测试表项转成了文字 `\\n`；本提交仅恢复真正换行，保留相同测试含义和30s/4096 valid来源门槛。另上一卡片压缩修订没有同提交devlog，feature gate [40808766586](https://github.com/lly8666/wbd-next/actions/runs/40808766586) 报缺feature-impact，本次补全并同步fec-auto卡。测试端到端和Rust actor仍NOT_RUN，不因治理绿灯宣称性能。
```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"同步 Normal FEC2 Auto 30s真实策略代码及测试修复、卡片状态与本批可审核影响声明；动态 Rust Auto/Health 尚未接线与通过。"}
```
