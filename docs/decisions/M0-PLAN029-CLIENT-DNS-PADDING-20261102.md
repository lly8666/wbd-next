# PLAN029｜Windows域名连接、配置界面与有限新流填充

PLANNED；[总入口](M0-LEGACY-ROLLOUT-20261102.md)、[提示词](../prompts/M0-PLAN029.md)。依赖028参数/effective/会话接口，DNS解析与UI静态接入可并行先做。复用027成熟Rust收发、DNS/WAL和生命周期；不重写分流栈、FEC、重传或黑洞恢复，不把UI存在当网络生效。

## 1. 地址字段与解析职责

MTU与padding余量统一消费先行[PLAN027A](M0-PLAN027A-MTU-UNIFICATION-20261102.md)落实的[MTU_CONTRACT](../architecture/MTU_CONTRACT.md)。内层IPv4后续片没有TCP/UDP端口，不得当新流重领填充；无需为识别填充重组所有IP分片。

- 客户端“服务器地址”允许IPv4字面值或DNS域名，端口独立；沿既有配置schema增加/明确canonical服务器地址键，旧server-ip可作为读取别名，不多维护两份值。server-name仍是服务端配置的借站域名/SNI；**不能把服务器地址的域名自动拿去替换SNI**。
- IPv4不查DNS，域名由冷层EndpointResolver解析。IPv6外层未获资格前，AAAA-only/IPv6字面值明确不支持，不能因此关闭隧道内IPv6阻断政策或转入死循环。本包不顺带开发IPv6外层。
- Resolver返回带来源/时间的候选数值IP及选定出口，raw/TLS接线只消费数值endpoint。既有API只有ParseAddr的地方不能只改GUI校验就算完成；需覆盖初建、重连、休眠唤醒及轮换。
- 自动导入连接配置包含server address/port与借站域名；手填路径同样有效。域名解析不需要先建立隧道，UI显示正在解析/所选IP/具体失败原因，不显示密码或内部secret。

## 2. 防DNS自环：独立直出bootstrap路径

系统业务DNS劫持与建立隧道所需DNS是不同职责。不能仅在第一次Apply前GetAddrInfo一次；开启劫持后的重连必须仍能解析。

执行顺序：

1. 接管网络前记录真实物理出口、源IPv4、网关和原DNS，排除Wintun/自身虚拟DNS。先准备原生owned的控制流旁路资源；解析完成才安装所选服务器endpoint旁路并进行真实TLS。
2. Bootstrap查询使用绑定物理源地址/接口的独立socket，优先原有效物理DNS，失败尝试配置的备用（默认1.1.1.1/8.8.8.8，可手动改）。复用旧 `internal/windowsclient/direct_udp_windows.go` 的bind+IP_UNICAST_IF方法与现有DNS实现；不造完整DNS服务器。绑定接口与WFP/重定向豁免**两项都要验证**，不是设置了接口就当然绕过本机劫持。
3. 查询与应答的必要规则通过现有owned网络事务安装，只限本程序bootstrap流/目标DNS，UDP和必要TCP回退均覆盖；不能为自己解析而让全机所有DNS直连，不能关闭全局DNS保护。也不要给用户系统DNS反复切换/flush来救自己。
4. 读回实际出口/所选IP，给服务器候选安装有限精确旁路；不追加成千上万路由。旧endpoint仍有lane使用时保留引用，新endpoint真实就绪再回收旧规则，Stop按owned记录恢复。
5. 查询失败不先杀健康lane，也不破坏已生效网络配置；沿现有建链退避重试，不另建每秒DNS守护线程。cold DNS工作不占Rust热锁，不阻塞已有业务。

缓存：沿成熟DNS库TTL，收到有效响应才更新；无TTL可用时采用明确短期缓存（例如60s），不宣称它是真实TTL。合并同域名同时查询，数目有界；不逐包查DNS/不每条Game lane查询。重连失败可失效缓存并重新查询，不永久锁死旧IP。TTL到期只影响下一次选择，不强制断健康连接。

多A地址沿最近成功/可达顺序有界尝试；**同一Game组初建选定一个endpoint**，不能每lane随机落到不同后端。域名IP变化不等于两台独立服务器共享会话；新端支持旧session恢复才续，否则明确完整重认证/地址重新生效，不承诺跨独立服务器无缝迁移。端口/site/config归属以028为准。

普通业务DNS继续默认主备1.1.1.1/8.8.8.8并有Windows手动入口，按用户分流政策走；bootstrap查询是必要受控例外。LAN/中国IP/TUN分流、内层IPv6空路由复用既有逻辑，不扩展复杂多代理共存或极端多网卡切换。本轮只要求一个代理实例与普通网卡重连有效。

