# PLAN026｜Windows 方案 B：Go 冷控制、Rust 独占 Wintun/Npcap

> 2026-10-28 用户已选择方案 B。此文件是 **M0 的完整施工单，不是实现或测试 PASS**。M0 直接在 main 连续开发；Linux 当前真实 raw/TUN/Rust 数据面不重写。优先一次写全 Normal/off 的产品+调用方+Stop+测试+装配，集中 Actions/真实性能 A/B，达标再连续移植其他模式、Health、换 lane。任务授权看 main registry.goal；本计划先只更新文档，不代写 M0 cursor 的事实。

## 1. 定死的运行边界与成功标准

**Go 保留**：Windows FakeTCP SYN/TLS/uTLS、真实身份/特征协商和 exporter、Wintun 创建与验证、WFP/route/DNS/MTU、owned WAL/崩溃恢复、CLI/WinForms、按 Rust 事件重新建 lane。**Rust DLL 独占**：Wintun 的业务 RX/TX、Npcap 业务 RX/TX、AEAD/PN、M2反馈与真实发送结果、FEC2、Game调度、Keepalive/健康和低频定时。稳态 Go 对每个业务包 0 次 FFI、0 次 ReadSegment/WriteSegment、0 次 channel copy、0 次 Go pulse；Go 可阻塞等控制事件和按需低频统计，CPU 不应随 PPS 增长。换 lane 不重建 Wintun/WFP/系统路由。

**不做**：不翻译 Go TLS、不重写 Rust FEC/M2/Game、不新开后台daemon/localhost IPC、不让 Rust 从任意 cold bundle 假造认证、不在 Windows 上复制 Linux 的 syscalls、不先重构已有可用 Linux 路径。不写装饰性防御代码、第二套包装、重复热查询或无界缓存；但 TLS/PN/四元组/代次、驱动真实结果、Stop借用与 Windows owned WAL/WFP 是**必须保留的产品安全边界**，不得删除。

**分期但一次授权**：A=Normal/off Rust Native I/O + 真 Stop + CPU同机A/B；A完成且精确SOURCE功能和成本证明后 B=Fixed/Auto、Game2/4统一引擎+Health/动态lane。M0 不用每小函数请求审批，不为每helper发 Actions；一批产品代码、单测、夹具、manifest和读回**写齐后**冻结 SOURCE 集中编译/core/真实功能，再一个场景一条性能 Actions。失败定位首错并仅复测相关保护，不刷 seed。

## 2. 现有代码核对：哪些直接用，哪些必须替换

main 源码基线 `7c09b9396fb4d9086be212786758244172008a9d`。真实产品 assembly 可能把原 Go 源固定引入 `r0/go_overlay`；动旧 `internal/faketcp` 前先复核 **装配 manifest 使用的 Go pin 与 patch**，不可只改不装配的副本。老项目参考 `wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`。

