> **B52 保存的连接配置一键真实原生连接/冷切换（本SOURCE待CI）**：基于B51a已通过双ABI/ARM64 APK/Linux Oracle [#45172614955](https://github.com/lly8666/wbd-next/actions/runs/45172614955) 11 SUCCESS/4 SKIPPED，正式Activity显示四个真实命名槽+mode，并允许用户指定当前实体Network后一击用该槽独立Keystore登录连接原Go/Rust；运行中则复用B48真实owned Stop和B49精确Network读回/1Hz前台单次续接，没有新Go/Rust热路径或无人值守重启。新SOURCE设备/E2E/性能仍NOT_RUN；详见[B52](../devlog/android-root-probe/20261123-b52-named-profile-one-tap-original-switch.md)。

> **B51 四套配置各自的密码/RouteKey本地恢复（本SOURCE待CI）**：在B50四命名槽上复用A38已有同一 AndroidKeyStore AES-GCM/AtomicFile/0600 记录，只为每槽分文件，绝不自造加密或更改 Go/Rust。保存时可选有效凭据，载入明确恢复该槽或留空等待用户输入，**不会错误继承其它WBD服务器的全局口令**；删除槽同步删本槽秘钥，全局“清除已保存凭据”删默认和四槽，主Keystore键随后删除。原Go TLS/账户、M4、Stop和B49冷切网原样。本SOURCE构建及APK看Actions，实体NOT_RUN。[B51记录](../devlog/android-root-probe/20261123-b51-profile-scoped-keystore-credentials.md)

> **B50 多连接配置产品接线（本SOURCE待CI）**：继B49源锁 [#45168583911](https://github.com/lly8666/wbd-next/actions/runs/45168583911) 11 SUCCESS/4 SKIPPED，正式Root App新增四个本地命名配置槽，复用原B22设置序列化，覆盖Go/Rust Normal/Fixed/Auto/Game2/4选项、三DNS/MTU/Health、单/组/all UID与直连；载入后先清旧复选框再对真实已安装包UID重建，**不会改变运行中的Root、Network handle或凭据**。原 B49 手动/一键冷切网和旧 native 所有权保持；Host+ARM64 APK/原Linux oracle看新SOURCE，实体/性能未验。[B50记录](../devlog/android-root-probe/20261123-b50-named-multiple-root-profiles.md)

> **B49 前台一键冷切网（SOURCE待CI）**：基于B48，用户选定真实目标Network后主动请求旧原Go/Rust完整Stop；原B48 Game/Normal UID撤销、Rust join、Go/RST清理、退出0确证后，由现有前台状态刷新一次性复用原 `start()`，当前Network精确读回，不自动在onLost后Root重启、不新建热路径或线程。见 [B49记录](../devlog/android-root-probe/20261123-b49-foreground-one-shot-cold-network.md)；正式APK/Host待新SOURCE CI，真机业务仍NOT_RUN。

> **2026-11-23 B48 正式Game2/4组级Stop及App冷切网 BUILD_PASS/HOST_PASS，实体NOT_RUN**：产品SOURCE `8b5d4ec18ace6c97300f01f8d96605834e5e1f67` [Android Dual64 #45163517303](https://github.com/lly8666/wbd-next/actions/runs/45163517303) completed SUCCESS **11 SUCCESS / 4 SKIPPED**，原Go/Rust双ABI、签名ARM64 Root APK含Game2/4 off/fixed原生READY/组Stop/UID与手动冷切网Host纯JVM、两Linux原Server Oracle及6个DNS/CN/M3 Host门全过；[功能卡 #45163517365](https://github.com/lly8666/wbd-next/actions/runs/45163517365) SUCCESS。原Go组级清理顺序已实际源码锁定：UID私有路由撤销→Rust唯一GameAdapter 1TUN/2或4 RAW join→Go冷RTO/RAW读者→RST journal移除，失败不能产生原生结束收据；App要求真实Game组+Native+UID（有路由时）+退出0才报告 `OWNED_STOP_VERIFIED`，且防旧会话仍在执行时重复START。物理Android Game2/4双向业务/实际Stop/冷切网/性能仍NOT_RUN，host准入不等于guest。无物理机/Server部署、main/M0未改，不做热切换或极端网络加固。

> **2026-11-23 B45 Game4/off 生产接线待同源软件资格**：由B44产品 `f193d5829a3d` [Dual64 #45132376536](https://github.com/lly8666/wbd-next/actions/runs/45132376536) **11 SUCCESS / 4 SKIPPED**继续。B45由同一原Go真实2/4条FakeTCP/标准TLS→原Rust一个GameAdapter/单TUN、2或4个RAW独立M3，Game4/off复用原0/4/50/140ms宽错峰并在TUN无下一App包时原生按期补发RAW副本；一个精确四端口Root RST journal且原UID route仅在四条TLS与M4真实READY后安装，App显式Game4/off/三DNS/Health/预设/计数。GameFEC、切网和外层修复仍禁止。**B45尚无同SOURCE编译/签名APK资格，Game4真实Android应用TCP/UDP/DNS/Stop/CPU/吞吐均NOT_RUN**。仅实验分支、PR#36 Draft，main/M0不改；不做极端工况或新安全架构。

> **2026-11-23 B44 Game2/off物理UDP53＋CN8503原Rust软件PASS**：产品SOURCE `f193d5829a3d` [Dual64 #45132376536](https://github.com/lly8666/wbd-next/actions/runs/45132376536) **completed/success 11 SUCCESS/4 SKIPPED**；原Android双ABI Go/Rust、签名ARM64 APK、原Linux server Oracle和各DNS/CN/M3 Host门同SOURCE成功。原Go真实双TLS→Rust单TUN双RAW Game2/off复用Normal的Network绑定物理DNS socket、64槽UDP53逆映射和CN8503冷匹配；App现支持隧道/物理/CN三种互斥DNS入口及九个原生计数。治理 [#45132376508](https://github.com/lly8666/wbd-next/actions/runs/45132376508) SUCCESS。**真Android Game2物理/CN DNS收发、两条TLS、真实App业务/UID/Stop/CPU/吞吐仍NOT_RUN**；ARM64 host准入不代表guest，4 KSU相关Job SKIPPED。Game4/FEC与切网未接，无实机安装授权、不重复旧重型测试。

> **2026-11-23 B43 Game2/off 原生隧道UDP53＋Health＋M4计数软件PASS**：本SOURCE `06937fa54efa` [Dual64 #45122281141](https://github.com/lly8666/wbd-next/actions/runs/45122281141) **11 SUCCESS/4 SKIPPED**，原Rust Game2单TUN双RAW复用Normal隧道DNS问题/回包映射，原15/30秒Health配置及Rust RAW/TUN/DNS原数值回读已由App→Go→Rust生产链接通；签名ARM64 APK和Linux原Oracle PASS。治理 [#45122281209](https://github.com/lly8666/wbd-next/actions/runs/45122281209) SUCCESS。Game4/GameFEC/物理CN DNS未开放；设备Game2 SYN/TLS/M4/UID/Stop及CPU/带宽NOT_RUN；下一步继续原生大类功能接线，不重开旧x86网络探针或安全加固。

> **2026-11-22 B41b真实CLI分发+签名APK同源软件资格**：`7fc34e6a7848` [Dual64 #45033871118](https://github.com/lly8666/wbd-next/actions/runs/45033871118) **completed/success 11 SUCCESS/4 SKIPPED**；Rust双ABI、原Go实际`runAndroidGame2`入口、Root UID源门、签名APK、Linux正常服务端Oracle均软件PASS。旧Cgo语法与CLI缺分发两次真实失败保留。Game2仅手工CLI/FEC off、App仍Normal/Fixed/Auto；无实机Game2双向包、Stop或性能资格。

> **2026-11-22 B41 原Go Android Game2/off生产冷端接线**：Android新 `game_android.go` 复用原FakeTCP/SYN真实所选Network，唯一RSTGuard journal匹配严格连续两客户端源端口；双真实Go TLS密码认证、原same-epoch独立exporter/ACK Detach、同一server保护/32，传给 `bridge_v4_game_native_android.go` 中通过现有原Go私有凭证验证的两lane Rust Game组，依序`game_group_join`、每lane原Bionic RAW绑定、B40单TUN双RAW原Rust M3/M4安装并核对native readback。仅此之后`QuiesceDetachedClientReceive`及原用户UID私有路由生效；Stop先join整组Rust再释放原Go lane和UID，不添加Go每包转发。此路径为显式CLI `--mode game2`，签名App仍只提供Normal/Fixed/Auto；Game4/固定Game FEC/App DNS/旋转未就绪。跨ABI/签名APK必须以本B41新SOURCE Actions为准，设备双方真实Game2/速度/CPU/Stop均NOT_RUN。

> **2026-11-22 B40 SOURCE软件验收收口**：[Dual64 #45031248129](https://github.com/lly8666/wbd-next/actions/runs/45031248129) 源码 `9ba1d39f82c4` **11 SUCCESS/4 SKIPPED**；Android Rust Game2/off 单TUN/双RAW真实worker跨编译与符号、签名APK、原Linux Normal/off Oracle PASS。依然没有Android原Go Game2双TLS产品入口/普通App UID路由和设备真实双lane M4，Game仍拒绝。不把CI BUILD称为Android E2E或性能资格。

> **2026-11-22 B40 原Game2/off Android Rust 真M4 worker源码施工**：基于B39已提交的原Go已认证2lane共同GameAdapter及其真实Bionic RAW socket，新增一个原TUN TX线程读取实际IPv4业务、`GameAdapter.offer/drain` 每lane原M3独立AEAD/PN并由现有IPv4/TCP builder提交真实sendto；两个lane各自由 `GameLaneOpener` 原M3开包、`GameReceiveOwner` 去重预留、真实TUN write后提交计数；原HealthClock kind0、10ms ACK进度簿，以及先join所有线程再归还 TUN/RAW的同步Stop。Game4/FEC、原Go Android双TLS产品入口、普通App UID切换、实机业务E2E尚未建立，仍不开放Game模式。具体是否可编译以B40同SOURCE Actions为准，不能把编译说成真实Go启动或内核实跑。

> **2026-11-22 B39 Android Game2原生组的实质第一段（M4未装）**：原Rust `game_group_join_original` Android分支现在必须从已认证的真实Go TLS/M1 lane及同一物理Network、同租约取得2/4条有序原FakeTCP tuple与原TX/RX序号，且拒绝已被Normal M4占用的lane。随后可选择性给整个已认证的Game组绑定每lane的Bionic所选Network精确IPv4 RAW RX/TX sockets，并在组级Stop回收FD borrows。这是Game2完整生产前的真实Rust cold→physical boundary，不是合成Game数据。没有 Android Game共享TUN、Game M4 raw/TUN worker、Go 2-lane TLS启动及UID接线；因此App/CLI仍拒绝Game、`drivers_installed=0`。软件验收仅看新B39同SOURCE Actions，真实设备NOT_RUN。

> **2026-11-22 B38实体Network直连子网生产接线**：新显式LAN直连选项从当前用户选定的ConnectivityManager.Network的真实IPv4 LinkAddress与前缀生成规范单条on-link CIDR，与原B33最多4条手工CIDR合并，Service冷读取同一Network再次核对，再通过原Go `--android-direct-cidrs` 接已有Root UID私有FIB throw路由。无新Go/Rust数据引擎、不更改主路由/Android默认Network；不代表强制走选中物理网卡。旧默认全隧道及旧本机/SAF预设不变。Host/签名APK资格看同SOURCE Actions，实体NOT_RUN。

> **2026-11-22 B37原Rust Health低唤醒接线**：原15s/90s Rust HealthClock是已安装的TLS后M4生命周期，现把Android用户显式的15/30秒间隔从Root App→Service→原Go CLI→已有`HealthKeepaliveSeconds`→Rust实际effective readback接线。默认15s不变；30s低频不改变90s dead、AEAD/PN/租约/真实TUN/RAW/owned Stop，不新增心跳goroutine或热路径。CPU/唤醒和手机省电效果NOT_PROVEN，需实测；Android Game/系统netd DNS/IPv6/热点仍未接。

> **2026-11-22 B36 真实选定Network DNS冷接线**：App显式选用已选择的Wi-Fi/移动/有线ConnectivityManager.Network的LinkProperties IPv4 DNS，START时绑定成同一数值上游，Service冷复核后复用B35原Go服务器域名UDP/TCP53与B34原Rust M4物理App UDP53，旧手动IPv4/默认223.5.5.5/SAF预设兼容。不读取默认系统DNS，不添加新包线程，不接netd系统Resolver、IPv6、物理App TCP53、Game；同源Actions/实机资格分开。

# Android Root 原生 WBD 客户端｜现行唯一执行方案

> **2026-11-22 B34b 两类主线正式Host/Build资格**：B34a原生产SOURCE `d70132608bf5772f61098199f1910dc13e542ecd` [Android dual64 #44978243692](https://github.com/lly8666/wbd-next/actions/runs/44978243692) **11 SUCCESS、4 SKIPPED**；[Governance #44978243728](https://github.com/lly8666/wbd-next/actions/runs/44978243728) **SUCCESS**。包括真实Go/Rust Bionic双ABI、签名ARM64 Root APK、原Linux Server Oracle、实际Java设置／CLI/范围测试和原Rust冷DNS ABI导出。B34全App额外指定普通安装App绕过及实体UDP53可选IPv4上游两项均标`WIRED/HOST_PASS/BUILD_PASS`，**不是**Android真实App业务E2E、物理DNS联网收发、跨profile出站或CPU/吞吐验收；系统netd DNS、IPv6/CLAT、Game2/4与物理TCP53仍未接通。


> **2026-11-22 B34两类真实主线**：全普通App模式新增额外最多6个已安装App的绕过清单，App与Service/Root前冷核验真实包名+UID；原本地/SAF预设冷保存，真实原Go `--android-route-exclude-appids` 仍在原私有FIB的20 profile、最多8个排除AppID（永远含本App及KernelSU Manager）、原journal/Stop运行。共享UID/跨profile同AppID会一起绕过；Android后续物理路由需真机验证。同时将物理/CN DNS模式的上游UDP53 IPv4从固定223.5.5.5推广为可选IPv4，App→Service→原Go `--android-physical-dns-upstream-ipv4` →原Go/Rust已认证M4冷设置与读回→原Rust已有 `android_setsocknetwork`/SO_BINDTODEVICE物理socket连接（可指定本地DNS 192.168.1.1）。不改系统netd、WBD自身服务器冷DNS引导、DoH、App TCP53、IPv6、Game；本SOURCE的Host/签名APK/原Linux Oracle须独立看Actions。


> **2026-11-22 B33d 最终同源软件资格**：实验源 `dd2292c8f9ca049b81d6afca05854630d8f1e59d` [Android dual64 #44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) **11 SUCCESS / 4 SKIPPED**；[Governance #44975823362](https://github.com/lly8666/wbd-next/actions/runs/44975823362) **SUCCESS**。包括Android原Go/Rust双ABI、正式签名ARM64 Root APK、原Linux Server Oracle、B33单/组/all UID直连CIDR原journal真实内核ip命令Host测试。此前B33/B33a/B33b源码门旧断言失败及取消Action均保留历史；资格仅限Host/Build。Android实体物理出站、用户App UDP/TCP逐字节E2E、CPU/吞吐/切网仍NOT_RUN，系统netd DNS/IPv6/Game/物理TCP53仍未实现。


> **2026-11-22 B33真实普通App IPv4分流/直连前缀**：B32a [#44969771959](https://github.com/lly8666/wbd-next/actions/runs/44969771959) 11 SUCCESS/4 SKIPPED、治理SUCCESS；B31真实三种UID模式服务端/32例外已同源通过。本批把可选最多四个**用户输入的IPv4 CIDR**从正式Root App→本机SAF预设→Service→原Go冷`--android-direct-cidrs`→single/group/all原Root journal**同一table 19842**内核`throw CIDR`真实安装/读回与Stop；首条UID规则前安装，默认空即原全隧道，原DNS/Go TLS/Rust M4/PN/Stop不增加额外数据面。此处的throw只让内核继续匹配**后续Android规则**，并非已证明一定经选定Network物理出口；实机/netd/首包延迟仍NOT_RUN，本SOURCE以Actions新证据为准。


> **2026-11-22 B32 Root选定普通App完整枚举**：B26以来只列launch/share/HTTPS处理器，不能覆盖大量没有这些Intent的普通游戏或App。本批在原侧载Root工具上增加`QUERY_ALL_PACKAGES`和当前用户`getInstalledApplications(0)`，保留旧Intent supplement、原`InstalledAppTarget.eligible`及Service冷UID复核、UID路由/Stop/SAF。Host/签名APK以本SOURCE Actions为准；实机可见性/真实应用E2E未验。


> **2026-11-22 B30 施工台账与主线批量推进**： 完整源码对照与完成度在 [ANDROID_ROOT_IMPLEMENTATION_BOARD](ANDROID_ROOT_IMPLEMENTATION_BOARD.md)。本次将WIRED/Host/手机部分证据/完全MISSING明确分开；不再重复实现已接原Go/Rust功能。优先修原Root UID路由三种范围的服务端IPv4直连例外，再按主线价值推进缺口；未经授权不动真设备。

> **2026-11-22 B29 Fixed/Auto M4 DNS 实际接线**：依用户最新优先级，实机受限时先补完成度。B17/B19 已接通 feature7 Fixed/Auto，App 默认Tunnel DNS开启，但原Go/Rust三种 DNS 冷授权只接受feature3，在 M4 之前拒绝Fixed/Auto。本批允许带真实FEC2 RX的同代feature7复用原Tunnel/Physical/CN DNS、唯一TUN、M3/PN与Stop，原Go FEC2 PENDING仍在M4前配置，不造新网络/安全框架。Host/BUILD看此SOURCE Actions，实机Fixed/Auto+DNS交付/性能仍NOT_RUN。


> **2026-11-22 B28 实体LAN服务端域名引导**：B27 `9d449f8f` 已开放真实Wi-Fi/Ethernet没有 INTERNET 标记时选择物理Network并让Service收到回调，但同LAN服务器的域名仍可能在旧原Go固定 223.5.5.5 物理DNS上不可解析。本切片只在**Android未验证有公网**、且用户填的是WBD服务端域名时，由 `RootClientService` 的既有**启动线程**调用 `Network.getAllByName(peer)`，严格使用同一当前选定handle，取有效IPv4（可能先返回AAAA），重新核验原 PhysicalNetwork 接口/ifindex/IPv4/MTU后，把**该IPv4**交给原Go `--peer-ip`。无本地A记录/本地DNS查询失败则回到原Go已存在的`--peer-host`/223.5.5.5引导，**不降级原标准TLS、RouteKey/认证、Rust M3/PN和owned Stop**。这不是“系统netd DNS已进入WBD”：仅为WBD自身*连接前*的冷域名引导，普通应用的 `getaddrinfo` 仍由系统Resolver处理，原M4只处理已进入TUN的应用UDP/53。无实机/服务器/重压测权限，BUILD/Host/真实LAN E2E须按独立 SOURCE 记录。


> **2026-11-22 B27 LAN-only Wi-Fi/USB Ethernet 原物理出口**：基线 B26 `c48d5923` 已由同源Actions验证11 SUCCESS/4 SKIPPED（Android签名APK＋原Go/Rust双ABI＋Linux原服务端Oracle，非手机E2E）。原 `PhysicalNetwork.available` 与 `RootClientService.onCapabilitiesChanged` 均要求Android `NET_CAPABILITY_INTERNET`，同时回调只注册Internet Network；因此有实际网卡IPv4、ifindex、MTU、可达**局域网**WBD服务器但被Android标记没有互联网的实体Wi-Fi/USB Ethernet会在UI不可选或监听丢失。B27将真实物理出口资格明确改成Wi-Fi/蜂窝/Ethernet且非VPN＋严格Kernel/LinkProperties本机IPv4同源读回，NetworkRequest按三类实际TRANSPORT订阅**无需INTERNET**；Internet capability本身变化不再释放已有同一原生owner。UI对无此标记的Network单独标“仅本地链路”，可填同链路可达的服务器**直接IPv4**与独立TLS SNI；不自动切网、不跳过原Go认证/32/M4与owned Stop、不更改主线HTTP/TLS或Rust RAW/TUN/DNS。这只完成软件接线；Android实体LAN接入/应用业务/E2E/CPU均NOT_RUN。Android系统netd DNS仍未由UID规则捕获。


> **2026-11-22 B26 日常使用接线（当前SOURCE的CI另验）**：在 B25 `776cec4f` 原Go/Rust双ABI、签名Root APK、Host原Linux Oracle `11 SUCCESS / 4 SKIPPED` 基线上，解决每次GitHub Actions调试签名变化卸载时 `noBackupFilesDir` 预设丢失：Root Activity 经 Android SAF 显式导出/导入正式B22/B25 `RootConnectionSettings` 非密钥设置，8192B上限；保留服务器、SNI、账户、MTU、AEAD、Fixed/Auto/DNS及包名+UID，不包含Keystore密码/RouteKey、PEM、物理Network handle或Root授权，不自动Start。导入冷表单并重新用当前 PackageManager检查包名+UID；签名升级后密码/RouteKey需要用户重新输入。进一步在原 `InstalledAppCatalog` 的launcher可见范围外**只增加 Android manifest `<queries>` 定向 text/plain `ACTION_SEND` 与HTTPS `ACTION_VIEW` 处理器**，供真实无Launcher但可见的App选择，Service仍使用同一冷PackageManager真实 UID 复核，不申请 QUERY_ALL_PACKAGES。此处**未接入全系统netd DNS或系统UID**；原M4只处理进入TUN的应用DNS。B26独立Action/Host/签名产物不是实体手机 E2E 或CPU结论。


> **2026-11-22 B25 Android多包共享UID的连接设置回填修正**：原 `SelectedAppGroup` 的稳定权限范围为**16个包名、最多8个不同App UID**，B24新增批选也复用这一约束；旧B22 `RootConnectionSettings` 却在写/读本机预设时硬限8个包，导致9–16个**同UID**合法App组合丢失。B25本地保存及读取全部改用原 `SelectedAppGroup.MAX_PACKAGES/MAX_UIDS`，并沿用 `InstalledAppTarget.validPackage` 与UID有效范围；测试覆盖16个同UID包来回、9个独立UID拒绝和17包拒绝。并不放宽实际内核route UID、Root权限、Go TLS/AEAD、Android包可见性；仅修被打断的日常配置恢复。同源Host/签名APK结果须看B25 SOURCE，设备/服务器/性能NOT_RUN。


> **2026-11-22 B24 Ethernet + App列表日常功能软件切片**：基线 B23 `17a5343c` 的同源 ARM64签名APK、双ABI/Host/Linux Oracle 11 SUCCESS/4 SKIPPED。原Activity的物理Network筛选及Service回调只认Wi-Fi/蜂窝，现加入Android真实 `TRANSPORT_ETHERNET`，原RAW/TUN/标准TLS/UID路由未改；Activity刷新/恢复时保留handle、ifindex、IPv4、MTU**完全相同**的选定Network，不自动重启或切换root会话。Selected-App模式加入本地label/package/UID过滤与按匹配结果批选，保留隐藏已选、依旧由原 `SelectedAppGroup` 限8个不同UID/16包并经真实PackageManager重新核验。遵守既有狭窄Android包可见性：只展示launcher可见App，不请求QUERY_ALL_PACKAGES、不获取系统/Root UID。B24以其新SOURCE的实际Action为编译/Host判据，不擅自运行Android实体或Linux服务器；Ethernet物理联机/应用TCP UDP、netd系统DNS及性能仍NOT_RUN。


> **2026-11-22 B23 严格TLS CA本机复用**：补齐 B22 连接设置恢复后“严格TLS勾选恢复，但旧本地CA未显示”的缺口。复用原 `wbd-server-ca.pem` 0600私有文件，导入时保存、重开Activity读回已校验证书、用户可手动清除；原 Go标准TLS/身份校验默认off、Rust M3/PN、UID owned Stop均不变。Android实机TLS CA恢复及业务仍未测；以最新SOURCE签名APK/Host为准，不擅自对接服务器。\n\n> **2026-11-22 B22 最新分支状态**：B21 [#44937445205](https://github.com/lly8666/wbd-next/actions/runs/44937445205) 的双ABI/Host/签名ARM64 Root APK/Linux Oracle 11 SUCCESS、4个KSU客体SKIPPED。B17显式Fixed、B19显式Auto→原Rust成熟Quality切档、B20真正FEC请求/应用读回与App UI、B21原M4现成内核收发数值可按需查均已接线，**不是Android实机E2E或性能PASS**。B22 进一步补Root App普通连接设置无备份本机保存/恢复、选定App按真实包名+UID复核后重选；普通模式默认Normal/off；不恢复物理Network/已授权内核路由、不自动Root Start。B22 CI待本SOURCE检查。**真实双端TCP/UDP第一交付、Android系统netd DNS、物理CPU/吞吐仍是主要缺口**，不要复活历史B14“Go Fixed永远拒绝”的旧阶段性陈述；无设备授权前继续软件闭环及同SOURCE Host验收。

> **2026-11-22 B14 Fixed 原 Rust M4 定向 MTU/受保护启动准入**：Android 原 `ProtectedScopedOwner` 的预算接口现共用同一个 `FrameBudget::derive`，feature3仍是 `FixedOff`，受保护feature7为原 `FecReservation::V3Fec2Fixed` 精确预留14B，和原 Go TLS后 `configureTunnelMTU` 的统一冷预算吻合。M4 唯一 TX readiness worker 冷启动时按 feature3/7 选一次预算，保留其小包 slab/TUN 优先、真实 PN/RAW；原生 `start` 已接受 feature7，但只有同原TLS generation 的 Fixed PENDING、M3 FEC RX、已绑定 PLAN027 QualityTx、未存在早期未分类记录才可启动，原 Normal/off feature3门不变。**Go `ConnectAuthenticatedPeer` 仍于 TLS 前拒绝 Android Fixed/Auto；可构建的Rust功能尚非产品开放/Android↔Linux E2E。** Fixed超本方向内MTU包仍需共享DF0 IPv4分片与DF1 PMTU闭环，下片处理，不允许静默降回Normal/off。

> **2026-11-22 B13 Fixed 原 M4→PLAN027 成熟 M2 软件闭环**：复用主线已审 Linux Auto `OriginalQualityTx` 有界 START/CLOSE、`SendWindowSampler/SendHistory`（共享实现，不造Android版M2），每一个原 Android M4 已确定内核复制的 kind2 source PN 参与本修订的 sender first-send；kind3 parity不进 F；原 PN/同一 socket 发送已认证 kind1 START/CLOSE，只有肯定内核复制才激活/关闭窗口。原已认证 M3 kind1 Quality 进入真实本地方向/epoch/PN范围/first_sent/3秒成熟的 `assess_wire`，只有新匹配成熟的正向 witness，且同一唯一 Fixed 修订确有 source RAW + parity RAW 肯定复制，才从 Native PENDING→APPLIED，C ABI readback 可读；缺失、重放、UNKNOWN、伪造零损或过期永远不置位。Linux 同原 owner 的 Fixed 服务端现也启用已存在的 `QualityRx`（只是对已认证 START/CLOSE 报告，非旧逐包 M2），让该协议有潜在真实对端；Go 及 Android CLI 产品 Fixed/Auto、原 `loop_start` feature3-only 不变。本片仅编译/Host/签名APK/Linux Oracle 软件验收，不把未运行的 Fixed 真链路算通过；下一片完成真实固定MTU/包路径和线下可实测接线后才考虑开放。

> **2026-11-22 B12d Android Fixed 认证 PENDING 接收与低频反馈实证（软件门）**：修正 B12a “先 APPLIED 才允许 FEC RX” 的循环依赖：同一原 Go TLS feature7 + 原 FFI Fixed PENDING revision 后，允许原 RAW/M1/M3 单 AEAD+unique PN 接收 kind2/3，经过 Fec2LiveRx source/repair + 原 /32/DNS/TUN；原受保护 kind1 才统计真实 PLAN027 low-rate Quality 报告和 Signal，不读外层 TCP ACK 充数。扩展原 M4 Native 低频数字读回为7项，全部来源于实际 RAW/TUN 或已认证 M3 opener。**本片只允许先收真证据，原 APPLIED=0、Android Fixed/Auto Go 入场门与 loop_start feature3-only 都不变。** 下一步将已认证的真实 low-rate Quality 与 TX first-copy 绑定到同一 native M2 成熟状态，形成准确 APPLIED，及真正 Fixed TUN MTU/大包路径后再开放用户功能。

> **2026-11-22 B12b/B12c Fixed 原 M1/M3/M4 TX 与控制接线（软件门；模式仍闭门）**：在 Android 同一原 Rust owner 上接入 `FixedStream::offer_source` 原 TUN M1 source-first → `fec_v2::source_into` → 同一 `seal_fec2_product_one` AEAD/PN → 原 M4 RAW `sendto` 真 copied；一个 readiness turn 最多一次4行 `poll_parity_quanta`，用真正 RAW copy 给 `DriverProof::Copied/NotSent`，优先新业务后排 parity，不另建线程/队列/PN。原 Go Android Fixed/Auto 配置桥从永久unsupported改成与 Linux同一原TLS feature7 PENDING stage/readback，Rust实际 PENDING 修订读回、双ABI ELF函数与四个真实M4 copy/TUN计数，Stop/join后先 `FixedStream::stop` 再原 crypto Stop。**Android `ConnectAuthenticatedPeer` 仍前置拒绝 Fixed/Auto，原 `loop_start` 仍 feature3-only，RX APPLIED 仍0；Auto reprofile、FEC源大包分片、M2真实反馈和 Fixed正式产品开放未完成。** 不能把新的 FFI 编译当成 Fixed Android E2E。

> **2026-11-21 B12a 原 Android FEC2 RX 数据面软件切片（Fixed继续闭门）**：原 M1 RX worker 的 FEC kind2/3分支复用同一原 M3 AEAD/unique PN replay，送现有 `Fec2LiveRx` 首交付/RS16恢复，再经原客户端 /32、DNS逆映射和唯一 TUN writer；只有真实写入才累计systematic/recovered。该接收缓存仅由Go原受保护feature7 handoff预备，并在原Stop/join后退休。由于 TX/parity/M2/真实 APPLIED 尚未接，修订固定为0、Android loop_start仍仅接feature3、Go FixedPending继续unsupported：没有任何可由CLI/UI调用的FEC2启用路径。下一片补TX原FixedStream与M4 copied-prefix/M2，最后才可开放Fixed/Auto。

> **2026-11-21 B11b App→Go 接线（真实原生数据路径）**：签名 Android App现提供 `startup-padding off|tls|flows`，默认off，Activity→Service→受保护Go `--startup-padding` → B11a原Rust M4 TX &真实RAW-copy计数；旧Intent和全部Java overload保留off。只影响进入Normal/off隧道的普通原LINK数据，不对DNS物理、Jumbo LINK、Health、FEC2 padding。尚未做Android实体业务及性能验收；不将它描述为FEC Fixed/Auto实现。


> **2026-11-21 B11a 原生数据面接线（待同源CI）**：在原Go已认证`--startup-padding off|tls|flows` 的正常客户端产品中，移植原Rust `TunnelStartupPadding` 与同一 M1/M3 `seal_normal_off_one_padded` 到 Android 真实TUN→RAW M4 TX worker。保留按真实sendto复制成功才记账、记录长度/MSS/外层MTU限制和原Go冷模式真实读回，默认off不变。本片先接原生 CLI→Rust，Android App选项另片才开放；Fixed/Auto/Game仍由现有Go/Rust拒绝门阻断，设备性能/真实业务未验。


> **2026-11-21 B10（真实 TUN 队列冷配置）**：原 Go 已支持 `--tun-txqlen-packets 500|2048`、`ip link set` 和严格内核读回，但 Root App 固定500。现在 Android App 可选500（原默认）或2048，走 Activity→同代 Service→原 Go→原内核 owned TUN 应用/读回，无任何新逐包队列或 Rust 分身。2048 是否提升吞吐/延迟没有实体性能证据，也不表示 FEC2 Fixed/Auto 已完成。Fixed/Auto 下一步仍须把原 Rust M1/FEC2 M3/M4 真进程生命周期接通，原 Go 拒绝门保留。


> **2026-11-21 B9 软件功能接线（真机及性能待验）**：原 Go `--record-cipher` 及已认证 policy、原 Rust `RecordSuite::try_from(identity.cipher)` 已支持 ChaCha20-Poly1305/AES-128-GCM/AES-256-GCM；Android App 现在提供同三项选择，并经 Activity→Root Service→原 Go argv 进入既有原 M3 AEAD/PN。默认 ChaCha20 兼容旧 APK；旧 Java 参数重载及 B8 外层 MTU 入口不变。没有新增加密实现、TLS/PN 前导、逐包 Java/Go 或“更安全”拦截。AES 可能有硬件性能收益，但未做 ARM64 实机速度/兼容测试，不宣称更快。未接线 Fixed/Auto/Game/系统 netd 与其他功能资格仍按 B8 记录。


> **2026-11-21 B8（软件接线；实机未验）**：Android App 原来固定 `--outer-mtu=1460`，现在给用户完整外层 IPv4 IP MTU 输入（576..1500B，默认1460，不含L2）。原生产路径 Activity → Service → 原 Go `--outer-mtu` → 已有 Rust 冷预算 → 内层 TUN MTU 自动应用和内核读回；旧 Java argv 重载继续默认1460。真实物理路径/MSS/record 限制若使 MTU 不可用则保留原 Go 错误，不静默截断。当前以软件补功能为先；Fixed/Auto/Game、系统 DNS/netd、物理 TCP53、IPv6、热点、自动切网及新 SOURCE 设备/性能 PASS 仍未完成。


> **2026-11-21 B7 原 M4 物理 DNS 重传与设备可验收**：解决丢包时相同 App IPv4 UDP/53 DNS 重传每次消耗新 synthetic DNS ID/64 槽的问题：原 `PhysicalDnsUdpFlows` 仅在相同源 IPv4、原解析器、UDP 源端口、原 DNS ID、QNAME/QTYPE/QCLASS 且槽未过期时重用 synthetic ID，不额外占槽；不同 App/解析器/请求仍隔离。仅新建槽 sendto 失败才取消，复用的重传失败不会丢掉此前真实发送的有效请求映射；成功逆映射消费一次，Stop 精确清空。新增两个 Rust 原 IPv4 测试、App 手动「查看本会话DNS收发」脱敏按钮（无 Root / 额外联网）、用户自控 `device_first_run.py` 只读新增 B5/B6 原 M4 CN/非 CN/TC/TCP53 固定事件汇总及 Python Host 回归。原默认隧道 DNS ON、物理/CN模式 OFF、TLS 校验默认 OFF/可选 ON；不操作 Android 系统 netd 或用户手机/服务器。**Fixed/Auto/Game/FEC、IPv6、TCP53物理代理、热点与实体设备应用 E2E 仍未完成**；BUILD_PASS 不能冒充实机成功。\n\n
> **2026-11-21 B6 真实 DNS 分流计数与 TCP53 兼容**：在 B5 已通过的 CN8503 原 Rust M4 单 TUN reader 上，把普通小包和 jumbo/EDNS 的域名路径决策收敛为同一个纯 Rust `v4_android_dns_route`。合法完整 IPv4 UDP53：CN 物理 223.5.5.5，非 CN M3 加密隧道 1.1.1.1；其他两种旧模式、默认设置不改。Android App 的普通 TCP53 **原样经原 M1/M3 WBD 隧道**，按真实完成的原 RAW 复制计数，不是新建直连 TCP53 代理。物理 UDP 回复 DNS TC=1 仅在实际写入原 TUN 后记录，**不等于客户端已发起 TCP 重试，更不等于该 TCP 查询拿到答复**。新原生只读 ABI 增加 `cnptx/noncnraw/tcpraw/ptctun` 四个实际收发计数，并由原 Go 低频 Pulse → Root Service → 独立 B6 数值与固定事件报告；旧 A47/B3d/B4 18/20/23 数值收据原格式兼容。增加同一原 Rust 物理 TC IPv4 反写+非 CN 原隧道 IPv4 逆映射+Stop 的 Host 组合测试及签名 APK 源码门。没有 Android 系统 netd DNS 的真实捕获或全局改写；这个范围仍须单独明确验证，并在设备授权后才能声称真机 E2E。TLS 校验默认 OFF、隧道 DNS 默认 ON、物理/CN 模式默认 OFF，全都保持。


> **2026-11-21 B5 CN8503 普通 App DNS 分流**：在原 B3/B4 全隧道/全物理 DNS 兼容路径外，新增显式第三模式 `--android-cn-dns-split`（UI 默认 OFF，原 UI 全隧道默认 ON，TLS 证书验证默认 OFF）。原 Go 先用已存在的固定源 CN8503 Go 规则完整验证原文件的 8431 domain、69 full、3 regexp，然后将**同一份原规则字节冷传递一次**到原 Rust M4；Rust 自己用冷编译 HashSet/RegexSet 解析完整原 IPv4/UDP53 QNAME，CN→同一物理 Network 的 223.5.5.5 UDP，非 CN→原 M3 AEAD 隧道 1.1.1.1，两个原有 inverse-map 回 TUN；无 Go/JNI 逐包、无第二 TUN reader、无 FakeIP。物理 DNS 的 UDP 发包不等于 Android 系统 Resolver 已接管；Split 模式目前不含系统 DNS、TCP53/回落、IPv6、DoH、Fixed/Auto/Game。Host 新 SOURCE 的真实 8503 Rust/Go 匹配、ARM64 签名 APK、Linux Oracle 待 CI 实证，手机/用户服务器未授权不操作。\n\n
> **2026-11-21 B4b Root Service 实生产传参补齐**：B4a 双 ABI Host 的 Java 收据已修复，但源码门发现 `physical_dns` Intent 未进入 Root Service 的 owner/launch/argv，现已接通同一生产参数链；该修补不涉及数据面和任何强制安全检测。等待新 SOURCE 原 APK 签名/Go Host/Linux Oracle，不用旧失败或前置绿色推断真实手机 DNS。


> **2026-11-21 B4a 新旧安卓收据兼容修复**：B4 源码首次 CI 的 Root App Java Host 因 M4 数值新增物理字段后拒绝历史 B3d 收据而失败。此轮生产导出读回同时兼容 A47/B3d/B4 三种确定字段格式并保留真实历史值，不制造物理DNS成功，原数据面不变；只在新 SOURCE CI 完成后登记 BUILD/Host 资格。


> **2026-11-21 B4 实际物理 DNS 模式（非 CN 分流）**：在原有 B3 默认隧道 DNS ON、TLS 证书校验默认 OFF 不变的基础上，为普通 App 进入原 WBD TUN 的 UDP/53 提供独立显式物理模式，默认 OFF。Root UI 的隧道/物理 DNS 选项互斥，原 Go CLI 同时收到两者时由显式物理模式优先；不拒绝旧参数组合、不添加安全门。App→RootService→原 Go argv `--android-physical-dns`→真正 FakeTCP/TLS/受保护 /32 租约→RAW+TUN 绑定→原 Rust `wbd_m0_embedded_go_android_physical_dns_enable/effective` 冷授权→现有唯一 Rust M4 TUN reader→绑定同一 physical Network 的 UDP Socket 到 **223.5.5.5:53**→已有 64 槽原解析器 DNS ID/QNAME/地址逆映射→原 TUN 写回。沿用上一轮 B3d 的真实计数口径：`dnsptx` 是原物理 UDP sendto 成功；`dnsprx` 是原逆映射应答写入 TUN 成功；`dnsperr` 是物理 DNS 失败。全部只代表已进入 TUN 的普通 App IPv4 UDP53，不是 CN8503 自动 QNAME 分流、不是 Android 系统 netd DNS、不包括 TCP53、IPv6、Fixed/Auto/Game。Host/Linux Oracle/双 ABI/签名 APK 与真机实际网络执行必须分开判定，不凭 BUILD 宣称手机解析成功。无用户授权不操作真机或服务器。\n\n
> **2026-11-21 B3d DNS 双向实绩接线**：原 Android Rust M4 在完整原 DNS IP 确定 RAW 复制后记录发送（Jumbo/LINK20 全部帧完成才算），在原 M3 AEAD/唯一 PN/逆映射 DNS 答复确实写入原 TUN 后记录回程；仅通过现有 Go Pulse→Root Service→本会话诊断收据呈现，不增加第二 TUN reader/Go 逐包，也不更改 A54 的 TLS/DNS 兼容默认。RAW_COPIED 仅是本地发出，INVERSE_TUN_WRITTEN 仍不是 Android 系统 Resolver 或 App 成功解析。CN8503/物理223.5.5.5、系统DNS、TCP53、IPv6、Split、Fixed/Auto/Game 待续接；无新 SOURCE 真机证据不得标 E2E PASS。

> **2026-11-21 A54 兼容性恢复（用户纠正 A53）**：A53 新增的 Android TLS 默认强制验证、实验 DNS 默认关闭、Java/Go 组合限制没有用户授权，现已全部撤销；当前恢复 B3 原有 Android App 默认 TLS 验证 OFF、隧道 DNS ON，原 Go CLI TLS 验证显式可选、DNS 开关独立。此处说的是 A53 额外兼容性门回滚，不变更原 FakeTCP/TLS 建链、受保护 Admission、Rust AEAD/PN/M4、真内核 TUN/RAW、路由/owned Stop。源代码和验收以 A54 提交及 CI 为准；A53 devlog 是历史行为，不再是现行要求。仍不得把编译/Host/旧手机日志写成当前 Android 真 E2E PASS。

> **2026-11-21 B3 继续开发**：按 Android 功能卡推进真实产品功能。本轮解决“隧道 DNS UDP/53 原生数据面已有64槽改写/认证回包与Stop，但无冷授权入口”的缺口：Root App有明确可关的开关，原 Go/TLS/lease/同代 RAW+TUN 绑定之后才允许原Rust M4启用普通应用 TUN UDP53→1.1.1.1，使用原M3/replay校验和反向地址映射，不增加第二reader、Go per-DATA或系统网络写入；原生ABI与真App/Go源码门/Host均必须同源通过。Android系统Resolver/netd、CN8503→物理223.5.5.5与TCP53、IPv6/分流、Fixed/Auto/Game、热点与所有应用/弱网/性能仍未凭这项接线取得资格。此任务巨大，按功能卡逐段落实代码和证据，不把B3编译当作全功能完成。

> **2026-11-21 A51 执行口径**：用户要求将最新 main `31ce49d9467cde33cce2d61c968129c3173a4b8d` 的修复完整并入 Android 实验分支。共同源码冲突中同一问题以 main 结果为准；尤其采用 main 的共享 `parse_data_packet_fast`、H2229 ACK、原 Go TLS/CLI、Windows/Linux 已验证修复。Android 独有 Root App→原Go冷控制→原Rust M4/原物理Network/UID路由/TUN/Stop 保留并核接线。已知 A48 真机 Normal/off `auth=1227,rtun=1218`，但这不是用户确认的应用Mbps/RTT或所有模式完成。**全功能接线一次排查，不以静态编译冒充运行资格**：DNS系统接管、Split/Fixed/Auto/Game、切网、热点、IPv6 和 Android 全App 核心均须真实调用链与单独验收；主线 Linux/Windows 成功不自动使 Android 可用。下一验收以合并SOURCE双ABI原件/签名APK/原Linux Oracle起点，之后逐层打穿 Android 真业务功能范围。

> 2026-11-20 A45 新实机接续（不替代本计划唯一优先级）：A44 SOURCE `8da73ff0428291b006b28f762cf18ea9122d4784` 真实 API36 selected UID两次`ORIGINAL_GO_UID_ROUTE_GET_MATCHED_TUN`、原Rust `TUN_IPV4_SEEN`/真正`APP_RAW_TX_COPIED`，但没看到`APP_REVERSE_TUN_WRITTEN`；这仅证明手机向外做了业务内核复制，非对端收包。用户另一个 Ping 应用不一定属于选定UID，不能将其不通冒充完整ICMP隧道失败。继续选定应用组（Chrome+Ping APP），先查原Rust RAW RX可读/解析/认证/反向TUN与Linux服务端入站和本机TUN应答，再研究公网forward/NAT/DNS；**不为此切换全局代理**。A45 同源 HOST/ARM64 构建和新 SOURCE 真机结果分别记录，不造PASS。后续仅以最新SOURCE/真实Actions/devlog定论。

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

### A39｜API36 A38安全TXT零事件：Keystore GCM IV与START前置保存阻塞

用户自行使用 `9a4ce82c5247fd3d099155759fe2d23223eac1ef` 的签名APK，导出的 `WBD_ANDROID_ROOT_SAFE_DIAGNOSTIC_V1` 为 `receipt_event_count=0`、`last_session_stage=NOT_STARTED`，不能得出Go/TLS/Root失败，也不能证明用户已按过Start。代码实审找到A38可能造成此症状的两个连锁缺陷：A38把 `RootEncryptedCredentialStore.save` 放在 `RootClientActivity.start` 内 Service dispatch 之前，任何异常即中止启动且没有Activity级收据；A38纯JVM JCE GCM自行设置随机IV，但AndroidKeyStore .setRandomizedEncryptionRequired(true)要求Provider在encrypt init时自行生成IV，实际Android平台可能拒绝调用者IV。A39改真实AES-GCM record encrypt为Provider自行生成随机IV并用cipher.getIV持久化，与原decrypt AAD/record格式兼容；把加密自动保存变为非致命side effect，失败可继续START原Go/Rust与原0600密码/key路径，同时固定收据记保存失败。Activity在onCreate/UI START触碰/预检拒绝/Service dispatch申请及成功/失败均写无秘密固定事件；报告器以后端START_REQUESTED或新UI_START_TAPPED为会话边界，精确识别“仅打开没点击”“预校验失败”“已dispatch但Service未收到”，避免零事件掩盖前置功能问题。Host/JVM需要真实双Provider IV随机性及GCM加解密/失败拒绝、非致命save callback、旧TLS失败覆盖、nativeGo入口无改动、原Linux Oracle和签名APK同源PASS。Android真机Keystore和连接未测，不能宣称一定解决用户新0事件。

### A38｜2026-11-20 A37实机“已关闭证书校验”仍UNKNOWN_AUTHORITY及登录凭据持久化

用户API36 A37产品SOURCE `033d96f81535a5a1c5a7ffe3b6075eb82b1e3227` 两次真实日志，均 `ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED`、TUN/真实RAW SYN+SYNACK/Association、原TLS payload TX+RAW peer payload RX，最终 `TLS_HANDSHAKE_FAILED_CERTIFICATE` + `TLS_CERT_REASON_UNKNOWN_AUTHORITY`，RST guard命中并STOP_CLEARED。复核 `r0/go_overlay/internal/realityfront/admission_v4.go` 真正握手前无条件 `tlsCfg.VerifyServer=true` 覆盖A37 Go解析出的false，根因已经源码确认。A38移除该覆盖，直接保留原ClientAdmissionConfig.VerifyServer，真正握手前从同一tlsCfg记录 `TLS_CERT_VERIFY_EFFECTIVE_DISABLED/ENABLED`，新增真实自签名 TLS1.3 + Original Protected admission 三模式 Host测试：默认false无CA必须成功，严格true无CA必须拒绝，严格true信任该CA必须通过。不要再将“flag disabled”误判为实际uTLS未校验。

用户另要求Settings里密码与简版原始RouteKey持久化：新增AndroidKeystore AES-256-GCM加密独立本机不备份存储（固定版本/随机IV/AAD/防篡改），只保存原始UI密码/短Key以便重开APP自动回填；原来的路线Key派生缓存仍只存派生结果，Go入口仍只读取临时app私有0600秘密文件，不进Intent/argv/SAFE TXT/backup。提供明确手动保存与清除按钮；在合法START前自动更新本机快照，不再每次点击START清空输入框。Host JDK真实AES-GCM round-trip/伪造/错误Key/非法短Key负例、Android build Keystore adapter、新版签名ARM64 APK与Linux真实Oracle同源验收。Root临时防火墙、/32/UID路由与精确恢复未改变。默认无TLS证书身份验证虽与main一致，但存在MITM风险；真正保护认证、租约、Rust M4业务及手机一键恢复仍未证。

### A37｜恢复主线原Go默认不校验TLS证书

核对 `main@2e615b90` 原Go已有 `--tls-verify-server` Bool默认false，TLS.ClientConfig.VerifyServer来自此布尔值。实验A36硬编码true，用户明确请求APK恢复主线默认。A37在实验原Go恢复Bool默认false、Android APK UI未勾选严格验证、Service/真实Go argv仅勾选时传 `--tls-verify-server` 与私有0600 CA。提供固定脱敏收据DISABLED/ENABLED区分验证策略，真实标准TLS、路由Key的先验识别、保护认证、/32租约、原Rust M4、Root网络恢复等不改。默认非严格模式加密但不验证服务端证书身份，有中间人风险。需同源签名APK/Host Go Java双态/原Linux Oracle及手机用户自测。

### A36｜A35 Android真机证书校验阻塞和临时Root网络恢复

用户A35签名SOURCE `4975c1abf4bc64357f3da246c85dcc15e84d9824` 两次真实API36收据：原FakeTCP Established、真正TLS ClientHello TX/RAW peer payload RX、RST guard真实命中，最终均原TLS证书校验失败；守卫精确Stop_CLEARED。原15秒发包无回包瓶颈已跨越，TLS信任/名称校验还未通过。新增原Go typed x509固定类别、OS_STORE/APP_PEM信任来源；APK通过本地SAF安全导入服务器CA PEM，不关闭任何TLS验证、不自动信任网络证书。新增APK「恢复网络」按钮：精确Stop原Go/Rust owner后，当前APK哈希验证同源Go ELF独立运行 `--android-recover-owned-root`，经root-only journal/flock精确回滚单UID/多UID/全App私有table、peer throw /32及同一连接RST iptables规则；无journal只readback检查专用表/优先级/marker为空，不删除任何外国规则或全局flush。验收必须为原Go route和RST双读回、root shell completion、退出0；失败保留恢复状态/原journal。严格禁止修改系统DNS、主路由、其他客户端规则与绕开TLS认证。下次用户自行验证单App UID，导入匹配服务器真实CA/SNI后Start→Stop/恢复→安全TXT，真实TLS/租约/原Rust M4/应用TCP UDP仍未证。

### A35｜2026-11-20 API36 三次原TLS超时：补原RAW FakeTCP精确RST守卫并分层收据

用户自行使用签名SOURCE `c010f7357d0334c48c479012011b6cdb7dad1e4f` 导出同一台API36手机三次独立有界启动108个固定事件：单UID一次、all ordinary apps两次，都在原Go Args/TUN/RAW → SYN/SYNACK → 真Association Established → 原TLS payload TX sendto → 原始15秒Bootstrap TIMEOUT；原RAW peer payload **三次均NOT_OBSERVED**，原RTO **三次均OBSERVED**，owner清理结束。认证、/32租约、M4、真实业务没有达到。更换预认证App UID范围没有改变此网络瓶颈，下一轮仅单UID。

根因优先候选：原真正Linux netns成功例在客户端和服务端都安装 OUTPUT TCP RST DROP，然而真实Android Root Go原来没有对应内核RST隔离。FakeTCP SYNACK到达无内核socket时Android kernel可能发送RST终止对端，导致原Go ClientHello虽然真实RAW发送却无peer载荷。**尚未经真机验证，不据此宣称修好**。

A35：新增Android Root原Go启动前独立root-only精确iptables OUTPUT过滤 **只匹配选定物理接口、原手机IPv4、对端IPv4、该次随机本地源端口、原服务端目标端口、TCP RST**；禁止全局RST flush、默认路由或系统DNS修改。强制root UID、0600 O_NOFOLLOW/O_EXCL durable journal、flock owner、精确规则 `-C` 和 comment单实例读回；异常重启可按完全验证的旧journal精准恢复；失败则禁止发SYN；Stop验证精准删除，失败保留journal并报告。无密码/路由密钥/ClientHello内容/地址入safe TXT。额外固定收据：守卫_READY/FAILED类、实际该规则命中RST数量是否大于零/计数不可得、STOP_CLEARED/UNVERIFIED；同源 Host fake iptables前向/冲突/重启/Stop负例 + ARM64原Go/Rust签名APK + 原Linux Oracle。真实Android设备网络变化由用户自主测试，不能自动部署。

若下次TLS仍超时：有命中RST则证明至少该规则拦截了匹配RST（不自动证明RST来自内核）；无命中RST应直接转向原Linux服务器RAW/TLS双向证据，严禁继续调密码/证书。Linux原服务器是否也需要等价守卫另行比对现有部署，不自动改变用户服务器。

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
