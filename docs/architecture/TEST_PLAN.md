# Actions：先编译、复用产物、广覆盖而不穷举

2026-10-23新策略以[一次修复决策](../decisions/NETWORK-ONE-REPAIR-20261023.md)为准：外层最多一次、固定高容量上限/按需使用回收，off IID1/2/5%残余参考0.15/0.25/0.75%。本页旧p³不再是新SOURCE验收模型。先同VM原失败A/B和相关正确性，再继续矩阵；旧两次结果保留，不因用户变更重写历史PASS/FAIL。

**2026-10-22网络矩阵新入口**：[NETWORK_MATRIX_20261022](../testing/NETWORK_MATRIX_20261022.md)。用户指定500Mbps/2%/单程200ms及50Mbps/30%/单程300ms，均按外层线路总容量计；最高FEC持续30%目标≤1%。该方案规定容量停止、37条有条件场景、独立Action并行、off修复预算/内层业务、Game相关损伤及宽松生命周期门，覆盖旧文中与之冲突的自动档选择目标和时间阈值。理论表是MODEL_ONLY，未跑不记PASS。

FEC v2工作包按[FEC_V2_TEST_PLAN](FEC_V2_TEST_PLAN.md)的短块/新wire/自动曲线与跨平台专项执行，覆盖下文旧20:R/Go字节相等专属门；本页性能一Action一场景、同job AB/BA、功能合批、容量停止和真实证据规则不变。不可把专项规划当已执行资格。

本文件是产品夹具与验收契约。当前已有治理、组件功能和专项测量 workflow；具体完成范围以精确 SOURCE 的 evidence 为准，不能把本文列出的工况或组件绿灯写成完整产品通过。

**测试开放顺序新授权（PLAN021）**：对已经真实接线的功能，一次精确 SOURCE 的 Actions 正向功能 PASS 就可先开放显式网络工况测试入口，**物理机、全局一体化验证、所有弱网矩阵和 p99 不是开放测试的前置硬门**。后续相应真实网络测试用于填补 `NOT_RUN`。切勿把原始 Go V3 的 Game 正例冒充新 Rust V4 公开 Game；未接线功能保持 `EXPOSED_NOT_WIRED`，并非 `PASS`。安全失败、WFP 原生持久化读回、owned WAL 外来/陈旧 CAS、认证/Stop 不随测试开放而放宽；Windows 现有真实 WFP CI 仅 TEST-NET scoped，不证明宿主全局 /1。


可执行的公共V4持续业务入口与参数用法见 [NETWORK_HARNESS](../testing/NETWORK_HARNESS.md)：产物复用、独立双向UDP/TCP、单Action单场景、同job AB/BA及实际能力限制。独立网络测试任务按用户2026-10-22最新授权与[长期接班说明](../testing/NETWORK_AUTONOMOUS_WORK.md)执行；不等待Windows接通或M0逐次派单。

## 0. 按能力交付，及时进入持续业务（2026-10-16 修订）

本节统一任务粒度与推进规则；旧日志/cursor 中更细的下一步只作历史计划。任务 ID、权限、原有硬门不变。

M0已有持续业务开发基线；2026-10-16的 [热路径成本补充方案](../decisions/M0-hotpath-cost-first-2026-10-16.md) 第6节规定该任务的有限配对集合，是否仍执行以最新授权与交付事实为准。下列首包/基线建立规则只用于缺口，不要求重做已完成步骤或重开已收口优化。优化前后均为Rust同拓扑/同夹具，原Go/Rust粗略观察保留为非因果证据；原正式资格硬门仍不变。

