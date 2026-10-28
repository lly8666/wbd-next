# M0 PLAN026 H327｜高损载荷发生器接收热路径与真实外部CPU收据（2026-10-28）

SOURCE `c8352931` P200 双向200ms/250Mbit/s/30% 实际运行的GitHub Actions artifact `12801400551` 已下载，其ZIP SHA256 `7724cb68fb1696872e39fe404d3ccb39855aeb231c290eb4cc085c11ec389dcb` 与GitHub Actions公布digest一致，内部artifact-manifest的 SOURCE 为 `c8352931e15c954aa2c5de7a31e024af3a7eeb35`，验证范围仍CAPACITY_LIMITED、不是250Mbps网络资格。

该运行中Linux的Python发生器兼作独立接收/探测器，CPU61.2975秒占单核94.304%。为只降低**测试侧**分配压力，`m0_wl_public_rate_app.py` 在P200使用预分配2048B的 `recvfrom_into`，对每包不再申请新的整个Python `bytes`，通过 `struct.unpack_from` 就地读取唯一序号；低速N0原流程不变。该变更不修改Rust Windows worker、M2、Go EXE或任何wire。

源锁提交 `[plan026-stress-p200-250m-30p]` 只跑真实签名Windows/Linux Normal 60秒高损负载和原owned Stop，并带上前次Win32 `SetThreadDescription` 一次性冷设置以重新检查Windows Rust TX/RX CPU实际名字。新结果会独立比较实际 Windows/Linux offered、goodput、Python generator CPU和真实TC drop，仍不足225Mbps则继续报容量受限，不降低门槛。

```feature-impact
{"kind":"none","ids":[],"reason":"仅将P200测试Python的每包recvfrom分配改为预分配recvfrom_into，加上真实已核哈希的旧Actions收据；不改任何用户模式、Rust业务加密或Go稳态数据路径。"}
```
