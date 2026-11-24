# Android Root 原生 WBD 客户端｜长期接续提示词（现行单一版）

**2026-11-24 最新用户决定：Android 高级 CN FakeIP = OUT_OF_SCOPE（明确不实现，不是待办）。** 保留普通 CN8503 域名 DNS 分流、真实 IPv4 CN 内核 FIB 直连、手工 CIDR；不引入合成 IP、FakeIP 映射、对应路由、UI/CLI 开关、代理数据路径或验收任务。按大类功能并行研读/合批接线，复用原 Go 冷控制及原 Rust 数据面；不展开极端工况、额外防御性安全开发或重复历史 SYN/TAP 探针。

## 1. 接续核查
只在 `experiment/android-temp-root-probe`、[Draft PR #36](https://github.com/lly8666/wbd-next/pull/36) 开发，不写 main/M0，不 reset/force。每次先查两边 HEAD、PR、最新 Actions 各 Job 与在途工作，审查可访问的未提交工作树，不重复 dispatch。读 AGENTS、章程、TLS/MTU 契约、[现行方案](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md)、[功能施工台账](../plans/ANDROID_ROOT_IMPLEMENTATION_BOARD.md)、[功能卡](../features/entries/android-root-native-client.json) 与最近 devlog；旧 SOURCE/旧提示仅历史证据。

## 2. 当前实际阶段与施工逻辑
历史 A48 SOURCE `4a19f20456e74f3e7700e3a2876eda40536bb8d9` ARM64 API36 原 Normal/off 已实证 SYN/SYNACK、标准 TLS（证书身份验证关闭）、认证、/32、UID、原 Rust M4 RAW/TUN 双向及 owned Stop，用户报告数据通了；应用层 TCP/UDP 独立逐字节与性能尚未验。A49/A50 删除重复 checksum/解析/poll；A54 已撤回额外 TLS/DNS 防御门。不要把旧 D2-S1/SYN/TAP 当当前阻塞。

B77–B79 七模式启动填充、Game4 复制策略、ARM64 ISA-L、CN IPv4 内核路由是最新软件施工批；先读取本 SOURCE CI，完成真实大类功能接线，独立模块可并行，合批冻结一次 SOURCE。剩余外层机会式重传应移植 main 当前真实成熟实现（Normal/Fixed/Auto 及 Game 原 M4、原密文与 ACK/SACK），不造新算法、不新增假开关，不为极端工况反复扩展测试。高级 CN FakeIP 不属于 Android 交付范围。

## 3. 原产品边界
Go 保留标准 TLS/认证、租约、OS/Root/Network 冷控制，Rust 唯一 TUN 与 RAW 长寿命 DATA；不引入 Java/Go 逐包转发、第二 TUN、重复检查、额外防御框架。原 M3 AEAD/PN、FEC 首交付去重、MTU/PMTU、generation 和 owned Stop 保留正常业务语义，证书验证沿 A54 用户选项；不自行加强。ARM64 唯一发布 ABI，x86_64 仅 CI 诊断，原生同源构建。真实设备/服务器另授权，默认不启动 KSU/TAP guest，不将 Linux oracle 或签名 APK 当 Android E2E。

## 4. 验收和交接
现有产品 CI 同源双 ABI、签名 ARM64 APK、原 Linux oracle、必要 Host 正常功能回归；按真实失败直接修复，不改写历史证据，不做海量极端测试。完成源码大类功能后再集中 ARM64 实机功能及同条件性能验收。每次短 devlog + 功能卡写明 SOURCE、分支、PR、实际修改、Action 各关键 Job、SYN/SYNACK/TLS/认证/租约/M4/Stop 真实阶段、FAIL/NOT_RUN/NOT_PROVEN 和唯一下一步。性能优先：first delivery、低 CPU、低唤醒、少复制、无跨流 HOL。无需反复重跑已完成阶段。
