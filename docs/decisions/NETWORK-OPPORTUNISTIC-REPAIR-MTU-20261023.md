# 机会式外层重传、统一 MTU 与真实性能验收 v3

状态：用户已授权的开发方案，**IMPLEMENTATION_PENDING / ACTIONS_NOT_RUN**。本次仅修改方案、入口和交接，不把文档提交当产品修复。适用分支 `experiment/network-matrix-tuning`；实际进度仍只在该分支 `docs/evidence/network-matrix-work/status.json`。本文件覆盖旧一次快速恢复 v2 的性能目标、保留比例、DATA RACK/PTO 和低损残余门；认证、完整性、generation、固定密文、MTU、Stop、真实计账不变。

## 1. 已确定的目标及优先级

- 外层重传只提供有限的 TCP-like 行为，不再承担“低于 5% 丢包尽量全部恢复”的业务 SLA；不要求完全符合 TCP。恢复碰巧补回业务仍正常首次交付，不能主动丢掉来维持某个丢包率。
- 首发、新业务低延迟、无跨业务 HOL、低 CPU 优先；最多一次原密文重传，稀疏业务仍豁免百分比限制。重传缓存满不能阻塞 TUN/raw 的首发通路。
- 持续充分负载、30% IID、反馈和宿主健康时，重传要有实际数量：标准高损用例要求 `R/C >= 6%`，同时 `R/F <= 10%`；目标额度为 `R/F ~= 9%`。达不到下限要定位候选/反馈/额度/调度，不能静默宣布通过。无真实缺口或资源不足时不得编造丢包/重复已确认包凑数；容量受限单列，不能用外观下限拖死首发。
- 0% 损伤、无注入乱序且容量健康时重传应接近 0；不再以“时间到了但没有 ACK”作为持续 DATA 重传理由。bootstrap、keepalive、认证和黑洞恢复独立保留，不一并删除。
- UDP/FEC off 的丢包不能明显超过实际首发线路丢包；**没有最低业务丢包率**，恢复后低于线路丢包当然有效。FEC/多 lane 的实际恢复继续按它们自身模型判定。
- 新增独立目标：**单条内层 TCP 应用流 500Mbps、单程 200ms、0% 人工丢包**。这是应用速率目标，不是此前 500Mbps 外层线路/2% 丢包目标；两个用例同时保留。单流资格不能用 8 流总和替代。
- Linux/Windows、ARM64/x86_64 使用同一策略与预算语义；当前岗位先测已接线的原生路径，不等待其他平台，也不把交叉编译当实机性能。FEC 专项仍由 `experiment/fec-network-tuning` 在外层 DATA repair off 下推进，本任务不重复其开发。

## 2. 分母、数学约束与新默认

每个方向统计 `F`=实际成功首发的外层 DATA IP 字节（含 FEC 首发/该方向 Game 副本），`R`=重传 IP 字节，`K`=其他控制 IP 字节，`C`=配置外层线路容量折算到同一时间窗的字节。重传 Accepted/Uncertain 在预算中保守收费，线上实际发出另列；未知不能当成功也不能反复退款。报告 `R/F`、`R/(F+R+K)`、`R/C` 三项。稀疏例外另计，不混入持续流量百分比验收。

若无控制流量，`R/F<=0.1` 对应总 DATA 的最多 9.09%；要达到 `R/C>=0.06`，必需 `F/C>=0.6`。低负载/反馈黑洞不可能同时无条件保证两项，不能发空业务补分母。标准 30% 用例按 `F/C=0.8/1.1=0.72727` 起跑：目标 `R/F=0.09` 对应 `R/C=6.545%`、合计占线约79.27%，保留控制和调度余量。

之前提出的 1/8 抽样在30%独立丢包下只有 `R/F≈0.0375`，不满足新要求，撤销。采用便宜的**固定约 1/2 候选选择**，目标额度9%、硬上限10%，不加按丢包率调抽样的控制器、不加实时 CPU 控制器。对混合长度必须核对候选字节覆盖；抽样键须均匀混合PN和连接种子，不能直接取PN奇偶导致周期性小/大包偏置，不逐包生成随机数。

