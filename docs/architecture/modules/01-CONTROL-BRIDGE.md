# 01 Go控制层与Rust引擎桥接

## 选择

保留原Go bootstrap可靠有序流（仅握手期间），Rust拥有平台reader。以已有 `BootstrapStream` 和 `StageTransition` 状态机为参考，不把它们的锁和重组缓冲带入steady。原 `Detach()` 只释放适配器、不发送FIN的行为必须保留。

只开放同步短C ABI：`engine_create(config_bytes)`、`engine_command(engine,command_bytes)`、`engine_poll_events(engine,out,capacity)`、`engine_wait_handle(engine)`、`engine_begin_stop(engine,deadline)`、`engine_destroy(engine)`。返回整数状态及required_len；out空间不足不消费事件。命令/事件采用版本化byte编码；Go传入slice仅在该次调用内借用，Rust当场复制冷参数，不保留Go指针。

Go单一控制goroutine消费事件，多个GUI/配置来源先在Go汇合，不让Rust控制队列变成无界MPMC。Rust线程不回调Go；原net.Conn适配器通过这条冷事件桥接Feed/Write/ACK。Linux使用cgo薄层，Windows使用原DLL加载方式/系统ABI，函数没有Rust专属布局。动态库不卸载到所有线程/回调完成之前。

## lane状态

`Created → Bootstrap → Prepared → Active → Draining → Quiesced → Removed`；任一阶段可到Aborting再Quiesced。generation一致才接受命令。Prepared的rx boundary、tx boundary、keys、MSS/WS/SACK/persona、policy、logical epoch必须一次性校验齐全后发布；RX/TX各确认本方向安装，Go才收到Activated。

唯一切换顺序：**Prepare → 受保护回复 → DetachTransition → CommitAdmission → 双 owner 安装确认 → Active/首次交付**。这是对早期“Active 后再 Detach”描述的修正，与当前 Go V4 调用点一致；不得按旧总览把顺序改回去。该契约不表示完整生产桥接已经验收。

1. Go创建系统资源和I/O lease，Rust注册唯一收包路由，bootstrap阶段只将该lane的段/ACK批次交旧适配器；其他Active lanes不经过Go。
2. 原TLS与用户认证成功后，服务端在最终保护回复可能到达客户端之前调用原适配器 PrepareTransition，取得精确 RX 边界，向 Rust Prepare 预留新 generation。此时只能保存有界 early 数据，不能交付业务或广告 lane 可用。TX 最终边界须包含保护回复实际消耗的 seq，不能猜测或在随后发送时继续改动已移交边界。
3. Go 发完/客户端校验受保护回复与派生材料后，执行 DetachTransition；把原适配器保有的 early records 及完成的边界交给 Rust。Detach 是移交 bootstrap 处理责任，不是关闭设备、释放 driver lease 或发送 FIN。移交期间物理 reader 仍唯一，Rust prepared 路由继续有界收容后续 early 包，不能存在双方都不接收的空窗。
4. 只有 DetachTransition 成功，可信 Go 会话调用点才提交 CommitAdmission。完整参数先验证，RX/TX 均安装成功后才发布 Active 并处理 early records；先到 early 包仍须经过真正 AEAD/PN 验证。Go 的 epoch/session 成功发布在 prepared owner commit 成功之后。任一方向安装失败都不得留下半激活 lane。
5. 边界之前仍属 bootstrap 退休上下文，之后属于 early/steady，单段跨边界按旧实现明确 TransitionOverlap 失败，不静默截断；中间设备重切段目前不承诺全支持。移交批次与 prepared 路由中的同一包只能由一个所有者接收并去重一次；迟到 bootstrap 不再喂给 steady AEAD。

失败边界：Prepare/回复/Detach 失败走原 AbortTransition 并撤销未发布 owner；回复或 Detach 已完成后 Commit 失败，当前候选 lane 必须失败退出，不能回滚到 bootstrap 重新喂同一批数据，也不能报告连接成功。abort/Stop 幂等；已经提交的 owner 走正常关闭而不是由 defer abort 销毁。early overflow、旧 generation、重复 commit、关闭与安装交错都只影响该候选，已有 Active lane 继续工作。真实 driver 借用在任何失败路径都须归还后才能释放。

bootstrap发送序号和重传仍由旧Go适配器决定，经Rust冷发送队列提交，不能保留第二个raw reader/writer。最终TLS/admission flight尚未ACK时保留有界`BootstrapRetiring`上下文，仅接收旧序号范围的ACK并重发原握手字节，按旧deadline退出；不得把边界后的record喂回TLS。steady不等旧flight全部ACK才启用，但seq所有权的边界必须固定，两个发送器不能同时推进同一序号。尾部退休后不再逐ACK穿Go。

边界初值继承旧64个bootstrap pending chunks、256KiB缓冲、4个flight chunks；early queue上界从原MaxTransitionRecords精确导入并纳入总预算。是握手限制，不可用于steady flow control或advertised window。满了只失败本lane握手，旧Active lane继续。

## 发布与关闭

immutable LaneConfig先构造，RX/TX通过命令安装，不共享可变密钥对象。关闭命令先将入口标Closing，停止新增工作，然后drain已接受业务至deadline，取消repair/parity/latejobs，解除reader route，回收driverlease，分别报RX/TX quiesced。Go收到所有确认后才EndSession/CloseAdapter/撤WFP/DNS/route；清理结果交原owned日志系统。

deadline到而driver不退出时标STOP_INCOMPLETE，不假报Disconnected、不强行free被引用内存。用户仍能重试清理/退出；原崩溃恢复接管owned残留。没有更多资源使用者时才destroy engine。重复Stop幂等，Destroy-before-quiesced返回Busy。旧lane失败不停止整个tunnel。

## 配置变更

hot参数（FEC决策、计数订阅）通过ConfigRevision在owner边界生效；key/cipher/MTU增减影响wire的参数建立新lane或明确下一block切换，不原地改正在Seal的context。客户端和服务端返回effective配置与拒绝原因；界面不能只显示用户输入。

## 资格

测试准备后断线、reply丢失/重复、early达到上界、Commit重复、Stop与Seal并发、late completion、Go GC压力、bootstrap失败退出、rotation旧lane不停。必须断言 Detach 前零业务交付、任一 owner 安装失败时零 Active/成功发布、Commit 失败不回灌 bootstrap、early 移交与新到包不重复交付。测试必须观察最后一个lease释放后才有quiesced。冷桥接CPU单列；steady正常包不得调用Go桥接，direct-TCP例外见10。

参考：[Rust FFI所有权边界](https://doc.rust-lang.org/nomicon/ffi.html)及旧项目上述两个适配器。这里是改I/O接入，不是重新开发TLS协议。
