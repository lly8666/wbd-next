# PLAN028｜简化认证、单端口多客户端与配置接线

IN_PROGRESS（2026-11-11：SOURCE8c0421 Windows自动AES256与四Linux三套cipher真实150s和六owner Stop PASS_SCOPED；用户明确不需运行同Windows宿主多Wintun，H1587原始route/WAL FAIL保留为该组合未支持限制；同账号跨OS独立安装已在SOURCE8a313真实150s PASS_SCOPED、最终综合质检与近MTU仍未齐，不得标COMPLETE）。主要实现已进入集成收尾，不将功能接通当全包完成；精确进度/SOURCE只读M0 cursor和evidence。功能范围留在本页，方法、压力、验收及退出统一见[专项验收](../testing/PLAN028_INTEGRATION_ACCEPTANCE.md)，入口为[M0-PLAN028](../prompts/M0-PLAN028.md)。既有实现按证据复用，不重做旧包；真实缺陷与必要接线继续修，暂停无关新功能/协议重构。

## 0. 施工边界：补接入与交接，不重做架构协议

**持续硬门：建链不能引入私有前导。**沿[TLS建链唯一契约](../architecture/TLS_HANDSHAKE_CONTRACT.md)使用显式/导入预共享route-key并保持服务器身份验证。H1048前置交换已废止；核当前实现与证据，不把历史整改指令重复当新任务。旧功能PASS不代表握手外观合格。

以下为原施工范围/先后关系，已完成项只索引复用；当前未完成任务由cursor及专项验收选择。2026-11-03用户明确要求收紧范围。已核实[H1000入口依赖](../devlog/M0/20261103-PLAN028-H1000-ENTRY-DEPENDENCIES.md)：当前Linux产品单会话、Game按lane递增服务端口、同lane活跃位拒绝重叠；这三点是需要补齐的真实接入限制，**不是推翻成熟数据面的理由，也不要求先完成所有多客户端产品功能才能验证一次轮换**。无新代码/证据变化，不重复写同一轮依赖审计；按下述工作包进入施工。

### 0.1 允许改什么，保留什么

- 本包只改必要的accept/association接入、会话与租约归属、Rust共享IO分发、lane代际交接和冷配置/OS适配。复用现有FEC/Auto、Game共享编码/复制/去重、机会式重传、record/AEAD/PN、Rust缓冲及驱动算法；不趁机换算法、扩大常规缓冲、增加每包头/反馈包，或重新造传输协议、通用多租户框架。
- 单外部服务端口按现有TCP连接五元组识别lane，客户端各lane可使用不同本地端口；不能要求四条连接连本地端口也完全相同。认证后的session/lane关联复用冷协商，**不为单端口分发新增稳态DATA路由头**。现有全局`handoffCommitted`/首会话完成后忽略新SYN的行为应改为按连接实例移交，后来的冷建链仍可接入，已接管业务仍由Rust处理。
- “唯一owner”是明确的资源所有权，**不是全服务器只能有一个客户端**。共享接收入口用连接索引定位目标会话/lane，共享TUN按已分配隧道IP定位出站session，复用现有队列/缓冲句柄；不逐包遍历所有会话，不为每个client复制全量原始收包，不让多个owner争读同一TUN，不恢复Go逐包搬运。冷注册表锁不得跨TLS握手、驱动IO或等待Stop持有；普通分发不引入全局每包大锁。线程/批处理沿已有模型，不强制为了本包造新执行器。
- 同一logical session可有旧active与新candidate/retiring lane实例；用现有generation/实例handle精确区分。prepare/commit/retire必须匹配自己的实例，旧回调不能清掉新lane位或释放新租约；失败只回滚候选。保留会话级FEC/去重归属和原密文语义，不因换一条lane清空整个会话。用最少的现有对象/引用实现，不为了这些状态做持久事务系统。
- 冷配置扩展仅限真实TLS保护下的Admission参数/续接材料，双方同批明确版本；不得把“冷接口适配”解释成允许TLS前私有交换。route-key在连接前通过本地预配置取得，复用原标准SessionID识别，不增加TLS字段/握手往返；其余TLS/稳态wire沿既有实现。详见唯一建链契约。

### 0.2 顺序与交付粒度

