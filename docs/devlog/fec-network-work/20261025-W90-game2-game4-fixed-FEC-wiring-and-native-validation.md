# W90｜在原 Go TLS 认证后的公开 Game2/Game4 owner 接入 fixed FEC2，限 Linux ARM64

2026-10-25，`experiment/fec-network-tuning`。用户直接授权新增 GameMode+FEC 接线并立即测试，覆盖了此前“Game+FEC未公开时不自行接”的旧待办限制，但没有解禁 Windows、主分支合并或宿主容量高负载。**候选代码不能因为编译成功就声明已完成产品验证。**

## 先刷新与实际原实现

入手 HEAD `d4759a1dcd9cacc0cc40ff9d27379f1a733780bc`；W88 原生 Game2/Game4 是 per-lane AEAD/PN、Game16逻辑包多路复制、先到一次和Stop，但**没有 FEC2 parity**。W89 共享长 GE15% 下 Game2/4 原生业务 UDP残余13.35%/13.15%和8.31%/8.57%，两者严重高于1%，旧结果和原验收门保持，不能偷换之前的`PASS_SCOPED`为受损期PASS。Game TX/RX已是 `GameAdapter` 作为同一认证 owner+M4实时TUN，不重复开一个AEAD/PN窗口。

## W90 候选实现，授权边界

- 新 `crates/wbd-engine/src/v4_game_fec.rs` 使用已有 `Fec2Owner(FecMode::Game)`、`StagedParity`/4行M3 SIMD、`Fec2LiveRx.accept_authenticated` 的存储与RS16；**按源及时通过原 Game 多lane FirstSend**，parity使用相同Game多lane编排后复制到原M4，源/修复行数根据所选实际k/r，Game FEC内核送达数按真实M4 copied记。逻辑载荷在原Game16内多一个类型字节（`2` source/`3` parity）+复用现有 FEC2 源10B/修复12B（预算保留14），不复制旧密文/PN，不改旧Normal矩阵或外层RACK/PTO。
- Game RX先由原每lane独立AEAD/unique PN和跨lane逻辑ID去重，**之后**送FEC2修复，decoder可能一次归还多个原始IPv4帧，原M4同一TUN对每个候选做真正写入；不把重构候选计数伪称已写入TUN。原 GameFEC off路径保留。
- 原Game的闭组有限期与修复行`r`不改变：Game owner按源速率早关组，已关闭修复作≤4行编码批次，实际已封装多lane复制的PN只在原M4分配；跨M4队列仍拥有源slab，Stop强回收，不能因修复阻塞新source。额外FEC source arena128×2048B和Game owner2MiB、RX有界48MiB/640组按需，不启动额外线程/定时器；性能CPU/RSS/吞吐要由真实Actions验证。
- 公开Linux CLI显式选择 `--game-fec=off|fixed0..fixed6` 仅Game2/4；TUN内层MTU从原Game边界**再减15B**（类型1+FEC2修复保留14）；无Game Auto。原 original Go TLS V4 extension中的预留字节21只在feature7且GameFEC存在时使用 profile+1，0为off；两端 `EstablishClientV4`/ `EstablishServerV4` 的受保护请求及响应严格匹配，拒绝降级、不同档位和feature3偷开；原Game legacy off extension字节不变。native固定配置在认证完整组join之后、原M4 loop_start之前完成。
- native FEC计数为`source_offered,parity_offered,parity_copied,systematic_candidate,recovered_candidate,rplanned,rsent,expired,failed,retained`，前两类候选不等同真实TUN写成功；原 `V4_PUBLIC_GAME_KERNEL` counted actual M4 deliver，严禁用Game中的多lane复制计数当普通v3外层DATA repair。
- 不触碰Windows/M0所属内容；仅Linux原生 Game2/4 和自己的网络实验夹具。已在本分支ARM64 product-build加 Native Game2/4 missing-source/all-lane-loss/first-source/Stop专项cargo，以及Go真实TLS profile mismatch专项Go测试。独立真网络夹具只允许显式`product.game_fec=fixed0..fixed6`，并验证双方applied与修复真实kernel copied。

## Actions 进展（以最终回填为准）

