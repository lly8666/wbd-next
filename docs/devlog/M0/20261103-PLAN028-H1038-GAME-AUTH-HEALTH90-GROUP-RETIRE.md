# H1038 PLAN028 — 只回收失联的 Game 原生组

H1037 已经实证两个 Game2 自动租约组同端口、单 TUN reader 并行收发，A 客户端 Stop 后 B 不受影响；但停止的 A 在服务端可能一直持有两条 Rust native lane，直到服务端整体 Stop。这会令 16 lane 原生资源被旧组占满。

修复沿用 **Rust 原 GameKernelOwner 自己的 Health90 / RX fatal stop AtomicBool**，不增加探测包或第二个计时器。新的私有原生 FFI 只读取对应组 M4 的已存在健康状态；Go 服务端原本每秒运行的冷 maintenance ticker 看到本组 dead 时，按已认证 cohort key 调用该组原有 `Close`，先精确 native M4/owner Stop，再释放这组 /32、FakeTCP tuples 和 epoch 实例；不清空同一端口其他设备的 BPF union，不重启共享 TUN reader，不借用另一个租约。

同设备下一代 A2 仍依赖 H1036 Rust 单调 generation 路由栅栏，不能被旧 A 的晚 Stop 误撤销。新 FFI 导出、Go 构建、原 Game2/4 产品和 H1037 双组原生回归是当前小门槛。**真实等待 90s 的服务端 A 自动退休在获得明确证据前不宣称测过**。Game4 多独立组、Windows 真实切网等 PLAN028 项继续开放。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1038 exact authenticated Rust Game M4 Health90 stop readback lets same-port Go supervisor retire only dead Game cohort and its own native /32/flow/epoch without a new health timer, preserving siblings."}
```
