# PLAN029｜Windows中国IP＋域名分流、单DNS、配置与有限填充

**IN_PROGRESS**；2026-11-12用户已启动，并进一步授权中国IP分流升级为IP＋域名并集分流、直连/隧道各一个DNS。此前产品测试范围不因方案更新自动升级。沿用[总入口](M0-LEGACY-ROLLOUT-20261102.md)、[M0提示词](../prompts/M0-PLAN029.md)。

**本次关键设计唯一入口：[CLIENT_SPLIT_DNS_CONTRACT](../architecture/CLIENT_SPLIT_DNS_CONTRACT.md)。** 它取代旧主备DNS、NIC多DNS轮询、普通DNS一律Tunnel、中国IP单独分流条款；历史源码/日志只作证据。保留原Rust隧道/FEC/Game，新增客户端分流执行层，不改服务端协议、不恢复Go逐包热泵。

## 1. 地址字段与解析职责

MTU与padding余量统一消费先行[PLAN027A](M0-PLAN027A-MTU-UNIFICATION-20261102.md)落实的[MTU_CONTRACT](../architecture/MTU_CONTRACT.md)。内层IPv4后续片没有TCP/UDP端口，不得当新流重领填充；无需为识别填充重组所有IP分片。

- 客户端“服务器地址”允许IPv4字面值或DNS域名，端口独立；沿既有配置schema增加/明确canonical服务器地址键，旧server-ip可作为读取别名，不多维护两份值。server-name仍是服务端配置的借站域名/SNI；**不能把服务器地址的域名自动拿去替换SNI**。
- IPv4不查DNS，域名由冷层EndpointResolver解析。IPv6外层未获资格前，AAAA-only/IPv6字面值明确不支持，不能因此关闭隧道内IPv6阻断政策或转入死循环。本包不顺带开发IPv6外层。
- Resolver返回带来源/时间的候选数值IP及选定出口，raw/TLS接线只消费数值endpoint。既有API只有ParseAddr的地方不能只改GUI校验就算完成；需覆盖初建、重连、休眠唤醒及轮换。
- 自动导入连接配置包含server address/port与借站域名；手填路径同样有效。域名解析不需要先建立隧道，UI显示正在解析/所选IP/具体失败原因，不显示密码或内部secret。

## 2. 单DNS与bootstrap

只保留 `dns.direct`（默认223.5.5.5）和 `dns.tunnel`（默认1.1.1.1）两个单endpoint设置，普通界面各一个输入框。所有route-mode/Normal/Game都不使用备份DNS、系统DNS自动回退或跨方向竞速；UDP截断可对同endpoint做TCP回退。旧列表第一项迁移、剩余项明确停用，具体兼容见契约§6。

CN分流模式下：中国域名查询只走直连DNS，其他查询只走隧道DNS；中国域名、LAN/显式direct4、中国IP业务并集直连。其他两route-mode保持其语义，不强行开启中国规则。resolver出口由内部用途固定，优先于普通IP分类；即使隧道DNS地址位于CN网段，也不能被直连。

服务器地址解析是唯一必要cold例外，始终复用同一个 `dns.direct` 从物理出口查询，不依赖隧道先建好；复用H1659/H1665 Npcap/CNAME与小包修复，取消原bootstrap/NIC备用链。初建/已接管后重连/休眠唤醒均真实验证，服务器地址不改SNI，多A/TTL失败不先杀健康lane。新查询合并、缓存、deadline及DNS回包分流见契约§4。

## 2A. Wintun捕获后IP＋域名分流

强制保持少量owned `/1` 捕获与控制例外，禁止数千CIDR路由、补集路由、等量WFP/NRPT规则。原已有更具体on-link/LAN路由保留；不能声称所有LAN包都进Wintun。被捕获业务由同一Rust ingress统一分类，flow固定出口，原隧道业务不终止TCP、不增加代理栈。

