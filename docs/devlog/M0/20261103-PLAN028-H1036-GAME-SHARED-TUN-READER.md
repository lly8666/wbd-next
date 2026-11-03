# H1036 PLAN028 — Game 共享唯一 Linux TUN reader

根因：每个原生 GameKernelOwner 独立 read_ready_batch 同一 TUN；如果直接接入两个 Game 组，一个组可窃读另一组目标 IPv4 的业务包。复制 Go fd 不是独立广播流。

本增量在原 Rust Game2/4 M4 上复用已存在的全进程单 TUN reader：只有原 Go TLS 认证、服务端 AUTO 租约 /32 且原生 Game 组完整 join 后才绑定；真实 M4 成功启动才发布 route，原 GameAdapter 保留 AEAD/PN/FEC 和真实 raw/M4 worker。TX 从每组有界非阻塞队列读取，不再调用 TUN reader。无可信 lease 的手动单组保留原行为。

精确 Stop：A 旧组退出先撤销自己的 alive/generation route，不移除 A2 新代和独立 B；A2 一经生效旧 A 的 TX 不再消费缓存包，较低 generation 的迟到发布也不能覆盖新代 /32；整个物理 TUN 由 Go 顶层持有，原生共享 reader 在各组 Stop 后才 Close。

**未完成**：Go 服务端目前仍只收一个 Game 组，尚未实现同端口同时多个 Game 组的认证分桶和并存。H1036 是必要的底层隔离，不冒充真实双 Game 组可用。

测试：Rust A/B/A2 同 reader 路由绑定/回收单测、新 C ABI 导出、原 Go Game2/4 TLS/Rust M4/UDP 原生回归。真实 concurrent Game 多组仍 NOT_RUN。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1036 Game AUTO protected /32 uses one Rust TUN reader across group generations, per-client queue route and exact Stop fencing; Go single-port Game multi-group still open."}
```
