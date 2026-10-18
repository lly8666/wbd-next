# M0 R0-023 · FEC2 CODE301 真实 ISA-L / 同机 ABBA 接口（2026-10-18）

## 为什么现在做与边界

接手 main H128 后逐提交核对发现 checkpoint 后只有 H128 的 cursor-only 提交，未漏记 M0 改码。正式任务仍是 R0-023 partial/unverified；PLAN-007 公共 FEC2 bit2/kind2/3 尚仅预留，M1/M3/M4 自治，M2 待命。继已核验的原 Go clone 冷策略和三目标 ISA-L safe-wrapper 的精确 SOURCE 收据，M0 需要提供真正指向 M3 CODE301 FEC2 codec 的共享 native 构建与同机成本入口；不能复用 V1 Go 矩阵 workflow 充当 V2 证明。

本轮 S 在 main 增加 `r0/fec2_codec_abba_probe.rs` 和 `.github/workflows/m0-fec2-codec-native-abba.yml`；仅在 Actions 的临时工作树组合冻结的 M3 CODE301 `fec_v2.rs` / 独立 oracle tests、M4 CODE7cef 的 `native/isal-safe/build.rs`、原主线 `native-isal` 功能和 Intel ISA-L 固定源码。真实生产 Go admission/KDF/kind、GUI/配置、Cargo shared ABI、raw/TUN 都未改变。这个脚手架只做 **一个** k16/r16/1200B codec-only 场景、同进程 A→B→B→A，先编译一次再消费；无旧Go网络互通/旧matrix逐字节约束。

## Actions 实际结果与停止条件

精确 run/attempt、SOURCE、job、ZIP digest 及哈希核验边界在 [SOURCE evidence](../../evidence/M0/M0-FEC2-CODE301-native-ABBA-0b21a2fee11a67c5ee977ddfabc252539085890d.json)，本文不建立第二份账本。

- 首次执行的 build **PASS**、consume **FAIL**：F2 11 个原生测试中 10 PASS，M3 自有的 `r1_f2_real_isal_exact_rows_and_missing_only_native_equivalence` 在 k=2 Maximum 时请求 4 条 repair；按已冻结档位公式实际只有 ceil(2×5/4)=3 条，合法拒绝为 `InvalidRow`。旧失败保持，既不是 ISA-L 编译失败，也不能把“10项绿灯”提升为整包 PASS。
- M0 仅改 shared workflow：即使独立 F2 功能步骤失败，也让后续单场景 ABBA 测量执行，**整体 Action 仍然 FAIL**。再次执行同一个非法工位断言仍失败；没有修改 M3 worker 原始测试或通过跳过来掩盖错误。M3 017 工作包内应按合法 parity_count 修正该测试与自己的 SOURCE，不要求 M0 代改。
- ABBA 测量一项测试 PASS，真实 NativeIsaL backend 被调用，四 leg 校验和一致、每 leg 96 blocks/1536 parity symbols。但每 leg 只有约 0.34–18.4ms、CPU ticks 0–1；**CPU_INCONCLUSIVE_SHORT_WINDOW**，不从短窗口绝对 wall 比值宣传 native x倍加速。kernel payload 首到、业务 packet p99/丢失、host容量/真实带宽均 NOT_RUN。该入口与二进制本身可留用作之后 worker 修正后的有边界证明，不能继续在相同错误上重复空跑。
- GitHub 普通 Governance 与 maintenance 对当前源码 SUCCESS，所证明的是对应身份/规则/工具自测而非 FEC2 产品资格。ZIP sha256 是 GitHub artifact API 返回值，本轮没有独立下载二次哈希，`artifact_zip_rehash_verified=false`。

## 持续保留的原任务事实与下一动作

Normal/off 旧冻结源码、D10 红灯、原 240s codec timeout、P10 次序矛盾和 SPARSE p99 回退均 OPEN。原始真实 Go TLS V4→Rust raw/TUN 已证明 oversize fail-closed + 小包不受阻 + Stop/lease 可回收，但超 MTU 业务 LINK 自动分片并在 peer 端交付**未完成**；不能靠新的 codec 组件补这条产品 hard gate。FEC2 bit2/kind2/3、applied revision、GUI、Windows/ARM 完整 native codec、Game+repair 与物理依然 DISABLED/NOT_RUN。

**下一动作（M0，一项）**：沿原 V4 Go→Rust owner 路径实现/接线认证后 LINK 大包有界 fragment TX 与 peer reassembly，复用现有 M3 LINK 组件及测试入口，并把 Stop、MTU−1/等于/+1、恢复小包、旧generation/loan 的 L01–L04/B01–B04 反例在精确 Actions 验证；不要开启 FEC-on 或重跑 024/D10。M3 017 的非法 row 测试由其工位自主修复，视为独立组件阻塞而非 M0 整体主线等待门。

## H129 Governance 结构修复（recovered）