- **功能批次**：同一能力的正常路径、必要边界和已知回归一起实现，编译一次后批量执行便宜断言。不要把一包→两包→12包、10ms→150ms逐项升级成独立交付。已有证据复用；新增测试必须回答新的故障假设、回归风险或能力缺口，不能仅为增加 PASS 数。
- **模块自主测试**：已分配完整工作包内，worker使用既有workflow自行构建、dispatch、验结果和修复，局部PASS不要求M0先合入才运行下一项。缺公共接口/夹具入口时按GOVERNANCE第3节一次协调；组件功能与成本可先测，完整产品资格仍由实际组合路径证明。M0按阶段集中验收，不为每条绿灯中断调优，也不等全部模块完成才首次接线。
- **当前 M0 收口**：在原认证 Go→Rust owner→真实 raw/TUN 路径上，确定性丢弃一个已知加密 DATA，观察后续不同合法包仍交付；可与必要的停止、换代、MTU、完整性回归合并。若精确源码已有该证据直接复用。该项证明缺包不挡后包，不宣称重传有效；随机 netem 丢了未知控制包不算此证据。小样本随机损失只作观察，不用反复增加几个包来获得“抗丢包通过”。
- **紧接着交付持续运行能力**：发送器、接收器与原 Rust 数据处理循环独立推进，应用发下一包不得等待上一包验收；steady 不逐包由 Go 测试代码调用 RX/TX helper 驱动。可以复用真实冷建连入口和测试设备边界，但不能另写 crypto/delivery 快捷路径。缺持续循环就实现它，不能只把串行 smoke 的包数加大后称性能测试。
- **第一份开发基线**：Normal 单 lane、FEC off、一个已验证 cipher、诊断默认 off；真实 Linux TUN/raw，优先独立 namespace/veth 两端。预声明固定比例的 64/256/1200/当前有效内层 MTU 大小包，明确长度计数口径，双向各 10Mbps，先无人工损伤，热身 10s、测量 60s。保留现有三 cipher 功能回归，性能无需先穷举三 cipher。记录实际注入/交付/missing、进程 CPU-s 与注入器 CPU、RSS、wire/PPS、socket/队列 drop、队列年龄及有业务输入时的交付空洞；RTT p99须来自独立计时业务/探针，不能拿测试 helper 等待时间或短循环 elapsed 换算。注入器不能逐包打印日志；若注入率未达到计划，如实判原因。
- **开发基线与正式资格分开**：认证、所有权、generation、完整性、MTU 和所用路径的安全关闭不得绕过；已知内存/生命周期缺陷先修。默认 capability 关闭、外部建连覆盖或尚未使用的异步 driver 边界等缺口按事实保留 NOT_RUN，不要求全部产品能力完成后才观察已可安全运行的热路径。开发基线必须明确真实/替代边界和未验项，不能升级生产能力或关闭 B01–B04。仅有 loopback 时可先做限定范围诊断，不冒充两端完整性能资格。
- **基线之后**：按风险另跑延迟、1%/5%损失和并发/生命周期场景。每个性能 Action 仍只有一个配置/seed/场景和一个测量 job；同配置预声明波形及同机顺序旧新 A/B 仍按第 2 节。功能批量的例外不能拿来混跑性能矩阵。FEC/Game及完整组合矩阵按实际依赖后续集成，不挡 Normal/off 基线。
- **停止扩展**：必要断言满足且结果可解释就关闭该功能批次，推进持续业务。性能差就按 CPU/队列/注入证据定位；宿主容量不足停止更重负载。复跑必须说明源码修复、夹具修复、新故障假设或预声明重复的目的，不能换 seed 刷绿。日志按能力批次汇总，S→H/intent/失败留痕机制继续有效；不为本节新增考核系统。

## 1. 一次构建，多次验证

模块测试入口按[PLAN-009](../decisions/M0-worker-selftest-entry-2026-10-19.md)补齐：M0一次提供公共prepare/paired执行能力，worker自己维护模块夹具、请求与结果。先编译/验功能取得真实manifest，再发独立性能请求消费产物；不能因worker不能修改workflow就要求M0逐条代跑。入口及有界ABBA扩展需实际实现/验证后才能使用，现有两leg规则不被文档自动绕过。

构建 job 固定 product SOURCE、legacy SOURCE、Cargo.lock、Rust toolchain、Go toolchain、C/汇编编译器、target/features/profile。产物含库/控制程序/预编译test二进制、manifest、SOURCE、文件size/hash、工具链和ISA能力说明。Linux x64、Linux ARM64、Windows x64 各自构建；cross-build成功不等于native性能通过。

Rust使用固定release配置（初始opt-level3、thin LTO、保留line tables用于profile；以构建耗时/运行证据再调），旧新对比不能偷偷使用不同性能flags。portable 不用 `target-cpu=native` 编译给别的VM，SIMD走runtime dispatch。依赖/编译缓存只加速构建，不能代替来源验证。AWS-LC/ISA-L native对象按目标固定，避免“Rust源码相同、Cflags不同”被忽略。

消费测试run按 build run/attempt/artifact ID 下载，逐文件验hash、目标和来源，再执行已有二进制；测试 job 不现场重编译、不下载浮动依赖。相同SOURCE可复用几十个功能run，不能把过期artifact只剩hash称可重现。编译器sanitizer版本单独build id，不参与正常CPU比较。R0先实现最小单目标闭环，再扩三目标，不先造远程编译平台。

## 2. 同一 Action 内顺序 A/B（2026-10-14 覆盖旧约定）

性能隔离单位是 **一个场景/配置/seed的实验**。独立资格仍一 run 一个测量 job；新旧比较允许该 job **连续两条测量 leg**，A/B或B/A。两个jobs即使同workflow也不是同VM，不合格；同时跑两程序争用也不合格。

request声明 `mode=paired_ab`、共同scenario/seed/effective config、两个完整SOURCE、两个build manifest hash、预定order。receipt每leg记录相同job ID、实际runner identity、起止单调时间、实际source/config与结果。verifier拒绝跨job、时间重叠、错误source/config、缺leg。A/B差异只有被测产品；一方不支持的行为单独说明，不能让新版本off对旧版本on。