| 参数 | v3 工程初值/边界 | 解释 |
|---|---:|---|
| 持续 DATA 候选比例 | 约1/2，压力可跳过 | 30%损失有15%首发字节的候选缺口；反馈一次成功率70%的简化估计仍有10.5%，足以争取9%目标；不是反馈覆盖的证明 |
| 全进程候选准入 | 32,768项/s，短突发最多一个32项批次 | 所有客户端/lane共享；覆盖500M近MTU包的一半，纯小包另判PPS容量 |
| 全进程重传发送 | 8,192包/s，另受字节预算 | 替代之前1,024/s，后者不足覆盖500M大包10%修复；不是固定CPU核数保证 |
| 字节目标/上限 | 每首发字节积累9%可用修复信用；独立核10%硬帽 | 默认不追满额度；整数余数累计，批量更新；token不跨空闲无限累积 |
| 短突发 | 至多8个有效外层MTU | 字节/PPS限制联合，滑窗允许已声明burst，不用毫秒比例误判 |
| 发送候选队列年龄 | <=20ms，且不越原绝对保留期限 | 到期放弃；不等待缓存、额度或socket长排队 |
| 维护批次 | <=32项，批次时钟、非逐包CPU采样 | 空闲没有DATA重传轮询；有剩余工作正常让出调度后续跑 |
| repair池总槽上限 | 全进程65,536，共享而非每client各一份 | `ceil(32768*1.5*1.25)=61440`向上取2次幂；仅选中包占槽 |
| repair池payload上限 | 128MiB初值，计入原endpoint总512MiB | 65,536×2KiB；实际slab/元数据/I/O引用需实算，不能假装所有buffer均2KiB |

固定槽上限不等于启动全分配：按需分配块、空块复用、低频回收；元数据也不能每周期全量触碰。修复引用不能耗尽首发Arena；先核实际共用池，设置首发可用余量或独立有界repair保留额度，压力下放弃可选引用。共享额度用既有批量grant，不逐包争全局锁。6%下限只用于声明的高损代表工况，不能挪作所有负载的产品最小发包率。

等长、无控制/反馈缺失的示意，F是外层首发，不是应用业务：

| F | p | 首发PPS（1400B） | 选择候选/s | 预算后预计repair/s | R带宽 | 一次机会理想残余 |
|---:|---:|---:|---:|---:|---:|---:|
| 500Mbps | 0% | 44,643 | 22,321 | 0 | 0 | 0 |
| 500Mbps | 2% | 44,643 | 22,321 | 446 | 5Mbps | 1.02% |
| 50Mbps | 30% | 4,464 | 2,232 | 402（9%额度） | 4.5Mbps | 23.7% |
| C=50Mbps、标准F=36.364Mbps | 30% | 3,247 | 1,623 | 292（9%额度） | 3.273Mbps，C的6.545% | 23.7% |

示意公式：有效修复包占首发包数为b时，`q=p-b*(1-p)`，`b<=min(s*p,0.09)`；混合长度时字节比例不能直接代入包数。它不再是低损恢复验收下限/上限；真实反馈覆盖、重排、期限和丢包相关性会改变b。低损2%不再要求0.25%残余；也不得限制业务必须高于1.02%。

### 2.1 非payload状态与PPS，不能漏算

shadow抽样不缩小真实PN空间。receipt/去重/质量统计覆盖所有实际首发和控制PN，重传仍复用PN。按实际每lane PN/s推导：receipt历史至少 `ceil(1.25*PNps*2s/256)+1` 页；3s接收去重至少 `nextpow2(1.25*PNps*3s)` 位及必要页标签。每报告8页是输出批次，不是整个历史仅8页；不能为覆盖大窗口每10ms扫描所有页。

