# 引擎与模块设计

2026-10-18新FEC工作包的算法、包头、档位与自动决策以[FEC v2](FEC_V2_BALANCED.md)为准，覆盖本文沿用旧Go矩阵/20源/32ms等历史选择；本页owner/分层/冷控制复用要求仍适用。实施/已测资格读registry/evidence，不从设计推断。

实施细节以[模块施工说明v2](modules/README.md)为准。本文保留总览；模块页明确V4协商、bootstrap退休、无漏唤醒队列、e×e缺源解码、96B shadow槽预算和固定密文/动态外观头的区别。

## Windows NativeOwner v2 规则（覆盖旧热路径示意）
以 [PLAN026](../decisions/M0-PLAN026-WINDOWS-RUST-NATIVE-IO-OWNER-20261028.md) 和 [NativeOwner v2](WINDOWS_NATIVE_OWNER_V2.md) 为准：Go只负责Windows冷建链/OS租约，Rust完全拥有Windows Wintun/Npcap的V4业务I/O。本文早期“direct-TCP Go热路径例外”、Go稳定运行Auto/Health等应视为历史过渡；如果任何旁路仍需Go处理真实业务，必须明确UNWIRED/未完成，不可声称Go业务CPU=0。Normal/off性能及Stop证明先于Game迁移；Linux旧实现不重构。

## 1. 运行边界

一个客户端/服务端进程：原 Go 控制层加载同目录的 Rust `wbd_engine` 动态库；Windows GUI 仍为原 C# 方案。动态库及依赖随 portable 包放在同一目录，不运行时解压到系统目录。Linux 同样使用固定安装目录的库，不另开数据面微服务。

Go 保留真实 TLS/uTLS 建连与借站行为、认证/租约、生命周期策略、配置/UI、路由/DNS/WFP/Wintun 管理和自动 FEC 决策。Rust 负责逐包路径；通过低频 C ABI 接收不可变配置快照、lane admission、rotation/idle 命令，按需合并输出状态与计数。不逐包 cgo，不用 localhost TCP/UDP 转发来连接 Go 和 Rust。低频桥接成本单独量化。

Rust 从物理收发入口拥有唯一读取权。初始建连阶段，它将有界的 handshake 数据批次送给原 Go bootstrap 适配器；切换按 [01-CONTROL-BRIDGE](modules/01-CONTROL-BRIDGE.md) 的 Prepare→受保护回复→DetachTransition→CommitAdmission→双 owner 确认→Active 顺序。Go 交回真实 seq/ack、MSS、TCP options、TLS 派生材料、generation 和尚未消费的精确字节边界；prepared 路由有界收容 early 数据，Detach 成功及双向安装完成之前不交付业务。不能先激活再 Detach，也不能为移交停止唯一 reader。这里只改原建连接口适配，不重写借站/TLS 算法。

系统设备/过滤规则仍由 Go 创建和清理；Rust 持有明确生命周期的 I/O lease。停止顺序为：停止接收新任务→有界 drain/cancel→归还全部 driver buffer→`quiesced` 回执→Go 关闭句柄/撤销系统配置。超时退出须留下 owned 状态供原恢复流程处理，不能假称清理成功。panic 不穿越 FFI；Windows DLL 用同目录绝对路径加载。接口使用 `abi_version + struct_size`、整数/字节数组/opaque handle；禁止保留 Go heap 指针或向外暴露 Rust Vec/String。

原 `platformflow` 的 direct-TCP/gVisor 分流是一项明确保留的 Go 热路径例外：先通过有界批量桥接沿用，单独统计其 CPU 和延迟。重写一个 TCP 栈不属于本轮。不得因此宣称“所有流量已全 Rust”。

## 2. 模块依赖与执行所有权

建议一个 Cargo workspace，模块先维持少量 crate：`types`、`engine`、`recovery`、`codec`、`platform`；不拆多个仓库/网络进程。公共 wire/handle/clock 类型归 M0，其余按迁移表分配。

```text
TUN / 原业务入口
  → TX owner：分类、LINK、可选共享 FEC
  → 每 lane 独立 AEAD / seq / frozen-wire
  → ready-only 批量发送

raw / Npcap
  → RX owner：外层校验、独立 AEAD、shard 首次去重
  → 共享 FEC / LINK → 真实业务首次交付

RX → 有界 ACK/交付事件 → TX recovery
Go control ↔ 有界命令/快照 ↔ engine
```

