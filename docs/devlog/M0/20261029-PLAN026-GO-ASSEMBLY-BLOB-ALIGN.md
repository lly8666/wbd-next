# M0 PLAN026 / 精确Go装配Manifest 追平Auto30s SOURCE

2026-10-29：Windows/Linux preflight Action40813413299 首错为 `assembly blob mismatch: r0/go_overlay/internal/realityfront/fec_v2_policy.go`，Auto30s源码早于本次Health接收施工修改过，原两份Go assembly manifest的blob未同步。本提交仅将 `fec_v2_policy.go` 与 `fec_v2_policy_test.go` 两个overlay result_blob指向当前main真实Git blob，**不更改测试阈值/代码行为、无产品PASS或网络重跑**。Health收包代码同前一commit，仍待编译和双端真实Keepalive发送。

```feature-impact
{"kind":"none","ids":[],"reason":"只校正两份装配manifest到当前真实Go FEC2源码blob，不改产品可见功能或资格。"}
```
