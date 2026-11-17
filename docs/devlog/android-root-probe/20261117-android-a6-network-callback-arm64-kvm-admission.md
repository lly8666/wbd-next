# Android A6：选定物理 Network 事件监控、Root Stop 世代防护、ARM64 KVM 准入

日期：2026-11-17。基线 SOURCE `7c557d0bcd8a6255620c0025a810322ad3ceef0a`；仅 `experiment/android-temp-root-probe`，用户授权 Actions-first 软件施工；main/M0 和实体设备均不动。

## 本次施工

1. 正式 `RootClientService` 移除每秒 `Handler.postDelayed` 物理网络轮询。使用 `registerNetworkCallback` 观察所有满足 INTERNET 的 Network，仅实际选中的 handle 发生 `onLost`、`onBlockedStatusChanged`、能力变化或 `LinkProperties` 精确物理身份/IP/MTU变化才请求 owner Stop。不因其他网络、默认网络切换而错误改选出口。回调本身不调用同步 `ConnectivityManager.getLinkProperties/getNetworkCapabilities`，使用 Android 直接派发的状态快照；Service 与 worker 退出均注销。原 Rust M4 物理 scope/readback 保持独立。
2. 新纯 Java `NetworkScopeGate` 记录会话 handle 与注销状态，`NetworkScopeGateTest` 覆盖零handle拒绝、选中/非选中 loss/link/cap/blocked、过期generation失效、同handle新会话；Job 中 `javac/java` 运行，静态检查无 `postDelayed`。这个测试不是实机/guest Android 网络行为 PASS。
3. Root 启动/停止：每次冷启动生成随机128bit token，写入 Root-only `owner.pid` 的第三字段；用户 Stop/网络损失先设置停止意图，阻止还未执行的 `su` 入口；已启动则仅发一次信号，Stop 侧最多12秒等待 PID 文件出现，必须校验 token+PID 内核starttime+原Go可执行路径才允许 SIGTERM。不能误杀旧会话；成功 signal 仍不是原Go/Rust join证明。仍无逐包Java/JNI、无新协议、无VPN。
4. 旧 macOS ARM64 AOSP guest [Action44042235770](https://github.com/lly8666/wbd-next/actions/runs/44042235770) 的 QEMU hang/ADB无设备历史保留。新 `arm64-cuttlefish-host-admission` 在 `ubuntu-24.04-arm` 检查真实主机 ARM64、`/dev/kvm` 可读写，绑定同一SOURCE APK/哈希后保存机器可读的 `ENV_BLOCKED` 准入票据：**Cuttlefish镜像与匹配host tools没有被部署**，即便有KVM也不假称 guest已启动；不再重复十分钟失败的 macOS 模拟器。

## 验收分层

Java状态门、Android Native Go/Rust构建、签名APK、原Linux server oracle和KVM host预检依各 Job 的实际结论登记；需查同源 Actions 结果才能升级。P2 Android16 ARM64 guest 真实Bionic装载/物理Network/TUN/RAW/原Go TLS与Linux server真业务、P3正式普通App→su、真实网络变化及Stop设备行为、最终KSU实体手机/热点/功耗均 **NOT_RUN**。不把KVM host job绿色图标当 Android E2E PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A6正式Root App物理Network事件回调替代1秒轮询，精确token/PID/starttime Stop，Java状态门，ARM64主机KVM预检替代挂死的macOS AVD；保留设备P2/P3 NOT_RUN。"}
```