500M TCP单向数据约45,389包/s；双向各500M还会在每向叠加对端内层ACK（延迟ACK每两包一次仅是例子）及控制。若每向约70k PN/s，初值1024个retained receipt页、524,288位去重窗口可覆盖上述时域；质量成熟元数据同样核容量。真实ACK策略和控制率必须readback后重算，不能从示例强制每两包一个ACK。共享字节界、按需页分配和有界dirty处理保留。

旧M1 2048槽只是10M源TUN-drop修复，不是500M资格。选中密文在600ms RTT仍可能同时存上万份，必须核当前Arena/ABI真实硬帽与fresh可用空间。优先有界按需块池+分别计repair引用和fresh预留，避免每包复制两份；不能只把逻辑shadow写成65k、底层仍8192全被保留引用钉住。fresh调度队列按几毫秒服务间隙和实际PPS算，不按400/600ms网络BDP堆待发送包。

netem延迟存储则需要线路BDP：`limit >= ceil(1.25*(fresh_pps+repair_pps+control_pps)*one_way_seconds)`，另看实际skb内存。它和产品队列、TCP流控窗口是三种不同资源；不调足模拟队列造成的随机外额drop不能算产品弱网能力。所有上限及定时维护均计真实布局/共享进程，不做每方向各领一次总预算。

## 3. 发送、反馈、清理的实现顺序

1. 保留批量raw发送、实际definite-copied前缀记账；批次汇总F一次更新credit。`GlobalRepairAllocator::on_fresh_accepted`当前逐记录进入advance、遍历account/pending，应拆成批量首发记账与一次有界维护。注意现有全局mutex本来按批次取得，不能虚构“每包锁一次”来量化收益。
2. 在建立repair索引/引用/定时状态之前做抽样和准入。没有选中的包不建repair条目，但仍纳入真实质量/RTT/已发分母。保留原密文，禁止重新seal或复制整record；缺空间放弃候选，首发继续。
3. **停用持续DATA的RACK快速修复、每包PTO/尾包猜测及其专用唤醒索引。** 用已认证、同lane/generation的收据实际覆盖位图找到“有后到见证的缺口”，没有收到收据不是收到negative。保留质量统计和冷层控制的RTT，不需要重新实现一套可靠协议或逐包CPU监控。
4. 缺口先等一个廉价防乱序宽限；之后按最新缓存收据复核，positive优先撤销。初值 `G=clamp(max(20ms,4*RTTVAR),20ms,100ms)`；候选进入发送的最早时间为 `max(sent+SRTT+G+20ms, first_authenticated_negative+G)`。20ms含现有反馈10ms与批次余量，不由netem真值驱动。单条新negative足够启动等待，不强制“两次报告齐全”；旧/重复negative不延长期限。
5. 等待只涉及选中的missing元数据，用现有有界索引/批次due处理；每批处理32项，不逐ACK扫描所有密文，不对每个PN重算RACK。最新positive更新与定时触发竞态必须复核。未知/未覆盖/过期反馈不修；末尾单包没有后到见证允许不修，不为尾包补新固定周期DATA探针。稀疏免比例仍最多一次，不保证稀疏尾包恢复。
6. 新的DATA保留初值 `H=min(1500ms,max(250ms,1.5*SRTT+4*RTTVAR+100ms))`，在接纳时冻结绝对deadline；R=400,V=5→720ms，R=600,V=5→1020ms，bootstrap R=600,V=50→1200ms。最高单程300ms。晚更新RTT不无限续命；若成熟检查已经晚于deadline就放弃，不能发早或偷偷扩大寿命。
7. 一次reserve/发送机会结束即退役repair资格。Accepted/Uncertain不再等重传ACK，明确未提交失败也可直接终止；不恢复多次机会。驱动持有buffer时等安全completion/取消后才回收。receipt/去重/质量小元数据与payload寿命分离，ACK释放、重复completion、晚回执/槽复用、Stop按原硬门验证。
8. 接收首次到达立即交付；不等外层缺口，不新增可靠SKIP握手。释放本地payload不等于确认业务已收。FEC systematic、Game副本去重及大包重组仍各自有界，新普通包不进入旧缺口等待。

