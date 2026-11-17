# Android Root 原生客户端适配｜授权施工方案（2026-11-17）

**状态：IN_PROGRESS，产品真实连接仍 NOT_RUN。** 用户已明确授权从临时 Root 探测转为 Android 原生 WBD 客户端开发；本文件覆盖旧“只探测、不开发完整客户端”的工作边界。唯一施工分支 `experiment/android-temp-root-probe`，最终 PR → main，不直接提交 main/M0 registry/cursor。长期入口：[ANDROID_TEMP_ROOT_PROBE](../prompts/ANDROID_TEMP_ROOT_PROBE.md)；产品卡：[android-root-native-client](../features/entries/android-root-native-client.json)；探针历史卡：[android-temp-root-probe](../features/entries/android-temp-root-probe.json)。历史探针方案保留在 Git 历史和本文件末尾的链接，不再占用产品开发优先级。

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
| **A 产品装配与首次 Normal/off 真连接** | 固定原Go/共享Rust源码；Android NDK/Bionic ABI/链接/16KiB页；平台物理绑定、root TUN ownership、启动停止；复用Go TLS/认证/租约/原Rust steady path | **IN_PROGRESS，首次真实WBD NOT_RUN** | 同 SOURCE Android16 KSU ↔ 真Linux WBD server：标准TLS、认证、租约、Rust owner、真实 TCP/UDP 双向、MTU、Stop/恢复 |
| **B 路由、统一 DNS、App 选择** | 独立可撤销主网络增量；按App UID规则；两DNS上游UDP53/TCP53、TTL/缓存；真实App系统Resolver；手动规则包原子更新 | PLANNED | 真直连不经WBD、隧道经过服务端；真实系统DNS、应用选择和owned回收均实测 |
| **C 产品模式与生命周期** | Normal/off、fixed/auto、Game原有lane；低频状态、前台Service、网络callback、重认证/轮换/切网、资源观测 | PLANNED | 同源模式及Stop；一次实际网络切换；有限业务 p99/CPU/RSS/idle 唤醒 |
| **D 条件热点USB与PR整合** | 手机/热点/USB独立开关、系统共享SNAT/conntrack、真实offload/CLAT边界、回归/PR | PLANNED | 已授权真机专项结果 + 清晰NOT_RUN 清单 + PR；未经验收不得自合 main |

**已验证：A1 ARM64 Bionic ABI + 共享 Rust Go↔Rust 认证冷所有权 C ABI 构建及导出通过（SOURCE `7a721ae82c18e68db58af1b43b7fb3ce16057b0d`，Action 44014838092）；但原Go完整连接器因 Android M4 RAW/TUN/Health/MTU 符号未移植而链接 FAIL。下一步：A2 抽出经核验的共享 M4 owner 驱动接口，把 Android Root TUN/物理RAW、网络绑定接到原 Rust PN/AEAD/Stop；A3 再在 Android16 KSU 与同源 Linux 服务端真实 TLS/认证/租约及 TCP/UDP 收发验收。** A1 的构建或符号检查不能宣称 A2/A3 成功；不要重新扩张短时探针按钮。

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

## 8. Action 分层验收和边界

- A：一Action一网络场景，source lock + manifest + hash复用原Go donor/Rust/Android，先Android16 KSU ↔ 同源Linux服务端标准TLS/认证/租约/Normal-off的真双向TCP/UDP + Stop，再冻SOURCE、写证据。不借现有合成DNS/loopback TCP结果推广。Android ARM64实际装载、ISA加速必须真机证明。
- B：两真实App（跟随/直连/规则分流/全隧道），受控解析CN、非CN、CN→海外A、UDP/TCP53/截断、bootstrap与不回环、手动规则成功/失败保旧、主网络Apply/Stop；少量公网解析，勿把某域名公网A写死。
- C：fixed/auto/Game原档位与lanes、重认证/切网、idle/wake、异常退出、普通/近MTU；低负载10–20Mbps、30–60秒先读CPU/RSS/p99和空闲唤醒，性能容量不足便停止，不刷500Mbps，不拿AVD代表手机耗电。
- D：实际ARM64手机Root授权、真实热点/USB、offload、CLAT/蜂窝切换/功耗专项另列授权与NOT_RUN。Android9–17保留可运行镜像的基本构建/能力矩阵，镜像缺失如实记录；adb-root不代表App su全版本。旧Windows/Linux产品不许回归。

一组相关代码/UI/配置/夹具完成后才跑较重Action。失败定位产品/权限/VM/夹具；复习原实现，做最小有证据修复。每完整包写 `docs/devlog/android-root-probe/` 短文，精确SOURCE+Action+失败+NOT_RUN+唯一下一步，同步功能卡/配置帮助。同步main仅在开工（已做）、首次最小真实链路后、最终验收前及确需共享接口变化时。完成功能和合理验收后提PR，交代真机待验清单并收工，不自行制造后续优化任务。

## 历史探针方案

旧 `ANDROID_TEMP_ROOT_CAPABILITY_PROBE.md` 内容在 Git `1f77125bc175d3d9fd55c93f6c371e6b20dc7a16` 同路径版本中完整保留；2026-11-17 以后以本授权适配计划为准。探针记录索引：[20261117 最终 KSU 日志](../devlog/android-root-probe/20261117-android-cn-geosite-dns6-kernel-final.md)。
