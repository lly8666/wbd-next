# PLAN029 H1846｜Direct RX 32条量子后不等丢失的auto-reset事件

- H1839 真 Windows/WSL2 签名 SOURCE a50f8c5 的 TCP 双向极慢且回程未全结束，未能观察到每次邮箱占用峰值；当前无法断定全部慢传皆由这处问题造成。H1843已修另一个确定漏洞：同一Direct TCP邮箱/Wintun写环满时丢已NAT的TCP段；其真实同源P2由H1844 [Action43598740573](https://github.com/lly8666/wbd-next/actions/runs/43598740573) 独立在测，不能用H1846修改后的SOURCE冒充H1844结果。
- 更直接的**已有确定调度缺陷**：`v4_windows_native_runtime.rs` RX每次从`sync_channel(256)`最多取`RX_WAKE_BATCH=32`项，之后无论是否取满直接`wait_ready([stop,npf,auto-reset direct/early_notify], u32::MAX)`。auto-reset Windows Event 不累计计数；多个`SetEvent`可能合并，只唤醒一次。若队列剩有第33条Direct TCP ACK/DATA且上游未再enqueue，RX可能进入无限等待，进而诱发TCP窗口停滞。这是真正`bounded fairness->park with backlog`的结构bug，区别于旧10ms TX轮询已计入TCP的误判。
- H1846限定原RX线程修复：记录此轮已处理的**真实包数**（含前一轮保留的单个TCP包），如果实际满32条且没有继续背压，原`wait_ready`这一次用**0毫秒**，先给真实Stop/NPF事件公平机会，随后进入下一有界邮箱量子；如果下轮邮箱已空则恢复`u32::MAX`无限事件等待。若真Wintun ring满仍沿用原5ms仅背压重试。纯函数单元测试同时证明0、31、32项与真实背压的超时区别以及空闲回归。无新thread、无第二Wintun reader/writer、无每连接/每包时钟，TCP有序与UDP原语义不变。
- 此SOURCE提交刻意**不带**`[plan029-v3-real-p2-rebuild]`，避免与H1844同场重复派发P2；普通源变更自动跑现有Windows/Linux Rust/Go回归，不把编译成功称为实网性能通过。正式产品`--split-enable`独立由H1845 [Action43599087343](https://github.com/lly8666/wbd-next/actions/runs/43599087343) 在 SOURCE7e1d继续实测。后续新SOURCE P2需要真实独立评估H1843与H1846的组合，不可跨SOURCE拼接。
- Game4 CN、IPv6旧WFP收口、GUI真按钮Connect Stop、慢磁盘FakeIP日志压力、P1 CPU归因和本轮P2完整性能门仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Fix Direct RX bounded mailbox quantum auto-reset notification coalescing: nonblocking recheck only after full 32 entries, with no idle polling and explicit unit regression."}
```
