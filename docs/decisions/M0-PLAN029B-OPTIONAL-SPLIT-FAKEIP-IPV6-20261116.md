# PLAN029B｜分流按需加载、普通/高级 CN、统一 IPv4 业务政策

状态：**DESIGN_APPROVED / IMPLEMENTATION_NOT_STARTED / PRODUCT_TESTS_NOT_RUN**。2026-11-16 用户授权将本轮讨论整理入库；本次只交付方案，不声明产品已改。实施者 M0，产品仍在 `main` 单写。

入口：[029](M0-PLAN029-CLIENT-DNS-PADDING-20261102.md)、[分流/DNS契约](../architecture/CLIENT_SPLIT_DNS_CONTRACT.md)、[029B接续提示词](../prompts/M0-PLAN029B.md)。本方案是029的增量工作包，**在当前已冻结的优化/验收批次安全收尾后接续，纳入029最终收口，030之前完成**；不取消在途Action、不等整个029先关闭，也不借此重开028/弱网全矩阵。

本页仅覆盖三项语义：①关闭分流的真实资源退出；②CN域名强制直连可选；③所有受管DNS的AAAA策略与现有IPv6入口处理。与旧029“CN域名默认始终直连、CN关闭可删除全部域名匹配、只处理CN AAAA”的表述冲突时，以本页为准。其他协议、功能与成熟修复不变。

## 1. 定案与范围

| 项目 | 实施决定 |
|---|---|
| 分流关闭 | 所有**已被本程序接管**的普通业务走原Rust隧道；不实例化业务Direct/FakeIP/分流规则和清理任务。DNS、IPv6基本检查、启动填充独立保留 |
| 普通CN | DNS仍按CN域名选direct/tunnel；回复真实IPv4，业务只按LAN/direct4/CN IPv4判断，CN域名解析到海外IP走Tunnel |
| 高级CN | 一个 `cn-domain-direct` 开关启用选择性FakeIP；CN域名海外IP仍Direct。仅CN模式有效 |
| DNS IPv6 | 所有受管UDP/TCP53的普通AAAA查询在本地立即NOERROR/NODATA，无上游查询；A不受影响 |
| Windows IPv6 | **保留现有IPv6接管与绑定，在既有IP入口复用版本检查并丢弃**；不解绑Wintun IPv6、不另开发IPv6栈/过滤驱动/旧WFP guard |
| Linux IPv6 | 保留现有自有TUN启用前 `disable_ipv6=1`；保留现有读包检查，不改宿主全局设置 |

优先级仍为真实首到、低延迟/无跨流HOL、低CPU；允许有界按需内存。标准TLS建链、认证/租约/generation、完整性、原密文机会重传、MTU、真实驱动与owned Stop不退让。外层MTU1460、Rust自动内层预算不变。

**不属于本包**：替换Direct TCP栈、导入sing-tun/Go热泵、调整FEC/重传、改外层wire、全面Linux/OpenWrt分流、Android适配、系统全局禁IPv6、DPI/DoH解密或安全DNS封锁。已有平台共享配置与纯Rust逻辑应编译/回归，不能把Windows证据推广到Linux产品。

### 当前源码入口，开工先核最新main

初审基线 `601d540401b7d516bf1e1dfaa9c2998cce07defb`（开工重新核最新main，不锁死在本基线）：

- `r0/go_overlay/cmd/wbd-client/m0_plan029_cold_split_windows.go`：既有 `split-enable`、route-mode、规则/日志路径的冷构造。
- `crates/wbd-engine/src/v4_windows_native_runtime.rs`：V3构造NativeSplitWorker，DNS回程、启动填充、Direct通知/线程接线；不能简单退回V2丢失新功能。
- `v4_windows_native_split.rs`、`v4_client_split.rs`、`v4_client_split_wire.rs`：当前all已有普通DATA快路，但对象与基础资源仍存在，CN与FakeIP当前耦合。
- `v4_windows_native_dns_{direct,client_tcp,tunnel}.rs`、`v4_client_dns_{wire,answer,cache,pending}.rs`：现有CN AAAA/HTTPS/SVCB空回答，真实UDP/TCP53路径与缓存。
- `v4_client_startup_padding.rs`：填充必须脱离业务分流实例的生命周期依赖，保持原算法/资格边界。
- `r0/go_overlay/internal/v4productcli/linux.go::openTun`：已仅对新建自有TUN禁IPv6；`crates/wbd-platform/src/linux_tun_sink.rs`已有IPv4版本检查。

