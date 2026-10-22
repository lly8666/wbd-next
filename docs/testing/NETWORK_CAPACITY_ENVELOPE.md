# 极限容量、包长和真实生效参数闭环

2026-10-22用户要求：现在计算极限工况并优化测试，不用穷举中间档；同时修复MTU。本文补充并优先细化 NETWORK_MATRIX_20261022 的容量/参数/执行顺序，不取消完整性、认证、无HOL、Stop和配置实际生效门。它是模型和实施任务，不是500Mbps产品PASS。当前实测恢复先读 `experiment/network-matrix-tuning` 的 status；不要重复dispatch其open_requests。

## 1. 口径与可复算入口

三个边界：单lane外层每方向500Mbps / 单程200ms / IID2%；单lane50Mbps / 单程300ms / IID30%最高FEC；Game4逻辑3Mbps、50Mbps总外层预算 / 单程300ms，独立与共同损伤分开。旧500Mbps/单程150ms被200ms覆盖；不擅自把两个边界合成500Mbps/300ms并声称用户要求。30/50/100Mbps业务是常用点，先受外层容量换算限制。

**2026-10-23用户澄清优先：大流量主场景按大包为主。** 主验收使用实际TUN MTU减去IP/UDP头的包长（或预先说明的1172B保守参考），附带约1%包数的小包/探针观察首次交付和p99。TCP使用持续长写入，由内核按实际MSS分段，记录真实IP包长分布。64/256B纯小包是独立PPS诊断；不要求500Mbps纯小包，不为这个非主目标分配数百MiB缓存或启动架构重写。下表小包行用于解释资源边界，不是新增硬门。

运行 `python3 -m tools.network_harness.envelope` 生成全部边界×64/256/1172/混合包×满组/单源组的JSON。复用 `tools/cost_model.py` 的时序与残余公式；network-harness-check在Actions执行反例自检并上传模型。`--request tests/network/xxx.json` 为一个真实请求出估算；runner prepare也输出 capacity-envelope.json。**模型不改产品配置、不扩大系统缓冲、不更改测试结论。** TCP/分片未建模明确显示，不把write当IP包。

统一假设：IPv4 UDP payload包含夹具头；inner IP=payload+28；outer IPv4/TCP=40；record=31；FEC2 source=10、repair=14（含编码长度）；Game在逻辑内层加16一次。真实TCP options/L2、LINK转义/分片、control和padding另计。包长权重是包数量占比。默认先使用线路80%预算，其中再预留R/F=10%修复；剩余20%留control、封装差异和调度余量。不是把500Mbps业务塞进500Mbps线路。

`A=E[应用字节]`；按256/512/MTU类内最大符号算保守parity长度；`W=每逻辑包全部lane的source+parity首发外层字节`；`lambda=0.8*C/(8*1.1*W)`；应用速率=`8*A*lambda`。真实k/r_sent直方图替换模型k，Game首发乘lane数但逻辑source率不乘。大UDP先算IP/LINK每个fragment的PPS与整报文成功率，不能当一个大record。

| 工况（每方向） | 应用payload | 应用预算Mbps | 外层首发PPS约 | 修复槽容量参考 | shadow上界MiB：分级slab / 当前2048slab |
|---|---:|---:|---:|---:|---:|
| 500M/200ms/off | 64 | 142.78 | 278,862 | 524,288 | 126.3 / 674.4 |
| 同上 | 256 | 262.23 | 128,041 | 262,144 | 95.9 / 311.6 |
| 同上 | 1172 | 335.31 | 35,763 | 65,536 | 66.2 / 86.3 |
| 50M/300ms/16:20 | 64 | 5.90 | 25,941 | 65,536 | 16.6 / 91.2 |
| 同上 | 256 | 11.27 | 12,378 | 32,768 | 13.2 / 43.6 |
| 同上 | 1172 | 14.76 | 3,542 | 8,192 | 9.5 / 12.4 |

表中memory是假设整个修复寿命均被保留、加25%包数余量、96B/slot预算；不是健康平均占用，更不是必须实分配。真实layout、slab可否复用、扩容重叠、RX/FEC等另算；endpoint总512MiB共享，不能每方向/每client各领512。当前全2048 slab无法在512MiB内提供500M纯小包的完整寿命覆盖，需分级slab/更紧凑缓存或明确缩短可修复窗口；不能因此阻塞fresh。CPU能力仍须实测。

