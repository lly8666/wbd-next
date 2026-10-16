# 02 owner、调度、唤醒与时间

## 线程与数据流

默认每个endpoint一个TX owner、一个RX owner；服务器多client共享这对线程。只有证明单owner饱和而宿主有余量，才增加成按TunnelKey稳定hash的多对owner，不能每lane开一对。Linux fd用非阻塞poll；Windows若capture库不能可靠非阻塞，增加每设备一个RX reader，只负责有界复制和投递，不能在reader中FEC解码。

落实检查：[M0热路径补充方案](../../decisions/M0-hotpath-cost-first-2026-10-16.md) 第4节。多个线程若仍持同一registry/owner mutex执行逐包工作，不算方向所有权拆分；registry只做安装/查询/关闭协调。实际循环复用batch存储，普通计量不能每轮调用线程CPU时钟。已就绪批量自然可为1，不等待凑数。

TX拥有seq/PN、encoder、shadow、repair budget、发送队列；RX拥有AEAD opener、received bitmap、decoder/reassembler、业务出口。两个方向的状态绝不由一把Lane mutex串行。跨方向只发receipt/载荷活动/外观ACK快照，队列单向有界。

跨线程SPSC采用 **rtrb**，不自写unsafe无锁环。预分配固定容量，push满返回原事件；不得覆盖consumer正在读的值。批量接口仅处理已有事件。控制入口串行，避免把SPSC硬当MPSC。`Arc`只用于创建队列和共享不可变资源，不能每层每包额外clone。

## 固定事件循环

每轮依次：stop/config≤8项 → 到期任务≤32项 → driver ready≤32包 → fresh/repair调度≤32包 → 完成与释放≤64项 → stats快照（到期才做）。总CPU片段达到约100µs时回到循环顶检查其他类；时钟读每8包一次而非每个小操作一次。某类仍有积压则本轮不sleep，但下轮必须轮换起始类，避免一直只做RX或timer。

同owner多个tunnel采用按**实际wire字节**的deficit round robin，起始quantum=4×outerMTU、deficit最多8quantum；只维护非空tunnel链。每tunnel的fresh/repair使用10:1字节权重，control每轮小独立预算且受总输出限制。单lane慢/不可写不占住列表头，跳到下一个ready lane。无每包排序或遍历所有idle tunnel。

首版不做优先级插件框架，不做每packet async task；deadline已到的稀疏包在下一轮立即处理，绝不等batch攒满。32包/100µs是公平调度初值；同包率微调须说明每轮服务延迟与syscall成本的变化。

## 不漏唤醒协议

queue由rtrb提供内存安全，睡眠另用owner共享`armed:AtomicBool`和OS event。消费者：排空ready→`armed.store(true,SeqCst)`→**再次检查所有输入及stop/next deadline**→有活则armed=false并继续，否则wait。生产者：先push发布事件，再`armed.swap(false,SeqCst)`，原值true则signal。不能只依据自己看到的“队列从空变非空”。

Linux用eventfd/mio Waker，Windows用独立auto-reset event并把Wintun事件/stop一起等待；不手动ResetEvent抹掉刚发生的signal。唤醒是提示，醒后重新读队列；允许多余一次唤醒，禁止遗漏一次。任何回收/stop队列也走同协议。shutdown时保证consumer还活着直到producer撤销。

## 时钟和定时器

借鉴Tokio分层wheel思想，但**不复制其unsafe链表**。owner本地3层×64桶，粒度1ms/64ms/4096ms，覆盖约262s；更久的rotation/idle/lease由Go冷层管理。TimerNode用arena索引prev/next实现O(1)unlink；节点持绝对deadline和owner generation，桶只是索引，触发前再比较绝对时间，不能提前触发。

每个shadow最多一个节点（min下一repair机会/硬过期），block/fragment各一个节点；重调度先unlink旧节点，不在heap无限积累stale entries。空桶有64bit占用位图，跳到下一非空桶；长暂停按占用桶推进，禁止for每毫秒追赶80秒。

到期积压每轮最多处理32项；同时硬资源allocator可主动淘汰已过期对象，不能因为timer backlog突破内存。记录timer_lag与work_budget_yield。先保证真实业务首到，再清理无用历史；owner中任何锁/睡眠/系统调用必须注明最坏阻塞边界。

## 测试与来源

R0/R1在Actions用Loom为“入队/armed/睡眠/stop”枚举关键交错；普通随机压力仅作补充。定向测空闲后单包、不停RX时TX/stop仍响应、10万同deadline、时钟跳80秒、满回收队列、慢lane、多个client公平性。单测用fake clock，禁止真实sleep堆测试时长。

参考：[rtrb](https://docs.rs/rtrb/latest/rtrb/)、[Mio Waker](https://docs.rs/mio/latest/mio/struct.Waker.html)、[Tokio timing wheel](https://github.com/tokio-rs/tokio/blob/master/tokio/src/runtime/time/wheel/mod.rs)、[Loom](https://docs.rs/loom/latest/loom/)。只借有界owner/timer方法，不把Tokio完整调度器搬进逐包路径。