M0先阅读本批涉及调用链及最近修复，不复活已撤回的读调度/FIN方案。H1940之类候选必须按其自身SOURCE收结果，不能被029B设计改写为已通过。

## 2. 分流关闭：冷构造真正退出，公共功能不随之消失

### 2.1 只保留一套配置含义

继续使用现有 `split-enable` 与 `route-mode=all|bypass-lan|bypass-lan-cn`，不新增另一个总开关：

```text
effective_business_split = split-enable && route-mode != all
effective_cn_domain_direct = effective_business_split
                             && route-mode == bypass-lan-cn
                             && cn-domain-direct
```

- `split-enable=false`：实际按all处理已接管业务；保存的route-mode/CN偏好可保留，UI显示当前未启用，不能启动旧Go分流作为暗中替代。
- `route-mode=all`：即使保存split-enable=true，也不创建业务分流实例。all不是“仅绕过LAN”；原OS更具体on-link路由与必要控制例外仍按029范围诚实报告。
- `bypass-lan`只加载LAN/direct4；不加载中国规则/FakeIP。CN模式才加载CN IP与DNS所需域名索引。
- 非活动功能的规则文件缺失、DirectFlow容量、FakeIP pool设置不应阻挡纯Tunnel/DNS启动；只解析必要的通用语法及活动功能约束，不为关闭功能做昂贵导入/冲突审计。

### 2.2 在原owner内部拆职责，不另造框架

以最小结构调整把当前NativeSplitWorker的公共与可选部分分开；可用普通结构体/Option/枚举，名称由M0结合代码决定，不要求另建线程或通用插件体系：

1. **基础入口/隧道**：既有包长/版本、租约、MTU与generation校验，所有模式必需。
2. **DNS服务**：单DNS、bootstrap、UDP/TCP53重定向/回程及AAAA空答，独立于业务分流。
3. **StartupPadding**：独立可选，off不建跟踪表；tls/flows按既有支持模式与预算工作，不以分流开关决定是否支持。
4. **业务分流**：仅effective_business_split=true创建；包含只读规则、Direct TCP/UDP/NAT、flow/fragment状态、就绪调度和业务Direct回程队列。
5. **FakeIP**：仅effective_cn_domain_direct=true创建；分配/映射/引用/持久writer/到期处理才存在。

**全隧道的普通非DNS包**绕过业务分类器与Direct表；复用已解析IPv4头，不查域名、CN集合/flow pin、不整包clone、不调用Go、不逐包读配置/时钟或加锁。DNS和启用的填充各走自己的最小路径，碎片/MTU继续原隧道语义，不能为“快路”吞掉有效后续片。

资源要求是“**停用组件没有实例和周期性工作**”，不是宣称整个进程零内存/零线程。尤其：

- 不建立业务Direct listener、业务socket表、Direct专属wait组/轮询/清理任务，不配置其专属辅助route/Defender Allow。
- DNS-over-TCP接入如确实复用同类kernel listener，只保留**DNS用途**的最小资源；不能为追求“listener=0”删TCP53支持，也不能借DNS名义加载完整业务Direct器。
- DNS缓存/事务、bootstrap物理socket、公共回注mailbox可以存在；只含这些活动功能，不预分配整张16384 Direct流表。按实际用途计数，不用进程总线程数判断是否关闭成功。
- 普通all数据快路保留原有自有FakeIP候选范围的廉价拒绝检查，防止旧应用缓存被当真实地址传出；不因此重建映射表/writer。
- 收包/清理共享原owner，真正无工作时事件等待。现有Stop唤醒、半关闭、Fair wait与工作量反馈修复不得丢失。