- IP表冷编译合并区间，flow命中O(1)；域名trie只处理DNS查询，不逐包解析TLS/SNI。
- **选择性FakeIP只用于已解析成功的中国域名**，保证CN域名海外CDN仍直连且不把共享IP的无关非CN域名误放。非CN域名保留真实IP、照旧进隧道或按CN IP直连。FakeIP不进入隧道或物理外网；TTL、映射持久/回收、CNAME、HTTPS/SVCB与DoH能力边界按契约§2.2，不自行简化成共享IP反查表。
- Direct UDP为Rust异步物理绑定socket；Direct TCP首选Rust本地内核TCP接入＋物理socket，两腿有界转发，不复活旧Go gVisor热泵、不把raw TCP当socket payload。先做真实Windows小型能力门，条件不成立才按契约限定备选，不同时写两套。详见契约§3。
- 现有 `Bypass4/Direct4` 保存、旧Go分流、静态classifier单测均不证明native V4已经接通。实际出口、逆向回包、owned Stop、内存与首到性能均需源锁证据。

用户最新决定不接入老WFP：按契约§3A解除guard/stage/Ready/Stop前置，保留owned配置恢复；不以假guard蒙混。Wintun借用buffer/发送slot顺序是真实API约束，不是安全防御；无WFP的系统DNS与旁路能力边界要诚实验收。

施工与退出按契约§6–7：先可行性边界→完整DNS/Direct/配置工作包→实际双出口→必要性能保护。契约是详细施工方案，本页不复制另一套参数表。

## 3. 配置/GUI/portable，只补接线

复用旧中文WinForms、服务器列表/切换、原生网络事务与portable目录，不换UI框架。参数来自028唯一schema：默认值、适用模式、作用范围、生效时机；CLI/help/config/GUI/effective读回与功能卡一致。

MTU编辑框标“外层 MTU（字节，上限）”，默认1460；最大1500可显式配置；它包含外层IP/TCP/隧道封装、不含以太网头。状态只读展示“有效外层上限”和“内层 MTU（自动生效）/OS应用状态”。切换模式、FEC或服务器不要求用户手算扣减，也不把派生内层值回写到外层设置；普通GUI不提供内层MTU编辑框。保存/导入保持旧外层键单位，明确旧内层override迁移，按契约第1节处理。

- 重点核服务器IPv4/域名、port、server-name、账号密码、预共享route-key导入/填写及服务器专属信任材料、自动/手动IP、Normal/Game、cipher、FEC及Normal auto策略、MTU、重传开关、idle/rotation、直连/隧道两格单DNS（bootstrap复用直连值）、分流/IPv6、padding。
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

## 5. 测试与退出

分流/DNS按[契约§7](../architecture/CLIENT_SPLIT_DNS_CONTRACT.md#7-一组可复用验收先正确出口再谈速度)的D1–D5/P1–P2执行；一Action一网络场景、不同Action并行、按SOURCE/hash复用编译。用可控DNS、CN/非CN endpoint与实际物理/隧道两出口，不依赖公共DNS恰好可达，不以mock冒充Windows真实路径。

额外保留原029任务：
- 服务器IP/域名在实际DNS接管后可初建/重连/唤醒，SNI不变；单DNS失败明确失败、不切备用，多A有界尝试。
- GUI默认外层1460保存→不同模式连接→读自动内层→断开重开，外层仍1460；只读OS内层不作为下一次输入。所有本包设置保存→CLI/配置→owner→effective→真实行为完整接线。
- padding off/tls/flows，稀疏TCP/UDP与大TCP＋小UDP代表，同VM off/on顺序比较实际填充、CPU/RSS、首到/p99；业务不因padding等待，预算/MTU/重传原密文/长流不周期重启。只填Tunnel，Direct不填。
- Normal与Game4做平台接线代表，不重跑028七模式全矩阵；容量耗尽停止更重同族。保留028限定收口的未验范围，不顺带启动030或Android。

收口需要IP＋域名分流、单DNS不回退、bootstrap不自环、真实TCP/UDP Direct/Tunnel回程、路由规模不随规则数增长、配置/GUI、有限填充及owned Stop均有对应证据；不能仅完成配置界面就关闭029。更新现有功能卡/registry/cursor/evidence，不新建交接系统。

建链沿[TLS契约](../architecture/TLS_HANDSHAKE_CONTRACT.md)：预共享route-key不在线私有交换，业务填充不改外层标准握手。当前默认1460与Rust自动内层预算不变。
