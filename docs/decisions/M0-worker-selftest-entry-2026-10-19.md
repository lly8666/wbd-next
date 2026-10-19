# PLAN-009：工位自主测试，M0只补一次公共入口

2026-10-19用户要求将工位测试解堵方案提交给M0合并。本文补充PLAN-008，不替换现有任务/权限或产品验收。入口实施前不得写成工位性能验证已可用。[核验记录](../evidence/M0/PLAN-009-worker-selftest.json)。

## 1. 事实与决定

- M1 SOURCE `64102db5e101df1f678e17919169927ad19bad06` 的worker-native `39188056715`为SUCCESS，工位记录133项通过；M3 SOURCE `437cc721d1009c835cb900384dadbdbf3ebea800` 的 `39187710688`为SUCCESS，工位记录默认/scalar 123项通过。本次独立核API身份/结论，未重新下载全部功能工件。
- push功能CI可自测，但专项旧新性能workflow固定旧SOURCE/夹具。M1/M3可以写模块测试，不能修改共享workflow，因此都请求M0代跑最终成本验证。
- 审查中M3又提交 `a5de4452a7c240d4866352de157deed3565a17b6` 的本模块ABBA夹具，H38尚未覆盖该提交。接班先恢复事实，不将CODE437绿灯当最新夹具已验证。
- 这不是按工位划分的GitHub账号权限事实。`permissions: contents: read`约束job token，不等于聊天账号不能dispatch；403须区分API限流、凭据权限与分配失效。

**决定：M0维护一个薄公共Actions入口；worker维护自己的夹具，自行留intent、触发、核验、修复和复测。** M0继续共享接口/依赖和产品集成。已有push功能CI、中央scope审计保留，不另建调度平台、审批队列或状态数据库。

## 2. 归属与发现

| 内容 | 归属 |
|---|---|
| 一个公共workflow、薄runner、共享native构建与产物校验 | M0；建议 `.github/workflows/worker-component-validation.yml` 和 `tools/worker_component_validation.py`，复用既有构建/hash/receipt工具 |
| 模块场景输入、断言、benchmark及结果解析 | 对应worker，放现有allowed_paths；M1为 `crates/wbd-engine/tests/`，M3为 `crates/wbd-codec/`；新测试名不逐条写死进公共workflow |
| 请求、证据、日志、cursor | 原角色requests/evidence/devlog/cursor；S→H不变，M0不代写工位进度 |
| 产品组合、共享ABI/root依赖、正式驱动和产品资格 | M0；组件测试不打开生产能力门 |

已发布入口覆盖的包内测试具有持续授权，不逐次批准SOURCE、测试名、seed或修复重跑；仍需唯一request和有新信息的复测。worker更新自己夹具无需先合main。新增共享target/依赖/跨模块接口才一次协调。

本轮无需开放worker对 `.github/workflows/**` 或 `tools/**` 的写权限，不更换task ID/epoch。PLAN-008链接本文让当前registry任务自动找到补充；长期提示词保持通用。入口完成后，M0在本文或配套证据登记**实际workflow/ref与可运行示例**；此前明确 `PLANNED_NOT_IMPLEMENTED`。

## 3. 一个入口，两阶段

### prepare：编译和功能验证，不报性能