所有源码提交自动触发ARM64 original-Go/Rust product build；初次错配签名中间SHA `95abf7f0` 的 [Action 40209000274](https://github.com/lly8666/wbd-next/actions/runs/40209000274) **编译失败** E0061（在加入`game_tx_empty`所有权门之前的过渡中间提交），随后改适配器并从[40209014616](https://github.com/lly8666/wbd-next/actions/runs/40209014616) 得到了原生Game2/4 FEC缺源恢复专项cargo Step SUCCESS；这不是最终 TLS协商候选构建。当前 Go TLS协商扩展已提交后等待最新真正源全部ARM64专项（Go真实TLS mismatch、Rust FEC/ISA-L/native kernel）结果，不预先称产品PASS。严禁保留旧错误或用早期通过产物代替新源。

## 网络验证计划

新产物真实ARM64完成功能门后**同一build artifact跨性能请求复用**，按W88原场景每方向3Mbps mixed UDP/TCP、75ms单程、外层Game DATA repair 不适用，Game2+FixedMaximum和Game4+FixedMaximum分别跑独立20%每lane +第1lane黑洞+无损恢复（每种模式一个性能Action一个job）；确证source/parity genuine per-lane/counter、恢复原IPv4/TUN、业务到达/p99、源TUN/root丢包0、Stop清理、核RSS/CPU/PSI。若正确性和这些保护回归确实通过，再每模式一个共享长GE15%和旧W89比较，明确随机未固定、Action非同VM不能声称严格CPU同比；不能为了理论≤1%改损伤门或刷seed。若尾延迟、FEC报错或TUN未到达，必须记录并修原反例后停止进一步多场景。

注意 Windows本岗位依用户要求 `TEMP_SKIPPED_USER_20261025`，`capacity_stop=true`，`merge_ready=false`；历史W85/W86/W89失败不修改，Go TLS/Native均不可把部分测试误称整体交付。


## W90 已确认 ARM64 专项及进入真实业务

精确候选 source `ad9eaab88b93501e3de64efdc8fabc89f087e51e` 的完整原生 product [Action 40209693209](https://github.com/lly8666/wbd-next/actions/runs/40209693209) **SUCCESS**，经过 Rust `v4_game_lane::tests::fec_game*` 两套 lane2/4 FEC缺源恢复、Go 真实 TLS 档位不一致严拒绝、原生 M3+ISA-L、已验证原 FEC TUN与Auto合同（无需并不代表 Game native真正端到端过）。同 Action 的产物 `network-arm64-public-40209693209-1` artifact `12604894755`，ZIP SHA256 `d9254af56a9461b88467cc2c62a360e7fb31308a3318be50d3e74e86b7d4301e`，后续两测试复用完全相同 build，不改 Game/FEC 产品代码。
- [W90 Game2+Fixed6 请求](../../../tests/network/fec-work/W90-Game2-FEC-fixed6-independent20-lane1-blackhole-arm64.json)：提交 `b8b17ee870972ea688c50a892f74c377e1104621`，真实 [Action 40209948309](https://github.com/lly8666/wbd-next/actions/runs/40209948309)，合同 [40209948336](https://github.com/lly8666/wbd-next/actions/runs/40209948336) PASS。
- [W90 Game4+Fixed6 请求](../../../tests/network/fec-work/W90-Game4-FEC-fixed6-independent20-lane1-blackhole-arm64.json)：提交 `4db880174dbef22626fbe27924071c6eea1950dc`，真实 [Action 40209953632](https://github.com/lly8666/wbd-next/actions/runs/40209953632)，合同 [40209953658](https://github.com/lly8666/wbd-next/actions/runs/40209953658) PASS。

两个真实网络 Action 都使用 `--game-fec fixed6`、Game 2/4原M4真实TCP/TUN、各方向3Mbps mixed业务、75ms单程；warmup15s后12s clean→25s各lane IID20%→25s lane1黑洞→12s clean；原 Game W88 1287B最大包改为**1200B最大包（明示新增15B FEC预算并保守避开边界）**，所以它们与 W88 同类但**并非完全相同包长分布、随机轨迹或同VM CPU A/B**。真实`netem_rng=unseeded_recorded`，只在两个 clean phase 保持原1%严格UDP/小包门，受损时记录实际丢包/恢复与p99，不能变相豁免新功能未收到真实恢复证据。等待原始artifact后再判 PASS或FAIL，本段不预支产品结论。

## W90 第一轮真实失效及单lane修复发送的更小候选

**不能宣称 Game+FEC 已通过。** 真正首次原生产品业务 `source=ad9eaab88b93501e3de64efdc8fabc89f087e51e` 的 Game2 fixed6 [40209948309](https://github.com/lly8666/wbd-next/actions/runs/40209948309) **FAIL**：已通过 Go TLS profile6、Game M4和真实FEC业务 source14/client、44/server、parity计划=内核发送 client28/server84，却在开始损伤相位前内层 TCP监听 accept 超时，RX端存在14/19条认定为“auth_rejected”的接收异常；不能当业务测量通过。artifact `12604984802` SHA256 `3aa1f124b04e18a51c2e9729bc82a38ad71424f24827d35e4bf4f9a698a377a9`。Game4 fixed6 [40209953632](https://github.com/lly8666/wbd-next/actions/runs/40209953632) **FAIL**：真实持续业务跑过各相位，累计 client/server source offered 53951/53878、parity copied72709/72578、M3 RS真实 recovered candidates4863/4297；但收到的Game原生raw记录仅88618/77287相对于 M4 copied471355/470617，所有 Clean phase UDP也丢失巨大、TCP回压且启动时无净路资格，host PSI peak仅2.98%。原始 artifact `12604114639` SHA256 `e7a3138fa0acbed7a7eba9904062f6aaa1dd7e1bd64676ebbfb7e7a69afc7cd4`。这不是“only parity decoded”也不是内核 source TUN drop；parity copied是实际 M4 first kernel copy，未证明客户端实际收到。
- 为分辨 Maximum冗余过高 vs 共通接线故障，原源码只换固定档0（同每方向3Mbps、Game2/4独立20%及黑洞，**不是刷seed**），[W90b Game2 40210447377](https://github.com/lly8666/wbd-next/actions/runs/40210447377) **FAIL/TCP setup timeout**（artifact `12605476053` SHA256 `41c4d3027fd9006dcb156264f34dd0e34d25fbc08f642b97a6e9a85f7f0eb3b0`）；[W90b Game4 40210452663](https://github.com/lly8666/wbd-next/actions/runs/40210452663) **FAIL**（artifact `12605316702` SHA256 `4206b5e6a5100561cbcdc699b19fe618b52df67046c1716f29a6ae83dbc0f559`），即使Fixed0仍存在Clean期严重丢包与TCP回压。无损源TUN drops0、并非整机CPU超压即可解释。上述均不是Windows或真实设备结论。
- 后续**一次更小修复排列候选**：源业务仍以现有 Game2/4 所有已就绪 lane 复制，**每个FEC parity逻辑行只在一个轮转lane发送**，而非把每行parity也乘2/4份。新增 `GameTx::Mode::GameFecParity` 保留认证LogicalPacketId/AEAD/PN、独立lane轮转及绝对过期；off原Game复制未改。目的减轻 Game4 RX duplicate/前置Game owner mutex/M4与parity爆炸；没有修改RS、FEC r、TTL、外层重传、源码生成线程或Windows。已添加原生 `fec_game_parity_one_rotating_lane*` 及恢复候选source丢失测试，ARM64新build Action [40210946119](https://github.com/lly8666/wbd-next/actions/runs/40210946119) 待实际结果后才能测试新产物/决定保留。
- 如果修复后依然净路TCP/UDP失效，必须保留负例并**回滚 Game+FEC 产品候选（或fail-closed）**，绝不可让用户误以为已完成；底层下一步需严谨切分 Game RX原生驱动drop/接收序号、M4队列时延、FEC late/conflict几类失败，不无限扩线程/缓存/带宽。Windows继续TEMP_SKIPPED，capacity_stop不变。

## W90 最终产品决策：失败，原公开 Game2/Game4 接线原子回滚

原生 corrected候选 `c4b439ae891a7af5e7cf84476024479247c7ce21` 的 [ARM64 build 40211176601](https://github.com/lly8666/wbd-next/actions/runs/40211176601) 完整 SUCCESS，新增一次修复只走一个轮转lane、源包仍所有lane复制并先经过真实 M4 copied 门，原生FEC缺源恢复/TLS双侧profile确认仍通过。ZIP artifact `12605522541` SHA256 `939fe977a1393a6a3ae69e18074a5d6ad4603064eb7d7e4c1abc45dcb8de58be`。
- [Game2+Fixed0 source-first/one-lane-parity W90c 40211434490](https://github.com/lly8666/wbd-next/actions/runs/40211434490) **FAIL**，artifact `12606261548` SHA256 `fc8a52bf934926ae8a2bf320a9b751672557edc81b03ebc6291e78f750830a52`。Go TLS Fixed0已经双方applied、native 真正 M4ParityCopied client14/server42，client source14/server44，全程较低 host压力，**仍在 real TCP worker setup 时超时，没有测量损伤相位**；Game2完整产品门仍未过。
- [Game4+Fixed0 source-first/one-lane-parity W90c 40211439531](https://github.com/lly8666/wbd-next/actions/runs/40211439531) **FAIL**，artifact `12605632967` SHA256 `84171380468091c638568861308eb68df2f97b886e81d7085187beb173d5afce`。Game4真实业务穿过各相位但**无损 clean_before C→S UDP 4753/6869 =69.2% 到达（30.8%缺失）**，其它clean同样失败；client/server repair `rplanned=16355/16378` 但真正 M4Copied `15162/15211`，所以修复不能宣称“全部发出”；FEC authenticted恢复候选627/521、实际 Game TUN delivered38684/35961，不等于两向业务零损。source TUN drop0、host PSI peak2%不证明瓶颈不存在，M4 copied/raw receive与大量RX接收拒绝显示主要不足未归因；TCP回压、p99/小包门失败。不能拿原生纠错单测冒充 Linux real Full Pass。
- 精确全部**6个失败真实Actions** 与原始 SHA256、双模式、两个冗余档、源首交、rotating parity均归档 [W90 终局负例](../../evidence/fec-network-work/20261025-W90-GameFEC-product-candidate-FAILED-rollback.json)。不刷seed、不更改任何历史 Clean/小包/p99门，不开展更高带宽或 Windows。
- 由于候选协议/性能尚未产品合格，已经**在一次 Git tree 更新中原子回撤**所有15个本轮改动源码/Go CLI/harness/Linux ARM64 build workflow原 blob，删除新 `v4_game_fec.rs`；对应单提交 `b5052654975b4c3aa33fdabcb90d0e0803768315`，**16个路径严格与本轮入手commit `d4759a1dcd9cacc0cc40ff9d27379f1a733780bc`的blob相同/新模块不存在**。已有 W90 请求、commit/artifact、负结果证据/日志保留，未来调查可重放精确候选源码，不会把未合格`--game-fec`放进当前可用纯 Game2/Game4产品。
- 原子回撤后[ARM64 native build 40211941478](https://github.com/lly8666/wbd-next/actions/runs/40211941478) 和[maximum row contract 40211941508](https://github.com/lly8666/wbd-next/actions/runs/40211941508) 自动触发，**要以真实结束状态记录，不能预填通过**。共享 Normal/Fixed/Auto FEC 和 W88/W89 纯 Game 的限域证据仍按原验收门、原源代码有效；不会扩大为 Windows/Game+FEC 通过。
- 若用户再次授权实际修复，首个价值高的工作是**有界区分真实 Game M4 send_one失败、raw socket receive/drop、每lane PN/outerTCP sequence、FEC RX late/conflict/invalid 与 GameTx owner锁时间**，再做确定性 native TUN/TCP SYN/ACK短链路反例，不能追加更多修复线程、更大buffer或更高载伪绿。本轮结论严格限定 **Game+FEC 仍未接成可交付产品**，其他Windows本岗 `TEMP_SKIPPED_USER_20261025/NOT_RUN`，`merge_ready=false`、`capacity_stop=true`。
