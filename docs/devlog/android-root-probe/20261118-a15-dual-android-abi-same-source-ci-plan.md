# A15: Android x86_64 同源码 CI + ARM64 发行护栏（2026-11-18）

按用户最新决议调整正式项目施工方案：手机仍只发行 ARM64；x86_64 Android 为 CI-only 原生 Bionic 目标，共享原 Go TLS/auth/lease 和 Rust M1/M3/M4/Stop、共用 Java App 控制路径。门禁 D0 双 ABI 编译+FFI、D1 x86 Android16 KernelSU 普通 App→su、D2 同源码 Linux server TLS/auth/租约 + App UID 真实 TCP/UDP 双向、D3 原 Stop/route rollback；ARM64 每批 ABI/16KiB/ELF/签名和 Linux oracle 另验，真机最后验收。

已知 KSU x86 探针 Action43986417528 PASS 不等于 WBD 真业务；A14 Action44222441113 ARM64 生成与 Linux oracle 部分 PASS，NativeBridge ARM64 ELF139 保留独立红门。用户 ARM64 最新自检 REAL_APP_UID_TO_TEMP_TUN_PACKET=PASS 是临时 UID-TUN 真包，没同时提供可核对的 SOURCE SHA，不能等同正式 TLS/M4。**本提交只改方案/功能卡；没有编译 x86 产品、运行新 Action 或操控实体设备**。x86 Android 原产品、正式 ARM64 TLS/M4/Stop、系统 DNS takeover 均 NOT_RUN；DNS 安全冷门保持 false。仅实验分支/PR #36 Draft，不动 main/M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A15 新增与 ARM64 正式客户端同源的 x86_64 Android CI 专用架构，明确 D0-D3 真 Android KSU/TLS/M4/TCP+UDP/Stop 门和 ARM64 16KiB/ABI/并发护栏；仅方案和功能卡修改，业务保持 NOT_RUN。"}
```