| 文件/功能 | 已经具备，必须复用 | 需要改变 |
|---|---|---|
| `r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go` (~424行) | Go连接、真实 TLS/owner、Npcap启动、Wintun、系统 Applied、Auto/operator/Stop | 保留冷控制；**移除稳态 Go Npcap reader + nativeFrames channel + peer.pulse**，换为 Rust NativeOwner.Start/WaitControlEvent；GUI控制低频可留 |
| `.../m0_native_v4_peer_windows.go` (~968行) | 当前 Wintun 轮询/读取、Rust seal/open FFI、Go Npcap发送和 M2回执、窗口、Stop、已知 N0 反例 | **这些业务责任移给 Rust worker**；旧 Go 实现仅作隔离的 A/B 旧基线，禁止作为新引擎内隐数据通道 |
| `.../m0_native_v4_rx_window_windows.go` | TCP-looking seq/window 及旧大序列问题 | Rust 每 lane 精确 seq32→64展开、可信认证锚和replay；不因大跨度旧缺口拒绝合法新包；保留 TCP ACK 表观与真实PN分离 |
| `.../m0_native_v4_game_windows.go`、`.../m0_native_v4_game_peer_windows.go` | Game2/4 按 lane Go TLS + Rust adapter，Go 仍管 packet pump | 第二阶段同一 NativeOwner 接多个 lane，取代 Go Game pump；不是另写 Game engine |
| `internal/realityfront/bridge_v4_windows_scoped_client.go` 和 `bridge_v4_windows_game_group.go` | 真实 TLS scoped owner、受限 epoch、Game group、设备身份 | 加 **薄 versioned native attach/start/stop/replace ABI**；不能继续每包 FFI 大数组 |
| `internal/windowsclient/native_udp_kernel_driver_windows.go` | 真 Wintun kernel ring/loan、单一设备 owner、read/write/wait/Stop | 借给 Rust 同一个 session 和 read event，Go 不并发使用业务 ring；Rust停止归还后 Go 才能 close |
| `internal/windowsclient/native_unified_assembly_windows.go`、`native_unified_network_transaction.go`、`native_product_activation_windows.go`、LiveOS readback | 真 OS WFP/lease/MTU/DNS/route 五阶段及 WAL/Applied/撤销 | **不重造**；把真实 authenticated-packet proof/Drain 回执换为 Rust worker，Stop Rust→OS cleanup，换lane保留这一层 |
| 老Go `internal/faketcp/npcap_windows.go`、`npcap.go`、`npcap_send_batch.go` | `pcap_open_live`、准确4tuple BPF、pcap next、mode/sendqueue和部分复制前缀判断、单一 reader gate | handshake结束一次性 `DetachNativeCapture`：冻结Go读者、交出真正 `pcap_t` 和有界early ingress，Rust RX独占读；新的 Rust TX handle独立负责发送并且真实结算，不复制Go API成热桥 |
| `crates/wbd-engine/src/v4_windows_owner.rs` | 有效 Rust ProtectedScopedOwner、AEAD/PN、arena/M2/FEC2/Game和Wintun身份 | **在现有 owner 上装原生 I/O workers**，不新建第二份record密钥或M2状态 |
| `crates/wbd-engine/src/v4_embedded_go.rs` 与 `wbd-platform/src/linux_*.rs` | 已验证的Linux Rust raw/TUN及批量/driveroutcome | 对照语义/测试oracle；**本轮不改Linux执行代码** |
| `r0/go_overlay/assembly`、Windows signed Wintun/WinForms、原native Actions/WSL2 harness | 有真实构建及产品/OS资格入口 | 更新原生 DLL产物/manifest/build tags、CLI/GUI控件与读回，受影响测试不可丢 |

### 本轮必须带入的真实失败

M0 cursor H315–H318（基线 main）仍记载 Windows N0 双向10Mbps、单程300ms、240s 中 `produced=0 ready=4` 的 Go→Rust M1 source group 拒绝，另有 M2首发/M3打开历史首错。Action `40632194865` 当时 IN_PROGRESS；**M0接手先查现时终态**，把原异常保存为独立 Rust ingress/真实Wintun N0 反例，不得因为旧 Go source batch API 消失就把缺陷标PASS。旧SOURCE七模式真实功能正例仍属于旧SOURCE，不能继承为新NativeOwner。

## 3. 架构选择：两个固定 Rust worker，长期一个 Wintun

```text
 Go cold: handshake/TLS/identity/OS/WAL/UI  ── verified lane+native lease ─┐
 Go steady: block on event (no business reader or 5ms pulse)                │
                                                                      Rust TunnelOwner
     Rust TX worker (1)                                            Rust RX worker (1)
     Wintun receive event                                          Npcap per-lane capture event
     Wintun ring → owned M1 slab                                   exact 4tuple RX → M3 unique AEAD/PN
     encryption/FEC/M2 + ready-only batches                       shared LINK/FEC/first delivery
     shared Npcap TX pcap_t → Ethernet send                        Wintun allocate/send ring
```

