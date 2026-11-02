# PLAN028｜简化认证、单端口多客户端与配置接线

PLANNED。读[总入口](M0-LEGACY-ROLLOUT-20261102.md)及当前M0 cursor，复用PLAN027限定收口及PLAN027A的精确源码资格；旧范围外NOT_RUN不因此重开027。本包补会话/配置接线和网络切换恢复，不优化FEC/重传算法，不更换已验证的TLS建链/AEAD实现。入口提示词：[M0-PLAN028](../prompts/M0-PLAN028.md)。

## 1. 对用户的行为

前置[PLAN027A](M0-PLAN027A-MTU-UNIFICATION-20261102.md)应先完成，配置/每client MTU直接消费[MTU_CONTRACT](../architecture/MTU_CONTRACT.md)的typed预算与readback。028只补会话归属/配置接线，不重新写Go加减公式或重刷单模式字节门。

**配置里的MTU统一指外层完整IP包上限（默认1460，不含L2；可显式配置1500）。**client传每session外层意图；server结合本方向出口/MSS/协商限制收窄。两端内层MTU均由027A自动推导，不新增用户手填内层MTU，不把收到的外层值直接写进TUN。requested外层值与effective内层/OS读回分别存取；多个客户端各有外层意图，不相互覆盖全局TUN。

- 服务端常用配置仅 `listen`、`server-name`、`users`；默认示例 `0.0.0.0:443`、`www.cisco.com`。每client模式/FEC/cipher/MTU等来自认证配置，不是服务端进程级单值。
- 客户端服务器地址可填IPv4或域名，端口单独填写；它与**借站域名/SNI**是不同字段。连接信息由服务端提供/导出，支持手填和导入，用户不手填route-key/tunnel-id/lane ID。解析机制交029，028接口接收已选择的数值endpoint，不在热路径查DNS。
- 用户名密码允许同账号多终端；正常启动自动生成内部安装/会话标识，各设备不互踢。安装标识可沿老版保存在portable目录，IP租约仍不持久化，不能误把“不持久IP”解释成每次换lane换设备身份。

## 2. 最短实现链

1. 配置统一解析/验证 → 真实TLS账号认证 → 服务端SessionRegistry分配/恢复logical session与租约 → 安装双方effective配置 → lane归组 → 当前Rust owner。GUI/CLI不能绕过这条链。
2. 复用 `logicaltunnel/lease_registry.go`、`realityfront/policy_v3.go`、`runtimeentry/automatic_lease_test.go` 的行为；当前入口在 `r0/go_overlay/internal/v4productcli/linux.go`、`realityfront/admission_v4.go`，目前固定tunnel/DesiredLanes检查需改为正确的会话归组，不只是删除检查。
3. 保留真实认证、每lane密钥/PN、generation、session隔离。用户只输账号密码不代表内部不要ID。内部ID自动生成，旧会话退出不能释放新会话/其他设备的地址。
4. **不要假装route-key已自动解决。**先追清它在旧建链前的作用：若需要双方预共享，服务端单独随机生成并不能让手填客户端知道。目标是不增加用户手填秘密；优先复用真实TLS内账号认证及既有协商导出会话材料，确需冷握手改造就在本包双方一起完成并标版本能力。不用公开常量冒充秘密，不强制隐藏密钥导入却声称支持手填账号密码，不影响稳态DATA格式。发现原借站机制确实不支持目标，先留下具体调用链限制和最小解决方案，不能靠关闭认证/借站校验过关。
5. 一个外部端口的accept/association入口按真实连接五元组分流，认证后挂到session+lane+generation；同IP/NAT/用户名都不等于同设备。Game四lane归一个逻辑session，不起四个服务端口/四套地址池。各客户端队列有界，某客户端拥塞不锁住所有其他session。
6. 一处参数schema复用旧PARAMETERS/configfile，给默认/适用模式/作用范围/生效时机/effective读回。双方认证配置携带这些信息并有限填充，不新增长期固定反馈包；不为每个设置增加一次往返。Unknown能力明确拒绝/返回不支持，不静默退到另一模式。

配置只在认证后的既有加密记录中传递，复用控制封装；每条可随机增加0..min(256B、实际记录余量)，单次协商新增总量≤1KiB，不额外发padding-only包、不等待随机时间、不突破MTU。配置多时按已有有界分段路径，不另塞HTTP/VMess等明文标识，不添加稳态逐包字段。100年内部自签材料不能伪充真实借站证书；借站认证/握手仍沿当前合格实现。

## 3. 参数作用域与地址/MTU

| 范围 | 内容 | 生效 |
|---|---|---|
| server | listen、借站域名、账号、出口/地址池等高级项 | 保存后显式重启；不要求第一版热重载 |
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

**不等到Android再设计会话恢复，也不为028提前开发完整Android客户端。**本包实现并验证公共路径变更入口、重新认证/会话接管、Windows/Linux客户端原生通知。Android阶段只接系统网络回调、底层socket绑定和VPN旁路，再做Wi-Fi/蜂窝/后台真机验证；Android未测不阻塞028，也不能把桌面Actions写成移动端PASS。

