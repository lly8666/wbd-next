# Android Root 原生 WBD 客户端｜长期接续提示词（现行单一版）

> 这是 **agent 每次接续时的操作入口**，不是历史 Actions 年表。权威执行方案：[`ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md`](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md)；当前基线为 2026-11-18 `b926881b` 的 [Action #44269992127](https://github.com/lly8666/wbd-next/actions/runs/44269992127)。**开工必须重新核远端 HEAD、PR 和 Actions，不能永久复述这个 SHA 或阶段状态。**

## 1. 开始前必须做

1. 确认仓库 `lly8666/wbd-next`、实验分支 `experiment/android-temp-root-probe`、`main` 两边最新 SHA、[Draft PR #36](https://github.com/lly8666/wbd-next/pull/36) 状态、最近 Actions 每一个 Job 的 SUCCESS/FAIL/SKIPPED 与在途结果；有未提交工作树时先审查，不重置、不覆盖、不重复启动相同重型任务。
2. 先读 `AGENTS.md`、`PROJECT_CHARTER.md`、`docs/architecture/TLS_HANDSHAKE_CONTRACT.md`、`docs/architecture/MTU_CONTRACT.md`、[现行唯一执行方案](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md)、[产品功能卡](../features/entries/android-root-native-client.json)、`docs/devlog/android-root-probe/` 的**最近**记录；旧计划只作证据，不允许复活历史“当前唯一下一步”。
3. 回复或动手前，以一句话归纳“原客户端走到了哪一个真实阶段、哪里还没有证据”；不要用绿灯、编译、旧 x86 探针、Go `--help`、`sendto=0`、App 界面或 Linux↔Linux oracle 代替 Android↔Linux 业务 PASS。

## 2. 唯一正在攻克的阻塞（会随最新证据更新）

**优先完成原 WBD Normal/off 从 Android 原 Go/Rust 到 Linux 原 Go/Rust 的真实 FakeTCP SYN/SYNACK、标准 TLS、身份认证、/32 租约、Rust M4 双向应用 TCP/UDP、owned Stop；不要在它前面插入 DNS、全局默认路由、UI、Fixed/Auto/Game 等新功能。**

已核验 SOURCE `b926881b`：Android16 x86_64 KVM/KernelSU 原生 Go `--help`、普通 App→su、原 TUN/RAW/PhysicalNetwork 读回、SYN `sendto` 和原 Linux server 启动通过；**服务端原 RAW SYN RX、原 SYNACK TX、Android SYNACK RX、TLS/认证/租约及 DATA 未证明，客户端在认证前退出**。[D2-S1 Action #44269992127](https://github.com/lly8666/wbd-next/actions/runs/44269992127) 整体 SUCCESS 为分层诊断，不是端到端 PASS。A21 默认普通 App IPv4 UID range/owned Stop 仅 host/构建通过，尚无全 App Android 内核真验证。

**立刻的诊断顺序：** 以同一 SOURCE 分离 guest 网卡 SYN → host SYN → **原服务端 RAW 初始 SYN 接收** → **原服务端 RAW SYNACK 发送** → Android 原 `ClientAssociation` 收 SYNACK → 真 TLS 认证租约。各节点提供来源和固定枚举。若现有 QEMU SLIRP/用户态 NAT 不保真，优先在独立 Actions Job 试**真实 TAP guest**（现有 host `-net-tap` 准入 PASS 不是 guest PASS），必须保持真实 `ConnectivityManager.Network` 与原 PhysicalNetwork socket 绑定，且有界回收，不制造伪网络。TAP 不可行则记录环境阻塞、考虑单独获授权的真实 ARM64 手机或有 ARM64 KVM 的自托管环境。**不要先修改 TLS/AEAD 抵消网络异常。**

## 3. 两个 ABI 的角色不可偷换

- **ARM64 为唯一发布目标**：原 Go `android/arm64` + 原 Rust `aarch64-linux-android`、16KiB、签名 arm64-v8a APK，必须最终在真正 ARM64 Android 验收。已有用户短时真机诊断不能代替正式 WBD 实连。
- **x86_64 仅为 CI 诊断平台**：在已可用的 Android16/KSU/KVM 上**原生**编译运行相同原 Go/Rust 核心，不能另写一个 x86 版协议或把它作为发布 APK。Linux/Windows 共享源码更改需保护原语义和回归。历史 ARM64 NativeBridge 独立 Go ELF SIGSEGV139；按需手动诊断，不作为日常阻塞。GitHub hosted ARM64 `/dev/kvm` 缺失不等于装 udev 就能启动 Cuttlefish。

## 4. 什么可以为“先跑通”简化

可以只测临时测试 App UID/Normal/off、从受控 Root shell 直接运行同一原始 ELF 的预认证阶段、短时隔离宿主 443/RST 抑制并精确恢复、临时测试证书/凭据、单独 TAP 网络试验；**阶段性成功按阶段命名**，不能称完整 E2E。

不能关闭/伪造原标准 TLS ClientHello/认证/证书校验、合法租约、Rust 原 M1/M3/M4/PN/AEAD/重放、真实 TUN/RAW、原生产代码路径；不能另写 x86 假客户端、模拟 SYNACK、伪造 App Root 权限、关闭整机 SELinux、改 Android 全局路由/DNS 来求 PASS。防泄漏、source/hash/owner journal、generation、精确 Stop 与回滚要保留；不得操作未单独授权的实体手机、联网服务器或购买资源。

## 5. 验收、测试与提交要求

- D0：双 ABI 同源码构建 + ARM64 正式 APK + 原 Linux Oracle；D1：x86 真原生 App KSU、Go/Rust、Network、TUN/RAW；D2a：RAW SYN/SYNACK 双端事实；D2b：原 TLS/租约；D2c：原 Rust M4 真双向 App TCP/UDP、UID 路由和 Stop。**每级独立 PASS/FAIL/NOT_PROVEN/ENV_BLOCKED，后级不可由前级继承。**
- ARM64 实体/原生 ARM64 guest 是另一道最终资格门；只在用户明确授权或可用自管 ARM64 环境下执行。Android 全 App IPv4 默认路由、DNS 系统拦截、切网、热点、FEC/Fixed/Auto/Game 放在 D2 完整闭环之后再实测；当前 DNS 冷门仍禁止提前启用，IPv6/system_server/netd/system DNS/Root 不得因“全部 App”UI 而虚报接管。
- 优先一条最短真实联机链、一段清楚的错误证据和有界重试。单 SOURCE/manifest/SHA 锁定 CI、使用真实原件、失败保存可核验收据，避免重复 dispatch 和海量临时探针；修改功能必须同步短 devlog/功能卡；不得改写历史 FAIL 或旧 SOURCE。
- 工作仅在 `experiment/android-temp-root-probe`，Draft PR #36 待验收；`main`、M0 registry/cursor 由 main 单写者维护，不能 force/reset、偷合代码，也不因 Android 限定回归直接宣布 Windows/Linux 所有模式通过。

## 6. 每次结束必须写明

请用简洁、可审计的结果交代：**本次 SOURCE/分支/PR；实际修改路径；最新 Action + 各关键 Job；原始业务已到达 SYN、SYNACK、TLS、租约、M4、Stop 的哪一步；剩余 FAIL/NOT_PROVEN/NOT_RUN；下一步唯一关键路径**。提供准确链接。历史阶段见 `docs/devlog/android-root-probe/`，不要把长期提示词重新写成追加式流水账。
