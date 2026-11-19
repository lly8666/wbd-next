# H2169｜恢复Game startup-padding签名原生job

H2168源 `65a49d29fa7f484a1a8cbb9d9e6fd709aedc1bcd` [Action44248395979](https://github.com/lly8666/wbd-next/actions/runs/44248395979)：原cheap/WinLinux Rust/Go编译通过，**Linux source-locked build及native-public-two-os两作业均SKIPPED**，因此原Game2/4 padding真OS TCP/UDP/NPF及Stop仍NOT_RUN。首错原因：中央 `tools/m0_native_ci_scope.py:EXPLICIT_NATIVE_MARKERS` 没纳入 H2168 有效标记 `[plan029-game-padding-real]`，不是业务网络验证通过。

本轮只在中央原权限名单增此单一明确标记，并针对“纯test-file无marker不触发、明确marker触发”写单测。不改产品Rust/Go/GUI/FEC，不扩大5-policy ×4矩阵。Workflow已明确仅两台 `game2off`、`game4fixed`，每台三档off→tls→flows；必须同SOURCE真实Go TLS+Rust Game M4 NPF成功复制回执、Win2025 Wintun/WSL2 Linux TUN内核TCP/UDP、MTU1460、owned Stop/WAL。失败保留，不拿H2167 unit当原生PASS。

新SOURCE自动 CI 与原生结果另查后再更新功能卡verification和M0 evidence_refs。旧H2167 Windows Rust419项PASS、GUI assembly PASS、H2162真实Game20/20不同SOURCE证据不变。完整技术029/029B仍OPEN；030 NOT_STARTED。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix the explicit test-only native gate for an already scoped Game padding Action, add guard test and audit; no product runtime, GUI or feature-card change."}
```
