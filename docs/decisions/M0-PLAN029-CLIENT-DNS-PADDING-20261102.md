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
- Direct UDP为Rust异步物理绑定socket；Direct TCP首选Rust本地内核TCP接入＋物理socket，两腿有界转发，不复活旧Go gVisor热泵、不把raw TCP当socket payload。先做真实Windows小型能力门，按契约§3B有界调查后选择单一后端，不同时写两套。详见契约§3。
- 现有 `Bypass4/Direct4` 保存、旧Go分流、静态classifier单测均不证明native V4已经接通。实际出口、逆向回包、owned Stop、内存与首到性能均需源锁证据。

用户最新决定不接入老WFP：按契约§3A解除guard/stage/Ready/Stop前置，保留owned配置恢复；不以假guard蒙混。Wintun借用buffer/发送slot顺序是真实API约束，不是安全防御；无WFP的系统DNS与旁路能力边界要诚实验收。

**2026-11-13施工修订**：按契约§3B允许精确owned Defender Allow的A/B/C诊断；不接旧WFP、不全局关防火墙。Allow无效不能排除显式Block。禁止assemblyOnly形成“未验不许执行验收”死锁；真实adapter可执行，Applied/Ready仍按实际结果。共用Wintun回注先定位，TCP选型有界，UDP与四阶段OS事务独立推进。

**资源修订（附件第八条落地到契约§5）**：4096 Direct软水位、默认16384硬上限按需增长；64MiB是分配上限不是队列目标。Direct硬满仅拒绝新Direct，TCP单流背压，UDP局部有界丢弃，DNS缓存淘汰/事务表明确失败/FakeIP安全回收分别处理；不可共用满表把Tunnel挡住。D3/P2缩小测试容量，明确验证满载时其他流继续与压力后恢复。

施工与退出按契约§3B、§6–7：有界定位与独立施工→完整DNS/Direct/配置工作包→实际双出口与压力退让→必要性能保护。契约是详细施工方案，本页不复制另一套参数表。

## 3. 配置/GUI/portable，只补接线

复用旧中文WinForms、服务器列表/切换、原生网络事务与portable目录，不换UI框架。参数来自028唯一schema：默认值、适用模式、作用范围、生效时机；CLI/help/config/GUI/effective读回与功能卡一致。

MTU编辑框标“外层 MTU（字节，上限）”，默认1460；最大1500可显式配置；它包含外层IP/TCP/隧道封装、不含以太网头。状态只读展示“有效外层上限”和“内层 MTU（自动生效）/OS应用状态”。切换模式、FEC或服务器不要求用户手算扣减，也不把派生内层值回写到外层设置；普通GUI不提供内层MTU编辑框。保存/导入保持旧外层键单位，明确旧内层override迁移，按契约第1节处理。

- 重点核服务器IPv4/域名、port、server-name、账号密码、预共享route-key导入/填写及服务器专属信任材料、自动/手动IP、Normal/Game、cipher、FEC及Normal auto策略、MTU、重传开关、idle/rotation、直连/隧道两格单DNS（bootstrap复用直连值）、分流/IPv6、padding。
- 不增加为内部调试服务的高级选项大墙；沿用旧字段，缺口集中补。一项设置至少一条真实生效证据，能共享一个实际场景读回的不要拆几十个Action。
- 更换服务器/账号/加密/模式/MTU需要新会话时，先正常Stop或现有安全切换，再接新配置；不能GUI显示新值而owner仍用旧值。保存不等于当前生效，显示“下次连接生效/当前已生效”。
- Portable配置、状态、日志和随包库留在程序目录；Npcap/系统服务资源沿现有安装方案，不为UI运行临时释放脚本。没有新权限或GUI库升级任务。

## 4. 新流启动填充：低成本扩展，不增加等待

**2026-11-16 用户最新修订（覆盖H2015/H2021不限条数/不限时间的策略）**：每个新Tunnel TCP/UDP流随机选择**前20–30条合格record、2–3秒启动窗口**；两个门槛哪个先到就停止。窗口内每条独立随机0..min(500B、当次真实外层MTU/加密记录余量)，**不恢复每流2KiB总字节或10%比例预算**。仅原Normal Tunnel M1加密，默认off，Direct不填，业务不等待；复用同代际256流有界表和现有粗粒度到期调用，不产生逐流线程/额外定时器。**共享海外CDN同IP双域名相反出口NOT_REQUIRED**，不再开发/验收，不伪称该反例已通过。

旧 `tls-startup-padding`默认off、只被动识别TLS。本包可对**隧道内TCP/UDP新流**做有限填充，业务首到永远优先，不改真实业务内容，不为随机时序sleep/delay发送。

