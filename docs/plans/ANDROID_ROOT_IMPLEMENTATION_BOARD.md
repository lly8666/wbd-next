- **B47 正式Root App Game2/4原生READY与显式手动冷切网 BUILD_PASS/HOST_PASS，实体NOT_RUN**：SOURCE `c3067af60b7013327907842c0148c5613a3199a8` [Android Dual64 #45158643764](https://github.com/lly8666/wbd-next/actions/runs/45158643764) **completed SUCCESS，11 SUCCESS/4 SKIPPED**，双ABI原Go/Rust、签名ARM64 APK、纯JVM Game2/4 off/fixed READY与原Native/UID两类Stop Host、2个Linux原Server Oracle及6个DNS/CN/M3 Host全通过；[功能卡 #45158643786](https://github.com/lly8666/wbd-next/actions/runs/45158643786) SUCCESS。正式Service现在真正识别Go Game READY且与原UID_ROUTE_INSTALLED双收据才能显示，显式“先Stop→刷新真实Network→手动再Start”入口、活跃旧Root期间禁止重写私有凭据；没有自动新Network Root操作。旧Go Game组仍缺与Normal对齐的原生/路由Stop完整日志，故不会虚报Game Stop已确认。实际Game2/4、冷切网、TCP/UDP/E2E/性能仍NOT_RUN。
- **B45 Game4/off原Go四TLS→Rust单TUN四RAW+宽错峰正式App接线，软件CI待核**：B44软件PASS基础上，原Go复用Game2同一2/4冷真FakeTCP/TLS、原Group单GameAdapter/同epoch租约，原Rust唯一TUN扩2/4 RAW M3，Game4原0/4/50/140ms错峰不靠新的App包触发后续RAW副本；一个原RST journal保存四连续端口精确规则与Stop/恢复，原UID route只在真实M4 READY后发布。App Game4/off三DNS/Health/预设/九项Rust计数/Host门接通，Game2/Normal回归保留。B45本SOURCE双ABI/签名APK/Linux原Oracle待CI，实机Game4真实业务/Stop/性能NOT_RUN，GameFEC/切网未开放。
- **B44 Game2/off 三DNS原Rust完整接线软件PASS，设备NOT_RUN** [Dual64 #45132376536](https://github.com/lly8666/wbd-next/actions/runs/45132376536) 11 SUCCESS/4 SKIPPED：在B43原双Go TLS/单Rust Game2 TUN+2 RAW上直接复用Normal的 `AndroidBoundPhysicalDnsUdp` / `PhysicalDnsUdpFlows` / CN8503 `choose`，当前Network精确物理UDP53于同一Rust TUN TX线程送/收、CN域名物理而非CN走原已认证隧道，原TCP53不改，Stop归还当代Socket。Root App保留三种互斥DNS模式、参数/预设，Go原低频计数增加物理DNS收发/失败。签名APK、双ABI、原Linux服务端Oracle已同SOURCE PASS，实体Game2/性能NOT_RUN；Game4/FEC等不开放。
- **B43 Game2/off 原生DNS/Health/计数软件PASS，设备NOT_RUN** [Dual64 #45122281141](https://github.com/lly8666/wbd-next/actions/runs/45122281141) 11 SUCCESS/4 SKIPPED：B42原Go双TLS/单TUN双RAW已有软件PASS；本轮Game2唯一TUN→M1前复用Normal原Rust UDP53 64槽映射，两条原M3认证RAW RX之后复用原逆映射回TUN；原Go App Health 15/30秒传到Group Rust HealthClock，低频Native RAW TX/RX/TUN/DNS计数进App。物理/CN DNS、GameFEC/Game4、切网仍不开放；实体与性能NOT_RUN。\n- **B41b Android原Game2/off Go→Rust双TLS/UID产品CLI软件PASS，实体NOT_RUN**：新增真实2条所选Network冷FakeTCP/SYN/独立Go TLS+受保护相同epoch/租约/每lane Detach、交由既有同一个Rust `game_group_join→raw_bind→m4_start`、两lane独立M3与单TUN的真实worker；原唯一root RST守护支持连续两端口、一份持久化journal/Restore；Go RAW RX在M4后`Quiesce`，原Root UID私有路由仅在双方TLS/M4完成后安装；组Stop先于lane Stop及UID撤销。入口为显式手工`--mode game2`，只支持Game2/off，Game4/FEC/应用DNS仍拒绝。**签名App仍不提供Game按钮；[本SOURCE Dual64 #45033871118](https://github.com/lly8666/wbd-next/actions/runs/45033871118) 11 SUCCESS/4 SKIPPED，真实设备/Server 双lane业务 NOT_RUN**。
- **B40 Game2/off原Rust Android M4源码完成、双ABI/签名APK软件PASS；Go/App及设备未接**：真正GameAdapter TX（1个实体TUN读）→原M3按lane RAW TX，2条各自原M3 AEAD/PN RAW RX→共享GameReceiveOwner first-delivery→同一实体TUN write；原HealthClock和ACK ledger内同一worker，组级Stop先join完整M4再drain RAW FD。仅2lane/FEC off。尚无原Go Android双TLS冷客户端、Root UID产品启动/E2E，Game仍不开放；[B40同源Dual64 #45031248129](https://github.com/lly8666/wbd-next/actions/runs/45031248129) 11 SUCCESS/4 SKIPPED；软件编译资格，不是M4实机。
- **B39 Game2 Android 原生底层在建**：既有原Go/TLS提交后的 `game_group_join_original` 新增 Android 真选定Network一致性、双/四lane原TCP source port/真实TX序号规范；Android新组级raw bind复用原 `AndroidBoundRawRx/Tx`，每lane精确BPF五元组及Bionic物理绑定，group Stop先同步归还借用再停同一GameAdapter。Rust `game_group_state.drivers_installed` 仍是0；无Android Game TUN/M4循环、Go双TLS模式入口、真实业务验收。Host Rust单测、双ABI动态符号/编译与治理需本SOURCE独立验证，绝不等同已上线Game2。
# Android Root 原产品功能施工台账（B30｜源码与设备分层）

- **B38原生产调用链完成、Host/Build PASS，实体NOT_RUN**：手工最多4条IPv4 CIDR之外，显式选用真实所选Network的LinkAddress子网自动并入原Root UID FIB throw路由；不改main系统路由、不新建包分类器；同源[Dual64 #45028073114](https://github.com/lly8666/wbd-next/actions/runs/45028073114) 11 SUCCESS/4 SKIPPED；真机NOT_RUN。
- **B37原生产Health接线Host/Build PASS，实体NOT_RUN**：可选原Rust已认证Health间隔15s默认/30s低唤醒，90s dead保持；原App→Service→Go参数→既有Rust HealthClock有效读回。Host/双ABI/签名APK分层验收，实体CPU/RSS/idle尚无实测。
- **B36选定Network DNS接线Host/Build PASS，实体NOT_RUN**：选中Network LinkProperties IPv4 DNS→Root App START→Service冷复核→B35 Go / B34 Rust既有DNS生产参数；Host/签名APK结果以本SOURCE Action为准，不包括系统DNS/IPv6/实体。
- **B35已完成源码接线，Build/Host PASS，实体NOT_RUN**：已选物理DNS IPv4不再仅接原Rust M4 App UDP53，也接原Go `--peer-host` 的冷UDP53/TCP53服务器域名引导；原 `Network` 绑定不变，默认223.5.5.5，不新增系统netd接管。Host/签名APK/实体资格依B35新SOURCE Action独立认定；Game/IPv6/热点/实体E2E仍缺。

- **唯一工作分支**：`experiment/android-temp-root-probe`，对照基线 `f115ab1840f1c50eb1922f9c34b67267ca1fd770`，Draft PR #36。主线 `main` 不写。
- **证据**：[B33c Android Dual64 #44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) **11 SUCCESS/4 SKIPPED**，包括签名ARM64 APK、原Go/Rust双ABI、Linux原服务端Oracle与原rootjournal全套Host测试；[Governance #44975823362](https://github.com/lly8666/wbd-next/actions/runs/44975823362) SUCCESS。Android真实应用E2E/性能依旧未验。
- **口径**：`WIRED` 源码确实连入生产调用链；`HOST_PASS` 同SOURCE已有Host/ARM64编译资格；`PHONE_PARTIAL` 旧真实API36片段凭据；`NOT_RUN` 手机/真实双端业务未验；`MISSING` 确认无生产路径；`BLOCKED` 需大范围不同架构或授权设备。不要把历史步骤名、单一日志和按钮等同真实能力。

| 功能主线 | 产品源码状态 | 可复验资格/边界 | 施工后续 |
| --- | --- | --- | --- |
| 标准FakeTCP→TLS→保护认证→/32租约、原Go受控启动 | WIRED | HOST_PASS；旧API36达成TLS/租约 | 保留原入口；真服务端归属、E2E后验 |
| 原Rust Normal/off M1/M3/PN/M4 RAW/TUN双向、Health、owned Stop | WIRED | HOST_PASS＋旧API36 M4双向内核收据；业务字节E2E NOT_RUN | 优先解决真实业务阻塞与CPU，再追优化 |
| 原Root 选定普通App UID / 最多8 UID / all-app(20 profile)，单TUN与原路由精确Stop | WIRED；B31三范围服务器/32例外HOST_PASS | B31正式签名APK/原Linux Oracle 11 SUCCESS/4 SKIPPED；全App实机NOT_RUN | B33扩展同私有FIB显式直连CIDR，无新逐包路径 |
| 原Fixed FEC2 TX parity、RX恢复、M2 Quality、DF0/DF1 PMTU | WIRED | HOST_PASS；Fixed物理E2E NOT_RUN | 不再造新的FEC2算法；补现有组合缺口 |
| 原Auto 低频策略、revision quiescent change、App REQUESTED/APPLIED回读 | WIRED | HOST_PASS；实体Auto稳态/换档 NOT_RUN | 原生性能验收前不调策略阈值 |
| 普通App IPv4 TUN→1.1.1.1 UDP53、反向映射，跨Normal/Fixed/Auto | WIRED | B29b HOST_PASS；系统netd不是入口 | 不重做已有64槽；验App DNS |
| 普通App IPv4 TUN→223.5.5.5物理 UDP53、CN8503分流与TCP53原隧道透传 | WIRED | HOST_PASS；只覆盖TUN内App包、TCP53不是物理直连 | 保留已有Socket/M3；后续按真实需求完善物理TCP |
| LAN-only Wi-Fi/Ethernet/蜂窝、同选定Network域名启动 | WIRED | B28b HOST_PASS；LAN手机 NOT_RUN | 使用现有Network，不新建resolver |
| App选择、设置持久化/SAF导入导出、凭据加密保存、TLS CA选配、诊断 | WIRED；B32完整已安装普通App枚举HOST_PASS | B32a同SOURCE双ABI＋签名APK/Linux Oracle 11 SUCCESS/4 SKIPPED，仍非手机可见性验收 | B33增加可保存/导出非秘密直连CIDR冷表单 |
| 全App额外按已安装普通App绕过 | **B34 HOST_PASS / BUILD_PASS** | 同源B34a原Go/Rust双ABI+签名ARM64 Root APK+Linux Oracle **11 SUCCESS/4 SKIPPED**；复用原20 profile UID FIB/8排除AppID配额（必含本App/KernelSU Manager），用户额外最多6包；App/SAF→Service双UID冷核验→原Go/journal精确Stop | **Android真机NOT_RUN**；跨profile同AppID可能共同绕过，实际物理出口未验 |
| 物理DNS可选IPv4上游 | **B34 HOST_PASS / BUILD_PASS** | 同源B34a 11 SUCCESS/4 SKIPPED；App/SAF→Service→Go冷参数→原Go/Rust M4冷设置/逐字节读回→已有Android绑定Network UDP53 Socket；默认223.5.5.5，可选LAN路由器IPv4 | **实体UDP53查询/E2E NOT_RUN**；系统netd/DoH、原Go冷服务器引导、物理TCP53均非此路径 |
| Android系统Resolver/netd UDP/TCP/DoH交付 | MISSING | 普通App TUN DNS ≠ netd DNS | 需要独立准确方案，不能声明已经全局拦截 |
| Android IPv6/464XLAT/IPv6 DNS全链 | MISSING | 当前TUN/租约/内核规则为IPv4 | 独立双栈架构；不要将AAAA解析误作IPv6可用 |
| Android Game2/Game4 原多lane TLS→Rust Game M4双向 | MISSING | Linux/Windows已有原Game，不等于Android端口 | 真正端口并接共享TUN后再开放App选项 |
| Android应用TCP/UDP双端逐字节E2E、切网恢复、低CPU/吞吐/首包 | NOT_RUN | 旧API36只有内核数据收据与用户主观“数据通了” | 必须有设备授权后验；此期不假造 |
| Android物理TCP53、原生业务IP直连例外 | **B33 HOST_PASS / BUILD_PASS** | 同源原Root私有table 19842最多4个真实CIDR throw，单UID/组UID/all-App同原journal/Stop；App→Service→Go CLI→真实ip规则命令Host PASS；签名APK PASS | **Android实体netd后续物理路由NOT_RUN**，物理TCP53仍MISSING |
| Android轮换/动态换物理Network、热点共享/Tether | BLOCKED | 原Go Linux rotation存在，Android明确禁用；Network loss只Stop | 后续独立源路径；不因可选参数存在而宣称实现 |

## B34 本批执行选择

上一B33c `dd2292c8` [#44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) 原Go/Rust/签名APK/Linux Oracle **11 SUCCESS/4 SKIPPED**。本批大类优先做**全App模式按已安装普通App额外绕过**与**真正物理UDP53上游IPv4可配置**，全部复用原Go/Rust、原持久UID FIB、原Rust物理绑定socket。B34a源 `d70132608bf5` [Android dual64 #44978243692](https://github.com/lly8666/wbd-next/actions/runs/44978243692) **11 SUCCESS/4 SKIPPED**，包括完整签名ARM64 APK、Go/Rust双ABI与原Linux Oracle；[治理 #44978243728](https://github.com/lly8666/wbd-next/actions/runs/44978243728) **SUCCESS**。不新建Go逐包Worker、Android系统resolver劫持或大型CI。

## 原B33完成的软件资格

B31已补服务端IPv4 /32例外；B32a已补完整普通App选取。**B33**进一步批量施工显式最多4个IPv4 CIDR的真实内核FIB直连例外：原Root Activity设置（可本机保存及SAF导入/导出）、原Service手动START、原Go冷参数、single/group/all原journal路由安装/读回/Stop、Host原伪ip内核命令回归，全部同一SOURCE。默认输入空保持原WBD全隧道，无新增Go/Rust逐包控制器。最新B33c SOURCE dd2292c8f9ca [#44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) 11 SUCCESS/4 SKIPPED，正式签名APK/Host/原Linux Oracle均PASS。真实手机netd/实际物理出站、应用E2E及性能仍NOT_RUN。

维护：本台账是**进度标记**，不是独立竞争执行方案；每批以SOURCE/Action更新行，既往NOT_RUN/FAIL不删。
