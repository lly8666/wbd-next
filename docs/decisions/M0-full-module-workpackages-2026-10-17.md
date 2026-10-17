# M0 / PACK-006 — 2026-10-17 本轮完整模块工作包，一次分配

## 判定与边界

2026-10-17 用户授权：M0**一次性**登记本轮其他工位完整能力包，然后继续已分配的 `R1-M0-HOTPATH-COST-024` 调优；不再每完成一包/一个参数请求M0新派单。依 `docs/GOVERNANCE.md` §3 和 `docs/architecture/TEST_PLAN.md` §0；本决策与 main registry `assigned_task` 同提交生效。包内实现→Actions→定位修复→S/H 都已授权；达到本包 `done_when` 再停。M0在安全批次/实际接线需要时集中集成，不为局部绿灯中断优化。

接手基线是**登记分支精确 HEAD，不是可据此声称组件PASS的新SOURCE**；登记时主线 `e73657f9fabdf60009f51e2b21477c767370f870`，M1 `35fdcf07b44bba2ffde249ac085902385b16eb3c`，M2 `c74a4fd71712411b1fb5b326d95d746116a04844`，M3 `0ecb459c9686254625a045ea19b85ae0e8d43080`，M4 `e19772fe65d8cfb347da3c7b182c25180ba91d37`。各工位旧cursor/checkpoint/history不因登记被覆写；新接手先自查分支，按registry本任务执行。角色active，路径、branch、reservation_revision=2、assignment_epoch=1不变。精确测试结果只能看各自source/run/artifact。

公共契约唯一入口 `docs/architecture/modules/00-CONTRACTS.md`，交付门 `11-IMPLEMENTATION-GATES.md`；其余**每个worker只加载下列本职模块页及直接依赖**，不重选架构，不传12页一套。共享C ABI/Go真正credential authority和engine组合只归M0；平台原生Go向量/ABI Actions不可用Python算式替代；生产features仍0。对已有旧任务成果只核精确SOURCE并复用；原任务partial、治理失败、NOT_RUN保留在历史证据，不自动升级为PASS。

## 这一次正式分配的四个完整能力包

### M1 · `R1-M1-OWNER-MEMORY-READY-WORKPACK-011`

- **为什么现在做**：已有early RX和bounded batch组件；M0原始Go→Rust数据worker仍有共同可变owner/registry和逐包分配。M1只补自己的运行时、内存、调度与有界回收契约，M0负责`v4_embedded_go.rs`接线。原010的88/88纯模块结果保留，不要求重做。
- **施工页**：`02-RUNTIME.md`、`03-MEMORY.md`；仅涉及Normal/Game公平边界时读`09-PIPELINE-GAME.md`。反例 **R01–R04 / M01–M04 / B01–B04 / G01（仅慢lane公平）**。
- **完整能力**：TX/RX逻辑所有权与可转移/借用接口，ready-only最大32/约100µs轮转、不凑批等待、重试唤醒（首次Wake失败还能被下一事件唤醒）、低频统计、arena slab/冻存handle及多生产者归还路径有界；parity作为首次发送服务而不是10% repair权重；Stop时驱动借用未还不free。按既有 `rtrb` / 00 buffer/clock接口，不新造完整数据面、不复制认证或AEAD。
- **允许**：仅 registry 的 `crates/wbd-engine/src/runtime/`、`memory/`、`tests/` 与 M1日志/证据/cursor/requests。**不改**`v4_embedded_go.rs`、`v4_owner_crypto.rs`、平台、Go、共享workflow。M0使用稳定接口自行组合。
- **done_when / 验证**：预编译后同一功能Action批量测 0/1/32/33 ready、Wake失败后重试、Stop和旧loan/rotation、arena多生产者return/backlog限额、parity持续fresh公平且内存不超；native组件结果与精确SOURCE留痕，实际Go/TUN综合与负载收益明确NOT_RUN交M0，不自报产品ready。

### M2 · `R2-M2-RECEIPT-REPAIR-BOUNDED-WORKPACK-009`

- **为什么现在做**：旧008 positive-witness索引已有纯组件实现但仍partial/unverified，缺把receipt、RACK/PTO、两次修复、稀疏独立与资源边界在一项完整能力内覆盖；此包接续并保留008事实，不重复发明状态机。
- **施工页**：`08-RECOVERY.md`（依赖00）；buffer归还界面只引用03既定契约，不加载别的模块施工。反例 **A01–A06 / R01–R04（timer/唤醒接口）**。
- **完整能力**：只认认证lane传入的receipt位图正证据；未报告page及PN/control洞不当丢失；shadow用同一冻结密文，代数/expiry/prefix-uncertain管理，两次attempt上限，第二次必须有新证据或PTO，dirty反馈活动驱动，稀疏无10%比例限制但次数/寿命/绝对预算有界，健康流量repair以已提交wire byte记账≤约10%；新鲜发送不等repair及shadow。
- **允许**：仅`crates/wbd-recovery/`和M2日志/证据/cursor/requests。**不改**codec/engine/Go平台/共享规则，不制造外观ACK等于真实receipt，不能假造外部TLS认证来源。
- **done_when / 验证**：fake-clock+真实FrozenRecord handle受控驱动功能Action合批证明反馈跳页、重复/乱序与ACK双丢、PTO尾包、第二次新证据、receipt到达/repair-send竞态、partial/uncertain、满环/压力/序号回绕；状态/内存/计数有界、repair不挡fresh。实Go和产品弱网资格仍待M0组合。

### M3 · `R1-M3-RECORD-LINK-FEC-WORKPACK-016`

