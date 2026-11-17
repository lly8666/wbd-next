# Android Root 原生客户端｜永久接续提示词（2026-11-17，Actions-first 行为等价）

## 权限与阅读入口
仅在 `lly8666/wbd-next` 的 `experiment/android-temp-root-probe` 开发，最终通过已有 Draft PR #36 → main，不直接修改 main/M0 registry/cursor。用户已授权正式客户端施工及 GitHub Actions 测试，**所有软件功能先 Actions 实测、整体完工后再请求实体设备专门授权**；本授权不包含操作/刷写真机、购买云资源。每次开始先读取最新远端分支及 main HEAD、PR、在途/失败 Actions、`AGENTS.md`、`PROJECT_CHARTER.md`、[现行方案](../plans/ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md) 尤其 `8.0`、[功能卡](../features/entries/android-root-native-client.json) 与 `docs/devlog/android-root-probe/` 的最新日志。不要把历史 SHA 冒充 HEAD；无本地 worktree 不宣称检查未提交改动。

## 事实证据与 Root 不能偷换的边界
- [旧 KSU Action43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528)，SOURCE `09a6a7e5f8aef5c3b38abb262655561ca89e5f9a`：Android16 **x86_64** AVD 普通 targetSdk37 诊断 App 经真实 KernelSU3.3.1 Manager 授权 `su`，确认 UID0、CapEff NET_ADMIN/NET_RAW、SELinux `u:r:ksu:s0`（系统 Enforcing）及真实 TUN/RAW/UID规则、App UDP/TCP及隔离 DNS/恢复；**没有执行 `adb root`，没有与 `adb root` 做配对对照**，只能证明 KSU 单侧范围内能力；不是 ARM64 正式 WBD。
- [Action44041601960](https://github.com/lly8666/wbd-next/actions/runs/44041601960)，SOURCE `bb30ed3d864460dc22af67aaade1d17c47182c58`：ARM64 Bionic 原Go/Rust完整 ELF 和正式 Root APK `BUILD_PASS`，同源原 Linux client↔server 真实TLS/自动租约/Rust M4双向UDP/Stop `LINUX_ORACLE_PASS`，**不是 Android↔Linux 实连**。
- [Action44042235770](https://github.com/lly8666/wbd-next/actions/runs/44042235770)，SOURCE `37f1b8abc77cc878d245b5b6dd1995c435ba259e`：四个 native/app/Linux oracle jobs PASS；macOS ARM64 Android16 AOSP 模拟器 QEMU 线程挂死、ADB 不上线，约10分钟后 guest job FAIL。对 Android 运行而言 `ENV_BLOCKED`，真实 APK 安装/原生联机 `NOT_RUN`，不能标成应用回归 FAIL。
- `adb root` 使 adbd/shell 以调试权限运行，**不等于普通 App 能调用 `su -c`**。KernelSU Root Profile 可改变 UID/GID、groups、Capabilities、SELinux 域；即使双方 `uid=0` 也不能证明相同访问权限。旧 KSU 的 App→su 成功不能反推 adb-root 等价，亦不能用 adb-root 代替正式 App 的授权闭环。只允许对**相同操作及真实可观察结果**宣称指定范围行为等价，不宣称全面等价。

## Actions 分层门禁，真实软件先行，实体 KSU 最后
- **P0**：同一 SOURCE/manifest/SHA 的 Android ARM64-v8a Bionic 原 Go/Rust/Java APK、16KiB、原 M3 wire oracle，`BUILD_PASS`。
- **P1**：同源 Linux 原 Go/Rust client+server 的标准 TLS、认证、/32租约、真实收发、Stop，`LINUX_ORACLE_PASS`。
- **P2**：**真实 Android16 ARM64 userdebug** guest，允许 `adb root` 仅帮助启动**原 Bionic 正式 native ELF** 做系统原生数据面测试；实际 `ConnectivityManager` 的物理 Network handle→`android_setsocknetwork`、Android netd、TUN/RAW、标准 TLS/原Linux服务器、认证租约、Rust M4双向 TCP/UDP、MTU/Stop 均须真测，成功才 `ANDROID_NATIVE_RUNTIME_PASS`。P2 **不**证明普通 App 自己 `su`。
- **P3**：同 guest **正式签名 APK** 作为普通 App UID 在 `untrusted_app` 下，必须经自己 `ProcessBuilder("su","-c",...)` 获得受控 CI Root provider 的真实授权，不可由 ADB 代启动冒充。核实际子进程 `uid/euid/gid/groups`、`CapEff/CapPrm/CapBnd/NoNewPrivs`、`id -Z`、`getenforce`、net namespace、Root 文件权限、真实 App UID路由/`android_setsocknetwork`、双向 WBD TCP/UDP、owned Stop/故障恢复；全部达标才 `ANDROID_APP_ROOT_E2E_PASS` / `ANDROID_LINUX_E2E_PASS`。CI provider 可以不是 KernelSU，但只证明覆盖操作的行为等价，**KSU兼容性留 P5**。
- **P4**：工作包 A→B→C→D 所有软件可重现场景 Actions 功能门。B 两真实安装 App/包名UID、CN IP域名、统一普通DNS两单endpoint UDP/TCP53及截断、直连/全隧道/分流/跟随、owned安全恢复和规则更新；C 原 FEC/Fixed/Auto/Game、生命周期/切网、MTU、CPU/RSS/p99/idle；D 共享软件路由。不能用合成netns或旧x86证据冒充正式 Android 系统行为。
- **P5**：全部软件功能 Actions 门通过后另行请求用户授权，实体 Android16 ARM64 KernelSU 正式 APK 的 Manager授权/真实网络、Wi-Fi/蜂窝、热点/USB、offload/CLAT、功耗与切网专项。缺测一律 `NOT_RUN_PHYSICAL_FINAL`，不私自合 main。

**环境路线**：首先单独低成本检查真实 ARM64 Linux runner `uname -m=aarch64`、`/dev/kvm`、隔离清理和 Android16 ARM64 **Cuttlefish userdebug** 官方镜像/host package 固定版本。Cuttlefish 是**待准入候选**，不可提前宣称 GitHub Hosted ARM64/macOS 支持 KVM/已可启动；真启动后实查 API36、ABI arm64-v8a、SELinux Enforcing、`sys.boot_completed`、PackageManager/ConnectivityManager/netd、TUN/RAW。无符合条件 runner 就 `ENV_BLOCKED`，可申请自管/具 KVM 的云 ARM64 Actions runner（外部资源需用户另行授权），不能回退 Android x86 或通过增加超时耗费 CI。无真实 P3 不能宣称 A 已正式完成；P2 可先查 ABI、系统调用及协议，B/C纯协议组件也可继续，但正式 App 门禁不放宽。

**对照测试**：若要证明 adb-root 与 KSU/CI su 对某操作等价，固定同一 APK/native SOURCE和相同目标网络/测试输入，分别记录原 App UID/SELinux、Root worker 全 UID/GID/Cap*/NoNewPrivs/SELinux、`SO_MARK`/TUN/RAW/`android_setsocknetwork`、系统 UID FIB及真实 TLS/业务与Stop后readback；发现权限/域/网络差异则记 `NOT_EQUIVALENT_FOR_SCOPE`，缺另一侧证据为 `NOT_PROVEN`。只凭 `uid=0`/`getenforce=Enforcing`/Linux server工作或旧KSU诊断不成立。

## 永久产品红线与唯一下一步
只做 Android arm64-v8a；固定原 Go donor `a7a82db31fe736ffedee330795a3234d358f1984`、原 Go 标准ClientHello/TLS/认证/租约冷代际、共享 Rust M1/M3/M4/PN/AEAD/FEC/MTU/Health/Stop。无 VpnService、FakeIP、Android新协议、逐包 Java/JNI/shell，直连保留内核原 TCP、WBD 才走 TUN；不刷真机、不关 SELinux、不写系统常驻 Root 模块。精确 owned journal/flock/compare-before-restore，禁止破坏 Android netd/全局路由或 root UID 放行。普通DNS只用 CN `223.5.5.5` 物理与隧道 `1.1.1.1`、bootstrap物理、失败不换上游；普通 per-App DNS不造 UID 身份。低频事件式 Network callback，降低空闲唤醒。单 SOURCE/manifest/hash 复用已构建原件，一个独立网络场景一个 Job，保留每次 FAIL/ENV_BLOCKED/NOT_RUN、短 devlog、功能卡和必要证据，不刷孤立小测试；main同步仅原既定窗口，PR保持 Draft。
**当前唯一下一步**：先锁定历史“旧KSU单侧App Root PASS、adb-root对照 NOT_PROVEN”和本次 macOS AVD ENV_BLOCKED；审计 ARM64 KVM/Cuttlefish runner 准入后做 P2 Android原Bionic→Linux 真连接，再做 P3 正式 App→受控 su 真实授权及同业务/Stop；未具备 runner 时继续源锁代码与可在 Linux/NDK 完成的组件证据，不伪装 E2E。