## 3. 普通CN与高级CN：DNS出口和业务出口分开

### 3.1 唯一开关与迁移

canonical配置/CLI键定为 **`cn-domain-direct`**（boolean）；GUI显示“高级CN域名分流（FakeIP）”。仅CN模式启用控件，其他模式保留偏好但effective=false；不再同时暴露含义重叠的 `fakeip-enable`。若最新main已存在等价canonical键，统一复用它并明确迁移，禁止两份真值。

**新建配置默认false**；对升级前已保存且没有此字段的旧配置，按旧CN域名直连语义一次迁移为true，非CN/all中只是保存偏好、不启功能。必须区分“读旧文件缺键”与“新建配置”，不能通用 `missing=false` 偷改旧用户行为；可用现有profile版本/导入来源，不另建迁移数据库。显式false必须保留，CLI显式值按既有优先级覆盖，不用bool零值冒充未提供。

| 条件（CN模式，未被LAN/direct4显式规则优先命中） | DNS出口 | 普通CN false | 高级CN true |
|---|---|---|---|
| CN域名→CN IPv4 | direct | 真实IP、Direct | 现有选择性FakeIP、Direct |
| CN域名→海外IPv4 | direct | **真实IP、Tunnel** | **FakeIP、Direct** |
| 非CN域名→CN IPv4 | tunnel | 真实IP、Direct | 真实IP、Direct |
| 非CN域名→海外IPv4 | tunnel | 真实IP、Tunnel | 真实IP、Tunnel |
| IPv4字面值 | 不查DNS | 按IP规则 | 按IP规则 |

因此**FakeIP关闭并不关闭CN域名的DNS分类**：域名索引仍由DNS按查询使用，DATA不查。只有all/bypass-lan等不需要CN DNS选择的模式才不加载CN域名表。

### 3.2 实现边界

- false路径返回上游真实A/CNAME/多A/TTL，保持实际RCODE和截断处理；不能继续调用强制FakeAllocator/FakeJournal的合成器，再把fakes字段清空冒充关闭。
- 两档都只有 `dns.direct` 和 `dns.tunnel` 各一个endpoint；bootstrap始终唯一direct；不回退系统/备用DNS。内部用途优先于IP分类。CN→海外实际业务Tunnel不意味着把它的DNS查询改走Tunnel。
- 禁止“CN域名解析到的真实海外IP加入Direct集合/反查表”。这会使非CN共享CDN串流，也会让开关失效。不做DATA级SNI窥探。
- true继续复用已验选择性FakeIP多A、CNAME、持久发布、refs、TTL/隔离回收；不借此删除身份/持久语义或重写一套allocator。false完全不启动该writer/分配器，不产生新FakeIP，不读取恢复全映射、不周期扫旧journal。
- false可以保留旧portable journal文件供再次开启时安全恢复，不能为“关闭”删除历史仍可能被缓存的映射。只保留识别自有旧地址所需的有限范围元数据；旧假地址不得从Tunnel或物理口发出，不随便映射到新real。
- 开关/route-mode变更**下一次重连生效**，先owned Stop回收旧generation再按新配置创建；正常lane轮换不改变配置、不销毁活动Direct/FakeIP。刷新本项目使用的系统DNS缓存，明确应用内旧缓存可能需要重解析；未知旧FakeIP快速失败，不等映射、不跨代偷偷接旧出口，不开发无缝双表热迁移。

### 3.3 配置/UI/功能目录必须一起落地

更新既有参数目录/schema、Go冷配置/CLI help、Rust冷ABI、真实GUI保存/加载/导入/服务器配置、effective回执及 `dns-split-ipv6` / `gui-config-feedback` 功能卡。新字段仅本地控制面；不加长期线上字段，不要求服务端同配。