1. **共享接入/会话包**：冻结最小session/租约/lane实例/IO归属接口；接单端口分发、同账号多设备、每client配置和Rust共享TUN，双方及装配清单同批写齐。复用老租约逻辑和现有数据面，不先做新平台。
2. **交接/切网包**：在同一接口上接旧新lane重叠、精确退休、原生网卡/IP通知200/500ms合并、出口重绑定和MTU安装；复用原生命周期、Health/idle/退避，不增第二控制器。顺序是**读取新路径限制→真实建链认证并确定最终预算→安装配置/应用MTU并读回→新lane放行业务→有界退休旧lane**。允许认证后预分配未放流的owner；禁止先开始真实业务再补MTU/路由。server只更新该session预算/必要路由，共用TUN不随最后一个client修改。
3. **认证冷路径修复包（历史范围）**：撤掉TLS前X25519前导，显式/导入预共享route-key，解除证书验证耦合并补真实握手审计，见§2第4项和唯一契约。已验实现直接复用；“只填账号密码”旧限制已撤销，不重复开发前导或key线上协商。

“代码写齐再测试”以**上述完整工作包的双方实现、实际调用/装配、配置读回与夹具齐备**为单位；不每helper跑一次Action，也不要求三包所有功能写完后才首次验证真实IO。公共接口先定，产品功能可分批递进；最终仍要完成本计划全部目标。每包一次SOURCE构建并复用产物，随后沿§5的有限场景验证，已有资格只补受影响部分。

## 1. 对用户的行为

前置[PLAN027A](M0-PLAN027A-MTU-UNIFICATION-20261102.md)已按用户指示限定范围收口；配置/每client MTU直接消费[MTU_CONTRACT](../architecture/MTU_CONTRACT.md)的typed预算与readback，未解决项保留H998原结论。028只补会话归属/配置/新路径衔接，不重新写Go加减公式或重刷单模式字节门。

**配置里的MTU统一指外层完整IP包上限（默认1460，不含L2；可显式配置1500）。**client传每session外层意图；server结合本方向出口/MSS/协商限制收窄。两端内层MTU均由027A自动推导，不新增用户手填内层MTU，不把收到的外层值直接写进TUN。requested外层值与effective内层/OS读回分别存取；多个客户端各有外层意图，不相互覆盖全局TUN。

- 服务端常用配置为 `listen`、`server-name`、`users`及持久route-key引用；route-key首次可由本地初始化生成并随连接配置导出，不要求手工造随机数。默认监听 `0.0.0.0:443`；SNI/证书身份按建链契约配置，不把示例域名当已取得真实站点私钥。每client模式/FEC/cipher/MTU等来自认证配置，不是服务端进程级单值。
- 客户端服务器地址可填IPv4或域名，端口单独填写；它与**借站域名/SNI**是不同字段。连接信息由服务端提供/导出，支持手填和导入；route-key允许显式填写或导入，tunnel-id/lane ID仍自动管理。解析机制交029，028接口接收已选择的数值endpoint，不在热路径查DNS。
- 用户名密码允许同账号多终端；正常启动自动生成内部安装/会话标识，各设备不互踢。安装标识可沿老版保存在portable目录，IP租约仍不持久化，不能误把“不持久IP”解释成每次换lane换设备身份。

## 2. 最短实现链

1. 配置统一解析/验证 → 真实TLS账号认证 → 服务端SessionRegistry分配/恢复logical session与租约 → 安装双方effective配置 → lane归组 → 当前Rust owner。GUI/CLI不能绕过这条链。
2. 复用 `logicaltunnel/lease_registry.go`、`realityfront/policy_v3.go`、`runtimeentry/automatic_lease_test.go` 的行为；当前入口在 `r0/go_overlay/internal/v4productcli/linux.go`、`realityfront/admission_v4.go`，目前固定tunnel/DesiredLanes检查需改为正确的会话归组，不只是删除检查。
3. 保留真实认证、每lane密钥/PN、generation、session隔离。用户填写账号密码及导入/预置route-key，不代表内部不要ID。内部ID自动生成，旧会话退出不能释放新会话/其他设备的地址。
4. **route-key首包前已预配置。**采用服务端32B随机持久key，客户端显式填写或导入；缺失在本地失败，不做线上获取。复用原HMAC占用既有32B兼容SessionID，ClientHello长度/字段/标准TLS流程不变。真实TLS完成后才发送用户名密码及配置；证书验证与key来源解耦。用户明确接受该配置成本；禁止再用X25519前导、公开常量、TLS后exporter或关闭识别来“解决”首次材料。具体调用/装配/测试按唯一建链契约。
5. 一个外部端口的accept/association入口按真实连接五元组分流，认证后挂到session+lane+generation；同IP/NAT/用户名都不等于同设备。Game四lane归一个逻辑session，不起四个服务端口/四套地址池。各客户端队列有界，某客户端拥塞不锁住所有其他session。
6. 一处参数schema复用旧PARAMETERS/configfile，给默认/适用模式/作用范围/生效时机/effective读回。双方认证配置携带这些信息并有限填充，不新增长期固定反馈包；不为每个设置增加一次往返。Unknown能力明确拒绝/返回不支持，不静默退到另一模式。