现有 `ReceiptState` 的timer处理已经有界，并非所有路径都全表扫描；不要为此次任务先重写万能时间轮。可以保留其有用的expiry结构，删除只服务旧RACK/PTO的部分。若BTree索引在更大候选量下成为实测热点，再用PN页位图/选中槽索引做最小替换。目标是少处理，不是同时加入三套控制器。

0%且无host drop的旧样本b179fd0e仍有387次outer repair，必须作为新反例保存。新策略在0%/无乱序代表长样本要求R/F<=0.05%（目标0），不能通过屏蔽duplicate统计刷绿；0%加真实乱序的独立诊断允许<=0.2%，超出定位feedback/宽限原因。这两个是工程允许带，非TCP数学定理，不能为守门重新增加全量扫描。黑洞不靠DATA PTO刷repair数，继续验原连接恢复。

## 4. MTU一次统一：不再保留无来源的100/1280限制

源码核查（基线a470dd08及其pinned旧Go）：

- 旧 `internal/faketcp/packet.go` 的DefaultMSS=1360，SYN/SYNACK builder使用它；1500-IPv4(20)-TCP(20)=1460，差的100B是**旧MSS上限**，不是实际还存在100B包头。当前Go初始TUN预算使用这个默认，后续只收紧，因此仅改Rust公式无法取回它。
- `r0/go_overlay/internal/v4productcli/linux.go::publicRecordWireLimit`仍有off1180、fixed/auto1280旧helper；逐调用确认在用还是死代码。在用改自动推导，不在用移除/明确历史测试，不能搜索替换所有1280。配置外层1280是合法输入；IPv6最小链路MTU1280是另一件事，当前IPv4 TUN禁止IPv6的策略保留。
- `crates/wbd-codec/src/path_budget.rs::FecReservation`仍引用旧FEC_HEADER=56和旧档位，产品FEC2又另算source10/repair14。统一成明确FEC2预算入口，不能因为helper单测PASS就宣称所有实际路径一致。旧wire可保留显式隔离测试，不作新产品默认。

统一冷路径预算快照，启动/认证/路径改变时计算，热路径仅做边界比较：

`M=min(config_outer,local_interface,known_route_PMTU[,other_validated_path_ceiling])`

`W=min(M-actual_outer_IP_header-actual_outer_TCP_header,peer_effective_MSS,local_record_cap,peer_record_cap,implementation_wire_cap)`

`TUN_single=W-record31-fec_reservation-game16_if_enabled`

这里peer_effective_MSS是实际可发送TCP载荷上限：对端通告按基础头计算，实际额外IP/TCP options依协议语义从可用载荷扣除，不把通告值再无条件减40；同时受本端实际IP包预算限制。

FEC2 off预留0；Fixed和Auto按最坏repair开销14（source10+编码长度差4）预留，auto切档不重设TUN；Game只扣16一次；LINK20仅分片/escape实际使用时扣，普通包不统一扣。cipher/padding有实际额外字段则从序列化器常量取值；startup padding只用剩余空间。应用UDP上限=TUN-实际内层IP头-8；TCP SYN MSS通常按基础IP/TCP头通告，含TCP options的实际segment payload还需减options，不能重复扣或把IP MTU当应用payload。

通过V4冷层配置将**本端通告MSS**绑定自己的实际接收路径预算，不再固定1360；本端record offer从实际接收能力计算，不再先用1360永久钳住。随后仍遵守真实peer MSS和双端认证record cap，不能把对端明确1360擅改1460；没有advertised MSS时保留协议fallback。动态MSS需穿透client/server SYN构造及Go/Rust handoff；旧Go仅Actions overlay，不能改公共旧仓库。握手路径改动是配置接线，不重写TLS建连。

无options、双方能力充足的预期（单位B）：