- 正常繁忙 endpoint 从 TX/RX 两个独立 owner 开始；驱动必须阻塞等待时可有专用 I/O waiter。线程数按 endpoint/shard 定，不按 client/lane/FEC block 建线程或异步 task。
- 同一逻辑 tunnel 的 RX/FEC 保持在一个 owner；多客户端按稳定 hash 分片。每 owner 管自己的 slab、计时器、状态表，避免每包中央 map/锁。
- 跨 owner 用有界 SPSC 队列；动态多生产者只能在冷入口汇合。用armed+二次检查协议合并唤醒，不仅凭empty边沿判断；具体见02，避免消费者睡下时丢失事件。队列携带handle和明确释放责任。
- 每轮至多处理 32 个已经 ready 的包或约 100µs CPU 工作，然后检查另一类任务。**不等待凑满 batch**，稀疏包立即发；100µs 是待校准公平性参数，不是额外 sleep。
- RX 必须先交付可独立交付的 systematic，再做恢复计算。FEC 单个 block 的矩阵工作若在目标 ARM 上持续超过预算，使用一个有界编解码工作队列，最多一个该 block 的任务，完成按 generation 校验；不要无证据先引入工作窃取/线程池层层嵌套。
- 定时器采用 owner 本地的分桶到期表与非空桶索引，按实际 deadline 唤醒。最高精度约 1ms，不给每条 record 建 OS timer，也不每毫秒扫所有空槽。长寿命任务分层分桶。

## 3. 缓冲与复制

Buffer 是带完整 generation 的句柄：owner、slot、长度、headroom、tailroom、可变/冻结状态。slab 采用少量容量档（先 256/512/768/1536/2048，超 MTU 单独慢路径），空闲表属于 owner；不得为了对齐把 wire 补成固定大包。

固定 off：驱动输入必要的一次拷贝后，独立 AEAD 原地密封；LINK→AEAD→发送不重复 clone。raw header 和密文缓冲可用 scatter/gather；driver 必须连续布局时一次性组装。发送成功后同一 frozen-wire 同时供恢复缓存使用，不再复制整 record。修复缓存保留用户空间 buffer，不 pin Wintun/Npcap/AF_PACKET 收包环。

FEC on：systematic 第一时间发出，编码保留的是自己拥有的明文 shard；每 lane 有自己的密文输出。Game 共享明文/LINK/FEC，不能共享不同 lane 的密文。每个模块只借用/移动一次 handle，不每层 Arc clone。跨 TX/RX 的引用计数仅在必要共享处存在，最终释放回原 owner。

队列、重传缓存、FEC heavy、compact/dedup、fragment 各有独立字节/数量上界，全部纳入 endpoint 内存预算。恢复缓存压力只牺牲修复能力，不阻止新业务入队；实际发送过载仍要丢弃/背压适用入口并报告，不能用“无 HOL”承诺无穷处理能力。control 有很小独立额度，不能挤成无限高优先级流量。

## 4. Normal、Game 与 wire 边界

Normal/off：不构造 FEC TX 状态、不跑编码器；从 auto-on 切到 off 时，旧 block 的有限 RX/drain 状态仍存在。Normal/on/auto 共享一套 LINK→FEC→record；旧自动档的上/下行独立策略、普通/激进、固定/off 意图不能混淆。

Game2/4：先分配逻辑 PacketID，再在共同方向完成 LINK 封装/fragment/size-class/FEC。给每个 lane 提交 ready shard，哪个 lane 准备好就发，不先等所有 lane 完成 AEAD。RX 验证每个 lane 的独立 AEAD 后，以逻辑 block/shard ID 做共享恢复及首次交付。相同 shard 来自另一 lane 可以补齐第一 lane 丢失部分；后到副本不重复解码。不能用未认证的外层 ID 抢先丢掉唯一有效包。

旧 Game envelope 为 32B，包含 sessionID、PacketID、length、laneID；新引擎使用 **16B lane-neutral envelope**：magic/version 4B、PacketID 8B、length 2B、flags 2B。session/lane/generation 从已认证的 admission context 取得。这个变化必须通过既有 TLS 后 admission 消息的一次能力/version 协商确认，无额外往返、无每包重复协商。旧端明确拒绝不支持的 Game wire，不能自动误读；产品迁移要求两端一起换包。标准 TLS bootstrap 本身仍沿用原版。