本次自动MTU后的主大包预算如下；是80%线路预算、10%修复预留的**初次压测目标**，不是理论峰值或固定产品限速。实际外层可用容量、CPU与统计需校准。模型同时保留1200B参考行，避免与历史结果混口径。

| 主工况 | UDP payload / TUN | 应用预算Mbps | fresh record/s | 健康flight / 最坏shadow槽 | 保留slab上界MiB/方向 | receipt历史页/方向 | netem最低估算包数 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 500M / RTT400 / off | 1301 / 1329 | 337.92 | 32,468 | 12,987 / 65,536 | 60.7 | 155 | 9,376 |
| 50M / RTT600 / max16:20 | 1287 / 1315 | 14.88 | 3,251 | 1,951 / 8,192 | 8.8 | 24 | 1,409 |

无control/重传预留的500M线上大包上限为44,643 records/s、约17,857个RTT flight；1.25×PPS×920ms仍落在65,536槽。别用健康flight当全部缓存寿命，也别用本表80%初始注入反过来压低产品能力目标。开启最高FEC时50M线路不是50M内层业务；协议冗余是容量账的组成部分。

Game4 strong纯64B、逻辑3Mbps，仅首发已约89.5Mbps（尚未加repair/control），**不能要求50Mbps线路跑满这个业务**。同容量80%预算该包型约1.52Mbps逻辑上限；256B约3.04Mbps，1172B约4.10Mbps。保留3Mbps目标时，为纯小包场景显式提高线路容量并另记请求；不悄悄减业务刷绿。mixed按模型的实际weights计算。

## 2. 参数逐项闭环（先修实际构造，不只改模块默认）

采用可信RTT R、RTTVAR V、反馈上限10ms：W=clamp(R/32,2,20ms)，PTO=R+max(4V,2W,4ms)+10ms；Tcache=min(3s,max(2PTO+50ms,2R+100ms))。V=5ms时，R400→W12.5/PTO435/T920ms；R600→W18.75/PTO647.5/T1345ms。V20ms时分别PTO490/T1030、PTO690/T1430ms；不能只按一组低抖动常数。更差抖动按公式/3s边界报告受限。所有时钟同端、Karn歧义排除；不能读netem真值调产品。

