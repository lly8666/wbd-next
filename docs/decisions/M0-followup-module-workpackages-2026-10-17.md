# M0 / PACK-007 — 已交付工位的一次后续完整包（2026-10-17）

## 权威与分配原因

main registry revision2/epoch1 继续作为唯一权限/任务权威；在精确 main `9dd248d64d42dcb2e0273d169e075dfc2d77e7c2` 上确认：M1 HEAD `01cdc623d0722fc2c1f47c23a4c2024752ac4d94` cursor seq13 `ready_for_integration`，CODE S `89a3acb23616a46ecc65fc2dcd0b75182b6b482a` 98/98 worker native [38998296147](https://github.com/lly8666/wbd-next/actions/runs/38998296147) PASS；M4 HEAD `42a622f30317f32f105ce13f2b298f9f05f14615` seq15 `ready_for_integration`，CODE S `aae512d1953975476ab78081f5801436c6573fda` 88/88 unprivileged platform native [38998105581](https://github.com/lly8666/wbd-next/actions/runs/38998105581) PASS。两工位完成原 `PACK-006` 权限内组件，属于已交付、可登记新包；不凭提交时间猜 worker 失联。旧cursor/H和worker CODE 与历史 run 保留，不要求工位重置分支。独立 scope audit 和 root old harness 失败不抹去；主线修正版 root ABI 脚本不自动替worker分支的旧脚本 PASS。

M2 `R2-M2-RECEIPT-REPAIR-BOUNDED-WORKPACK-009` 仍 partial（63/63 scoped source `269fd8f88ba6df97ebb8fe1f3e29cc58b1ca90c2`、PTO tail/32 real RACK evidence待修；分支H cursor refs历史FAIL保留）；M3 `R1-M3-RECORD-LINK-FEC-WORKPACK-016` 仍 partial且已有H后新CODE，依本包自主推进。**M2/M3任务和所有worker权限/branch/epoch均不变。**

本控制提交首先逐blob集成 **M4已完成011** 的 platform 原有模块精确 SOURCE `aae512d1953975476ab78081f5801436c6573fda` 到main，文件列表 `linux_batch.rs`、`linux_raw_carrier.rs`、`linux_tun_sink.rs`、新增 `linux_mtu_scope.rs`、`lib.rs`。M0未手工修改M4源码；原`linux_packet_preflight.rs`和`linux_route_events.rs`在main与此SOURCE相同，故不覆盖。集成是否成功另以**main新CODE SOURCE** GitHub Actions native/真实Go Rust kernel回归判定，工位unprivileged PASS不能继承为真实raw/TUN PASS。以后M4只在工作分支自主改012；M0不得和它并写同一platform源文件，有集成修改交M4固定最小补丁，待完成安全边界串行合并。M0在自有engine/Go/probe里调用冻结接口。

## M1 `R1-M1-DIRECTIONAL-OWNER-SPSC-WAKE-012`

- **为什么**：M0 024已消除进程全局registry DATA锁，但同一受保护session TX/RX仍共用 `ProtectedScopedOwner` 的一个 `Mutex<Entry>`，真实多worker会互等。旧011仅抽象ReadyTurn和有界返回，尚无真正SPSC/OS wake。完整本包形成可供M0组成真正方向owned worker的最小实际运行时接口。
- **施工**：`docs/architecture/modules/02-RUNTIME.md`、`03-MEMORY.md`、依赖00契约。实现实际单生产者→单消费者的 bounded **rtrb** TX/RX publish/consume接口以及STOP/epoch借用栅栏、失败后可重试的armed/wake（linux native条件优先，Windows不可用明确NOT_RUN）、线程归还多生产者审查；复用已有011 `ReadyTurn`、`WakeGate`、`Arena::drain_returns_bounded`。不得仅交换两个Mutex字段就假装AEAD/PN状态已拆开，owner token/generation不泄露。满队列返回原UniqueBuffer/FrozenHandle；不在worker写原Go认证/cipher/wire/new unsafe SPSC。
- **许可**：仅main registry已有 M1 `crates/wbd-engine/src/runtime/`、`memory/`、`tests/`及M1 docs/cursor/requests。M0负责共享 `Cargo.toml`/`Cargo.lock` rtrb pin、loom dev-only及共享CI；缺依赖时先做可验收的无依赖有界接口/其他反例，**明确BLOCKED部分**，不能用自造unsafe队列代替真实rtrb。
- **done_when**：0/1/32/33 ready/no-fill、不同TX/RX方向不共争可变owner、满额pressure返回原句柄、lost wake重试、Stop前后悬挂borrow归还、generation旧回调拒绝、新流首到不被旧队头卡住、100µs/32公平与实际wire byte parity成本，精确SOURCE native Actions成组；提供给M0能够消费的稳定方向接口/最小签名和fallback。Go保护+raw/TUN真实资格、rtrb/loom/OS事件未确证、物理平台均按实 NOT_RUN。不反复跑已验证旧011用例。

## M4 `R1-M4-RAW-TUN-STOP-PMTU-RACE-012`

- **为什么**：011已交付 revisioned netlink/MTU缓存、typed KernelSendSignal、raw/TUN <=32 ready I/O，但真实接口删除/换ifindex、route-storm、EMSGSIZE/partial与Stop/晚loan并发仍需要更完整的本职平台硬门与可组合接口。M0只做受保护Go→Rust engine层接线；M4负责平台层错误/借用事实和测试。
- **施工**：`04-CARRIER-IO.md`及`06-LINK-MTU.md`直接依赖，复用main的旧单一`linux_route_events.rs` watcher，不另造监听器。覆盖 link/route事件与1秒TTL和100ms debounce、原始`ifname/ifindex/generation`绑定、DF/EMSGSIZE/ENODEV、raw Tx uncertain prefix+suffix分类、TUN ShortWrite、Stop与在途借用/关闭、old-generation after Stop，以及连接撤销后绝不带旧冻结密文按新MTU重封。真实系统可用 native runner 时只在有界网络命名空间跑实际 Linux 原生测试，缺 CAP_NET_RAW/CAP_NET_ADMIN 一律UNSUPPORTED/NOT_RUN，不擅自扩权或动用户机器。真实sendto连续批不宣称一个sendmmsg raw syscall。
- **许可**：仅registry内`crates/wbd-platform/`、`r1/go-bridge/`、M4 docs/cursor/requests。不得自写Go TLS凭证断言或跨engine owner API、根CI/Cargo；集成期间平台源码为**M4单一作者**，M0只对011已冻结blob做一次原样集成，012后续需修改同一文件必须从新交付SOURCE串行集成。
- **done_when**：受影响 I01–I04、B01–B04、L01、P01 指向的设备/MTU、partial/uncertain、Stop/loan/generation、0/1/32/33及bad slice先检查反例的单批native结果、资源上限、具体接口/fallback、exact-source产物与失败/NOT_RUN都留痕，M0可独立接线。Linux真实设备正向、Windows/ARM native、500Mbps、prod0和物理资格只在真正测得时才升级。

## M0 / 024 与共享待办

- 保留任务 `R1-M0-HOTPATH-COST-024`、原Go TLS认证→Rust原M1/M3 owner→raw/TUN、原023资格未验证、production feature0；本次只使两个空闲工位有后续授权，不为每个断言派单，不增加新目录权限、另设工位或调整M2/M3。
- 主线 M0 实际待接线：将M4-011 `ScopedRouteBudget` error/MTU fail-close及ready driver与原 `v4_embedded_go.rs` 相连，不把另一个cache作为新authority；用M1-011已冻结ReadyTurn/有界returns让真实owner改善服务公平，同时为012将来的同会话TX/RX独立PN/AEAD owner状态拆分留出明确接口。
- **共享请求处理**：M1 `M1-R1-SPSC-DEPS.md` 所需rtrb/loom和 M3 `M0-REQUEST-PACK016-NATIVE-ISA-L.md` 受控ISA-L链接及原Go矩阵的安全绑定由 M0 在共享 Cargo/lock/Actions 固定版处理；M1 `M1-R0-ABI-HARNESS.md` 旧worker branch硬编码"3 passed"问题已在main `tools/r0_abi_bundle.py`修正，不把老branch历史FAIL洗掉，不授权M1写根工具。
- M0之后在Actions证明真实driver+Go session功能、Stop、MTU变化、D10/SPARSE、预编译同VM Rust P10 AB和独立BA。普通 push Governance、worker scoped unit、platform UDP本地通过都不表示产品PASS。
- `PACK-006` 原已交付CODE与证据历史仍保留，原worker checkpoint无需覆盖。发生共同ABI或活跃写冲突即报告阻塞并做最小串行接口变更。
