# PLAN029｜客户端中国 IP＋域名分流与单 DNS 契约

2026-11-12 用户授权的设计修订，**DESIGN_APPROVED / IMPLEMENTATION_NOT_QUALIFIED**。本页替代029旧“中国IP单独分流、DNS主备、按DNS目标IP决定查询出口”条款；不是产品已实现声明。主入口：[PLAN029](../decisions/M0-PLAN029-CLIENT-DNS-PADDING-20261102.md)，接续：[M0提示词](../prompts/M0-PLAN029.md)。

## 1. 产品语义，先定清楚再实现

“中国”指内置/用户更新的规则集合，不是在线判断地理位置；不是只匹配 `.cn`。中国域名与中国IPv4是**并集直连**：中国域名解析到海外地址仍直连；非中国域名解析到中国IP，DNS查询走隧道，实际连接仍按中国IP直连。不要把用户的“其他地址走隧道”误写成与“中国IP全部直连”相冲突的规则。

| 路由模式 | 普通DNS选择 | 业务出口 |
|---|---|---|
| `bypass-lan-cn`（界面改名“绕过局域网和中国IP/域名”） | 中国域名→直连DNS；其他→隧道DNS | LAN/已有自定义direct4、中国IP、中国域名直连；其余隧道 |
| `bypass-lan` | 普通域名全部隧道DNS | LAN/已有显式direct4直连；其余隧道 |
| `all` | 普通域名全部隧道DNS | 原有本机/控制必要例外外全部隧道；不顺带打开中国规则 |

- 保留三种route-mode值与既有自定义规则语义，避免改所有配置/协议。CN模式升级为IP＋域名，新配置CN域名匹配默认开启；如保留显式域名开关，关闭仅回到IP规则，UI必须标清，不维护另一套DNS架构。
- `dns.direct` 单一IPv4地址（可选端口，默认53），默认 `223.5.5.5`；`dns.tunnel` 同格式，默认 `1.1.1.1`。每方向只有一个输入框、一个实际upstream。此处方向指**直连/隧道**，不是业务上/下行。
- **所有模式取消DNS主备、竞速与跨方向回退**。8.8.8.8不再隐含启用。UDP截断后对**同一个endpoint**做DNS-over-TCP、同endpoint有界重试不是备用DNS。超时/SERVFAIL/NXDOMAIN不能改走另一方向、系统DNS或另一地址。
- 服务器地址为域名时，bootstrap复用唯一 `dns.direct`，始终通过物理出口，包括all模式；这是建立隧道的控制例外，不给其他域名直连权限。不新增第三个bootstrap备用列表，不依次尝试NIC多个DNS；原物理DNS只作恢复WAL数据。服务器地址为IP不查DNS。
- 允许两个字段填同一个endpoint，但必须按内部用途标记强制各自出口，不能只按目的IP分类。普通业务访问1.1.1.1也不能因它是resolver而获得物理逃逸；直连DNS的自有查询始终物理，隧道DNS的自有查询始终隧道，即使resolver落在中国/LAN网段。
- IPv6仍沿已有阻断政策；不在本包实现IPv6外层。DoH/DoT/DoQ内的域名不可见，不解密、不全网封禁：这些流量按可见目标IP规则，不能声称已做域名识别。界面说明启用应用“安全DNS”会绕过本地域名规则；可选让用户关闭，不静默修改浏览器。

## 2. 一条快路径，不给所有业务套代理栈

```text
少量OS捕获路由 → 原Rust Wintun ingress（仍只有一个reader）
  ├─ 自有回注/现存flow → 已固定路径
  ├─ 普通UDP/TCP 53 → Rust DNS dispatcher（查询级分类）
  ├─ 中国域名本地映射地址 → mapping → Direct
  ├─ LAN / direct4 / 中国IP → Direct
  └─ 其他 → 原Rust隧道/FEC/Game（保持原始IP包传输）
Direct UDP → 绑定物理接口/源IP的Windows UDP socket → 原flow回包
Direct TCP → 本地内核TCP接入 → 绑定物理接口的TCP socket → 原flow回包
```

先辨认owner内部的DNS/回注/控制用途，再处理业务规则；DNS53不能先被中国IP/LAN捕获。已存在的应用TCP/UDP流固定决策和目的地址，更新规则只影响新流；DNS缓存刷新、换lane不会把同一TCP中途切到另一出口。