网络切换与定期轮换共用已有唯一生命周期控制器。Rust保持稳态owner和有界切换状态；原有Go冷控制负责TLS/认证及OS操作。不新增第二个失联判断器、常驻探测包、逐包FFI或高频网络轮询。

1. **通知只表示路径可能变化。**冷入口合并地址/接口/路由通知，重新读取去server的实际物理出口、源地址、数值endpoint及已知MTU，形成进程内`path_epoch`和快照。TUN自身路由/DNS/MTU操作、无关网卡和重复初始通知不应不断触发重连。实际出口不变且lane健康，保留连接；不能仅见到“网络事件”就杀所有lane。
2. **新路径可用且仍需连接，尽快发起一次真实建链。**默认约200ms合并通知，最迟500ms处理一批，避免连续通知永远延后；只在冷路径定时，不延迟业务包。第一次尝试不等90s dead或旧lane释放；同一epoch合并一个重连意图，Game按已有有界冷建链并发补lane，不因每条通知起一组握手。连接失败复用1–30s退避；确认是另一条可用路径时可重置一次退避，重复通知不能反复重置。没有可用出口就等事件/既有退避，不空转。
3. **完整新建链，不搬旧TCP五元组。**沿现有TLS/账号认证，用自动生成的设备/逻辑会话关联材料申请续接；server认证后恢复本设备session和仍有效租约，接受新公网IP/端口，不等旧连接dead。账号、源IP、公开安装ID单独都不能授权夺取会话；同账号其他设备不受影响。不需新用户字段、不增加稳态DATA头，续接信息并入028既有受保护冷协商。
4. **逻辑会话保持，lane身份更新。**保留TUN和内网IP，重协商每client配置，使用新的lane密钥/PN/generation。合法session共享的FEC/去重状态按现有有界策略保留；旧lane密文/重传缓存不移交给新密钥。新epoch到达或用户Stop使旧建链结果过期时，关闭其自有资源，不能再提交READY或覆盖新路由。退休回调按session/lane/generation所有权清理，不能释放新连接的IP或其他设备资源。server重启失去租约等无法续原地址时明确报告重配，不保证旧内层TCP存活。
5. **可重叠就交接，已断就直接恢复。**旧路径可用则A→A+B→B；旧路径已断不强求A继续交付，新lane通过真实认证、配置/MTU安装和实际IO就接管，旧资源有界回收不能阻塞恢复。所有权交接仍只允许一个调度者读写共享TUN，不能为加速启动两个互抢的owner。Game健康lane继续送；全组失效时允许先用可用的已认证lane恢复业务并标记degraded，再补齐目标lane数，不等最慢lane才能交付，不宣称降级期已有完整四副本保护。
6. **休眠和手动断开不自动唤醒。**payload idle休眠时只记最新路径、失效旧endpoint快照；真实新业务合并WakeDemand后才建链。显式Stop后网络通知不能复活连接。已配置保持在线/未休眠的会话即使暂时无业务仍可重连；Health沿既有节奏且不刷新payload idle。

### 4.2 路径绑定、MTU与自动FEC

- Windows复用原生接口/地址/路由变更通知，Linux客户端复用rtnetlink事件；监听挂在冷OS适配层，回调只记录变化并唤醒已有控制器。raw/Npcap绑定也需随真实出口更新：重新选择接口/源地址/下一跳、过滤器和owned旁路route，不能只给TLS换个socket而让Rust继续在旧网卡发送。不改server listener端口，不全局重启其他客户端。
- 域名endpoint按029直出解析接口携带网络epoch：旧缓存仍可用时先尝试，过期/新路径失败时走新出口的解析和有限候选，不经隧道DNS形成建链依赖环。028先实现数值endpoint的完整切换并冻结该接口，029补DNS组合用例；不复制解析器。
- **默认外层MTU1460不变，显式最大1500不变。**每个新lane按027A取新路径已知限制并重算双向预算；用户保存的外层意图不变。有效内层变小须在新路径承载业务前应用/OS读回；旧TCP已协商MSS不能靠新SYN钳制修复，超限包沿027A的DF/ICMP/已支持兼容路径处理。不能以“IP没变”掩盖MTU黑洞。客户端并存lane取实际调度所需的安全预算；server仍按session约束，不改全局TUN或其他client。内层自动计算不等于主动探测公网PMTU。
- fixed/off与Game配置保持；Normal auto旧路径测量作废，恢复用户配置的初始档/已有启动策略后再观察新路径，不将旧低丢包估计、RTT或旧报告直接套用。明确区分路径epoch和安全generation，不额外造每包标识或反馈协议。
- 无系统通知的公网NAT映射变化/单向黑洞仍由既有Health/dead/重连兜底，不能宣称所有移动问题500ms恢复；此500ms只是可用路径通知的处理预算，不是网络建链SLA。

