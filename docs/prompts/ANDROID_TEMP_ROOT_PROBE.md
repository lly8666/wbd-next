**2026-11-24 B83 用户范围冻结（当前最高优先级）**：除手机端显式手动联网更新官方 CN 域名列表（唯一功能待办；已有内置8472、文件导入/恢复）外，所有 Android 主体功能标记为基本完成开发、转入验证；未实现的高级功能冻结不开发，不把它们说成已接线。只修实际测试发现的业务/性能问题，不扩极端工况。高级 CN FakeIP 仍 OUT_OF_SCOPE。优先复用一次 Android16 x86 KVM/KSU guest 跑 ART 冷控制、x86 原生原Go/Rust、ARM64 NativeBridge 真 Rust MTU 和原Go c-shared help；原 ARM64 独立 Go ELF139 与 hosted SLIRP/TAP RAW 路径阻塞保持历史，不为冷测试重开这些诊断；ARM64 真机集中验证真实业务、内核设备差异和性能。

# Android Root 原生 WBD 客户端｜长期接续提示词（现行单一版）

**2026-11-24 最新用户决定（B80）**：每次从 main 同步已正式合入的全部源码、功能/优化与历史（真实双亲 merge，保留 Android 专有代码），平台差异只在 Android Bionic RAW/TUN、Root/Network、App 冷设置等适配层处理。优先复用 main 共享核心，不复制一套协议/算法；main 的 Windows/服务端专有逻辑保留源码而不误启用在 Android。Android 必须适配原表演式/机会式外层重传，旧逐 record M2 Receipt 已废弃，禁止复活。高级 CN FakeIP 仍明确 OUT_OF_SCOPE；普通 CN DNS 与真实 IPv4 内核直连保留。

**2026-11-24 最新用户决定：Android 高级 CN FakeIP = OUT_OF_SCOPE（明确不实现，不是待办）。** 保留普通 CN8503 域名 DNS 分流、真实 IPv4 CN 内核 FIB 直连、手工 CIDR；不引入合成 IP、FakeIP 映射、对应路由、UI/CLI 开关、代理数据路径或验收任务。按大类功能并行研读/合批接线，复用原 Go 冷控制及原 Rust 数据面；不展开极端工况、额外防御性安全开发或重复历史 SYN/TAP 探针。