FEC 首版继续旧 GF(256) generator 和 56B header，LINK/MTU 语义不趁机改变；BlockID 在逻辑方向统一分配，内部扩展成 64 位，wire32 位用有界 serial arithmetic。rotation 不重置仍存活的逻辑 block；新 lane 的 MSS 更小时从下一 block 边界采用新的最小 payload 预算，旧大 shard 不硬塞到它，其他 lane 继续工作。无 A+B 重叠能力时须报告，不能先 kill A 再建 B。

固定密文重传与新的 generation 隔离仍是硬门。TCP seq32 高频绕回必须有内部 extended offset，不能混同 record PN64、逻辑 PacketID64 或 FEC BlockID32。共享 FEC 的跨 lane 抗损收益只在独立/部分独立丢包下成立，共享物理黑洞不因为 4lane 就被数学消除。

## 5. 编码与加密后端

**FEC 选 Intel ISA-L 的 GF(2^8) erasure-code 子集，Rust 小型 FFI 包装，加标量参照后端。** 旧 Go 已经通过 klauspost/reedsolomon LowLevel/custom matrix 做 SIMD，包括 ARM NEON；这里目标是批量矩阵核、共享 Game 运算、缓存和内存所有权改善，不是第一次 SIMD。ISA-L 接受自定义矩阵，可保留旧 generator。只编译需要的编码文件；固定 upstream tag/commit 和许可证，不引入整个压缩/存储栈。

完整k20编码一次fused call；partial只算active columns，实际发送parity=min(active_k,配置parity)，header仍记配置档。解码对e个缺源求逆e×e矩阵，再构造直接输出系数，不重建parity；公式/输入顺序见07。每owner至多缓存64份近期矩阵，短shard走标量；没有无界组合cache，scratch padding不上网。

ISA-L 依赖调用者保证长度、别名、指针边界；FFI 一处验证并封装，系统调用错误路径也测试。x86_64 和 ARM64 使用 runtime ISA 分派；Windows x64 构建验证其受支持的 MSVC/汇编路径。无法得到合格向量后端时只能明确 FALLBACK，不能假报 SIMD。见官方 README 的编译要求。

**AEAD选aws-lc-rs非FIPS后端**：AES-128-GCM、AES-256-GCM、ChaCha20-Poly1305，显式独立nonce、原地seal/open、预建key。保留旧V3向量作为迁移oracle，V4新admission绑定对应新KDF向量，不能声称key逐字节不变。原AAD/nonce/8B HP格式不改；HP原语用RustCrypto aes/chacha20，不用QUIC的5B HP包装。低频bootstrap TLS不搬到新密码库。

不删除认证/完整性/nonce 不复用来换“性能”；这些同时保护正确性。真正优先删除重复 clone、重复编码、全表扫描、串行等待和多余封装。新增依赖 license/平台支持/portable flags 由 R0 固定，单凭网上 benchmark 不能宣布比旧版本快。

## 6. 平台 I/O 与可选加速

首版保留 AF_PACKET 与 Npcap/Wintun 的平台能力，Linux 收发使用已 ready 的 recvmmsg/sendmmsg 批次；旧版已有批处理能力，指标须对比实际额外改进。socket 缓冲设置后读取有效值、drops、queue age；只调大 buffer 不是吞吐优化结论。

packet_mmap 仅当 profile 显示系统调用/拷贝是主成本再实现；AF_XDP 作为以后可选 Linux 后端，不成为 ARM/Windows 的必要条件。标准 kTLS/TCP stream 会引入可靠有序依赖，不用它实现本项目无 HOL 数据面。GSO/GRO 不能跨独立 record 边界冒充报文完整；首次版本不靠它保证性能。空闲不 busy-spin，不能拿占满核心换一个漂亮 p99。

对外配置只暴露有用户意义的性能档/内存上限/已有业务参数，内部 batch、slab、timing 参数先作为诊断有效值。新增参数必须进入原统一参数目录、CLI/配置与适用 UI；避免几十个调参开关代替合理默认值。