OS仅保留现有两条 `/1`、必要服务器endpoint和极少数内部端点的owned规则。原OS已有更具体LAN路由保留，不能声称所有本机/LAN包必经Wintun；接管到的包必须在Rust正确分类。**IP/域名条目增加不增加系统路由或WFP规则数**，也不建立逐域名NRPT。直连socket用物理源地址＋`IP_UNICAST_IF`，验证真实出口与不自环；不能靠绑定一个选项就假定已绕过捕获。

既有快路只增加一次统一分发与缓存命中；域名匹配不在普通DATA逐包进行。Normal/FEC/Game共享这一个分流层，不各做一套；Direct不经过外层AEAD/FEC/lane复制/startup-padding，隧道路径不多经过TCP用户态栈。

`all`或关闭CN域名功能时，不为停用功能建立DNS映射/trie或新跟踪线程。纯Tunnel包沿既有buffer ownership移交，不为分类clone整包；普通Tunnel短UDP可用有界决策cache或直接区间查询，不强迫每个一次性5tuple都分配socket/持久flow。内部自有DNS用途标记只存在本地元数据，不增加隧道线上字段。

### 2.1 中国IP与域名表

- 复用旧内置中国IPv4、更新器和自定义CIDR。冷层编译为合并排序的只读 `u32` 闭区间，二分最坏约13次比较（约6209条时）；首次流查一次，后续缓存。无需构建65536×多版本巨表。
- 新内置中国域名集合采用 `v2fly/domain-list-community` 的 `geolocation-cn` 固定commit构建快照，记录源SHA、日期、许可、归一化后条数与hash。不是复制整个代理软件。构建器展开include/attribute；保留exact/suffix/keyword/regex实际语义，禁止把regex静默当suffix或无声丢规则。常用exact/suffix编译反向标签trie；少数其他规则冷构建线性时间匹配器、仅DNS查询调用，不用回溯正则。
- 域名统一ASCII大小写、去终止点、规范IDNA；suffix按标签边界匹配，`evil-example.cn`不能命中`example.cn`。问答和压缩指针用成熟解析库，不能逐包扫描字符串猜域名。
- 两类数据默认内置、离线可用；手动导入/更新验证后原子替换，失败保留旧快照，不后台自动更新。规则快照只读共享，flow保存版本和最终决策，不长持全局锁。活动flow不随名单变化迁移。

### 2.2 为什么只给命中的中国域名使用本地映射地址

只做“DNS答复IP→中国域名”的全局缓存会串CDN：一个中国域名和一个非中国域名可以共用海外IP。把该IP全部直连会误放后者；每包解析TLS/SNI也解决不了UDP、ECH与已有连接。

采用**选择性FakeIP**：只对命中中国域名规则、已从直连DNS成功获得真实A记录的答复提供本地映射地址。非中国域名的普通A答复保留真实IP。因此国外隧道大流量无需额外地址翻译，更无需终止内层TCP。

具体契约：
1. 按原始QNAME决定resolver/方向，查询只发给选中的一个upstream；CNAME目标不重新选择另一resolver。只接受与查询匹配、CNAME链可达的A记录，不学习无关additional。上游无有效A、NXDOMAIN或超时，不制造可用FakeIP。
2. CN域名的可达A记录分配映射：`fake_v4 → {qname/alias chain, real_v4, resolver/policy generation, expiry, refs}`。多A逐条保留可用候选，不把每个lane分配到不同服务器。必要CNAME链一致改写，不能漏出附加真实地址让应用绕开决策。
3. 该流连接fake地址时一次查表，固定真实地址和Direct决策；TCP内核接入/UDP直连回复复原应用原看到的fake源IP。FakeIP绝不能进入隧道、物理链路或服务端租约表。互联网服务器不需要支持新协议。
4. 默认选择 `198.18.0.0/16` 为本机映射候选，启用前检测物理路由、内网、隧道租约与自定义规则冲突；一个高级pool字段可改，冲突明确报错，不覆盖已有网络。仅为本机用途保留，不更改服务端地址分配。
5. 合成答复TTL不大于真实有效链最短TTL，默认再上限60s；TTL0不入普通DNS缓存，但仍短期保留已发映射供连接使用。映射独立于DNS缓存、lane和FEC生命周期；已连接引用存活时绝不重绑定。映射达到容量不能退成“把共享真实IP一律直连”。
6. 程序目录可持久一份小型映射快照，以原子合并/批量写入保存分配和隔离期；仅DNS分配/退休时更新，不在DATA逐包落盘。重启恢复OS/应用缓存仍可能引用的地址；新答复不能在必要映射记录持久前发出。新增映射用单writer批量追加/原子小批事务，命中已有映射不重写整个快照；不按每个查询fsync、不引入数据库服务，报告冷DNS开销。活跃流、已公告TTL、随后10分钟隔离期均满足后才可回收复用；异常旧地址没有映射时明确失败，不转隧道或随便解释成真实IP。应用违反TTL长期缓存无法无限担保，需说明重解析。正常Stop不清空仍有TTL的映射；lane轮换不清表。
7. IPv6阻断时AAAA答复为明确NODATA；选择性合成的CN域名HTTPS/SVCB暂返回NODATA，避免ipv4hint/ipv6hint/别名绕开本地映射。不删其他域名HTTPS功能；非CN真实hint按IP政策，CN域名经应用自身加密DNS返回的hint不在可观察保证内。合成应答清AD，不伪造DNSSEC有效签名；需端到端DNSSEC/IP字面校验的应用可显式关闭域名分流回到IP模式，不能静默降级。