- **一台 Windows 客户端一个逻辑 TunnelOwner、一个 Wintun session、一个 Rust TX worker、一个 Rust RX worker**；新增 lane 只增有界 lane 状态/精确 capture handle，不增高频 goroutine、worker或 Wintun。Game4 及短暂 old-retiring 在 Win32 等待句柄上限内；目标机验证 Npcap `pcap_getevent`，由同一个 RX worker 收敛 wait events + update/Stop，不反复扫描空 lane。
- Go握手时独占其`NpcapEndpoint`读者；认证成功后冻结并退出reader，**在受控detach时移交原 `pcap_t`**（而非再开一个接收者和争抢同一业务）。保留、排空有界的已读过渡帧和准确seq/ACK边界；Rust只能在认证及driver成功绑定后开始交付。若实际 Npcap handle 交接不成立，以**事实和可测的等价方案**另写小节决定，不得让两个业务reader长期并行。
- Rust TX **单独打开同NIC的发送专用 pcap handle**（所有lane共享），避免同一 `pcap_t` 被两个线程同时无锁读写；Go只持其握手期间短暂的发送权。发送可选择现有sendqueue方式，但在 Npcap 部分队列短写时只认**真实已复制前缀**，不重传uncertain可能已发的后缀；M2 接收 `Accepted/Uncertain/NotAttempted`，Accepted不等于对端ACK。
- Wintun由Go创建，Rust经已验证的NativeDevice lease仅**借用同session**；不可从字符串 GUID 任意 reopen 作为 product proof。Go不在Rust worker存活时Close/EndSession，Rust持有ring loan只到本轮使用并release，不把Npcap指针放进异步queue。Go原WAL/系统事务依旧是唯一OS manager。
- TX/RX 内部使用现有 Rust Arena/slab、原地 seal/open 和有界控制事件；Wintun copy至自有slab通常只需要一次。批量只发ready包，稀疏立即处理，不等待凑8/32；用 Win32 wait events、Rust M2/Health真实deadline唤醒，**不得固定5ms或1ms空转**。Go设备/identity/PnP核验在建链/变更/故障边界，不能每包调用系统API。原始CPU、thread wake、GC/RSS、PnP/NPF drop的观测必须可被关掉。
- Rust现有 `Registry<Mutex<Entry>>`只准在冷创建/读取状态/停止访问；worker持有固定的共享 owner 引用/分lane局部状态，热路径不得每包查global map和抢大锁。两方向用有界反馈queue，Stop严格退还inflight、冻结密文与驱动loan。
- 需要明确处理 underlay MAC/路由/MTU变化：由Go低频系统事件发有版本更新或触发重连；不能用每包重新查询路由来“保正确性”。真实TCP-looking IPv4 头/Persona/4tuple必须与旧Go wire兼容，Linux服务端无需调整。

## 4. ABI：一次性留好换 lane，不做每包桥

可调整具体命名但必须冻结下面**语义**，一份版本化C ABI（`abi_version`、`struct_size`、opaque handle、typed状态/StopReceipt）。不传 `*TUN`/`*NpcapEndpoint` Go heap 指针，不跨DLL释放的裸指针；原生句柄需要明确授权/唯一close与DLL引用期。

```text
CreateTunnel(GoTLSVerified, stableTunnelEpoch)  → Tunnel
AttachWintun(Tunnel, authenticated OS device lease, actual native session/readEvent)
AttachNpcapLane(Tunnel, Lane, transferred read pcap_t + exact flow/seq/persona/MAC)
StartNative(Tunnel)                            → Running
WaitControlEvent(Tunnel, cancel)               → LaneDue/Unhealthy/Wake/Dead/Fatal/Stopped
ReadStats/ReadStatus(Tunnel)                    → bounded snapshot
UpdatePolicy(Tunnel, revision, settings)        → accepted/applied/rejected
PrepareLaneReplacement(Tunnel, oldRef, authenticatedCandidate) → Candidate
CommitLaneReplacement(Tunnel, candidate)       → new Active, old Retiring
AbortLaneReplacement(Tunnel, candidate)        → release candidate only
RetireLane(Tunnel, oldRef)                     → fully quiesced
RequestStop/JoinAndRelease(Tunnel)             → final quiesced receipt
```

以上可以合并导出，但状态不能虚假简化。第一阶段 Normal/off 的未实现 lane操作返回明确 `UNSUPPORTED`，不能空成功；不需要额外的 per-packet Seal/Open/Transmit FFI。Go冷控制通过阻塞WaitControlEvent唤醒做TLS和CLI Stop，界面按需低频ReadStats不驱动协议工作；Windows Go跑起来不应该跟PPS相关。

状态为 `PREPARED→IO_ATTACHED→RUNNING→STOPPING→QUIESCED→RELEASED`，候选失败只回滚候选，不终止有效旧lane。新 `LaneSession` 内保持自己的密钥、PN/seq/nonce、4tuple、capture handle、健康时间；**TunnelEpoch 属于设备OS/WAL并在同一次隧道激活内固定**，不能让轮换出来的新 LaneIncarnation 抢过Wintun/WFP owner身份。Go user credential与TLS exporter必须来自真实受保护会话，保留 server/client 严格KDF和generation。

## 5. M0 Normal/off 连续编码任务（全写齐再集中 Actions）