- **为什么现在做**：已有三cipher、LINK/FEC纯组件和成本测量；旧015分配与旧014 cursor不一致，包完整覆盖它们的必要编码/资源/真实接线接口，不能把组件CPU比率当500Mbps产品资格。
- **施工页**：`05-RECORD-CRYPTO.md`、`06-LINK-MTU.md`、`07-FEC.md`；依赖00，不替M0选择路径。反例 **C01–C04 / L01–L04 / F01–F06**。
- **完整能力**：记录PN/nonce/HP与三cipher源码向量兼容，wire32扩展与不同代去重；小包短路径、LINK MTU变化中已发送片不混stride、旧部分重组晚到/预算和末片先到；GF256旧Go matrix golden+平台原生ISA-L编解码e维缺源，与partial k及生命周期；FEC parity首发不是repair，不隐藏产出滞后、Normal off与Game差异，profile change drain有界。保留已有优质算法和可信FrameBudget，不为了新指标刷seed。
- **允许**：`crates/wbd-codec/`及M3日志/证据/cursor/requests。**不改**engine/Go平台/构建公共配置。需要公共ABI、Cargo根依赖调整时向M0送精确最小接口提案，独立编码工作不等待。
- **done_when / 验证**：固定Go兼容golden与真实Rust native SIMD平台探针、三cipher+L01–L04+F01–F06合批，MTU改变与真实历史字节一致、资源封顶、不污染正常首次到达；若有实质CPU改变才同job A/B按同配置和源码测，未接线Game/产品/P0之上的收益记NOT_RUN。

### M4 · `R1-M4-CARRIER-DRIVER-BATCH-WORKPACK-011`

- **为什么现在做**：已有75/75 UDP unprivileged batch/Stop模块证据，但M0 024真实raw路径仍有逐DATA sysfs、单包I/O、缺类型化EMSGSIZE反馈；现需明确**单一修改者**由M4负责底层平台实现，M0只改engine/Go桥接和验收，不再在main同时动同一平台源文件。
- **施工页**：`04-CARRIER-IO.md`；只为MTU变更边界直接参照`06-LINK-MTU.md`预算契约与024§3。反例 **I01–I04 / B01–B04（driver loan/Stop部分）/ L01（MTU±1）/ P01（设备变化）**。
- **完整能力**：真实Linux原raw/TUN接口上，设备级link/route通知（复用M0已在main `linux_route_events.rs`，不再造另一个监听器）、版本化MTU/error类型、EMSGSIZE/ENODEV失败即失效、接口删除/替换/恢复、只在可信变化/错误路径sysfs观测，逐DATA仅内存内预算+kernel DF保护；ready-only非等待≤32，适用FD用recvmmsg/sendmmsg及真实 prefix/suffix/uncertain 结算，I/O/header存储复用，release/Stop/rotation不泄loan；wire32回绕以可信扩展参考验证。已有代码与M0 main目标入口冲突时先明确接口/补丁供M0批次集成，**禁止**在旧worker分支上自行改main或重复维护平行netlink watcher。
- **允许**：仅`crates/wbd-platform/`、`r1/go-bridge/`、M4日志/证据/cursor/requests；**不改**M0 `crates/wbd-engine/src/v4_embedded_go.rs` 或共享权限/资格。已做的M4 010证明复用，不从unprivileged fixture推断raw真实PASS。
- **done_when / 验证**：原M4 native测试功能合批覆盖0/1/32/33批、partial/EAGAIN/uncertain、真实MTU down/up、route/ifindex变更、Stop/loan及seq32 wrap；CAP_NET_RAW 不支持则UNSUPPORTED，给M0提供具体接口/编译验证或固定patch及确切SOURCE。M0负责原Go认证raw/TUN的真正联调、同host P10对比、外部ABI与跨平台资格，不以mock代原生。

## M0保留与阶段集成

- registry保留`R1-M0-HOTPATH-COST-024`：按2026-10-16决策§3–7继续原始Go TLS认证→Rust owner→raw/TUN持续业务热路径。M0拥有 `v4_embedded_go.rs` 和 `v4_owner_crypto.rs` 的组合/方向注册重构、Go真实fixture/共享workflow与最终AB/BA验收；上述M4负责**平台底层**调整。必要时先以冻结的接口签名集成M4最小差异，M0不并发修改M4文件。
- 先核并复用已存持续业务和netlink原生功能证据；当前剩余是TX/RX摆脱共享registry mutex、ready≤32立即drain与分配复用、事件/EMSGSIZE安全边界，然后真实功能C批、D10和SPARSE分别单场景Action、P10 Rust A→B与独立B→A各同job同VM预编译复用产物；C50仅在宿主有容量且P10全交付。CPU%不跨拓扑拼接，p99+missing优先，无HOL不按同一TCP流越字节验证。
- 集成时根据各worker`ready_for_integration`的精确CODE/SCOPED SOURCE核单批文件差异、公共接口、worker自身中央scope审计和native功能，再在main真正Go/Rust raw/TUN入口做受影响组合回归。源码SOURCE改变后旧PASS仅保留历史；共享适配需要前进就做最小G2决定，不能替工位包内开发。
- **保留历史OPEN**：原023 B01–B04资格、超MTU自动fragment/reassembly全实路径、Game/FEC-on、发布配置、Windows native、500Mbps、物理/80秒中断均未因本登记变PASS。production ABI features=0，`unverified=true`，不得部署用户机器。
- 一次性登记即是全部本轮worker开发授权；**没有**“每一步找M0”“先M0调完再开工”的额外闸口；不创建第二个任务层级/审批表。可中断按S→H恢复，下一交接只写本包完成边界、精确test SOURCE和一个剩余动作。
