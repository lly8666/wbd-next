# M3 R5-M3-FEC2-CODEC-NATIVE-017：FEC2 RS16 Cauchy scoped handoff

时间：2026-10-18，授权：main registry M3 `assigned_task=R5-M3-FEC2-CODEC-NATIVE-017`、`reservation_revision=2`、`assignment_epoch=1`、`work/m3-r1-codec`。

## 前置恢复

- H30 前 worker `HEAD=093e6f7bbc5f933172d95d5610c7a272d3e66e3a`，cursor `checkpoint_sha=09a181d679d050fe7d07c473feaa54b1a411c4be`；差额 1 commit、仅 cursor，旧016 native/scalar/old-Go source CODE `422a26127496560c0a52e6745ecc8f354e3f4f18` 完全保留。
- H30 中央 `39046275022` 实际失败：`SCOPE_AUDIT_FAILED: verified cursor lacks reviewed PASS evidence`；不篡改既有 `result`，不能称 H30 PASS。恢复新 evidence `docs/evidence/M3/017-intake-recovered-H30.json` 与 H31 cursor 后启用017。后续本 worker 分支 push Governance 亦可能因结构/旧证据审计独立 FAIL；任何局部 codec PASS 不消除该红灯。
- 016 原 `422a...` Go/Scalar/native + AB/BA 独立工作量测、Go V1 56B头资格均冻结；不继承到 V2。V4 认证、独立 record 和 same Seq same wire 不变。

## 新源码（仅 codecs + M3文档/cursor）

- `crates/wbd-codec/src/fec_v2.rs`：全新 `Rs16`，GF256 `0x11d`、公式 `C[i,j]=(32+j)/(i XOR (32+j))`；row0 XOR，k1 20 行重复特例，无旧 Go matrix 字节互通。七 profile 比例和 `r=ceil(k*rho)`，1≤k≤16，1≤r≤20。
- 独立 kind2/3 **record payload 内** 10B SOURCE 和 12B REPAIR 大端字段，`block_id:u64`、source index/zero flags、repair row/k/L；数学源是 `original_len:u16 BE || frame || zero_tail`，修复中的前缀原长被同样保护。SOURCE parse 保持零长帧合法，REPAIR 严格要求 12+L 一致；所有输出显式预算 `record_payload_budget-14`，不二次扣 Game16/LINK20。
- `encode_into` 可借源写最终 owned/borrowed parity 输出 buffer；每 owner job 至多4行，dirty output 本次覆盖，缺长的数学尾是零，严禁读取池 capacity 尾；`PreparedBlock` 为多个≤4行量子只保留 **1 份** length-prefix/zero-tail 数学输入，native GF tables 按同 block `(first_row,row_count)` 有界复用，block 退役自动释放。无需线程池/独立 scheduler。
- `recover_missing` 先校验给定已认证 REPAIR 的 block/k/L、重复 row、已知源长度，再用仅 e 个缺源与 e 个合法独立 repair 行求 e×e 逆；缓存初限64 key。输出 direct fused 系数、保护原长、校验 zero_tail，返回仅缺源；结果复用已分配输出缓冲（仅原地移 2B 前缀），避免额外全帧 `to_vec()`。
- `BackendChoice::{Scalar,PreferNative,RequireNative}` 和 `BackendUsed` 明确标识；当前 worker branch 没有 shared `wbd-isal-safe` native feature，`RequireNative` 给 `NativeUnavailable` 而非假 native；源码 `#[cfg(feature="native-isal")]` 路径需 M0 共享构建后以 real `Tables::encode` 证明。scalar 短块 `L<64` 保守 fallback。
- `crates/wbd-codec/src/fec_v2_tests.rs` 通过 `record_frame::fec_v2_oracle_tests` 命名空间运行，不污染旧 R0 的 13 个 WBC/WBG filter。验证独立 GF multiply/division oracle、所有 k×7 profile、MTU/污尾/BE golden、partial、全部 missing count、零长、row0/k1、malformed/长度+identity、非前缀 parity 组合、cache上限、prepared table reuse；ISA-L guarded 测试等待 feature。

## 未声称的范围

当前代码只是独立 standalone codec；FEC2 kind2/3 和 capability 必须由 M0 原 TLS/admission/KDF 下安全启用，不能凭 magic 嗅探。未经认证、epoch/direction、RX 逻辑首次交付、block freshness/TTL、owner 组关闭 T、parity fairness、backpressure、真实 MTU/driver、Game 4lane、PN/AEAD 仍归各 owner；本 codec 不接自定义线程、不中断原 V1/off 短路。跨模块公共协议/MTU语义交 M0。用户产品 **FEC-on NOT_RUN/default off**。

阻塞详细在 `docs/devlog/M3/M0-REQUEST-PACK017-NATIVE-SHARED-INTERFACE.md`：M0 提供真实 Intel ISA-L v2.31.1 wrapper 的 worker source-pinned Linux x64/aarch64/Windows native 编译/测试和单一 16:16 L1202/e4 AB/BA 同VM成本入口；cross build≠native。不得用旧016性能或理论模型替代新017。完整独立证据将采用 SOURCE 命名保留推送后的 Actions run/attempt、manifest、artifact digest、失败历史/回退路径。