1. worker先推源码/夹具S，再推引用S的功能请求I。请求沿ACTIONS_CONTRACT既有身份字段，增加精确配置文件路径/hash；详细fixture/config放模块允许路径。不要求请求填写自身提交SHA，不新造任务表。
2. 从**主线已发布的冻结control ref**启动公共workflow，只需输入 `role_id/request_id/request_ref`，由role定位请求；`request_ref=I`为完整SHA。M0每次入口版本发布一次固定 `qualification/worker-ci-<版本>`，不移动旧ref，普通实验复用它，不逐请求由M0打标签。request的dispatch_ref记录真实控制ref；candidate/harness/request源码独立核验，不能假装workflow是在候选树上运行。
3. 启动时读取最新main registry并保存SHA，核active/branch/task/epoch/revision及I在登记分支的祖先关系；分支后续前进不使历史S失效，角色已重新分配则停止。配置/adapter路径归本角色且无越界，package/target/features由公共入口有限约束；输入不直接拼shell，不能覆盖共享文件。
4. 初版仅落实Linux x64 M1普通Release、M3真实ISA-L Release两种适配，不先造全平台框架。源码可直接构建就直接checkout；确需把旧工位模块装入已验证共享root，使用M0固定精确路径/hash装配清单，旧新共享root/wrapper/lock/flags完全相同，仅替换被比较模块。manifest给出组合控制源和模块源，不能把合成构建当完整原树。
5. 一次编译功能/bench产物，运行本次受影响断言。已有同SOURCE同feature证据可复用，scalar通过不能替代新增native cfg。失败保留日志，不输出“合格可消费”。prepare的时间不是正式成本结果。
6. manifest记录source/harness/config、平台、工具链、features、Cargo.lock、共享overlay/native库、各二进制hash。两份独立二进制、或同一二进制内精确旧新模块都支持；后者核两模块Git blob/hash和实际调用版本，测试内写死candidate字符串不是来源证明。
7. prepare产出真实artifact ID、run/attempt、manifest SHA-256和已验范围。worker核验后再建性能请求；build hash未知时不填假值，也不拿源码hash代替。每次新源码只重编受影响产物，后续不同测试复用。

### paired：消费固定产物，一条Action一个性能场景

1. 新请求引用已存在的leg manifest hash、build run/attempt/artifact ID及共同scenario/seed/config/harness。消费核平台/features/native后端和各文件hash，不取latest；准备结束再计时，测量中不编译、下载或安装。工件过期/hash错就停止并补prepare，不静默换源。
2. 单个测量job顺序运行旧新，默认 `paired_ab` 的AB或BA。功能矩阵/编译不混为性能，独立工位Actions可以并行；concurrency含role/request且不取消正式测量。
3. **复用现成ABBA**：M0可在现有request/receipt校验器增加有限 `paired_abba`：恰4 leg，ABBA或BAAB，A/B各固定一个SOURCE/build身份，单job、不重叠、工况相同，并补正反例。不要将4腿伪装为samples=2或丢后两腿，也不强制每个优化4腿。历史4腿证据保留原口径，不能倒写成新校验器已验证。
4. M1两二进制、M3单二进制都可，不把单进程变成全局要求。两边夹具、输入/缺源、warm-up、结果校验、native后端、线程数/编译优化一致。诊断/分配计数扰动CPU时两边保持一致并标范围，不据此宣布生产默认CPU。
5. 每leg记录CPU时间/wall/工作量/checksum、RSS或有界内存、必要分配/缓存统计；host CPU/ISA、核数/配额、CLK_TCK、PSI/steal和区间齐全。CPU窗口按实际分辨率判断，不能硬编码100 ticks=1秒；时窗足够不继续加量。warm/cold cache分清，本轮主测声明的steady成本，dirty/eviction另验功能。
6. 相同有效工作量比较CPU/操作，不靠少解码/少交业务/少发副本变快。分配请求字节不是复制字节、RSS不是live payload，未测指标记NOT_INSTRUMENTED，不为补完所有计数无限扩夹具。
7. 原FAIL/INVALID/CAPACITY_LIMITED/INCONCLUSIVE/NOT_RUN保留。产品单核/锁瓶颈不能都推给host；背景容量异常或量化不足就停止更重场景，不宣布改进。无新证据不刷seed、无固定收益百分比门；必要复核才补一次相反顺序并复用同产物。

### 恢复与运行身份

仍用intent→查run→dispatch→验产物→S/H。run-name以role|request_id开头；核run/attempt/job/manifest，超时先找已发生run，重复标DUPLICATE不能挑好的一条。workflow名字带M0不等于worker不能调用。限流按实际reset合理退避，不扩大量查询；工具确无dispatch权限时留明确失败，由有权限执行者转交**同一请求**，不反复改代码假装解决账号权限。

中央scope独立证明写入边界，不在每次prepare/paired前重扫所有工位历史；入口只核本请求必要身份/路径。scope未验不写PASS，审计API限流也不等于native功能失败；M0集成时仍核对应精确SOURCE的必要scope证据。

## 4. 先接已有夹具，不重复开发