每leg之前：停止上条程序→确认owned namespace/进程/队列清理→相同拓扑重建→同样热身。默认热身10s、测量60s，弱网三阶段/恢复用120s，生命周期/长测按实际周期最少时长。编译/下载/压缩不在计时段。顺序在request前确定，不按看到的结果换顺序。关键结论需要时另一个run做反向BA，保留全部结果。

同VM只消除了硬件型号差异，不能消除宿主争用随时间改变。每leg记录 CPU型号/flags、逻辑核/实际cgroup quota、频率可观测值、内存、内核、虚拟化、PSI/steal、后台负载、NIC有效buffer、各进程CPU-s、进程/内核drops和queue age。做轻量同源RTT/注入器校准，出现背景变化给INCONCLUSIVE，不按两个不同型号CPU的“百分比”作优劣结论。

功能测试可一个job顺序运行多个便宜断言；不要把所有功能也限制成独立120s run。模块各自request命名，Actions并行运行在各自VM即可，禁止多性能实验挤同一VM。

## 3. 容量阶梯与停止

先做注入器/原路径空载基线，再 Normal10Mbps/方向、Game3Mbps/方向（逻辑业务，非每lane各3M）。按10→50→100→200→500Mbps上升，大包/实际混合优先；极小包单列PPS阶梯，不默认500Mbps小包也同价。FEC20:20和Game副本先算所需wire带宽，超过已知链路能力的组合只做模型标记。

满足以下证据组合才判容量：输入实际注入率、CPU/调度压力、收发drops、队列年龄斜率、吞吐随负载饱和；不能看到总CPU80%就称够用，也不能看到一个owner满核就全部甩给host。分类为：

- `HOST_CAPACITY_LIMITED`：宿主/注入器/内核资源已限制，无法公平测更高负载；停止该资源维度更重的点。
- `DATAPLANE_BOTTLENECK`：背景正常，产品单线程/锁/分配/编码达到上限；保留profile并优化，不用runner标签掩盖。
- `INVALID_INJECTOR`：负载/损伤/包率没按计划送出，不能评价产品；少量skip按实际偏差容忍，不能一slot就整场作废。
- `INCONCLUSIVE`：两leg背景差异或样本不足，不能宣布回归/改进。

一旦达到上限，不继续更高带宽/更多lane/更重FEC浪费Actions；继续较低负载的密码、MTU、生命周期等正交功能。用测得每包/每字节成本、实测可共享占比、wire需求给容量区间，至少列输入与误差；超出实际验证区域都标 **PROJECTED_NOT_TESTED**。不能线性外推越过cache/memorybandwidth拐点仍当通过。

## 4. 分层覆盖账本

不用全部笛卡尔积。以下锚点全覆盖，其余用pairwise+实际风险组合；每个配置有“已生效回执+对应test ID”，不能只测解析成功。

| 层 | 工况/断言 |
|---|---|
| 纯核心/向量 | GF256旧新/标量/SIMD、k1..20/parity4/8/10/12/16/20、短/不对齐、损坏/重复；3种AEAD/HP/KDF、nonce/seq wrap、bitmappage、budget/timer/freedhandle |
| 正常首到 | UDP/TCP/混合双向和单向，64/128/256/512/1200/MTU内最大；1包/s稀疏、10ms批突发、持续满速；payload完整和每流首次到达 |
| 弱网 | RTT10/50/150/300/600ms；off IID0/1/5%，高损10/20/30%预算退化；固定FEC按模型选必要点；数据/反馈非对称损失；乱序/重复 |
| 突发/相关 | Gilbert-Elliott，预声明seed/状态时间；Game各lane独立与共享黑洞两类；100ms/1s/10s单向黑洞及恢复；80s留R6专项 |
| FEC档位 | Normal off、固定全部档、auto普通/激进；上/下行不同档、on↔off、旧block drain、sizeclass sparse flush；Game2/4固定档不误启auto |
| MTU/真实业务 | outer1400/1500、真实TCPoptions/peerMSS、内层budget−1/等于/+1；UDP大报文/多fragment、TCP大write经真实MSS分段；IPv4 DF/非DF、合法ICMP错误；超限拒绝有计数不静默挂死 |
| 生命周期 | A→A+B→B；新lane失败旧lane继续；idle关闭后首个payload重建；keepalive丢失不冒充无业务；auth/generation/多client隔离；断开/重连/退出清理 |
| 系统/产品 | DNS1.1.1.1与8.8.8.8互备、LAN直连/其他隧道、可选中国IP分流、IPv6默认拦截空路由；GUI切服/保存/真实生效；Linux服务重启；portable不泄漏文件 |