| 参数族 | 计算/余量与实施要求 | 本次审计实际缺口（main d8ba2cf2） |
|---|---|---|
| Shadow metadata与密文 | N=nextpow2(1.25*实际data record PPS*Tcache)；字节与槽同时限制、确认及时释放；低损健康占用参考PPS*RTT，坏路按寿命封顶 | 实际构造4096；共用Arena128槽；实验分支512仍只是小修。先拆fresh资源和repair保留资源，不能只扩4096 |
| 修复带宽 | 每方向R<=max(F/10,32KiB)，大流量约9.09%总数据字节；process cap覆盖所有获准方向的总repair额度，借用有界 | 实际额外64KiB/s方向cap、128KiB/s进程cap；不是高速profile。500M/2%理想p+p²=2.04%，接近满线首发需要约1.25MB/s，而64KiB/s不足 |
| 修复调度 | 8MTU burst；fresh:repair按字节10:1；候选排队<=20ms；grant金额按repair_rate*renew_interval+burst，免逐包全局锁 | max_grant32KiB/50ms等也要同账核算；不能只改最外cap、内部发放率仍封顶 |
| PTO/重排/期限 | 使用上式，更新只影响未来计划，不使原有hard deadline无限续命；PTO尾探测有界，快速重传需真实后到证据 | 实际固定80ms PTO、15ms reorder、2s expiry；应接真实估计器，不能正常600msRTT下先耗尽两次重试 |
| Receipt页 | 至少ceil(1.25*lane PN PPS*Tcache/256)+1页；8页是每报上限，不是全部历史容量。dirty gap<=2ms、顺序<=10ms，重复反馈有限 | 实际仅8 retained页/2048PN；高PPS覆盖期过短。默认重发间隔仍据8ms SRTT；要接实际RTT |
| Auto质量/成熟观测 | 观测live-data覆盖至少PPS*实际统计horizon；用聚合计数/压缩页，不额外clone全payload。过载/未知须标样本无效，不能假装线路丢包并无限升档 | MatureFirstSend仍max_live_data4096；高时延高PPS也会把质量窗口挤满，需与receipt容量共同审核 |
| Record去重 | nextpow2(1.25*PN PPS*(max(Tcache,FEC horizon)+2R))；PN包括控制、不把原PN重传再计PN；分页按需 | 原始owner仍1000PPS/8192窗口，500M近MTU约167ms即滚出；8KiB预算不是高吞吐方案 |
| Fresh队列与批量 | ceil(PPS*2ms)，最低64最高8192；另限bytes/age。2ms是容量估算，不是定时攒包；batch先32、按调度耗时证据调 | 不能把数十MiB shadow变发送排队。500M小包按表约558槽；近MTU约72槽；两端/两向公平 |
| FEC TX | 每class lambda更新250ms、T=min(C,max(Tmin,1.5*15/lambda))，Normal C=clamp(R/4,8,24ms)，Game C=clamp(R/8,4,12ms) | 模块有trusted_rtt，FixedStream产品接线未调用。64 pending jobs按job速率*可接受codec等待计算；3个open class与已封组积压分开 |
| FEC RX | 按source block PPS*实际相对晚到horizon*1.25与字节双界；接收端共同传播延迟不等于额外等候。若要接纳两次outer repair，模型horizon可取Tcache；仅及时parity模式可以更短但需声明 | 32组/1MiB/150ms/128代均是固定接线值。不要机械改640；active heavy、completed compact和去重需分开计。接收horizon变长不允许延迟systematic交付 |
| MTU/MSS | min(outerMTU-IP/TCP,peer MSS,local/peer record limit)-31-FEC预留14-Game16；参数只扣一次。LINK20仅fragment；正常TCP MSS=TUN-MTU-IP/TCP | 旧record cap1180给Fixed仅1135B，而TUN1200；S030每端约7k包被本地尺寸拒绝。见第3节 |
| 内核缓冲与模拟链路 | 产品socket队列按服务中断PPS*bytes*暂态时间评估并看实际getsockopt/drop/age，不按线路BDP无限放大；内层TCP窗口则需要业务BDP | netem是延迟模拟存储，必须能容纳PPS*delay，完全不同于产品发送队列 |
| TCP序号与时间单位 | 外层Seq32按record字节推进，所有比较必须模2^32；活跃未定界字节区间<2^31。PN/计数使用宽整数，ms/ns换算单一入口；定时wheel约1ms分辨率、到期任务有poll预算 | 500M大包在80%/repair预留模型下约97s一轮Seq；60s smoke不足以覆盖。未知旧80s中断根因不因数值相近而定案 |

**不能把大N直接套现有全表扫描。** `ReceiptState::refresh_rack_wakes`在见证更新时扫描全部entries；扩到数十万前须改成发送顺序游标/有界增量索引，或给实际摊销成本证据。保留slot generation、固定密文重传、取消竞态。本次不是指示网络agent立刻重写全部模块：先使当前正确性通过，再按“时序与预算→缓存/去重容量→增量索引和slab”完整能力批次实施，同source回归，不逐数字拆几十个smoke。

高吞吐参考metadata只要比payload小得多即可；无需保留所有记录一整段最坏寿命。数据已收到就回收，未知/过期明确Abandoned。CPU理论预算仅为上界：单核心全双工每外层收/发事件预算约`1e6/(2*PPS*1.1)`微秒（表500M小包约1.63us），尚含不到注入器/系统中断等，因此不承诺任何4核runner一定跑满。小包达不到应报告PPS瓶颈，不伪称带宽达标。

实施优先级与边界：

- **P0正确性**：自动MTU、真实mode与fixed-applied、UDP/TCP持续推进；先收口原失败。不得靠FEC掩盖本地oversize/重复TUN/错误receipt。
- **P1低损高时延恢复**：真实RTT驱动PTO/W、两次修复寿命、repair字节预算、receipt历史/节奏、replay窗口作为同一完整能力批次。初始RTT未知先保守600ms，收到可归因样本后更新；不用注入器传netem真值。稀疏业务可超比例但绝对预算/次数/寿命仍有界；过期后的迟到systematic仍按首次到达规则交付。
- **P2容量**：主大包按最大65,536 shadow槽/方向作为高带宽档参考，**不是所有lane启动时分配同等payload**。缓存payload按需保留并及时释放，整体512MiB预算（双方各自计算）内包含fresh/RX/FEC。低速与Game按每lane真实PPS设更小界；未证CPU扫描问题前不先做多级slab重构。扩大元数据前审全表扫描，改有界增量推进；fresh池与repair不可互相饿死。临时更小容量必须readback并写CAPACITY_LIMITED，不能暗改算法目标。
- **调度绝对门**：两次修复上限不变；配置外层预算按实际发送字节结算；新包不用等ACK或等缓存空位；poll/batch有32包或约0.2ms起始budget（实测调，不定时攒32）；长耗时FEC工作拆量子，缺包只影响本逻辑恢复，不阻塞其他source/lane。已有有效budget优先复用，避免叠一套调度器。
- **CPU收益**：记录每GiB首次交付CPU-s及每百万处理record CPU-s、p99/未到率，模型给单核工作预算而非跨VMCPU百分比比较。sameVM AB/BA只对实际改动做一次有意义对比；容量上限不同的VM不能直接相除。编译一次、多请求复用；源码变再重建。