平台依据：[Windows路由通知](https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-notifyroutechange2)、[Linux rtnetlink](https://www.man7.org/linux/man-pages/man7/rtnetlink.7.html)、[Android网络回调/Network绑定](https://developer.android.com/develop/connectivity/network-ops/reading-network-state)。Android后续接真实底层网络选择与VPN socket旁路，不能把VPN自己的默认网络通知当物理切网；不在系统回调线程做TLS握手。

## 5. 测试：少而覆盖关键差异

代码/双方/配置读回写齐后构建一次，功能可顺序合批，性能一Action一场景，各模式Action并行。优先当前真实Windows↔Linux夹具，Linux原生arm64补相关server/session接口；不以纯mock或旧Go PASS代替真实产品。

| 场景 | 最小验收 |
|---|---|
| 同账号两设备 + 另一账号一设备，同端口 | 不同模式/FEC/cipher/MTU/IP能同时传TCP/UDP；改一个不影响另一个，Game四lane仍只算一个设备 |
| 地址 | 自动/手动、冲突一次、重连续租、server重启重配；7天到期用注入时钟测纯租约，不真等7天 |
| 参数 | requested/effective/真实包一致；错误配置清楚失败，不破坏其他会话，不重复全档数学 |
| 各模式换lane | **Normal off/fixed最高/auto、Game2 off/最高、Game4 off/最高，共7模式逐项有真实generation替换证据** |
| 生命周期组合 | idle后唤醒、保活损失不误关、恢复与轮换交叠，复用027通过项，仅补本包会话/配置变化影响 |
| 网络切换 | 复用7模式场景增加一次真实出口/源地址切换；新认证/新generation、原session/IP、真实恢复与旧资源回收有证据。单纯netem恢复或人工发事件不算OS通知接线通过 |

换lane每模式约120–180s、Normal5–10Mbps/方向、Game逻辑3Mbps，允许测试配置20–30s轮换，至少2次**成功的**A→A+B→B，含一段5%随机损伤。保持真实建链/加密/owner，不伪造ready或直接切指针。0%健康片段不应因正常轮换重置内层TCP；first/p99/超时/10ms发送与到达桶分阶段报告。确认新lane真实包已到、旧lane最终回收、IP/配置保持，计时器触发不算完成。

MTU配置组合复用上述多client场景：一方默认外层1460、另一client显式外层1280，server有自己真实出口限制；分别核外层意图、方向effective与自动内层，不手填内层预期到产品里。模式/换lane后用户保存的外层数值不被自动结果覆盖。

30%/250ms只选Normal最高FEC及Game4最高FEC代表，允许失败重试和网络理论残余；验新包不中断、最终成功/明确退避、资源可回收，不要求一次成功或零损。正常低损容量内出现新增连续秒级全流停顿、异常TCP重置、跨client污染应定位；细小丢失/p99波动先比较同源无轮换基线，不硬压零。若需要真实5–10min轮换区间，仅一个代表长测约11min，已有等价027证据可替代，不让七模式都跑长测。

网络切换增量按以下有界方式验，不叠加一整张新弱网矩阵：

- 单元/集成覆盖重复通知、程序自改路由、快切A→B→A、建链中Stop、过期READY/回收、休眠切网后首次业务；用现有可注入时钟，不等真实dead90或7天租约。只为必要竞态和状态转换写测试。
- 7模式真实场景每项加入一次切网，以现有Windows客户端→Linux服务端为主；Linux客户端原生通知仅补Normal和Game4最高FEC代表，不再复制七模式全表。Normal auto与Game4最高FEC两个代表分别覆盖可重叠交接和旧路先断后连、1460路径→1280→恢复；可并入该场景既有分阶段损伤，不做模式×损伤×切网类型全排列。同账号多客户端场景只切其中一台，另一台持续业务，验证不会互踢。
- Actions只变更自建测试接口/地址/到server的专用路由，不断开runner管理网络。Linux用隔离netns/veth，Windows用owned测试地址/路由/虚拟链路，让真正系统通知和真实驱动生效；驱动换接口需有对应证据，软件事件注入不能冒充。ARM64 server复用必要会话接管用例；Android、物理Wi-Fi/蜂窝保持NOT_RUN，留到安卓阶段。
- 分开记录`t_path_available / t_reconnect_requested / t_authenticated / t_first_business`、最大交付空洞、p99、真实TCP是否持续、重连次数、旧资源数以及CPU/RSS。恢复预算按同源同路径冷建链耗时+通知合并+当次实际退避解释：250ms单向仅一次往返已约500ms，不能要求全恢复<500ms；低损容量内不应无故等dead90，30%允许多次认证尝试，不能拿握手失败算业务HOL。线路全断期间不要求交付，但恢复后不能等永久旧锁/旧owner或排无界旧队列。
- 无切网对照复用同SOURCE合格阶段，确认没有新增周期包、忙轮询和稳态CPU/p99回退；只在确有差异时做一次同VM顺序A/B。捕获计数/时序/有限包头摘要即可，不存大pcap；一Action一场景，构建产物按SOURCE/hash复用。

退出：目标账号密码操作、单端口/多客户端/独立配置/IP全部真实有效，7模式换lane和Windows/Linux网络切换资格齐或复用有效证据，相关配置/UI/endpoint事件接口提供029/030及未来Android；未解阻断不藏，容量/物理/Android NOT_RUN准确。更新原tls-auth-multiclient/idle-rotation-keepalive等功能卡，不另立重复生命周期产品。