1. **复核 main 原始边界**：从入口 `runM0NativeV4Windows` 追踪真正Go TLS/assoc→Npcap读goroutine→Rust owner→Wintun kernel loan→native OS product proof→Stop；对照 assembly生效路径及旧H315–318 run终态。只读盘点已有哪些封装，不重复引入第二OS policy。
2. **写 Rust Windows platform I/O**：推荐 `crates/wbd-platform/src/windows_npcap.rs`、`windows_wintun.rs`、`windows_wait.rs`；小范围 `unsafe` 审计岛（外部仍deny unsafe）；仅实现可借用的原生 `pcap_t` capture、一个共享TX handle、`pcap_next_ex`/sendqueue receipt、WintunRing读/释放/写、Win32事件wait及Stop。不要重写Rust crypto。
3. **写 Rust NativeOwner**：挂在已有 `crates/wbd-engine/src/v4_windows_owner.rs`，必要时分出 `windows_native_owner.rs`；Normal/off 两worker、现有 unique opener/PN/M2、Rust seq64和强制真实driver结果、single owner/Stop。先按已ready+事件驱动，别超前写通用线程池、工作窃取、空转poll。
4. **一次性交接 Go capture / Wintun lease**：在原Go Npcap实现或 R0 assembly有界补丁提供只允许一次 `DetachNativeCapture`，等Go reader彻底退出后移交已打开的句柄，保留early数据；Rust关闭唯一 owner handoff 资源且Go不能double close，DLL模块加载期直到join。Wintun同session加受guard的native借用，不重复StartSession；Go不再调用ring business API。
5. **接入完整产品路径**：改 `m0_native_v4_windows.go`、scoped Windows bridge和 `windowsclient` packet-proof / Stop；旧 `m0_native_v4_peer_windows.go` 的业务循环不再出现在默认Normal路径，可在显式A/B legacy构建中保留。打包DLL、Go build tags、CLI/WinForms有效状态及 WFP/route/DNS/WAL readback必须闭环，不能只在Unit测试生成fake Applied。
6. **同一开发批写完测试与夹具**：Rust driver/mock边界、Go endpoint移交后禁止Read/Close互踩、Wintun ring IPv4/IPv6/畸形包、Npcap partial/uncertain、wrap 2^31/2^32、旧H315–H318 `produced=0 ready=4` 等价native负例、Stop in-flight/取消、早到包交接、双向真实UDP/TCP、用户Disconnect+崩溃恢复。旧Go复用断言作为wire/身份oracle；**无真实签名设备的模拟测试不是产品PASS**。

**代码/测试/装配齐→固定一个SOURCE一次集中检查→Normal/off真实功能+N0 240s→同VM A/B性能。** Fail取首个error stage/rc与真实capture，不放宽旧条件；若A未过，后续模式不开始。

## 6. 必须证明的“性能最优”而不是宣传

同一个 Windows host/driver/NIC、同 Linux 服务端、同 MTU/FECoff/流量/波形、同完整源码+artifact hash的两腿顺序 A=旧 Go pump，B=新 Rust NativeOwner。每个performance Action只运行一个场景/一个测量job，同机 AB 或 BA；可以复用不同已编译产物但必须写清独立SOURCE。前一腿彻底Stop和cleanup再跑后一腿。性能新旧不得跨机器比较一个CPU%。

采集：真正 first-delivered/lost/late/duplicate/p50/p95/p99、双向TCP/UDP吞吐/PPS、outer bytes / fresh/control/repair，Windows Go线程CPU + Rust worker CPU + kernel CPU + 最忙单核、进程CPU秒/GB与百万包、idle wake次数/秒/平均睡眠、Go GC/heap、Rust Arena峰值/总RSS/私有工作集/handle count、Npcap driver dropped (测量段delta)、Wintun ring wait/drop、Go热路径FFI计数=0、Stop后线程/句柄归零。场景至少 **稀疏1pps、空闲、burst、正常10Mbps 0%/300ms N0 240s**；高吞吐按宿主容量和旧NETWORK_HARNESS/误差判断，若容量不足只记CAPACITY_LIMITED。

初始门槛：新Rust NativeOwner在业务等效下**总CPU应可测下降**、Go PPS相关CPU=0、空闲不高频唤醒、p99不能显著劣化、RSS及句柄增长有界、真实双向业务/Stop不弱于旧版；不虚报“50%降低”这种无依据固定值。若无改善，先profile Npcap event、batch、Wintun copy、锁，再做最小性能修复，不为写优化而换协议。

