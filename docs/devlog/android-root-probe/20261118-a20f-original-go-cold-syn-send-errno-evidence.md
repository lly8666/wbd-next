# A20f：原 Android Go RAW 就绪后早退；新增原 SYN 发送 errno 只读类别（2026-11-18）

**真实 SOURCE `fa5f070ea48bac80e69213a0c5f3b9123eacbe4d`**：[Actions #44253521779](https://github.com/lly8666/wbd-next/actions/runs/44253521779) **整体 SUCCESS**；D0 双 ABI、ARM64 正式 APK、D1 KSU App Root 与真实 Android `PhysicalNetwork`、D2-S0 原 Linux server/client/Rust、D2-S1 双侧原 Go 内核 TUN/RAW 均真实 PASS。此次把原 Go RAW 里程碑后的观测延长为 45s；官方 Job 日志却出现 `D2_S1_ORIGINAL_GO_EARLY_EXIT_BEFORE_AUTH_HANDSHAKE`，且 `D2_S1_ANDROID_SYNACK_NOT_PROVEN`、`D2_S1_ANDROID_ORIGINAL_AUTH_LEASE_NOT_PROVEN`。按已确认的原生时序，**Go 在 AF_PACKET RAW 创建后仅约 1 秒就非零退出，尚不足以推论是 QEMU NAT 拦截，必须先区分原初始 SYN 是否通过 syscall.Sendto**。正式 `RootClientService` 不记录原 Go 原始 stdout，原因目前不明；因此绝不将 TLS/M4/Stop 标 PASS。

本次最小化源锁源码改动**只提供可验证诊断，不改数据面**：在原 Go `runClient` 原 `ClientAssociation.Start` 第一次 SYN 写入后/出错时，`runtime.GOOS=="android"` 才打印固定 `V4_PUBLIC_ANDROID_COLD_SYN_TX_OK role=client source=original_go_raw` 或 `V4_PUBLIC_ANDROID_COLD_SYN_TX_FAILED role=client class=<enum>`。类别只包括 `permission_denied / network_unreachable / invalid_argument / source_unavailable / buffer_pressure / other`，基于原 syscall errno 的 `errors.Is`，无 IP、账号、UID、句柄、密钥、TCP bytes、errno 文本或 TLS transcript。**原 syscall 发送、SYN 组包、RTO/重试、TLS、原 Rust AEAD/PN/M3/M4、Go return err 均不改变。** 实际 Linux oracle 行为不变。正式 Java `RootClientService` 仍只通过 `OriginalGoMilestones.matches` anchored 原始日志产生 `RootDiagnosticReceipt` 固定枚举，不输出用户数据；新增 host spoof/前缀拒绝测试，D2-S1 的 SOURCE-locked receipt 新字段 `original_android_cold_syn_send` 只有确切原 Go 证据才 PASS 或特定 FAIL。

**新 SOURCE CI 尚无结果**；在下一轮看到 `SYN_TX` 类别前，禁止盲改模拟器/Android 路由，`SYNACK/TLS/32/真实 M4 TCP+UDP/Stop` 仍 NOT_PROVEN/NOT_RUN，系统 DNS 双冷许可保持 false。仅实验分支 PR #36 Draft；main/M0、ARM64 正式发行和来源固定数据平面不变。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A20f 同源真 Android Go RAW 后约1s非零退出，未知 SYN send 失败原因；仅加 Android 原 ClientAssociation.Start 成功/errno 分类固定日志与正式 RootClientService 的安全枚举、host 防伪校验，不修改原 SYN/TLS/AEAD/M4/路由/Stop，D2握手仍 NOT_PROVEN。"}
```