允许同批给本地ABI增字段/版本并同步caller、DLL/装配manifest、大小/对齐检查；不能滥用未知reserved位。相同SOURCE构建Go/Rust/GUI，旧DLL不能读取新结构。UI显示“已保存、下次连接生效”与owner实际effective两者区别。

## 4. IPv6：少产生、已接管即丢，保留现有最小机制

### 4.1 所有受管AAAA本地空答

在DNS公共入口、选择CN域名规则/上游**之前**处理普通有效的AAAA(qtype=28)：UDP53、应用TCP53走同一应答语义，bootstrap仍只请求A。Normal/Game、all/分流、FakeIP on/off均一致。

- 立即返回 `RCODE=NOERROR`、AAAA答案为空的NODATA，保留事务ID/合法question与TCP长度帧；正确处理RD/RA及现有EDNS边界。不要伪装权威答案/已验证DNSSEC，合成答复清AD。
- 不发送上游AAAA、不等待超时，不使用REFUSED/SERVFAIL/NXDOMAIN代表“IPv6关闭”。不因为AAAA空答污染同名A缓存或把域名判为不存在；A的真实NXDOMAIN仍保持NXDOMAIN。
- 不为实现空答虚构SOA/签名；没有适用负缓存TTL时，不声称客户端一定缓存多久。复用现有成熟wire builder，不引入第二套完整DNS库。
- 不把所有HTTPS/SVCB(64/65)一起封掉。**仅高级CN的选择性FakeIP域名**继续现有NODATA规则，防止hint/alias绕过映射；普通CN和非CN保留原响应，不为了IPv6删除H3/ECH/IPv4提示等能力。A答复附带的AAAA或HTTPS ipv6hint、加密DNS、旧缓存可能仍触发IPv6尝试，入口政策负责处理，不宣称所有IPv6地址来源消失。
- DNS-over-TCP已有部分帧、多请求、截断回退/FIN/Stop需要复用；AAAA过滤不能在TCP中间层把一条连接卡住。UDP上游TC后的同endpoint TCP重试仍只用于实际需要上游的查询。

### 4.2 Windows：不解绑Wintun IPv6

**本包明确不采用 `ms_tcpip6` 解绑方案。**不配置全局DisabledComponents，不恢复旧自定义WFP guard，不另写驱动/IPv6协议栈。原因：解绑TUN不等于主机禁IPv6，可能改走物理接口，且会破坏“先接管再丢”的原路径。

使用现有少量owned IPv6捕获配置，让受管IPv6进入原Wintun reader；在已存在的包版本/长度解析处立即拒绝，释放ring继续下一包。普通IPv4检查本来就读取首字节，不新增独立全包IPv6扫描、哈希表、逐包时钟/日志/锁、线程或定时器；可合并重复头解析，但不得删除长度/租约/MTU验证。

- IPv6不得进入业务分流、FakeIP、FEC、AEAD、Direct socket或触发Tunnel payload idle/唤醒/重建。少量本地统计复用现有计数，不逐包打印。
- IPv6丢弃仍算“已消费入口工作量”，保持原批次/公平预算；不能把IPv6当EOF、整批无工作或终止读循环导致紧随的IPv4睡200ms，也不能无限drain让其他任务饥饿。
- 不为零星硬编码IPv6额外开发ICMPv6响应引擎；该类应用可能等待自身超时，文档/UI按范围说明。若有真实可复现产品延迟问题，另以最小系统拒绝方案处理，不能凭猜测扩大029B。
- **默认路由不等于全部捕获**：已有更具体on-link、绑定物理接口、系统组件流量可能绕开本程序。保持029无旧WFP的明确边界，不把“多数受管业务IPv4-only”升级为全系统无IPv6泄漏保证；也不得为掩盖D4缺口解绑IPv6、删除宿主路由后测一个从未发出的包。

### 4.3 Linux：已有接口级关闭不重做

