# A20｜原 Linux WBD server → Android x86 KernelSU 正式 RootService D2-S1（2026-11-18）

**已证实基线**：[SOURCE 4952442a Actions #44238444687](https://github.com/lly8666/wbd-next/actions/runs/44238444687) 全 workflow SUCCESS：D0 同源码 ARM64/x86 原 Go/Rust 原生 Bionic、ARM64 签名 APK、Android16 x86 普通 App→KSU Root、正式 PhysicalNetwork 精确读回、D2-S0 x86 原 Linux WBD server/client/Rust ELF 真实启动、Linux 原 TLS/M4 oracle。Android 正式业务 TLS/租约/M4 仍 NOT_RUN。

**实际新增的 CI 工程**：仅 CI-only x86 APK 编入 `X86CiOriginalStartActivity`，不进入 ARM64 APK。该 Activity 只对正式 `NativePayload.stage`、`PhysicalNetwork.available/exact`、`InstalledAppCatalog` 和 `SelectedAppGroup` 作相同来源与 UID 约束检查，使用真实普通 App UID 的 Intent 调用 **生产 `RootClientService.START/STOP`**。绝不自己实现 TLS、加密、TUN/RX/TX、JNI 或 packet pump。

新增独立 `android-x86-kvm-ksu-original-d2-s1` Actions Job：复用已验 x86 Android16 KSU App→su 和同 SHA 构建的原 Linux x86 WBD server/Rust，单 Runner 内真实启动服务端；路由密钥由原 `--init-route-key-file` 生成，测试账户密码、TLS cert/key 仅作业内临时生成、0600，不写到命令行、Intent、工件、日志或提交。私有文件以真实 App UID/0600 放入一次性 Android 模拟器沙箱；正式 `RootClientService` 启动原 Go Bionic/Rust M4，按原 Java 固定阶段事件严验真实内核 TUN 和 AF_PACKET RAW，独立记录 SYNACK/TLS 认证 /32 租约/M4+UID/Stop。

**验收红门**：D2-S1 最低只认实际生产 RootService 通过真 Go 原 TUN/RAW 到达预认证阶段；即使 Job 成功也不宣称 D2 TLS/租约/真实 TCP+UDP/Stop。原服务端在宿主 loopback，Android Emulator `10.0.2.2` NAT 未经证明可承载原 FakeTCP，若 SYNACK 不到则收据 NOT_PROVEN 并另行处理物理网络；不能为求通过放宽 Wi-Fi/蜂窝 Network、内核路由、VPN/DNS 或另写数据循环。所有敏感原始服务端日志在作业临时目录销毁，只上传固定枚举与 SHA。**本提交未运行新 D2 Job，不能预报 PASS。** DNS takeover 双冷许可 false，只有实验分支 Draft PR #36，main/M0/ARM64 发布不改。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20 新增同一 Actions x86 原 Linux server→真实 KSU Android 正式 RootService 的原 Go/Rust TUN/RAW D2-S1 准入；CI-only Java 仅调用正式控制器，阶段真实验收，TLS/M4双向/Stop/DNS 未运行不虚报。"}
```
