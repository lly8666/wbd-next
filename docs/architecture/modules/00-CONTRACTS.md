# 00 公共类型、依赖和协议契约

2026-10-18的[FEC v2](../FEC_V2_BALANCED.md)授权新增一次性能力/kind/自描述短块契约，M0登记时冻结精确值。本页原bit0/bit1及只识别LINK/Health是旧已实现基线；V2新增位需两端明确支持且绑定原认证/KDF，不能假称无需协商。新block_id为u64，其他TCP/旧LINK的wire32规则不变。不要求与旧Go数据面网络互通，C ABI/控制层接线仍须实际验证。

## 模块边界

固定一个Cargo workspace：`wbd-types`（纯类型）、`wbd-codec`（record/LINK/FEC）、`wbd-recovery`（恢复纯状态机）、`wbd-platform`（设备/网络I/O）、`wbd-engine`（组合及cdylib）。后三者只依赖types与必要codec；platform不依赖engine，recovery不直接访问socket，codec不创建线程或读取系统时钟。engine是唯一组合者。测试fixture可引用所有模块，生产依赖不得倒置。

时钟由engine提供`MonoNs(u64)`，从进程单调起点计时，deadline用checked/saturating arithmetic；禁止把墙钟变化送进PTO/FEC/idle。配置用`ConfigRevision(u64)`不可变快照，变更只在owner循环边界安装。

固定标识：`TunnelKey(slot:u32,generation:u32)`、`LaneKey(tunnel,slot:u32,generation:u32)`、`RecordPn(u64)`、`SeqOffset(u64)`、`LogicalPacketId(u64)`、`BlockIdExt(u64)`、`BufferKey(slot:u32,generation:u32)`。不靠裸u32在模块间猜其含义。任何槽generation即将回绕时停用该槽，不回到旧值；wire32只用于已有TCP/FEC/fragment字段的有界扩展。

BufferKey只在所属arena/owner上下文有效。跨owner消息的队列端点明确source arena；C ABI不暴露这个key，仅暴露engine/lane opaque token。不得在64位key里压入指针再假称有generation校验。

## 输入输出（Rust内部契约；不是跨平台ABI布局）

| 模块 | 输入 | 输出 / 约束 |
|---|---|---|
| platform | `TxFrame{lane,seq,record_handle,carrier_snapshot}`批次 | `TxBatchOutcome{accepted_prefix, uncertain_index, error}`；返回时内核已复制或明确仍持有lease |
| record | `seal(keys,pn,kind,UniqueBuffer)` | `FrozenRecord`或错误；失败PN不重用 |
| record | `open(keys,wire:&mut [u8])` | authenticated `OpenedRecord{pn,kind,payload_range}`；范围不含tag/padding |
| LINK | `fragment(packet,FrameBudget,PacketId)` | frame handles；普通单包不封装新头 |
| FEC | `push_source(handle,now)` / `on_due(now)` | 先Systematic，再可选ParityJob；不直接发送 |
| recovery | `on_sent` / `on_receipt` / `on_timer` / `on_send_result` | Release / RepairCandidate / NextDeadline；没有等待fresh的方法 |
| engine | 上述事件 + `ControlCommand` | 业务Delivery、实际SendCompletion、低频状态事件 |

发送生命周期固定：**预留PN/seq → Seal一次 → Ready → syscall结果 → Commit成功/不确定/失败 → 缓存与预算结算**。密文已形成但未发送也不回退PN。Seq只允许在还未向任何发送方发布时撤销最后一个预留；第一版直接保留洞，不能为省一洞冒险复用。接收真确认只认认证过的record，外观ACK不能直接释放shadow。

错误分层：`Malformed/Unsupported/Stale/Duplicate/Late/NoCapacity/WouldBlock/IoUncertain/FatalLane/FatalEngine`。NoCapacity必须带受限资源；Duplicate/Late不是payload corruption。fatal只关闭受影响lane；共享engine invariant破坏才engine级关闭。任何错误不得输出未认证业务或伪造成功发送。

## M0 交付给四 worker 的可编译 Buffer 契约（G2/R1 首包）

公共Rust-only API 为 `wbd-types::buffer_contract`：`BufferOrigin{owner_arena,BufferKey(slot,generation)}`、`FrozenMetadata{LaneKey,SeqOffset,RecordPn,carrier_snapshot}`、`UniqueSealable`、`FrozenRecordHandle` 和 `driver_read(&Frozen)->DriverRead<'_>`。**这是最小所有权/借用接口而非真实内存池/性能证明，也不属于C ABI**。

