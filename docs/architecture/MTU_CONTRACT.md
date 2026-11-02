# V4 MTU契约｜唯一口径

规范版本1，2026-11-02。**这是PLAN027A待落实的目标契约，不是当前全模式已实现/已验声明。**实施/差异/测试入口：[PLAN027A](../decisions/M0-PLAN027A-MTU-UNIFICATION-20261102.md)，资格仍查 `path-mtu-budget` 功能卡与精确SOURCE证据。后续028会话配置、029填充、030界面必须消费本契约，不再各自创造扣减表。新wire变化须同提交修改规范、唯一实现、实际编码长度用例及配置读回；不为新agent复制多份公式。

## 1. 单位和范围

| 名称 | 精确定义 |
|---|---|
| configured_outer_ip_mtu | 用户允许的完整外层IP包上限，默认1500；不含以太网头 |
| effective_outer_ip_ceiling | 本方向/lane已知限制的最小值：用户、物理出口IP MTU、有效路由PMTU、发送实现；**接口1500不证明互联网整条路径1500** |
| peer_advertised_mss | 对端SYN中的原始MSS值，TCP数据容量基于最小IP/TCP头；不是IP MTU，也不等于TUN MTU |
| record_wire_cap | 完整加密record，含外5B、受保护PN、kind/marker、tag；不能把TLS length字段的body长度当wire长度 |
| record_payload_cap | 扣掉record固定成本后的明文载荷容量，不再重复扣31 |
| single_inner_ip_cap | 当前模式不需LINK拆包时能承载的**完整内层IP包**，包含内层IP/TCP/UDP头 |
| effective_tun_mtu | 操作系统接口出站IP MTU；requested、planned、实际OS读回分开。它不自动限制所有接收包，更不是外层raw发送MTU |
| rx_wire_cap / rx_reassembly_cap | 已认证接收资格及实现容量；不因本地TX路径变窄而擅自收窄对端合法在途接收窗口 |

程序普通变量也需表达单位。Rust仅在关键边界使用轻量newtype/明确字段，不包装每个usize；C ABI用带单位字段和版本/struct size，避免一个`pathMTU`既指Wintun又指物理网卡。方向、lane、generation、budget revision属于快照身份。

本轮统一正式公开的外层IPv4配置上限为1500；不是所有576..1500都可用：还必须满足推导后的内层容量≥当前产品最小576及实际平台要求。576是现有产品政策，**不是IPv4所有链路必须≥576的协议定理**。IPv6最小1280不应被套在IPv4-only TUN上；现有IPv6阻断不变。jumbo/9000只保留明确实验能力，未逐端/逐模式真实通过不得从CLI数字合法推断支持，更不能静默截到2048。

## 2. 唯一计算，MSS选项不能漏

对每个发送方向、每条lane分别计算（全为字节）：

```text
P = min(configured_outer_ip_mtu, physical_link_ip_mtu,
        known_route_pmtu_if_any, implementation_outer_ip_cap)
O = (actual_ipv4_header_bytes - 20) + (actual_tcp_header_bytes - 20)
M = peer_advertised_mss - O
W = min(P - actual_ipv4_header_bytes - actual_tcp_header_bytes,
        M, agreed_record_wire_cap, implementation_record_wire_cap)
record_payload_cap = W - 31
single_inner_ip_cap = record_payload_cap - mode_reservation
```

使用checked算术、真实合法头长与已有MSS缺失规则（当前IPv4 raw默认536）；缺失不擅自当1460。若handoff输入已是扣选项后的容量，要命名成adjusted capacity，不能再扣O。SYN本身选项不自动成为每个DATA的选项；ACK-only的SACK长度按自身包计算，不能把最大ACK选项40B永久预留给所有DATA。

`agreed_record_wire_cap`沿真实TLS认证协商结果：当前双方最小值契约若已存在就遵守，不自行改成未经协商的更大值。配置0/缺省只在冷层表示auto，derive先解析为实际上限；认证后不能拿0当合法cap或“无限制”。TX方向使用对端接收MSS与实际本地发送路径；不能拿C2S路由MTU冒充S2C。完整record和平台buffer容量均需扣其真实前置空间/封装，不能只看到2048数组便宣称2048 record可发送。

