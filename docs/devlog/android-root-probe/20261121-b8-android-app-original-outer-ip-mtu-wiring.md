# B8｜Android App 外层 IPv4 MTU 接入原 Go/Rust（软件优先）

## 真实缺口与原生产接线

SOURCE `096b2c23563267351352b276cc8ea6bc03a3a67b` 原 Go 已提供 `--outer-mtu`（完整外层 IPv4 IP 包），原 Rust 有唯一 MTU budget、认证后的 TUN MTU 自动应用与读回；但 Android Root App 生产 argv 一直硬编码1460，用户无法按物理网络实际情况选外层预算。A48 旧真机曾有原 M3 `auth=1227`、反向 TUN `rtun=1218`，并非本 SOURCE 或本次性能证据。

- Activity 增加外层完整 IPv4 IP MTU 数字输入（576..1500，默认1460）。`START.outer_mtu` → Service（旧 Intent 默认1460）→ 同代 Root owner → 真实 `OriginalGoCommandArgs.build(...,requestedOuterMTU)` → Go `--outer-mtu` → Rust 原预算、TUN MTU 和内核读回。
- 旧 Java argv 方法重载继续默认1460，不新增 JNI、数据面 worker/packet copy、TLS安全检查、路由规则或协议格式。原物理路径、MSS/record 上限继续取实际最小；若内层预算不足产品最小576，沿用已有错误，不悄悄截断。
- 同一 Host JVM 测 576/1460/1500、575/1501 拒绝；原签名APK源码门锁定 App→Service→Go→现有 Rust预算。真实 Android 网络、吞吐和 Stop 为 NOT_RUN/NOT_PROVEN，本次只请求同 SOURCE 软件 CI。

## 已审计但未能通过打开开关来完成的功能

1. **Fixed/Auto/FEC2**：Android Rust M4 目前只有 Normal/off，主线 FEC2 M1 systematic/repair、M3 unique PN 与M4恢复、档位和 MTU 需接进原 Android 唯一 owner，不能只开放 Go/UI `--mode`。
2. **Game2/4**：缺真正多条 TLS/FakeTCP lane 的 Android Go 生命周期与 Rust Game RX/TX、ACK、Stop；一条 Normal 不能冒充四条 lane。
3. **DNS**：B6 普通 TCP53 仅原 M3 隧道透传，系统 Resolver/netd 仍未拦截；物理 TCP53、CN非DNS IP direct、IPv6/热点都需要各自真实包路径，不从 CN8503 UDP QNAME 路由外推完成。
4. **切网**：目前 NetworkCallback 只停止旧同代连接；切换新真实 Network 的完整重认证/租约/物理 socket/UID owner 重建是独立产品接线。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B8原Activity/Service/Go argv新增完整外层IPv4 IP MTU用户输入576..1500/默认1460，复用原Rust预算和TUN自动配置，Host源码门覆盖；Android真机与高级模式仍未证明。"}
```
