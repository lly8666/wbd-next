# 03 缓冲、引用和资源预算

## 类型与所有权

首版池用owner私有的分页arena和预分配`Box<[u8]>` slab。page内slot不搬动，空闲索引用Vec栈；先用安全Rust的slot索引借用，不为“零拷贝”直接造跨线程裸指针。`UniqueBuffer`可修改；seal后成为`FrozenRecord`仅可读，必须全部引用释放后才回到free list。生命周期不依赖GC。

选择能装下**实际headroom+record+tailroom**的最小slab：256/512/768/1536/2048；配置jumbo时加4096/8192/16384档，最大65535兼容包单独慢池。分配不先清整个slab，只写即将上网/参与编码的范围，禁止把dirty尾当合法padding或GF零源。

跨owner传递包含完整所有权的buffer对象/lease，不传一个无生命期的slice。driver临时buffer必须先拷贝到owned slab再调用下一次读取。跨owner最终释放通过单独return SPSC回到arena owner；return队列满时留在consumer有界return backlog（容量等于已借出的最大handle数），继续尝试，不能drop key造成泄漏或阻塞整个业务。池耗尽时明确NoCapacity，不能把回收任务丢掉。

跨owner lease引用机制只封装在一个小模块，必要unsafe逐项说明地址稳定/唯一可变借用/归还条件并用Miri/loom测；不能把unsafe分散到codec。owner内部Game/FEC引用为普通计数和generation key，不每个副本new Arc。buffer从分配到释放必须能画出唯一责任链。

return的“单生产者”按**可能执行最后一次Drop的线程**计算，不能因都归一个lane就当SPSC。多个completion/consumer可归还时，使用固定生产者对的独立SPSC并合并消费，或沿用经验证的有界MPSC；不要只为符合库选型强换队列或新增unsafe。return backlog和未完成driver loan都计入总预算；Stop后仍有借用必须保留归还通路，不关消费者再等待生产者退出。池payload复用不代表零分配，Arc控制块、Vec扩容及重组输出仍须计数。

## 各路径复制预算

| 路径 | 允许的必要复制 | 禁止的复制 |
|---|---|---|
| Linux正常off TX | TUN进入owned slab；原地seal；header用iovec或预留headroom | LINK→record→pending连续clone |
| Windows正常off TX | Wintun临时数据到owned slab；Npcap需连续sendqueue时再组装 | 为repair再复制整密文 |
| Normal FEC TX | source保留明文供parity，独立密文输出 | 同block多次保留同一明文 |
| Game TX | 一份逻辑frame/shard；每lane一份独立密文 | 每lane重复fragment、FEC编码 |
| RX | capture临时数据到owned；原地open；交TUN必需拷贝 | decoder借驱动buffer3秒，跨模块再clone |

读同一密文计算HP、AEAD、checksum属于读取成本，不装成“零字节成本”。冻结的是record字节；TCP/IP header独立scratch可以重写ACK等字段。若platform同步send已复制，返回后无kernel引用；若以后异步发送，completion前必须保留lease，不能沿用同步free时机。

## 预算与淘汰顺序

endpoint高吞吐初始总上限512MiB，含shadow/FEC/fragment/ready queues/metadata，driver内核buffer另报。低内存档减小总量并明确恢复覆盖。shadow单方向软上限128MiB，显式容量档256MiB；这些从总量中划分，**不是每client/lane各领一份**。

预算登记只在批量申请/释放时更新owner本地计数，跨owner按预先授予quota分片，不每包争用全局atomic。某owner需要扩quota通过低频控制申请；不可临时越过全局上限再补账。

高吞吐512MiB档初分TX224/RX224/未授予弹性64MiB，全部按需提交。TX的128MiB shadow包含自身元数据，余量供encoder、ready和bootstrap；RX的heavy默认上限160MiB、compact/dedup16MiB、fragment8MiB，余量供收包/业务出口及元数据。子项满只触发该类pressure，不能凭子上限把owner总额超支；实际Rust布局导致余量不足时R0调账并给size证据。小内存档按相同比例缩放并限制admission，不能把完整512MiB暗中乘以client数。弹性quota是慢控制消息，不是每次分配找全局锁。

pressure优先回收到期state→无用repair→最旧shadow→旧incomplete FEC heavy转compact→拒绝新的超额repair/large reassembly。新的普通payload保有很小独立reserve，control保有更小reserve；两者也有总上限。持续超载最终仍会丢新包，必须计数，不许为保存重传而无限堆fresh。

队列按 `ceil(observed_PPS × 2ms)` 估计正常待服务容量，最低64、上限8192槽；另限bytes和最老age。2ms是容量估计不是必须等待时间。满时丢新到项并计原因，不从SPSC生产者端覆盖旧项。严禁把128MiB shadow上限直接变成128MiB fresh排队。

这个公式用于容量规划/诊断，不是每2s重建一次SPSC。创建时有已知负载档则按预算PPS取值，否则初始1024槽；固定队列只在受控quiesce重配时替换。观测PPS超出设计量优先报告age/drop和调整下次配置，不在热路径动态搬迁整个队列。回收队列容量另按最大借出handle数规划，不能套普通fresh的1024上限。

## Shadow空间细化

hot ShadowEntry预算64B：pn、seq_offset、first_sent、last_sent、hard_expiry、BufferKey各8B，共48B；wire_len/flags/timer_index/retry_epoch各4B，共16B。TimerNode预算24B：deadline8B，prev/next/entry_slot/entry_generation各4B。另留索引/对齐余量，总模型用**96B/slot**，实际布局和额外表单独测；不写`repr(packed)`冒未对齐读风险。

shadow以PN低位直索引、完整PN+generation验证；PN包括control/失败预留，所以容量观测必须按PN推进速率加裕量，不只数成功data。碰撞时淘汰旧repair shadow，不阻止新发。需要扩N时采用至多两代ring：新发写新ring，ACK先查新再查旧，旧ring在原Tcache内排空后释放；最多一次迁移在途，不全表搬包，不反复生成第三代ring。扩容无总预算则保持当前覆盖并报告pressure。

## 必测反例

同槽复用/旧completion、Drop与stop、满return队列、部分send失败、clone后提前free、FEC持明文时seal覆盖、opaque key跨arena误用、pool allocation失败、128→256容量切换、清理后在用bytes归零。稳定负载热身后Normal/off allocator增量应接近零；若不是，列明确慢路径及次数，不靠RSS未增长宣称无分配。

参考：[slotmap的generational key思想](https://docs.rs/slotmap/latest/slotmap/)。借身份防复用原则，不给每一字节buffer再套多层通用map。