| outer | record wire W | Normal/off TUN | Fixed/Auto TUN | Game/off TUN | Game+FEC2 TUN |
|---:|---:|---:|---:|---:|---:|
| 1500 | 1460 | 1429 | 1415 | 1413 | 1399 |
| 1400 | 1360 | 1329 | 1315 | 1313 | 1299 |
| 1280 | 1240 | 1209 | 1195 | 1193 | 1179 |
| 1500，真实peer MSS1360 | 1360 | 1329 | 1315 | 1313 | 1299 |
| 1500，真实peer record1280 | 1280 | 1249 | 1235 | 1233 | 1219 |

两向预算分别计算；共享TUN取实际活动路径所需安全包络，不能用一客户端低MTU改坏其他客户端，不能因单lane升/降MTU重seal已冻结密文。Game新lane更窄时保持旧包预算快照，已有兼容分片/有计数终止保留，新包立即用新预算。产品不支持的极小budget或jumbo须提前明确拒绝，不能截断、溢出或悄悄按1280成功。

记录 `mtu_budget_version`、config/interface/route、advertised+peer MSS、local/peer record cap、每层开销、TUN实际readback、限制因素及每向最大实际IP长度。这是统一函数结果，不是各模块复制一套减法。Linux原生和Windows共享语义都要改到实际入口；平台未测记NOT_RUN，不能由ARM的9个ping反推全部完成。

MTU验收：同包构建复用；1500/1400/1280、peer1360/record1280/非对称路径、off/fixed/auto/Game代表边界；每层budget-1/= /+1；UDP真实边界/2×MTU/最大合法datagram、TCP长write按MSS实际分段；DF/EMSGSIZE/ICMP、magic escape、片乱序/缺片、padding、MTU变化/rotation。超MTU多片在高损下按片数建模，不要求同普通包残余；所有外层IP长度不得越预算，大包不拖住其他流。FEC开启时parity最大长度也要实测，不能只测systematic。

## 5. 验收：UDP、TCP、混跑分别定义

### 5.1 UDP和线路损失的正确关系

常规off、一个UDP业务包恰好一个外层DATA、无复制/分片时：优先用首发DATA标识对应的实际擦除率p_data，不能把包含ACK/repair的qdisc总drop率当它。缺精确分类时可用已校准IID损伤概率及置信带，但报告MODEL_BASED，不能宣称逐包实测。

健康容量、充分样本的工程允许带：`q_app <= p_data + max(0.002,3*sqrt(p_data*(1-p_data)/N))`，0.002是0.2个百分点；**无下限**。实际本地oversize/owner/TUN/driver drop仍必须定位，不能藏进允许带。0%无乱序正向用例目标业务missing=0、产品drop=0；偶发外部测量故障独立归因，不用0.2个百分点掩盖0损bug。IID区间不用于相关burst，后者用同一损伤trace/时间块。

报告注入/首发/首到/唯一修复补回/重复/未到/迟到；分包数与字节、按大小分桶；保留drain结算。q变低不FAIL，q过高查最早drop边界。FEC/Game按实际k/r、联合副本和损伤相关性验收，不与此off上界混用。分片UDP用 `1-(1-p)^m` 等对应模型，禁止把30%线路直接当m片报文的残余门。

### 5.2 单TCP 500M/200ms/0损

应用每方向目标500Mbps，RTT400ms：`BDP=500e6*0.4/8=25,000,000B=23.84MiB`。测试socket可用窗口至少约1.5BDP=37.5MB，初始64MiB上限；需要时只在owned namespace/测试socket提升到足够值，读回真实SO_SNDBUF/SO_RCVBUF、window scale、advertised window、cwnd，不能认为设置值即实际可用窗口，也不修改系统全局生产默认。

outer1500/off TUN1429，内层IPv4/TCP基础40B、timestamps12B示例，实际TCP payload1377B；500Mbps应用首发仅DATA约544.66Mbps外层，ACK/控制另计。TCP500用例配置每方向至少700Mbps外层能力（或可验证更高），不能复用500Mbps线路限速，也不能把80%起跑公式变成该用例的业务目标。双向同时500是额外容量要求，分别声明；先测一个方向单流+反向ACK，再在容量允许时反向/双向混跑。

