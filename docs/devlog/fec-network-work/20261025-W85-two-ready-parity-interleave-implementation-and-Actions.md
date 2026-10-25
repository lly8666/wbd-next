# W85｜最多两个已就绪组的 parity 编码批次交错（Normal only）

2026-10-25，独立 FEC 岗位，`experiment/fec-network-tuning`。本条记录是**实施/验证过程**，不是某个尚未完成的性能结果、合并或 Windows/Game 证明。

## 冻结证据与目标

已重读 `docs/testing/FEC_AUTONOMOUS_WORK.md`、`docs/evidence/fec-network-work/status.json`、W79–W83 真原生收据、W84 分时段分析，并刷新 GitHub HEAD/Actions。入手时 HEAD=`cc60407c4df43a2cf1770e0ca614c2065a6a6f1a`，没有 W84 之后漏记产品测试。参考构建 `7ad0ba91b656ff8e9ee965d0c093a18e048971fb`；W80 固定最高档长 GE 1.3412%/1.5306%、W83 同进程长1.3207%/1.3026%及短0.2148%/0.1997%，历史失败和阈值不变。W84 Auto 升档期贡献主要残余，本轮不碰 Auto。

## 原代码确有连续同组排列

实际 `crates/wbd-engine/src/v4_fixed_stream.rs` 的 `FixedStream` 原仅一个 `in_flight:Option<InFlight>`，`poll_parity_quanta` 可顺序取五个 4-row M3 quanta，若 M4 32 槽剩余足够，会把同组 20 行一次顺序封装。生产 `crates/wbd-engine/src/v4_embedded_go.rs::original_fixed_stage_due` 原经过每行的 `e.owner.seal_fec2_product_one` 分配 PN/seq 和 AEAD，然后同批 `sendmmsg`；原 `settle_staged(copied,not_sent,uncertain)` 只接受单组汇总，不能直接加第二组。

## 本轮候选和不变量

- `b03a76c5`：`FixedStream` 引入一个可选 `peer`（总在途≤2），两套预备数学工作区与 4-row 输出缓存，只有第二个**已关闭已就绪**组存在且 M4 有≥2 quantum 空间才编码双组；每组仍≤4行一个 SIMD quantum，回调以 A0/B0/A1/B1 ... 顺序提供给**原** M4 PN/seal，绝不搬动既已 sealed 的记录。
- `stage_order:[u8;32]`、固定长度记录双组每一个提交行的归属；M4 真正核实 copied 前缀 + 0/1 uncertain + 未发送后缀后逐行归属给各自 job，再统计各组 `r_sent`，不提前造 ACK。未结算期间不能重编码；到期只淘汰未 staging 的剩余辅助 parity；Stop 精确释放两个 math workspace/source slabs，仍优先 source first-ready。
- 有单组或只有一 quantum M4 空间时退化成旧单组，无等待凑组、无线格式或 matrix 变更，不增加 r、外层 DATA 修复、独立线程/定时器、逐包堆分配。旧 pendingJobs=64/2MiB charged ceiling 和 closed+10ms 正常期限保持。
- 数字旁路 `interleave_stats()` + existing `WBD_FEC_EGRESS_DIAG=1` 时每0.5s输出 paired_quanta、alternating_offered_rows、single_quanta、max_same_group_run、max_ready_age_us。注意 offered≠M4 copied，更不是远端成功收货；真正 sent 仍以现有 original FEC owner `r_sent` 为准。
- 额外 math scratch 上限随实际 record_payload_budget：两组各最多一个 `k≤16` 源 padding 工作区 + 每组四个 `MAX_BATCH_ROWS` 修复输出；对正常 MTU1500 估单组≤16×(1500−14+2)+4×1500≈29.8KiB，两组约60KiB，按实际Vec capacity复用、有界；不影响已有 M1 2MiB pending source loans。整机 CPU 及每有效 GiB 要由同 VM 实测，不能因编码行数相等直接声称 CPU 不变。

## Actions 正确性与真实失败

该分支 push `crates/wbd-engine/src/v4_fixed_stream.rs` 自动触发 `network-arm64-product-build.yml` 的原生 ARM64 Rust/Go+ISA-L bundle 编译和原有 FixedStream 单元测试，另有 ARM64 maximum-row contract。第一次产品构建 Action [40201676599](https://github.com/lly8666/wbd-next/actions/runs/40201676599) **失败**：成功编译、旧测试 `m0_fixed_stream_full_maximum_five_quanta_one_genuine_m4_prefix` 假设只有 block2，实际上其测试已放入 block2 k16 + block3 k1；新增选取就绪 peer 令回调看到 block3，表明旧测试单组前提错误。随后新增双组 4-row/内核 partial-prefix 归属、single fallback、TTL、Stop/revision 测试；Actions [40201776497](https://github.com/lly8666/wbd-next/actions/runs/40201776497) 双组新测试曾因新源随后关闭时点写错而失败；[40201813887](https://github.com/lly8666/wbd-next/actions/runs/40201813887) **8 pass, 1 fail**，仅剩旧单组夹具多余 block3；两次失败保留，不能伪绿。
- `7cb64bfce4fe2539a6cfc87eae41fbb4914235d7` 将旧单组夹具第二阶段 `16` 个新包改为 `15`：先前已存在 block2 的第一个包，补15个才是唯一恰好完整的 k16，不要另造 block3。新双组测试验证 A0 B0 A1 B1... 单次 M4 的 `copied3/uncertain1/not_sent4`、一组到期另一 source first-ready、不重复、释放；老单组测试继续验证同一 staged M4 send 全20行与连续 math slab 重用。
- 最近一次源+观测 `7cb64bfc` 完整 ARM64 构建 Action [40201990439](https://github.com/lly8666/wbd-next/actions/runs/40201990439)，maximum contract [40201990341](https://github.com/lly8666/wbd-next/actions/runs/40201990341) 结果应按 Actions 重新确认。本条没有凭未完成的测试宣称成功。

## 测量决策（待事实更新）

正确性通过后，在一个 **Actions 性能 job/同 VM/顺序 AB** 用已验证原 `7ad0ba91` 对照精确 candidate `7cb64bfc`，8Mbps/方向、96% UDP混合 TCP2、64..1287B 分布、75ms单程、outer DATA real OFF、long GE [3,17,100,0]、严格1%门（失败如实保留）。收集 actual paired/alternative offered、真实 parity sent、kernel source/remote capacity、UDP总体及小包损失/p99，CPU-s/RSS及成本、同 VM host PSI。若没有足够双组就绪或收益不够，撤回候选，不升级至三四组、不堆线程或额外缓存。
