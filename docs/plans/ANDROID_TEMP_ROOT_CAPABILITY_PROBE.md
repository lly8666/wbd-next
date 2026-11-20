# Android Root 原生 WBD 客户端｜现行唯一执行方案

> 更新：2026-11-18，已核验业务诊断 SOURCE `731ea034ce527ef2bf5a214d9a7431c96cb205dc`（[A25 Action #44285914998](https://github.com/lly8666/wbd-next/actions/runs/44285914998)）。**本文件是当前执行口径，不是历史阶段流水账。** 每次施工先核远端 HEAD、PR、正在运行的 Actions 再更新事实；以下 SOURCE/Action 仅是本次编辑时已核验证据，不能被下一会话当作永远最新。
>
> 原路径 `ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md` 为保持引用稳定而保留；任务已经从“短时能力探针”升级为正式 Android Root 原生客户端。旧 A3/A6/B2/A9/A15 分阶段方案及其原文，可从 [本次整理前的 Git 历史快照](https://github.com/lly8666/wbd-next/blob/b926881b59581c073066d42f315b176f95e23c0b/docs/plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md) 和 `docs/devlog/android-root-probe/` 查阅，**不再具有并列执行优先权**。

## 1. 单一目标、权限与平台边界

**第一优先：使用真正原 Go + 原 Rust，把 Android Normal/off 原始 WBD 客户端与同源 Linux 原服务端的 FakeTCP SYN/SYNACK → 标准 TLS ClientHello → 身份认证 → 自动 /32 租约 → Rust M4 双向应用 TCP/UDP → owned Stop 跑通。** 第一条真实业务链闭环高于 DNS、全应用默认范围、UI、美化、Fixed/Auto/Game、热点或性能调参。

- **正式产品仅发布 ARM64**：`arm64-v8a`，Go `GOOS=android GOARCH=arm64 CGO_ENABLED=1`、Rust `aarch64-linux-android`、Bionic NDK，签名 APK 内不混入 x86 诊断 ELF，ARM64 16KiB ELF 门独立保留。**x86_64 是 CI-only 的原生 Android16/KVM/KernelSU 集成后端**：同一 Go donor/overlay、原 Rust M1/M3/M4、原 App Service、Root/TUN/RAW/路由/Stop，只允许必要 ABI/汇编条件编译差异；不实现独立 x86 协议或发布 x86 安装包。
- 施工只在 `experiment/android-temp-root-probe`；[Draft PR #36](https://github.com/lly8666/wbd-next/pull/36) 保持 Draft。`main`、M0 registry/cursor、已有 Linux/Windows 行为不直接改、不 force/reset、不自行合并。共享 Go/Rust 改动必须具备原 Linux oracle 与平台编译回归，跨平台未经测试的功能明示 NOT_PROVEN。
- 用户已授权在仓库实验分支进行软件施工与 Actions。**不因本计划而获得操作用户实体手机、部署个人服务器、购买 ARM64 云主机、刷写 boot、调整用户网络配置的授权**；真机动作需用户明确授权。允许准备供用户自行执行的只读收据脚本；主动连接/安装/Root START 前需另行确认适用范围。
- 复用 `AGENTS.md`、`PROJECT_CHARTER.md`、`docs/architecture/TLS_HANDSHAKE_CONTRACT.md`、`docs/architecture/MTU_CONTRACT.md`。标准 TLS 首载荷、真实认证/完整性、/32 租约、原 Rust PN/AEAD/replay/M3、generation、MTU/BorrowFence、owned Stop 不可妥协。没有 VpnService、FakeIP、伪 TLS、独立数据协议、Go/Java/JNI/shell 逐包转发、第二 TUN reader。

## 2. 当前真实进度（以各自被测环境为范围）

[同源 Android dual64 Action #44285914998](https://github.com/lly8666/wbd-next/actions/runs/44285914998) 对应 SOURCE `731ea034`：工作流整体 SUCCESS，**12 Job SUCCESS + 3 Job SKIPPED**（普通 x86 D1、普通 SLIRP D2-S1 与历史 NativeBridge）。独立 Wi-Fi TAP guest Job SUCCESS 只表示预认证脚本正常收据、清理和源锁，并不证明 TAP 出站或端到端业务。

| 阶段 | 已验证 | 不得推断 |
| --- | --- | --- |
| D0 同源原 Go/Rust 生产源码双 Bionic ABI | ARM64 ELF/签名 APK、x86 CI-only 原生 ELF 与诊断 APK 构建，独立 Linux 原服务端 oracle 和基础 DNS/M3 Host 门通过 | 不代表 Android↔Linux 真实连接 |
| D1 x86 Android16/KVM/KernelSU | 原 Go ELF `--help`、原 Java APK、普通 App UID→真实 KSU `su`、选定 PhysicalNetwork handle/ifindex/IPv4/MTU 读回真实执行 | 不代表 ARM64 真机，也不是 adb-root 与 KSU 全面等价 |
| D2-S1 原协议预认证 | 原 Linux server/TUN 启动，Android16/KSU 普通 App→su、真实 WLAN0 PhysicalNetwork、原 TUN/RAW 与原 Go SYN `sendto` PASS；原 Go 未认证 RST RX OBSERVED；旧 SLIRP host lo SYN OBSERVED | **A25 Wi-Fi TAP guest 实际 RX=NOT_OBSERVED（boot 与 D2），DHCP lease=NOT_PROVEN；原 Linux RAW 有效 SYN RX、SYNACK TX、Android SYNACK RX 均 NOT_PROVEN**；客户端认证前退出 |
| D2 完整 Android↔Linux | **NOT_PROVEN / 尚未达标** | TLS/认证、/32 租约、Rust M4、真实应用 TCP/UDP、认证后 UID 路由与 Stop 不能凭 D2-S1 绿色 Job 宣称 PASS |
| A21 默认普通 App IPv4 UID 范围 | Java/Go Host 测试、带回滚 journal、同源正式 ARM64 APK 构建通过 | **真 Android 全应用内核 E2E 未测试**；不代表系统 DNS、IPv6、root/system/isolated UID 也被接管 |
| 原生 ARM64 Android | ARM64 正式 APK 构建通过；用户早前提供过短时 Root/TUN/UID 诊断证据，按其各自范围保存 | 同一正式 ARM64 原 Go/Rust 对原 Linux server 的完整 WBD 业务 **NOT_PROVEN** |

关键固定收据：[A25 Artifact #14420055907](https://github.com/lly8666/wbd-next/actions/runs/44285914998/artifacts/14420055907) 的 `android_original_selected_interface=WLAN0`、`guest_to_host_tap_l2_during_boot=NOT_OBSERVED`、`guest_to_host_tap_l2_during_d2_session=NOT_OBSERVED`、`isolated_tap_dhcp_lease=NOT_PROVEN`、`original_android_unauth_rst_observed=OBSERVED`，原 Linux 双 RAW marker 缺失；`host_tap_exact_cleanup=PASS`、`owned_dhcp_process_cleanup=PASS`。宿主上任何 SYN 或原 Go `sendto` 成功均不是服务端原 `raw.ReadSegment` 收到合法 SYN 的证据。

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

### 网络环境资格门｜Hosted x86 TAP 两种后端均未承载原业务

[旧宿主 TAP 准入 #44264710804](https://github.com/lly8666/wbd-next/actions/runs/44264710804) 只证明宿主接口可创建。新实测分别尝试了 `-net-tap`（[A24 #44282946884](https://github.com/lly8666/wbd-next/actions/runs/44282946884)）和针对 Android 原 `wlan0` 的 `-wifi-tap` + 隔离短 DHCP（[A25 #44285914998](https://github.com/lly8666/wbd-next/actions/runs/44285914998)）。A25 真 guest 启动、真实 `ConnectivityManager.Network`、App→KSU 与原 Go SYN sendto 皆已执行，但 TAP kernel RX 两个时段均 `NOT_OBSERVED`，真实 DHCP lease `NOT_PROVEN`；原 Go 收到未认证 RST。不能称原业务已经走 TAP，也不能将该行为归为 TLS/证书/AEAD BUG。测试域名/路由无任何权限绕过；现有 `-net-tap`、`-wifi-tap` hosted 配置在当前 SOURCE 应按 **ENV_BLOCKED_NETWORK_PATH** 退出本轮，不重复 dispatch 相同 QEMU/KSU 重型任务，不通过关闭 SELinux、强加 Android 默认路由/DNS 或伪网络来凑 PASS。

**唯一后续网络资格关键路径**：在先获得用户对真实 ARM64 设备或自管 ARM64 KVM runner 的单独明确授权、或已实际可用的获授权隔离环境后，再用同原 Go/Rust/签名 ARM64 APK + 原 Linux server，先取得客观 guest 物理接口 SYN → host SYN → 原 Linux RAW 初始 SYN RX → 原 Linux RAW SYNACK TX → Android ClientAssociation SYNACK RX；通过后依序继续 D2b 真 TLS/身份/32租约、D2c Rust M4 双向真 App TCP/UDP/单测试 UID 内核路由/owned Stop。**当前无此授权或环境时停止真实网络部署，只准备离线最小验收和错误枚举，不做实体手机/个人服务器操作。** GitHub hosted ARM64 `/dev/kvm` 缺失是另一环境门，装 udev 不解决。

### A26｜依用户新指令：只做正式 APK ↔ 原 Go/Rust 接线与 Actions Host 验证

2026-11-18 用户明确要求**不做模拟网卡绑定测试、不做真机测试**；优先把签名 ARM64 APK 与原 Go/Rust 主程序、RootService 生命周期的接线完成，并在 Actions 进行可信源码/编译/签名/资产/接口验证。这是当前唯一主动施工切片，**不改变**前述 hosted x86 网络环境 `ENV_BLOCKED_NETWORK_PATH` 的事实。不启动 x86 KVM/KSU/TAP guest、不操作实体 Android 或用户服务器、不构造伪 SYNACK/TLS 代替真联机。

生产 RootService 的原 Go argv 由**同一个**无 Android/网络运行依赖的纯 Java 类装配，Host JVM 执行真实生产代码的 IPv4/域名、CA、Normal/off、protected auto-IP、外层1460B、单/多/全 App UID、secret-file paths 和拒绝错误输入等用例；逐一对应原 Go CLI 注册 flags。官方签名 APK 构建后，对真实 `classes.dex`、同 SOURCE 的 arm64 Go ELF / Rust `.so` SHA256、Bionic ABI、原生动态链接和源锁做验证，上传限定枚举的 `wiring-receipt.json`。保留现有 RootService→su→root-only ELF stage/真实 owner token/原 Go exec/Rust M4/原 Stop/标准 TLS，不以 Host 工具替代数据面。

Actions **默认**执行 Host、源锁原生双 ABI 构建、ARM64 APK 签名和独立 Linux oracle；x86 KSU Native、D2-S1、TAP guest 必须显式手工 `workflow_dispatch` 才运行，本次不选择。任何 BUILD/WIRING PASS 都不等于 Android ROOT、物理网络、FakeTCP SYNACK、TLS认证/32租约、Rust M4 真 TCP/UDP 或 owned Stop 的设备执行；本批上述运行项记 `NOT_RUN`，A25 的历史实测状态仍保持。

### A27 — App IPv4 default, server IPv4 exemption and bounded diagnostics

User requested an honest check of default whole-phone routing, explicit
server-IP bypass, and efficient log export for future phone debugging,
without simulated NIC binding or real phone testing. The default
currently captures only ordinary App IPv4 UIDs in 20 user profiles,
excluding controller/KSU Manager; it is not full system, IPv6, DNS,
CLAT or hotspot coverage. Updated Android UI reports exact limits.

Original Android Go now supplies its real server IPv4 (post-physical
DNS bootstrap where applicable) to the all-app route journal. The
owned private table 19842 adds a host /32 THROW exception with strict
readback BEFORE any App UID routing rule; failures roll back precisely
and never touch the system default route. The v4 journal supports
exact-owner recovery from older v3. Throw means private WBD TUN bypass,
not a verified later Android netd physical route. Optional handpicked
App UID modes are NOT yet destination-exception-qualified.

APK includes user-initiated Android system document export of an
allowlisted, bounded original-Root stage report (source/API, time, fixed
enum, last stage, private FIB bypass stage). No raw native stdout,
logcat, server IP, account, credentials, UID list, payload or root
journal goes into that file. The exporter needs no Root or network.
Go Host FIB fake runner checks bypass before UID, invalid server,
foreign modifications, exact Stop and v3 recovery; Host Java tests
production export behavior and signed APK DEX. All new-source genuine
Android network, TLS, data and physical exception status NOT_RUN.

### A28｜2026-11-19 按用户要求把 main 最新代码、功能卡及历史整合进独立实验分支

基线：实验分支 `cd6207bab1eb624f8f5b51bdec06854fbee77076`、`main` `46a756df1114aecda8dc2d5d259a5cbb4c9a909f`、共同祖先 `0e57cab2d53e2c95962eb673050fa54695fd3665`。main 独立266个提交、实验独立244个提交。用**双父非强推** merge commit 完整纳入 main Git DAG；保留 main 功能源码及 `docs/devlog/M0/`、`docs/evidence/M0/`、全部更新的功能卡、TLS 规范、decisions/prompts、main Actions/工具/构建工作流以及 Android 实验独有历史，不截断原有旧 FAIL/NOT_RUN。

按共同祖先逐文件审计，交叉改动恰有7个：`crates/wbd-engine/src/{lib.rs,v4_embedded_go.rs,v4_owner_crypto.rs}`、`r0/go_overlay/internal/realityfront/{bridge_v4_embedded_linux.go,bridge_v4_linux_client_product.go}`、`r0/go_overlay/internal/v4productcli/linux.go` 与 `android/README.md`。三方行级合并同时保留 main 的 Rust 32 owner/lane 上限、Linux 原Go服务器 64 冷关联/8 有限 Decoy、短 routeKey v2 KDF/0600 cache、Linux NAT interface local IPv4 自动识别、受认证 Normal 启动 padding 和安全 TLS 契约，以及实验 Android 的真正物理 Network handle、原始 FakeTCP、Bionic TUN/RAW、UID 私有表 `throw server/32`、Rust M4/Stop、限枚举导出。main 新功能在 Linux/Windows 的 PASS **不向 Android 继承资质**；Android 依然 Normal/off、密钥 UI 仅原 64hex，短 Key Android helper 仍 `NOT_WIRED`，无 Fixed/Game、系统 DNS/IPv6 的新许可。若代码合并与现有原生编译互斥，不通过改文件名/偷换入口/虚构 E2E 绿灯解决。

在**同一合并 SOURCE** 的 CI 需至少检查 rust/cargo、原Go Host 和原 Linux server、signed ARM64 APK 与 Bionic ELF/DEX/接口/脱敏导出、main feature catalog、main 治理回归。x86 Android KSU/TAP guest 均显式手工 opt-in，本轮不跑模拟网卡/真机；用户设备/服务器不动，PR #36 保持 Draft 不合 main。合并后所有旧SOURCE证据保留，新增 SOURCE 的真机联网/M4/应用TCP UDP/Stop 始终 `NOT_RUN`。

### A29｜2026-11-19 新版 Android Root Lite v2（用户授权做简版安装测试 APK）

从已真实双父同步 main 的实验分支 `6de1d62aecd31c1c78f23577819cc9549754fe00` 出发，原 [Actions #44466332473](https://github.com/lly8666/wbd-next/actions/runs/44466332473) 11 SUCCESS + 4 SKIPPED（Host 原 Linux oracle、Bionic Go/Rust、签名 ARM64 Root APK）；真机网络/M4/Stop仍未执行。新版只将适合 Android 冷层的 main H2208 **8..32 ASCII 英数字 short RouteKey v2** 引入 Root Activity，沿 main Go/Kotlin相同 PBKDF2-HMAC-SHA256 4096/domain salt 派生原 32B、持久私有 noBackup AtomicFile/HMAC 0600 缓存，复用老64hex输入及原 Go `--route-key-hex-file`，不增线上 wire/协议/认证轮次或明文密钥 Intent/argv。新UI标 Lite，进阶 Root自检折叠，保留普通App默认IPv4、单App可选、服务器/32 THROW/UID precise recovery/SAF脱敏导出、Normal/off原Go/Rust、原Linux server。全 App 权限不自动放大；用户首次测试建议手动只选一个 App。

不开放 main Linux Decoy/NAT/padding、Windows GUI、Game2/4、Fixed/Auto。先做 Host KDF主线同源3向量/缓存负例与原Go CLI 32B file、同 SOURCE Rust Bionic/Go ABI/原Linux oracle、签名 APK 生产 DEX/原ELF/SHAs + feature catalog。CI 的原 APK 同内容增加直观 Lite 文件别名，每次随机 debug 签名同包名不能覆盖旧版，先Stop+路由检查再卸载。未单独授权的实体 Android、个人服务器和网络设备与重复 KSU/TAP guest 继续不运行；真正 SYNACK/TLS/32租约/M4/双向业务/owned Stop仍NOT_RUN。任何新 CI 失败不隐瞒。



### A30｜API36 用户真实 EXIT_1/PRE_TUN 的 Root/原 Go 早期启动诊断

用户自行运行签名 Root Lite v2 SOURCE `6bcdbc6c7c27b71a8ea47c25f8385cd177daa985`，上传的 V1 允许列表报告：Android API36，Root su 子进程 1795106883788ms 启动，1795106884129ms 非零退出，约 **341ms**；记录了 `NATIVE_SOURCE_VERIFIED` / `ROOT_GRANT_REQUESTED` / `ROOT_PROCESS_LAUNCHED` / `ROOT_EXIT_BEFORE_GO_RAW`，没有 TUN/RAW 里程碑。界面退出码 **1**。**ProcessBuilder.start 成功不等于 su 授 root、shell 真执行、原 Go ELF 被加载；`OWNER_CLEANUP_FINISHED` 仅 Java finally 清除暂存文件，不等同原内核 route/Stop 已清理。** 全普通 App IPv4 只是启动选项；此时未得到 UID 安装证据，server /32 throw NOT_OBSERVED 不表明排除规则异常。真实故障原因尚未分类，不推定 TLS/key/服务器故障。

A30 唯一范围：保持 Root 原私有目录/owner PID/执行/Stop 与原 Go/Rust 协议不变，在真正的 root `su -c` shell 打印严格常量阶段：进入、EUID0校验、0700根目录、旧owner PID守卫、原始Go/Rust文件复制、owner PID写入、Go exec请求。原 Bionic Go `Run` 仅在Android client 打印固定入口、参数解析被拒或通过、物理接口存在及 TUN open前/后阶段（均非TLS/业务资格）。Android Service 只对白名单精确锚点记录 enum+毫秒，SAF TXT继续过滤一切 stdout原文、errno/IP/用户名/账号/密码/密钥/PID；正常里程碑仍以原 TUN TxQLen 和真实 SYNACK/TLS/lease/M4/Stop 为准。报告只有在同一session有 `START_DIAGNOSTIC_STAGES_V2` 才对非零退出按最后观察阶段分类；历史V1仍保留 `ROOT_PROCESS_BEFORE_RAW_OR_GRANT_UNPROVEN`。Host 复现用户V1与14类V2固定阶段，实际源锁ARM64构建和Linux oracle/功能卡门验证。不得在聊天中擅自运行个人手机/服务器或KSU/TAP guest。新debug签名需用户自行保存旧TXT、确认无原生会话/UID路由遗留后再安装；不要无证明地删除 owner.pid 或 flush ip rules。

### A31｜API36 原 Go 冷参数 parse 真拒绝：13类脱敏细分

用户自行运行签名 A30 SOURCE `e85a19883151a101f9dbc12848a6ab6dec3e0780`，22项固定事件已证明 `ROOT_SHELL_ROOT_UID_VERIFIED`、root私有目录/owner检查/原生文件stage、`ORIGINAL_GO_ENTRY`(1795109008277ms) 后2ms `ORIGINAL_GO_ARGS_REJECTED`，随即 `ROOT_PROCESS_EXIT_1`。**真实Root与原 ARM64 Go ELF均已执行，Go `parse(role,args)` 拒绝，网卡/TUN/RAW均未到达**。全普通App与服务器/32 readback只是输入范围、并非内核代理已经生效。旧数据不足以分辨密码/routeKey私有文件、身份ID、CN8503规则、全App排除ID、peer/CA/策略等哪项实际失败。

A31保持原 Go`parse`返回值/文件权限/安全拒绝、TLS/证书/路由/Stop和所有原协议**不变**，只在实际原 Go Android client `parse` 非零返回点用固定分类函数将错误归于13类并输出 `V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=ENUM`，不输出raw err/文件路径/用户名/密码/IP/密钥。原 RootService严格锚定映射封闭事件枚举和时间戳，SAF TXT在泛拒绝之后标最后已证原因。Host原Go类别+敏感内容反例、Java13类/旧A30报告、ARM64签名原Go/Rust、原Linux oracle及feature catalog负责验收；不模拟网卡、不运行KSU/TAP guest或私有手机服务器。Android真机测试仍是用户自主操作，拿到下一份固定TXT才做针对性修正。之前真正客户端的TUN函数没有被删除，不能凭parse失败调整MTU/TLS或内核路由。

### A32｜API36 PASSWORD_FILE：Android MODE_PRIVATE 权限与原 Go 0600 不兼容

用户自己安装 A31 SOURCE `ec9d40fab0442fa6e5efaf38adc2ded2649913ff`，23条固定事件证明 KernelSU EUID0、原Bionic Go启动，`ORIGINAL_GO_PARSE_PASSWORD_FILE` 导致 exit1，尚未到物理网卡/TUN/RAW/原TLS。深入审查发现客户端高概率真实 BUG：Android旧 `RootClientActivity.privateText` 用 `openFileOutput(name,Context.MODE_PRIVATE)`，未复核文件权限；AOSP `ContextImpl.setFilePermissionsFromMode` 在默认路径包含 `S_IRGRP|S_IWGRP`，即可能生成 0660。原 Go `readPrivateArgFile` 绝不接受组/其他权限 `st.Mode().Perm()&0077!=0`，0660 会拒绝为 `PASSWORD_FILE`。同样写入口用于下一关 RouteKey hex，因此不只修密码。手机没有上传实际 stat，故源码不兼容可确认、设备具体 mode 仍待复测。

A32 **直接修 App 写方**而非放宽原Go：3种固定私有文件（密码、派生32B route-key hex、可选TLS CA）改为 `Os.open(...O_NOFOLLOW|O_CLOEXEC|O_CREAT|O_TRUNC,0600)`、对同fd `fchmod(0600)` / sync / `fstat` 检查普通文件、App UID、单一硬链接、精确0600、合法大小。生产 `RootClientService` 在执行任何 `su` 前 `lstat` 二次核验，固定 `APP_PRIVATE_CREDENTIALS_0600_VERIFIED/UNSAFE` 事件只记录时间/枚举，不泄露密码/IP/UID/路径。原 Go O_NOFOLLOW/0600拒绝与标准TLS/认证/Rust M4/服务器/32私表、精确owned Stop仍原样。已签名CN文件原本 chmod0600，安装ID由原Go负责0600，不引入root长期秘密拷贝。新宿主正反例覆盖真实POSIX 0660/0640/0604、错owner、符/硬链接、坏长度和RouteKey/CA，并在原Go回归中加入两种0660拒绝。只按新SOURCE Actions签名APK/Go Rust/Linux oracle/Feature catalog验Host，不运行KSU guest/模拟NIC或用户真机；**BUILD_PASS绝不等于用户手机已修复**。请用户自行保全旧TXT/安全Stop后安装新测试版，单次Start导出新TXT验证。

### A33｜API36 A32实机已达TUN/RAW/SYNACK候选，下一轮同时覆盖TLS及认证失败分段

用户新提供SOURCE `3e2c0cfd7a9dff5598f1c7a33ab6eaaff9e3d67b` API36固定29事件：0600 readback、原Go ARGS_ACCEPTED、真TUN/RAW、SYN sendto、原raw reader SYNACK候选（MSS合法）均 OBSERVED；约15秒后exit1。V2报告误把TUN当最后阶段已由A33修正；SYNACK打印发生在原ClientAssociation.HandleSegment之前，不能冒充原Association Established，更不能冒称对端原Linux server RAW SYNACK、标准TLS/认证/32租约。15秒只与TLS候选超时预算吻合，根因仍 NOT_PROVEN。

A33仅在原Go Android冷路径增加真实Association Established、原Rust产品构造、真TLS attempted/verified/固定失败类别、保护Admission request write/reply及verify等marker；Java只允许有界固定枚举，Host Go classifier/Java V2阶段优先级/锚定反例与同源正式ARM64 APK+原Linux oracle。Android实机、联网服务器、KSU/TAP不自动启动。下一份用户自测安全TXT在同一次有界启动中可定位多个临界点；没有合格环境/授权不得执行外部业务闭环。

### A34｜API36真FakeTCP Established，TLS约15秒OTHER：原数据首收发诊断

用户自行提供 A33 SOURCE `f8031ef1cf2f15e2769208d76bf2b072275b6084` 真机 33事件：原Go/0600/TUN/RAW/SYNACK候选、原Association Established与TLS Attempted OBSERVED，14,997ms后 OTHER/exit1。原Linux服务端身份、原ClientHello对端实际接收、真TLS/认证/租约、M4/Stop仍未证。A34仅观察原ClientAssociation原sendto成功后的首非空Bootstrap TX、严格4元组的AF_PACKET peer payload RX及失败时对应本会话未观察到的方向/已有RTO。补明确的原BootstrapTimeout/OS timeout/cancelled/closed；未知错误恰逢预算耗尽只记DEADLINE_ELAPSED_OTHER，不冒称根因。无新传输/伪ClientHello/密钥或错误正文入TXT，不放宽标准TLS/认证、原Network/路由/Stop。先以用户自主真机安全TXT判TX/RX，再取得同SOURCE原Linux服务端RAW/TLS收据，不先扩DNS/全App。

### D2b→D2c｜网络资格通过后的真 TLS/租约与业务闭环

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

### A32 source-locked验收收尾（仅功能卡/文档，不改变APK）

`3e2c0cfd7a9dff5598f1c7a33ab6eaaff9e3d67b` [Actions #44587763808](https://github.com/lly8666/wbd-next/actions/runs/44587763808) **11 SUCCESS/4 SKIPPED**，同SOURCE ARM64原Go/Rust ELF、Linux原Go server、真实签名APK、POSIX 0600/0660权限反例以及保护型诊断Host PASS；工件[#14563460168](https://github.com/lly8666/wbd-next/actions/runs/44587763808/artifacts/14563460168) SHA256 `5a211659dfe2341d4bc5a2b44ddfcf148386104f023ba8317bf58e81729deb95`。之前第1次Native Build Host断言变量NameError FAIL、第2次CI-only提交缺功能卡导致治理FAIL，都在同一A32 devlog保留；最后纯文档功能卡提交修治理，不重跑产品构建。Android真机权限/解析/TUN/业务/Stop仍NOT_RUN。