保留 `openTun` 在自有TUN up前写 `net.ipv6.conf.<owned_tun>.disable_ipv6=1`；只影响该接口，不改all/default/物理接口。Linux服务端TUN内部IPv4-only与客户端阻止物理IPv6绕行不是同一职责。读入异常包仍沿已有首字节检查，不为省几条指令移除包格式约束。接口重建/Stop沿既有ownership，不新增系统管理组件。

## 5. 一次完整实施，避免重复优化当前M0工作

1. 先恢复最新cursor、现有优化Action、已测SOURCE及近期FIN/就绪/公平性修复；安全收完当前批次。029B不要求重新解释所有历史，只回读本次触及路径。
2. 同批完成冷配置/effective、公共DNS/填充与可选业务分流解耦、普通CN路径、AAAA策略、GUI/目录/ABI/manifest及必要夹具。保持现有TCP后端、调度与FEC逻辑；不每个helper触发网络Action。
3. 冻结准确SOURCE；Actions组件/配置验证后，用已有真实签名Windows/WSL2夹具做以下代表场景。基线取**最新已合格的同产品路径**，不是未完成的H1940假设或历史Go版本。
4. 只修有具体证据的缺口，收够退出证据就停止；029B完成后回到029尚未完成清单，不因此启动030或另开栈优化工程。

## 6. 有界验收：配置可用、资源真关闭、真实出口、CPU/p99

### 6.1 功能和接线（组件用例可批量）

| ID | 必要范围 | 通过依据 |
|---|---|---|
| B0 配置/迁移 | 新配置false；旧CN缺键保语义；显式false；all和split=false压制业务分流；CLI/GUI导入保存→重连→effective | 原真实配置链/同源DLL，不能仅UI勾选或构造函数PASS |
| B1 纯Tunnel | split=false；另核split=true+all等价；DNS A/AAAA UDP+TCP；padding off与已支持tls/flows；bootstrap/休眠后解析 | 实际Tunnel业务/回包；无业务Direct实例、规则加载、writer或周期工作；DNS/填充实际仍有效 |
| B2 CN开关 | 同可控CN域名→海外A、非CN共享同海外A、CN IP、LAN/direct4、CNAME/多A；分别普通/高级 | 两出口真实观测符合§3表；普通CN无FakeIP/writer，上游选择不变；高级映射不出机、不污染共享IP |
| B3 IPv6 | 国内/国外QNAME，all/CN，UDP/TCP AAAA；A保持；真实硬编码IPv6尝试及IPv4混跑 | AAAA本地NOERROR空答/上游请求0；受管IPv6不出WBD隧道/Direct；IPv4连续前进；无可达IPv6测试路径则NOT_RUN |
| B4 生命周期 | 高级CN→普通CN→all的Stop/重连；系统DNS缓存刷新、残留应用FakeIP、lane轮换、晚回调代表 | 原配置生效边界、旧假地址不外发/不重绑；旧owner退出；DNS/路由/文件和已建立Direct按原策略回收 |
| B5 平台/模式 | Normal主测；Game2/Game4实际入口做短代表；Linux x86/ARM64共享库及已有TUN设置回归 | 各实际可用模式消费同一配置；未接线明确NOT_RUN/拒绝，不用Normal绿灯冒充全模式 |

不跑全模式×全部开关×全部DNS全排列。纯逻辑的组合在同一组件Action覆盖；真实模式接线选最少代表，必要跨模式冷构造缺口由M0现场补。Linux未有的完整客户端分流不由本包新增。Game不支持的padding按现有明确边界拒绝/显示不适用，不静默新增支持。

**真实IPv6要求**：复用现有D4失败经验，宿主必须有受控且实际可发往捕获路径的IPv6目标/路由（可在隔离测试网络搭建，无需公网）；记录应用发包、实际路由、Wintun入口/外口计数。单纯AAAA空答、宿主无IPv6路由或应用没发包都不能证明捕获有效。正常Stop及失败finally恢复owned网络状态。只保留有界计数/摘要，不大pcap。