配置只在认证后的既有加密记录中传递，复用控制封装；每条可随机增加0..min(256B、实际记录余量)，单次协商新增总量≤1KiB，不额外发padding-only包、不等待随机时间、不突破MTU。配置多时按已有有界分段路径，不另塞HTTP/VMess等明文标识，不添加稳态逐包字段。100年内部自签材料不能伪充真实借站证书；借站认证/握手仍沿当前合格实现。

## 3. 参数作用域与地址/MTU

| 范围 | 内容 | 生效 |
|---|---|---|
| server | listen、server-name、账号、预共享route-key引用及信任材料、出口/地址池等高级项 | 保存后显式重启；不要求第一版热重载 |
| session | 账号身份、隧道IP、Normal/Game、lane数、加密、期望outer MTU、启动填充/idle/rotation策略 | 同路径换lane继承配置；换网络保留用户意图，按新路径重算effective MTU/质量状态 |
| direction/block | fixed/off/auto策略、Auto有效档位 | Normal上下行独立；沿现有块边界切档/旧块有界退役，Game无Auto |
| local | GUI、DNS/分流、设备路径、日志 | 按已有本地配置，不盲传给server照单执行 |

- 自动地址7天租约、活动续租；不能第7天杀活跃连接。server重启可丢内存租约，客户端重新认证获取effective地址；同一轮换/休眠唤醒优先续原地址。手动IP占用或越界明确拒绝，不悄悄换IP；有效账号不能靠手动IP抢别人的会话。
- 共用server TUN保持稳定设备MTU；**不要每个客户端连接时改全局TUN MTU，也不要取最小客户端MTU拖低所有人**。复用现有path_budget/路由或分片接口，在出站session边界应用各自上限；如果内核路由MTU需要按租约设置，则是有限每client路由，不是下发整份中国IP表。TCP MSS/PMTU及超限UDP行为沿成熟逻辑，不吞包无说明。
- 原加密suite/record/link/FEC头开销由现有预算推导，不恢复旧固定扣减。端到端配置、owner、实际包三者读回一致；UI区分已保存/下次连接/当前生效，不新增复杂证明框架。

## 4. 复用生命周期，重点验换lane

策略/参数见总入口；027若已接通不得重新搬一次。冷TLS建链沿Go，稳态切换/状态沿现有Rust唯一owner；不得Go与Rust同时判断失联或轮换。

- 所有模式都是 A→A+B→B。B完成真实认证、session配置/MTU安装和可用性检查前，正常可用A继续送业务；失败留A并按既有1–30s退避重试。高损不保证第一次B成功。
- Normal的逻辑会话/IP/内层TCP连接不因正常换lane重建；Game优先一次替换一个lane，健康兄弟继续发，不等全组最慢lane。旧lane只承接有界尾包/已有工作，保留旧3s replacement grace为参考，当前已验证期限优先。
- FEC/去重归属及generation切换沿当前设计：合法跨lane首到不重复交付、旧generation不污染新身份；不要“清空所有FEC状态再换代”，也不无限保留旧状态。
- 保活不刷新payload idle，丢保活不是闲置；真正失联走dead/reconnect，只有双边成熟闲置才休眠。新数据遇到休眠发一次合并WakeDemand，失败退避后能重试，不“重建失败一次后永远卡住”。
- 027当前单向黑洞修复只有对应SOURCE真实通过后才能复用；不把双向恢复通过推广成单向。

### 4.1 网络切换：本包做公共逻辑与Windows/Linux接线，Android后接系统入口

**不等到Android再设计会话恢复，也不为028提前开发完整Android客户端。**本包实现并验证公共路径变更入口、重新认证/会话接管、Windows/Linux客户端原生IPv4路由/地址通知与物理网卡/IP读回。Android阶段只接系统网络回调、底层socket绑定和VPN旁路，再做Wi-Fi/蜂窝/后台真机验证；Android未测不阻塞028，也不能把桌面Actions写成移动端PASS。