- H129 `95f9b57d8804d762bcc065e5b9728c8652a39060` 的普通 Governance run `39086745204` attempt1 **FAIL**：`tools/governance.py::validate_cursor` 对 `context_refs` 限制最多8条；H129为便利引用插入本日志但未移除旧参考，共9条，`SCOPE_AUDIT_FAILED: unbounded context_refs`。这是 M0 cursor-only 自身结构边界错误，非CODE301 codec或产品失败；不能作为 Governance PASS。完整selftest/model本次NOT_RUN。
- 立即仅压缩 M0 cursor 的context_refs（旧024历史/失败仍通过已有evidence、其它历史入口可追溯），不改分配、产品状态、S构建或任何worker源；用新的H修正，不重跑M3失败组件。原 Governance 红灯保留历史，并以修复H的精确新run判断当前交接是否PASS。

- H130 `1c53c2243fc72e792ac95226810229056a23d9e5` Governance run `39086911530` attempt1 **FAIL**：当前 cursor 的 `last_tested_source=0b21a2f...`，`evidence_refs` 同时含 `source_sha=0b21a2f...` 与旧 intake `ede83b9...`，触发 `SCOPE_AUDIT_FAILED: cursor evidence SOURCE mismatch`。修正只把 cursor 的直接 `evidence_refs` 限定为本轮同源CODE301证据。旧 intake 的独立 SOURCE / D10 / p99 / 原 normal-off 收据继续由原文件、上述本轮 evidence 与 devlog 指向，不删文件、不拼资格；新 H 仍 partial/unverified。

## 2026-10-18 补续 · M3 修正版 CODE8cc 真实 ISA-L 与足量 e4 ABBA CPU 合格窗

M3 分支精确 CODE `8cc5b06d6832565a80b60402a5fe2e1078e9ab2e` 在 `fec_v2_tests.rs` 修复 k2 Maximum r3 却要求四行的非法测试参数（保留非法四行负例）；CODE 主数学未改变。M3 worker 标量回执 `39088682284` 122/0/1，R0-wire 13/0、record6/0、LINK7/0 均通过。但 M3 最新 `work/m3-r1-codec` H35 seq35 仍记录 `partial/unverified`、请求 M0 真 ISA-L 与 CPU；其 scope/Governance `39088913192` 因 control/source mid-audit 移动 FAIL（不冒充完工或替 M3 写 cursor）。

M0 实际更新仅两个共享点：`r0/fec2_codec_abba_probe.rs` 在 `b432315a55020aa9e6e638154fe44d944b2a523d` 把仅96次编码扩大为**一腿固定400000块编码 + 400000次缺e=4数学恢复**；`.github/workflows/m0-fec2-codec-native-abba.yml` 在 **SOURCE `f088ca04541df962d483751a759959ac3caf0c39`** 硬钉修正版 M3 CODE8cc、M4 native build `7cef7e849e293373d907a3b64007b4ce8946da78` 和 Intel ISA-L `c387163fcbca62701d646149564c550c78a4f985`。Actions-only 临时 codec clone，无公共产品功能启用。Rust 1.85.1 Release，同一编译二进制/同一 Linux x64 消费 VM，确定性场景 C(k16,r16,1200B,e4，缺号1/5/10/14)，预热/正确性检查后 A=scalar→B=真实 NativeIsaL→B→A。输出编码/恢复分别 wall_ns 和 /proc/self/stat 进程 CPU ticks（机器 CLK_TCK=100）；**每个阶段每腿均需要 wall≥1s、CPU≥100 ticks**，未达时只 INCONCLUSIVE 不报比值。一个场景/seed/job，未跨 VM 比时钟。

[精确 run39090941413](https://github.com/lly8666/wbd-next/actions/runs/39090941413) attempt1 build job117567366371 SUCCESS、consume job117567553814 SUCCESS；真实上游 ISA-L native 功能 **F2 11/11 PASS**，k2 修正被正确消费，复测不再 k2 非法行失败。各腿 CPU 时长秒编码 A0=75.11 / B1=1.31 / B2=1.30 / A3=75.06；e4 恢复 A0=19.87 / B1=1.13 / B2=1.13 / A3=19.87；8个阶段均超过100 ticks 且 wall≥1s。计算相邻CPU成本比例：编码 A/B=57.33588，反向 A/B=57.73846；恢复 17.58407 和17.58407。编码 checksum 每腿7014000000、恢复 checksum 每腿680000000。**限定为同一固定codec微基准，不能宣传产品 throughput、p99 或网络加速**。构建+结果工件已由 GitHub API 返回 ZIP digest，未独立 ZIP 复哈希；build/consume 之间校验编译二进制 SHA。run artifacts build ID12122563022、result ID12122374044。

原 `39086268414`/`39086460623` CODE301 功能 FAIL 与96块短窗 CPU_INCONCLUSIVE 保留，不涂绿。Linux ARM64/Windows 的完整 V2 codec 数学真 native、Go 实际启 FEC2 bit2/kind2/3、M1调度与M4冷策略接线、D10/240s/p99 / R0-023 全产品资格仍 OPEN。完整 SOURCE 证据：[CODE8cc 合格收据](../../evidence/M0/M0-FEC2-CODE8CC-qualified-native-ABBA-f088ca04541df962d483751a759959ac3caf0c39.json)。**M0 自己继续原 R0-023，不接管 M3 独占代码/正式任务；M3 可独立据此更新自己工位 H 与治理结果。**