## 1. 接续核查
只在 `experiment/android-temp-root-probe`、[Draft PR #36](https://github.com/lly8666/wbd-next/pull/36) 开发，不写 main/M0，不 reset/force。每次先查两边 HEAD、PR、最新 Actions 各 Job 与在途工作，审查可访问的未提交工作树，不重复 dispatch。读 AGENTS、章程、TLS/MTU 契约、[现行方案](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md)、[功能施工台账](../plans/ANDROID_ROOT_IMPLEMENTATION_BOARD.md)、[功能卡](../features/entries/android-root-native-client.json) 与最近 devlog；旧 SOURCE/旧提示仅历史证据。

## 2. 当前实际阶段与施工逻辑

**B82 测试收口候选：** B82 WIRED_CANDIDATE / feature-freeze candidate：CN IPv4 直连同一已合并 CIDR 表覆盖普通 App 与显式软件热点（真实内核 throw，冷批量路由和索引读回，Stop/Restore）；独立普通 UID TCP/UDP 字节回显测试 APK、双向流式 echo/RTT、可选 Android 系统 DNS、同 SOURCE fixture Host loopback，现有 CI 先产 APK 再执行历史源码门。无新 WBD 协议/数据线程/防御框架。B81 官方 8472 条 Go/Rust Host、双 ABI、两个 Linux Oracle PASS；APK 旧 send_staged 断言、维护旧 regex-lite graph FAIL，已按实际源修候选。B82 CI/设备/性能尚未验。主线先测七模式、UID/直连/DNS、IPv6/热点、冷切网/轮换，再短性能 A/B；不扩大热迁移/idle dormant/在线规则下载等非当前主体测试前提。 集中计划见 [ANDROID_ROOT_TEST_MATRIX](../plans/ANDROID_ROOT_TEST_MATRIX.md)。
历史 A48 SOURCE `4a19f20456e74f3e7700e3a2876eda40536bb8d9` ARM64 API36 原 Normal/off 已实证 SYN/SYNACK、标准 TLS（证书身份验证关闭）、认证、/32、UID、原 Rust M4 RAW/TUN 双向及 owned Stop，用户报告数据通了；应用层 TCP/UDP 独立逐字节与性能尚未验。A49/A50 删除重复 checksum/解析/poll；A54 已撤回额外 TLS/DNS 防御门。不要把旧 D2-S1/SYN/TAP 当当前阻塞。

**B80 WIRED_CANDIDATE**：冻结 main `5b1311c0748452c1c8dac66fc2a6e517777529fa`，双亲 merge `a0d31730e772dea9d1884076c945c7c810b879c9`（Android 原父 `1997efa2d89b52e11f21037c7972deee9139a0c0`）；206 个 main 变化文件完整同步，两个 Rust 重叠文件三方无损重放、Cargo 双依赖合成、Go manifest 按实际合成 blob 更新。Android Normal/Fixed/Auto 单 lane 与 Game2/4 off/fixed 复用 main `CosmeticOuter` 的 Normal-v3 `OuterAckIndex`/`ReceiptState`/9% pacing/10% quota，按真实 kernel copy 保留原密文一次，RAW ACK/SACK 元数据、Go 已协商 SACK、Game 物理 AEAD 后 ACK、现有 TX owner due/readback 和 Stop。Android 单 lane 使用同一个 main Game v3 控制器，不冒称已移植 Linux Normal process-global allocator。App/Go 显式 ON/OFF，旧 Android 预设默认 OFF 至实体资格，七模式开关可用性仍须同源构建和实体验证。main 8472 官方 CN 域名快照/手动更新源码已同步，Android 现役仍是经验证的 8503 typed snapshot，普通 CN 数据资产与冷导入适配另续；Linux H2376 满队列公平算法同步，Android 直接 TUN 不凭空加 Linux SharedTun 队列。旧 B79a 9 SUCCESS/1 FAIL/5 SKIPPED，APK 旧七模式 padding 拒绝断言已全部改正并补 App 开关往返正向用例。当前 SOURCE CI/实体/性能 NOT_RUN，不把接线当 PASS。

B81：复用 main 官方 CN 域名发布数据、原 Go 冷规范化与原 Rust 四类型匹配，App 导入/恢复下次 START 生效；不引入 FakeIP 或新增热路径。先读取本 SOURCE CI，按实际失败修复，继续把 main 正式成果做 Android 原生平台适配。独立模块可并行、合批冻结一次 SOURCE；不为极端工况反复扩展测试。

## 3. 原产品边界
Go 保留标准 TLS/认证、租约、OS/Root/Network 冷控制，Rust 唯一 TUN 与 RAW 长寿命 DATA；不引入 Java/Go 逐包转发、第二 TUN、重复检查、额外防御框架。原 M3 AEAD/PN、FEC 首交付去重、MTU/PMTU、generation 和 owned Stop 保留正常业务语义，证书验证沿 A54 用户选项；不自行加强。ARM64 唯一发布 ABI，x86_64 仅 CI 诊断，原生同源构建。真实设备/服务器另授权，默认不启动 KSU/TAP guest，不将 Linux oracle 或签名 APK 当 Android E2E。

## 4. 验收和交接
现有产品 CI 同源双 ABI、签名 ARM64 APK、原 Linux oracle、必要 Host 正常功能回归；按真实失败直接修复，不改写历史证据，不做海量极端测试。完成源码大类功能后再集中 ARM64 实机功能及同条件性能验收。每次短 devlog + 功能卡写明 SOURCE、分支、PR、实际修改、Action 各关键 Job、SYN/SYNACK/TLS/认证/租约/M4/Stop 真实阶段、FAIL/NOT_RUN/NOT_PROVEN 和唯一下一步。性能优先：first delivery、低 CPU、低唤醒、少复制、无跨流 HOL。无需反复重跑已完成阶段。