## 3. Direct TCP 是真工程，不能只写一个分类函数

旧 `userspace_tcp_direct_windows.go` 使用Go gVisor/tun2socks终止直连TCP，UDP用物理绑定socket。复用其接口绑定、错误、回包、资源归属语义，**不把旧Go逐包路径接回新Rust**。旧项目已放弃的“原始TCP包直接塞普通Winsock/raw NAT就能通”也不要复活。

本包首选 **Rust改写到本机Windows内核TCP listener，再异步中继到物理绑定TCP socket**，借鉴sing-tun system stack的接入方法，不直接导入它的Go运行时。这样不实现第二套拥塞控制/重传栈，也不让隧道TCP进入代理层；不能承诺比所有其他方案CPU更低，必须实测。

1. owner启动时建立仅owned本地TUN地址的listener和一个虚拟对端地址；使用现有捕获范围或最多一条精确内部route保证回包进同一Wintun，不借外网/他人地址。生成有界NAT端口映射，保存原应用5tuple、fake/real目标、generation；内部TCP回注先于业务分类识别。
2. 对已判Direct的SYN/后续段，只改本地接入所需地址/端口与校验和，写回Wintun交Windows TCP；由其处理ACK/窗口/SACK/重传。listener accept从映射查原目标，创建物理绑定非阻塞连接；双向byte relay用Rust现有IOCP/事件运行时，支持半关闭、RST、连接失败反馈。返回本地TCP段逆变换成应用期待的原目标。不能立即ACK却丢掉尚未可靠接纳的数据。
3. 每flow异步状态可以有，每flow OS线程、全局互斥串行等待、定时轮询不可以有。背压只暂停该flow的读取，其他flow继续；无用户态额外重传缓存。复制缓冲按需池化，优先复用现有库，不为splice/零拷贝神话造驱动。
4. **先做一个真实签名Windows最小能力门**：Wintun→本地内核listener→物理socket→逆变换，验证SYN/FIN/RST、窗口、源绑定、回注不自环和Stop，再写其余完整集成。不能用Linux或内存mock判Windows此方法可用。读sing-tun Windows相关限制/issue，方法有借鉴价值不等于移植自动成功。
5. 若确证当前Windows网络事务不允许这条内核接入且最小修复需要换驱动/重构网络控制层，则记录首个因果证据，改用**仅Direct TCP的成熟Rust smoltcp适配器**，本地短RTT接入＋物理Winsock腿，不自行实现TCP栈。先查窗口缩放/SACK/分片支持，补有界接入，不把UDP和隧道分支一起塞入栈。二选一交付，不长期维护两条默认后端；不得因未知担忧同时开发二者。

Direct UDP复用旧语义移入Rust：每活跃5tuple一个物理绑定socket，IOCP事件收发，socket池/flow表有界，回复重新组IP/UDP并复原fake/原目标；保留datagram边界。不同QUIC/游戏flow不因端口相同串接。仅需要直连/DNS终止的IP分片做有界重组，其他隧道片保持原路径；后续片不能猜端口、随机改路。超MTU按现行契约返回错误/ICMP或分片，不静默截断。常用Direct ICMP echo可借原生异步ICMP接口重建对应ID/seq；其他未支持协议明确报告，不偷偷走隧道冒充直连。

