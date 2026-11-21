# B12b/B12c｜Android 原 Fixed TX source/parity 与真正 Go/Rust Pending Bridge

起点 SOURCE `b429d3a474fee3b7a0f005722a00ebbbea72bc42`：B12a 真原生 ARM64/x86 Rust 单 M3 重放 FEC2 RX/TUN 编译已通过，但 Fixed 数据来源与原 Go 请求没有连接，Android 仍拒绝 Fixed。此片只推进无设备依赖的真实原生源发送与原 TLS 冷控制，不伪装最终验收。

## 真实生产组件

- 同一个 Bionic TX readiness worker、预留在原 M1 Arena 中的 TUN source，调用跨平台原 `FixedStream::offer_source`；使用已有 `fec_v2::source_into` 与 `ProtectedScopedOwner::seal_fec2_product_one`，同 PN/AEAD/FrozenRecord 后用原 `send_staged` 进实际 RAW 内核 socket。
- 同一个 TX worker 的空闲或新 source batch 之后，一个 turn 至多一个现成原 `poll_parity_quanta(...,1,...)`（最多4修复行）；原 M3/RS16 + 原 AEAD/PN + 同一 RAW；`DriverProof::Copied` 仅发生在真实原 `send_staged` 的 PN 相等与 copied 正结果，其他为 NotSent。没有第二网络线程、回调 Go DATA 或平行 PN。
- 原 Go Android Fixed PENDING 复用 Linux 源码 `stageOriginalFixedPending`/readback 的原 TLS身份、方向和 revision，不用假成功。Android 新原生 C ABI 只在原 committed TLS feature7、相同epoch 及未启worker 时接受 pending；只有真正 RX APPLIED 才可能读到 applied=1，当前该修订仍0。
- 真正 M4 `fec2_source_raw/fec2_repair_raw/fec2_source_tun/fec2_recovered_tun` 四个低频只读计数（发端真RAW成功、接端真TUN成功）由同一 original Go Bridge 读取，不从 queue acceptance 计数。Stop/join 后先 `FixedStream::stop` 退休原 source/parity，再终止 M1 crypto 和 scoped socket。
- 同 SOURCE 的签名 ARM64 APK 构建要求原 Rust ELF 真导出 `fixed_stage_pending/fixed_pending_readback/fixed_m4_counters`，源码 Host 门确认 source/parity 不回退Normal LINK；原 Linux/Windows共享代码逻辑不改。

## 明确仍未完成

Android 原 Go ConnectAuthenticatedPeer 的 Fixed/Auto pre-TLS 拒绝保持；`loop_start` 继续只允许 feature3。未实现真正反向 M2/质量反馈的原 FEC APPLIED、Auto无跨修订改配、Fixed大IP分片与有效TUN MTU，因而 **Fixed/Auto尚不能选用**，系统不会替用户开FEC。代码级双ABI/签名APK/Host/Linux Oracle与真机Android↔Linux SYN/TLS/M4/性能独立报告。下一步唯一关键是 M2 reverse + TX/RX pending到 APPLIED 的真实所有权转移与TUN容量匹配，完成后再开放 Fixed。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B12bc Android真Rust FixedStream source-first、parity最多4行/turn、同原PN/AEAD/RAW-copy与Go TLS Fixed PENDING ABI读回，实际来源四数收据，Stop/join收敛；M2与模式授权仍未完成。"}
```