## 回退

源码隔离：无 codec V1 API/wire/record/Go/ABI/CI/public config 变更。M0 若尚未启用 V2 保持 FEC off；如验证发现 V2 缺陷，显式禁用 `fec_v2_rs16` 协商/feature，使用旧现有独立 record/off，而不是在同 session 内猜旧 WF 或把旧 Go FEC matrix 当新算法。已发已认证相同 Seq 重传仍须使用其冻结密文。

## 验证分类

- 旧 R0 wire 精确 13 PASS 与既存记录见源码锁定 Actions （见单独017 evidence）；不因 F2 新测试进入而提高旧 13 的计数。
- F2 scalar 源码锁编译与功能、negative/e×e/owned 重复批：以最新 Action 有源锁收据为准。
- F2 real ISA-L Linux x64 / AArch64 native / Win64 native 与 scalar 等价：**NOT_RUN，缺正式共享构建入口**。
- F2 Release AB/BA 单源固定16:16（+e4）CPU 同 VM：**NOT_RUN**，旧016比值不可代替。
- 实际帧 p99、source 首发/成组率、30/50/100Mbps、真实 NIC/MTU/Go V4、FEC-on 产品：**NOT_RUN**，由 M0 后续集成，仅组件结果不构成产品资格。

## 2026-10-18 · CODE8cc 的真实 FEC2 ISA-L/e4 功能及组件成本：已验，不是产品

M0 提供新共享 build+consume exact SOURCE 入口：main control `f088ca04541df962d483751a759959ac3caf0c39`，worker `8cc5b06d6832565a80b60402a5fe2e1078e9ab2e`，M4 native build `7cef7e849e293373d907a3b64007b4ce8946da78`，官方 ISA-L `c387163fcbca62701d646149564c550c78a4f985`，Linux x86_64，Rust1.85.1 `--release --locked --features native-isal`。Actions run `39090941413` attempt1，两 job success；F2 独立数学/帧/真实 ISA-L 原生测试 **11 PASS / 0 FAIL**，k2 Maximum r3 合法批与非法四行双后端反例均通过。不改变 scalar/Cauchy 数学或退让 InvalidRow 校验。

同一 Actions consume 进程、同 VM、同已锁定 Release binary 的 k16/r16/1200B、e=4 缺源 `[1,5,10,14]` 编码+恢复，400000 blocks 与 400000 次 e4 decode 每腿，ABBA 顺序 scalar/native/native/scalar；4腿 parity/recovery checksums 一致、所有 CPU 及 wall 分段都达到事先阈值（最低 113 ticks、1.13s）。scalar/native *内核进程 CPU* 比：encode AB57.33588/BA57.73846、e4 recover AB=BA17.58407。不得放大到 packet 首到/p99、host goodput、500Mbps 或 FEC-on 产品性能。

M3 已独立下载/rehash GitHub build/result ZIP，以及全部10份成员的 SHA256，核对原 manifest/receipt、二进制与日志；确切校验摘要、输入 SOURCE、测试计数、CPU数据见 [M3 S 收据](../../evidence/M3/017-8cc5b06d6832565a80b60402a5fe2e1078e9ab2e-real-isal-e4-abba-partial.json)。原 M0 同批 [证据](../../evidence/M0/M0-FEC2-CODE8CC-qualified-native-ABBA-f088ca04541df962d483751a759959ac3caf0c39.json) 为共享来源；本 M3 核验更进一步单独核对ZIP完整性。不需要重新跑已通过的 Linux x64 固定内核场景，也不把此前 CODE301 native 两次 FAIL 和 96-block CPU_INCONCLUSIVE 擦掉。

**仍待 M0 共享接线：** Linux aarch64 与 Windows x64 上的 *M3 FEC2 codec 数学/真实 native tests*（不是已通过的 safe-wrapper 小测试），以及 NEON指令真实分派/Win Go bridge load 有各自独立归属。main 预留 capability/kind2/3 默认 OFF，首次包、M1 owner/MTU/Stop/Go/GUI/Game/raw/TUN、p99/物理均不属于该 scoped CPU PASS。

**治理单独缺口：** M3 H35 常规 Governance `39088913192` FAIL，日志 `ROLE_SCOPE_FAILED: control or source moved mid-audit`，不能记PASS；中央只读 scope `39089044776` FAIL，原因为超过 `.governance/policy.json` 的 `max_delta_commits`，`M0 must accept an intermediate scope receipt`。main 原始 checkpoint M3 从 `0ecb459c9686254625a045ea19b85ae0e8d43080` 开始；此事要求 **M0 全源审核并接受新的中继scope checkpoint**，不能由 M3自行改main，也不能仅扩大“终身”提交预算。M3 普通 H 仍如实 `partial/unverified`，单独向 M0 传最低请求。旧 H30 `39046275022` evidence非PASS FAIL 永久保留。
