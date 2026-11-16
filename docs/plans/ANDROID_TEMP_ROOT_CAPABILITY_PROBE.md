# Android 临时 root 能力探测计划

状态：**PLANNED，尚无 Android 兼容/连接/性能 PASS**。2026-11-16 用户授权独立实验；分支 `experiment/android-temp-root-probe`，起点 main `3b2c6e267d6b7047f334c450bcbc2c37bdbe4a19`。接续入口：[固定提示词](../prompts/ANDROID_TEMP_ROOT_PROBE.md)，登记：[功能卡](../features/entries/android-temp-root-probe.json)。

## 1. 先回答可行性，不先造完整客户端

目标：查明已取得临时 root 的手机，能否以小幅、可撤销的运行期改动支持：手机应用入隧道、独立开关的 Wi-Fi 热点/USB 网络共享入隧道、Wi-Fi/蜂窝切换、低频保活与低空闲开销。**不使用 VpnService，不要求系统 VPN 钥匙标志；普通前台服务通知与 root 授权提示不承诺隐藏。**

不开发提权/解锁/root 安装工具，不刷机、不改 boot/system、不安装常驻模块、不关闭 SELinux。没有现成 root 就报告条件不满足。这里的“临时”指我们不增加永久系统改动，不保证第三方 root 工具自身无永久改动。

Rust 探针应证明“实际操作成功”，不是只查 `uid=0`。Android 版本、内核配置、SELinux 域、root 管理器、厂商 netd/tethering 模块共同决定结果。Actions 只能证明特定镜像/权限路径；真机能力另列。探测完成即提交结论，不扩张成 Android 完整产品开发。

## 2. 复用边界与最低成本实现

- 原产品 FEC/加密/机会式重传/生命周期与无 HOL 语义保持不动。未来 Android 仅增加 OS 适配和冷控制，不能复制出 Android 专用协议核心。
- 当前 `crates/wbd-platform/src/linux_raw_carrier.rs` 受 Linux GNU/musl 条件编译限制，**Linux ARM64 已通过不等于 Android/Bionic 已可用**。本轮独立探针使用 NDK ABI，检查相同 syscall/权限需求，不直接取消产品平台门。
- 建议独立 `experiments/android-root-probe/` Rust workspace：`std + libc + serde_json`，同步 `poll/epoll`、固定缓冲、一次性 JSON 汇总。没有 Tokio/Go 常驻层、逐包 shell、轮询守护或新通用框架。规则安装时少量调用现有 `ip`/netfilter 工具可以接受；缺工具先给出结论，不引入完整用户态网络栈。
- 可配一个独立的薄 Kotlin 测试 APK，只负责应用 UID、root 请求、系统网络回调、进程启动/停止与前台服务可行性；不搬原 VpnService 占位壳，不走 JNI 逐包回调。`minSdk=28`，编译/target 采用开工时最新稳定 SDK，不能降低 target 来掩盖权限限制。
- 探针 NDK 构建 `aarch64-linux-android`（真机）和 `x86_64-linux-android`（AVD）。按官方镜像实际 ABI 补必要目标；ARM64 包同时检查 4KiB/16KiB page-size 装载兼容，不把 x86 模拟器结果当 ARM 指令加速证据。
- 默认 `inspect` 只读；显式 `exercise` 才创建临时对象。所有子进程/操作有截止时间；空闲等待事件，无毫秒轮询、无持续 CPU 采样、无常驻 wake lock。阻塞等待用户 root 授权可到 30 秒，其余单项通常 3 秒，单次探测预算 120 秒，可有依据调整。

## 3. 必须逐项探测的能力

每项输出：实际执行身份/SELinux context、尝试的操作、返回值/errno、观察证据、是否产生改动及清理结果。不可把权限名称存在当操作成功。