这些是待实施任务，当前提交只实现MTU和模型报告。接手者核对实验分支现有修复，已做部分直接复用。每批完成后测原反例+低损普通业务保护，然后继续矩阵；遇到容量或架构约束按证据调整计算前提并留痕，不无限追求一个预设数字。

## 3. 内层MTU随外层配置自动计算

网络agent `c297a8052272b1cb7a326ae0281d773e4669ca99` 的1180→1280是已定位缺口的局部修复；本分支按用户新要求将其推广成一次冷路径推导，**不把固定1280当最终设计**。S030 run39804670142是旧故障证据；S031 run39807984023及S032压力A/B仍由原agent持有，不重复dispatch。合并本分支时保留其其他数据面修复，只解决同一linux.go预算片段的文本重叠。

公开Linux两端新增 `--outer-mtu`，默认1500，声明外层IPv4 L3包上限；允许输入576..9000，但扣完开销后不足产品当前576B内层下限会明确拒绝启动。公式：`recordWire=min(configOuter,interfaceMTU)-40`，再取`peerMSS/localRecordLimit/peerRecordLimit`的最小值；`TUN=recordWire-31-(Fixed/Auto?14:0)-(Game?16:0)`。初始建TUN时用现有1360 MSS上限；认证后取真实对端限制，只能收紧，然后才启动Rust TUN读循环。各Game lane共同取最小值。无需新协议字段；沿用已认证的record limits。现有IPv4/TCP稳态头40、record31来自当前实现，若以后增加options/外层IPv6必须更新统一预算，不硬套40。

| 外层配置/实际接口 | 有效MSS/record约束 | Normal/off TUN | Fixed/Auto TUN | 当前Game/off TUN |
|---|---:|---:|---:|---:|
| 1500/1500 | MSS1360 | 1329 | 1315 | 1313 |
| 1280/1500或1500/1280 | MSS1360 | 1209 | 1195 | 1193 |
| 1500/1500 | peer record1180 | 1149 | 1135 | 1133 |

表格是公式预期，最终Actions readback才是实效证据。Auto始终预留14，不随升降档改TUN；LINK20只由实际分片扣除，不能再扣一遍。正常TCP依内层MTU自然分段；UDP不超过`TUN-28`无需内层IP分片。Jumbo外层不保证Jumbo内层，仍受MSS/record/slab限制。没有实现主动PMTU探测；路径低于已知接口/配置的情况仍需正确配置或后续PMTU能力，不宣称自动探测互联网最窄点。

功能验证复用同一原生ARM包：Normal/Fixed/Auto×外层1280/1500，客户端1500/服务端1280的非对称Fixed，以及Game2/4代表边界。每例读实际TUN MTU，双向验旧1135/1136反例、新MTU-1/MTU、DF MTU+1明确本地拒绝及Stop。Go单测涵盖peerMSS小于预算、接口限制、旧record限制、jumbo仍受MSS限制、过小有效预算拒绝。ICMP不是UDP/TCP压力PASS，下一步继续实际持续业务；不得只用小ping宣布MTU完成。Windows目前仍由M0维护的另一CLI/GUI入口，**本提交不冒充Windows已接线**；后续直接复用同一预算语义及原生Wintun MTU设置，禁止覆盖其并行改动。

大UDP兼容仍是独立门：正常应用发MTU+1/2×MTU的UDP时，记录内核分片或EMSGSIZE/ICMP；已有LINK路径保持。若FEC入口接到超预算单片必须明确计数/拒绝，不能当网络随机loss；需要强制兼容时以原有fragment路径做定向修复，不为高损大报文硬设低残余门。所有密文/path/DF硬检查保持。

## 4. 少而有效的测试顺序

