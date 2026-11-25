## B112｜FEC真实读回及原生先感知物理丢失恢复（当前）

B111 `3c97a97597beff6f54ffe8a0a40293cc8bfeaec6` [Action 45562169772](https://github.com/lly8666/wbd-next/actions/runs/45562169772) 14/3/9；默认/显式隧道DNS UDP/TCP PASS，Fixed/Auto/Game4 Fixed真实1%下行丢包业务PASS，Game4恢复候选PASS；Fixed/Auto通用诊断未启用，恢复交付未证；WiFi后原生先joined Stop但exit1，自动恢复未触发。B112三guest：Android原9计数真实读回、五次普通业务burst、原生明确物理丢失且完整清理后交给现有Java自动恢复，保留实际原Network验证与真实二次业务。详见 [B112 devlog](../devlog/android-root-probe/20261125-b112-fec-recovery-handoff.md)。不改变数据面/协议/MTU，不重跑DNS/基础七模式，实体ARM64待验。

## B111｜七模式远端业务收口，轻损恢复及DNS/自动重连（当前）

B110 `9e3c2e95b56e51b976bb0af75d4532c890746e25` [Action 45560632409](https://github.com/lly8666/wbd-next/actions/runs/45560632409) 15/2/9；四Game真实双向业务及Stop PASS，累计7/7。真实隧道UDP53 PASS，默认TCP透传请求未绑定上游而超时；重连guest缺phone服务未执行。B111六guest：默认TCP透传、显式App TCP DNS relay、原Service自动重连、Fixed/Auto/Game4 Fixed真实1%下行丢包与原恢复计数。详见 [B111 devlog](../devlog/android-root-probe/20261125-b111-loss-dns.md)。不修改协议或数据热路径、不宣称Game候选等于恢复交付、实体ARM64仍待验。

## B110｜Game真实远端、隧道DNS及生产自动重连（当前）

B109 `18a687c75a038856c86232d6992bd9dd4ce0bbe3` [Action 45557921405](https://github.com/lly8666/wbd-next/actions/runs/45557921405) 14/5/8；Normal/Fixed/Auto真实独立远端普通App双向TCP/UDP+1MiB/方向及Stop PASS；四Game实际lease/M4+UID和server 12/12 lane commit，但误要求Normal SYNACK枚举，业务NOT_RUN。B110 6guest并行：四Game原wire各lane双向计数/真实业务/Stop、Normal真实隧道DNS UDP+TCP、Normal正式Service Wi-Fi自动恢复（无手动START）。不重跑已通过3模式基本矩阵及失败的非产品普通kernel TCP carrier额外试验。详见 [B110 devlog](../devlog/android-root-probe/20261125-b110-game-dns-reconnect.md)。物理ARM64、真实FEC恢复及热点未证。

## B109｜真实独立远端七模式（当前）

B108 `6f63538348aabfeff6eaca39fac63cf53050b6be` [Action 45553595090](https://github.com/lly8666/wbd-next/actions/runs/45553595090) 11/2/8；Android独立原peer实际SYNACK/lease/M4 READY，33双向原包；server gate要求互斥singleton marker故App业务NOT_RUN，独立Linux普通TCP carrier connect FAIL。B109修正原Normal auto-lease multi-session和Game group验收分支，七独立Android实际peer业务、独立Linux carrier诊断。详见 [B109 devlog](../devlog/android-root-probe/20261125-b109-real-peer-seven-modes.md)。无生产改动、未证明远端E2E或性能。

## B108｜CI-only 原报文转接，真实独立远端业务（当前）

B107 `da7eb919c7762afa33c763aee713fffb51a67c22` [Action 45550257467](https://github.com/lly8666/wbd-next/actions/runs/45550257467) 14/0/8；16/16多/全App probe、hostname/default DNS、实际onLost/Stop/显式新handle重连、3/3 cleanup PASS；native scope flag及生产自动重连未证。ARM64 host无KVM。B108只试一条Normal/off真独立peer路径：临时veth/tc+ADB reverse传递原IPv4/TCP字节，独立Linux内核carrier 1MiB及真实Android正式RootService→原Linux server→普通App TCP/UDP/Stop。非物理网络资格，未证阶段不得冒称PASS。详见 [B108 devlog](../devlog/android-root-probe/20261125-b108-original-remote-carrier.md)。

## B107｜普通域名启动与默认 Resolver（当前）

B106 `a0d72bc6ffc5b74dbec7c4653580a9d97a1e26a2` [Action 45549418682](https://github.com/lly8666/wbd-next/actions/runs/45549418682) 7/1/12；真实Linux IPv6 SIT/普通UID/下游TCP+UDP/DNS/Stop全部PASS；CI-only b91 strings导入缺失导致3 guest NOT_RUN。B107修编译、两guest加真实hostname bootstrap及默认Resolver；原network guest继续验证同handle onLost/Stop/显式重连，独立收据。不重跑green IPv6。详见 [B107 devlog](../devlog/android-root-probe/20261125-b107-default-dns-and-active-scope.md)。真实Android远端RX/生产READY自动恢复仍未证。

## B106｜活跃 M4 多/全 App 组合及 Network callback（当前）

B105 `4957c16ec9cc03ac1a2ace274a447907fac713b0` [Action 45545657277](https://github.com/lly8666/wbd-next/actions/runs/45545657277) 18/2/7；七模式普通选项/Resolver/业务TX PASS，8/8 cleanup；SIT双端安装/ICMP6 PASS但普通UID读checkout拒绝，Wi-Fi新handle重连PASS但native scope flag未观察。B106 3 guest+1 host：真实多/全App CN/Resolver/TCP SYN/UDP TX与物理直连，真实Network onLost后原Stop及显式重连，IPv6普通UID业务恢复测试。详见 [B106 devlog](../devlog/android-root-probe/20261125-b106-active-scope.md)。非远端E2E/生产READY自动恢复。

## B105｜普通选项与实际 Wi-Fi 恢复（当前）

B104 `968bd6509ca60d42bee21590180232e8bdc764d1` [Action 45543122668](https://github.com/lly8666/wbd-next/actions/runs/45543122668) 14/1/7；IPv4真实下游转发/DNS/Stop与API35/36 UI配置持久化PASS；IPv6 SIT identity失败。B105冷态独立设置alias，真实IPv6重验；7 Android模式常用AES/flows/outer/Health30及系统Resolver+活跃M4；另1 guest真实Wi-Fi关闭、native scope invalid及新handle显式重连。详见 [B105 devlog](../devlog/android-root-probe/20261125-b105-options-sit-network.md)。无远端M4 RX或生产READY自动恢复结论。

## B104｜正常工况：热点转发、IPv6承载、UI配置保存（当前）

B103 `30a78c44a1998b76f1a9c6623596d376966dc8f7` [Action 45538321422](https://github.com/lly8666/wbd-next/actions/runs/45538321422) 21/0/6；9/9同进程连接Stop/物理恢复，15/15同socket持续DNS/Activity切换，7/7 Linux原协议混合TCP/UDP scoped PASS。B104 2个真实Linux内核netns组件任务（IPv4下游SNAT/CIDR直连/DNS/Stop，IPv6双SIT owner及普通UID/下游业务/DNS/Stop），2个stock Android API35/36正式APK UI两配置保存、重开载入。详见 [B104 devlog](../devlog/android-root-probe/20261125-b104-forwarding-ui.md)。不冒称实体热点、Android远端RX、生产READY自动重连或手机性能。

## B103｜正常连接周期及混合业务（当前）

B102 `559dcdb22782c64af33d65d68547e522e36d45bd` [Action 45535658071](https://github.com/lly8666/wbd-next/actions/runs/45535658071) 19/0/7；14/14场景、8/8 cleanup、七模式原M4物理UDP DNS与TCP53、11/11 DNS后普通业务、12次真实直连TCP/UDP含1MiB/方向逐字节PASS。B103 3 Android guest×3同进程原native Connect/Stop/配置切换，首连接同socket持续DNS和实际Activity后台；7个独立x86原Linux双端混合TCP/UDP参考（20s、20ms、1% IID）。详见 [B103 devlog](../devlog/android-root-probe/20261125-b103-normal-connection-cycles.md)。非Android远端RX或生产READY自动重连；不再扩展特殊边界。

## B102｜正常工况优先（当前）

B101 `0ff84b89e71ae023d048c17d4990a6182fd1badd` [Action 45532853139](https://github.com/lly8666/wbd-next/actions/runs/45532853139) 20/0/6；12/12 Game共同MTU、579线上包0超限、4/4实际crash Restore、8/8 cleanup，Linux DNS6 NAT PASS（非Android NAT）。用户明确停止罕见工况防御性扩测。B102 8guest：11场真实TLS后原M4物理UDP DNS/原App TCP DNS、CN/隧道DNS发送及普通业务；3真实UID场各4次普通TCP/UDP直接业务及Stop恢复。详见 [B102 devlog](../devlog/android-root-probe/20261125-b102-ordinary-usage.md)。远端双向、READY切网/后台、热点、实体ARM64仍待验。

## B101｜异构Game共同预算 / crash recovery / DNS6（当前）

B100 `471f9406b09d581e61ddc0c7e6f88cfc58b6e124` [Action 45530309154](https://github.com/lly8666/wbd-next/actions/runs/45530309154) 11/9/6；mixed 4/8（末lane小MSS PASS，首lane小MSS失败）；crash真实exit86、原Restore因CI su引号未执行；Bionic IPv6 relay UDP/TCP PASS，Host DNS6 attr29失败。B101同原Rust oracle在TLS前汇总最小lane MSS到共同offer，认证后仅一次TUN MTU，12 mixed含中间/双低MSS；四crash修读回，DNS6 exact dport mask兼容，8guest+1host并行。详见 [B101 devlog](../devlog/android-root-probe/20261125-b101-group-cold-budget-recovery.md)。无remote E2E/READY自动恢复新证据。

## B100｜真实 crash journal 恢复、异构lane MSS、DNS6分层（当前）

B99 `9d40a9b2a2b90744af9a706062153af1f5e95530` [Action 45527391628](https://github.com/lly8666/wbd-next/actions/runs/45527391628) 21/1/6，7/7独立线上长度239包0超限、3/3真实双UID/CN；DNS6 guest kernel无nat表NOT_RUN。B100 9 guest+1 host：4场实际退出/原journal恢复，8场Game异构MSS（最小lane先/后），原Bionic IPv6 loopback relay+Linux netns实际DNS6 RPDB/NAT独立验收。详见 [B100 devlog](../devlog/android-root-probe/20261125-b100-recovery-mixed-mss-dns6.md)。新SOURCE待验，不称远端M4/READY恢复。

## B99｜实际 RAW wire、双 UID 及 DNS6（当前）

B98a `9f3d93a86d99a013de349bd485655d8ecf4d7f2e` [Action 45521294719](https://github.com/lly8666/wbd-next/actions/runs/45521294719) 18/0/6；28/28 OS MTU+DF超限+Stop、56/56临界TX检查，7/7 guest cleanup；4原MTU ABI tests PASS。B99新增11 guest（最多9并行）：7模式独立AF_PACKET wire长度，single/group/all两个普通UID实际业务/真实CN快照路径（隔离host本地别名），IPv6 DNS原owner显式UDP/TCP和恢复。详见 [B99 devlog](../devlog/android-root-probe/20261125-b99-wire-multiuid-dns6.md)。未证明真正远端RX/READY恢复。

## B98｜原 MTU 审计与7模式边界矩阵（当前）

B97 `94cb981fa71affb20c462f7a105310b0be3dd98d` [Action 45506419874](https://github.com/lly8666/wbd-next/actions/runs/45506419874) 14/0/6；Fixed/Auto实际 source+parity PASS，累计7/7 App TX；DNS TC PASS。main 共享 path_budget.rs/测试及 M3 FEC seal 实现完全相同，Android接线错误而非自动MTU公式。B98 7 guest × 4场景（1280/1460/1500/1500+server record1200），真实TLS+OS TUN、MTU-1/MTU UDP DF、MTU+1 EMSGSIZE、真实RAW计数/Stop。详见 [B98 devlog](../devlog/android-root-probe/20261125-b98-mtu-boundary-matrix.md)。未证明远端双向或实体ARM64。

## B97｜Fixed/Auto record budget 与 FEC source/parity（当前）

B96 `bae7a69c2d47a91ea0fd3813474e8985b38a4677` [Action 45503675129](https://github.com/lly8666/wbd-next/actions/runs/45503675129) 19/1/6，8/9 guest完整PASS，9/9 cleanup；24/24 UID回显、3/3 Resolver DNS/Stop、7/7原TLS/M4/Stop、5/7实际 App TX。Fixed/Auto App socket成功而 RAW copy不增，源码发现14B reserved inner budget被共享M3已编码record入口拒绝。B97仅同owner冷态分离两视图、保持原MTU/PN/AEAD/Stop；两FEC独立guest及32包真实source/parity，另DNS TC→TCP新guest。详见 [B97 devlog](../devlog/android-root-probe/20261125-b97-fixed-record-budget.md)。remote M4/repair/M2 APPLIED及READY自动恢复未证。

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

**2026-11-24 B84 用户要求：APK UI 收口重构。** 四个常驻页面：连接（真实M4+UID状态、当前服务器/下次配置、连接/断开/选服务器）、服务器（4个命名槽、独立凭据/CA、备份与冷切换）、应用（默认全局普通App或仅选定App，统一选择全量隧道或CN/自定义分流，未接管App保持系统路由）、设置（原传输/Health/IPv6/热点/恢复/诊断）。全量按钮清除CN/物理DNS/IPv4/IPv6/自动LAN直连例外，CN分流按钮启用已有CN IPv4+域名策略；选定App共享当前FIB策略，不声称每个UID独立不同规则。默认全局普通IPv4（原服务端、Root/系统/WBD/Manager绕过，IPv6与普通系统DNS显式选择）。配置变化只在下一次START生效；命名服务器切换复用原B49/B52完整Stop→新认证。显式手动联网更新官方CN域名库已接候选：下载v2fly最新release、核上游SHA、同四类protobuf提取、原Go/Rust冷规则解析；成功原子替换，不自动更新或改变已运行会话。主体新增功能冻结，转入测试。真实APK先构建，然后本轮一次x86 KSU guest跑新四页UI截图/交互、ART原生冷参数、Root及ARM64 NativeBridge Rust MTU/Go c-shared；不重跑TAP/旧直接ARM64 Go SIGSEGV。B84 CI和真机未验。

**2026-11-24 B83 用户范围冻结（当前最高优先级）**：除手机端显式手动联网更新官方 CN 域名列表（唯一功能待办；已有内置8472、文件导入/恢复）外，所有 Android 主体功能标记为基本完成开发、转入验证；未实现的高级功能冻结不开发，不把它们说成已接线。只修实际测试发现的业务/性能问题，不扩极端工况。高级 CN FakeIP 仍 OUT_OF_SCOPE。优先复用一次 Android16 x86 KVM/KSU guest 跑 ART 冷控制、x86 原生原Go/Rust、ARM64 NativeBridge 真 Rust MTU 和原Go c-shared help；原 ARM64 独立 Go ELF139 与 hosted SLIRP/TAP RAW 路径阻塞保持历史，不为冷测试重开这些诊断；ARM64 真机集中验证真实业务、内核设备差异和性能。

**2026-11-24 B82**：B82 WIRED_CANDIDATE / feature-freeze candidate：CN IPv4 直连同一已合并 CIDR 表覆盖普通 App 与显式软件热点（真实内核 throw，冷批量路由和索引读回，Stop/Restore）；独立普通 UID TCP/UDP 字节回显测试 APK、双向流式 echo/RTT、可选 Android 系统 DNS、同 SOURCE fixture Host loopback，现有 CI 先产 APK 再执行历史源码门。无新 WBD 协议/数据线程/防御框架。B81 官方 8472 条 Go/Rust Host、双 ABI、两个 Linux Oracle PASS；APK 旧 send_staged 断言、维护旧 regex-lite graph FAIL，已按实际源修候选。B82 CI/设备/性能尚未验。主线先测七模式、UID/直连/DNS、IPv6/热点、冷切网/轮换，再短性能 A/B；不扩大热迁移/idle dormant/在线规则下载等非当前主体测试前提。

[集中测试方案](ANDROID_ROOT_TEST_MATRIX.md)

**2026-11-24 B81**：B81 WIRED_CANDIDATE: Android uses main's official flattened CN domain snapshot via shared build-time importer, typed Go cold normalization and existing Rust M4 matcher (all four types); App local import/reset applies on next START, no runtime fetch or FakeIP, disabled CN split skips Go rule parsing. Legacy 8503 host evidence stays historical. B80 exact ACK/SACK test crate and obsolete source assertion repaired; assembler pin matches actual merged main blob. CI/device/performance not yet verified.

**2026-11-24 最新用户决定（B80）**：每次从 main 同步已正式合入的全部源码、功能/优化与历史（真实双亲 merge，保留 Android 专有代码），平台差异只在 Android Bionic RAW/TUN、Root/Network、App 冷设置等适配层处理。优先复用 main 共享核心，不复制一套协议/算法；main 的 Windows/服务端专有逻辑保留源码而不误启用在 Android。Android 必须适配原表演式/机会式外层重传，旧逐 record M2 Receipt 已废弃，禁止复活。高级 CN FakeIP 仍明确 OUT_OF_SCOPE；普通 CN DNS 与真实 IPv4 内核直连保留。

**2026-11-24 最新用户决定：Android 高级 CN FakeIP = OUT_OF_SCOPE（明确不实现，不是待办）。** 保留普通 CN8503 域名 DNS 分流、真实 IPv4 CN 内核 FIB 直连、手工 CIDR；不引入合成 IP、FakeIP 映射、对应路由、UI/CLI 开关、代理数据路径或验收任务。按大类功能并行研读/合批接线，复用原 Go 冷控制及原 Rust 数据面；不展开极端工况、额外防御性安全开发或重复历史 SYN/TAP 探针。

**B80 WIRED_CANDIDATE**：冻结 main `5b1311c0748452c1c8dac66fc2a6e517777529fa`，双亲 merge `a0d31730e772dea9d1884076c945c7c810b879c9`（Android 原父 `1997efa2d89b52e11f21037c7972deee9139a0c0`）；206 个 main 变化文件完整同步，两个 Rust 重叠文件三方无损重放、Cargo 双依赖合成、Go manifest 按实际合成 blob 更新。Android Normal/Fixed/Auto 单 lane 与 Game2/4 off/fixed 复用 main `CosmeticOuter` 的 Normal-v3 `OuterAckIndex`/`ReceiptState`/9% pacing/10% quota，按真实 kernel copy 保留原密文一次，RAW ACK/SACK 元数据、Go 已协商 SACK、Game 物理 AEAD 后 ACK、现有 TX owner due/readback 和 Stop。Android 单 lane 使用同一个 main Game v3 控制器，不冒称已移植 Linux Normal process-global allocator。App/Go 显式 ON/OFF，旧 Android 预设默认 OFF 至实体资格，七模式开关可用性仍须同源构建和实体验证。main 8472 官方 CN 域名快照/手动更新源码已同步，Android 现役仍是经验证的 8503 typed snapshot，普通 CN 数据资产与冷导入适配另续；Linux H2376 满队列公平算法同步，Android 直接 TUN 不凭空加 Linux SharedTun 队列。旧 B79a 9 SUCCESS/1 FAIL/5 SKIPPED，APK 旧七模式 padding 拒绝断言已全部改正并补 App 开关往返正向用例。当前 SOURCE CI/实体/性能 NOT_RUN，不把接线当 PASS。

> **B75/B76 2026-11-24 批量接线**：B73/B74 [产品 #45334679723](https://github.com/lly8666/wbd-next/actions/runs/45334679723) 9 SUCCESS/1 FAIL/5 SKIPPED，旧B29源码断言固定4处cold DNS检查，B73新增第5处；Feature catalog SUCCESS。B75普通App IPv6 DNS走原系统IPv6 DNS relay（UDP，TCP随原开关），B76热点IPv4直连CIDR与IPv6一致、保留实际下游路由；CI同源待验，真机后续统一。

> **B73/B74 2026-11-24 用户要求一次性大类功能合批接线**：B72 [#45328655906](https://github.com/lly8666/wbd-next/actions/runs/45328655906) 11 SUCCESS/4 SKIPPED。B73完成可配置隧道DNS在原Normal/Fixed/Auto/Game和App/系统/热点DNS的共同入口；B74补IPv6热点普通UDP/TCP DNS共用原三DNS模式。源码、设置及Stop同批；新CI待验，真实设备以后集中验收。不扩极端工况/防御开发。

> **2026-11-24 B72（用户指令：继续大类功能接线、并行批量开发，不展开极端工况或额外安全加固）**：B71 `992f77f4e81b` [Dual64 #45324658533](https://github.com/lly8666/wbd-next/actions/runs/45324658533) 11 SUCCESS/4 SKIPPED，签名ARM64 APK及原Linux Oracle通过。B72在原SIT/6rd IPv6 UID FIB中接手工直连CIDR与选定Network自动LAN IPv6直连，复用批量内核路由和原冷启动/配置/Stop；本SOURCE待CI，Android真机未验。旧D2/SYN探针不是现行阻塞。

> **B59 原物理UDP DNS大EDNS应答回App（B59a软件PASS，实体NOT_RUN）**：B58a产品 [Dual64 #45209186326](https://github.com/lly8666/wbd-next/actions/runs/45209186326) 11 SUCCESS/4 SKIPPED、B58b [治理 #45210124110](https://github.com/lly8666/wbd-next/actions/runs/45210124110) SUCCESS。原Rust接受最多4096B EDNS UDP53物理DNS应答并做ID/QNAME/租约逆映射，但此前把超过隧道MTU的合成IPv4单包直接写TUN。B59使Normal/Fixed/Auto和Game2/4在回复超过原会话inner MTU时，复用B16 RFC791 `fragment`、同一TUN FD/BorrowFence分片写入；小回复保持原一次写、只完整写完才计一次成功。没有新TCP代理、M3、线程、系统Resolver修改；Host测试涵盖大EDNS真DNS回答及576/1260/1460 MTU重组与写失败。B59a产品SOURCE `ccc5d47868c3` [Dual64 #45220240360](https://github.com/lly8666/wbd-next/actions/runs/45220240360) **11 SUCCESS/4 SKIPPED**，真机依然NOT_RUN。[B59记录](../devlog/android-root-probe/20261124-b59-physical-edns-original-tun-fragments.md)。

> **B58 批量原生普通App IPv4功能（新SOURCE待CI）**：上次B57 [#45202808785](https://github.com/lly8666/wbd-next/actions/runs/45202808785) 11 SUCCESS / 4 SKIPPED。正式Root App可选从8个原UID/16包扩为**16 UID／32真实安装包**；现有用户IPv4直连FIB `throw CIDR` 从4扩为**16条**，四配置槽/SAF保存不变。原Go `--android-route-uids`、rootjournal单/组/20用户全App三个owner同步，路径只在TLS/租约/Rust M4完成后安装；把每条UID/直连前缀都全表查询的启动O(N²)改为“先完整直连读回 → 装所有UID → 一次完整精确读回”，保留原持久化journal、同代Stop及命令失败回滚，没有新增逐包组件。新增Java/Go Host测试，不新开工作流；实体Android路由效果/性能仍NOT_RUN。[B58](../devlog/android-root-probe/20261123-b58-bulk-app-cidr-root-route.md)。

> **B57 Game2/4原IPv4大包/PMTU业务接线（本SOURCE待CI）**：B56 [Dual64 #45196398008](https://github.com/lly8666/wbd-next/actions/runs/45196398008) 11 SUCCESS/4 SKIPPED之后，Game唯一TUN读取完整IPv4不再因超预算直接丢：DF0复用B16 RFC791分片并经原GameAdapter/M3/RAW；DF1生成现有TUN本地ICMP3/4通知App；较大物理UDP53仍走原绑定Network Socket。普通App TCP53仍M3透传、物理TCP53/系统DNS/IPv6未接。3项Rust Host、原双ABI/签名APK/Linux Oracle同源待新CI，真机/性能NOT_RUN。[B57日志](../devlog/android-root-probe/20261123-b57-game-original-ipv4-fragments-pmtu.md)。

> **B56 Android 原Game2/4 RAW RX 低唤醒/业务吞吐（本SOURCE待CI）**：基于B55b [#45189246018](https://github.com/lly8666/wbd-next/actions/runs/45189246018) 11 SUCCESS / 4 SKIPPED，原2/4路Game M3 RAW RX继TX后加入最多8包的原位连续处理，避免每条record都走poll；无定时逻辑的RX idle改为30s同一RAW+Stop eventfd即时唤醒，原PN/AEAD/FEC/TUN/ACK/owned Stop不变；Game Rust文件增原Dual64工作流触发，不加Job。[B56记录](../devlog/android-root-probe/20261123-b56-game-raw-rx-event-driven-burst.md)，同源签名APK/Host/Oracle待本SOURCE CI、真机性能NOT_RUN。

> **B55 原Game2/4 M4首送/低CPU热路径（本SOURCE待CI）**：前SOURCE `c3f4b828` [#45185545494](https://github.com/lly8666/wbd-next/actions/runs/45185545494) 11 SUCCESS/4 SKIPPED，本批原Rust单TUN读取同一GameAdapter/2/4RAW最多8包无逐包poll，原Health/Game4/FEC到期优先的1s eventfd TX idle、2/4路RX idle 250ms→1s。无新线程/用户态额外分组控制/协议；3条Rust Host +签名APK按新SOURCE验，真机业务与CPU NOT_RUN。[B55](../devlog/android-root-probe/20261123-b55-original-game-event-driven-burst.md)。

> **B54 四套配置的可选原Go TLS CA跟随（本SOURCE待CI）**：为B52多服务器切换补已有B23可选私有CA的各槽保存/载入/删除与重开App正确回填，继续原Go标准TLS及默认验证开关，不新建证书机制、不影响 Rust M4/UID/Stop或按普通App路由。B53批量SAF迁移依旧不导出CA，重装仍要手动重导；新SOURCE正式签名APK/双ABI/Oracle依据Actions、真机NOT_RUN。详见[B54](../devlog/android-root-probe/20261123-b54-profile-scoped-original-ca.md)。

> **B53 四套Root连接一文件SAF迁移（本SOURCE待CI）**：继B52一键跨原生Stop/START接线，本批以原四槽命名Profile/RootConnectionSettings同一Codec导出/恢复普通服务器、Normal/Fixed/Auto/Game/FEC、UID/三DNS/MTU/Health/CIDR设置；选中/空槽原样保留，不包含密码/Key/CA或旧Network。导入只修改四个本地Profile并清对应旧Keystore槽，绝不动当前Go/Rust或UID规则，无后台新控制器。正式签名APK及Host同源结果看Actions，实机NOT_RUN。详见[B53记录](../devlog/android-root-probe/20261123-b53-four-profile-saf-backup-restore.md)。

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