网络切换与定期轮换共用已有唯一生命周期控制器。Rust保持稳态owner和有界切换状态；原有Go冷控制负责TLS/认证及OS操作。不新增第二个失联判断器、常驻探测包或逐包FFI；原生通知和合并后的冷路径物理出口检查不属于稳态包处理。

1. **比较真实物理出口、源IPv4及已知effective MTU。**客户端冷路径在原生OS通知合并后读回这三项；任一实际变化交现有控制器重新认证并应用新预算。同NIC/IP的MTU收窄也必须处理，不能留下永久黑洞。TUN自身、重复通知和未改变上述结果的网关/路由噪声不触发重连；不增加主动公网PMTU探针。
2. **网卡、IP或有效MTU真正变化后才开始新建链。**事件按200ms静默合并、首个通知后最长500ms；检测到有效新物理出口即按现有TLS认证路径尝试，不等90s dead。Game仍按现有有界冷建链补lane，不重复派发。失败仍按既有1–30s退避；没有可用物理出口时等下一次原生网络通知/既有退避，不空转。
3. **完整新建链，不搬旧TCP五元组。**沿现有TLS/账号认证，用自动生成的设备/逻辑会话关联材料申请续接；server认证后恢复本设备session和仍有效租约，接受新公网IP/端口，不等旧连接dead。账号、源IP、公开安装ID单独都不能授权夺取会话；同账号其他设备不受影响。不需新用户字段、不增加稳态DATA头，续接信息并入028既有受保护冷协商。
4. **逻辑会话保持，lane身份更新。**保留TUN和内网IP，重协商每client配置，使用新的lane密钥/PN/generation。合法session共享的FEC/去重状态按现有有界策略保留；旧lane密文/重传缓存不移交给新密钥。新epoch到达或用户Stop使旧建链结果过期时，关闭其自有资源，不能再提交READY或覆盖新路由。退休回调按session/lane/generation所有权清理，不能释放新连接的IP或其他设备资源。server重启失去租约等无法续原地址时明确报告重配，不保证旧内层TCP存活。
5. **可重叠就交接，已断就直接恢复。**旧路径可用则A→A+B→B；旧路径已断不强求A继续交付，新lane通过真实认证、配置/MTU安装和实际IO就接管，旧资源有界回收不能阻塞恢复。所有权交接仍只允许一个调度者读写共享TUN，不能为加速启动两个互抢的owner。Game健康lane继续送；全组失效时允许先用可用的已认证lane恢复业务并标记degraded，再补齐目标lane数，不等最慢lane才能交付，不宣称降级期已有完整四副本保护。
6. **休眠和手动断开不自动唤醒。**payload idle休眠时只记最新路径、失效旧endpoint快照；真实新业务合并WakeDemand后才建链。显式Stop后网络通知不能复活连接。已配置保持在线/未休眠的会话即使暂时无业务仍可重连；Health沿既有节奏且不刷新payload idle。

### 4.2 路径绑定、MTU与自动FEC

- Windows和Linux均在冷OS适配层订阅原生IPv4路由/地址/链路变化，200ms静默、最长500ms后读回物理出口网卡、源IPv4及已知有效MTU；实际变化才唤醒已有控制器。raw/Npcap绑定也需随真实出口更新：重新选择接口/源地址/下一跳、过滤器和owned旁路route，不能只给TLS换个socket而让Rust继续在旧网卡发送。不改server listener端口，不全局重启其他客户端。
- 域名endpoint按029直出解析接口携带网络epoch：旧缓存仍可用时先尝试，过期/新路径失败时走新出口的解析和有限候选，不经隧道DNS形成建链依赖环。028先实现数值endpoint的完整切换并冻结该接口，029补DNS组合用例；不复制解析器。
- **默认外层MTU1460不变，显式最大1500不变。**每个新lane按027A取新路径已知限制并重算双向预算；用户保存的外层意图不变。有效内层变小须在新路径承载业务前应用/OS读回；旧TCP已协商MSS不能靠新SYN钳制修复，超限包沿027A的DF/ICMP/已支持兼容路径处理。不能以“IP没变”掩盖MTU黑洞。客户端并存lane取实际调度所需的安全预算；server仍按session约束，不改全局TUN或其他client。内层自动计算不等于主动探测公网PMTU。
- fixed/off与Game配置保持；Normal auto旧路径测量作废，恢复用户配置的初始档/已有启动策略后再观察新路径，不将旧低丢包估计、RTT或旧报告直接套用。明确区分路径epoch和安全generation，不额外造每包标识或反馈协议。
- 公网NAT映射变化、无有效路径变化的网关事件、未被OS通知识别的路径故障及单向黑洞仍由既有Health/dead/重连兜底，不因500ms通知处理预算宣称500ms内完成TLS建链；它不是握手SLA。

