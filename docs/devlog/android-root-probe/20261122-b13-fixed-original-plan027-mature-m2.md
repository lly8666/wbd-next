# B13 原 Android Fixed｜真正 PLAN027 成熟 M2 到 Native APPLIED

起点 SOURCE `53234947eb0633923b4bb3d29d0bc4667232ffd6`，前轮 [dual64 #44924720502](https://github.com/lly8666/wbd-next/actions/runs/44924720502) 为11 SUCCESS、4 SKIPPED。**不是 Android FEC E2E。**

## B13 本次真实接线（同一个原 owner）

- 复用 Linux Auto 正式 `SendWindowSampler/SendHistory` 封装，重命名现有 `LinuxQualityTx` 为平台共用 `OriginalQualityTx`，不是第二个 Android M2 算法。原 Go feature7+相同epoch的首次 Fixed PENDING 初始化一份本方向 client→server QualityTx；禁止无 quiescence 的后续修订覆盖老窗口。
- Android M4 `FixedStream::offer_source` 经原 M3 AEAD/唯一 PN 和同一个 scoped RAW `sendto` 的明确 copied 结果才调用 `OriginalQualityTx::settle_batch`；kind3 parity 或未发 source不能增加 F。原单 worker 用现有受保护 Health kind1、当前同一 PN allocator 发送 START/CLOSE，真实 kernel copied 才使窗口 START 有效或 CLOSE 归档。空闲调度加入已有窗口 deadline，无 busy poll、Go逐包或新 sender。
- 本方原 M3 认证、唯一 PN 的 Kind1 Quality `WireReport` 回调进入原 `SendHistory::assess_wire_with_age`，检查 *本地匹配* lane/epoch/direction+ID+PN区间、sender真实首包计数、`mature=true/complete=true`、容量非受限、sender本地age≤10s、3s接收端成熟和重复ID。原报告内容本身并不证明任何业务交付。只有成功匹配的全新报告、真实正向证据、同修订原 source及parity RAW copied，才设置 RX `applied_revision`。先PENDING允许认证RX；从不凭 raw ACK 或纯Go请求设置APPLIED。
- Linux Fixed server 原本仅Auto启用 `QualityRx`，现对同一受保护feature7+公开M2臂下的 Fixed也创建既有 RX windows，使真实START/CLOSE有匹配可回的 matured report；Linux其他模式数据/密文/预算不变。
- 原 Go Android只读收据更新为9 u64：0/1真实 source/parity RAW copied、2/3 TUN source/recovered、4 unique symbol、5/6认证Quality/Signal见数、7成熟匹配Quality、8精确 Native APPLIED。它不是逐包 Go DATA，更不伪造成功。
- 原引擎的确定性 Linux 主机单元测试用本模块同一 `OriginalQualityTx` 检验：parity排除、坏first_sent、未成熟、错误窗口ID、重复报告都不得替代真实M2。Android源码门同步保留 Go Fixed pre-TLS 硬拒绝、`loop_start` feature3-only。

## 剩余阻塞

**当前未开放 Android Fixed/Auto。** Android Fixed 的原 App/Go正式调用链、按实际Fixed Rust方向的内TUN MTU应用和超限IP处理，以及Android↔Linux业务/丢包恢复/同SOURCE物理设备和性能，仍待独立事实验收。不要将构建、符号和Host纯逻辑测试当作已经在手机实际收到成熟反馈。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B13复用原PLAN027低率QualityTx为Android Fixed source真实M4 copied PN、同owner Kind1 START/CLOSE、原认证M3 3s成熟matched报告，条件严格才APPLIED；Linux Fixed QualityRx复用，同源码9数读回及测试；模式仍闭门。"}
```