**M1 Game015**：旧 `c80ff6a52ee58860f7c108307fe25d74438703e2`，候选 `64102db5e101df1f678e17919169927ad19bad06`；已有 `crates/wbd-engine/tests/m1_game015_same_vm_cost.rs`，blob `4c70bedf3bd4d07e959eaf73dcd63feb1ebe2821`。同一fixture精确放入两树，release两二进制，共同inputs/first/duplicate/complete/checksum。方法见原M1请求。M1自己完成成本验收，不重跑无变化133断言。

**M3 FEC2-018**：旧 `8cc5b06d6832565a80b60402a5fe2e1078e9ab2e`，CODE437优化；最新夹具 `a5de4452a7c240d4866352de157deed3565a17b6` 的 `crates/wbd-codec/tests/fec2_plan008_abba.rs` 和 `tests/support/fec_v2_code8cc.rs`。先核旧snapshot等原blob `26881b892af8845120721d66108a4a03154be223`、新模块等CODE437并实际编译。复用单进程k16/r16/1200B/e4 native旧新ABBA，不重复scalar/native竞赛。新增cfg用例 `r1_f2_native_decode_tables_and_workspace_reused_dirty_tail_exact` 必须运行；native依赖沿已验证wrapper与official ISA-L pin，记录hash，禁止静默回退scalar。

上面是审查时快照，执行前核工位新提交/已有run。修复后用新SOURCE；M3夹具尚未证明能编译/通过，失败归M3修复，不能把入口可用当优化成功。工位旧“只能M0代跑”请求在入口发布后按本决策接续，不必等待再分配。

## 5. M0一次完成与退出条件

1. 在当前025中补这个短前置，不新开派单轮、不停独立开发。先核有无等价入口，有则参数化复用；不让用户重复批准。
2. 实现薄入口、两阶段调用、M1/M3构建适配、有限ABBA校验与使用说明。无路径扩权则registry不变；不修改worker源码/cursor，需要fixture适配由本工位做。
3. 一批便宜测试覆盖：错role/task/epoch、越界path、源码/hash不符、缺leg/顺序错/时间重叠、ABBA混工况/同label不同SOURCE、scalar冒充native、失败/过期artifact、残缺日志。复用工具tests，不每反例一Action。
4. Actions做入口回归，再用当前M1/M3待验工作验证真实调用路径，可由worker自行发起，各自独立性能Action。入口正确返回代码FAIL/INCONCLUSIVE也可证明基础设施有效，不要求优化一定变快才能交付入口。
5. 主线登记实际workflow/ref、请求示例、产物消费方法和入口证据。工位自行改过时“等M0代跑”下一动作。M0继续产品纵向集成，M1/M3验完交付冻结模块。M2/M4随后复用，不以全平台/所有模块适配挡住这两项。

**收口**：无需M0改CI源码或代dispatch，M1/M3可对包内新提交自行prepare→paired→修复→新请求，证据可恢复，共享CI所有权和产品硬门不变。组件成本不能升级为整链路/500Mbps/p99/Windows/ARM物理通过。

## 6. 历史 v3 入口发布记录（由第 7 节 v5 取代）

2026-10-19：第 5 节公共入口已在 `.github/workflows/worker-component-validation.yml` 与 `tools/worker_component_validation.py` 实装，推荐冻结控制 `qualification/worker-ci-v3` → `3f87d3ec9c06f7362c95c301437116d53be14c4f`；[实际调用、manifest消费、M1/M3例子](../devlog/M0/PLAN-009-worker-ci-v3-runbook-20261019.md)。旧 v1/v2 独立保留不移动。精确控制 SOURCE 的 contract-smoke `39197303106`、maintenance `39197303104`、Governance `39197303044` 均 SUCCESS。实现证明仅覆盖入口静态契约/负例回归；M1/M3 的真实 prepare 和 paired run 由工位自行请求、执行及验收，当前证据仍为 NOT_RUN。M3 现有四腿 fixture 缺绝对每腿 monotonic timestamp，成品只可记 INCONCLUSIVE，不冒充 validated paired_abba PASS。M4 当前独立中央 G2 `39197439844` SUCCESS，不覆盖 M4 产品装配 HOLD。产品 FEC2 OFF、性能资格 NOT_RUN。

## 7. v5 后续版本（当前唯一推荐入口）