- M1唯一分配者：arena生成`UniqueSealable`实现，有唯一可写窗口；所有headroom+payload+tag预分配同一内存；不跨owner传活裸slice，归还时检查owner+generation并提供bounded return queue/backlog。
- M3 seal：先分配PN（失败也烧号），持有`&mut [u8]`独占写窗口，就地AEAD/HP，成功后消费该唯一buffer调用`freeze(written_range,metadata)`；失败不能发布未认证密文，不能为封装分配第二份packet object。
- M2 recovery：只持有/复制`FrozenRecordHandle`的**handle**并引用既有PN/seq及同一密文，不重新Seal、不重新生成PN；若实际M1实现的clone复制payload，则不满足性能门。
- M4 driver：对冻结handle调用`driver_read`取得与handle寿命绑定的只读片段；若OS异步借用需再登记驱动lease，在真实completion/cancel后才归还owner。驱动不可取得密文可写访问。
- M0负责接口签名、模块连接和端到端回归，不自造第二个arena、第二份加密记录。本节最初只定义R0类型/mock范围；当前首包、持续业务和复制成本的完成范围读取精确SOURCE的evidence，不能用这段历史接口说明宣称仍未开工或已经全面通过。

具体slab/backlog、共享引用计数优化和有界关闭是M1/M4实现的实测要求。旧`wbd-platform::BorrowFence::wait_drained()`无限等待、按批Vec分类和锁/Arc都是**R0 fake correctness harness**，不是生产性能路径；生产停止必须提供单调deadline、超时仍有借用时不free的显式未清理状态（可以上报/隔离/留待完成），禁止超时强制释放仍被driver持有的缓冲区。尚未贯通时先完成Normal/off首包；已有同路径证据直接复用，不为后续集成重走逐包小台阶。

## V4 admission：最小一次性升级

原Go `realityfront/admission.go`、V3十字节policy、一次TLS保护的请求/回复保留。V4请求/回复在各自V3内容后附**24B扩展**：schema:u16=1，features:u16，tunnel_epoch:16B，feedback_page_limit:u8=8，reserved:3B=0；网络整数均大端。features固定bit0=receipt_v1、bit1=shared_game_v1，其他拒绝；Normal也使用相同明确版本，不嗅探新旧格式。

首lane请求epoch全零，服务端认证后分配随机逻辑epoch；同一逻辑tunnel新增/rotation lane请求必须带已分配epoch，服务端核租约/账号/tunnel绑定后原样确认。旧lane替换只换lane incarnation/key，不换逻辑epoch；idle重建按旧生命周期是否创建新tunnel决定epoch，不能混用上次未完成FEC。

旧TunnelID可能按installation稳定复用，并不等于本次逻辑运行的代次，所以不能直接省掉epoch再从1重置PacketID/BlockID。全新Game先完成一条lane的admission取得epoch，其余lane再并行建立，第一条可用即服务业务；每条握手没有新增往返。不得同时提交四个epoch=0让server分出四组共享FEC。首lane失败的候选epoch随candidate退出；同一TLS请求的重发复用原回复，不再分配。已有active tunnel的零epoch重建只在原Go生命周期明确允许新逻辑运行时执行；否则拒绝，不能收到一个请求就清空旧active状态。

ExporterContext沿用原序列化字段，然后纳入V4扩展的规范回复值；version=4。KDF info使用 `WBD-TLSLIKE-V4/<cipher>/c2s|s2c`，其他HKDF分段沿用旧76B。Go完成KDF，把各方向76B material交Rust。模块测试保留V3原向量另加V4向量；不要把V4期望密钥写成V3字节。只改受保护admission及其domain separation，不改TLS握手库/借站算法、不增加RTT。

V4尚未实现的能力不广告；旧端明确unsupported，正式包要求两端升级。不得自动降级到另一算法后仍显示原配置成功。

## Control bundle与Game

record kind保留LINK=0、Health=1；V4 Health payload可承载控制bundle：magic`WBC4`4B、schema1B=1、TLV数量1B、总长u16（含8B包头）。每TLV为type:u8、flags:u8=0、value_len:u16、value。type1为receipt（08）、type2为旧health字节、type3为旧质量报告字节；每包至多8TLV，总长不超record预算。首版所有未知type、非零flags、非法长度和重复receipt均拒绝；不可使用不可信长度跳出边界。旧9B health仍由显式legacy测试适配，不与V4生产嗅探混用。

Game envelope为magic`WBG4`4B、PacketID:u64、payload_len:u16、flags:u16=0，共16B，置于完整逻辑业务包前、LINK分片和FEC之前。因此所有lane共享相同fragment和shard字节。身份从经认证的lane→tunnel epoch映射取得，不删除逻辑身份隔离。

本页字段是编码基准，R0实现带显式offset的codec/golden；不得直接dump Rust/C struct上网。未知情况返回明确错误，不创造备用wire格式。

## 必测反例

旧V3端遇V4、未实现feature、错epoch、重复admission、ABI旧size、u32/u64边界、配置revision回退、初始化失败关闭。每项失败不产生可用steady lane；修复retry不能调用Seal。
