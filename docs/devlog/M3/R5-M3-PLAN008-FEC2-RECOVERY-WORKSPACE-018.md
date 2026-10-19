# M3 PLAN-008 · FEC2 恢复工作区与解码表缓存（018）

任务来源：main registry 2026-10-19 PLAN-008、`docs/decisions/M0-integration-unblock-2026-10-19.md` §1 M3 / §4。独立 M3 分支 `work/m3-r1-codec`，只写 codec/M3 文档、证据及本角色 cursor。原017 组件 Linux x64 real ISA-L 结果已被 M0 于 `docs/evidence/M0/M0-M3-017-scoped-acceptance-unified-G2-2026-10-18.json` 接受，**不重复** scalar 对 native 的旧400k竞赛，原 FAIL/NOT_RUN 保留。

## 本轮源码与语义

- CODE `17ca59c01e8cb4c2963f466b109d7d8d1d55801b`：`fec_v2.rs` 中逆矩阵命中改为返回 `CacheKey` 并借用 `BTreeMap` 内矩阵，移除旧 `clone()`。在 `native-isal` 特性下复用对应键最终 e×k ISA-L `Tables`，以同一 FIFO 键淘汰；已知源输入的带 u16 原长的 symbol 缓冲留在 `Rs16` 内，每次按实际 symbol 长**全区清零**后重填，避免脏尾和旧 block 泄漏。所有临时内存归本 `Rs16` 实例拥有，未跨接收 owner、epoch 或方向共享。
- CODE `437cc721d1009c835cb900384dadbdbf3ebea800`：新增 scalar 65+不同缓存键淘汰、复原长度/值及统计上限测试；`#[cfg(feature="native-isal")]` 增加同一 k16/e4 丢源集跨不同 block 与帧长的解码表/补齐 workspace 复用、零尾/全值等价测试。native 新测试编译与执行**仍未验证**。
- 不更改 GF256 `0x11d`、Cauchy 生成矩阵、7档 profile、r/e 限制、kind2/3 10/12B wire、公开 `recover_missing` API、返回顺序及 owned 输出、密文认证、generation、Stop、产品开关。既有 owned API 必须将每个恢复的源交给 caller，因此没有冒称输出 Vec 可以在跨调用时无代价复用；重点是输入补齐和缓存表。

## 内存账与功能验证

`DecodeCacheStats` 列出缓存 inverse payload、ISA-L 展开表实际 **32B/系数** payload、已知源 workspace 留存 Vec capacity。最坏公开参数 k=16、e≤16、cache≤64、symbol_len≤65535：逆矩阵 payload ≤16,384B；native 表 payload ≤524,288B；私有已知源 workspace 最多 15×65535=983,025B，payload 上界合计 **1,523,697B**（约1.45MiB）。**不包括** `BTreeMap` 节点、Vec header、分配器开销或必须返回给 caller 的输出 Vec；实际工作集由新 native Action 记录。每次 `decode_cache_stats()` 可查看 retained payload，不是进程 RSS / 分配器计数。

