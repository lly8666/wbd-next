## B96｜专项编译解阻与同源 fixture 复用（当前）

B95 `6545a6940d7973fd8b56d6e6beebb2a67fe8380a` [Action 45432269092](https://github.com/lly8666/wbd-next/actions/runs/45432269092) 6/1/10，CI adapter `route:func` 误写导致编译失败，全部 guest NOT_RUN。B96 修正声明并增加早期 AST/bash/Python/Java fixture admission；九 guest 复用同 SOURCE+SHA256 的普通 App APK；原 B95 DNS/前台 UID/7模式逐 socket TX/Stop 验收继续执行。生产路径不变。详见 [B96 devlog](../devlog/android-root-probe/20261125-b96-specialty-build-unblock.md)。

## B95｜真实前台 UID 与 DNS dump 默认属性（当前）

B94 `881e543e16958478e9f3d975d4997eecfa5d6292` [Action 45427547974](https://github.com/lly8666/wbd-next/actions/runs/45427547974) 11/9/6；七模式真实 TLS/Admission/lease/原 Android native M4/group/Stop PASS，FEC pending PASS，不是远端 wire；普通 App group Java/all AF_INET 双向 TUN 各一次 PASS，其余及物理 baseline EPERM；系统 DNS 规则/NAT/dummy 已装入，kernel dump attr14 导致 readback/cleanup 未证。B95 仅接受内核 disabled suppressor sentinel，非默认仍拒绝；真实普通 App 可见 Activity + foreground importance、UID 两轮 socket + 物理前后、逐 socket native TX 和 DNS owner/query/Stop receipts。九专项隔离并行，详见 [B95 devlog](../devlog/android-root-probe/20261124-b95-foreground-uid-and-dns-dump.md)。不冒称远端 M4/READY 自动恢复/实体 ARM64。

## B94｜真实 Android DNS netlink / UID socket / 冷 ACK（当前）

B93 `860f78d17944167754aaa8064584d84fc9b02b47` [Action 45422304796](https://github.com/lly8666/wbd-next/actions/runs/45422304796) 12/9/5；真实 WiFi loss callback/Stop/恢复手动 START/Stop PASS；三 UID 5500 CN prefixes+peer throw 和 route-get/排除/Stop PASS，普通 App UDP EPERM；七模式原 MSS+Association PASS，TLS deadline；DNS exact netlink ADD/GET/DEL PASS，Android ip 不支持 ipproto 且读回丢字段。B94 正式系统 DNS 仅 cold netlink rule I/O（同 journal/NAT/Stop/Restore）；原 server CI ACK dispatch、Java/AF_INET UDP + 物理对照及独立 native stage receipt。9个隔离 guest 并行，B93生命周期不重复。详见 [B94 devlog](../devlog/android-root-probe/20261124-b94-android-dns-netlink-and-cold-ack.md)。未证明 remote M4/READY 自动恢复/ARM64手机。

## B93｜真实故障分层及隔离并行（当前）

B92 `982bad849468b1cb59faaabd3861ab3f4d7c33d7` [Action 45416465988](https://github.com/lly8666/wbd-next/actions/runs/45416465988)：真实 RootService 前后台/Stop/Normal→Fixed 冷启动 PASS；WiFi loss 未证；七模式夹具缺 Rust SYN MSS 初值 panic；CN UID 已安装5501 throw 和规则但超时未清理；系统 DNS UID batch exit255、原清理 PASS。B93同正式 Run Rust MSS/record cap、TUN FD nonblock 修复与逐阶段 receipt；三个 UID 独立 guest；系统 DNS 冷 stderr 与 exact rtnetlink capability probe；独立真 NetworkCallback/恢复手动 START。九专项+一 lifecycle guest，保留原安全/性能契约、无基准，不冒称 peer M4/READY 自动恢复。详见 [B93 devlog](../devlog/android-root-probe/20261124-b93-real-failures-isolated-next.md)。

## B92｜隔离并行 Android 专项（当前）

B91 `2b6b904b874065dd7a03f1152ed836662e606e05` [Action 45412992618](https://github.com/lly8666/wbd-next/actions/runs/45412992618) 真 Bionic 物理 UDP 与 TC→同 Network TCP DNS PASS；系统 DNS dummy 创建语法 FAIL、后续12项 NOT_RUN。B92修原 cold ip dummy/alias 顺序；7个隔离 KSU guest 并行 UID、Normal、Game2、Game4、系统物理/隧道/CN DNS，共用 native/CN artifacts，不等 Linux server。独立第8个 guest 验收生产 RootService preauth 前后台/Stop/模式重启/真实 WiFi loss与恢复手动 START；不冒称 READY 自动恢复/配置冷切或远端双向 M4。独立结果和清理 readback，guest 间不互相阻断，不重复既有物理 DNS/七模式 preauth，无性能基准。详见 [B92 devlog](../devlog/android-root-probe/20261124-b92-isolated-parallel-android-acceptance.md)。

## B91｜真实 Android 内核、系统 DNS 与认证后 native 接管（当前）

B90 SOURCE `0d710fd6e39abb4d85c6935f56b09756d28c47ea` [Action 45409736062](https://github.com/lly8666/wbd-next/actions/runs/45409736062) 11 SUCCESS/1 FAILURE/5 SKIPPED；正式 APK/双 ABI/Host 原 TLS/Game/Rust PASS；KSU 在文件 mv/chmod staging 权限失败，专项未运行。B91复用真实 D1 root-owned cp、修正 route-journal.json，独立验收原 UID/CN FIB、普通 App UDP↔真实 TUN、Android Network Resolver 物理/隧道/CN DNS（隔离 TUN DNS fixture）、原 Stop；原双端 Go FakeTCP association 进程内 cold wire → 真实标准 TLS、原认证/租约 → 正式 Go/Rust Android Normal/Game 七模式真实 TUN/RAW/native M4 startup、UID 发包/native TX/Stop。非 Android↔Linux 物理 peer E2E，不测性能，不加产品防御。各场景保留真实结果，旧 owner 未清理不继续。真实 RootService 切网/配置与最终 ARM64 仍待验。详见 [B91 devlog](../devlog/android-root-probe/20261124-b91-postauth-native-and-system-dns.md)。

## B90｜B89 真实结果收口；Android 内核及 DNS 专项（当前）

B89 SOURCE `3cba0860e93606a5559955bd74eff4b4263d2ffe` [Action 45406291224](https://github.com/lly8666/wbd-next/actions/runs/45406291224) 9 SUCCESS/2 FAILURE/6 SKIPPED；[KSU Job](https://github.com/lly8666/wbd-next/actions/runs/45406291224/job/138490237533) 七模式 preauth/cleanup 7/7 PASS，独立 Bionic 原 TLS PASS，peer TLS/lease/M4 NOT_PROVEN。两失败为同一 CI oracle 脚本重复插入与引号，B90 修复。

B90一次 KSU boot 使用原 Go TUN/rootjournal/真实内核与普通 App UID UDP 验证 single/group/all+排除/CN/Stop；真实 PhysicalNetwork+原 Bionic DNS dialer 对本地 fixture 验证 UDP、TC→同 Network TCP。测试 /32 非认证租约。系统 Resolver、隧道 DNS、认证后 native handoff 与切网后续单独验证。B90 待实测，不再重复七模式或跑性能基准。详见 [B90 devlog](../devlog/android-root-probe/20261124-b90-android-kernel-specialty.md)。

## B89｜用户验收范围更新：停止性能测试，集中 Android 接线

B88 SOURCE `5a286b6bfa9f6094e24d2d162ccf097d116a2d0c` [Action 45401336748](https://github.com/lly8666/wbd-next/actions/runs/45401336748) 6 SUCCESS / 1 FAILURE / 10 SKIPPED。构建失败为 PLAN030 Linux management_snapshot_linux.go 在 GOOS=android（同时满足 linux build tag）引用仅 Linux/FEC build 的 V4LinuxGameCohortID。B89对三份 Linux 服务管理文件加 !android，Android只保留共享入口的冷编译适配；手机不接入服务器管理。修正H2408 SYN/TLS独立期限的过期静态测试。B88治理/维护亦失败：main H2409 M0 cursor last_tested_source 与既有 evidence_refs 不一致，保留真实红灯，不修改M0 cursor或放宽治理。B88性能矩阵在依赖失败后SKIPPED，不重跑。

用户新指令：不做性能测试，其他平台既有结果保留，集中实际Android接线、尽可能复查A48真实ARM64 Normal/off历史通路与其余六模式差异。A48真机原认证、/32、双向M4及Stop曾通过，非最新源性能或全部模式验收。B89使用一个 Android16 x86 KSU boot、一个原Linux shared server、同源CI-only APK，连续七种模式 Normal/off、Fixed6、Auto、Game2/off、Game2/Fixed6、Game4/off、Game4/Fixed6，默认无附加DNS/outer repair，TLS证书验证OFF符合真实产品默认。实际生产RootService发出参数、Go实际解析mode/profile/lanes与预期匹配、真实TUN、首个已绑定RAW和SYN sendto（Game此时只有首lane，不声称全部lane），每模式通过原Stop、等待owner结束、核查TUN消失和原RST规则/日志无残留。未清理不强行重启。独立CI Bionic Go真实TLS/admission测试二进制（同源、原关联夹具，非APK），在相同Android guest运行既有Normal各FEC、mixed Normal/Game、Game冷组、epoch和FEC wire/证书测试。Host只跑原真实TLS/Android Rust lane mapping/A48-A49 parser等接线功能测试，不跑Linux live dataplane及十四场景性能矩阵。标准正式ARM64 APK、原Go/Rust ABI、DNS等现有构建门保留。所有新SOURCE结果待CI，SLIRP/TAP不重开，真机全部模式认证/UID业务/M4和完整Stop不能从模拟推断。

复查重点：Normal三模式共享原Go/Linux client product和Bionic Rust direct TUN/RAW，Game独立原Go冷组→真实2/4 Rust group接管，沿用相同TLS admission、MSS/MTU预算、A48 Android TCP checksum pending→原M3，以及真实UID路由/Stop。Game首RAW/SYN日志只在实际绑定/发出成功后各一次，无新增数据面检查。不加防御、FakeIP、热迁移或替代协议。

## B88｜B87集中软件验证收口；同步 main H2409

B87 SOURCE `eeaa60b4b6d02ff97c1cee03ab282d1cd500ea0a` [Action 45385768439](https://github.com/lly8666/wbd-next/actions/runs/45385768439) **12 SUCCESS / 0 FAILURE / 5 SKIPPED**；正式ARM64 APK、两ABI、Host及原Linux oracle PASS，功能目录PASS。D2真实Android16 KSU [job 138418781855](https://github.com/lly8666/wbd-next/actions/runs/45385768439/job/138418781855) 和 [artifact 14916392463](https://github.com/lly8666/wbd-next/actions/runs/45385768439/artifacts/14916392463)：普通App su、exact Network、正式RootService→原Go、真实TUN+AF_PACKET和SYN sendto PASS，按preauth范围停止。SYNACK/TLS/lease/M4未证明。ARM64 host [job 138418589714](https://github.com/lly8666/wbd-next/actions/runs/45385768439/job/138418589714) 真实收据为 aarch64 KVM_NOT_ACCESSIBLE/ENV_BLOCKED，不是 guest PASS。B85/B86a/B87累计18/18增强场景按各SOURCE和各自范围收口，不跨SOURCE迁移PASS。

B88冻结 main `6b8617626648a6ebed6ecad3e3be63016a3249bb` (H2409)，旧共同祖先 `5b1311c0748452c1c8dac66fc2a6e517777529fa`；46 commits、118 changed files，11个双方变化文件按三方精确补丁及实际合成blob合并，真实双亲提交。H2397–99全模式Linux/Windows native公平、ready service、Linux Game sendmmsg，H2394 Normal off协商MTU，H2400–09 原冷TLS RTO/tuple/NAT cohort/最终ACK、Normal分离SYN/TLS期限和Detach竞争修复。Android保留原Bionic direct TUN、RAW、DNS、Root及设备特化；Normal采用main独立SYN/TLS期限和原Detach竞争/冷ACK，Android Game在每lane真实Detach时复用同一原ACK方法并在旧Go RAW接收窗口处理旧TLS重复段，已有最终ACK收尾保留。main Linux SharedTun公平队列和Windows Wintun ready-order不等同于Android直接TUN路径，未另加队列/防御框架；Android Game4实际CPU/sendmmsg适配另据设备/原worker数据决定。Linux服务器管理完整同步但手机不进入其非nil管理入口。未实现Android热迁移，不部署实体或外部服务。

新SOURCE改变共享协议/数据面，使用 [android-native-matrix] 重新并行两ABI七模式（与B85同标准弱网，便于观察性能变化），[android-guest-retry]仅D2原生新SOURCE preauth；保留标准构建/host/oracle，旧stock UI、ART冷套件不重跑，不开TAP/SLIRP握手/独立旧ELF139。全部新SOURCE结果待CI，ARM64真机端到端及性能未验。

## B87｜真实 KSU 冷套件收口，定向补 D2 preauth

B86a SOURCE `15f2969f89e72f9573243e0122f68bb5ced43ac5` [Action 45381240919](https://github.com/lly8666/wbd-next/actions/runs/45381240919) **11 SUCCESS / 2 FAILURE / 4 SKIPPED**；双ABI、正式ARM64签名APK及完整Host源码门、两Linux oracle、功能目录和维护均PASS。正式APK [14912914468](https://github.com/lly8666/wbd-next/actions/runs/45381240919/artifacts/14912914468)。Android16 KSU实际综合冷套件 [14914477279](https://github.com/lly8666/wbd-next/actions/runs/45381240919/artifacts/14914477279) 的 receipt.json 实证：普通App→KSU su、x86原Go help、实际PhysicalNetwork、ART七类生产helper、四页和四种分流接管UI、ARM64转译原Rust MTU 1389/1375/1373/1358、原Go c-shared help均PASS；不是正式ARM64 ELF或业务E2E。

D2 [14914492915](https://github.com/lly8666/wbd-next/actions/runs/45381240919/artifacts/14914492915) 实际启动原Linux server、普通App→su、Network读回、真实RootService START，随后日志 NETWORK_SCOPE_VERIFIED → START_REFUSED，未启动原Go。对照生产Activity和Service，CI Activity设置 has_ca=true 却遗漏 tls_verify_server=true，触发既有CA配置拒绝；B87只修CI参数与正式App一致，不改变证书默认/原协议/生产热路径。Cuttlefish host Job在下载APK后旧路径缺少SOURCE失败，修到真实 artifact 的 android-root-app 子目录；仅host准入，不启动guest、不宣称KVM可用。B87用 [android-guest-retry] 只补D2 preauth与原标准Job，不重跑已通过的综合冷套件、API35/36或14个Linux弱网场景。D2即使成功也只到原Go TUN/RAW/SYN阶段，不重开已知SLIRP/TAP握手阻塞。ARM64实体业务/性能仍NOT_RUN，main不动。

## B86｜B85 实测结果与两项 Android guest 定向续测

B85 SOURCE `3cd25ceba4fff1a2f322534c4a828b97f9d1e8d6` [Action 45376451064](https://github.com/lly8666/wbd-next/actions/runs/45376451064)：25 SUCCESS / 3 FAILURE / 3 SKIPPED，全部结束。9个原生/Host/原Linux jobs、API35/36 stock真实正式APK UI+独立普通UID TCP/UDP（不经WBD）、14个双架构七模式原Linux场景 SUCCESS。ARM64正式APK已签名并上传（[artifact 14911876866](https://github.com/lly8666/wbd-next/actions/runs/45376451064/artifacts/14911876866)）；root-arm64-app 在旧UI文案源码断言FAIL。两个KSU job均在CI-only Java Activity调用已移除的 InstalledAppCatalog.launchable 编译FAIL，未启动guest。治理/维护成功；独立旧NativeBridge/Cuttlefish/TAP SKIPPED。

B86仅改CI测试：使用真实生产 discoverable 接口；旧UI文案断言改为实际 ServerAddress.valid 调用；[android-cold-suite] [android-guest-retry] 触发同一新SOURCE标准构建及两项未完成的KSU并行（ART/Root/原x86及ARM64转译MTU/Go c-shared；D2仅真实preauth），不重开已通过的14场景和stock guest，不重跑TAP/SLIRP握手/旧ELF139，不改任何正式产品Java/Go/Rust代码、不增安全门。历史B85通过只属于B85，B86新结果待本SOURCE；ARM64真机完整业务及性能未验。A48历史真机Normal/off原SYN/SYNACK/TLS/认证/租约/M4双向/owned Stop已观察，不回退到早期SYN阻塞。

## B85 并行批量模拟（本轮显式触发）

B84 实际 [Action 45373452414](https://github.com/lly8666/wbd-next/actions/runs/45373452414)：ARM64/x86 native、签名 ARM64 APK（[artifact 14910378010](https://github.com/lly8666/wbd-next/actions/runs/45373452414/artifacts/14910378010)）、APK wiring、官方更新器逐条8472条、Host DNS/Rust、原 Linux oracle、维护/功能目录均实际PASS；root-app 最后历史UI源码字符串断言FAIL；KSU job在下载产物目录校验FAIL（未启动模拟器）。B85修正两处，不把前次失败改成PASS。

同SOURCE 构建产物共享：ARM64正式APK+普通UID fixture（构建一次）；Android x86/ARM64 native assets（构建一次）；原 Linux x86/ARM64 CLI+Rust（各构建一次）。提交标记 [android-parallel-test] 自动开启独立场景，fail-fast false：
- 2个 stock x86 KVM guest Android API35/API36：安装真正签名ARM64 APK（Java UI，不执行ARM64独立Go），真实四页导航和四种接管/分流组合截图；实际独立普通UID TCP/UDP回显夹具，经10.0.2.2仅验证模拟器普通网络/夹具，不冒称WBD。
- 1个 Android16 KSU 冷套件：x86原Go/Rust、普通App Root、ART七类cold helper、NativeBridge ARM64实际Rust MTU与原Go c-shared CLI。UI、ART、转译独立收据。若UI/ART失败继续尝试翻译，不修改正式ELF。
- 1个 Android16 KSU D2-S1：复用已证明原 RootService 到原 Go TUN/AF_PACKET，自动批次仅到真实 preauth 立即停止；不反复试已知SLIRP/TAP握手阻塞，不将成功归为M4或认证Stop通过。
- 14个独立原生 Linux 场景（x86/ARM64 × 7模式）：复用原 W167 LinuxExperiment 真实两端 Go TLS/Rust M4/内核 TUN 和 UDP 业务/owned namespace cleanup。20s、10Mbps每方向、1% IID、75ms 标准轻弱网，最大7并行，不做极端容量测试；保存每场景原始指标/独立结论。它们属于共享Linux协议验证，不是Android E2E或手机性能。
- 原有 Host / 源码门 / M3 / DNS / CN / Linux normal wire / 治理保留；旧NativeBridge ELF139、Cuttlefish、TAP不自动重试。

总计18个增强场景（4 Android guests + 14 Linux模式参考），其中原KSU冷job与D2 job为既有job复用。全部新SOURCE未运行前NOT_RUN；不要跨SOURCE或跨平台迁移PASS。用户明确授权Actions模拟，不部署真实手机或外部服务。

**2026-11-24 B84 用户要求：APK UI 收口重构。** 四个常驻页面：连接（真实M4+UID状态、当前服务器/下次配置、连接/断开/选服务器）、服务器（4个命名槽、独立凭据/CA、备份与冷切换）、应用（默认全局普通App或仅选定App，统一选择全量隧道或CN/自定义分流，未接管App保持系统路由）、设置（原传输/Health/IPv6/热点/恢复/诊断）。全量按钮清除CN/物理DNS/IPv4/IPv6/自动LAN直连例外，CN分流按钮启用已有CN IPv4+域名策略；选定App共享当前FIB策略，不声称每个UID独立不同规则。默认全局普通IPv4（原服务端、Root/系统/WBD/Manager绕过，IPv6与普通系统DNS显式选择）。配置变化只在下一次START生效；命名服务器切换复用原B49/B52完整Stop→新认证。显式手动联网更新官方CN域名库已接候选：下载v2fly最新release、核上游SHA、同四类protobuf提取、原Go/Rust冷规则解析；成功原子替换，不自动更新或改变已运行会话。主体新增功能冻结，转入测试。真实APK先构建，然后本轮一次x86 KSU guest跑新四页UI截图/交互、ART原生冷参数、Root及ARM64 NativeBridge Rust MTU/Go c-shared；不重跑TAP/旧直接ARM64 Go SIGSEGV。B84 CI和真机未验。

**2026-11-24 B83 用户范围冻结（当前最高优先级）**：除手机端显式手动联网更新官方 CN 域名列表（唯一功能待办；已有内置8472、文件导入/恢复）外，所有 Android 主体功能标记为基本完成开发、转入验证；未实现的高级功能冻结不开发，不把它们说成已接线。只修实际测试发现的业务/性能问题，不扩极端工况。高级 CN FakeIP 仍 OUT_OF_SCOPE。优先复用一次 Android16 x86 KVM/KSU guest 跑 ART 冷控制、x86 原生原Go/Rust、ARM64 NativeBridge 真 Rust MTU 和原Go c-shared help；原 ARM64 独立 Go ELF139 与 hosted SLIRP/TAP RAW 路径阻塞保持历史，不为冷测试重开这些诊断；ARM64 真机集中验证真实业务、内核设备差异和性能。

# Android Root 原生产品集中测试矩阵（B82 候选）

目的：一次构建、一套签名 ARM64 APK、一份可重复普通 App 流量夹具，先真实功能后性能；不做海量极端工况/重复x86探针。仅在用户明确授权的 ARM64 手机、受控 Linux 服务端及弱网环境执行。不因构建/Host或历史记录冒称新 SOURCE 真机 PASS。

## 1. 当前范围冻结

七模式（Normal/off、Normal Fixed、Normal Auto、Game2/off、Game2 Fixed、Game4/off、Game4 Fixed）、原Go TLS/认证/租约、原Rust M4、UDP/TCP、普通App单/组/all UID、内核直连、三DNS模式及系统普通53、真实Network、冷恢复/轮换、多配置、IPv4/IPv6软件热点、CLAT、SIT IPv6承载、startup padding、Game4 stagger、ARM64 ISA-L、outer v3、普通CN官方快照/手工导入/恢复、CN IPv4（B82含软件热点）均已源码接线或候选。旧MISSING台账行不再作当前依据。

非本次测试前置：连续热迁移/独立lane热轮换、业务idle-dormant唤醒、Private DNS/DoH主动拦截、硬件热点offload/裸IPv6 M3；高级CN FakeIP明确OUT_OF_SCOPE，不实现。Windows专有驱动/服务端管理工具非Android客户端入口。不得把未实现能力标已接线。

唯一新增功能待办：用户显式手动联网更新官方 CN 域名列表，复用 main 现有手动更新格式/版本与 Go 冷规则导入，正常连接不下载；不阻塞其他已接线功能的验收。

## 2. 构建与环境

- 每个冻结SOURCE仅跑一次现有 Android dual64 CI。原Go/Rust双ABI、ARM64签名APK、两个原Linux Oracle、必要Host。保存同SOURCE/manifest/hash；不同场景复用同一APK和Linux产物，不重编译。
- 新 `traffic-fixture.apk` 为独立普通 UID，无Root、VPN或替代协议。CI Host只验证真实普通socket回显夹具与构建，不代表Android WBD。允许拿同一次产品CI产物在授权真机跑七模式。
- 最优环境：一台真实Root ARM64 Android + 同局域网/受控Linux服务器 + ADB控制电脑（用同一测试网络和服务端）。无需再采购资源或重跑SLIRP/TAP。GitHub hosted CI负责软件层；可用 x86 KVM/KSU + ARM64 NativeBridge 复用一轮真实 Android ART/冷控制与真实 Rust MTU 测试，详见 [复用计划](ANDROID_ROOT_X86_REUSE.md)。不将模拟器结果冒充 ARM64 真机。
- 产品debug签名每SOURCE可能变，先冻结APK再跑所有场景；若以后需连续迭代，由用户授权使用本地持久测试签名密钥对候选APK重签；不把密钥上传仓库、不自动卸载/改签设备。首次签名切换先由用户备份配置、Stop并确认旧规则清除。

## 3. 真实App功能（顺序，单手机不并跑两个owner）

| 场景 | 实际最低证明 |
|---|---|
| Normal/off 基准 | SYN/SYNACK、原TLS/认证、/32、M4+UID Ready、普通App TCP/UDP逐字节双向、Stop |
| 其余六模式 | 同一测试UID与服务端，实际native mode/FEC/lane readback，短TCP/UDP双向，Stop；Auto换档另记观测 |
| DNS/直连/UID | 一个Normal代表场景覆盖单/组/all、绕过、普通CN和非CN两实际upstream、UDP/TCP53和系统resolver；不能以解析成功独立证明物理/隧道分流 |
| IPv6/热点 | 支持SIT的真实双方显式开启，测试IPv6实际地址、IPv4/IPv6下游普通应用；软件热点CN CIDR、普通DNS与Stop独立验证；CLAT视当前真实网络能力 |
| 生命周期 | 一次 Wi-Fi/蜂窝或以太网冷切换、一次配置切换、一次定时轮换，旧owner结束、新代真实Ready及业务恢复；非热迁移 |

所有失败保留实际阶段，不重刷已完成前置。与WBD连接无关的宿主/设备能力不足标 ENV_BLOCKED/NOT_RUN。

### 可直接重复的业务测试命令

在获授权Linux测试机的 **隧道内可达地址**（不是外层WBD peer IP，避免走server例外直连）运行：

```bash
python3 android/root-app/ci/traffic-fixture/server.py --bind <server-tunnel-ip> --port 18080
```

授权手机手工安装一次 `traffic-fixture.apk`。在 WBD Root App 选择 **WBD Traffic Test**（org.wbdnext.testtraffic）的普通UID，选择模式，等真实M4+UID Ready，再在ADB电脑运行：

```bash
python3 android/root-app/ci/traffic-fixture/run.py --host <server-tunnel-ip> --label normal-off --samples 32 --mib 4 --expect-uid <selected-uid> --output results/normal-off.json
```

其余模式仅改变 App 真实连接配置和 `--label/--output`，不用重装。可选 `--dns cn-name,non-cn-name` 测 Android 普通系统resolver；配合真实upstream计数判分流。IPv6可用真实隧道侧IPv6地址。原 `android/root-app/ci/device_first_run.py` 同时负责收集源、业务阶段和Stop路由记录；夹具 label不是原生mode证明，实际走M4需对照选定UID、M4真实增量与server收包。未授予设备/服务端授权时不部署。

## 4. 性能（正常功能之后）

用同一设备、网络、服务端、APK，避免同一手机并行场景争用CPU。先Normal/off代表，再Normal Fixed/Auto、Game2/4代表；对 outer off/on、ISA-L 实际 backend、padding off/flows 只做相关代表性 A/B。同一场景连续3次、顺序 A/B 与 B/A，固定数据量、MTU和背景负载。夹具记录TCP连接及首回包、TCP/UDP p50/p95/p99、成功样本、流式双向echo速率；正常短测4MiB/32样本，性能可增加样本/数据量。echo速率不是最大单向带宽；若要因果CPU或满带宽，另用真实单向stream/iperf3并对齐服务端字节、手机原Go/Rust进程CPU时间、墙钟和温度，记录空闲固定时间唤醒。只选一档代表性受控弱网（如10% loss），不在个人公网服务器随意设置netem。

## 5. 退出与交接

报告 SOURCE/PR/Actions、各真实阶段、场景PASS/FAIL/NOT_RUN/ENV_BLOCKED、延迟/交付/CPU/带宽。不改写历史证据。正常功能问题才修；不新设无业务价值的防御性测试门。不因某场景失败自动扩大功能范围。