参考：[Microsoft IP_UNICAST_IF](https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ip-socket-options)；旧代码见[direct_udp_windows.go](https://github.com/lly8666/wobuzhidao/blob/a7a82db31fe736ffedee330795a3234d358f1984/internal/windowsclient/direct_udp_windows.go)。其接口索引字节序需沿实现，禁止凭名字重新猜。

## 2A. Windows 中国 IPv4 分流：Wintun 先捕获、后分类（用户 2026-11-12 明确指定）

**本条是 PLAN029 的强制实现/验收门，不是可选性能建议：维持 Windows 原有紧凑 Wintun 捕获方案。严禁把内置中国 IPv4 的数千条 CIDR、局域网前缀或用户自定义直连清单逐条写入 Windows 系统路由表（包括批量 New-NetRoute/CreateIpForwardEntry2、隐性 PowerShell 回退等）。** 不可换一个实现层把同等规模的规则灌入 WFP/防火墙来规避本约束；避免巨大系统规则、慢 Apply/Stop、系统 FIB 冲突和 WAL 恢复开销。

### 当前代码实情与必须补的接线

- **已有资产要复用：** Go `internal/splitroute/policy.go` 以 `go:embed china_ipv4.txt` 内置中国 IPv4 CIDR（老快照 2026-10-03，共约 6209 条原始前缀）；旧 `route-mode=bypass-lan-cn|bypass-lan|all`、`china-ip-file`、`update-china-ip`、`direct4`、GUI“导入/手动更新/内置列表”均已有；保留固定HTTPS更新、CIDR完整校验、失败不损坏旧快照、重连应用和来源/许可。无自动后台下载，离线默认可使用内置数据。
- **已有捕获机制要保留：** `internal/windowsclient/compact_plan.go:BuildCompactNetworkPlan` 只用少量 owned 路由实现 Wintun IPv4 公网捕获，基础为 `0.0.0.0/1` 与 `128.0.0.0/1`，加真实服务器 underlay 物理出口的精确 `/32` 逃逸和必要的少量 DNS `/32`；原 OS 已有的更具体 on-link/LAN 路由保留。不能把中国网段扩成系统 direct route 或从现有有限捕获退回“补集数千条 capture route”。
- **关键缺口必须真实修复：** 当前正式 Windows 原生 `--native-v4-product` 虽读取/传递 `Bypass4/Direct4`，但 `BuildCompactNetworkPlan` 在 OS route plan 内置空它们；旧 `TUNScopedFlows` / `TUNPacketDispatcher` / 原生物理 TCP/UDP direct 接线在旧 Go 非 V4 分支，**不能以旧代码存在、GUI保存或本地分类单测当作正式 V4 已按中国 IP 真直连**。先跟踪当前 Rust 原生 Wintun 收包路径、OS capture 与分类点，补全实际 V4 执行链；不绕回 Go 逐包热泵或第二数据面/控制器。
- **分流顺序固定：** Windows 原有有限路由先把应捕获的 IPv4 送入 Wintun → 在当前 native Wintun ingress/generation 内按目标 IPv4 及业务DNS优先级作有界分类 → 中国/LAN/自定义CIDR判 direct，经真实物理 NIC 绑定的原生 TCP/UDP 直连出口，并把真实回包按原 flow/lease/generation 安全交还；其他 IPv4 走已认证 Rust/FEC/Game 隧道。DNS-hijack 开启时普通 UDP/TCP 53 的隧道内 DNS 优先于 CN/LAN 直连；服务端/Bootstrap 控制流按精确 underlay 旁路，不被 Wintun/DNS 自环。
- **效率与隔离：** 连接建立时对 CIDR 排序归并为只读有界区间，按目标地址查找或流级缓存；不逐包扫描 6209 条文本规则、不逐包改 Windows 路由或 WFP、不在 Go 添加稳定态逐包热路径。依赖现有 interface+generation 关联/片段校验、真实 socket 接口/源地址绑定；未知片段、外部接口、损坏规则和退出/换网严格 fail-closed，不能以错误直连造成泄漏。原 `route-mode` 三种语义保持一致，`all` 仍保护服务端和必要本机地址。
- **用户操作与状态：** GUI 的“分流模式/中国IP表/额外直连网段”必须走 CLI→native owner→实际分流执行路径；当前读取的是内置列表还是用户导入/更新快照要能只读报告，不能只显示保存成功。沿现有 WAL/精确 owned CAS 管理少量路由、DNS、WFP；Stop/失败/换网恢复宿主原路由，不能触碰非本程序所有的系统规则。

### 必须增加的真实 Windows 验收

1. 在签名 Npcap/Wintun、同一真实 GUI/CLI 原生 V4 构件上，使用默认内置中国 CIDR 及导入列表，各测可控 CN IPv4、LAN、自定义CIDR和非CN IPv4 的 **UDP/TCP 实际物理出口/隧道交付**（抓包/双端socket源地址或可核对的OS路由收发），不能只测 classifier 返回值、Wintun就绪或 mock。
2. 启动前、Applied后及 Stop/故障恢复后记录 Windows `Get-NetRoute`/IP Helper 的实际 owned 路由键与数目；提供**与中国 CIDR 条目数无关的常数级有限 route 数量**证据，只允许两条 `/1` 和受控 underlay/DNS 例外，不出现数千条中国网段/补集/用户自定义CIDR。额外检查未污染外部既有路由以及 WFP/NRPT/WAL 精确清理。
3. 验三种 `route-mode`、DNS 53 优先级、bootstrap DNS 物理出口、CN TCP/UDP 双向回复、fragment/多flow/不同generation、重连/Stop；错误或无法物理绑定时禁止静默漏流。不同模式无需重新全跑 028 七模式弱网矩阵，聚焦 Normal 和 Game4 的真实接线代表。

**029 退出判据增量：** 上述 Windows V4 **“Wintun 先劫持后分流 + 不产生海量 Windows 路由 + 真实直连/代理双路径”**有源锁真实 OS 收发与 owned Stop 证据；在此之前标 `NOT_QUALIFIED`，不能用旧 `wobuzhidao` 的分流 PASS 或 028 signed Wintun 普通隧道 PASS 替代。此项可以同本包 DNS bootstrap 和 GUI 验收合并最少数量的场景，但不能跳过实际出口区分。旧原生反例及历史 FAIL 保留。

## 3. 配置/GUI/portable，只补接线

复用旧中文WinForms、服务器列表/切换、原生网络事务与portable目录，不换UI框架。参数来自028唯一schema：默认值、适用模式、作用范围、生效时机；CLI/help/config/GUI/effective读回与功能卡一致。

MTU编辑框标“外层 MTU（字节，上限）”，默认1460；最大1500可显式配置；它包含外层IP/TCP/隧道封装、不含以太网头。状态只读展示“有效外层上限”和“内层 MTU（自动生效）/OS应用状态”。切换模式、FEC或服务器不要求用户手算扣减，也不把派生内层值回写到外层设置；普通GUI不提供内层MTU编辑框。保存/导入保持旧外层键单位，明确旧内层override迁移，按契约第1节处理。

- 重点核服务器IPv4/域名、port、server-name、账号密码、预共享route-key导入/填写及服务器专属信任材料、自动/手动IP、Normal/Game、cipher、FEC及Normal auto策略、MTU、重传开关、idle/rotation、业务DNS主备及bootstrap DNS高级项、分流/IPv6、padding。
- 不增加为内部调试服务的高级选项大墙；沿用旧字段，缺口集中补。一项设置至少一条真实生效证据，能共享一个实际场景读回的不要拆几十个Action。
- 更换服务器/账号/加密/模式/MTU需要新会话时，先正常Stop或现有安全切换，再接新配置；不能GUI显示新值而owner仍用旧值。保存不等于当前生效，显示“下次连接生效/当前已生效”。
- Portable配置、状态、日志和随包库留在程序目录；Npcap/系统服务资源沿现有安装方案，不为UI运行临时释放脚本。没有新权限或GUI库升级任务。

## 4. 新流启动填充：低成本扩展，不增加等待

旧 `tls-startup-padding`默认off、只被动识别TLS。本包可对**隧道内TCP/UDP新流**做有限填充，业务首到永远优先，不改真实业务内容，不为随机时序sleep/delay发送。

配置一个canonical模式（建议 `startup-padding=off|tls|flows`），默认off；旧bool true映射tls保留原语义，flows是明确新选择。GUI用“关闭/仅TLS启动/所有TCP与UDP新流”。同配置不得隐含两套policy，CLI/别名冲突规则统一。

实现定案：

- off快路不分配新增跟踪表、不取随机数、不新增逐包时钟/解析；flows只复用已解析的流信息。额度沿owner已有首发字节计数结算，不新加全局每包锁。
- 复用现有flow identity/解析，不重组4KiB TLS前缀来识别所有新流。TCP根据新连接/流实例，UDP根据现有5元组新流活动；不能把每个UDP包或每次lane轮换当新流。TCP纯ACK、控制/Health、FEC parity、外层重传不触发新预算；直连分流不填。
- 沿老上界：每逻辑隧道最多256个受跟踪流、前12个合格首发record、每流最多2048B新增padding；启用窗口一次随机1–2s（由旧2s上限收敛），每record随机0..min(256B、剩余预算、实际MTU余量)。随机的是**可填充窗口与字节量，不是业务发送时间**。旧16MiB累计上界如仍有实际用途可保留，不重造容量模型。
- 正常成功首发的字节额度按现有padding预算≤约10%，最多2KiB启动突发；Game实际多lane新增填充字节也记账，不能每lane重新领一整份逻辑流预算。无空间/预算/跟踪槽直接跳过，不为padding切碎本来能直送的大包，不挤占FEC符号和新业务优先级。
- 在现有record padding位置、AEAD seal前追加可去除padding，LINK/FEC编码语义和业务原文不变；内部仅携带必要padding eligibility，不能加线上DATA固定字段。原密文外层重传不重新随机或重新seal。当前codec没有对应能力时先补明确的受保护版本/能力接口，不贴自造明文尾标。
- 启动窗口结束后保留已有flow的“已处理”标记直到其正常结束/idle淘汰，不能每30s对长流重新启动填充形成周期特征。复用流表生命周期/有界队列，没有每流线程/独立定时器；一轮仅处理有限到期项，状态满跳过新流。
- 填充不是“无法识别”保证；本包验有限/不延迟/开销及外层格式，不能为追求未知DPI百分比无限增加字节/观测。

## 5. 独立测试与退出

| 场景 | 验收重点 |
|---|---|
| IPv4与域名初建 | 同一实际服务器均通；address与SNI不同，真实借站握手保留 |
| DNS已被接管后重新解析 | 先连、开启真实DNS/WFP、清本程序缓存、正常Stop/重连/唤醒；bootstrap从物理出口出入，不进TUN自环 |
| 主DNS失效/多A/地址更新 | 可控DNS夹具只损伤目标DNS；备用生效，多A有界尝试，IP变化后旧lane与旁路正确回收，健康连接不因查询失败中断 |
| 失败边界 | NXDOMAIN/超时/AAAA-only清楚报错，无无限重试/网络脏状态；IP输入不依赖DNS可用 |
| 新配置/UI | 读回实际DNS/分流/IPv6/MTU/加密/FEC/mode等；同账号客户端改一个不串另一个，Stop恢复旧网络 |
| Windows Wintun 后分流与路由规模 | 原生V4真实 CN/LAN/自定义 direct TCP/UDP 经物理NIC，非CN 经 Rust 隧道；内置/导入IP表及三模式，DNS53优先；OS Get-NetRoute 启动/Applied/Stop无数千条 route，WFP/WAL精确回滚 |
| padding模式 | off零新增、tls保留旧触发、flows覆盖TCP/UDP，超预算/满表/MTU边界/重传原密文/长流不周期重触发 |

DNS用Actions可控真实应答器/TTL/黑洞注入保证可重复，验证真实Windows物理接口+owned规则，不只mock解析器。默认公共DNS地址核配置与一条可达读回；外网DNS偶发不可达与产品自环分开记录。保护Actions管理连接但不能绕过被测业务路径；故障退出按现有owned恢复，不新建救援系统。

UI/config验证补一条：默认外层1460保存→不同模式连接→读自动内层→断开重开，外层输入仍1460；较小实际路径只影响effective展示。只读内层值不得作为下一次连接输入，padding直接使用027A给出的余量，不按GUI的1460自行扣减。

模式覆盖：DNS重连/唤醒选Normal、Game4最高档两个真实代表；七模式换lane完整表由028统一维护，不在此重跑。域名有效的每次换lane不得误把SNI改为服务器域名。padding做稀疏小TCP/UDP及持续大TCP+小UDP各一条容量内同VM off/on，报实际填充、CPU/RSS、首到/p99/超时；正常业务不为padding主动延迟，差异超过噪声才修，最多一次必要反序。默认off普通性能不回退；不重做200M全矩阵。

退出：域名在真实DNS接管后仍可初建/重连/唤醒，配置与UI生效，Windows native V4 内置中国IP数据能在 Wintun 捕获后真正执行直连/隧道分流且 OS 路由数保持常数级，有限填充各模式语义及成本清楚，Stop无脏状态；更新dns-split-ipv6/gui-config-feedback/相关新功能卡，不重复新建分流系统。

建链沿[TLS建链契约](../architecture/TLS_HANDSHAKE_CONTRACT.md)：route-key缺失本地提示，不从被劫持DNS/网络私有前导取得；本包新流填充仅用于隧道内业务，不能用于掩盖或改写外层TLS握手。
