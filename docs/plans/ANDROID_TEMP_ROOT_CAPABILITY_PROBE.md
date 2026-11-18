# Android Root 原生 WBD 客户端｜现行唯一执行方案

> 更新：2026-11-18，基线 SOURCE `b926881b59581c073066d42f315b176f95e23c0b`。**本文件是当前执行口径，不是历史阶段流水账。** 每次施工先核远端 HEAD、PR、正在运行的 Actions 再更新事实；以下 SOURCE/Action 仅是本次编辑时已核验证据，不能被下一会话当作永远最新。
>
> 原路径 `ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md` 为保持引用稳定而保留；任务已经从“短时能力探针”升级为正式 Android Root 原生客户端。旧 A3/A6/B2/A9/A15 分阶段方案及其原文，可从 [本次整理前的 Git 历史快照](https://github.com/lly8666/wbd-next/blob/b926881b59581c073066d42f315b176f95e23c0b/docs/plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md) 和 `docs/devlog/android-root-probe/` 查阅，**不再具有并列执行优先权**。

## 1. 单一目标、权限与平台边界

**第一优先：使用真正原 Go + 原 Rust，把 Android Normal/off 原始 WBD 客户端与同源 Linux 原服务端的 FakeTCP SYN/SYNACK → 标准 TLS ClientHello → 身份认证 → 自动 /32 租约 → Rust M4 双向应用 TCP/UDP → owned Stop 跑通。** 第一条真实业务链闭环高于 DNS、全应用默认范围、UI、美化、Fixed/Auto/Game、热点或性能调参。

- **正式产品仅发布 ARM64**：`arm64-v8a`，Go `GOOS=android GOARCH=arm64 CGO_ENABLED=1`、Rust `aarch64-linux-android`、Bionic NDK，签名 APK 内不混入 x86 诊断 ELF，ARM64 16KiB ELF 门独立保留。**x86_64 是 CI-only 的原生 Android16/KVM/KernelSU 集成后端**：同一 Go donor/overlay、原 Rust M1/M3/M4、原 App Service、Root/TUN/RAW/路由/Stop，只允许必要 ABI/汇编条件编译差异；不实现独立 x86 协议或发布 x86 安装包。
- 施工只在 `experiment/android-temp-root-probe`；[Draft PR #36](https://github.com/lly8666/wbd-next/pull/36) 保持 Draft。`main`、M0 registry/cursor、已有 Linux/Windows 行为不直接改、不 force/reset、不自行合并。共享 Go/Rust 改动必须具备原 Linux oracle 与平台编译回归，跨平台未经测试的功能明示 NOT_PROVEN。
- 用户已授权在仓库实验分支进行软件施工与 Actions。**不因本计划而获得操作用户实体手机、部署个人服务器、购买 ARM64 云主机、刷写 boot、调整用户网络配置的授权**；真机动作需用户明确授权。允许准备供用户自行执行的只读收据脚本；主动连接/安装/Root START 前需另行确认适用范围。
- 复用 `AGENTS.md`、`PROJECT_CHARTER.md`、`docs/architecture/TLS_HANDSHAKE_CONTRACT.md`、`docs/architecture/MTU_CONTRACT.md`。标准 TLS 首载荷、真实认证/完整性、/32 租约、原 Rust PN/AEAD/replay/M3、generation、MTU/BorrowFence、owned Stop 不可妥协。没有 VpnService、FakeIP、伪 TLS、独立数据协议、Go/Java/JNI/shell 逐包转发、第二 TUN reader。

## 2. 当前真实进度（以各自被测环境为范围）

[同源 Android dual64 Action #44269992127](https://github.com/lly8666/wbd-next/actions/runs/44269992127) 对应 SOURCE `b926881b`：工作流整体 SUCCESS，**13 个成功 Job + 1 个按条件跳过的历史 NativeBridge Job**，不能说 14 项均执行 PASS。

| 阶段 | 已验证 | 不得推断 |
| --- | --- | --- |
| D0 同源原 Go/Rust 生产源码双 Bionic ABI | ARM64 ELF/签名 APK、x86 CI-only 原生 ELF 与诊断 APK 构建，独立 Linux 原服务端 oracle 和基础 DNS/M3 Host 门通过 | 不代表 Android↔Linux 真实连接 |
| D1 x86 Android16/KVM/KernelSU | 原 Go ELF `--help`、原 Java APK、普通 App UID→真实 KSU `su`、选定 PhysicalNetwork handle/ifindex/IPv4/MTU 读回真实执行 | 不代表 ARM64 真机，也不是 adb-root 与 KSU 全面等价 |
| D2-S1 原协议预认证 | 同源原 Linux server 确实启动；原 Android RootService 原生 TUN/RAW 初始化；原 Go FakeTCP SYN `sendto` 系统调用成功；测试内隔离 Linux loopback 观察到 TCP SYN | **尚未确认服务端原 RAW 代码读到合格 SYN、原服务端发 SYNACK、Android 收到有效 SYNACK**；客户端在认证前退出 |
| D2 完整 Android↔Linux | **NOT_PROVEN / 尚未达标** | TLS/认证、/32 租约、Rust M4、真实应用 TCP/UDP、认证后 UID 路由与 Stop 不能凭 D2-S1 绿色 Job 宣称 PASS |
| A21 默认普通 App IPv4 UID 范围 | Java/Go Host 测试、带回滚 journal、同源正式 ARM64 APK 构建通过 | **真 Android 全应用内核 E2E 未测试**；不代表系统 DNS、IPv6、root/system/isolated UID 也被接管 |
| 原生 ARM64 Android | ARM64 正式 APK 构建通过；用户早前提供过短时 Root/TUN/UID 诊断证据，按其各自范围保存 | 同一正式 ARM64 原 Go/Rust 对原 Linux server 的完整 WBD 业务 **NOT_PROVEN** |

关键日志：[D2-S1 #44269992127](https://github.com/lly8666/wbd-next/actions/runs/44269992127) 出现 `D2_S1_REAL_ORIGINAL_ANDROID_TUN_RAW_CONFIGURED_PASS`、`D2_S1_ORIGINAL_GO_EARLY_EXIT_BEFORE_AUTH_HANDSHAKE`、`D2_S1_ANDROID_SYNACK_NOT_PROVEN`、`D2_S1_ANDROID_ORIGINAL_AUTH_LEASE_NOT_PROVEN`。先前宿主 Linux loopback SYN 证据 **不是** 服务端原 `raw.ReadSegment` 收包证据。

环境历史：macOS ARM64/ReactiveCircus Android Emulator QEMU 挂起 ADB 未上线（[Action #44042235770](https://github.com/lly8666/wbd-next/actions/runs/44042235770)）；GitHub hosted `ubuntu-24.04-arm` 上 `/dev/kvm` 不可用；x86 guest 的 ARM64 NativeBridge 原 Go **独立 ELF 139**，隔离 c-shared 诊断成功不等于原 ARM64 产品正常运行。NativeBridge 仅保留手动历史诊断，不再作为日常关键阻塞。

## 3. 目前唯一关键路径：D2 真实握手，不再扩展附带功能

### D2a｜先定位原始报文断点

采用**同 SOURCE** 的原 Android Go/Rust + 原 Linux Go/Rust server，复用现有 `android/root-app/ci/x86-kvm-ksu-native.sh`、`x86-d2-original-root-preauth.sh`、`x86-d2-cold-wire-observer.py`。分层记录下列有来源的事实，不能仅靠 `sendto=0` 或 guest/host 代理 TCP 结果推断对端认证：

1. Android 原 Go 成功创建 TUN/AF_PACKET、选定真实 `PhysicalNetwork`，发送初始 FakeTCP SYN：记录 syscall 结果、原 socket 出口与限定错误类别。
2. Guest 虚拟物理网卡是否看到 SYN；Linux host 入口/loopback 是否看到 SYN，QEMU SLIRP/NAT 有没有将原始报文转换为普通 TCP socket。抓包只在 CI 临时分析，工件只留下固定 SYN/SYNACK/RST 计数/阶段码，不上传私密流量。
3. **Linux 原服务端** 是否通过原 RAW reader 收到并验证初始 SYN（`V4_PUBLIC_ORIGINAL_SERVER_RAW_INITIAL_SYN_RX`），是否通过原 RAW emit 发出 SYNACK（`V4_PUBLIC_ORIGINAL_SERVER_RAW_SYNACK_TX_OK`）。
4. Android 原 `ClientAssociation` 是否真收到并接受 SYNACK（`ORIGINAL_GO_TCP_SYNACK_SEEN`）。若未到达此处，不先改 TLS、证书、AEAD 或全 App 路由。
5. 精确定位原 Go 认证前退出的原始 errno/阶段，不增加伪成功标记；错误栈仅在 CI 私密日志排查，公开工件去凭据化。

**根因尚未最终归因**。当前主要假设是 Android Emulator 的用户态 NAT/SLIRP 不能保持 FakeTCP/RAW 语义；这需要上述双端原生 socket 证据确认，不提前把它写成定论，也不能默认是程序安全检查太严。

### D2b｜仅当网络路径确认阻塞时，优先隔离 TAP guest 实测

[独立 TAP host 准入 #44264710804](https://github.com/lly8666/wbd-next/actions/runs/44264710804) 只证明 KVM 权限、Emulator `-net-tap` 参数展示和宿主 `/dev/net/tun` /隔离 TAP 接口读回；**并未启动真实 TAP Android guest**。

下一切片：单独有界 Job 中启动 x86_64 Android16/KSU guest 的实际 TAP 网络，以不影响 Actions runner 默认路由/DNS 的隔离 host TAP/桥接或受控网络命名空间承载原协议。必须逐项实查 guest boot/ADB、普通 App KSU `su`、`ConnectivityManager` 中真实 Network handle/源 IPv4/ifindex/MTU、原 `android_setsocknetwork`、原 Go/原 Rust/原 Linux server 双端 RAW 收发和反向路由。**不能为了 TAP 绕过产品的 PhysicalNetwork 绑定校验、伪造系统 Network 或无差别关闭整机安全策略。** 如果官方模拟器 TAP 后端与 KSU 镜像不能组成可用 guest，则留下 `ENV_BLOCKED` 和具体原因，及时止损；不得无限重试。

若 TAP 仍不可行：可考虑已有用户授权范围内的自愿、手动 ARM64 真机最小诊断，或在单独获得授权后使用具 KVM 的 ARM64 自管 runner/隔离实验网络。不要把 hosted ARM64 缺 KVM 归咎于一段 udev 权限配置。

### D2c｜将预认证真正升级为业务 PASS

网络层可用后，固定一套临时证书/测试凭据和测试账号，逐一证明：

- 原 Go 发合法 FakeTCP SYN/SYNACK 及标准 TLS ClientHello；原 Linux server 真实读取和认可，不能用自建简化协议/假的服务端回应。
- 真 TLS 证书/身份验证、原认证、自动 /32 租约的**双端一致**证据，非仅一条客户端“Ready”日志。
- 原 Rust M1/M3/M4 唯一 DATA path 双向 UDP 与 TCP 的真实测试 App 业务，有实际收发内容与有界超时、原始路由/物理出站和唯一 TUN reader；Normal/off 先闭环。
- 正式 App UID→KSU `su`→原生 worker，认证之后才安装被测的**一个**真实测试 App UID 路由，真内核规则/表/MTU 读回；按 owned generation/owner.pid starttime/Stop 顺序准确清理，再检验**相同**规则不残留。
- D2 E2E 绿色只能由这些真实条件联合门决定。预认证测试 Job 可以成功结束并产出阶段收据，但必须明确写 `D2_PREAUTH_ONLY; TLS/LEASE/M4 NOT_PROVEN`，不能冒称全链通过。

## 4. 现有功能暂缓扩展，不丢失已做成果

- **A21 全普通 App IPv4 默认路由**：正式 UI 已默认 all-apps；通过 20 个 Android user 段的普通 AppID 10000–19999 `uidrange` 构成私有 table 19842，排除 WBD 与已安装 Root Manager AppID，采用版本 3 journal/flock/fsync/原规则精确回读/Stop。**已完成的是源码与 host 假 ip Runner 回归，不是设备内核行为**。D2 联调使用**一个有界测试 UID**，禁止提前启动全应用系统路由。之后再真实设备验证多 UID、所有普通 App、工作资料/共享 UID 与失败清理。
- **DNS / CN**：固定 CN 物理 DNS `223.5.5.5`、隧道 DNS `1.1.1.1`，服务器域名 bootstrap 物理先解析；原始 8503 条 geosite、Host UDP/TCP、Rust DNS53 映射已有源码/Host 证据。但系统 Resolver/内层真 DNS interception 和 TCP53 尚未完整验证，`hijack_enabled=false` / `android_dns_physical_ready=false` 等实际冷安全门未通过前不启用；无跨上游兜底、FakeIP 或 per-App 假 DNS UID。
- **产品功能顺序**：Normal/off 真实连接 → App/Root/TUN/UID/Stop 安全闭环 → DNS/规则分流/全隧道/直连/按包选择及全应用范围 → Fixed/Auto/Game/FEC、切网/Health/CPU/延迟/低唤醒 → 热点/USB/CLAT/物理功耗。既有完成模块不必重做，但每一步区分 Host 与 Android 真实验收。
- **网络与资源**：原手机选定 Network handle、ifindex、IP、MTU 不可悄然改用默认 Network；切网采用低频 callback 与会话 Stop，外层用户完整 IPv4 MTU 默认 1460B（不含 L2）、1500 仅显式最大，内层 Rust 预算及 OS 读回。停止只撤销自己精确增量，不 `ip rule flush`，不重置系统全局路由/防火墙或关闭 SELinux。

## 5. “快速跑通”的允许与禁止

**允许加速的，是测试路径与排程**：临时直接通过受控 Root shell 运行**同一原始 ELF** 做预认证诊断、在隔离 CI 中短时针对 host loopback 443 RST 建精确规则且退出恢复、使用临时账号/证书、只跑 Normal/off 和单 UID、分阶段标记“可执行/可通信”而不要求每一步都达到整机产品 PASS；有上限、有日志、能复原。

**不可用来造绿灯**：关闭 TLS 认证/证书校验/真实 lease、伪造 SYNACK、假 AEAD、去掉 Rust 原数据面、伪装 Android 物理 Network、使用 host Linux 成功代替 Android、把 x86 结果写作原生 ARM64、强制放开 SELinux 或破坏用户主网络、为快速修模拟器而重写公共 Linux/Windows 协议。

## 6. 分层验收与失败定性

| 名称 | 最低证据 |
| --- | --- |
| `BUILD_PASS` | 同 SOURCE 原 Go/Rust 及签名 ARM64 APK 源锁、ELF/FFI、Host 测试；不包含真设备 |
| `ANDROID_X86_ROOT_RUNTIME_PASS` | 真 x86 KSU App `su`、原 Go ELF/原 Rust、TUN/RAW/Network 读回 |
| `D2_PREAUTH_PARTIAL` | 标注 SYN 发送、Linux RAW RX、SYNACK TX/RX 各自的 `OBSERVED/NOT_PROVEN`；无 TLS/lease 冒名 |
| `ANDROID_X86_E2E_PASS` | 原双端 TLS/认证租约、Rust M4、真实 app TCP/UDP 双向、内核 UID 路由与 owned Stop |
| `ANDROID_ARM64_NATIVE_PASS` | 原生 ARM64 Android（非 x86 NativeBridge）同一原 ARM64 ELF/签名 APK 的实际 Go/Rust 与系统路径 |
| `ANDROID_ARM64_E2E_PASS` | 经单独授权的 ARM64 真机或合格原生 ARM64 guest 上原双端完整业务、Root/路由/Stop；真机特有 KSU/SELinux/netd/热点另列范围 |

记录 `FAIL`、`ENV_BLOCKED`、`NOT_RUN`、`NOT_PROVEN`、`SKIPPED` 必须不同列；单纯 Actions SUCCESS 仅代表 job 自己的准入范围。CI 收据用固定枚举、源 SHA/manifest/hash、关键读回，不上传密码、route-key、私有证书、应用通信正文或全 PCAP。真实物理设备观察与用户自述证据必须单列，不冒充 Actions 可复验。

## 7. 开发执行节奏与文档治理

每次启动先读 [长期接续提示词](../prompts/ANDROID_TEMP_ROOT_PROBE.md)、`AGENTS.md`、`PROJECT_CHARTER.md`、当前分支/main HEAD、[Draft PR #36](https://github.com/lly8666/wbd-next/pull/36)、最近 Actions（含 SKIPPED/失败）、本文件、[产品功能卡](../features/entries/android-root-native-client.json) 和新 devlog；实际最新提交与现存工作树优先，不能把本次基线 SOURCE 强行当最新。若上一 Agent 已触发 CI，在途先收据，不重复 dispatch。

一轮集中解决**一个真实阻塞的纵向切片**；可并行研读互不依赖的东西，但同批冻结 SOURCE 后原双 ABI 编译、原 Linux server、KSU guest 及同一场景收据用同一来源，避免针对琐碎日志发多轮重型 CI。修复需附实际失败点和验证；改功能时同步更新功能卡/短 devlog，不重写旧 Actions 的 FAIL 史。新功能未有运行价值前不抢 D2 最短路径。

历史入口：[实验能力探针卡](../features/entries/android-temp-root-probe.json)、[Android Root App 说明](../../android/root-app/README.md) 和 [2026-11-18 D2/TAP/A21 阶段记录](../devlog/android-root-probe/)。这些是证据库，**不是与本方案竞争的下一步任务清单**。
