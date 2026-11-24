# A17：x86 Android KSU 原客户端原生启动准入（2026-11-18）

在 A16 **同一 Go/Rust Android Bionic 双 ABI** 构建上，增加 CI-only 的 x86_64 Android 签名 APK 装配脚本及 Actions KSU 单一模拟器作业。x86 APK 仅携带原 x86 Go ELF/Rust M4 .so + exact SOURCE/SHA + CN8503；正式 ARM64 APK 保留原 debug helper 和 ARM64-only 发行，**不混入 x86 二进制**。同一 Java NativePayload 根据已签名的单一 ABI 资产和系统 SUPPORTED_64_BIT_ABIS 严格验签，RootClientService 仍经真正 `su -c` 启动原 Go，RootStopCommand 仍以准确的原生 ELF 路径、PID、kernel starttime 和 generation 发 SIGTERM。新增 JVM Stop 双 ISA 验证。

新增 Actions `android-x86-kvm-ksu-original-native` 使用历史成功的 Ubuntu x86 KVM/Android16/KernelSU3.3.1 镜像、同一 Action 的 Go/Rust 与 pinned CN artifacts，构建内部测试 APK、安装到真实模拟器、启动 Activity、核验源锁后，从相同签名 APK 资产 staging 的**原生 x86_64 Go ELF** 经真实 KSU shell `su` 执行 `--help`，生成严格真实 receipt。**此作业目前只自动证明原生 ELF/KSU shell/Activity 部分，不假称普通 App→su 已授权，也不假称原客户端 TLS/认证租约/M3/M4 TCP/UDP/Stop。** D1 的普通 App→su 及 D2/D3 仍 NOT_RUN，不得凭 D0/D1 partial 升格；不存在伪造服务器/协议、独立 Java/Go packet pump 或新 JNI 功能。

本批提交前的已验证事实：[A16c Action44230920834](https://github.com/lly8666/wbd-next/actions/runs/44230920834) ARM64+x86 原 Go/Rust Bionic 源码编译链接执行完成，但 manifest x86 ELF 校验逻辑 FAIL；修复后完整 D0 Action 结果应独立另核。新 KSU job 同样等真实 Actions 执行后才更新结果。原系统 DNS 接管两道冷门仍 false，main/M0/真机不变。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A17 新增正式 Java 控制器/原 Go-Rust 的 x86_64 Android CI-only 签名 APK 严格源锁、真实 x86 KSU 原 Go ELF help/Activity 准入 Action，保留 ARM64-only 发布和两架构精确 Stop；不虚报 App→su/TLS/M4。"}
```