Android阶段仍参考[Android网络回调/Network绑定](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)。当前桌面版作原生通知后真实物理出口网卡/IP/有效MTU读回；Android后续接网络选择与VPN socket旁路，不把VPN自己的默认网络当物理切网。

## 5. 验收：唯一专项计划与完整退出条件

执行[PLAN028集成可靠性专项验收](../testing/PLAN028_INTEGRATION_ACCEPTANCE.md)：L0确定性边界→L1七模式/多客户端/平台与生命周期短测→L2计算容量、渐进压力和弱网恢复→L3冻结SOURCE后有限综合长测。这里不再复制一张易过时矩阵。既有合格证据按SOURCE和未变依赖复用；已知严重失败定向修复，未触发候选不得宣布因果成立。

M0有现场决策权：依据实际PPS/BDP、FEC恢复模型、相关丢包和宿主/产品容量，调整场景、压力、顺序、样本长度和合理性能容差；事先说明依据，保留旧结果，不降低认证/隔离/完整性/建链外观/MTU/generation/Stop硬门。不要求坏网络一次换代成功、超恢复能力零损或耗尽VM仍达标；也不允许用容量借口掩盖产品单线程/锁问题。

范围至少包括标准真实TLS、同账号多设备单端口/独立配置/IP、七模式实际A→A+B→B、Windows/Linux真实驱动与网络切换（含同NIC/IP有效MTU变化）、idle/Health/黑洞/Stop、UDP/TCP大小包混合及共享TUN隔离。低损健康阶段不能因轮换无故重置内层TCP；切网/失联恢复预算按实际建链、退避和dead策略解释，不使用一刀切握手SLA。

最终按专项覆盖表逐项交付：必要功能真实有效、已知阻断关闭且回归、稳定容量/退化边界清楚、有限长测通过，才关闭028。原FAIL和范围外NOT_RUN保留；Android/物理未测明确，H998同socket收窄不能借新代重认证PASS改写。同步已有功能卡/配置/帮助/接口；不另建治理或第二生命周期控制器，不因本包验收自动启动029/030。

## 2026-11-04修订：H1048前置交换方案废止

H1048曾引入server先发`WB-R1`及每向37B X25519数据，再进入ClientHello。该实现虽有功能/认证测试PASS，但违反用户标准建链外观红线，**不再是有效设计**。历史devlog/evidence原样保留，仅限其SOURCE功能事实；不标外观PASS。现在以[TLS建链唯一契约](../architecture/TLS_HANDSHAKE_CONTRACT.md)的预共享方案及有限验收为准，代码修复状态以最新cursor/evidence为准；本次文档更正不等于产品已修好。

## 2026-11-11 H1580 接线与SOURCE证明导航

已追补旧Windows native CLI `--native-v4-product` 默认false的歧义（默认true，GUI仍显式加），原TLS请求不再硬编码 `AutoLease:false`/ChaCha。Normal Off/Fixed/Auto 与 Game2/4分别经原Go受保护TLS绑定每client cipher/自动或手动 /32，Rust ColdSnapshot/Game组核有效值，Wintun OS事务只接已认证的租约；校验错误失败而非静默降级。GUI 只对已有选择更正 V3 AES 与 V4 待验区分，不做029/030。

本次源码、Linux x86_64/ARM64原生手动两账号真实业务/Stop、Windows源码装配/Go Rust编译、Game4 overlap、Windows Npcap/Wintun 旧SOURCE150s局部资格、原历史失败及新源码 NOT_RUN，一律以 [028覆盖表与默认配置](../testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md) 和 [H1580 devlog](../devlog/M0/20261111-PLAN028-H1580-WINDOWS-AUTO-CIPHER-RECOVERY.md) 的**精确 SOURCE、平台和入口**为准。特别保留 H1577 Action42983815178 overall FAIL与原native `PASS_SCOPED`；修复兼容报表不等于同场重跑。外层MTU1460、FEC默认Off、Windows15s/90s/idle0、Linux默认不轮换均保持。