[worker-native 39187710688](https://github.com/lly8666/wbd-next/actions/runs/39187710688) 在 CODE437 Release/1.85.1 build+consume SUCCESS，默认 Rust **123 PASS / 0 FAIL / 1 ignored / 26 filtered**；同源 wire/record/LINK/static/G2 bootstrap Actions 均 SUCCESS。两份 ZIP 及所有4成员由 M3 独立下载核对 SHA256，具体摘要、计数及精确测试 SOURCE 存在 `docs/evidence/M3/018-437cc721d1009c835cb900384dadbdbf3ebea800-default-scalar-cache-partial.json`。该 PASS 是**默认/scalar**，不包含新增的真实 native `cfg` 测试。

CODE437 普通 Governance `39187710740` FAIL，日志确指 `ROLE_SCOPE_FAILED: control or source moved mid-audit`；同期 main PLAN008-025 控制源提交，未证明 M3 角色违规。中央新 G2 `39188046597` 已使用分页 G2 而非64增量旧门，但因 GitHub `HTTP 403 github_rate_limited remaining=0` 中断，**不是** audit PASS，也**不是** 64门复发。切勿凭旧 H37 成功冒充新 CODE437 Governance PASS；下一次核定需 main 稳定/API 可用才重新跑，不能删旧红灯。

## 给 M0 的一次共享 native + ABBA 接口请求

M3 不写 main/shared workflow、`native/isal-safe`、`r0/` benchmark fixture或根Cargo。请 M0 在可用配额下集中提供**一次**源码冻结 Linux x64 原生 build+consume Actions：

1. 修复版输入 `worker-M3 437cc721d1009c835cb900384dadbdbf3ebea800`，基线 `worker-M3 8cc5b06d6832565a80b60402a5fe2e1078e9ab2e`，当前已审查 M4 `native/isal-safe/build.rs` 及 official ISA-L `c387163fcbca62701d646149564c550c78a4f985`（或更新它们时固定新 hash）。实际 `--features native-isal`，完整 F2 oracle/dirty/length/missing/eviction，包括新 `r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact`，`BackendUsed::NativeIsaL` 不得只测 safe-wrapper。
2. 旧版与新版均用相同 release/ISA-L 编译条件，将两套 Rust 源码作为分别命名的模块置于一个 test-only benchmark 二进制中；在同一 runner / VM / **单进程**固定一个 k16/r16/1200B/e4，采用旧/新/新/旧 ABBA 顺序，含真实 `recover_missing` 与校验和、分阶段 wall 与 `/proc/self/stat` CPU ticks；各阶段 CPU 与 wall 时窗不够即 `INCONCLUSIVE`，不宣称有加速，不搜索多seed挑结果。主要对比 native**旧/新**恢复成本，另按统一宿主测分配/拷贝/表创建/内存数据；`DecodeCacheStats` 是 payload 静态账，不代替实际 allocation counter。
3. 工作流 manifest 包含两份 `fec_v2.rs` / test `sha256`、`Cargo.lock`、native `libisal.a`、工具链、host/quotas、二进制、场景参数及 S/source SHA；构建一次供消费 job 验 hash，不以本地模拟或另测 scalar/native 比值替代。无跨平台 native V2 即写 `NOT_RUN`。
4. M0 保留正式 CI/性能一 Action 一工况/回退基线归属；M3 对真实失败只改本角色 codec；原017已接受 baseline 及所有失败收据不删。**FEC2 产品继续 OFF**。

## 任务状态

`partial/unverified`：默认/scalar 功能及内存静态上限已验；新版 ISA-L native、旧新同VM ABBA/CPU、运行时分配/拷贝数、跨平台 V2、产品路径仍 `NOT_RUN`。下一步只有 M0 交付上述一次共享 Actions 入口或报告不可跑原因后，M3 复核实测结果并针对真实 codec 回归修复。

## 2026-10-19 · 原生 PREPARE-004 通过，提交唯一 4-leg paired 请求

真实官方 ISA-L source-lock native [Actions 39218789735](https://github.com/lly8666/wbd-next/actions/runs/39218789735) attempt1：authorize/prepare PASS，13/13 F2 native oracle（含 decoder-table/workspace dirty-tail）PASS，Linux x64 Rust1.85.1。主机上全套原生 prepare 原始 ZIP `12170931928` 与全部4项内部文件由 M3 独立重新 SHA256 验证；manifest `cc403870009d17d135c27cfe754ef2d7feb3e314718d186c9e145a7a0450dc37`，同一 release m3-abba 二进制 `ee8bccb44ff7bba2267186f05f1cf507f2c115e22e04001af4243cd5733d05f1`。详见 `docs/evidence/M3/018-b4d638a-v7-prepare004-real-native-13pass.json`。基线 A CODE8cc；优化 B CODEb4d（仅补 #[cfg(test)] 测试模块注册）；夹具 CODE42b3。

新 `M3-018-NATIVE-E4-PAIRED-001` 独立 `kind=performance`、`mode=paired_abba`、`samples=4`、`measurement_jobs=1`、`A-B-B-A`、k16/r16/1200B/e4，每腿2,000,000恢复，必须消费上述 *同一个* prepare manifest。FEC2 product OFF。现有 runner 的 M3 收据缺每腿绝对单调时间边界；即使测试实际执行，官方评级仍 **INCONCLUSIVE**，直到另行修复/验收资格，不夸大速度。测试计数造成的 R0 wire shared consumer FAIL [39217619084](https://github.com/lly8666/wbd-next/actions/runs/39217619084)（实际23/23 passed，消费者死校验13），与 FEC2 正确性分开。

## 2026-10-19 · 真实原生 ABBA 已执行，资格仍 INCONCLUSIVE

[PAIRED-001 Actions 39229126775](https://github.com/lly8666/wbd-next/actions/runs/39229126775) attempt1 **SUCCESS**，授权与同一 VM/job `117982629177` 的实际 `m3-abba` Rust test **1 PASS**。A/B/B/A 各200万次真实 `NativeIsaL` k16/r16/1200B/e4 缺源恢复，四腿校验和均 `3400000000`（总计800万次）。同一个先前成功的 `PREPARE-004` artifact id12170931928、manifest sha256 `cc403870009d17d135c27cfe754ef2d7feb3e314718d186c9e145a7a0450dc37`，没有换版本/工况。

独立下载 paired artifact id **12175592655**，原始 ZIP sha256 `93b6a3025be943959c2c934478c3a645b7a0b02669400a87760d2529a7a77946`，两个 member `log-abba.txt` / `receipt.json` 的散列/原文一致。腿序 CPU ticks **544(A),351(B),349(B),524(A)**，clock 100ticks/s，平均 A=5.34s、B=3.50s；**本固定场景的观察值** CPU 约减少34.46%（A/B约1.526倍）、申请 heap allocations 次数由每腿6800万降至2800万（少58.82%），gross requested bytes由每腿46,368,000,000降至12,496,000,000（少73.05%）。这不是实际内存复制量/RSS；A未提供 retained payload 统计，不能把其统计0误作消耗0。

**正式收据必须维持 `INCONCLUSIVE`**：v7 runner缺每腿 absolute monotonic start/end，尽管 fixture 原生 CPU 每腿≥100 ticks/1s 且测试 PASS；不据此签发正式性能提升或产品资格。完整原始数据/哈希/局限详见 `docs/evidence/M3/018-b4d638ab-39229126775-native-e4-old-new-abba-inconclusive.json`。Windows/ARM、Go TLS、产品500Mbps/p99/物理路径仍 NOT_RUN，**FEC2产品OFF**。H47普通治理曾因 main移动两次失败，但同一 HEAD 的中央 G2已有两次 PASS；旧失败保持原记录。