v3 是历史合同/回归通过的控制 SOURCE；v4 为历史冻结检查点，**均已被 v5 取代**，冻结分支不移动。当前推荐：`qualification/worker-ci-v5` → `484861e5aff4eb9098a25a42f1522e19716f09e8`。v5 增加 Cargo libtest 非零功能测试计数验证，避免 `0 passed` 也错误进入性能准备阶段；对应完整 SOURCE 的 [contract-smoke 39199797039](https://github.com/lly8666/wbd-next/actions/runs/39199797039)、[maintenance 39199797121](https://github.com/lly8666/wbd-next/actions/runs/39199797121) 和 [Governance 39199797034](https://github.com/lly8666/wbd-next/actions/runs/39199797034) 均 SUCCESS。两角色独立 request/prepare/paired 调用、工件核验和版本限制见 [v5 操作手册](../devlog/M0/PLAN-009-worker-ci-v5-runbook-20261019.md)。目前未运行角色实际性能：M1/M3 自主 dispatch/功能验收/优化交付；M0 不代工位写 cursor。M3 旧 ABBA 日志没有四个绝对 monotonic 时间区间，仍如实 INCONCLUSIVE。产品 FEC2 默认 OFF。

## 8. Forward-only v7：M3 native companion-test overlay 修复（最新共享入口）

2026-10-19 M3 原 v6 [prepare 39210496325](https://github.com/lly8666/wbd-next/actions/runs/39210496325) 真实 authorize、官方 ISA-L build、Rust Release compile 均完成，但 Cargo 目标 native 测试 **0 executed** 后正确拒绝 prepare；根因是 v6 只把候选 `fec_v2.rs` 覆盖到冻结控制树，遗漏候选 `fec_v2_tests.rs`，保留了旧测试文件。此项仅为共享 CI 装配 FAIL，**不是** FEC2 数学正确性 FAIL，M3 native 资格与同机 ABBA 仍 NOT_RUN。

M0 已在 main SOURCE `c0c192cf293a294b5962f3f064d913149eb00639` 修复候选 `fec_v2_tests.rs` 与 `fec_v2.rs` 精确同源覆盖，manifest 增加该文件的 Git blob/SHA256，实际执行整组 `fec_v2_tests` 并强制新 dirty-tail 用例被执行且 `ok`；缺文件/被 ignored 的反例纳入工具测试。**新唯一推荐冻结控制**：`qualification/worker-ci-v7` → `c0c192cf293a294b5962f3f064d913149eb00639`（不移动 v5/v6）。此控制 SOURCE 的 contract-smoke [39214403113](https://github.com/lly8666/wbd-next/actions/runs/39214403113)、maintenance [39214403124](https://github.com/lly8666/wbd-next/actions/runs/39214403124)、Governance [39214403112](https://github.com/lly8666/wbd-next/actions/runs/39214403112) 均 PASS。首次修补 SOURCE `f4f8660...` 的日志正则转义错误导致 [39214300653](https://github.com/lly8666/wbd-next/actions/runs/39214300653)/[39214300811](https://github.com/lly8666/wbd-next/actions/runs/39214300811) FAIL，保留原红灯，没有篡改控制或覆盖旧run。

主线自动分发切到 v7 的 CODE SOURCE `86cab9c50104a05024573ae9bebf442c6d6af10b`，其 [dispatch 39214553911](https://github.com/lly8666/wbd-next/actions/runs/39214553911)、[maintenance 39214553774](https://github.com/lly8666/wbd-next/actions/runs/39214553774)、[Governance 39214553945](https://github.com/lly8666/wbd-next/actions/runs/39214553945) PASS；没有新的 M3 v7 意图，故**没有实际 M3 v7 prepare**。M3 自己提交独立 `M3-018-NATIVE-E4-PREPARE-003` 完整 JSON（保留之前 SOURCE/baseline/harness/config，改 request_id、supersedes_request、control ref/SHA），普通 Governance→中央 G2 exact SOURCE 后主线自动触发。prepare 真实通过后才能另建 paired ABBA；M0 不改 worker 分支，产品 FEC2 OFF。精确证据见 [v7 收据](../evidence/M0/PLAN009-M3-v7-test-overlay-source-20261019.json)。