### 6.2 资源与性能，只测真正可比较的场景

启动/effective回执低频报告：业务分流是否实例化、加载的CN IP/域名规则数、业务Direct listener/flow数量、FakeIP allocator/映射/writer状态、活动清理任务，以及**分清用途的DNS资源**。不要求RSS绝对为0，不为测关闭效果加入逐包完整时间戳/全局原子热点。

- **P-B1**：同VM旧/新顺序A/B，业务同为all、FEC/padding/MTU/repair一致、相同DNS与真实TCP/UDP负载。比较CPU秒/实际交付GiB、整机user/kernel、RSS/保留容量、空闲唤醒、唯一交付、小TCP请求响应p50/p95/p99、并行业务UDP p99/最长空洞、FIN/Stop。不能用旧关闭DNS/填充的V2当功能等价基准。若现有夹具把split off当旧适配器，先修夹具与有效路径证明。
- **P-B2**：固定普通/高级CN各自相同实际出口与业务，测关闭FakeIP后的持久writer/分配等成本变化。要比较纯机制成本，使用CN→CN目标使两边都Direct，DNS预热/冷查分别标注。CN→海外在两档出口不同，只做功能/实际体验报告，不能拿路线差异当算法CPU增益。
- 先用容量内Normal每方向10Mbps混合大小TCP/UDP、穿插稀疏请求；按已有资格可追加一次同场500Mbps单向或700Mbps双向聚合（350+350）的Direct保护测量，沿原夹具且声明方向。已有同源等价场景可直接复用，不为029B重新跑10GiB/30min或极限弱网矩阵。
- IPv6杂包混入是小比例真实控制流量代表，不做IPv6洪泛竞赛；检查“丢弃IPv6后IPv4继续”，避免把网络不存在误判性能好。
- 先通过资源真关闭/真实出口/无挂死硬门；性能不要求虚构的固定百分比收益。同VM对照若CPU/GiB或p99出现持续、超出本次噪声的退化就定位；5%可作调查线，不是所有p99/VM一刀切硬门。同时看绝对差、分位样本量和missing，不能靠丢慢包改善p99。p99样本优先每类数百至约千次短请求，报告实际数量，不以几个probe宣布尾延迟改善。
- 一Action一个场景/一个测量进程组，双端是同一场景；ON/OFF或旧/新是该场景预声明的顺序配对，禁止同时跑。独立场景可跨Actions并行；一次按SOURCE/manifest/hash构建后复用。宿主配置/核心配额/CPU饱和/steal或PSI/队列drop说明容量；达到容量不继续更重同族，不把单线程忙或软件空转一概甩给VM。
- 如差异接近噪声，最多一次反序确认；资源减少且功能/p99不退化即可保留，不为了追求漂亮百分比刷seed或增加十几轮测试。

## 7. 留痕和退出

沿现有devlog/evidence/功能卡/参数目录及M0 cursor，不增加第二套任务状态。每条证据标精确源码、构建来源/hash、actual effective、run/attempt、平台和范围；产品未测就是NOT_RUN，原FAIL保留。仅文档落地不改变当前M0任务/源码资格。

029B完成需要：§2停用资源真实退出而DNS/padding不丢、§3开关/旧配置迁移与双出口生效、§4所有受管AAAA及真实IPv6入口覆盖、配置/GUI/所有活动模式接线、必要同VM性能保护与owned Stop均有对应证据。未具备的范围明确保留，不以单个绿色Action收口。达到后更新029剩余清单，后续重复提示只恢复新事实，不再自创调优。

参考：[RFC2308 NODATA](https://www.rfc-editor.org/rfc/rfc2308.html)、[RFC9460 HTTPS/SVCB](https://www.rfc-editor.org/rfc/rfc9460.html)、[Linux接口IPv6设置](https://docs.kernel.org/networking/ip-sysctl.html)。引用用于固定语义，不据此宣称当前产品已通过。
