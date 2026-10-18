# M3→M0：017 FEC2 真实 ISA-L 构建/同 VM 配对入口（跨所有权阻塞）

日期：2026-10-18。任务 `R5-M3-FEC2-CODEC-NATIVE-017` 已在 main registry 登记；本请求仅指 M0 持有的 root/shared native build/CI 和能力/kind 协商边界，M3 不代改这些路径。

## 已查事实与阻塞

- `main` 包含 `native/isal-safe/src/lib.rs` 和 `native/isal-safe/build.rs`，`crates/wbd-codec/Cargo.toml` 定义 `native-isal = ["dep:wbd-isal-safe", "wbd-isal-safe/native"]`。安全 FFI 需要官方 ISA-L v2.31.1 / `c387163fcbca62701d646149564c550c78a4f985`。
- **当前正式 worker 分支** `work/m3-r1-codec` 没有 `native/isal-safe`，codec Cargo 也未声明 native feature 和该依赖。M3 不跨越所有权修改 root workspace、`native/`、锁文件或 Actions workflow，更不复制已验证的 SIMD 数学内核。
- M3 新 `crates/wbd-codec/src/fec_v2.rs` 已提供 `#[cfg(feature="native-isal")]` 的真实 `Tables::new/encode` 分支，仅在调用成功后返回 `NativeIsaL`；`RequireNative` 在当前默认无 native feature 时返回 `NativeUnavailable`，不把标量 fallback 标 native。
- 016 独立冻结 `422a26127496560c0a52e6745ecc8f354e3f4f18`、旧 Go V1 vector、old AB/BA cpu/block；这些不能证明 V2。
- M3 worker Actions 目前只能跑默认 scalar 新独立规范，`M3-017 real native`、Linux ARM64 native、Windows x64 native、V2 paired cost **NOT_RUN**。

## 最小需 M0 提供的接口

1. 在 **M0 所有权下** 将既存 safe ISA-L 构建对本轮隔离 codec 源码提供真实 feature/lock/native 依赖，或提供只读源锁定合成 job：从本 worker 精确 CODE SHA checkout `crates/wbd-codec/**`（含本轮 test），其余来自 M0 精确 main/control SHA；产物清楚记录 worker/control/compiler/target/feature/upstream ISA-L/cache/binary SHA。不要从移动分支读错源。
2. Linux x86_64 native job 先独立编译真实 `--features native-isal`，再运行 `record_frame::fec_v2_oracle_tests::r1_f2_real_isal_exact_rows_and_missing_only_native_equivalence` 及 `r1_f2_prepared_native_cached_tables_real_ec_encode_data`；逐字节比 V2 independent oracle/scalar，不拿旧 Go V1 相等作为标准。输出 `NativeIsaL` 实际调用证据，缺 feature、fallback、仅 cross build 一律不可计。
3. 同一个真实消费 VM：先编译一次、产物 SHA 固定，单一 FEC2 codec 场景 `k16/r16/L1202`（1200B 帧含 2B protected length），同一批确定字节、缺 `e=4` 的 encode+missing-only recover，在消费 job 里顺序 AB 与另一次同 VM BA 两腿；明确 Rust Release/compiler、ISA flags、容量、热身、有效 CPU/wall 时间窗、每 block CPU、backend 与 binary SHA。跨 VM 绝对时间不可直接比；旧 V1 工作包012/016结果只是参考。
4. Linux AArch64 必须 native runner 真实执行 NEON；Windows x86_64 必须 native runner 真正执行官方 Win64 ABI/GF 与 bridge load；cross-build 或 QEMU 不冒 native。容量不足时按包内要求停止更重工况，不静默丢 30/50/100 Mbps 资格。
5. 公共 kind2/3、`fec_v2_rs16` capability bit2、V4 admission/KDF/auto-mode、MTU budget 接线一律由 M0 协调，V2 默认 OFF，不因局部 codec PASS 启用产品。

## 收据要求

提供 source-locked workflow run/attempt、build+consume job id、校验过的 manifest/artifact digest、编译和所有 test 原始日志、实际 NativeIsaL 后端选择、AB/BA 分别观测的 CPU/ns/block 与汇总。M3 继续完成自己的 codec 修复与证据；M0 不必为了普通提交/H 或局部 PASS 先合并，可在完整017提交后做最终有源锁验证。正式公共构建入口未就绪时以 `BLOCKED_SHARED_NATIVE_INTERFACE` 留痕。

历史 H30 审计 `39046275022` 为失败（`result` 非 PASS），此请求不更改旧证据、不声称其已过。