配置一个canonical模式（建议 `startup-padding=off|tls|flows`），默认off；旧bool true映射tls保留原语义，flows是明确新选择。GUI用“关闭/仅TLS启动/所有TCP与UDP新流”。同配置不得隐含两套policy，CLI/别名冲突规则统一。

实现定案：

- off快路不分配新增跟踪表、不取随机数、不新增逐包时钟/解析；flows只复用已解析的流信息。额度沿owner已有首发字节计数结算，不新加全局每包锁。
- 复用现有flow identity/解析，不重组4KiB TLS前缀来识别所有新流。TCP根据新连接/流实例，UDP根据现有5元组新流活动；不能把每个UDP包或每次lane轮换当新流。TCP纯ACK、控制/Health、FEC parity、外层重传不触发新预算；直连分流不填。
- 最新规则：首次合格record时每流随机抽取20..30条上限和2000..3000ms窗口；任一先到即停止，**即使某条业务record没有MTU填充余量，它仍计入前20–30条并启动窗口**，窗口内每record单独随机0..min(500B、实际M1外层记录剩余空间)。**无每流累计字节/百分比额度**；最多256受跟踪流，满槽时不填新流，普通业务照发。
- 实际MTU余量为0时直接填0，业务先发、不拆包、不占用FEC；Game4接CN分流不自动开启尚未验收的Game record填充。
- 在现有record padding位置、AEAD seal前追加可去除padding，LINK/FEC编码语义和业务原文不变；内部仅携带必要padding eligibility，不能加线上DATA固定字段。原密文外层重传不重新随机或重新seal。当前codec没有对应能力时先补明确的受保护版本/能力接口，不贴自造明文尾标。
- 复用原有有界flow标识和≤8项/粗粒度轮转回收，完成/过窗的活跃flow仍保留已处理标记直到真正idle，避免周期重启；不加逐flow线程、等待定时器、独立背景任务；原密文外层重传不再次抽样或重新seal。
- 填充不是“无法识别”保证；本包验有限/不延迟/开销及外层格式，不能为追求未知DPI百分比无限增加字节/观测。

## 4A. 2026-11-14 H1827真实慢路径与跨流HOL专项（用户新增施工优先级）

