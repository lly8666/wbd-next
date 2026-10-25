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