| 能力 | 关键条件 | 最小真实验证与结论边界 |
|---|---|---|
| 应用获得授权 | 普通 app → 已安装的 `su` 或受支持 root 启动方式 | 记录 app UID 与子进程实际 UID/GID、cap effective/permitted/bounding、SELinux 域。分别记录无授权/拒绝/授权；`adb root` 是另一条路径，不能顶替 app→su PASS。|
| TUN | `/dev/tun` 或 `/dev/net/tun`、`TUNSETIFF`、通常需 `CAP_NET_ADMIN` 与 SELinux 允许 | 创建非持久 owned TUN，设置 IPv4/MTU并读回，真实读写少量合法 IP 包，关闭 fd 后回收。只 open 设备不算 PASS。|
| 外层 raw | `CAP_NET_RAW`、SELinux、内核 socket 支持 | 以产品需要的 raw IPv4/TCP 方式真实收发受控报文，核对出口、checksum、内核 RST 行为；AF_PACKET 仅在确需时探测。创建 socket 成功不等于蜂窝路径可用。|
| 缓冲与过滤 | 当前 socket 选项、BPF/过滤接口权限 | 设定并读回小范围 `SO_RCVBUF`，明确内核返回值口径；记录内核上限和过滤可用性，不自动扩大全机 sysctl。|
| 策略路由 | `CAP_NET_ADMIN`、netlink、netd fwmark/rule 优先级 | 读取现有规则，选择无冲突 owned 表/mark 位，在受控流量中验证“应用包→TUN，外层连接→真实网络”。不可覆写完整 Android fwmark，不按整个 root UID 放行。|
| netfilter/NAT | 实际 iptables/nft 后端、内核 hook、conntrack/NAT 支持 | 少量专用链/精确 tuple 规则添加、读回、命中、删除；验证新旧规则不冲突。不要同时上两套防火墙后端。系统不提供的能力如实标记。|
| 转发与租约 | IP forwarding、forward hook、SNAT/conntrack | 受控两下游源地址→owned TUN，SNAT到一个合法隧道租约，验证反向还原。**不放松服务端 source /32 校验**。模拟 L3 转发不等于真实热点/USB PASS。|
| DNS/IPv6 | UDP/TCP 53 路由、DNS策略、IPv6入口控制 | 测本机和转发的 UDP/TCP DNS，不只测53/UDP；服务端域名 bootstrap 走底层，不能递归进未建隧道。只阻断被接管的内层 IPv6/AAAA；不全局禁物理 IPv6，避免破坏蜂窝 IPv6-only、CLAT、IMS。Private DNS/DoH 另列边界。|
| 网络切换 | 普通应用 `ACCESS_NETWORK_STATE`/网络回调，底层 socket 选网能力 | 记录 Network/ifindex/address/MTU 的变化；验证控制面 socket 与 raw 都能选同一底层、避免回环。API能调用不等于 raw 绑定成功，必须看实际出口。|
| 后台运行 | 当前 target 对前台服务/通知的要求、root子进程执行与存活条件 | 普通 app 身份启动薄壳；读回服务类型和生命周期。不要用 shell 身份、低 target、关闭省电来冒充普通启动可行。独立报告原生文件执行位置/SELinux限制。|
| 无 VPN 标志 | 不注册 VpnService、不建立系统 VPN 网络 | 检查 APK 清单和系统网络状态，无 VPN transport；真实 OEM 状态栏最后真机确认。前台通知仍可出现。|
| 回收 | owned 句柄/规则/路由、可用 root 权限 | 正常停机、子进程异常退出、重复启动、拒绝授权均有界；只清理自有对象，不清空整机规则。|

`CAP_SYS_ADMIN`/网络 namespace 仅可能用于夹具，不是产品最低要求；真机没有 namespace 能力也应继续判断 TUN/raw/路由。`WRITE_SECURE_SETTINGS`、system UID、全局 permissive 也不是默认依赖。Android 沙盒不允许读取的信息用 `UNAVAILABLE`，不要为了日志扩大权限。

## 4. 热点、USB、切网必须额外查的坑