1. **当前阻断先收口**：复用S030/S031/S032，不重跑整张矩阵。MTU边界+正常关闭合为便宜功能批次。32~34%残余不能借“理论不够”免责；也不能把k1..4硬套16:20。
2. **静态参数门**：输出实际生效的shadow槽/字节、PTO/W/expiry、repair方向/全局cap、retained receipt页、replay窗口、FEC限制、TUN/MSS/record与outer预算。不是再造监控系统：一次启动摘要+每秒已有汇总即可。和本文比对，明显80ms/64KiB等未改时先做定向修复，不盲跑500M。
3. **容量探索不是10/50/100/200/500全跑**：先已有低点校准；以近MTU大包为主、少量小探针，按可交付PPS/CPU-s估算一个有余量的高点。高点过可跳过同路径中间点；失败且可归因容量时最多一次中点定位，随后更高负载标PROJECTED_NOT_TESTED。每台新VM重新短预热。纯小包只做一个在资源范围内的PPS点，不能要求500M小包。普通接口单核饱和仍属产品瓶颈，不能只凭整机CPU未满排除程序问题。
4. **最终高点**：H500 off/2%/200ms和H50 maximum/30%/300ms，均以大包为主+小包探针；Game4逻辑3M实际业务分布（先核总wire），独立/共同突发各一条。纯小包能力仅单列，不阻塞大包主目标。只在实际可用模式上跑；Game+FEC未接线记UNSUPPORTED。高点通过允许推断同配置、同类包分布、同宿主资源上界内更轻负载，结论写“覆盖推断”，不是实测PASS。
5. **不能由极限推断的少量反例**：稀疏单包/尾包、上下行5%/0与0/5、低RTT重排、小/大业务竞争、Auto低→高→低、lane rotation、payload-idle与keepalive/重建、单/双向黑洞。每类一个代表波形；功能可同Action合批，性能每Action一个场景/一个测量job，独立场景可并行，AB/BA同VM顺序。
6. **有限收口**：同一失败无新信息不刷seed；一轮修复跑原反例+受影响普通业务保护，不回到全套从头测。生产correctness失败和机器容量不足分开。修复字节/实际k/r/临界延迟缺测不宣布模型达成；只补当前归因需要字段。

先60s steady定容量，主高点可行后单独做约240s持续大包（500M模型可跨两次Seq32回绕），记录实际byte/seq进展。若VM只能较低速，复用组件近回绕注入验证，不为了等待真实回绕无限延长Actions；长稳态/物理资格单列。质量报告/keepalive不算真实业务持续交付。

两极端的理论：off2%两次修复理想残余0.0008%、额外2.04%；off5%为0.0125%、5.25%，只有反馈/寿命/预算充足且IID时成立。它是目标参考，不设“必须零损”。最高档30%满16理论0.02283%，k1为2.7%、k2约2.511%、k4约1.739%、k8约0.381%。按**源包权重**汇总actual(k,r_sent)而非按组数平均；低速partial目标>1%时报告目标不可达并保留可交付指标，不无限延长等待或伪造满组。TCP有自己的拥塞/重传，记录steady注入/反压、ACK/cwnd/RTO、业务到达；无效注入不能冒充满速，长期零进展需修复，不能只看幸存UDP p99。

## 5. netem和包型的测试预算

表中500M小包、256B、近MTU的建议模拟队列分别约80,522 / 36,972 / 10,327包，含delay×PPS×1.25、10%repair及5%control-PPS余量。**默认32768不覆盖前两项**。相同Gbps不能统一队列包数；允许提高本次namespace的netem limit，但不改产品全局sysctl。内核skb内存、生成器和双向总额也要记录，模型遗漏流量使实际backlog偏高时重算。损伤队列溢出不能算预设IID随机丢包。

当前independent Game netem 的rate是**每lane**上限；填写50M会变成4×50M，不是共享50M。若用每lane12.5M总50M，明确标固定分额不可借用；共享总线路场景用shared队列50M或以后在现夹具加真实共同rate父级，不声称prioq本身能限总带宽。无需为本轮另造测试框架。

报告在已有evidence里保留：模型输入/版本、真实SOURCE、有效参数、包型PPS/大小分布、外层字节分项、CPU/PSI/单核上限、各边界拒绝/queue-age、首次到达/未到/迟到、实际FEC分布、Stop及下一步。一份全量模型不进入每个agent启动上下文；接班先读本页§3–4和当前status，有问题再按表查模块。
