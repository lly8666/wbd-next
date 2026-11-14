# PLAN029 H1829｜FakeIP磁盘IO与Rust共享TX隔离，原子压缩候选

- **中断/在途**：H1828 SOURCE`ec16ff8773344d5bbba639f8d6ffbae3dd95ea12` Windows/Linux原生库与计划资源pure两架构、governance/feature、native-functional均PASS（只是组件），原M0-WIN-LINUX无P2场景仍在途；不重复dispatch历史H1823/H1825/P2。H1825签名物理296ms/Direct6360ms与120/120 Tunnel UDP/Stop PASS_SCOPED，慢TCP和P1 +7.42%入口A/B仍OPEN。
- **首个已证实的代码结构**：原`v4_windows_native_dns_direct::DirectDns::resolved`及`v4_windows_native_dns_client_tcp::persist_and_synthesize`在原Rust TX处理普通业务同一线程调用`FakeJournal::persist_batch`，同步`File::write_all+sync_data`，磁盘抖动能阻塞其他flow的调度；这不是已经证明的1MiB TCP慢原因。
- **本批实现**：`FakeJournal::open_async`在CN cold owner开启唯一writer，默认阻塞recv不忙轮询；8任务上界及512KiB append字节队列，精确带ticket和full identity snapshot，writer只追加→sync→回执，原Rust TX每轮最多消费8结果，只有回执确认且pool仍是同一key/TTL/revision才`acknowledge_durable`。CN UDP53 `DirectDns.awaiting`和TCP53 `Phase::Durable`仅挂起自身DNS答复，5s deadline/失败局部SERVFAIL，不走备用DNS、不发布未持久化Synthetic A；Tunnel/P2/其他Direct TCP/UDP无持锁等待磁盘。
- **长期压缩候选**：现有16MiB WAL在12MiB历史高水位进入低频（至少60s）快照，`durable_candidate`完整覆盖活跃/TTL/隔离期，**若任何pending renewal则不缩写旧durable身份**。同一writer将完整镜像写入当前portable目录独立`create_new` temp，先CRC/全记录一致性校验并`sync_all`，释放旧fd后同目录`rename`原子替换再打开append；失败保留旧文件，不删未知owned之外资源，日志不足时仅相关新CN失败。压缩只在coarse tick，禁止逐包全表扫描。旧同步`open/persist_batch`保留纯journal fixture，正式CN接线使用`open_async`。
- **纯单测新增**：真实fsync前不能发布FakeIP、writer回执后才能从pool取得、重开文件映射一致；多次续期后压缩只留最新映射并保留至少10分钟隔离。新源码CI/签名DNS真业务、崩溃中间态、磁盘延时下Tunnel p99与Stop均**NOT_RUN**，不可把blob/设计当作通过。Writer `Drop::join` 在极端不可取消OS fsync时仍可能等待，必须在实际Stop/断电路径测并判断是否引入后台隔离回收；不凭纯单测宣称无全局HOL。P1/Game4/GUI/IPv6和Direct长TCP仍OPEN。
- 没有新WFP/大route、Go包热泵、逐flow IO线程、TCP协议栈或改变外层TLS/FEC/MTU。保留任何旧FAIL，当前PLAN029仍IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Existing CN FakeIP durable-before-answer behavior unchanged; implementation isolates blocking fsync to one bounded per-owner writer and adds cold journal compaction without introducing user-facing config, route, GUI, wire protocol or platform entitlement. Real native validation pending."}
```
