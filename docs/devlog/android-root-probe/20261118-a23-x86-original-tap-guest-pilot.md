# A23｜x86 Android16/KSU 原核心 TAP guest 单场景试验（尚待真实 Actions 收据）

本次根据现行唯一计划优先处理 D2：`b926881b` 同源 D2-S1 真实原 Go SYN `sendto` 和原 Linux server 启动已经证明，但宿主普通 TCP SYN 不证明原服务端 AF_PACKET 合法 SYN RX，SYNACK / TLS / 认证 / /32 租约 / Rust M4 / App TCP+UDP / Stop 均 NOT_PROVEN。TAP host `#44264710804` 的 PASS 仅包含宿主 KVM、`-net-tap` 帮助和私有接口读回，不包含 guest。

本变更只添加一条 **限定为带 `[d2-tap-guest-pilot]` push commit 或显式 workflow_dispatch** 的独立 x86 Android16 KSU Job。共用该批源码锁定 ARM64 发布资产、x86 原 Go/Rust、原 Linux Server 构建和正式 Java RootService；用已有首轮 SLIRP KSU 安装流程，在第二次 guest boot 前创建仅由 Job 拥有的 `wbdtapci0`，私有 TAP `10.0.2.2/24`（与原 CI App 已固定的对端 IP 一致，**不更改 App 或伪造 ConnectivityManager Network**），检查主机子网冲突与真实 `-net-tap` 能力；真实 guest 第二次启动通过后，普通 App 必须从系统 `PhysicalNetwork.available/exact` 获取实际 handle/ifindex/IP/MTU，否则 `ENV_BLOCKED` 退出，不绕开绑定。仅当该门通过，原 D2 路径才将 Linux 原 server RAW 监听从 `lo/127.0.0.1` 切到 owned TAP/`10.0.2.2`，保留原 FakeTCP/TLS/凭据/租约/Rust/Stop、不改协议。宿主 AF_PACKET observer 按固定 TAP 地址只计 SYN/SYNACK/RST，原服务端双固定 RAW marker 继续按源码辨认；退出不论成功失败先有界 Stop 再删除**仅本 Job 创建**的 TAP，绝不动全局路由、DNS、SELinux 或用户物理设备。

**证据边界**：这是一轮尚未执行的新 CI 试验，不是 TAP guest、D2a RAW、D2b TLS 或 D2c M4 已经通过；该独立 Job 的 SUCCESS/FAIL 和工件按它自己的 SOURCE 与固定 enum 收据判定。系统 DNS 冷门仍 false；ARM64 仅发布目标，x86 仅诊断，不触碰 `main` / M0。不重跑旧 NativeBridge。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"新增唯一源锁x86/KSU真实TAP guest原Linux RAW握手诊断门：先核系统PhysicalNetwork，环境阻塞即终止，收据与owned清理独立于E2E。"}
```