## 7. Normal/off 达标后迁移其余模式，接口从第一阶段预留

- **Fixed/Auto**：把现有 Rust FEC2 FixedStream + M2使用同NativeIO收发；Go真实TLS+OS/WAL仍保留，Auto不建立双控制器（既有低频Go controller可作为冷控制过渡，最终可由Rust健康信息驱动），revision/effective和block边界一致。应用时需要相同真实kernel/Stop证据。
- **Game2/4**：Go按2/4 lane 做旧TLS，不再有 `m0_native_v4_game_peer_windows.go` 的packet pump；同一TunnelOwner+共享Wintun+共享Npcap TX/一RX worker动态接入2/4精确 BPF capture handles。复用现有GameAdapter shared LINK/FEC/logic packetID、每lane独立AEAD/PN；坏lane不全组HOL，按真实driver发送结果计算副本，Game4错峰任务沿用绝对到期时间。现有Game group只有一次性join，**动态成员迁移尚需新代码**。
- **Health/Keepalive**：Rust codec 已有 `AUTHENTICATED_HEALTH_KIND=1`、`ControlTlv::LegacyHealth/LegacyQuality`，但现在 kind1 主要接 M2 receipt；先明确**认证解密+唯一PN后按TLV分流**，一个控制出口合并已ready M2/Health/Quality，不能新key、newPN、newTimer线程或误把Health刷新payload idle。旧Go 15s/90s只是有来源的历史默认策略，V4使用需明确配置/有效回读、真双端证据。
- **Make-Before-Break 换lane**：老项目 `internal/runtimeowner/runtime.go` 的 `BeginSameIDReplacement→PromoteSameIDReplacement→RetireIncarnation` 是语义oracle。Rust发现LaneDue/Unhealthy只发控制事件，Go短暂创建新4tuple/TLS和候选capture；Rust在旧lane活跃时Prepare新owner状态，认证+设备已ready后**原子发布新TX active**，旧lane仍RX/晚到/已冻结修复，限时排空/CloseWrite/完成或到grace后Stop旧capture。最多1 Active、1 Retiring、1 Candidate per logical lane、隧道一次仅一个转场；失败回滚候选不破坏健康旧lane，避免换lane时重置Wintun/WFP/DNS/route。旧3s grace只是初值，不保证绝对无丢包；源端口要避开正在Active/Retiring的tuple。Game2/4只换坏lane并保持其他lane业务。
- **休眠/唤醒**：Rust区分有效业务idle vs保活/反馈/重复，Go在确定Dormant/WakeDemand事件执行网络生命周期；首包需要有界持有/退避，不能丢新业务当成功。全部lane dead或OS设备失效才做完整重建。

## 8. 验收与交付边界

M0应一次持续施工，不分解成每函数一工单：
1. Normal/off的Rust Npcap/Wintun真实reader/writer、bridge、Go caller、OS/WAL产品/Stop、功能夹具和A/B旧版比较**全代码写齐**，集中Actions并定位首错；真实N0 240s+同机CPU/RSS/p99/空闲成本可比。迁移成功后旧Go业务pump不再默认运行。
2. 上述门过后，同一 NativeOwner 接Fixed/Auto/Game2/4并完成真实双端和Stop回归；再实现 Health、动态lane（只留接口尚未装线的必须记 `UNWIRED/NOT_RUN`，不得空成功）。
3. 同步 `docs/features/entries/*` 对应稳定卡片、Go CLI/config/GUI帮助、runtime有效配置readback、DLL/装配manifest/Actions、devlog feature-impact。不能把文档提交的SOURCE当产品新资格；Windows x64/Linux/ARM64/物理资格按实际RUN分范围。

提交必须复查**Go冷建链/OS侧 与 Rust native worker**、**Windows客户端 与 Linux原服务端**、**启动/stop两方向**，以及冷到热移交及热到冷退出每个资源句柄。保留旧未解释N0/80s问题和适用SOURCE，不能凭函数删除自然判修复。最终报告真实性能、失败与范围；无明确物理授权不部署真实用户机器。

```feature-impact
{"kind":"none","ids":[],"reason":"本文件只发布PLAN026执行和重构设计，不更改产品代码或默认配置；M0产品改造完成时须另行更新实际受影响功能卡和证据。"}
```
