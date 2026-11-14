# PLAN029 H1828｜按驻留容量约束Direct TCP；不覆盖H1827施工

- HEAD `e96d99d9c1c0bc6530310fc76c47021a39a6e76e` H1827已补Direct-only Wintun进展计数、NativeTcp actor进展反馈、贯穿TCP全程的UDP与分段计时夹具，并更新029计划/M0启动提示；本批保留它们，不重复写同一功能/派发旧场景。H1825 Action43578369480物理296ms对Direct6360ms、真半关闭、120/120 Tunnel UDP与owned Stop仅功能PASS，性能仍OPEN。
- **新增本批单点代码**：`TcpDirectRelay`暴露真实`VecDeque.capacity()`和闲时释放，两方向新读仅在已分配空闲空间或全局驻留容量预算足以增长时入队；NativeTcpActor保留`buffered_bytes`实际待发长度和`resident_bytes`真实容量双账，8MiB Direct TCP子池满时仅该flow背压；低频500ms空闲且queue为空才收缩，避免每write`shrink_to_fit`抖CPU；平台allocator超限只结束相关Direct并释放账本，不挡Tunnel或其他flow。容量测试保留空闲后仍驻留→释放的单测。理论16k×双64KiB≈2GiB为旧账本风险，不是已测RSS；整个64MiB全分配上限和实际内核占用仍需源锁压力验证。
- **治理恢复**：H1827第一次Governance STRUCTURE失败因combined热文件32995>32768字节，其他人后续精确修订START_HERE至32759；本批M0.md仅缩写旧028 H1625历史快照并保留原证据，为H1828 cursor留热字节预算。不得用治理绿冒充真网验收。
- **仍OPEN**：FakeIP现有`persist_batch.write_all+sync_data`仍同步在TX，必须后续移到有界单writer，DNS只有相关新Synthetic A等durable ACK；16MiB WAL需低频快照压缩、隔离期/引用保护及崩溃恢复；Windows Direct共享事件完成通知/完整RSS/queue age/P1 CPU因果、Game4 CN、GUI、IPv6仍未完成。H1828新SOURCE Windows/LINUX编译及签名场景暂时全部**NOT_RUN**，先收已在途Action不重复dispatch。

```feature-impact
{"kind":"none","ids":[],"reason":"Only Rust Direct TCP retained allocation accounting/idle reclaim and compaction of old 028 M0 prompt; no new public setting, protocol, route policy or GUI behavior."}
```