1. **共享使用系统原有热点/USB/DHCP。** 分别开关“接管手机”“接管 Wi-Fi 共享”“接管 USB 共享”。本轮不实现打开热点/USB的厂商私有API，不另跑 DHCP/hostapd；先要求用户打开系统共享。接口按类型、地址/路由及实际入口识别，不能写死 `wlan0/rndis0/rmnet0`。
2. **硬件/eBPF tethering offload 可能绕过普通 hook。** 先只读识别，再以真实下游业务比较入口/TUN/出口计数；不能只看首个 SYN 命中。现有通路接不住就报告该功能受限。仅当确需且能读回/恢复时，真机专项可评估临时禁用 offload；不将任何单个 settings key 当所有 ROM 通用方法，也不默认永久关闭系统加速。
3. **手机业务与共享业务合并到既有会话/租约。** 优先内核 SNAT/conntrack；不要每台下游另造隧道或在用户态逐连接代理 TCP。共享关闭后恢复原系统共享路径；隧道临时重连期间如何保留/暂停所选业务须明确，不静默改成直连。
4. **Wi-Fi↔蜂窝是新路径建链。** 未来复用 [PLAN028 §4.1–4.2](../decisions/M0-PLAN028-SESSION-CONFIG-20261102.md) 的通知合并、重认证、代际隔离、地址租约和 MTU 更新。可重叠时 A→A+B→B，旧网络已消失就直接重建；不能承诺旧 TCP 五元组无缝迁移。休眠中网络变化不应自行唤醒隧道。
5. **IPv6-only 蜂窝、CLAT与 AP+STA 是条件能力。** 必须确认 raw IPv4 能否经过当前 CLAT/真实出口；否则报告需要适配而不是借普通 TCP 成功冒充可用。同一 Wi-Fi 同时上网和开热点取决于硬件/ROM，Actions不能证明。
6. **MTU与电量不重造一套策略。** 消费 [MTU_CONTRACT](../architecture/MTU_CONTRACT.md) 的外层默认1460与Rust内层预算；探针只验证设置/读回与边界包。共享客户端常见1500，未来仍需现有超MTU处理、TCP MSS及ICMP/PMTU；MSS不能修复UDP或已建立TCP。固定FEC/off可沿用关闭自动档质量报告的现有语义；保活、dead、真实业务idle分离，热点评估也算真实业务。只延长 keepalive 不能证明蜂窝耗电下降或 NAT 长期有效。
7. **清理不是把全机恢复到旧快照。** 记 owned 对象和修改前值，撤销自己的增量；全局参数只在仍为本次设置值时恢复，避免覆盖系统同期变更。必要守护只阻塞等子进程退出，不周期巡检。root撤销未必撤销已运行进程权限；同时杀掉守护和工作进程时不能承诺自动清理，报告残留并提供下一次有权限启动时的 owned 恢复。

## 5. Actions 先行：Android 9 到最新稳定版

2026-11-16 官方资料确认最新稳定大版本为 **Android 17/API37**。开工再核官方版本与 `sdkmanager --list`，记录镜像实际 API/revision/ABI；不凭名称猜可用性。稳定新版本自动纳入，预览版单列、不混稳定资格。每个系统主版本必列一行，12L也列；不要求穷举每个安全补丁/QPR。

| Android | API | 重点 |
|---|---|---|
| 9 | 28 | 最低版本、NDK/系统命令兼容 |
| 10 | 29 | 应用执行路径与后台差异 |
| 11 | 30 | tethering模块/eBPF边界 |
| 12 | 31 | 前台启动限制与转发变化 |
| 12L | 32 | 独立镜像回归 |
| 13 | 33 | 通知/应用权限差异 |
| 14 | 34 | 前台服务类型/新target行为 |
| 15 | 35 | 16KiB装载、网络模块差异 |
| 16 | 36 | 最新稳定系统行为回归 |
| 17 | 37 | 最新稳定target与权限上界 |

### 实施顺序

**A. 一次构建、多次复用。** 新建独立 `android-root-probe-build.yml`，固定 Rust/NDK/SDK依赖，产出各 ABI Rust探针、薄壳APK、SOURCE/manifest/SHA256。不反复编译整个WBD。16KiB目标至少有ELF检查；实际16KiB系统装载若镜像不可用就留真机待验，不从检查推导运行PASS。

**B. API28和最新稳定版先作两条独立 canary。** `android-root-probe-case.yml` 输入 API、镜像、构建artifact/hash、case；Actions运行名含 `android-root-probe|apiXX|case|SOURCE`。一个Action只运行一个模拟器、一条有界探测场景；场景内部顺序做只读→操作→清理，禁止同VM同时压多台AVD。

先确认 `/dev/kvm`、实际硬件加速和镜像可启动；无KVM不硬跑极慢软件仿真。使用官方可root AOSP开发镜像并验证 `adb root`，**Google Play release镜像不能用“无法adb root”证明该Android版本不支持临时root**。SELinux保持Enforcing；镜像本身是Permissive的结果单列，不计入Enforcing资格。

**C. canary通过后，其余API独立Actions并行，默认最多3条。** 不用一条workflow扇出多个测量job。缓存SDK下载/构建产物，缓存key包含镜像revision、emulator与工具版本；每个场景全新AVD数据，不能复用改过路由的快照。每条约20分钟总上限、boot约5分钟、探针通常120秒，依据可证实基础设施情况调整，不靠反复放大超时刷绿。

同API先普通app未提权负例，再开发镜像root操作正例。真实 app→su 若镜像无root管理器就列 `NOT_RUN`；可以提供**明确标注的CI专用root桥**检查IPC/生命周期，但它不是实际su授权证据，不进入交付APK。额外搭root管理器不是本轮必跑项。