## 3A. 不接入老WFP；把Wintun驱动约束与产品自设限制分开

**2026-11-12最新用户决定：029不接入老项目WFP guard/防泄漏保护体系。** 本节替代上一修订“修改旧Block并加例外”的施工方法；不再为迁就老WFP继续扩规则/权限框架。不修改系统或第三方防火墙，不用一个假guard/no-op成功回执骗过现有检查。

源码审阅依据：原Go `native_wfp_guard_plan_windows.go` 的非Wintun port53 Block；overlay `native_wfp_exact_arm_windows.go` 的纯Block验证；`native_unified_network_transaction.go` 的 `Stages [5]`、`guard/lease/mtu/dns/routes` 固定顺序及Recover完整guard前置；Windows真实入口 `PrepareOriginalTLSNativeProduct`。**这些是项目自己的设计，不是Wintun API要求**。接手时追最终装配链，不能只看到历史INACTIVE注释或ErrN4NativeGuard名称就判断是否在当前产品执行。

### 删除依赖的完整工作包

1. 新029正式入口不创建/恢复/等待旧WFP guard，网络事务只保留实际需要的租约、MTU、DNS、少量路由与owner资源管理。按现有代码最小调整固定stage顺序、收据、校验和调用方，不另造通用事务框架。Ready/AllNativeOSApplied检查真实需要的项目；用明确schema/字段标记WFP不参与，不能伪报WFP已Applied。
2. Stop先停止接纳、取消并回收IO，再恢复本程序拥有的DNS/路由/接口。旧guard是否存在不再是清理其他明确owned资源的前提；已不存在为幂等成功，未知归属/外部资源不碰，其余确定资源继续清理并汇总残留。现有owner/generation/原值记录是为了不误删系统状态，保留，不做多代理攻防。
3. 兼容历史安装：只保留一次性旧journal读取与**精确删除本程序owned旧WFP对象**的迁移入口，不重新Arm；原记录/对象不能证明归属则报告具体残留，不全局清空WFP、不禁用系统防火墙。迁移不是新正式runtime的WFP依赖，也不能把原旧schema忽略后假装清理完成。
4. 同批改入口、Windows owner adapter、装配manifest、事务/receipt、GUI Ready和Stop判断及对应测试。新产品常规运行不应调用旧WFP arm；旧负测和历史证据保留但标为历史，不再用“没有guard必须拒绝启动”约束新029路径。

### 无WFP后的DNS/IPv6边界必须诚实

- 主路径采用owned系统DNS配置指向本地单DNS入口，应用普通系统解析进入Rust dispatcher；进入Wintun的UDP/TCP53按QNAME策略处理。物理Direct socket按接口/源地址绑定即可，不另找WFP许可。自有bootstrap仍使用唯一direct DNS。
- **不再承诺拦截所有任意应用的DNS绕行。** 硬编码LAN DNS可能沿更具体on-link路由绕开Wintun，绑定物理接口的程序及加密DNS也不能单靠两条 `/1` 全面捕获。不为补这一点重新接入WFP或开发另一个拦截驱动。可对已配置的有限DNS地址用精确owned捕获规则实现正常场景，不能扩为扫描所有地址/海量route。UI/help与D1验收据实际出口明确边界；普通系统DNS和已接管业务必须按设置正确工作。
- 原IPv6阻断意图仍需用实际已有可恢复的原生设置/捕获后丢弃路径落实，不得因删WFP悄悄放行，也不能仅有IPv6默认route就宣称所有本地/绑定物理IPv6均被禁止。范围不够如实记录具体缺口，优先普通路由/接口层最小实现，不恢复旧综合guard。既有非本程序配置保持原样。
- 单DNS不跨方向回退、中国IP/域名分类与FakeIP不出本机仍是产品功能要求。缺少某条WFP状态不再算网络功能失败；某功能真实出口不符才是失败。

### Wintun真正需要保留的约束

