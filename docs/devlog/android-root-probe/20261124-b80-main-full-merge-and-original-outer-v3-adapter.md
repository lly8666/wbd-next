# B80｜完整同步 main 与 Android 原表演式重传适配

**2026-11-24 最新用户决定（B80）**：每次从 main 同步已正式合入的全部源码、功能/优化与历史（真实双亲 merge，保留 Android 专有代码），平台差异只在 Android Bionic RAW/TUN、Root/Network、App 冷设置等适配层处理。优先复用 main 共享核心，不复制一套协议/算法；main 的 Windows/服务端专有逻辑保留源码而不误启用在 Android。Android 必须适配原表演式/机会式外层重传，旧逐 record M2 Receipt 已废弃，禁止复活。高级 CN FakeIP 仍明确 OUT_OF_SCOPE；普通 CN DNS 与真实 IPv4 内核直连保留。

**B80 WIRED_CANDIDATE**：冻结 main `5b1311c0748452c1c8dac66fc2a6e517777529fa`，双亲 merge `a0d31730e772dea9d1884076c945c7c810b879c9`（Android 原父 `1997efa2d89b52e11f21037c7972deee9139a0c0`）；206 个 main 变化文件完整同步，两个 Rust 重叠文件三方无损重放、Cargo 双依赖合成、Go manifest 按实际合成 blob 更新。Android Normal/Fixed/Auto 单 lane 与 Game2/4 off/fixed 复用 main `CosmeticOuter` 的 Normal-v3 `OuterAckIndex`/`ReceiptState`/9% pacing/10% quota，按真实 kernel copy 保留原密文一次，RAW ACK/SACK 元数据、Go 已协商 SACK、Game 物理 AEAD 后 ACK、现有 TX owner due/readback 和 Stop。Android 单 lane 使用同一个 main Game v3 控制器，不冒称已移植 Linux Normal process-global allocator。App/Go 显式 ON/OFF，旧 Android 预设默认 OFF 至实体资格，七模式开关可用性仍须同源构建和实体验证。main 8472 官方 CN 域名快照/手动更新源码已同步，Android 现役仍是经验证的 8503 typed snapshot，普通 CN 数据资产与冷导入适配另续；Linux H2376 满队列公平算法同步，Android 直接 TUN 不凭空加 Linux SharedTun 队列。旧 B79a 9 SUCCESS/1 FAIL/5 SKIPPED，APK 旧七模式 padding 拒绝断言已全部改正并补 App 开关往返正向用例。当前 SOURCE CI/实体/性能 NOT_RUN，不把接线当 PASS。

## 实际施工

- main 父 `5b1311c0748452c1c8dac66fc2a6e517777529fa`，Android 父 `1997efa2d89b52e11f21037c7972deee9139a0c0`，双亲 merge `a0d31730e772dea9d1884076c945c7c810b879c9`。保留 main 202 项单侧变化与双方4个重叠文件，Android 550 项分叉变化不覆盖。原主线性能反证、PLAN030/Windows当前工作文档随历史保留；尚未合入 main 的 PR 不带入。
- 共享：`Cargo.lock` / `crates/wbd-engine/Cargo.toml` 合成 regex 与 regex-lite；`v4_embedded_go.rs` / `v4_presentation_ack.rs` 双方原修改重放核对；main Go assembly manifest 三处 create blob 指向实际 Android 合成源码。
- Bionic：`android_root_io.rs` 延续 A48 DATA 的原 M3 pending parser，额外返回 ACK/已协商 SACK，纯 ACK 不进 M3；`v4_owner_crypto.rs` definite copy 后借原 ciphertext；`v4_android_original_m4.rs` 同一 Normal-v3 控制器的 single-lane adapter，真实首发/一次复制/预算、ACK、现有 TX deadline，Stop 清理；`v4_android_game_m4.rs` 复用 main Game group 控制器，物理 AEAD 进度先于业务 TUN 去重，shared group budget、实际原密文复制。
- App/Go：七模式原 `--outer-repair on|off` 真实 FFI，SACK 来自原 Go SYN/SYNACK handoff，配置持久化/四槽/导入导出保留旧 OFF；实际 native readback 只报告 enabled/copies/first_wire/repair_wire，不伪造旧 Linux 详细计数。无新线程、socket、PN、协议或逐包 Go/Java。正式 Android 默认 ON 与性能待实体资格，不先变更旧预设。
- 旧 [B79a 产品 CI](https://github.com/lly8666/wbd-next/actions/runs/45341177983) 9 SUCCESS / 1 FAIL / 5 SKIPPED；[APK Job](https://github.com/lly8666/wbd-next/actions/runs/45341177983/job/138265982866) 失败是原 Java Auto TLS 启动填充旧拒绝断言，Fixed/Game 相邻旧断言一并正向化。新 Host/dual ABI/APK/oracle 待同源 CI，不擅自测试手机/服务器。
- Main H2376 公平与最新 CN domain 源码历史已合，Android 是否有等价满队列及普通域名快照 8472 的 data/cold importer 仍待适配；高级 CN FakeIP 不做。参考 [main scoped outer closeout](../../devlog/M0/20261124-OUTER-REPAIR-SCOPED-CLOSEOUT.md)、[H2376](../../devlog/M0/20261124-PLAN029-H2376-FAIRNESS-CLOSEOUT.md)。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Full main two-parent sync, shared Normal-v3 cosmetic outer controller adapted to Android original Normal/Fixed/Auto/Game2/4 native M4, actual cold on/off/readback, fixed stale seven-mode argv tests, current scope and no Android advanced CN FakeIP."}
```