**D. 权限可用后再做短数据探测。** 每方向上限1Mbps、5–10秒，小/近MTU TCP、UDP与少量ICMP；两个模拟下游地址检查SNAT往返，指定流量的DNS/IPv6策略，重复Start/Stop及一次异常退出。若namespace/veth不可用改用owned TUN与受控对端验证可达范围，缺转发能力不冒充热点通过。网络事件模拟只证明回调/重绑机制，蜂窝切网仍未测。无需FEC/Game弱网大矩阵，更不测试500Mbps。

**E. 资源/失败分类。** 保存host CPU/内存/PSI和探针自身 CPU-time/RSS/唤醒、操作耗时；不能把模拟器进程CPU当手机运行成本。无root/镜像缺失/内核不支持/环境容量不足分别报告，不判代码通过或强行判产品失败。定位后修一次可重复问题再跑受影响API；已有通过且无影响的版本不重测。已知容量不足停止更重同族，最多一次有理由的基础设施重试。

Android镜像不提供真Wi-Fi/蜂窝基带、USB设备共享链路和OEM加速器。**全部API模拟器绿也不能填“Android9–17所有手机兼容”。**

## 6. 证据、验收与停止点

输出一份紧凑兼容表和机器可读JSON。最少字段：SOURCE/artifact hash、API/release/ABI/page_size/kernel、镜像revision、`execution_path`（app/adb-shell/adb-root/app-su）、UID/cap/SELinux、各能力结果/errno/证据、创建对象/清理结果、必要资源数据、下一步。路径/地址按用途去标识化，不上传手机序列号、SSID、凭据或业务正文；默认不存大pcap，删除本次owned镜像原始临时文件，保留摘要与hash。

探测结果用 `SUPPORTED_IN_SCOPE / PERMISSION_DENIED / UNAVAILABLE / ENV_BLOCKED / FAIL / NOT_RUN`，含明确scope；“正确识别不支持”可以是工具逻辑PASS，不能把该能力填SUPPORTED。代码缺陷/清理失败让测试失败；能力不足正常产报告，但aggregate不能把它归入全版本可用。功能卡沿用仓库已有验证状态，不创造不兼容枚举。

交付条件：

1. Android9到最新稳定版每行有真实Actions结果或具体未测原因，至少最低/最高可运行镜像有真实positive；做不到则明确本轮受阻，不能宣称完成全范围验收。
2. TUN/raw/路由/NAT/网络绑定/后台/root路径分别给“可复用、需薄适配、不支持”的结论。先满足手机基础功能；某ROM热点受限不牵连所有功能。
3. 操作路径正常与异常清理有证据，且无全局规则清空/系统永久修改；实际变更残留必须可定位。
4. 有低成本真机后续清单：用户手机 app→su Enforcing、ARM64 raw真实出口、Wi-Fi/蜂窝各一次切换、真实热点与USB各一个下游、offload旁路检测、短息屏/Doze和退出恢复。功耗、长NAT保活与运营商IPv6-only另作条件项，**本次不擅自部署真机**。

阶段完成后给一个决定：可进入Android薄壳开发、仅支持受限功能、或被某项系统能力阻断。列剩余工程量；不要接着扩到完整VPN/桌面功能移植。未来实际接线仍须标准TLS、同源真实数据通路、无HOL、MTU、地址隔离和owned Stop，探针不能替代这些验收。

## 7. 持续交接与资料

未来开发在本分支独立施工，仅改探针/薄测试壳/专属workflow及本任务文档，复用仓库Actions约束；不占M0身份、不改main registry/cursor、不取消别人的run。接手先读本计划、提示词、功能卡、最近一份 `docs/devlog/android-root-probe/` 与其Actions；发现聊天中断先补实绩再继续，不扫描整仓历史。每个完成包更新短日志和卡片，记录当前SOURCE、结果、阻塞与唯一下一步；方案阶段记录不代表功能已实现。

关键官方依据（开工时核版本）：

- [Android17稳定版发布](https://android-developers.googleblog.com/2026/06/Android-17.html)、[API37 SDK](https://developer.android.com/about/versions/17/setup-sdk)。
- [AVD镜像/root差异](https://developer.android.com/studio/run/managing-avds)、[模拟器硬件加速](https://developer.android.com/studio/run/emulator-acceleration)。
- [SELinux也约束root](https://source.android.com/docs/security/features/selinux)、[前台服务要求](https://developer.android.com/develop/background-work/services/fgs)。
- [Tethering模块](https://source.android.com/docs/core/ota/modular-system/tethering)、[硬件offload](https://source.android.com/docs/core/data/tethering-offload)、[Wi-Fi STA/AP并存](https://source.android.com/docs/core/connect/wifi-sta-ap-concurrency)。
- [Android网络回调](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)、[NDK网络绑定](https://developer.android.com/ndk/reference/group/networking)。
