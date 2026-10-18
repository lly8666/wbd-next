# M0 恢复 R0-023 集成入口 · 2026-10-17

本轮不重开024：Normal/FEC-off已测基线锁定 `fca4456313e59c0a67f4d8b98959a62d2af71b12`，仍保留 D10 `39032995995` 旧A交付短缺 FAIL/INCONCLUSIVE。用户要求恢复原业务集成、Stop与超MTU，本 S 在main registry将M0转回原分配的 R0-023，不改变 M1/M2/M3/M4 权限或工位任务。

- M1 正式main registry仍分配 `R4-M1-GAME-SHARED-PIPELINE-WORKPACK-013`；worker HEAD `9d4f68aab2bb1f57bfb96dd8a472bc7eec43f556` 的 cursor 仍指历史已完成012，**不表示Game013完成，也不得由M0在worker分支替写**。M1沿现有 PACK013 自治继续。
- M2 正式main registry仍分配 `R2-M2-AUTHENTICATED-REPAIR-INGRESS-WORKPACK-010`；worker HEAD `c345061c992c505c92eb19181de96a531cc39d96` cursor 仍指已交付009，**不表示010已交付**。M2继续010，不追加逐步派单。
- M3 CODE `422a26127496560c0a52e6745ecc8f354e3f4f18` 正确性已有精确 SOURCE 结果；现有 M0 专项 workflow 在同一个consume job使用已经编译/sha验证的 Release binary 顺序 scalar→ISA-L，同一 20:20/1200B 工况，只有一个性能场景，不重构 ISA-L crate 或脚手架。跑完再追加实际run/hash，不提前写 PASS。
- M1/M4冻结源码对 main 的绝大部分模块已相同；差异需逐文件判定，避免覆写主线的 original Go owner 接线帮助函数。后续 M0 原 R0-023 优先原业务真实超MTU/Stop/借用生命周期，必要组合检查才做相应 source-pin paired tests。D10、原R0-023、Game/FEC-on/物理/产线资格都不继承前项绿色。

## 2026-10-17 · M3 同机标量/ISA-L CPU Action 收据

