# A22：Android 执行方案与长期提示词去历史叠加（2026-11-18）

本次只做**文档与功能卡**治理，基线 `b926881b59581c073066d42f315b176f95e23c0b`；[Actions #44269992127](https://github.com/lly8666/wbd-next/actions/runs/44269992127) 整体 SUCCESS，13 成功 + 1 历史 NativeBridge 条件跳过。D1 x86 原生 Android16/KSU App→su/PhysicalNetwork/Go/Rust TUN RAW PASS；D2-S1 原 Linux server 实际启动、原 Go SYN sendto PASS，**原 server RAW SYN 接收、SYNACK 双端、TLS/认证/lease、Rust M4、真 App TCP/UDP、Stop E2E 未证实**。A21 all ordinary App IPv4 UID route 的 Java/Go host、ARM64 APK build PASS，不是 Android 设备内核全局路由 PASS。

问题：旧 `docs/plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md` 累加了 A3/0a/A15 多套互斥优先级，旧 `docs/prompts/ANDROID_TEMP_ROOT_PROBE.md` 最新下一步仍指向早已开发过的 B2c2b2，同时旧 Actions 列表掩盖当前 D2 网络预认证阻塞。

处理：把计划改为一份唯一现行路线（ARM64-only 发行、x86 CI-only 同源原生验证、先 D2 FakeTCP/TLS/M4/Stop、SLIRP/NAT 双端 RAW 证据与隔离 TAP guest 候选、后续 DNS/A21 全 App/性能）；长期提示词改为启动校验+唯一真实阻塞+明确安全/权限边界+证据交付格式。历史方案保留 Git commit 快照与原 devlog 链接；更新产品功能卡的摘要、限制和当前阶段验证条目。功能卡受仓库 16KiB 上限约束，将 A2 之前重复/旧阶段验证行归档到 [基线功能卡原文](https://github.com/lly8666/wbd-next/blob/b926881b59581c073066d42f315b176f95e23c0b/docs/features/entries/android-root-native-client.json)，保留 A2 后的 PASS/FAIL/NOT_RUN 及新 D2 行；这不是撤销旧失败证据。

**本次不是新的网络/ARM64 真机/协议运行结果，不能以文档变更将 D2 或全 App E2E 标成 PASS。** 实验分支 + Draft PR #36，main/M0 与 Go/Rust 产品代码均未改动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"清理 A3/0a/A15 与旧 B2 下一步叠加，把现行方案和长期接续提示词收敛到 D2 真 FakeTCP/TLS/租约/M4/Stop 单一关键路径、x86 CI-only ARM64 发布与 TAP/原生ARM64环境对照；同步功能卡不夸大验收。"}
```
