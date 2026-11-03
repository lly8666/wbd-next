# PLAN028 H1037 — 同一 443 的多组 Game2/4 原 Go TLS 入场

### 根因及修复

1. 服务端 `--auto-ip` 属于非法客户端专用参数；真正的自动客户端租约启用条件是服务端 `--lease-pool`。H1036 的 Game 共享 reader 分支误看 `c.autoIP`，因此自动租约服务端未真正启用 Rust 唯一 TUN reader。本次修正。
2. Game 原服务端只接收 `n=2/4` 个 SYN 并建一个组，客户端交错到达时无法保证组成员属于同一设备。改成**每条原 FakeTCP 关联并行运行原 Go TLS 认证**，随后按 TLS 保护完成后的 `principal+TunnelID+Epoch+lane count` 组合分组；只有 lane1..n 各一且完整通过组内 keys/incarnation/policy 验证后，才允许真实 Rust GameAdapter/M4。
3. 不完整候选按 45s 冷期限回收，重复 lane 及组身份不匹配 fail closed；不同账号/设备的独立群组互不误拒绝。相同逻辑会话的继任代在真正 M4 Ready 后才精确 Stop 老代，不得用 SYN、NAT IP 或局部 TCP 端口作为认证权限。
4. 只为 `--lease-pool` 的服务端启用共享物理 reader；一个 OS TUN fd，按可信 `AUTO /32` 分入每组固定 64/8 包有界路由，Rust 原生 Game2/4 的 AEAD、PN、FEC、M4、raw 各自保持。单个组 Close 不关闭另一个组所用的 TUN，顶层最后关 reader。手动单组仍走旧的专用路径。
5. 同一 Go AF_PACKET 监听端口使用一个 union `SO_ATTACH_FILTER`，仅排除已由原 TLS 认证并成功启动 native M4 的具体 TCP DATA；新 SYN 与其他候选继续交给原 Go，避免把之前设备密文重新交给 Go 热路径。

### 硬边界

Rust `MAX_SESSIONS=16` 是总 native lane 资源，不宣称 32 个在线 Game 客户端；新的 Game2 双客户端只需 4 lane。Game2 / Game4 原 wire/FEC/Health 策略不改；新群组未通过真正 native smoke 前**只算 source candidate**。Game group Health90 服务端主动退休、真实 Game4 FEC 双组和 Windows 物理切网仍需后续单独验证。

### 最小测试

原 Go 两个独立 Game2 TLS cohort 元信息纯单测、原 Go Game2/4 单组 TLS/native 回归；新增 3-netns 原生两个账户/两个自动 `/32`，在服务器 443 同时收发真实 UDP，客户端 A Stop 后 B 继续可用，最后核实两个组与唯一共享 Rust TUN 完整 Stop。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1037 server --lease-pool activates Rust Game shared TUN, independent original Go TLS per 443 flow cohort keyed only by authenticated account/installation/epoch/lane, multiple Game2/4 groups with exact native Stop."}
```
