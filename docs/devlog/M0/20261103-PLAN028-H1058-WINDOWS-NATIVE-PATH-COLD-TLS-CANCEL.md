# PLAN028 H1058 — 原 Windows OS 网卡通知取消仍在途的旧 TLS

H1043 已实现真实 IP Helper IPv4 路由/地址通知和200ms静默/最长500ms合并（只对实际物理网卡ifindex或源IPv4改变发起新建链），但 `runM0NativeV4WindowsGeneration` 原来仅在 OS Applied 或 READY 后读取 `pathChanged`。因此 FakeTCP SYN / TLS 在途时切到新网卡，旧 TLS 可以阻塞至超时并作为普通初始失败让 CLI/GUI 退出，而不是及时发起新原 TLS。此处是冷控制责任缺口，**不是新恢复器或 Go 热泵**。

本次仅补在唯一 Windows supervisor 的原 generation 调用外一层 `m0WindowsRunPathScopedGeneration`：原有 native OS watcher 发出经过过滤的事件，本代发短 channel 信号并取消**本代 context**，待原 `runM0NativeV4WindowsGeneration` 中的旧 Rust/WAL 精确 Stop/Join 完成后，交还 `errM0WindowsPhysicalPathChanged`，由原 `generation++` 分支再次发现真实源接口/IP、重建 FakeTCP+TLS+预算及 OS Apply/readback。明确的错误密码 `ErrAdmissionAuth` 不得被改写为路径重试；父 context 用户 Stop 不能复活。事件合并时间不是 TLS 恢复 SLA。无新 TUN reader、逐包通知、密码算法、稳态 wire 或后台定时器。

同时加 Windows 原 Go 三个 cold unit：在途 TLS 取消／重认证信号、User Stop 不重建、认证拒绝不变。两份 Windows overlay 的原 `manifest-plan020-m0.json` pinned `result_blob` 更新至新源码。此提交**SOURCE 未测**；Windows 实际 NIC/IP 变化、重认证到业务首包、Game切网和CPU/p99仍需真实 Windows OS 场景。

H998 在线收窄 FAIL、旧 ARM64 Game4FEC Action FAIL、远端 ICMP 未测及 CPU 因果未证保持旧限定证据。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1058 native Win IPv4 event cancels pre-READY original TLS context, await exact Rust/WAL Stop before existing generation++ TLS reauth; targeted Go tests and assembly pin."}
```