用同runner直连TCP同RTT/同窗口/同MTU或明确差异进行环境校准；若直连也到不了目标，报告环境限制，不宣称产品500M PASS。产品源已注入足量但单核/队列受限则属于产品容量问题。预热10–20s或观测cwnd稳定，正式60–120s；目标500Mbps，工程通过带>=目标95%且实际注入满足声明、无产品drop/持续停顿，目标带必须标在报告，不把475写成精确500。如不能满目标保留实测上限和原因，禁止多流替代单流。

FEC off、有损TCP不再要求原低损满速，内层TCP固有拥塞/重传如实报告；但0损500M不因此撤销。丢包TCP的同流有序等待不是隧道跨业务HOL，不能混淆。

### 5.3 TCP+UDP混跑、延迟和生命周期

代表混跑：大包TCP占约70%注入字节、近MTU UDP约29%、独立小UDP/短TCP事务约1%，并记录真实包数（该分配是字节份额，不是小包仅1% PPS）。不添加本次未授权的小包专用优先调度器；先保证已有有界批次、方向公平、读写解耦。测0损和一个高损/突发波形，容量先算总包率与封装。

看每个业务/方向的10ms或更细交付桶、最长空洞、首发队列年龄、锁/worker间隙、未损新包p99及deadline内交付比例。故意损坏一条内层TCP/丢一个外层包时，其他UDP/独立TCP仍推进；确定性功能用例验证无缺口门控。持续网络用例中超过约100ms的多业务共同零交付作为诊断触发，结合实际输入和损伤trace归因，不能把连续线路擦除当产品HOL。p99分首次成功与修复补回，报告未到避免幸存者偏差；不强制把允许多RTT晚到的修复包也压成lossless p99。

保留代表rotation新lane建立再退旧、idle/keepalive/业务唤醒、单向/双向黑洞及恢复；不因删除DATA PTO破坏控制层恢复。Stop、generation隔离、固定密文、认证完整性、SEQ回绕、回收低→高→低继续按原硬门。不要重新铺全量生命周期笛卡尔矩阵。

## 6. 性能基准与CPU判断

冻结实现前最新有效产品SOURCE（当前可用参考b179fd0ef83814a05e41833a1f312a8792625b3b，最终以实际核验为准），不能用已证实源TUN丢包的旧A当“更省CPU”的成功基准。新/旧Go冷层、Rust、编译选项、ISA/cipher、MTU、宿主CPU、注入字节/PPS、诊断级别全部记录。

三种比较不能混为一谈：

1. **A旧产品→B新产品，同损伤同负载**：一次Action、同job/VM顺序执行，改善归因于本次提交。MTU改动会改变PPS，分别给原生最优MTU的用户收益、必要时共同MTU一次诊断，不能将PPS下降全说成重传算法CPU收益。
2. **新产品0%→新产品2%/30%，同首发负载**：一个预声明损伤波形的Action，比较损伤附加成本；同一对照顺序也可作为固定paired场景。不是同runner同时跑两个压力进程。尾部回0%可看回收/恢复，不能声称完全相同netem抽签。
3. **同SOURCE repair off→opportunistic**：仅在需要分离重传固定成本时跑一个代表点；不要求每个矩阵点三种A/B全跑。OFF保持质量观测与其他功能一致，不靠关闭整套统计获得虚假收益。

纯UDP、FEC off、等量首发时：发送封装/加密量基本不变，额外密文重传<=10%；接收在p=.3、b=.09时约 `(1-p)*(1+b)=0.763` 倍无损包数，解密量甚至可能更低。故没有理由把30%损伤自动接受为成倍CPU；但10%网络开销不等于总CPU必定只加10%，ACK处理/缺口维护/锁/系统调用仍需测。