- 原完整 worker CODE `422a26127496560c0a52e6745ecc8f354e3f4f18`。M0 workflow `d361f7563c770b30f6e684dcadededf4961f1d53` 的原 build+consume 编译一次 Rust Release test 二进制并核 sha，然后在 **同一 consume job/VM** 用固定 20:20×1200B、同一 deterministic 源，`WBD_FEC_ORDER=AB` 顺序 scalar→真实 Intel ISA-L，共两条连续 leg。
- [Actions 39044413886](https://github.com/lly8666/wbd-next/actions/runs/39044413886) SUCCESS：真实 Go矩阵/ISA-L 正确性3/3，标量 2712 blocks/1.25096s CPU，ISA-L 123331 blocks/1.25022s CPU，两个 leg 各5个 >=250ms有效窗口、0坏窗口，编码20 systematic+20 parity并恢复4/块。观测的codec块每单位CPU处理能力约45.5倍，**不是原隧道吞吐、业务RTT、具体 AVX dispatch、完整FEC-on/500Mbps**。p99纯codec操作 wall: 标量507789ns、native13242ns，同样不是packet p99。
- 初次 [39044344082](https://github.com/lly8666/wbd-next/actions/runs/39044344082) Rust AB 测量原始完成，M0 自增 Python regex 转义错误导致结果解析FAIL，完整失败保留；修正后的 d361 Action 为独立实际 PASS。所有 build/result artifact IDs、hash和源码详见此独立 JSON。
- 工位登记不变：M1主线任务 Game013，M2主线任务恢复010。M3码 `422a` 已冻结但worker cursor仍 PARTIAL；M0 不抢改M3分支，不在未交付前将其真实产品集成冒充通过。Normal/FEC off已测SOURCE `fca4456` 原样冻结，D10失败原样保留。


- 反向 [BA Action39045641512](https://github.com/lly8666/wbd-next/actions/runs/39045641512) SUCCESS，M0 workflow `a4ca2fe` 的 `measure_order=BA` 只跑这一场景：同一测量 job 的 ISA-L 先行（52631块/1.24988CPU秒、p99 codec 34846ns），scalar 后行（1996块/1.25186CPU秒、p99 codec 704415ns），10/10原始窗口有效。build/result IDs+SHA在原M3 evidence JSON 的 `reverse_BA`。两个 runner 的倍率不相加、不直接比较绝对CPU。前一条 AB receipt 保留。M3角色正式交付及Go V4 FEC-on仍未因此直接通过。

## 2026-10-17 · M1/M2/M3/M4 精确组件验收与 R0-023 阶段实际接线

- 原 Normal/FEC off 基线永远固定 `fca4456313e59c0a67f4d8b98959a62d2af71b12`，历史 D10 39032995995 FAIL/INCONCLUSIVE 原样保留；新 M0 CODE `ede83b98edba1fee6f73bc99454040cc95392d4d`。
- M1 Game013 CODE `e2050aec` 已 117/117 + central scope PASS，main `7d0a1c7` 只导入 Game 两文件+mod 声明，不倒灌 worker 旧 memory/early_rx/generation；main native-functional 39047827609 PASS。
- M2 恢复010 CODE `654a3c1` 70/70 + central scope PASS，main `006cab6` 只导入 typed ingress、rx_feedback、workpack_tests+lib 声明，保留 main 原优化过的 receipt.rs；main recovery/native 39047929179 PASS。
- M3 CODE `422a261` 113 PASS/scalar、真实 native ISA-L 3 PASS、独立同机 AB39044413886/BA39045641512 PASS；`ede83b9` 只导入十个不同 codec/src blobs，原 record/wire/LINK functional 专项全 PASS，默认 native feature 仍 OFF。工位 H30 central39046275022 **FAIL verified cursor lacks reviewed PASS evidence**，之前 H29 central PASS；不能声称最终工位 H30 形式核验通过。
- M4 PACK013 CODE `b7bcde7` 94/94、原始4个平台 hot-path blobs 与 main 完全相同，不重复导入；M4 平台仅历史 scoped 单测不同。
- 原始 protected Go TLS→Rust V4→真实 raw/TUN 组合 native 39047975684 PASS：MTU 下降 fail-closed、恢复后 driver lease 按原 generation 安全重建、大1728B真实内层 IP 在现有单帧预算下拒绝、随后的小包继续 kernel copied、活跃双 worker Stop/Release+旧句柄拒绝重启。只证明 **安全拒绝** 而非 LINK 超 MTU 自动分片后交付；完整 R0-023/产品资格仍 OPEN。
- A=`fca4456` vs B=`ede83b9` 严格同机配对 P10：AB39048219356 CPU-s/GiB 104.54→109.33 (+4.58%)，BA39048219347 79.71→78.55 (−1.46%)，A/B两方向0 missing/invalid；**CPU因顺序/宿主变化结论不定**。p99 B 各leg 稍高，不宣布无回退；20pps SPARSE AB39049004790 已用于下一次限定首到验证，未得结果前不编造。
- Unified native functional `39047975666` codec 组240秒串行 timeout（其他子组PASS）；原 M3 worker suite 串行口径与 worker 多线程不一致。M0 `d8a11d` 仅把统一 codec 功能组测试设为4threads，保持性能独立跑，Action39048697568尚待实际归档；原红灯保留，不能按任何单独专项 PASS 伪造整个 workflow SUCCESS。
- 证据 `docs/evidence/M0/M0-023-modules-intake-ede83b98edba1fee6f73bc99454040cc95392d4d.json` 保存来源、产物 GitHub 提供的 SHA256/运行ID、差异清单与未验范围。当前 Go Game / repair typed 只是组件导入、尚未完成实际认证接线，整体产品功能保持 OFF。下一步仅接 live V4 owner 的 LINK fragment TX / M2 ingress，按必要结果选取组合回归，不做024微调、容量加压或 D10 重跑。

## 2026-10-18 · 真实原 Go LINK 分片经 Rust owner/raw/TUN 双向验证

原 R0-023 此次只处理已存在 M3 LINK/MTU 源码与原 Go V4→Rust owner 的最后一段业务接线，不重启024、未启 FEC2 bit2/kind2/3。main S 按序为 `7f23a0b` (AEAD 后 LINK Pending 不向 TUN 误交付)、`77115c0` (原 Go linkdata 真分片→三 cipher AEAD→真实 Rust reassembly/TUN UDP app)、`e3c4682`/`62b12cf`（原 owner 单一 PN/seq/loan/route-scoped 验证分片 seal）、`a96dabb`（真实 background TUN 走有界 LinkPacketPlan，每帧 M1/AEAD/真实 M4 raw）、`821962b`（独立原 Go TLS opener+linkdata.Reassembler 验证 S2C 1728B 一次交付及小包无 HOL）。

精确 SOURCE **`821962b7fc204facf5e1e5599a0b3fead3c3a58c`**，原 clone `a7a82db`，Linux x64 构建/消费 Actions **[39089250014](https://github.com/lly8666/wbd-next/actions/runs/39089250014)** attempt1 **SUCCESS**。真实 C2S 原 Go 1370B 内层 IP 在三 cipher 下均以两条原 Go LINK frame 通过原 raw/PN/AEAD，经 Rust 有界 M3 RX 合成一次并经真实 TUN 到应用，第一片不输出业务。真实 S2C 1700B UDP/1728B TUN 内层 IP 经原 Rust 2个独立 PN/冻结密文、raw IPv4/TCP，Go TLS opener + Go LINK 重组成相同 IPv4/UDP 字节；随后的52B小包仍被内核复制，Linux接口65536→1500中途缩 MTU 时原驱动保持 fail-closed、复原后才许可新 lease、Stop/Release 后不复活。原 Go端仍不是生产普通发布入口；完整产品、Windows/ARM、GUI、FEC-on仍 NOT_RUN。

早期只改 TX 尚未改原反例的 Action `39089148178` 为 **FAIL**（旧测试仍期望1728B完全拒绝）；在 `821962b` 把同一真实路径断言改成 **必须确实2片并重组** 后独立完整跑 PASS，未跳过测试。原 C2S SOURCE `77115c0` Action `39088956872`亦 build+consume PASS。先前 D10 `39032995995`、统一 codec 240s timeout、P10/SPARSE p99 风险及 M3 FEC2 CODE301 k2非法row测试均保留原状；ZIP摘要来自 Actions API，未独立下载复哈希。唯一详细证据为 [821962b source 收据](../../evidence/M0/M0-023-real-go-link-fragment-821962b7fc204facf5e1e5599a0b3fead3c3a58c.json)。

**本次收口边界**：开发功能源锁已证明 1370B C2S / 1728B S2C 经实际业务和原独立 Go peer 交付，不可把它升级为任意合法最大UDP。原 arena 每 slab 2048B、每 ready turn 最多32帧，对超过32帧和更大 65KiB TUN UDP仍明确 fail closed；中途已发部分片后MTU突变、uncertain/prefix和未知 PN/loan细节尚缺真实组合覆盖。Normal/off 开发诊断随既有workflow唯一10Mbps场景运行，但未经同job新旧AB/BA比较，不宣称收益。当前 R0-023 继续 **partial/unverified**。

**一个下一动作**：沿本次真实 Go→Rust owner 的相同调用点补有界跨 turn 分片 staging/归还与中途 MTU/Stop/partial syscall 接线，验证大于32片合法UDP、L01–L04/B01–B04 实际借用与小包无 HOL；既有通过场景不重跑无关优化/旧D10。

## 2026-10-18 / 023：先整包预备 original M1 LINK slabs 再封 PN（安全增量）

发现前版原始 Rust background TUN 超MTU段逐片 `arena.allocate()→seal_fragment...`：原M1 slab资源如果在第k片耗尽，前k−1片可能已经消耗 PN 并入TX队列，留下必然等TTL的部分逻辑 packet。新 M0 源 `dd01c86b84a4f85875c3197cf995749f1c44e5bf` 增加 `stage_bounded_original_link`：先用原 M3 `LinkPacketPlan` 固定 frame_mtu/packet_id 并限制本轮 `<=32`，在一个原 M1 arena 内预备完整分片/loan；任一预备失败整个局部数组丢弃回同一 M1 return queue，**封装者此时一个 PN 都没消耗**。仅所有片都预备成功才开始原 M0 owner `seal_fragment_with_worker_snapshot` 严格路径。独立随机 small packet 仍走原Normal零额外LINK开销。这个安全边界不假装覆盖 *seal/queue中途失败后* 或内核sendmmsg前缀/未知完成的全packet原子性；更不等于支持所有 65KiB UDP。

真实 M0 native Go→Rust `1689d67ab23ada9f4130a963ec7cc223e1f1cca4` source锁定 [run 39093072101](https://github.com/lly8666/wbd-next/actions/runs/39093072101) attempt1 build117573724785 SUCCESS/consume117573990178 SUCCESS；本轮新增 `m0_link_materialization_never_admits_half_packet_on_arena_failure` 原 Rust M1 arena 真slot + M3 LINK帧造/解析1/1 PASS，原Go三cipher真实丢已知encrypted PN0而PN1通过/noHOL、内核真实1728B TUN大包S2C分两片回原Go reassembly once、随后小包1、MTU65536→1500失败关闭/route恢复与Stop均 PASS。双向10Mbps Normal/off 10s热身60s开发诊断观测offered=delivered 10Mbps/方向，线程RX CPU2.0082s，TX CPU2.0175s；**不是正式产品性能资格**。结果/构建 GitHub artifact digest已读，未独立ZIP复哈希；SOURCE详细边界与其它工位阶段见 [receipt](../evidence/M0/M0-023-preseal-full-link-staging-1689d67ab23ada9f4130a963ec7cc223e1f1cca4.json)。同期 `dd01c86b` native-functional 全组 + r0-native-abi独立成功，正式精确 SOURCE 依 `1689d67a`。

继续保留：合法大 UDP 受原 TX TUN 2048B slab 限制、跨轮次 >32 帧支持未实现；原 M1 `seal/queue` 部分接受、旧/新route MTU在已发半包、原M4 kernel prefix/uncertain/Stop借用组合尚需真实反例；FEC2 bit2/kind2/3仍OFF。M3 最新 H36 同意CODE8cc真 native及合格CPU，但本身中央scope由于main审批检查点后75次提交超过64上限失败，需要 M0 人工逐提交审核中继点、不改上限，ARM64/Windows完整新codec仍 NOT_RUN。M1/M2/M4既有 scoped 结果并不等产品。分工与剩余产品验收顺序另见 [7大门阶段快照](M0-023-next-stage-snapshot-2026-10-18.md)。

## 2026-10-18 · M0 R0-023：真实 AEAD/PN/Replay FEC2 kind2/3 的 gated 接线增量

SOURCE `ee5d2cad1ba8818488a91097e4da04fcc55b8e63`：在**原有** `wbd-codec/record_crypto.rs`、`record_replay.rs` 中增加显式 opt-in 的 `m0-fec2-record-probe` record 能力，只在专门方法里允许 2=FEC2_SOURCE、3=FEC2_REPAIR。默认 `seal_in_place` / `open_in_place` / `open_unique_in_place` 仍限 kind0/1，且在有该feature编译时仍拒绝2/3；既有 normal/off 冷层、Go认证、原 owner/driver 路径没有自动激活FEC2。新显式入口必须由后续**受保护 Go TLS 能力/KDF/epoch/方向/配置**赋权后才可接入，当前没有此证明，不能声称FEC-on。

关键不是新密码栈：直接重用原 ChaCha20-Poly1305/AES128/AES256 AEAD、8字节HP、一个TX PN分配器；RX `ReplayProtectedLaneRx` 用**同一原有bitmap**接受认证且具资格的 kind2/3，普通kind0仍可乱序先达/后达，tamper必须AEAD失败再进入PN，重复同PN跨类型严格拒绝；M3的10B source/12B repair在真实AEAD打开后才交解析/恢复，错误flags能通过AEAD也仍由M3拒绝。源码启用feature无Go protected admission、无packet end-to-end: app capabilities/product始终 OFF。

<https://github.com/lly8666/wbd-next/actions/runs/39098885644> attempt1 SOURCE精确 **SUCCESS**：默认编译及显式feature编译各跑两条覆盖三套真实cipher的记录、丢失恢复、去重/错误反例，分别2/2 PASS。artifact ID12125319675 GH SHA256 `7ee4beec5c611be0f4ad2ee22ce37d05d8124aafa08e50ac762f9c47b1d4b023`；GitHub工件ZIP未独立复哈希。同一SOURCE G2 bootstrap39098885668、R0 wire39098885673、record framing39098885649、LINK-FEC/MTU39098885643及主线 governance39098885646 均SUCCESS；合批native-functional39098885670在写入证据时codec旧240s门还未终结，其他engine/normal/fec/kernel/receipt与build PASS，不抢报全run。最早SOURCE0ad33f45的E0716编译失败为新增测试临时Vec clone借用错误，已保留并以新源码ee5d和真实Actions修复。

详细来源/新旧失败/产品边界：[`M0-023-fec2-protected-record-ee5d2cad`](../../evidence/M0/M0-023-fec2-protected-record-ee5d2cad1ba8818488a91097e4da04fcc55b8e63.json)。下步先将真实 TLS 受保护 bit2/epoch/direction/KDF 和原 `ProtectedScopedOwner` 的**同一PN** 接到此限定入口，再通过M1 parity job、M3 真实record enc/recover及 M4 raw/TUN、M2反馈完成有据实功能验收。原R0-023大包跨轮次和 Stop/MTU/核内不确定边界、历史D10/p99仍OPEN；产品开关不能提前打开。

**晚到SOURCE回执修正：** `ee5d2cad` 的 [全组 native-functional 39098885670](https://github.com/lly8666/wbd-next/actions/runs/39098885670) 最终 **FAIL**，仅 codec job117591061533 240s超时 `exit_code=124`、另有旧 `r1_tx_cooperative_release_cpu_wall_diagnostic` 出现在 unexpected ignored；plan/build和 engine/normal/fec/kernel/receipt 5个其它验证组分别 SUCCESS。此红灯为先前已存在、仍未关闭的旧codec长时门，不是定向三cipher FEC2 kind2/3 PN-replay测试的失败。定向run39098885644仍 2/2 default + 2/2 opt-in PASS；没有跨SOURCE拼装整套资格。详见已纠正同SOURCE [证据](../../evidence/M0/M0-023-fec2-protected-record-ee5d2cad1ba8818488a91097e4da04fcc55b8e63.json)。

## 2026-10-18 M0 快速集成 · FEC2 original Rust owner 的实际 PN/Seq/Frozen TX 路径

沿上次同一原record AEAD/PN/replay 合格源 `ee5d2cad...`，在 `crates/wbd-engine/src/v4_owner_crypto.rs` **复用原来完全同一** `ProtectedScopedOwner.seal_scoped_authenticated_one`，内部只在显式测试feature `m0_fec2_owner_probe` 下调用已经编译验证的 `LaneTxCrypto.seal_fec2_after_admission_in_place`，而正常缺省源码仍用 kind0、相同 PN/Seq/MSS/record 封装检查、generation-scoped M1 FrozenRecord 与原 TxOwner。新 `seal_fec2_probe_one` 首先执行 M3 10B source/12B repair 解析/flags/range检查、已冻结真实 M4 FrameBudget 限额，随后进入同一原owner流程；如无 feature、未Commit/Detach或非法 M3 数据则fail closed。**没有为 FEC2 绕开实际 owner 或自建 PN/Replay/Seq**。功能仍严格**test-only，不从合成 cold248 推导 Go TLS credential/bit2 权限**，无产品C ABI、公配置或默认 ON。

新增 `v4_probe_bridge.rs` 原 ScopedOwner/PrivateGoV4Handoff fixture 每个 ChaCha20/AES128/AES256 密钥方向依次 `LINK0→M3 source2→M3 repair3`，同样的 PN0/1/2、连贯TCP-like Seq、M1原 arena loan→真实FrozenRecord queue→原 ReplayProtectedLaneRx AEAD解密，按原 M3 RS16 缺源恢复。pre-Detach试图FEC2发送无PN/无loan逃逸，非法flags在封包前拒绝，M1 loan在批次归还后0，Stop/Release成功；默认不带probe feature的Rust release library也编译成功。历史首轮新测试 `39100648669` 因 Rust `TxDispatch` 无Debug触发 `unwrap` E0277，第二轮 `39100727877` 因误用容量0 `Vec::new` 触发M1原定的零分配bounded drain返回0，均按真实原契约纠正，未要求M1改接口或削弱真实断言。

固定 SOURCE `c60e9d6e95aff49cc98eb039e7347659eaaa6213` [Run39100892712](https://github.com/lly8666/wbd-next/actions/runs/39100892712) attempt1 原owner feature-only test **1/1 PASS** + 生产缺省Rust build PASS，artifact12126114397 GH digest b19162c0...；同 SOURCE [原真实Go V4/Rust raw/TUN 39100892715](https://github.com/lly8666/wbd-next/actions/runs/39100892715) build/consume均**SUCCESS**、原先Normal/off按原用例稳定；`native-functional 39100892732` 的 plan/build/engine/fec/kernel/normal/receipt全 PASS，**该main changed-path matrix没有执行codec分组**，不得据此说旧codec 240s红灯消失；r0-native-abi39100892718、cross-abi39100892706、G2bootstrap39100892806均 SUCCESS。所有SOURCE/hash、区分底层证明和网络资格见 [收据](../../evidence/M0/M0-023-original-owner-fec2-same-pn-c60e9d6e95aff49cc98eb039e7347659eaaa6213.json)。

**下一关键瓶颈：**在原真实Go V4的*受保护 TLS 请求/回应*完成 feature bit2 的双方能力/epoch/direction/KDF 和独立的applied policy，才能让原owner从 test-only 进入授权的真实send/receive；再把 M1 source-first与ParityJob、M3修复、M4真实raw/TUN、M2认证后反馈贯通。Go TLS bit2/完整产品 FEC2仍 OFF，原R0-023 65KiB UDP跨轮次、MTU/Stop/driver 前缀未知、历史D10/p99 和旧codec 240s均未结项，不能用已成功的原owner FEC2 **测试**代替网络产品资格。

## 2026-10-18 · M0 real Go TLS bit2 capability & source-locked private Rust V2 handoff（加速集成）

本轮把**原Go真TLS credential-checked admission**从严格 feature `0x0003` 扩展为**仅包内未导出的私有测试开关**可提出 `0x0007`（bit2=FEC2）。原 `EstablishClientV4` / `EstablishServerV4` 默认公开配置不提供 bit2：旧0x0003位于相同v1闭环、未知/残缺feature拒绝。真TLS凭据校验后服务器必须与请求 feature 精确匹配，0x0003↔0x0007不静默升级/降级，失败候选不commit epoch。原Go exporter/KDF对实际受保护扩展(含bit2/epoch)计算hash上下文并派生C2S/S2C密钥；Go verified snapshot冻结功能位，`cold248` 原reserved11仍为0，绝不使用它自行赋予Rust写入权限。

紧接原 private `v4OwnerBridge.prepare`，`v4PrivateHandoffFromVerifiedSession` 根据同一Go credential-check 产生的**冻结snapshot**为默认0x0003继续生成原32B `WBGH/v1`，而0x0007仅生成 `WBGH/v2`，offset27:29 exact BE 0x0007，剩余3B保留清零；Go真正 embedded/probe bridge 都走此统一入口。Rust `PrivateGoV4Handoff::decode` v1要求全部尾5B为0，v2要求固定feature0x0007+3B reserved0，失败不释放有效 owner。**Rust目前只解析授权上下文的结构化 metadata，不因此令 FEC2 source2/repair3 进入生产。** 真授权/方向/applied profile/owner Stop lifetime 与数据面仍待接线。

Actions：
- [真实 Go V4 TLS 39102069847](https://github.com/lly8666/wbd-next/actions/runs/39102069847) SOURCE49498f3a7... build/consume PASS，17个 V4 顶层Go测试PASS、16项作为required：真TLS三cipher bit2 7/epoch与双方方向KDF，双向协商不一致硬拒+epoch rollback，未知feature非法，受保护exporter精确上下文 off↔on独立；
- [原 Go真实TLS→嵌入式 Rust owner 39102424680](https://github.com/lly8666/wbd-next/actions/runs/39102424680) **SOURCE c6d1e2b8214cee3b78cae43c14ffb581864c578f** build117601245951 / consume117601531073 SUCCESS：新增 `TestR0V4EmbeddedNativeProtectedFec2Bit2Scope` 三cipher真实Go保护协商→Go私有handoff v2→原Rust owner Prepare/Commit→Stop/Release全部PASS，原Rust v1/v2 malformed字段负例 `m0_private_v4_real_go_fec2_bit2_handoff_is_metadata_not_permission` PASS，其它原Normal/off Go/Rust raw/TUN保持真回归PASS；
- 同SOURCE治理maintenance39102424631 SUCCESS；工件GH摘要/排除项见 [精确回执](../../evidence/M0/M0-023-protected-go-fec2-bit2-rust-v2-handoff-c6d1e2b8214cee3b78cae43c14ffb581864c578f.json)；
- 历史原native-functional run39102069872 codec组240秒 FAIL（其它组通过）和前SOURCE cdc176 的native 10ms smoke FAIL均按真实run保留、不以本轮c6成功消去旧红灯。

最短下一动作是**让Go真TLS经Private owner已提交、代际/epoch/方向/真实applied policy后向Rust赋予一次性仅属于该scope的 FEC2 2/3使用权**（不是只相信可伪造私有32B metadata），然后在已导入M1/M3/M4/M2代码上跑真实FEC2 source/repair过OS原raw/TUN/driver；失败的历史codec/D10/p99与原R0-023大UDP跨轮次MTU/Stop边界保留OPEN。默认公开FEC2产品OFF；本轮**是控制链路成功，不是FEC2网络产品资格**。

## 2026-10-18 · M0 Go真实TLS→原Rust owner 的受限FEC2 epoch/Stop grant

承接H140 Go原真TLS bit2/受保护KDF→原Rust私有WBGH/v2元数据，本轮补真正的**测试专用owner授权状态**。`ProtectedScopedOwner` 新增feature-gated `Fec2ProbeScope`（原generation、epoch、M1 owner ID、lane、探针用Strong profile5/revision1），默认`None`；在owner Commit之后仍拒绝kind2/3，只有独立的原Go package-private callback完成TLS认证、受保护应答、Detach和原Rust Commit后通过额外`wbd_v4_fec2_owner_probe`测试构建调用匹配的Rust绑定，才被允许原source/repair探针。错误epoch/feature/profile/revision、重复绑定拒绝，Stop撤销，旧handle不能再确认旧scope。默认Go hook为空操作，默认Rust release完全**没有** grant/status FFI符号。owner真正AEAD/PN/Seq与M1 FrozenRecord仍只有一份；没有旁路数据/第二套密码分配器。

精确SOURCE `c534e5892bbe4ef3d18355ac71723f6bcf6d41d5` 的 [Actions39104136996](https://github.com/lly8666/wbd-next/actions/runs/39104136996) attempt1 **SUCCESS**：原Go pinned `a7a82db31fe736ffedee330795a3234d358f1984` 真人口TLS与原Rust native release联合，同一job三套密码套件运行 `TestR0V4Fec2ActualGoTLSEpochOwnerGrantScoped`、原默认0x0003控制与元数据0x0007兼容测试，Rust `r1_m0_original_owner_fec2_source_repair_same_pn_staged`验证Commit后scope前禁止、绑定后真正原M1→FEC2 source2/repair3 AEAD PN/Seq以及错误参数拒绝。Rust普通release无上述授权符号。工件 ID12127314845，GitHub SHA256 `3acb8f2c00c574f6532c46fbdf9d1d50a4b0448a2989db47bbe29b206393f058`（未另行重新计算ZIP digest）；完整字段在 [SOURCE证据](../../evidence/M0/M0-023-real-go-fec2-owner-grant-c534e5892bbe4ef3d18355ac71723f6bcf6d41d5.json)。

两次初期真实错误已保留：旧SOURCE 39103821683 缺Go普通版空回调文件，39104016657定向Actions在编译原测试包时漏原native-probe raw辅助文件/标签，均按原实际编译边界修复后通过；先前39103933765旧150ms内核netem独立试验FAIL，旧codec240s/D10/p99也仍OPEN。

**重要非产品说明：**原Rust不能独立密码学证明任意同进程C调用确由Go TLS凭据拥有者发起；此信任依赖原Go私有同进程代码路径，且仅额外测试标签编译。Strong/1只是探针，不是已生效真实Go FEC2自动/固定CLI/GUI配置。没有实际FEC2 parity经过M4 raw/TUN、没有M2认证反馈、没有产品用户态启用，FEC2产品OFF；原023 65KiB跨轮次/MTU/Stop/prefix不确定仍未收口。**下一动作为**将已有绑定生命周期送入原M1 source-first+M3 FEC2→M4真实收发和M2 auth ingress，逐条Source锁真实业务反例，非再跑微基准。

## 2026-10-18 · M0 R0-023 真实 Linux M4 raw TCP FEC2 source2/repair3 端到内核

已把上轮 H141「真 Go TLS→私有 Rust owner epoch/grant」推进至**真实 M4 内核发送**：额外test-only feature 下，`v4_embedded_go.rs` 的单轮有界探针预先用 M3 真 RS16 Strong k2 制备 113/127B 两源和一条 repair（这里只发送source索引0与repair行0，**没有**把原M1 Fec2Owner实时调度当已接入）；在任何PN/Seq前取得两个原 M1 Arena slab；每个走同一 `ProtectedScopedOwner.seal_fec2_probe_one` →原AEAD/8B HP/PN→冻结M1 TX→原 `ScopedRawIpv4Tx.send_one`，不自造第二加密器。真实 Go credential-checked 0x0007 私有scope已成功绑定 generation/epoch；错误scope在发送前拒绝。独立 Go syscall.SOCK_RAW/IPPROTO_TCP 原raw socket 在专用root netns捕获真正源/目的地址、端口、TCP Seq、密文长度（不以源码内计数代替收包）；3个cipher各 2 条刚好 PN0/1，连续Seq。真实内核raw链路已实测，但**尚无客户端解码/恢复或FEC2 TUN应用交付**，也没有实际applied Go CLI/GUI FEC2配置，产品开关仍OFF。

精确SOURCE `f6069a955d06508814341a23e22db27713424454`：
- [定向真实Go/Rust/M4 raw Actions39106157016](https://github.com/lly8666/wbd-next/actions/runs/39106157016) attempt1 job117612320575 **SUCCESS**，Go `TestR0V4Fec2ActualKernelRawSourceRepairAfterProtectedGoTLS` 三套cipher内核实包均PASS，保留原3套Go TLS授权/原Rust FrozenRecord真实AEAD测试，Rust生产默认build不含任何该授权FFI。Artifact12128403235 GitHub ZIP sha256 `f75578329961529947d32281e3b5d02691a70f0a8e41efa6639889b847054250`，M0已下载并**独立重新计算完全一致**；`real-kernel.log` SHA256 `0db2038762f05c9f107303a4270db9bf4b363a7029d0cd8fd168507026342632`；3种cipher返回PN均0/1。
- 同SOURCE [旧完整Normal/off原内核39106157061](https://github.com/lly8666/wbd-next/actions/runs/39106157061) **整体FAIL**，build SUCCESS，原正常 Go/TUN raw双向0ms真实三套都PASS、10ms configured netem三套探针仅EXPLORATORY_PASS，但旧150ms configured netem中第三cipher的第二个合法LINK fragment经过原M3表后仍无完整应用交付（raw_to_tun=INVALID），前两cipher在该场景PASS。**旧150ms红灯保留OPEN**，不能用0/10ms和本次FEC2实包成功覆盖。
- 第一次定向 `39105586754` 被新增shell选择器漏引号阻止执行，后来 `39105856135` 真FEC2内核raw已PASS，但原传统Action因为意外重复拼接的脚本尾部syntax失败；`f606`修复重复尾部并同时复核上述真实old0ms/10ms与150ms，记录全部发生经过。未刷seed/增加场景来粉饰高延迟异常。
- 同SOURCE治理工具maintenance39106157020和S Governance39106157008 SUCCESS。

[SOURCE、zip成员SHA、历史失败和下一硬门精确回执](../../evidence/M0/M0-023-fec2-actual-m4-kernel-source-repair-f6069a955d06508814341a23e22db27713424454.json)。

**后续优先**：原实包的真正下游Rx同一认证PN/范围和M3 e1缺失恢复→原M2反馈→独立TUN app，区别「实际TCP raw发送成功」和「真实FEC2修复应用收到」。产品Go实际applied fixed/auto revision、M1短块source-first完整调度、Windows/ARM64、R0-023 65KiB跨轮次/Stop/MTU、旧codec 240秒与D10/p99都继续OPEN。旧150ms source fragment失败先限一条可重复的新根因假设，不盲跑全部网况。

## 2026-10-18 · 原Go内核raw实包→独立原M3认证PN→RS16 e1恢复（R0-023）

本轮承接H142已经验证「真Go TLS→原Rust owner→M4原raw TCP内核source2/repair3→独立Go SOCK_RAW捕获」，只补**实际密文捕获后的认证/唯一PN/修复**，避免重写组件或重复测CPU。额外 `m0_fec2_owner_probe` Rust试验构建在同一已验证的原Go TLS→Rust Entry内准备一个**独立客户端接收视角的原M3 `ReplayProtectedLaneRx`**，密钥来自当次受保护Go exporter S2C、独立PN bitmap；仍必须由真实Go post-Detach的原owner generation/epoch probe scope授权才可使用。原Rust TX不变，仍一份原`ProtectedScopedOwner`和M1 `FrozenRecord`/M4 AF_INET raw；收包者只接收Go从*真实kernel*读到并经IPv4/TCP tuple、seq、长度核对过的密文，绝不引用sender原明文。该测试接收者不等于真实已部署客户端，不提供产品ABI或自动配置。

Go端独立收包后把密文通过独立的额外试验C入口提交给Rust实际 M3 `open_unique_with_fec2_after_admission_in_place`；kind2 PN0仅存储source0且交付0B；**同密文重放**在独立Replay中被拒；**repair PN1密文篡改**在原AEAD阶段失败，不占用合法PN1；然后原合法 kind3 PN1 通过M3 `parse_repair`/ `Rs16::recover_missing` 完成 e=1 只恢复未发送的source1共127B，Go按原公式逐字节比对。再交同一个repair应被拒。三个实密码suite全部通过。这个e1测试是“故意只发source0、repair0，数学上缺source1”，**未使用Linux丢包注入或M2真实反馈**，正式M1 Fec2Owner源码/调度未接实包。

精确源码 `c7bd452423e932255fbe3916a2a12e6727a3cdb8` [Actions39107436575](https://github.com/lly8666/wbd-next/actions/runs/39107436575) attempt1 job117616234174 **SUCCESS**；定向原Go TLS/三cipher、原Rust M1/M3 owner、实际独立Go root netns捕获、Replay anti-duplicate/tamper和RS16 e1整条门成功，默认Rust release仍无该FEC2探针ABI。Artifact12128972528 原GitHub和M0独立重新计算ZIP均为 `sha256:db12af775113bc533980f73f281ab5c4f6d428d4eb435dee29f833d1acea54e3`；实包日志SHA `f21c2e22059d7acd7e2da6249f14c26108538fb844499f84a30333795d9b1fd4`。严格SOURCE/边界详见[回执](../../evidence/M0/M0-023-real-kernel-fec2-peer-m3-rs16-c7bd452423e932255fbe3916a2a12e6727a3cdb8.json)。

**下一个硬门：**原M2接真正认证成功的FEC2源/修复receipt→真实原TUN app交付；接上已交付M1 source-first短块调度和真实applied Go固定/自动配置/修订，而非只保留额外探针。另限一条独立假设定位旧Normal/off `39106157061` 150ms下suite3第二LINK片仍pending，不能用本轮正确恢复来消除原红灯。R0-023 65KiB跨轮次/MTU/Stop/PREFIX、旧codec240s/D10/p99及真实Windows/ARM64仍OPEN；public FEC2 OFF，产品资格NOT_RUN。
