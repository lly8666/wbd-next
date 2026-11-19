A28 latest user directive (2026-11-19): sync latest main code, full client feature cards and all main development archives into experiment/android-temp-root-probe WITHOUT touching main. Use a real two-parent merge of source-locked main SHA 46a756df1114aecda8dc2d5d259a5cbb4c9a909f and prior experiment cd6207bab1eb624f8f5b51bdec06854fbee77076, preserve all history and inspect actual overlapping source paths. Crucial cross-platform merge: main 32 Rust slots, server short-key v2/decoy/NAT/padding MUST NOT silently enable Android Fixed/Game, short-key UI or different TLS. Keep Android original Go/Rust Normal/off Root UID route + exact server /32 exception + Stop + safe diagnostic. Verify merged SOURCE via Actions Host/signed ARM64 APK; do not auto-run KSU/TAP or touch a phone/server. See A28 in sole authoritative plan. If main HEAD moved, report frozen SHA explicitly and plan a follow-up sync; never reset/force or merge Draft PR into main.

A27 latest user scope: Audit default ordinary-App IPv4 whole-app
UID range, make original-server resolved IPv4 a private-table
/32 THROW exception before any all-app UID grant with exact readback,
owned Stop, v3 owner-journal migration and Host Go tests. Add one-click
APK offline SAFE TXT export through Android system file chooser: only
allowlisted Root stages/timestamps/SOURCE/API and private-FIB status;
never raw native stdout, logcat, server IP, password, route-key or
UID/package names. Current whole-phone promise must remain narrow:
system/root, IPv6, Android DNS/CLAT/hotspot and actual netd
egress NOT_CONNECTED/NOT_RUN. User does not authorize emulator NIC
binding or physical phone/server tests. Do source-locked Host tests
and ARM64 APK build only; no KSU/TAP guests.
 
A29 user request (2026-11-19): Build one Android Root Lite v2 signed ARM64 TEST APK from the already-merged experiment branch. Only Android-appropriate new main feature: v2 8..32 ASCII alphanumeric short route-key, PBKDF2-HMAC-SHA256 4096 domain salt, HMAC-verified derived 32B cache in private 0600 noBackup AtomicFile, or original 64hex route-key. Both paths feed the same 0600 --route-key-hex-file, never the short secret/argv/Intent/log or a new TLS roundtrip. Preserve original Normal/off Go FakeTCP+TLS/Rust M4, physical Network, all ordinary App IPv4/server /32 private-FIB THROW, exact Stop and safe TXT. Lite UI collapses optional Root selftest. Host golden vectors, signed APK DEX/native SHA and original Linux oracle required; Android physical end-to-end remains NOT_RUN and must not be inferred from build. No phone/server/KSU/TAP guest use without explicit authorization. Same app package with disposable debug CI signing cert: STOP+route cleanup then uninstall old debug version before installing new. Do not alter main or close Draft PR.

# Android Root 原生 WBD 客户端｜长期接续提示词（现行单一版）

> 这是 **agent 每次接续时的操作入口**，不是历史 Actions 年表。权威执行方案：[`ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md`](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md)；最近已核验业务诊断为 SOURCE `731ea034` [A25 Action #44285914998](https://github.com/lly8666/wbd-next/actions/runs/44285914998)。**开工必须重新核远端 HEAD、PR 和 Actions，不能永久复述这个 SHA 或阶段状态。**

## 1. 开始前必须做

1. 确认仓库 `lly8666/wbd-next`、实验分支 `experiment/android-temp-root-probe`、`main` 两边最新 SHA、[Draft PR #36](https://github.com/lly8666/wbd-next/pull/36) 状态、最近 Actions 每一个 Job 的 SUCCESS/FAIL/SKIPPED 与在途结果；有未提交工作树时先审查，不重置、不覆盖、不重复启动相同重型任务。
2. 先读 `AGENTS.md`、`PROJECT_CHARTER.md`、`docs/architecture/TLS_HANDSHAKE_CONTRACT.md`、`docs/architecture/MTU_CONTRACT.md`、[现行唯一执行方案](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md)、[产品功能卡](../features/entries/android-root-native-client.json)、`docs/devlog/android-root-probe/` 的**最近**记录；旧计划只作证据，不允许复活历史“当前唯一下一步”。
3. 回复或动手前，以一句话归纳“原客户端走到了哪一个真实阶段、哪里还没有证据”；不要用绿灯、编译、旧 x86 探针、Go `--help`、`sendto=0`、App 界面或 Linux↔Linux oracle 代替 Android↔Linux 业务 PASS。

## 2. 唯一正在攻克的阻塞（会随最新证据更新）

**优先完成原 WBD Normal/off 从 Android 原 Go/Rust 到 Linux 原 Go/Rust 的真实 FakeTCP SYN/SYNACK、标准 TLS、身份认证、/32 租约、Rust M4 双向应用 TCP/UDP、owned Stop；不要在它前面插入 DNS、全局默认路由、UI、Fixed/Auto/Game 等新功能。**

已核验 SOURCE `731ea034`：Android16 x86_64/KVM/KSU 真普通 App→su、原 Go/Rust 资产、真实 WLAN0 `ConnectivityManager.Network`、原 TUN/RAW、FakeTCP SYN `sendto` 和原 Linux server 启动已 PASS；原 Go 未认证 RST RX OBSERVED。针对 `-net-tap` 与 `-wifi-tap`+短隔离 DHCP 两轮 guest 试验，宿主 TAP kernel RX 在启动/D2 均 `NOT_OBSERVED`、真实 DHCP lease `NOT_PROVEN`；原 Linux RAW SYN RX、SYNACK TX、Android SYNACK RX、TLS认证/32租约、Rust M4 真业务和 Stop 均未证明。A25 [Action #44285914998](https://github.com/lly8666/wbd-next/actions/runs/44285914998) **12 SUCCESS+3 SKIPPED 是按阶段完成的诊断，不是端到端 PASS**。A21 全 App 仅 Host/构建通过，系统 DNS 冷门仍 false。

**下一步唯一网络资格门**：当前 hosted x86 TAP 试验记 `ENV_BLOCKED_NETWORK_PATH`，不得重刷相同 QEMU/KSU Job 或改 TLS/AEAD、伪造 Network/默认路由/DNS。只有获取用户单独授权的真实 ARM64 设备，或实际可用且获授权的自管 ARM64 KVM/隔离真实接口，才继续原 Go/Rust ↔ 原 Linux RAW SYN RX→SYNACK TX→Android SYNACK RX→标准 TLS/认证/租约→Rust M4 真双向 TCP/UDP/owned Stop；无环境/授权时只准备离线最小验收收据，不动手机/服务器。

**本轮最新用户优先指令（A26）**：明确**不做模拟网卡绑定或真机测试**。可在实验分支直接施工签名 ARM64 APK ↔ 原 Go/Rust 的生产 CLI argv/RootService/Stop 接线，GitHub Actions 做同源双 ABI 编译、实签 APK 资产 DEX+原Go/Rust ELF SHA/DT_NEEDED + Go flags 对照、Host JVM 正反用例与原 Linux oracle。x86 KSU/TAP guest 默认仅显式手工 dispatch，不做本轮测试。Host BUILD/WIRING PASS 不升级 A25 的 ENV_BLOCKED_NETWORK_PATH 或 Android↔Linux 真业务资格。

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
