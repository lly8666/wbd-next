# PLAN029 H2057｜真实测试子进程 abort 后恢复 FakeIP 异步持久化（不是Wintun崩溃）

- 单源Rust `v4_client_fake_journal.rs`子进程在临时真实FS上打开`open_async`，为CN FakeIP排队、等原writer实际fsync完成并取得 durable ACK，输出唯一ACK标志，然后**直接`std::process::abort()`，无Drop/join或自然测试结束**。
- 父测试进程只在子进程非零崩溃退出且确认ACK标志后继续，从同一真实磁盘journal `FakeJournal::open`重建；检查实际映射的real IP/FAKE IP、TTL quarantine、原cn身份不变，新域新alias在durable前不能发布；不会借系统DNS或Tunnel替代。该测试同时在现有Windows2025/Linux Rust library CI内执行。
- **范围：REAL_PROCESS_ABORT_COMPONENT_TEST_PENDING，不是用户实际WinForms/Wintun+Windows路由WAL进程崩溃恢复PASS。** 原H2043 8异步任务+第9拒绝及独立Tunnel票组件证据不变。H2055真实GUI和H2056物理TC各自实网场景仍在途，绝不借此次纯测试promote。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add exact physical-file async FakeIP writer durable ACK followed by real child process abort and parent restart, scoped to process/component only."}
```