| 类别 | 应怎样处理 |
|---|---|
| 第三层IP接口 | Wintun只收发IP包；直连TCP仍需内核接入/完整转发，不能把IP包当socket字节，不能注入以太网帧 |
| RX借用buffer生命周期 | 数据不能在Release后被异步引用；需要排队才复制进有界池，不能持有ring借用等DNS/connect/另一个flow，分类快路不多clone |
| TX分配顺序 | 官方发送顺序受AllocateSendPacket顺序影响；**先完成DNS/组包/目标决策，再分配发送buffer并立即填充提交**。不能先占slot再await，造成跨流阻塞 |
| ring容量/背压 | 使用当前已验容量与合法2次幂范围，无包用事件等待；ring满仅相关流背压/有界丢弃，不无限重试、忙等或动辄重启owner |
| MTU/包长 | 原1460外层、Rust推导内层与IP实际长度校验继续；不是Wintun只支持1460，也不为直连错误套外层record预算 |
| 本地接口地址 | server认证租约 `/32` 保持；若Direct内核TCP需要辅助本机地址/route，作为独立owned本地资源，不假冒新server租约、突破账户隔离或增开第二Wintun |
| 单reader和generation | 一个会话的一个Wintun入口后分发多flow，多异步socket可以并发；单reader不等于全连接串行。lane轮换不重建分流器/直连flow；真实Stop后的旧回调不能写入新session |

旧测试硬编码adapter名/测试用户/IP、固定stage数或“只能送隧道”的绑定假设，若进入普通产品路径就改成实际owner配置；不能直接删除真正的租约/generation/长度一致性检查。一个本地socket失败只影响其flow。规则、身份、配置hash在冷路径验证，不逐包查系统/WAL。

### 最小验收增量

D1/D4/D5使用**无本程序WFP guard**的新入口跑普通系统DNS＋Direct TCP/UDP＋Tunnel收发＋Stop；检查新建WFP对象为0。加一例精确owned旧journal/WFP迁移清理且不碰其他对象；一例DNS/Direct连接等待时其他flow继续收发；一例旧generation晚回调不能写已关闭ring。DNS旁路与IPv6覆盖未达范围如实记录，不做攻击矩阵、不重新全跑028。

