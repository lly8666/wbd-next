# PLAN026｜Fixed/Auto FEC2 与 Game2/Game4 接入同一 Windows Rust NativeOwner（研究／施工契约）

**2026-10-29，M0，状态 DESIGN_ONLY / NOT_WIRED / NOT_RUN。** 本文是用户新授权的方案研究，不是代码提交或功能资格。仍由 main `.governance/registry.json` 的 M0 PLAN026 goal 控制，遵从 [PLAN026 Windows Option B](M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md)、[FEC v2](../architecture/FEC_V2_BALANCED.md)、[Windows NativeOwner design](../architecture/WINDOWS_NATIVE_OWNER_V2.md)。产品源码与旧接口以当前 `main@44faf335` 逐文件核查为准，**不能从本文件推导任何新的 FEC/Game PASS**。

## 0. 恢复事实／已收口的边界

- Normal/off 的有界 Windows M2 优化属于旧 SOURCE `9ed3da31`；Linux client/server 相同设计的 1200ms bounded shadow floor 产品修复 `c5896861`，最终 Linux dual-native 真 50/100Mbps ×1/5/10/30%×50/150/300ms 24 场，`b9c2c170` Action [40733603221](https://github.com/lly8666/wbd-next/actions/runs/40733603221)：**50M 12 PASS、100M 10 PASS +2 INCONCLUSIVE**，后者 100M/1%/50ms CLIENT 与 100M/5%/50ms SERVER `pacing_catchup_limited=1`。全部48端均实际非零 R 且 R/(F+R) 0.475678%–8.197135%，max R/F 8.929063%，真实丢包和 Stop。两份独立 source evidence 在 `docs/evidence/M0/PLAN026-LINUX-DUAL-SOURCEB9C2-{50M,100M}-12-SIGNED-20261029.json`。不把两个红场改绿。
- Windows↔Linux 新产品 `bf84929b` 的母测试 Action [40734260484](https://github.com/lly8666/wbd-next/actions/runs/40734260484) 与 subsequent fanout：检查时 24 个 Windows native runs **23 success / 1 in_progress** (run40736177552); 不是 24/24 已结案。本研究不重启/延伸压力矩阵；保留原 Actions 自身终态。以上均是 Normal/off，不外推到 Fixed/Auto/Game。
- Windows NativeOwner 固定双 worker 的 Normal/off 已可运行；**当前 Windows Fixed/Auto 和 Game 仍有 Go 稳态包泵**。以前七模式的 signed original Go/Rust 功能 PASS 只证明旧路径，不证明下面的 Rust-only I/O。独立 150Mbps/物理旧 FAIL/NOT_RUN 不在本研究中改写。

## 1. 实际源码／热路径差异（不是拟议的重复引擎）

| 部位 | 当前精确源码 | 现存可复用能力 / 真正缺口 |
| --- | --- | --- |
| 已有 Windows 双 worker | `crates/wbd-engine/src/v4_windows_native_runtime.rs` | `stage_sources` 只走 `v3_seal_entry` Normal/off kind DATA；`open_and_deliver` 只走 `v5_open_record_entry` 与单个 IPv4 TUN delivery；`send_control` 只管 M2；`WbdWinNativeAttachV1` 单 flow/单 capture。TX event waits `Wintun,rx_notify,Stop,M2 deadlines`，RX wait `Npcap,early,Stop`，**暂不支持 FEC due、FEC multi-frame decode、Game 2/4 capture/复制 due**。 |
| Windows Fixed/Auto Rust 算法 | `v4_windows_fec2_owner.rs`, `v4_fixed_stream.rs`, `v4_windows_owner.rs`, `v4_fec2_live_rx.rs` | `stage_fixed_source_entry` 用实际 M1 slab + `FixedStream::offer_source` + kind2 AEAD；`stage_fixed_parity_entry` 每量子最多4行 kind3；`fixed_change_revision_entry` 含同代次 quiescent transition/M2 maturity reset；`open_symbol_entry` 在唯一 M3 open 后按 typed kind 解码，可一次恢复多个 source；`m2_kernel_firstsend_entry`/真实前缀预算已经存在。**缺口仅真实 native TX/RX worker 调用与事件 deadline，而非新FEC编码器。** |
| 旧 Windows Fixed/Auto Go 包泵 | `r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go`、`m0_native_v4_peer_windows.go`、`internal/realityfront/bridge_v4_windows_auto_controller.go` | 现有 mode 分支 Fixed/Auto 仍用 `newM0NativeV4PeerForMode`，Go `ReceiveReadyIPv4`、per-packet source input copy、Rust FFI、`endpoint.WriteSegment`、Go pulse；Auto 用真正 Rust mature2s/8s+actual-k 质量和 Go policy controller，不能另造第二策略。必须从产品默认移除旧包泵（旧实现只保留显式同 VM A/B 参考）。 |
| Windows Game 的 Rust owner | `v4_windows_game_owner.rs`, `v4_game_lane.rs`, `v4_game_fec.rs`、`windows_lane_lifecycle.rs` | Go TLS 完成后的 `WinGameGroup` 聚合 2/4 独立 AEAD/PN lane；同一个 `GameAdapter` 共享逻辑 packet ID、Game RX dedup 与可选 GameFecTx/Rx；`Game4` 独立 copy due；`stage_for_windows_native` 及真 M4 send-result、TUN prefix finish 已有。**缺口是绑定到同一 native runtime 的 2/4 RX capture、单共享 TX 和 Wintun、统一 wake/Stop；当前还通过分配 Vec / C ABI 批次往 Go 暴露业务包。** |
| 旧 Windows Game Go pump | `m0_native_v4_game_windows.go` + `m0_native_v4_game_peer_windows.go` | 每 lane Go Npcap reader → Go channel，Go 读/写 Wintun，`StageGameRecords/OpenGameRecord/OpenGameFecBatch/DueGameFecParity` 逐包调用；该段在 NativeOwner Game 默认路径**必须消失**，Go 只可冷建 2/4 套 FakeTCP/uTLS/授权 TLS lane。 |
| Rust Windows OS I/O | `crates/wbd-platform/src/windows_native_io.rs` | 真 `NpcapRx::event/read`、`NpcapTx::send_batch` 16KiB/最多8 ready queue、`WintunRx/Tx` scoped borrowed session、`WakeEvent` 和 `WaitForMultipleObjects` 最多64句柄。继续借 Go 创建的设备、只有 Rust 收发；不要重开 session、双重 pcap_close、每包 PnP、Go 回调。 |
| 原 Linux 能力 oracle | `v4_embedded_go.rs`, `v4_fixed_stream.rs`, `v4_game_public_kernel.rs`, `v4_game_lane.rs`, `r0/go_overlay/internal/realityfront/bridge_v4_game_native_linux.go` | 原始 Go TLS/identity 只做初始化；Rust raw/TUN 负责 M1/M2/M3/M4、FixedStream、GameAdapter、copy deadline、真内核结算。Linux Game 使用一个 Rust TX + **每lane一个Rust RX**，不是 Windows 最低线程数目标，不能直接照搬线程布局。Linux 若由 Go 低频 Auto controller 调整 policy，也不是Go每包收发的理由。 |

## 2. 建议唯一热架构：一 TunnelOwner / 两 Rust worker / 所有模式同一排队点

```text
 Go COLD: FakeTCP/TLS/exporter + 2/4 authenticated lane setup + OS/WAL/Wintun
            │ exactly-once versioned native handle/lease transfer
            ▼
  Rust TunnelOwner {mode: Normal | Fixed | Auto | Game2 | Game4}
        ONE Wintun session / tunnel epoch / OS owner / first-delivery policy
        ├─ TX worker (one per tunnel)
        │    Wintun ready → original M1/Arena → mode dispatcher
        │      Normal: kind DATA → AEAD/PN → NPF
        │      Fixed: FixedStream kind2 sources IMMEDIATE → NPF
        │          monotonic FEC close → bounded <=4 kind3 parity quantum → NPF
        │      Auto: same FixedStream; one M2 mature-evidence policy actor
        │      Game: ONE logical LINK/FEC source, GameAdapter fanout
        │          2/4 independent lane AEAD+PN → shared NPF TX
        │          independent Game4 copy and FEC parity deadlines
        │    exact NPF prefix disposition → same owner M2/FEC/Game credit
        └─ RX worker (one per tunnel, not each Game lane)
             wait {Stop,Update,early-ready, Npcap RX events lane1..lane4}
             fair bounded ready-drain per lane (<=32 frames/turn)
             per-lane AEAD + original PN/replay + seq32 unwrap
             Fixed: typed SOURCE/REPAIR → one Fec2LiveRx
             Game: unique per-lane open → shared logical ID dedup/FEC decode
             true Wintun copied prefix → logical first-delivery commit
             bounded wake to TX for authentic M2/ACK/control
```

**不要**先把 Linux Game TX+N RX 线程照搬至 Windows：Win32 WaitForMultipleObjects 原生最多64句柄，4 lane + Stop + Update + Early 足够。一个 RX 按 lane 限量轮转，防止高损坏/坏一条lane饿死其余lane；每lane仍各有 PN、密钥、seq窗口、Npcap RX 句柄。跨 lane 只在必要的 GameRx/FEC/逻辑ID commit 持短锁；先在本 worker完成 AEAD，再共享判重，不在锁内阻塞 Wintun/NPF。与 Linux 可并发 RX 的差异需要**真实高PPS锁/队列等待**验证；单 RX 成本若被证实吞吐/交付不足，再精准调整，不先引入线程池。

数据不经 Go：实际 Wintun Read/Write、Npcap Read/Write、LINK/FEC/AEAD、M2/Health、Game调度全部 Rust；**运行中每业务包 Go FFI/Go channel/Go ReadSegment/WriteSegment/Go pulse 必须为0**。一秒统计/OS只读检查可限为冷控制或由OS事件触发，不能以高频Go定时器驱动协议。Rust ready-only NPF 8帧批，稀疏立即发送；窗口不足允许早退、不强制聚齐。预分配 Arena/小栈批，勿为每包构造Game `Vec<Vec<u8>>`、共享global map或查询DLL Proc。

## 3. Native ABI 升级和真实 Go→Rust 所有权

- **V2** typed `TunnelNativeAttachV2{abi_version,size,tunnel_epoch,device_lease, mode,effective_policy, shared_tx_capture, per_lane[N<=4]{authenticated_owner_ref,persona,flow,initial_seq32,rx_capture}} `；V1 Normal/off ABI不破坏，V2入口不能把未支持模式虚报为成功。Go 原有 `V4WindowsEstablishOriginalFEC2ClientOwner` 与 `V4WindowsEstablishOriginalGameClientGroup` 负责真正凭据/TLS/KDF及feature7/GameFec; Rust仅接受同一原 TLS 保护的 scoped handles。
- 任何模式 `Attach→ValidateAllBorrowed→StartNative→ReadEffective→Applied`。多lane只有同 tunnel epoch 和正确 owner、MTU、4tuple/ifindex，且Go读者完整退出、early frame 有界移交后才会启动。Npcap RX per lane、Npcap TX 单独独占句柄，Go持有 DLL/borrow 生命周期直到 Rust join；Wintun OS/WAL/route始终一个实例。
- `mode` 和 `feature7/profile/revision` 是原认证后真实生效读回，不允许从CLI enum伪造启用。Windows Fixed/Auto 的当前 `m2.arm` 与 Rust FEC owner唯一，Game group已有Rust owner要**移动/引用同一个实例**而不是再实例化第二个 GameAdapter/密钥/PN。候选 lane 的 owner只来自新的真实 Go TLS；不从字符串、裸指针、GUI选择实例化密钥。
- 一次 native block/control接口可提供 `Start/WaitControlEvent/ReadStats/UpdatePolicy/PrepareCandidate/Commit/Abort/Retire/RequestStop/Join`；不是 per-packet `Seal/Open`。当前 `windows_lane_lifecycle.rs` 已有 Candidate/Active/Retiring 与旧代次屏障，但**不是已接线 Native I/O**，单独严格标为后续工作。

## 4. Fixed/Auto 具体接线、CPU开销约束

1. **Fixed TX**：真实 Wintun 已ready原帧批 → `stage_fixed_source_entry` 产生 type2 受保护源、同一原Owner的 seq/PN → ready-only NPF 批；成功前缀结算真实 M4 & M2 F；绝不等FEC block满再发首包。独立 `FixedStream::next_deadline()` 与下一批 ready parity；每轮最多既有4行 quantum，不循环编码所有排队行饿死新包。parity 使用 kind3 独立 AEAD/PN，不占逻辑新业务第一到达。NPF `Accepted/Uncertain/NotSent` 三态用于 `FixedStream::settle_staged` 和 M2，不能当 peer ACK。
2. **Fixed RX**：一次 per-lane M3 authenticated PN/open 后交给 `Fec2LiveRx` typed source/repair。源能交付立即 Wintun；最多16个真恢复帧有界提交，prefix 失败保留未交付状态；不等待下一组、不为每包分配新的Vec/FFI复制数组。反向kind1是同一RX control入口，不要在Go再开反馈worker。Off仍走现有短路径，不做空FEC轮询。
3. **Auto**：共用上述 FixedStream。Linux原同源Go `FecV2Step`/Windows `bridge_v4_windows_auto_controller.go` 的 mature 2s/8s、actual-k、UNKNOWN/censored/host-capacity gating 是**语义oracle**。最终要只有一个 Rust 内部低频 revision/policy actor读取 M2成熟证据后 `quiescent_change`；不保留Go 1Hz `Tick` 与Rust第二controller并行。为降低迁移风险先以纯Rust policy replay测试对齐已有Go golden，之后才切Rust唯一owner。Go只低频接 operator、GUI请求，版本化 revision/event 回执到 Rust；未验证的自然/丢包上升降档不得写APPLIED。Auto保留既有<=120s策略资格的精确SOURCE边界；窗口不成熟时保持 UNKNOWN 和当前配置。
4. **事件调度**：TX wait timeout=min(M2反馈/M2候选、Fixed FEC block close、Game due、Health due) 同一个单调时间基准；无真实待办使用 INFINITE wait。Linux `GameAdapter` 和 Windows M2 当前计时原点不同，**绝不可直接比较不同原点的绝对 deadline**；要么统一 TunnelClock，要么按各自单调clock换算剩余时间后取min。到期立即 ready 发，不设5ms/1ms空轮询。只使用有需要的update/Stop/NPF/Wintun kernel events唤醒。

## 5. Game2/4 (含固定GameFEC) 具体接线

- Go按2/4条真正原 TLS 做冷握手后一次Join，Rust同一GameAdapter拥有一个共享逻辑 LINK/FEC TX+RX与每lane独立AEAD/PN。**不是每lane单独编码一次FEC**，也不能用复制副本作为外层同 lane RETRANSMISSION；每个lane复制同一逻辑symbol独立 M4结果，M2预算/repair不能把Game多lane容错成本算成Normal重传。
- TX一轮：原Wintun source立即 `GameAdapter::offer` → 单逻辑packetID和可选FEC typed symbols → `stage_for_windows_native`/真实内部 staged tickets → 各lane生成真正加密wire、NPF按lane exact MAC/tuple/seq发送；预留错峰 Game4 + FEC close 的真实 deadline。不要“每lane等满”或长时间等坏lane；失败lane拒绝其后ticket，但仍健康lane的独立第一到达；每次真实前缀driver后结算copy、GameFEC source credit与 parity row，不在尚未发出时提前计数。
- RX唯一worker为每个可就绪的Npcap lane限量drain，提前做原lane AEAD/replay（参考Linux `GameLaneOpener`），进入一个共享 `GameReceiveOwner` 的逻辑去重/FEC decode；`GameFEC` 可吐多帧，先做真正Wintun copied-prefix再 `finish_fec_batch`；其他lane的晚到/重复不得再次交付或延长同业务尾延迟。健康lane不能因为坏lane队列/锁/延迟而跨业务HOL。
- 静态Game2/4先做到真实全join/真实Stop。动态Make-Before-Break后续复用 `TunnelLanes` state machine：老代次RX/尾包允许有界Retiring；新候选只有经过Go真实 TLS、BPF与设备ready才原子发布 TX active，且同隧道最多一个候选/老代次；失败只Abort候选，不重启Wintun或WFP。**现有Windows Game group一次性join，不得写成动态lanes已实现。**
- 暂不要抄 Linux `v4_game_public_kernel.rs` 的每lane RX线程、10ms poll和 idle `sleep(2ms)` 到 Windows：Windows已有 `NpcapRx::event`；只移植GameAdapter/first-delivery、发送真实回执与期限逻辑。若4lane wait handle失效，报告native capability FAIL，不私下退回Go包泵。

## 6. 代码施工优先序／最小回归与完整验收（未执行）

**一次完整实现批次再集中Actions：**
1. `v4_windows_native_runtime.rs` 引入 mode-aware NativeAttachV2/一对长期worker的统一 Wintun/NPF/Stop、per-lane descriptor；`windows_native_io.rs` 只做必要的多Event handle归属与driver prefix微改。Go scoped windows bridge/loader + CLI prepare/WinForms/Stop与mode readback同步接线；反对另一套global registry、通用线程池。
2. Fixed/Auto TX/RX调用已经存在的 `stage_fixed_source_entry`、`stage_fixed_parity_entry`、`open_symbol_entry`、`m2_*` 原Owner；实现 typed FEC event wake、first-source priority、driver accepted/uncertain/not-sent，复用 Linux FixedStream 的 native benchmark/oracles。Auto policy确定为一个Rust actor后关掉旧Go tick；保持版本化配置/真实生效读回。
3. Game2/4统一NativeOwner挂接现有 `WinGameGroup`，共享Wintun+NPF TX，一 RX公平处理最多4 captures、提前per-lane解密、共享GameRx/FEC逻辑、错峰和每lane M4 exact-prefix settle；从默认产品移除 `m0_native_v4_game_peer_windows.go` 的全部数据loop/channel/Go per-packet FFI。只保留独立A/B旧源路径。
4. 同批写ABI布局/struct_size、调用方、signed驱动装配、CLI配置/帮助/GUI effective、Stop/失败回滚、单测、真实场景夹具和SOURCE manifest；再冻结一个SOURCE。未真正接线模式必须返回 UNSUPPORTED，不准静默走legacy Go或报Rust-native。

**便宜回归**：Windows Rust core+Go编译与ABI、Linux Rust FixedStream/GameAdapter黄金测试、C ABI内存布局、Npcap借用/移交、MTU seq32 wrap与loss no-fresh-HOL、FEC kind2/3与kind1同键认证、parity4行quanta失败/uncertain、Game4即刻首副本及50/140ms实际到期、RX once delivery/partial TUN、多lane Stop、Auto 2s/8s maturity/revision、孤立lane故障和4lane公平性；新Rust模式无任何稳态Go ReadSegment/WriteSegment/Go pulse/业务channel。

**官方产品功能**：固定真实 Go TLS/签名 Npcap/Wintun ↔Linux原Rust raw/TUN，用真实源编译Windows Fixed/Auto、Game2/4 off + Game2/4 fixedFEC，对应各模式至少双向UDP/TCP first delivery、FEC真实核内恢复/实际k/r、M2反馈、mode/profile/revision APPLIED、Game每lane copy+去重、owned Stop/WAL；原有七模式Go稳态旧正例不转移。Linux不重新测已经PASS的逻辑，作为协议oracle。但产品cross-platform 新SOURCE仍须同一build真实兼容证据。

**性能**：仅功能合批正向后，一个性能 job 一个损伤场景，旧Go泵 vs Rust-native同Windows VM连续A/B（同runner同驱动同场景同MTU、每腿严格Stop），分别Fixed、Auto、Game2、Game4真实业务≥1个代表负载：持续、空闲/1pps/burst、真实FEC丢包、Game2/4坏1条lane和Game4错峰。严禁不同VM CPU%做收益。采原EXE Go+Rust整进程 CPU seconds/first-delivered GiB、kernel/user/线程CPU、Go FFI和packet-pump计数0、Rust wake/s、每包malloc/arena峰值/handles/RSS、Npcap copy+drop、Wintun原生ring占用、真实 offered/first/p99/UDP+TCP、GF编码quantum耗时与FEC恢复、真实Stop；强调旧Win100M30%50ms Normal/off product kernel CPU曾较高，不保证新模式绝对省CPU。**先确认业务等价、Go PPS相关工作归零与成本可测下降**，再报告模式资格。任何容量受限或驱动unsupported不刷seed、不做假PASS。

## 7. 本批决定与未完成项

决定：*复用 Rust 现有唯一协议 owner，在当前2 worker Windows NativeOwner上把mode dispatcher与shared typed native I/O接通*；非每包FFI；不用新Go data plane，不给每Game lane加 Rust线程，不改已成熟Linux原内核收发，不修改 FEC v2编码矩阵/参数，也不轻易把Health/动态lane“顺便完成”。

未完成：NativeAttachV2与Fixed/Auto/Game Rust-only I/O **尚未实现**，native mode-specific SOURCE Actions **NOT_RUN**，Health/Make-Before-Break最终接线 **NOT_RUN**，物理 Windows/150Mbps/同机模式 CPU A/B **NOT_RUN**。目前只研究与明确施工契约，旧Normal和Linux24真实结果不升级成这些模式的资格。
