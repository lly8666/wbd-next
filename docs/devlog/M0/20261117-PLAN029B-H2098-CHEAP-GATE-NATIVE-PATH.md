# PLAN029B H2098｜H2097未派出原生 Action；接回现有便宜门再签名一次

H2097 `SOURCE=5d6656fe0c1d67c3d8ca88e94a306c367aaf0434` 仅证据/游标/日志，原 [governance Action44078097514](https://github.com/lly8666/wbd-next/actions/runs/44078097514) PASS；该commit **没有命中**`.github/workflows/m0-wl-public-normal-full.yml` 的 `on.push.paths`，未产生Windows/WSL2 native Action，故真实B2=**NOT_RUN**。不把提交消息marker当已跑，也不重跑H2095 SOURCEaa53的错误字节。

H2098将 `tests.test_m0_plan029b_b2_guest_scope` 纳入原cheap workflow：用Python AST验证`0x6202`、`0x01000001`确为真实二进制常量，保留非CN背景DNS有限观察但错误QNAME/出口/额外同场重试依然失败；并将这一个测试文件列在on.push.paths，以后fixture回归不能隐形。现有 `test_m0_native_ci_scope` 加断言：test-only无显式marker不启昂贵OS，显式 `[plan029b-b2-cn-ordinary-real]` 才开。**本次提交带唯一marker**，让原Windows Go/Rust同SOURCE签名 + WSL2 B2 普通CN双DNS两UDP + 既有双向内核TCP/owned Stop照常执行。

产品冷配置/Rust网络/Defender规则不动；前两次不同首错的原Action、原ZIP及FAIL保留，H2098结果在实际artifact返回前记NOT_RUN。高级CN、真实IPv6、GUI/Stop/Game和同VM低容量A/B仍为后续独立边界，不触发028/大流矩阵。

```feature-impact
{"kind":"none","ids":[],"reason":"H2098 only original source-locked Windows signed workflow path/cheap Python wire AST test and evidence/cursor; no production code or feature behavior change"}
```