参考：[Wintun官方使用与API](https://git.zx2c4.com/wintun/about/)。移除WFP冷控制依赖主要减少装配/Apply/Stop复杂度，不能无测量宣称会大幅降低稳态CPU。

## 4. DNS 数据通路，避免自环和隐藏回退

- Windows系统DNS指向本机owned虚拟DNS入口（一个值），原设置只保存在WAL用于Stop恢复。拦截到的普通UDP/TCP53统一进dispatcher，按QNAME而不是应用指定的DNS IP选upstream。现有on-link路由若绕过TUN，须按§3A覆盖系统DNS和实际被捕获的53；不能单凭两条 `/1` 宣称全机DNS已接管。
- Direct DNS由Rust共享绑定物理接口的UDP socket发起；Tunnel DNS作为owner内部用途明确的UDP流进入现有Rust隧道，回复在写Wintun前按自有tuple/transaction分离。内部端口要保留并避免与应用碰撞，不能抢普通DNS回包。TCP53按同方向接入/有界连接复用；Tunnel TCP fallback可复用Windows内核接入，必须标记强制Tunnel，不能被CN IP规则或本地53再次捕获。
- DNS可以复用一个小事件任务/分片，但不得阻塞Wintun reader等查询结果。合并同`qname/qtype/upstream/policy`并发请求，保持各客户端ID/源地址；校验回复来源、ID、question，缓存键带resolver与policy版本。UDP TC=1只回同endpoint TCP；每次总查询预算建议5s、至多两次UDP尝试含一个TCP回退总deadline，沿既有重试库实现，不新增长时间sleep链。
- 隧道未就绪时非CN查询按现有唤醒/建链触发，有界等待，deadline到返回SERVFAIL；绝不临时直连。CN DNS/Direct业务不应为了隧道休眠而停止。反过来，纯直连业务不延长隧道payload idle；隧道DNS属于真实业务，可唤醒并计活动，health/keepalive仍不计。
- cold服务器bootstrap复用当前Npcap物理查询成果与CNAME/小包验证，参数改为唯一`dns.direct`。Go仅在初建/重连冷路径使用；业务DNS不能每查询绕Go逐包泵。多A服务器选择与已有健康lane保留不变，SNI不被地址域名替换。
- 物理切网：按既有owner generation关闭/重建失效direct socket、清resolver相关缓存；不能承诺TCP跨物理网络无缝续传。隧道仅换lane不销毁direct流和FakeIP引用。Stop停止接纳→取消DNS→回收direct IO与内部listener→现有WAL恢复，晚回调不能复活旧owner。

## 5. 资源预算与性能预期（初值可按证据调整）

| 状态 | 初始建议 | 回收/成本 |
|---|---|---|
| 已编译CIDR/trie | 每配置一份，只读共享 | 更新时原子换快照，不每flow复制 |
| DNS事务 | 256并发上限，可按实测调 | 同查询合并；满时明确SERVFAIL，不全局堵塞 |
| DNS缓存 | 4096项＋8MiB字节上限 | 正/负TTL与resolver版本；不延长上游TTL |
| 域名映射 | 按需增长，16384项软目标、60000项硬上限＋16MiB目标预算 | 活跃引用/TTL/隔离期保护，entry实测size后修预算；无可回收槽拒绝新合成并报告 |
| direct flow | 按需分块增长，4096默认上限、可调至16384 | UDP默认60s idle；TCP以FIN/RST/OS关闭为主，不能30s误杀空闲持久TCP |
| 转发缓冲 | 16–64KiB池化块、每方向按需借用，共享默认64MiB上限 | 无每flow预分配大窗口；达到上限仅该TCP背压/UDP有界丢弃 |
| direct/DNS分片重组 | 最多128 datagrams且8MiB、2s上限 | 按tuple+IPID+generation；非重组路径不占额度 |

以上是工程起点，不是虚构已测上限。用size_of/分配器采样核算实际字节；60000个映射不代表程序预分配60000个socket。统一粗粒度到期轮/现有timer结构，每次处理有限到期项，不每100ms全表扫描；正常DATA流缓存无需每包调用系统时间，复用worker时钟并降频更新last-used。

500Mbps/约1400B约4.46万包/s/方向；200Mbps约1.79万包/s，200Mbps全64B约39万包/s，不能把两种工况当同一CPU要求。区间分类每新流O(log N)、flow命中预期O(1)，域名trie只随DNS查询数增长。预期新增成本主要是**Direct TCP双内核腿/复制**、DNS新查询和少量flow查表；不凭“Rust”承诺百分比收益。

对原纯Tunnel稳定路径，分流开关同VM顺序A/B，目标CPU/实际交付GiB和p99无超出噪声的显著回退；可用5%作调查线，不作所有VM硬失败阈值。Direct吞吐对照同VM普通物理socket报告额外CPU、goodput、p99，计算每包/每GiB成本；系统TCP CPU包含内核，不能只看进程CPU宣称零开销。达到已知容量立即停止更重同族。

## 6. 配置迁移、GUI与开发顺序

沿当前schema注册canonical `dns.direct` / `dns.tunnel`（若现有单值键已满足可保留别名，一处真值）；明确IPv4可选port，初版不支持resolver域名，避免递归bootstrap。

- 老业务DNS列表仅第一项迁移到tunnel，旧bootstrap显式第一项迁移direct；缺省分别1.1.1.1/223.5.5.5。其余旧备选仅迁移提示“已取消备用”，不继续运行。显式新键优先，存在冲突给清楚迁移说明；保存后只写新单值schema。
- GUI两格：“直连DNS（中国域名/服务器地址解析）”“隧道DNS（其他域名）”；CN域名开关/规则来源日期与hash只读摘要，保留IP表/自定义CIDR与手动更新。展示配置已保存/当前effective，不宣称仅保存即生效。
- 先完成共享policy/DNS契约和一个真实Windows Direct TCP能力门；随后直连TCP/UDP＋DNS/FakeIP＋配置迁移作为一个完整工作包实现；再接GUI、测试与性能。有限startup-padding沿029原方案独立开发，只影响Tunnel，不拖着本次分流一起重做协议。
- M0主线单写，读实时cursor，收已有H1661/H1663等Actions；本次文档修订不重复派发、不改动在途源码。新agent遵循本页，不按旧功能卡恢复备份DNS/海量route/Go热泵。

## 7. 一组可复用验收，先正确出口再谈速度

每Action一个网络场景/测量进程，场景内可分阶段和同VM A/B。SOURCE/各平台编译产物hash复用，独立场景不同Action并行。用WSL2/netns可控CN/非CN模拟endpoint与两个真实DNS服务器，临时小规则表＋一项内置快照读回；不依赖公网网站可达或公共DNS答复变化作为唯一判据。接口抓取仅包头/计数摘要，不保留大pcap。

| 场景 | 必须实际验证 |
|---|---|
| D1 两DNS单值与三route-mode | CN QNAME只到direct DNS，其他只到tunnel DNS；实际进入Wintun的1.1.1.1/网关53按QNAME处理；旁路on-link案例独立说明，禁止伪称全机拦截；TCP53、UDP TC回退同endpoint；任一DNS黑洞不换地址/方向；两个字段相同地址仍走各自方向 |
| D2 域名/IP并集与CDN反例 | CN域名→非CN A直连；非CN域名→同一非CN A走隧道；非CN域名→CN A按IP直连；IP字面访问按IP规则。用真实TCP/UDP及两侧收件验证，不能只看classifier |
| D3 DNS边界 | 多A/CNAME、无关additional不学习、NXDOMAIN/TTL0/过期、AAAA阻断、HTTPS/SVCB不逃映射、restart恢复映射、容量满/碰撞有界；FakeIP在物理/服务端抓取为0 |
| D4 接线生命周期 | 分片/近MTU包、大TCP写入、小UDP混跑；规则更新不迁移老flow；lane轮换不打断Direct；idle下Direct仍通、Tunnel DNS唤醒；物理DNS bootstrap在接管后可重连；Stop/WAL/晚回调与模式重开 |
| D5 系统规模 | 内置/1万级规则加载，路由/WFP数不随条目数增长；没有新Go逐包热点；GUI两DNS保存→配置→owner有效值→真实出口；默认1460外层不被内层回写 |
| P1 纯Tunnel保护 | 同VM分流off/on顺序，50→100→200Mbps按容量上探，大包为主＋小UDP时延；未变模式不重复028整矩阵 |
| P2 Direct与混合 | 同VM直接物理socket基线→经过分流Direct TCP/UDP→直连大TCP与Tunnel小UDP共存；0损伤先看实现成本，容量内再一场5%单程50ms代表，Normal与Game4各做必要接线代表而非全笛卡尔积 |

报实际注入/唯一交付/缺失、p99与最长空洞、flow/DNS等待、缓存命中、进程/线程CPU＋host内核忙、RSS/peak及owned资源。DNS性能分缓存命中/未命中，不把远端解析RTT算成本地分类慢。纯Tunnel比较相同业务/实际出口；Direct路径省掉公网隧道延迟不等于CPU优化证据。

退出：真实Windows双出口、CN域名/IP并集、单DNS不回退、不会CDN误分流、普通Tunnel性能保护、配置/UI可读回与owned Stop全部有证据；NOT_RUN/设计完成不冒充实现PASS。不重新要求028排除的多Wintun或全L3，不增加Android/服务器新wire工作。

## 8. 实现参考（借鉴方法，不照搬依赖树）

- [sing-tun system TCP接入源码](https://github.com/SagerNet/sing-tun/blob/dev/stack_system.go)：原始包改写至本机listener及逆映射方法；Windows适配要先验，实施时锁参考commit并审查许可，不复制Go热路径。
- [sing-box FakeIP](https://sing-box.sagernet.org/configuration/dns/server/fakeip/)：本地地址映射思路；本项目选CN域名局部启用，不要求代理所有TCP。
- [v2fly域名数据](https://github.com/v2fly/domain-list-community)：构建时固定版本与许可，运行时不解释整个配置生态。
- [Microsoft IP_UNICAST_IF等选项](https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ip-socket-options)：接口字节序与源绑定按官方和旧项目已验实现。
- [smoltcp](https://github.com/smoltcp-rs/smoltcp)：仅在内核接入真实不成立时的Direct TCP备选；不预先并行开发两个栈。
- 旧源 `wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984` 的 `internal/windowsclient/userspace_tcp_direct_windows.go`、`direct_udp_windows.go` 和 current PLAN029 bootstrap：复用行为/绑定/回包/失败语义，当前Rust平台模块接线。

本页为架构选择与待测预算，不宣称经过上述全部性能验证，也不保证域名分类能识别应用加密DNS或规则之外的中国网站。
