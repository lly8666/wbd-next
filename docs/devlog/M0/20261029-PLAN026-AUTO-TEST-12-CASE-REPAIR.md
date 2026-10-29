# M0｜PLAN026 Auto30s 首个回放失败与过时计数修复

2026-10-29，Go preflight [40808955700](https://github.com/lly8666/wbd-next/actions/runs/40808955700) 构建 SUCCESS、12个 `TestF2Control` 中除 Aggressive 时间范围外全部 PASS；实际首个断言为 `fec_v2_policy_test.go:239 normal=balanced aggressive=high`。原因是改成真正30s缓降后旧测试仍只运行80s，无法完成五次真实分档。用180s虚拟时间恢复原语义断言：Normal最终Light、Aggressive最终Mild（正好高一档）；不改变算法/快升/可信样本条件。旧workflow `m0-fec2-go-cold-policy.yml` 仍硬编码8个测试，当前源码已有12个；改为准确12，仍要求全部PASS、同一冻结二进制SHA、无FAIL。这是前期自动触发的便宜Go测试修复，不是用户要求最后运行的真实Auto网络矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"只调整既有FEC2测试虚拟时间和过时测试数量断言，不改变30s Auto策略产品实现、参数或现有功能卡。"}
```
