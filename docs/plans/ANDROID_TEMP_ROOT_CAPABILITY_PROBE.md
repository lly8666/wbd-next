# Android Root 原生客户端适配｜授权施工方案（2026-11-17）

**状态：B2c2c 原Rust M4唯一TX就绪线程已有真实NDK物理DNS UDP53 fd、同TUN IPv4/UDP回包映射和Stop；`android_dns_hijack_ready=false`、`android_dns_physical_ready=false`，直到完整CN8503/物理TCP53/系统Resolver归属同代认证前严禁启用。修正SOURCE `9d902a171764b832b3528b111ce6a371a5feedb2` [Action44108696248](https://github.com/lly8666/wbd-next/actions/runs/44108696248) **10/10 Jobs SUCCESS**（Rust物理/隧道DNS7项真实IPv4报文、ARM64 Bionic Go/Rust ELF、签名APK、原Linux真TLS/租约/M4/Stop oracle）。上一版 `71565fd` [Action44107830995](https://github.com/lly8666/wbd-next/actions/runs/44107830995) 因Host模块测试路径错误FAIL（本身Rust7/7 PASS），原记录保留。Android16 ARM64模拟器 `KVM_NOT_ACCESSIBLE` 真实业务 NOT_RUN，实体KSU P5未授权。** 用户已明确授权从临时 Root 探测转为 Android 原生 WBD 客户端开发；本文件覆盖旧“只探测、不开发完整客户端”的工作边界。唯一施工分支 `experiment/android-temp-root-probe`，最终 PR → main，不直接提交 main/M0 registry/cursor。长期入口：[ANDROID_TEMP_ROOT_PROBE](../prompts/ANDROID_TEMP_ROOT_PROBE.md)；产品卡：[android-root-native-client](../features/entries/android-root-native-client.json)；探针历史卡：[android-temp-root-probe](../features/entries/android-temp-root-probe.json)。历史探针方案保留在 Git 历史和本文件末尾的链接，不再占用产品开发优先级。

## 0. 用户更新：Android 仅 ARM64、较大跨层批次和合理并行

**唯一 Android 目标 ABI 是 `arm64-v8a`**（Rust `aarch64-linux-android` / Go `GOARCH=arm64`）。不再进行 Android x86、x86_64、armeabi-v7a 的开发、交叉编译、打包或验收；已存在的 x86 Android 源码/ZIP/Actions 仅历史留档，不代表新目标。Linux/Windows x86 产品、回归和保护区完全不受影响。首个 Actions 真业务目标是 Android16 ARM64 userdebug/Cuttlefish P2 原生及 P3 普通 App→受控 su；Android16 ARM64 实体 KernelSU 仅最后专项终验；Android9–17 仅按可用 ARM64 镜像/真机选择后续覆盖，无 ARM64 镜像记 NOT_RUN，不补 x86 平台测试。真机操作仍需用户明确授权。

**工作节奏**：以一次可审计的大批次推进同一功能纵切面，Go 原 TLS/租约冷控制、Rust 既有 PN/AEAD/M3/M4、Bionic RAW/TUN/物理Network、owned Stop、Android 构建和文档同时推进。互不相依的代码研读、平台接口、纯协议、Go CLI/UI 和文档尽量并行；合并时统一检查 source-lock、generation/lease、MTU、BorrowFence/Stop，一次 SOURCE 集中跑 ARM64 Actions，避免为孤立小改动重复触发较重构建。真正 Go→Rust 链接及真设备验收仍有顺序依赖，禁止 fake stub / 合成 PASS。更大批次也不以跳过安全、测试或日志为代价。

**A3 Android guest真业务验收入口（未通过；非本批代码待办）**：已通过 [Action44041601960](https://github.com/lly8666/wbd-next/actions/runs/44041601960) 同源原 Android ARM64 Bionic client/Root APK `BUILD_PASS`、原 Linux server+Linux peer 真 TLS/认证/租约/Rust M4双向 UDP/Stop `LINUX_ORACLE_PASS`（SOURCE `bb30ed3d864460dc22af67aaade1d17c47182c58`）。[Action44042235770](https://github.com/lly8666/wbd-next/actions/runs/44042235770) ARM64 macOS Android16 AOSP emulator QEMU挂死/ADB未上线，`ENV_BLOCKED`，**Android业务仍NOT_RUN**。优先 P2 在真实 ARM64 KVM/Cuttlefish userdebug Actions 跑原 Bionic→同源Linux 真业务，P3 用正式普通App→受控 `su` 真实授权做原WBD/Stop；最后实体 KSU 终验。旧KSU x86探针不是 Android ARM64 E2E，也从未与 `adb root` 配对证明等价。

## 1. 事实基线（不得将能力探测当产品链路）

- 2026-11-17 Android 分支由旧 HEAD `1f77125bc175d3d9fd55c93f6c371e6b20dc7a16` 正常 merge main `0e57cab2d53e2c95962eb673050fa54695fd3665`，得到 `d5126fcd4cc7c848b62181ebddf8dadcb4225397`；两个分支相对共同祖先修改路径无重叠冲突，保留双方历史。后续每次恢复重新核对远端HEAD/main与Actions。
- 源码 `09a6a7e5f8aef5c3b38abb262655561ca89e5f9a` 的 [KSU Action43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528) **PASS**：普通 targetSdk37 App→KernelSU UID0、真实私有 namespace UDP53 6/6（Direct4/Tunnel2）、CN geosite 8503 / APNIC CN5500（合并4119）、内核 UID 选路 10/10、策略18/18、TUN/RAW/合成 NAT/恢复。私有合成 DNS/路由不是实际系统Resolver或 WBD TLS/认证/租约。
- 用户提供 Android16 真机 ARM64 KSU 报告，Root、TUN、RAW、IPv6、SO_MARK、策略18/18、UID选路10/10和合成NAT均 PASS；分流设置截图显示 CN8503、区间4119、`dns_udp_gate=SUPPORTED_IN_SCOPE`，但未导出该手机 DNS 六条子用例 JSON，因此不将截图写成逐项6/6独立证据。当前真机 Wi-Fi 下的物理 WBD、热点/USB、CLAT、切网、能耗依旧 NOT_RUN。
- Go 产品现有 `r0/go_overlay` 是针对 pinned `lly8666/wobuzhidao` 原始 Go 源 `a7a82db31fe736ffedee330795a3234d358f1984` 的 source-locked 装配，并非可直接作为单独 go.mod 构建的完整产品。正常 Linux 客户端 `V4LinuxClientProduct` 在 `bridge_v4_linux_client_product.go` 内进行 Go TLS/authenticated handoff→Rust owner；`crates/wbd-engine/src/v4_embedded_go.rs` 的真实 Linux raw/TUN worker与 `wbd-platform` 驱动明确限制 GNU/musl。Android Bionic/NDK 链接、行为和16KiB页必须另证，不得泛化 Linux ARM64 结论。

## 2. 核心边界与性能目标

一套共享 Go 冷控制/TLS身份/租约、Rust AEAD/FEC/重传/稳态/MTU/Stop；Android仅做 App Java 原生控件+root工作进程的薄系统适配。不要分叉整套 Linux 客户端，也不为平台迁移重构通用引擎。TLS 首个载荷严格合法 ClientHello；无 TLS 前私有交换，不改 [TLS_HANDSHAKE_CONTRACT](../architecture/TLS_HANDSHAKE_CONTRACT.md) 和已有认证、地址隔离、generation、AEAD、fixed-cipher retransmission、lane 边界、owned Stop。不同流/lane 无 HOL，内层 TCP 有序。FEC/ARM加速沿实际原生后端证据判断，不阻塞 Normal/off 闭环。

优先 **首次真实业务可达 > p99/无跨流HOL > CPU/唤醒 > 有界内存 > 可维护性**。可合理用内存换CPU，避免稳态逐包JNI/Java、shell、PackageManager、日志全表、轮询；TUN和物理socket由同一root原生工作进程持有，App只传低频控制消息。直连业务保留原应用 TCP 内核连接；不复制 Windows Direct TCP 双连接relay。无VpnService；前台通知与 root 授权可以显示。已具 Root 是先决条件，不开发提权/刷机/常驻系统模块、不改boot/system、不关闭SELinux；操作真机要明确授权。

## 3. 四个工作包及单一实际下一步

| 包 | 实施范围 | 本次状态 | 验收 |
|---|---|---|---|
| **A 产品装配与首次 Normal/off 真连接** | 固定原Go/共享Rust源码；Android NDK/Bionic ABI/链接/16KiB页；平台物理绑定、root TUN ownership、启动停止；复用Go TLS/认证/租约/原Rust steady path | **BUILD_PASS + LINUX_ORACLE_PASS；Android业务NOT_RUN** | 同SOURCE P2 真实 ARM64 Android Cuttlefish 原Bionic→原Linux server 真协议/数据，再 P3 普通签名 APK→受控 su 真实双向 TCP/UDP 与 Stop；实体 KernelSU 兼容性最后终验 |
| **B 路由、统一 DNS、App 选择** | A8多UID原Go/Java、B1普通双DNS Host、B2a真实8503 CN geosite、B2b同SHA签名APK+Go冷规则、B2c1 NDK物理socket冷绑定、B2c2a原Rust唯一TUN DNS53透明识别均已源码和Host门验。**B2c2b1新增同原Rust引擎纯Rust UDP53 Tunnel交易（1.1.1.1:53）64槽/12秒，原UDP source端口+DNS ID/QNAME与原目的DNS双向映射及IPv4/UDP校验和、恶意响应/容量/Stop Host4测试，同源ARM64 ELF/签名APK/原Linux oracle 10/10 PASS**；**B2c2b2已将映射接入同原Rust M4 TX（小包+jumbo）、原AEAD/M3认证RX→TUN与Stop，`hijack_enabled=0`冷许可不打开**，DNS仍未接管；**B2c3已把服务器FQDN原Go冷物理223.5.5.5:53 DNS查询接到真实FakeTCP/TLS之前，APP支持域名输入，同源10/10 PASS，但Android设备实际执行仍NOT_RUN**；**B2c2c原Rust同TUN worker已接真实Bionic物理UDP53 send/recv并验证源/ID/QNAME后构造真实IPv4 UDP回包，源码SOURCE 10/10 PASS，冷许可仍未启用** | **B2C2B2_ORIGINAL_RUST_M4_HOOK_BUILD_PASS；ANDROID_DNS_HIJACK_DISABLED** | 后续须完成物理223.5.5.5 NDK双协议出站与Tunnel1.1.1.1实际联通、TCP53有界流、netd Resolver导入/CN IPv4-owned Stop；Android P2/P3仍NOT_RUN |
| **C 产品模式与生命周期** | Normal/off、fixed/auto、Game原有lane；低频状态、前台Service、网络callback、重认证/轮换/切网、资源观测 | PLANNED | 同源模式及Stop；一次实际网络切换；有限业务 p99/CPU/RSS/idle 唤醒 |
| **D 条件热点USB与PR整合** | 手机/热点/USB独立开关、系统共享SNAT/conntrack、真实offload/CLAT边界、回归/PR | PLANNED | 已授权真机专项结果 + 清晰NOT_RUN 清单 + PR；未经验收不得自合 main |

**历史早期A1记录（不代表现行待办；后续ARM64原Go/Rust完整链接已PASS）：A1 ARM64+X86_64 Bionic ABI + 同一共享 Rust Go↔Rust 认证冷所有权真实C ABI导出、双64位 ELF 16KiB对齐（SOURCE `c385502ab12a4e42c26e7a8beb57ec4aa68eb2f5`，Action44015392698，阶段清单/ZIP14298207771）；但原Go完整产品连接器在ARM64因 Android M4 RAW/TUN/Health/MTU 产品符号未移植而链接FAIL，x86完整链接NOT_RUN。**彼时历史下一步（现已完成 ARM64 原生链接，不再作为当前待办）**：A2 抽出经核验的共享 M4 owner 驱动接口，把 Android Root TUN/物理RAW、网络绑定接到原 Rust PN/AEAD/Stop；A3 再验真实 Android 与同源 Linux 服务端 TLS/认证/租约及 TCP/UDP 收发（现行准入以 §8.0 P2/P3 为准，实体 KSU 最后终验）。** A1 的构建或符号检查不能宣称 A2/A3 成功；不要重新扩张短时探针按钮。

### A2 ARM64 原 M4 施工切片：就绪线程/Health/Stop

本批沿同一冷 Go 已认证 generation 复用原 Rust `ProtectedScopedOwner`，在 ARM64-only `v4_android_original_m4.rs` 中把 Bionic RAW/TUN 接成最多 8 个包/次的双原生就绪线程：沿既有 M1 FrozenRecord、原 PN/AEAD/唯一重放、M3 LINK 及认证 /32 TUN gating；原 `HealthClock` 发送/解析真实加密 kind0，原 `BorrowFence` 持有每次 syscall，同一原 Owner 的 Stop 先 eventfd 唤醒两个线程并 join，再停止密码状态和关闭 FD。切网 ifindex/物理MTU通过原已绑定 RAW FD 定期读回，不回退默认网络。Android 仅编译 ARM64。**此处均是代码施工，不等于编译、链接或设备运行通过。** 大包/fragment/真实FEC/Game/完整原Go产品符号和 Root控制器仍属真实未解决项。

## 4. 真正的 Android 产品架构

Java 原生 Activity → 配置/应用列表/授权/Start/Stop/状态 controller → 低频进程IPC → UID0 native worker（Go cold TLS/auth/lease、Rust稳态、TUN、raw/physical socket）→ owned内核路由/网络绑定。Android连接遵循系统当前 Network/ifindex/源地址/MTU；bootstrap域名DNS必须物理直连且在建链前完成。root UID不是万能出口放行，不能覆写 netd fwmark；隔离表夹具与生产净增量行为分离。Linux现有入口/默认值不得改变。Android app/NDK ELF 采用真实 Bionic 构建，检查 syscall/struct布局/链接/arm64 4KiB与16KiB；cross-build 不等于设备装载，不等于 ARM crypto/FEC ISA 实际选择。

## 5. 中国 IP / per-App 策略

业务 egress：规则分流 = LAN/CN IPv4/自定义直连→内核实际物理出口，其余→WBD TUN；全隧道 = 普通Internet全部WBD，LAN/系统/控制例外明确列举；直连 = 普通业务内核直连；跟随默认 = 用户默认模式。按实际目标 IPv4/UID 一次内核分类，不对 DATA 检测域名、不建立域名→真实IP强制直连映射。中国域名海外A仍可WBD、外国域名中国A仍可直连。CN IP 复用APNIC转换/区间，CN域名复用 geolocation-cn include/attrs/类型，内置离线规则。内核共享同一地址集合和少量路由，设备不支持时只实现一种有证据的兼容后端，不能每App复制5500条CIDR。

v2rayNG仅作为选择列表交互参考，不引入其VpnService/代理核心。Java原生 ListView/Adapter，真实安装App图标、名称、包名、搜索/已选过滤、系统App默认折叠、批量设置；按包名+必要用户标识持久化，启动/变更时解析UID，共享UID展示组绑定，不在数据面查询。普通主用户优先，多用户/工作资料列限制。诊断文本UID表单保留在工具入口，不能冒充正式产品列表。

## 6. 统一普通 DNS（用户明确取消 FakeIP）

只提供 **国内DNS 223.5.5.5** 和 **隧道DNS 1.1.1.1** 两个 IPv4 单endpoint（如现有配置可设置端口则沿用），无备用/竞速/跨方向回退。全局“CN域名DNS分流”在规则分流模式默认开、全隧道默认关；开时按原查询QNAME命中CN→国内DNS物理发，其他→WBD隧道DNS；关时被接管的普通DNS统一隧道DNS。WBD服务器域名bootstrap无论模式都单独由国内DNS物理发，服务器IP不用查DNS，不能递归回环。

per-App 仅改变业务 IP 出口，不重建 netd 每UID DNS、不恢复共享系统Resolver的原始App UID；选择“全隧道/直连”不保证系统DNS相同出口，UI必须注明。支持 UDP/TCP53，同一endpoint的 UDP TC 回退TCP，TTL与 bounded cache/in-flight/coalescing、CNAME原查询一次选出口；失败返回错误，绝不暗用其他DNS或系统DNS。自有DNS socket标记防重定向循环，不给普通应用的DNS IP全局豁免。AAAA可按 Android 内层IPv6禁用策略空答；仅拒绝接管内层IPv6，绝不关物理IPv6/CLAT。Private DNS/DoH/DoT/DoQ不解密，不保证域名分类生效，只按可见IP出网并标注用户设置限制。

手动「更新中国IP和域名规则」：CI把固定上游转换为轻量规则包；Android一次从可信 HTTPS 下载，核版本/格式/条数/大小/hash，后台处理并原子替换，失败保留已加载旧版；不定期轮询、不逐个抓域名、不清空全机conntrack。新连接切新规则，既有flow尽量pin原出口。版本与来源日期条数可见，不能宣传APNIC为准确geoIP。

## 7. 生命周期/路由安全/能耗

采用 ConnectivityManager callback 低频送消息到 native，与已有rotation/reauth/health/idle/keepalive/dead和MTU预算复用；无第二协议计时器。可重叠切网 A→A+B→B，断网直接重建，不承诺旧五元组迁移；payload idle与keepalive独立。UI visible时低频读取缓存状态，隐藏后停UI刷新；前台service可用但数据进程不依赖Activity，不持有默认永久wake lock。手机/热点/USB独立开关，先做手机，后做物理共享：采用Android原生系统热点/DHCP与内核SNAT/conntrack，沿服务端原 /32 租约验证，不自写DHCP。offload/eBPF/CLAT/AP+STA必须真机证实。

生产路由/DNS修改以 **owned journal / 可重放撤销** 为准：只增加精确规则/表/链、应用现有状态改变时compare-before-restore，正常Stop/异常退出回收；禁止 `ip rule flush`、全机规则快照整体恢复、向所有root UID放行、隐式默认直连泄漏。若root失权/进程双死不能撤销则明确报告，避免在正常路径叠极端恢复框架。

## 8.0 用户确认：Actions-first 功能等价而非 KernelSU 品牌锁定（2026-11-17）

### 历史证据及 Root 等价结论
- [KSU Action43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528)，SOURCE `09a6a7e5f8aef5c3b38abb262655561ca89e5f9a`：Android16 **x86_64** AVD 普通 App `org.wbdnext.rootprobe`（targetSdk37）真实通过 KSU3.3.1 Manager 的 `su`，Root UID0、NET_ADMIN/NET_RAW CapEff、`u:r:ksu:s0`，SELinux Enforcing，内核 TUN/RAW/UID路由、App UDP/TCP及隔离 DNS和回收均有证据。`ksu-boot-and-test.sh` 明言**不执行 `adb root`**，ADB 仅运送/读取指令，`adb shell su` 也不等于 `adb root`。**已证明 KSU 单侧功能，完全没有同机 adb-root 配对试验，`ADB_ROOT_VS_KSU_EQUIVALENCE=NOT_PROVEN`**；旧 x86 不能代替新 ARM64 正式 WBD。
- [Action44041601960](https://github.com/lly8666/wbd-next/actions/runs/44041601960) Android ELF/APK `BUILD_PASS` + 同 SOURCE 原 Linux server↔Linux peer 标准TLS/租约/M4双向UDP/Stop `LINUX_ORACLE_PASS`，并非 Android 真连接。[Action44042235770](https://github.com/lly8666/wbd-next/actions/runs/44042235770) 其后的 ARM64 macOS Android16 AOSP emulator QEMU 主循环/CPU 线程卡住，ADB 不上线约10分钟，guest `ENV_BLOCKED`/`NOT_RUN`，不能误判 WBD 应用失败。
- `adb root` 只证明 adbd/shell 可获得调试 Root，不授予普通 App `su`。KSU Root Profile 可限制 `su` 的 UID/GID、groups、capabilities、SELinux；**`uid=0` 或 `getenforce=Enforcing` 均不足以证明权限或网络行为等价**。只能对同一程序/同操作/相同 Android 系统网络语义/可观测结果在指定范围内认定行为等价，不能宣布 Root 提供者全面等价。

- [A6 Action44056494256](https://github.com/lly8666/wbd-next/actions/runs/44056494256)，SOURCE `f7f142da2ad8e58365b7e36dd1ba6f734b32923c`：**5/5 Jobs SUCCESS**，原M3、ARM64 Bionic原Go/Rust、签名Root APK、原Linux WBD server oracle；Java事件Network门16断言、生成的Root Stop脚本 `sh -n` 11断言、`owner.pid`旧2/新3字段POSIX解析PASS。`ubuntu-24.04-arm`实测 `aarch64` 但 `/dev/kvm` 不可访问，**ARM64 Android P2/P3 环境 `ENV_BLOCKED`，不是正式Root App联网通过**；不再尝试已有hang的macOS AVD。需可信有KVM的ARM64 Actions runner及固定Cuttlefish镜像/host工具，否则保持NOT_RUN。

- [A7 Action44060369629](https://github.com/lly8666/wbd-next/actions/runs/44060369629)，SOURCE `170ed6e47b0878d470cc83ef3cdebe9e781cfe7b`：**5/5 Jobs SUCCESS**，原Go/Rust ARM64 Bionic+签名无VpnService APK BUILD_PASS、原Linux WBD server oracle PASS；A7 `InstalledAppTarget` JVM真实包名/UID 17断言 PASS、最小Launcher `<queries>` Manifest PASS、A6网络回调16/Stop语法11及owner PID兼容回归PASS。**真正 Android16 PackageManager/卸载广播/Root UID路由及 Android↔Linux业务依然NOT_RUN**；aarch64托管runner `/dev/kvm` 不可用、Cuttlefish P2/P3 `ENV_BLOCKED`。共享UID不能逐包分开；不得把编译的包选择器冒称真实Android per-app功能完成。

- [A8同源 Action44063911490](https://github.com/lly8666/wbd-next/actions/runs/44063911490)，SOURCE `c76215d1ea4a215560b401c47ef5d1342ef70bf2`，**5/5 Jobs SUCCESS**：v2多UID rootjournal Go测试（部分失败回滚、跨版本崩溃恢复、活Owner锁、外国priority/table拒绝）、Java多包UID组19断言、原M3、Android ARM64真实原Go/Rust ELF与签名Root APK、Linux原server标准TLS/租约/M4双向UDP/Stop oracle均PASS；A6/A7 Host回归保留。首轮[Action44063385632](https://github.com/lly8666/wbd-next/actions/runs/44063385632) Java非法系统UID构造器负例测试夹具FAIL已按实际修复，不能改写旧FAIL。修复SOURCE治理[Action44063911524](https://github.com/lly8666/wbd-next/actions/runs/44063911524)因只改测试/devlog而未同改功能卡FAIL，当前最终证据提交补齐卡片；不把治理失败写成软件失败。**真 Android16 ARM64 PackageManager、内核多UID rule、App→su/与Linux双向WBD仍NOT_RUN**：Actions ARM64 runner`/dev/kvm`不可用，Cuttlefish P2/P3`ENV_BLOCKED`。DNS/分流尚未开发实际系统E2E，实体KSU最后。

- [B1 同源 Action44069144804](https://github.com/lly8666/wbd-next/actions/runs/44069144804)，SOURCE `8534a9182475a07072a4ae0e77807e23e6a3261f`，**6/6 Jobs SUCCESS**：原Go独立DNS模块 Host **真实UDP/TCP loopback7组**（原始QNAME分流、bootstrap物理、split关闭、TC→同DNS同Path TCP、无跨上游回退、坏ID/畸形包拒绝、TTL缓存/并发合并）PASS；同源原Go/Rust ARM64 Native、Root签名APK、原M3、Linux标准TLS/租约/M4 UDP/Stop oracle PASS；DNS包另交叉编译Android ARM64 test ELF但**并未接入运行中原Go CLI或Android system Resolver/原Rust M4 TUN**。ARM64 host仍`KVM_NOT_ACCESSIBLE`，P2/P3 `ENV_BLOCKED`，不能宣称 Android DNS 可用。下一步优先 B2 同源CN Geosite真实规则数据/真实Path绑定/系统DNS拦截和IP分流，实体KSU最后。

- [B2a 修复版 Action44073025085](https://github.com/lly8666/wbd-next/actions/runs/44073025085)，SOURCE `6dc6e9f0fc51ac885ba4c8832be0c63789d44f49`，**7/7 Jobs SUCCESS**：老诊断v2fly固定提交`41504eae2a11f305fe88cfc605cf6c105a80bf5a` 导入8,503条规则，真实SHA `45496d28e7a90472274fdf6c23afd43a0e478f9127dea241b628ca730863b1d6`，domain8431/full69/regexp3/keyword0，MIT LICENSE；原Go B2a CNRules四语义、坏SHA/截断拒绝和实际host UDP/TCP53格式/同endpoint TC loopback PASS，B1普通DNS回归、原M3、ARM64 Go/Rust Native+Go B2交叉编译、签名无VPN Root APK、原Linux服务器真TLS/租约/Rust M4/UDP/Stop oracle均PASS。**首轮 [Action44072465559](https://github.com/lly8666/wbd-next/actions/runs/44072465559) B2测试夹具FAIL**：误将`foo.example.cn`认为固定Geosite应命中；真实规则不覆盖所有`.cn`，改为负例且源规则未变，旧FAIL保留。Android物理/隧道DNS socket未接、真系统Resolver未接、CN数据仍仅Action工件，P2/P3受host KVM缺失ENV_BLOCKED、实体KSU最后。

- [B2b 修复版 Action44077291894](https://github.com/lly8666/wbd-next/actions/runs/44077291894)，SOURCE `26dc7ea1cf550b57c11103ea5b7ae2e103854699`，**7/7 Jobs SUCCESS**：原v2fly固定提交真实CN8503及MIT/SHA、Go 0600/NoFollow/symlink+篡改拒绝Host测试、B1 UDP/TCP DNS及原M3、Go/Rust ARM64原Native、独立签名Root APK内的真实规则TXT/许可证/provenance逐字节验证及原Go `--android-cn-geosite-file`冷装载源码门、Linux原WBD server真实TLS/授权/租约/Rust M4/UDP/Stop oracle均PASS。旧 [Action44076363045](https://github.com/lly8666/wbd-next/actions/runs/44076363045) 仅Linux oracle Job FAIL：独立donor拼装缺复制Go新`dnsnative`包，Go编译依赖未找到，**未执行真Linux业务**；修复代码 `linux-original-oracle.sh` 同源复制该包、不改变原协议，故旧FAIL保留、新SOURCE全重跑。正负证据均是软件；Android普通App→KSU su、原Go Root实际0600文件读取、系统Resolver及物理/WBD TUN真实DNS仍NOT_RUN/NOT_CONNECTED。Cuttlefish ARM64准入 `KVM_NOT_ACCESSIBLE`，P2/P3 `ENV_BLOCKED`，实体P5最后另授权。

- [B2c1修复版 Action44081252165](https://github.com/lly8666/wbd-next/actions/runs/44081252165) SOURCE `abec46f78515a86228f7e29b2ada069545278f5e`，**8/8 Jobs SUCCESS**：新独立Host真实Linux lo套接字测试四项，含原Go UDP DNS与TC→同Path TCP的两个socket `ControlContext`预连接fd回调、IPv4源接口核对、Tunnel/外国上游及错ifindex/MTU/IPv4拒绝、模拟netd标记失败保证零UDP发包；同源原Go ARM64 Bionic CGo中的NDK `android_setsocknetwork`及有界Bionic `getsockopt(SO_BINDTODEVICE)`代码真实编译链接，原Rust M4 ELF、B1/B2 CN8503 host真DNS、原M3、无VPN正式签名Root APK及原Linux server真TLS/租约/M4/UDP/Stop oracle均PASS。旧首轮 [Action44080505516](https://github.com/lly8666/wbd-next/actions/runs/44080505516) host测试PASS但ARM64原Go编译报Android `syscall.GetsockoptString`未定义，APK/Linux oracle skipped；修复保留设备回读、改NDK有界 `getsockopt`，旧FAIL/skip永久保留。**原Go仅在冷阶段构造物理DNS绑定器（`socket_opened=0 dns_capture=NOT_CONNECTED`），尚无实际Android DNS发包、系统Resolver或隧道DNS包接管**；ARM64 runner KVM不可访问，P2/P3 ENV_BLOCKED，实体KSU P5不碰。

- [B2c2a原Rust唯一TUN DNS53观察同源Action44085089405](https://github.com/lly8666/wbd-next/actions/runs/44085089405)，源码 `e22b456155ca30e75d5c86c9c29b903d7ea351c9`，**9/9 Jobs SUCCESS**：Rust Host5项真实格式IPv4 UDP DNS53、TCP53流候选、QNAME/EDNS/畸形QR/压缩域名/分片与散布首段长度、原IP包字节不变 PASS；CI静态核实原Rust `v4_android_original_m4::tun_worker` **唯一一次**真实TUN `read_ip_scatter`、先认证租约/IPv4再透明识别再原M1/M3 `seal_android_read_normal_ip`；新Bionic readonly C ABI `wbd_m0_embedded_go_loop_dns_ingress_observed`导出并强制 `hijack_enabled=0`；原M3、B1 DNS host、B2 CN8503、B2c1真实Host socket、原ARM64 Go/Rust ELF、CN8503独立签名Root APK、原Linux服务端 TLS/租约/M4 UDP/Stop oracle全部PASS。Android host准入仍 `KVM_NOT_ACCESSIBLE`，**这不是实际Android TUN包观察、DNS抢答、Tunnel DNS1.1.1.1出口或系统Resolver接管**；无第二TUN reader/Go Java逐包/新协议/FakeIP/VpnService。下一B2c2b只有完整有界 DNS backend +回复映射/精确 Stop +Android guest验收后才可启接管。

- [B2c2b1修复版同源Action44091367458](https://github.com/lly8666/wbd-next/actions/runs/44091367458)，SOURCE `17a5322e39893ceac567f461a8a345c25d17305b`，**10/10 Jobs SUCCESS**：新原Rust UDP DNS53完整IPv4 packet双向Tunnel1.1.1.1 NAT原上游反映射+IPv4/UDP伪头校验和、source端口唯一映射、DNS ID/QNAME验证、容量64/12秒/Stop、畸形/分片不改字节Host Rust4项PASS；B2c2a原M4 TUN入口/原M3、B1真DNS UDP/TCP Host、B2a真实CN8503、B2c1物理socket scoped Host、原Go/Rust Android ARM64 Native、签名无VPN Root APK内的CN8503 TXT+MIT、原Linux WBD server真TLS认证/租约/原Rust M4双向UDP/Stop oracle全部PASS。**首轮 [Action44090496300](https://github.com/lly8666/wbd-next/actions/runs/44090496300) B2c2b1 3/4 PASS且坏包夹具FAIL**：误写已为0的UDP长度高字节而非低字节，源解析器正确接受合法包；修复仅改坏长度低字节。中间SOURCE `fb2f1ca`只触发governance未触发产品workflow（新增Rust模块路径未列入），故最终修复SOURCE通过修改`android/root-native/ci`源锁脚本强制同源全跑。**Rust mapping仍未接入原TUN与认证RX hook，hijack_enabled=0；Android系统DNS/E2E/真实KSU不算成功**。ARM64 runner `KVM_NOT_ACCESSIBLE`，P2/P3 `ENV_BLOCKED`、P5实体最后另授权。

### Actions 准入、各层真实验收及最后实体终验

| 门 | 执行环境与实际证明 | 正确等级 | 严禁扩大 |
|---|---|---|---|
| P0 | 同SOURCE arm64-v8a Go/Rust Bionic/独立APK/16KiB/M3 oracle | `BUILD_PASS` | 不能证明 Android 运行 |
| P1 | 同SOURCE 原 Linux client↔原 Linux server 真 TLS/租约/Rust M4/数据/Stop | `LINUX_ORACLE_PASS` | 不能算 Android E2E |
| P2 | **真正 Android16 ARM64 userdebug guest**；允许 `adb root` 仅启动**正式 Bionic native ELF**，在 Android RAW/TUN/`ConnectivityManager` Network handle/`android_setsocknetwork`/netd 与同源 Linux server 真 TLS/认证/租约/TCP+UDP、MTU、Stop | `ANDROID_NATIVE_RUNTIME_PASS`，按子项真实结果 | **不证明 App→su** |
| P3 | 同guest **正式签名APK**、普通原 App UID/`untrusted_app`，必须自己 `ProcessBuilder("su","-c",...)` 经受控 CI Root provider 获授权，并实际验证 Root 权限、netd/UID路由、WBD双向TCP/UDP和Stop/崩溃恢复 | `ANDROID_APP_ROOT_E2E_PASS` / `ANDROID_LINUX_E2E_PASS` | Root provider 可非KSU，但不能称 KSU 已兼容；`adb root` 不可冒充 App→su |
| P4 | A/B/C/D全部可重现的软件功能逐场景Actions；B真实App选择/普通双DNS/分流/内核owned；C模式/切网/MTU/CPU/idle；D软件共享 | `ACTIONS_SOFTWARE_COMPLETE_FOR_SCOPE` | 合成namespace只是组件证据，未测不升级 |
| P5 | 软件 Actions 完成后**单独申请实体 Android16 ARM64 KernelSU 授权**，正式 App Manager授权、物理网络/热点USB/offload/CLAT/切网/功耗 | `PHYSICAL_KSU_FINAL_PASS`（按实测范围） | 未测硬件继续 `NOT_RUN_PHYSICAL_FINAL` |

P2 可以先解除 Bionic 运行/内核协议风险，但**A 包产品完成必须 P3**。KSU 和 CI Root provider 不同只可获得“所测系统调用和功能的行为等价”结论，KernelSU Profile、厂商内核/SELinux/热点USB/真实功耗都在 P5 重新确认。没 P3 环境可以做 B/C 纯逻辑单元/原 Linux组件，但正式 Android App 功能不可升格。

**ARM64 环境路线**：先单独轻量验证 Actions runner 真 `uname -m=aarch64`、`/dev/kvm`、隔离、清理；首选候选 Android16 **ARM64 Cuttlefish userdebug** + 固定配套镜像与 host tools。Cuttlefish、ARM64 KVM 云/自管 runner 目前都**没有本项目可用的已证实环境**；不假设 GitHub Hosted/macOS ARM64 有 KVM，不靠无限延长 emulator timeout。拿到实际 guest 后必须读回 API36、ABI arm64-v8a、`sys.boot_completed`、PackageManager、SELinux Enforcing、Net handle、TUN/RAW；无条件标 `ENV_BLOCKED`，需外部 runner/云成本须另行授权，不碰用户实体手机。

**权限/业务对照合同**：若将来比较 `adb root` 与 KSU/CI `su`，每条路径必须固定相同程序/SOURCE/测试输入，记录原App `uid`/SELinux/targetSdk、Root worker `uid/euid/gid/groups`、`/proc/self/status` 的 `CapEff/CapPrm/CapBnd/NoNewPrivs`、`id -Z`、`getenforce`、net namespace，真的打开 `/dev/net/tun`、AF_PACKET/RAW/`SO_MARK`/`android_setsocknetwork`，验证 Android netd/UID FIB、原 Go 标准ClientHello→认证/32租约→Rust M4的 TCP+UDP双向及owned Stop、崩溃恢复。缺少配对结果为 `NOT_PROVEN`；权限或结果不一致是 `NOT_EQUIVALENT_FOR_SCOPE`，不许把 UID0 假设为全面等价。

保持 **Actions-first、P0→P5，实体测试最后**、main/M0不改、PR #36 Draft；一场景一独立 job/Action、同一SOURCE/manifest/SHA，保留真实 FAIL/ENV_BLOCKED/NOT_RUN、镜像/runner/权限/网络脱敏证据，不上传凭据或原始pcap。**下一步唯一优先：先准入 ARM64 KVM/Cuttlefish Actions 环境，再 P2 原 Bionic→Linux 真业务，随后 P3 原签名 App→受控 `su`。**

## 8. Action 分层验收和边界

- A：同一SOURCE/manifest/hash复用原Go donor/Rust/Android与原Linux服务端；现有Linux-only真实协议oracle PASS。按§8.0 P2§真实ARM64 Android userdebug原Bionic→Linux真 TLS/认证/租约/双向TCP/UDP/Stop，再按§8.0 P3§普通App→受控su同源闭环；不能用合成DNS/loopback TCP或adb root代替P3。Android硬件ISA加速须最终实体机确认。
- B：两真实App（跟随/直连/规则分流/全隧道），受控解析CN、非CN、CN→海外A、UDP/TCP53/截断、bootstrap与不回环、手动规则成功/失败保旧、主网络Apply/Stop；少量公网解析，勿把某域名公网A写死。
- C：fixed/auto/Game原档位与lanes、重认证/切网、idle/wake、异常退出、普通/近MTU；低负载10–20Mbps、30–60秒先读CPU/RSS/p99和空闲唤醒，性能容量不足便停止，不刷500Mbps，不拿AVD代表手机耗电。
- D：实际ARM64手机Root授权、真实热点/USB、offload、CLAT/蜂窝切换/功耗专项另列授权与NOT_RUN。Android9–17只看可运行 ARM64 镜像或已授权真机，缺 ARM64 镜像记 NOT_RUN，不运行 Android x86 矩阵；adb-root不代表App su全版本。旧Windows/Linux产品不许回归。

一组相关代码/UI/配置/夹具完成后才跑较重Action。失败定位产品/权限/VM/夹具；复习原实现，做最小有证据修复。每完整包写 `docs/devlog/android-root-probe/` 短文，精确SOURCE+Action+失败+NOT_RUN+唯一下一步，同步功能卡/配置帮助。同步main仅在开工（已做）、首次最小真实链路后、最终验收前及确需共享接口变化时。完成功能和合理验收后提PR，交代真机待验清单并收工，不自行制造后续优化任务。

## 历史探针方案

旧 `ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md` 内容在 Git `1f77125bc175d3d9fd55c93f6c371e6b20dc7a16` 同路径版本中完整保留；2026-11-17 以后以本授权适配计划为准。探针记录索引：[20261117 最终 KSU 日志](../devlog/android-root-probe/20261117-android-cn-geosite-dns6-kernel-final.md)。