本段补充§2/§2A及分流契约§3B、§5、§7，不替代完整029出口。H1823真实同VM签名P2：普通物理TCP 1MiB回声281ms、Wintun FakeIP Direct TCP 6141ms；H1825双腿TCP_NODELAY源码经[签名Action43578369480](https://github.com/lly8666/wbd-next/actions/runs/43578369480)核实，物理296ms、Direct6360ms、120/120 Tunnel小UDP、半关闭及两端owned Stop均PASS。调大读量与NODELAY两种小假设均未解决约22倍异常，性能仍OPEN；不同Action主机绝不能拼作精确同VM算法A/B。

**按依赖和证据排序施工，不盲目继续调参：**

1. **先修工作量反馈与分腿定时。** 现有stage_sources返回的只是Tunnel数，Direct-only满8个Wintun读槽时仍可能返回0；Direct TCP accept/非阻塞收发取得进展也不回报TX wait。分别记录捕获总数、Tunnel数、Direct数、TCP socket进展、逆向mailbox满轮次；满量子可再公平轮转，不能多等10ms；遇WouldBlock停止即时自旋。以后共享Direct socket事件/IOCP就绪管理替换10ms周期轮询，不给每flow开线程或粗暴降为1ms。只在明确新时序后进一步追首个等待点。
2. **一个P2夹具贯穿大TCP全过程。** 既有每16KiB发送后sleep4ms是同条件的功能测试，不是峰值吞吐。单场记录connect、上传完成、半关闭、首回包、下载结束；Windows Tunnel小UDP从Direct TCP启动前直到TCP完全结束（保留原120条最小精确证据，并额外统计全程总数、p99、最长空洞、唯一交付及Stop）。远端需要时补内核TCP分腿收发/队列年龄时间；不能把原120条约数秒称为全程不卡顿。
3. **隔离DNS成功FakeIP的durable fsync。** 当前DNS答复在Rust TX调用同步FakeJournal.persist_batch/write_all/sync_data，虽然不逐DATA写仍可能阻塞所有Tunnel/Direct。单个有界写任务或复用既有阻塞设施；只有相关DNS回复等待准确fsync回执并确认pool.acknowledge_durable，其他业务继续。合并相同续期，失败只影响对应DNS并SERVFAIL，不能提供未落盘/可能错绑的FakeIP。
4. **低频journal紧凑化与恢复。** 现有16MiB append上限无压缩；由同一后台持久化worker在低负载创建只含有效/受保护隔离期映射的快照，用同目录临时文件fsync、原子替换和目录持久化（平台支持范围据实验证），读回验证后才继续发新FakeIP。失败不能使旧active/ref/隔离映射被重用，不引数据库，不在TX压缩。
5. **真实共享已分配内存而非pending len。** VecDeque在排空后可保留capacity；仅累加pending_bytes()不能兑现64MiB的已分配总上限。16,384个连接×双向64KiB理论2GiB只是风险上界，**并非已测RSS**。使用按需共享缓冲块归还池或精确追踪已保留capacity+低频空闲回收，保住已有TCP、小UDP与Tunnel压力退让，不每write shrink或为全流预分配。
6. **最后复核P1 CPU。** 真实同VM从7.375变7.9219 CPU秒/60s，增加7.42%但只约0.0091核；未单独归因于分流/重复flow查表/Direct空转/复制，亦未单独统计内核CPU。先处理调度/同步磁盘与分配风险，再以同SOURCE同VM顺序A/B看CPU/GiB、真实交付、p99、最长空洞，噪声与容量分开报告。

当前尚未合格的不止P2：Normal V3仍有GitHub Actions试验门、Game4 CN分流未接、GUI真实Connect/Stop及D4 IPv6/中断恢复和完整DNS/填充仍需落实。每批源码/夹具/日志同SOURCE冻结后再启动对应单场Action，不把某子项绿灯当029交付。

### H1832 正式冷入口与GUI接线（仍待本SOURCE签名实测）

H1831 [Action43585387611](https://github.com/lly8666/wbd-next/actions/runs/43585387611) 在SOURCE `268fdc150937416a51991b440a961a5dc96a1a3e`签名Normal验证异步FakeIP落盘后CN CNAME→两个真实A→两个不同FakeIP、物理Direct UDP/原Windows应用回包与owned Stop均PASS；应用首次DNS答复531ms/1次，不能与独立fsync或峰值延迟混同。H1829/H1830的Rust组件失败已保留并修复。

H1832正式冷配置新增`split-enable`（默认false，显式开启下次连接生效）和便携`cn-rules-file`（CN模式必填独立、有效、冷读的规则源）。CLI`--config`→真实原Go cold V3→单Rust Wintun owner；取消`GITHUB_ACTIONS`作为产品选择条件，原CI试验marker仅供现有单Action复测。GUI配置输入保存及内部绝对路径受控复制同SOURCE完成；网络Ready仍只能取本次签名driver/OS四阶段WAL、Rust owner/业务通路真实回执，不能把`--check-config`或设计当实际联网。Game2/4在未接`NativeSplitWorker`前若显式要求CN分流必须冷拒绝，而非假Ready；按既定029出口继续Game4接线。H1832新CLI/GUI源码和实体Stop的签名测试在本提交时**NOT_RUN**。

## 5. 测试与退出

分流/DNS按[契约§7](../architecture/CLIENT_SPLIT_DNS_CONTRACT.md#7-一组可复用验收先正确出口再谈速度)的D1–D5/P1–P2执行；一Action一网络场景、不同Action并行、按SOURCE/hash复用编译。用可控DNS、CN/非CN endpoint与实际物理/隧道两出口，不依赖公共DNS恰好可达，不以mock冒充Windows真实路径。

额外保留原029任务：
- 服务器IP/域名在实际DNS接管后可初建/重连/唤醒，SNI不变；单DNS失败明确失败、不切备用，多A有界尝试。
- GUI默认外层1460保存→不同模式连接→读自动内层→断开重开，外层仍1460；只读OS内层不作为下一次输入。所有本包设置保存→CLI/配置→owner→effective→真实行为完整接线。
- padding off/tls/flows：单元验证每flow前20..30合格record、2..3s窗口（先到为止）、随机0..500B与实际MTU且**不实施累计2KiB/10%额度**；真实物理Npcap/tcpdump核外层加密包长度/MTU、业务TCP/UDP回程、双Stop；必要时同VM off/on比较CPU/RSS与p99，Direct不填、业务不等待。
- Normal与Game4做平台接线代表，不重跑028七模式全矩阵；容量耗尽停止更重同族。保留028限定收口的未验范围，不顺带启动030或Android。

收口需要IP＋域名分流、单DNS不回退、bootstrap不自环、真实TCP/UDP Direct/Tunnel回程、路由规模不随规则数增长、配置/GUI、有限填充及owned Stop均有对应证据；不能仅完成配置界面就关闭029。更新现有功能卡/registry/cursor/evidence，不新建交接系统。

建链沿[TLS契约](../architecture/TLS_HANDSHAKE_CONTRACT.md)：预共享route-key不在线私有交换，业务填充不改外层标准握手。当前默认1460与Rust自动内层预算不变。

## 2026-11-17 用户收口范围修订：仅日常典型场景

此修订仅改变**本轮开发/测试预算**，不改变既有产品功能的安全边界、资源限额或历史证据事实。用户明确“不再搞特别极端工况测试和适配”，要求以最短路径完成普通 WinForms 保存→有效配置→Connect/正常 Disconnect→重新 Connect、默认1460/自动内层、CN IP＋域名/单DNS、真实Direct/Tunnel TCP/UDP及Normal Padding生效。已证H2055/2056/2059不同SOURCE原生结果保留；H2031密文Padding、H2041 Game4不重跑。

本轮**不再补测/扩展**极端五类同时满额、慢磁盘人为阻塞、强制杀进程/整机、长时间高负载或大规模CPU/RSS A/B、IPv6旧矩阵、同海外CDN双域名相反出口。其证据范围保持`NOT_RUN`/历史组件限定，不得标`PASS`或因未跑就误判日常使用失败。保留旧契约整体D1–D5/P1–P2尚未全部达标的事实：仅按用户新限定口径进行**日常使用范围的 scoped closeout**，不要把它提升为全场景的完结。

## 2026-11-17 H2062｜三个日常小场景独立 Action、同一已编译产品

用户明确授权把 H2061 普通 WinForms Disconnect→Connect、服务器域名在首次 DNS 接管后再 Connect、CN DNS TTL 过期与 FakeIP 正常 Stop/重启恢复 **一口气分为三个独立 Windows2025/WSL2 Action**。极端资源满、慢盘、强制崩溃、高吞吐矩阵继续 `NOT_REQUIRED_FOR_USER_NORMAL_SCOPE`；历史 `NOT_RUN` 和 FAIL 不改。

复用 H2061 Action `44007996775` 在 WSL2 环境启动之前已上传、但**尚未获得原生业务资格**的 Windows EXE/Rust DLL 与 Linux Go/Rust SO；产品 SOURCE 固定 `0e57cab2d53e2c95962eb673050fa54695fd3665`，每份归档的 `manifest source_sha`、各文件 SHA256、ABI 和当前产品路径不变证明后，才用新 fixture SOURCE 的测试代码。不同 SOURCE 绝不合并为一个新产品 SOURCE 合格。每 Action 一 VM/一网络场景，正常 Stop/owned journal/finally 清理；协调 push 只 dispatch，不再创建第 4 个原生场。

- `gui_reconnect`：原 H2061 两次 WinForms Connect 与 OS 1460/1389、两次 WAL Stop、第二代真实 Direct/Tunnel TCP/UDP。
- `domain_reconnect`：同 GUI 两代，服务器设为 `vpn.edge.cn.example`，Linux eth0 原生 UDP TC1/同 endpoint TCP53 分别收到两次查询与回答，原 TLS SNI 不变，两代 OS Applied 与第二代双出口。
- `dns_ttl_restart`：真实 WinForms/Wintun 应用对 `www.cn.example` 三次 CN DNS：首次、等待 2s TTL 过期后的再次查询、普通断开/重连后再次查询；Linux eth0 对三个唯一 DNS ID 都给出真实物理 A/CNAME、有效 FakeIP 回包。随后复用原完整 Direct 32KiB TCP/UDP、Tunnel TCP/UDP 与 owned Stop。不可将缓存单测或 GUI 标记冒充原生验收。

上述均为 `IMPLEMENTED_TEST_FIXTURE_PENDING_NATIVE`，只有 ZIP 源锁与实际应用/物理端口/Stop 回执齐全后可标 `PASS_SCOPED`；若 WSL2 启动失败仅记 `ENVIRONMENT_BLOCKED`，不是产品业务 FAIL。除首次编译 Source 的旧 Action 外不重复其仍在途的 dispatch；新 Action 只为三个不同网络场景。

## 2026-11-17 H2065｜正常 Stop → 新 Go 进程源端口持久轮换

最新真实 H2064 同 SOURCE 三 Action 已通过首次 Windows GUI/OS1460/1389、物理双 DNS／CN FakeIP TTL2 过期、owned Stop；但第二次 WinForms 正常 Connect 确实创建了新 Go 进程，其 FakeTCP TLS SYN 沿用物理源端口41031、没有 SYNACK。旧 `m0WindowsOriginalColdClientPort` 只按**进程内** generation 递增，因此正常 GUI 子进程重启重复旧 4tuple，不能靠重跑 Runner 或改测试标 PASS。

本轮新增轻量客户端 Go **冷代际 port ordinal 的非敏感 portable 文件**：每次真正进入 TCP cold TLS 前持久更新，下一 Connect 选不同 TCP 4tuple，目录与现有 owned state 同一便携程序数据目录；该文件是下一次启动必需的非secret配置状态，不是 WFP/OS 活租约，正常 Stop 清理仍只恢复本项目 live OS 资源。缺损记录 fail-closed，不重用旧端口。Game/FEC/标准 TLS/认证/wire 不变。纯单元/旧 SOURCE PASS 不升级新产品：新增 SHA 真 Windows 双代和第二 DNS/TTL 三独立场验收 PASS 才能结束日常用户范围。