初始工程目标：容量健康时，新版2%/30%场景两端合计产品CPU相对同源无损 **增量争取<=15%，允许带<=20%**；超过20%标PERF_REVIEW并定位，不能直接判“VM问题”或默许。低基线时同时看绝对核时间与重复性，接近噪声的百分比不硬判；若机制上有必要超过，给分项测量/替代目标再留痕，不静默改门。新版无损相对有效旧版目标不退化，>5%作为回归调查线，非一次噪声即判最终失败。

同时报告两端各user/system CPU-s、host softirq/IRQ/PSI、单核热点、注入器CPU、cycles或CPU-s/百万**首发**与实际处理record、CPU-s/GiB offered和delivered。丢更多包会使CPU/GiB delivered变差或总CPU变低，不能只选一个分母。相同seed在不同发送节奏不代表完全同一擦除trace。发现差异只补一轮有信息增益的BA/诊断，不刷seed。

## 7. 有限开发与Actions执行包

先结清status在途结果；保留b179无损10M修复，不重复证实已关闭源TUN缺陷。然后按以下完整能力收口，所有执行验证只在Actions，构建后复用精确artifact/hash：

| 工作包 | 开发和必要验证 | 性能场景（各自单独Action） |
|---|---|---|
| V3-A | 候选准入、批量信用、成熟negative一次机会、无DATA PTO、资源回收；真实readback+竞态/乱序/未知/Stop功能批次 | 0%反例同VM A/B；30%/300ms持续UDP（满足F/C起跑口径）检验6%和10%及CPU |
| V3-B | 统一MTU、动态本端MSS、Go/Rust/driver/GUI适用项、模型/夹具同一预算 | 便宜边界合批；1500最大正常包持续UDP/TCP；模式相关FEC parity与Game边界复用现有路径 |
| V3-C | 最新成品基线，审计receipt/去重/质量窗口与首发池容量，不为稀疏小包500M优化 | 既有低点校准后一个合理高点；目标TCP500/200ms/0%；原H500外层/2%；H50/30% off（FEC最高由FEC岗位另测） |
| V3-D | 联合交付，有限异常/生命周期 | 混跑0%和高损代表点、反向损伤5/0与0/5、稀疏/乱序、rotation/idle/黑洞；功能可合批，性能每Action单一预声明场景 |

CPU剖析仅失败/异常时有界打开，正式性能默认诊断off、最低计数；跨平台验证分别记录。现有host容量不足时停止更高资源点，给PPS/CPU/BDP投影和PROJECTED_NOT_TESTED，不能让重复中小点阻止交付；产品单核瓶颈需要修或如实OPEN。独立Action可以并行，同VM顺序A/B；不派新角色、不等M0、不改FEC岗位分支，不重复dispatch已有run。

工具同步是V3-A/B必做：`tools/cost_model.py`、`tools/network_harness/envelope.py/config.py/runner.py/分析器`、请求schema/例子、帮助/readback/参数目录及适用GUI。显式 `policy=outer-opportunistic-v3`、attempt_limit=1、loss_trigger=authenticated_mature_gap、data_pto=false、抽样/工作量/字节预算/MTU版本；未知policy/未观测readback不冒充生效。老请求/模型/证据继续按旧policy解释。此文档提交**不改运行请求、不dispatch、不宣布工具已支持v3**；执行agent需新增请求并验真，不能仅换标签。

完成在既有status/devlog/evidence/final-report记精确源码、产物、已测场景、通过允许带、未测高点和重要OPEN；无新信息不重跑、不为追精确6.000%或理论最优无限调参。

参考：Linux TCP窗口/自动调优语义见 [kernel ip-sysctl](https://www.kernel.org/doc/html/latest/networking/ip-sysctl.html)；MSS基础头/实际options扣减见 [RFC9293 §3.7.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.7.1)；IPv6的1280是最小链路MTU要求，见 [RFC8200 §5](https://www.rfc-editor.org/rfc/rfc8200.html#section-5)，不是本产品IPv4的最大业务MTU。