baseline RTT必须同源码/同job条件校准；包含内核/驱动时间，不能只测函数调用。hosted Windows没有Npcap/权限时，相应项明确UNSUPPORTED；模拟driver可验功能但不能替代真实抓包/吞吐资格。Linux ARM hosted native用于ISA正确性与该host性能，不能冒充用户ARM机器。

### 剩余集成易错点的最小验证（2026-10-17）

以下并入现有模块用例/manifest，已有等价同路径证据直接复用；不新建任务ID、不重开已完成的024优化，不要求每行一个Action。功能反例同一能力批量跑，只有受影响性能锚点才做同job顺序A/B；不追加固定收益百分比或全矩阵前置门。

| 接入时机 / 现有ID | 必须证明的边界与省时做法 |
|---|---|
| R1/R2，I01–I04、A01–A06 | 从接近seq32回绕处开始，双向持续、乱序、旧repair跨界；另验参考高水位前进超过初始半空间。真实owner/driver用同一扩展逻辑，PN不重用；不靠定时换lane掩盖。无需先压满500Mbps或做小时长测 |
| R1/LINK，L01–L04、M01–M04 | 末片先到、已发半包时MTU下降、并发小包继续交付；旧parts+新输出的内存峰值受界、无混合stride。真实TCP大write按分段计，合法大UDP与越界输入分开 |
| R3/FEC，F01–F06及R01–R04 | 持续20:20且fresh始终有活：健康容量下parity按实际产出服务、待发年龄不持续增长，重传10%独立记账；稀疏k小、切档off仍drain、compact后输出lease未被复用 |
| R4/Game，G01–G04、C01–C04 | Normal重叠不误复制；Game逻辑ID跨lane/换代一致，重复零交付；一lane慢不拖全体；分别声明独立丢包与相关黑洞，不能用独立概率替代相关实测 |
| R5/R6接入，P01–P04、B01–B04 | 首次Wake失败后有业务能再次唤醒，旧完成事件不破坏新epoch；keepalive与payload idle独立；旧配置回执不覆盖新选择；标准发布配置实际加载匹配库并走原认证/停止入口 |

无HOL只保证外层缺包不挡后续独立业务；单条内层TCP流仍有TCP自身的有序语义。定向测丢掉已知DATA后其他独立包/流的首次到达，不能要求同一TCP流绕过缺字节交付。FEC模型按实际k/r、碎片数量、parity是否及时发送和相关损伤解释残余loss，不用“20:20”标签一刀切零丢包。

延迟必须同时保留未到达/超deadline数量，不能删掉慢包后仅对幸存包报更好p99；RTT与单程不能混用，跨机单程时间没有可靠时钟校准就标不可判。内层Mbps、外层wire Mbps、PPS及源包/parity/副本/repair/control分别记账；CPU下降若伴随少发parity/副本、少交业务或路径未接通，不能记优化成功。

旧夹具借鉴入口：原 `docs/REALPATH_TEST_FIXTURE_GUIDE.md`、`scripts/` 和对应workflow；R0按实际参数/产物schema移植最小adapter。不要直接复制整套旧STATUS/历史失败规则。沿用损伤阶段实测校验、10ms业务首到桶、effective config、两端进程/host CPU、socket级drop、包长账本和hash。每个模块识别自己的request与run，不帮别人重复dispatch。

## 5. 分析与判定

- UDP以发送序号和接收首次时间计数；TCP既测持续stream，也测多条独立业务连接的短请求/响应，不只用iperf吞吐。大write不是一个线上TCP超大包，应验实际segmentation/PMTU。
- 延迟报告 p50/p95/p99/p99.9、超业务deadline数、未到达数、最大连续有offered而无delivery时长；稀疏自然空桶不判HOL。随机业务内容加可验证hash，避免压缩/去重巧合。
- 用 wire trace的方向/长度/seq/ACK/timestamp摘要检查TCP-like/TLS-like、握手/票据、同密文重传、无IP碎片异常。只保存有界header摘要/必要失败切片，不持久海量业务pcap。
- 低损off比较 p³ 的适用条件；FEC按实际partial k、repair到达/相关trace oracle验，不拿20:20保证任何loss都零业务损失。判定器的允许带来源写进config/manifest。
- 统计CPU-s/GiB delivered与CPU-s/Mpacket，RSS/峰值/slab在用/活跃shadow、owner等待/queue age/syscalls/scheduler wakeups；diagnostic mode与普通默认off性能分开。
- PASS/FAIL、CAPACITY_LIMITED、UNSUPPORTED、NOT_RUN、INCONCLUSIVE分别留痕；程序失败不能让aggregate workflow绿灯变成通过。先看实际业务，再看microbenchmark。

每阶段只保留能解释结论的小摘要、hash和必要失败日志。模型/单测绿灯不能填产品资格。R6完成才进入可交付前状态，物理验收仍另列。
