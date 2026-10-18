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

## 2026-10-18 补充：M0 共享入口已提供，需源锁重测修正版（M3 独占缺陷已修）

收到 M0 source-locked [CODE301 原生批次证据](https://github.com/lly8666/wbd-next/blob/main/docs/evidence/M0/M0-FEC2-CODE301-native-ABBA-0b21a2fee11a67c5ee977ddfabc252539085890d.json)：
- run `39086268414` / `39086460623`，真实上游 ISA-L Linux x64 功能原测试 10/11 PASS，失败项为 `r1_f2_real_isal_exact_rows_and_missing_only_native_equivalence`：测试将 `k=2` 的 Maximum profile `r=ceil(2*5/4)=3` 当成四行请求；合法 codec 按 `InvalidRow` 拒绝。两次原失败永久保留。
- M3 **测试夹具**已在精确提交 `8cc5b06d6832565a80b60402a5fe2e1078e9ab2e` 修正：从 `Profile::Maximum.parity_count(k)` 算 `batch=min(r,MAX_BATCH_ROWS)`，并对 k2 原非法四行请求在 scalar 和 RequireNative 两分支加 `Err(InvalidRow)` 回归断言。**不是削弱 codec 验证或放宽 wire 约束。**
- M0 工作流 `.github/workflows/m0-fec2-codec-native-abba.yml` 当前硬钉 worker `3011431370f1757212df92800c1b56e87ba51d65`，因此已知首次失败重跑不会消费新夹具；该 workflow、root `Cargo.lock` 和 safe-FFI/平台构建属于 M0，M3 未改。

**现在向 M0 请求唯一最小共享动作**：将 Actions-only 临时构建的 worker checkout 和 input-assert/manifest 中 M3 SOURCE 一致改为 `8cc5b06d6832565a80b60402a5fe2e1078e9ab2e`（或 M3 后续正式 S 源锁 commit，如仅证据文档更新保持测试文件 SHA 不变），然后重新编译真实 `native-isal` 一次，先独立验证全部 `r1_f2_` 原生测试与真实 `BackendUsed::NativeIsaL`；必须保留所有旧 FAIL，只有新 run/attempt 的原生日志全 PASS 才可收口功能。

原 `39086460623` 四腿 ABBA checksum 相等而 CPU 测量仅 **0.34–18.4ms 每腿**，`CPU_INCONCLUSIVE_SHORT_WINDOW`。M0 请在同一固定 k16/r16/1200B、同一消费 VM、同一 Release 二进制中使用**足够长、事先约定的有界测量窗**（如每腿 `>=1s`、真实进程 CPU tick 可靠，事前固定总工作量或预热标定；容量不足直接 INCONCLUSIVE），纳入缺 `e=4` recovery 且对齐每腿相同真实 workload，随后 AB 与 BA 保留全部原始数据；禁止把原短窗壁钟比宣传为吞吐收益。流程继续只读 FEC2 codec、无 Go V1 wire 承诺、不启 product FEC-on。AArch64/Windows 现阶段只有 safe-wrapper native，不等于该 M3 V2 codec 原生三目标通过。

M3 本工位继续完成 scalar/治理 Actions 与 S→H 证据。M0 共享入口不需等 M3 任务整体完成才重新锁源执行；若公共 workflow 尚未更新，则明确 `M3_NATIVE_RETEST_PENDING_M0_SHARED_ACTION`。

## 2026-10-18 · CODE8cc Linux x64 已解决；剩余唯一共享与治理请求

M0 已按上述修复 SRC 重新锁定共享 native 工作流，run `39090941413` attempt1 **build+consume SUCCESS；真实 F2 native 11/11 PASS，k16/r16/1200B/e4 400000次 ABBA 进程CPU窗合格**。M3 独立验证两份 ZIP 和10份成员 SHA256，收据在 `docs/evidence/M3/017-8cc5b06d6832565a80b60402a5fe2e1078e9ab2e-real-isal-e4-abba-partial.json`。因此原先“CODE301→CODE8cc source swap”及 Linux x64 CPU时窗要求已经**关闭**，不要再次重复相同测量，防止用不同宿主挑好结果。

现在只请求 M0 在其**独占 shared/CI/main** 范围逐项判断：

1. **治理分段验收**：M3 H35 Governance `39088913192` 是 `ROLE_SCOPE_FAILED: control or source moved mid-audit`；M0 中央 scope `39089044776` 因从 main `scope-checkpoints.json` 当前 M3 checkpoint `0ecb459c9686254625a045ea19b85ae0e8d43080` 到新 worker 源超 `max_delta_commits` 而 FAIL。由 M0 在不跳过任何 worker commit/path、核对已审计记录后创建正式**中继scope receipt/更新 main checkpoint**。不得 M3 自改main，不提高总量限制，不把 H33/H35 局部Governance或 G2 bootstrapping 冒充中央scope PASS。
2. **跨平台 codec，而不是 wrapper**：Linux aarch64 与 Win64 各提供完整 M3 FEC2 `fec_v2.rs` + `fec_v2_tests.rs` + safe ISA-L feature 的源锁原生 runner；目前只验证了三目标包装层 `ec_encode_data`，不等于完整 V2 7档/partial/corrupt/恢复内核。AArch64 要注明 NEON 是否确实调度；Win64 的 Go bridge loader 是另一所有者 M4/M0，不可将 wrapper native PASS 冒作它。
3. 若平台条件不足，精确记录 `NOT_RUN` / `UNSUPPORTED` 并按相应 gate 保留，不扩大测试矩阵，不因Linux x64 组件PASS开启 product FEC-on。

共享工作流、根Cargo/lock、`.governance/scope-checkpoints.json`、M0原 Go/ABI 仍由 M0 拥有。旧 H30 `39046275022` FAIL、CODE301 两次原生 F2 FAIL、原96组 CPU短窗、H35治理 FAIL 保留。M3 后续只因真实新缺陷改本工位 codec。