RFC6691明确MSS与实际选项的关系：[官方依据](https://www.rfc-editor.org/rfc/rfc6691.html)。例如peer MSS1200、DATA TCP头32、IPv4头20，即使本地P1500，record最多1188，不是1200；Normal内层上限1157。这比仅验证MSS1460+options的用例更能抓漏算。

### 实际V4层次和模式预留

```text
Normal     : IPv4 / TCP / record(inner IP)
FEC2       : IPv4 / TCP / record(FEC source 或 repair)
Game       : IPv4 / TCP / record(Game16 / inner IP)
Game+FEC2  : IPv4 / TCP / record(Game16 / type1 / FEC source 或 repair)
Normal LINK: IPv4 / TCP / record(LINK20 / 内层IP的一段)
```

| 模式 | mode_reservation | source相对完整内层IP的总成本* | 最坏repair相对最大源IP的总成本* |
|---|---:|---:|---:|
| Normal off | 0 | 71 | 不适用 |
| Normal Fixed/Auto FEC2 | 14 | 81 | 85 |
| Game2/4 off | 16 | 87/副本 | 不适用 |
| Game2/4 FEC2 | **31=16+1+14** | 98/副本 | 102/副本 |

*假定外层20+20、record31、零padding。FEC source头10，repair头12且编码符号包含原长2；修复符号是否按size class补齐，以真实编码器输出为准，只有实际承载/发送补齐字节才算wire。14是满足最大修复包的预留，不是每个source都带14。lane副本/FEC/外层重传是额外实际流量，不能再作为固定头扣一次。

Game+FEC不能沿旧模型只扣16+14；当前实际GameFecTx还有type1，原1399预期应为1398。旧V1 56B预算仅限明确的legacy schema/历史测试，不可被V4固定/自动选中；不要求删历史codec，要求V4入口不能误选。

### 无其他上限、20+20头的基准向量

| outer IP MTU | Normal | Normal FEC2/Auto | Game off | Game FEC2 |
|---|---:|---:|---:|---:|
| 1500 | 1429 | 1415 | 1413 | **1398** |
| 1492 | 1421 | 1407 | 1405 | 1390 |
| 1400 | 1329 | 1315 | 1313 | **1298** |
| 1280 | 1209 | 1195 | 1193 | **1178** |

均为完整内层IPv4包；内层IPv4 UDP应用长度再扣实际IHL和UDP8（IHL20时减28），TCP减实际IP/TCP头。不要把应用发送64KiB的TCP write当一个64KiB IP包。相同AEAD tag长度的三种现有加密套件基础成本均31；其CPU不同不影响上述尺寸。

PPPoE若OS出口已报告1492，就用1492，不能再减8；以太网/VLAN属于L2。IP MTU、捕获帧长、真实物理线速（FCS/preamble/IFG若计）分别报告，不能用pcap缺失的L2字节声称已实测。

## 3. 单一实现和生效快照

在现有Rust `path_budget`归口V4纯计算API，Go冷层通过无IO副作用的预算C ABI调用同一实现，pre-TLS也可调用；两端启动已需匹配Rust库，不再长期维护Go第二套公式。初始MSS/offer与认证后effective为不同阶段输入，同一权威计算。若确有冷加载限制，只允许同份声明生成的冷适配并共享字节向量，记录消除双实现的具体边界，不能回到手写加减常量。

快照输出P/每项上限及限制原因、MSS raw/adjusted、W、模式和层次、source/repair原包上限、padding余量计算基数、LINK能力/片容量、内层planned MTU；OS applied是安装回执，不混进纯数学输入反向推外层。适用LINK chunk为`record_payload_cap-20`，**仅当前完整支持的Normal/off路径有效**；其他模式输出NONE，不因可以算一个数就声称具备分片重组。

先准备设备/认证协商→derive→安装OS及Rust同revision→读回→放行真实TUN业务。健康热路径只读不可变快照、现有长度比较；不逐包FFI、查网卡/路由、拼JSON或遍历lane集合。codec仍验证传入载荷/输出长度，但不能对已是source cap的输入再扣14/31。平台发送器检查最终IP总长≤P、record≤W；防越界用错误结果，不能用户一个超限包就panic/Stop全部会话。

Windows1400 cap去向必须明确：用户显式record上限继续保留；历史默认魔数若没有独立实现限制，经实际1460 record全链验证后去掉，自动取预算。不能静默调大并跨越真实arena/驱动容量。旧Windows `--mtu`已标作外层ConnectionMTU，Linux `--outer-mtu`保持同语义；TUN字段是derive结果或明确高级override，不能把旧键默默改单位。帮助/配置/UI/启动readback同步。

## 4. lane、Auto、路径变化

- Game共同源/FEC编码使用**本方向参与承载新业务的活动lane**最小容量；不取所有历史/retiring/待建lane的全局最小值，不把小client的MTU传播到其他client。lane各自加密仍独立。
- 新lane更小：先完成认证和预算检查，不能不适配便加入复制集合。能安全收窄逻辑/TUN预算才原子加入；否则暂不接纳该lane或按已有生命周期重建该组，健康旧lane继续工作。不得为这一项造新跨lane路由/逐大小择lane调度器。
- Auto为可能启用FEC预留14，降到off不反复升TUN；Game固定档切换FEC on/off属于新effective配置，不伪装纯r值变化。FEC size-class/最大符号不能把repair撑过W。
- TX路径收窄：通知已有冷控制安装新revision，停止发送不再适配的旧大record，尺寸仍合法的小业务/健康lane尽量继续。原PN/密文不能裁剪、重新加密或跨新lane重用；机会式repair太大直接退休。尚未发出的旧大parity/分片计划有界取消，按现有FEC/LINK到期处理，不拖住所有新包。
- 若现有owner不能安全在线更新，就沿成熟generation重建，保留账号/IP/业务入口及owned清理；不能称这种行为无缝，也不能自动把MTU问题当认证失败。路径恢复更大只在下次建链/明确重配再提升，无需主动探测或每秒振荡调TUN。
- 本轮不新增复杂主动PMTUD/探测包。读取现有路由、发送EMSGSIZE/有效PMTU事件；没有可确认的中间路径MTU就标未知，保留用户降低outer MTU入口。无ICMP的公网MTU黑洞仍是单独物理资格，不能用本地网卡读回冒充已解决。

未来028共用server TUN时仍按每session预算/有限每client路由MTU或既有出站适配，不在每client登录时改全局TUN。这里的预算API必须可复用，不能在027A提前开发多租户框架。

## 5. 超MTU大包：优先让IP层正常工作

**默认：TUN MTU≤已保证的单record业务容量；普通TCP由OS分段，大UDP由IP语义处理。不是“所有大包丢弃”，也不承诺高损时大UDP必达。**

| 输入/情形 | 决策 |
|---|---|
| 合法内层IP≤effective_tun_mtu且≤本方向单record上限 | 原快速路径，不能因预扣LINK20降低所有包利用率 |
| TCP应用一次写大量字节 | 让真实TCP栈按MTU/MSS分段；只在现有转发/路由确有必要处复用MSS clamp，SYN/SYN-ACK只降不升。无逐包用户态TCP重分段 |
| IPv4 DF=1且超过本隧道对IP层承诺的MTU | 本地OS返回EMSGSIZE/已有内核ICMP即有效；若包已进用户态，返回正确ICMPv4 Type3 Code4与可用内层下一跳MTU，丢本包，不静默黑洞、不杀lane |
| IPv4 DF=0大UDP/其他IPv4 | 优先由发送端/转发内核在进入TUN前正常IPv4分片，所有模式把每个IP片作为普通业务包。对真实入口仍出现的合法超限包，共享**有界IPv4分片慢路径**（优先成熟旧helper/库）；接收端OS重组，不为此新增每模式LINK协议 |
| 明确已支持的Normal/off LINK兼容通路，逻辑包在其宣告的虚拟MTU/兼容上限内但超过单record | 沿已认证能力进行LINK拆包/重组，保留已验的1728B/跨32片/接近65KiB兼容；DF不禁止隧道内部封装拆分。Windows未接完整LINK不能接受该能力声明 |
| 未支持LINK的Windows/FEC/Game通路 | 不发送接收端不识别的LINK格式，更不能偷偷降为Normal/off；靠正确TUN MTU、IP分片或DF的PMTU反馈处理 |
| 畸形IP/声明长度不符/超65535/无法承载的offload对象 | 明确计数并丢本包，不截断成合法小包、不把局部错误升级成全owner退出 |

IPv4分片慢路径只处理确有需要的包：正确IHL/options复制规则、8B片偏移对齐、原ID/已有offset/MF、各片IP长度/校验和；UDP/TCP端到端校验和不重算成每片校验和，不先重组已分片输入。缺端口的后续IP片不能被当新TCP连接、误直连或误启动029 padding；沿既有IP分流结果。不要把原大包再写回同一个TUN碰运气造成循环。内核已经分片时不再拆一次。

复用原有有界慢路径/队列，必要大包缓冲按需一份、读入后及时释放Wintun ring，分片批次上限沿已有32/轮且新小业务先处理；不为所有packet扩大slab到64KiB、不新增后台线程/全局重组表。内存/槽不足丢该datagram有计数，不能无限等。TUN读取能识别完整实际长度：不能2048缓冲截掉大包尾部后把它当合法完整IPv4。

ICMP走正确反向路由并带原IP头及必要引用，复用成熟实现；不对ICMP错误再产生错误、不对非首片/广播多播伪造反馈。用已有有界控制额度防正常大包突发占满控制路径；若无额度，简单token计数即可（建议20/s、burst20，作为控制上限而非恢复时延保证），无逐流定时器。不得重放全套逐包M2回报。

IPv6当前按原政策阻断；未来启用需另遵守ICMPv6 Packet Too Big、最小1280等约束，不照搬IPv4中间路由分片。

标准依据：[RFC1191](https://www.rfc-editor.org/rfc/rfc1191.html)、[RFC1812 §4.3.2/§4.3.3.1/§4.2.2.7](https://www.rfc-editor.org/rfc/rfc1812.html)、[RFC8200](https://www.rfc-editor.org/rfc/rfc8200.html)。内层IP fragmentation和LINK fragmentation是两层不同机制，不合并成一个“支持大包”开关。

## 6. 控制、重传、填充与计量

所有实际发送包都受最终长度约束，包括真实冷TLS/FakeTCP分段、ACK/SACK、Health/Quality/退休、parity、Game副本、repair。冷TLS可以按成熟TCP字节流跨多个segment；稳态独立record默认一包一record，不能为撑大record偷偷依赖TCP流重组/HOL。

padding只用当前实际record剩余空间，满业务包可为0；控制TLV聚合先去padding，再减少可拆分的报告/页，不能截断不可拆字段或饿死Health。不因附件列出Receipt/8页大小就复活已经退役的线上M2。编码器有格式不等于当前运行发送该格式。

F/R/C/副本与业务字节分账按**成功实际发出**的IP总长计数；L2另列。数学开销不是线速实测。批次/低频readback给mode、方向/lane、generation/revision、配置/接口/路由来源、MSS、record、TUN planned/applied、最大wire/拒绝原因；大pcap不落盘，使用有界头部摘要/长度直方图即可。

## 7. 大包测试如何解释

一个datagram拆n片，每片最终未恢复概率q且独立时，完整交付约 `(1-q)^n`；一般相关损伤不能套独立式，可用联合上界 `P(缺失)≤min(1,Σq_i)`作宽参考。q必须是**该模式经过FEC/Game后的残余片损失**，不是直接把30%线路loss当q。另报完整datagram丢失、片损失、到达时延与重组到期，不能只看已到包p99。

无损容量内、明确支持范围应完整通过；高损只要求表现可解释、迟到/丢片有界退役、不妨碍并行小UDP/其他TCP和Stop，不以大UDP零丢或统一1s恢复硬门误判。TCP同一流本来有序，项目要求的是隧道不把一个流缺片扩散为其他流HOL。
