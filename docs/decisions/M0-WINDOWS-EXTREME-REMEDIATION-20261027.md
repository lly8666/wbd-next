# Windows 接线整改、共享参数与极限性能验收

状态：用户授权的施工方案，产品修复与性能结果 **NOT_RUN**。审阅 main `c7fef14b6e2443ba432d52478f33c374af6466e7`；不是重新做已通过的接线，也不宣告 Windows 已有 Linux 的性能资格。

M0 接手入口：[执行提示词](../prompts/M0_WINDOWS_REMEDIATION_EXECUTION.md)。证据：[本次只读审计](../evidence/windows-main-audit-20261027.json)。现行外层策略仍是[机会式 v3](NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md)，不恢复旧快速重传 SLA。

## 0. 执行方式与范围

- 用户要求：**先把本整改包代码、调用方、测试用例、装配/构建清单、参数读回、夹具改动全部写完，冻结 SOURCE，再集中执行 Actions 测试。** 编写阶段可做静态审查，不逐 helper dispatch，不以普通 Normal 绿灯代替缺失能力。
- 一个批次 intent 足够。M0 保持当前唯一集成作者；按最新 main 追加实验分支，不覆盖其未提交代码/cursor。先结算正在执行的 run，不重复启动。修复本批依赖，不顺带开发下一批认证/GUI/生命周期新功能。
- 代码完成后的顺序：同源装配/编译及组件回归 → 一次真实 Windows/Linux 全功能批次 → 独立性能 Actions。失败后只修原反例和受影响保护门，不全矩阵重跑。
- 正确性优先：账号/地址/generation 隔离、认证、固定密文重传、Stop、真实首次交付不变。业务不等 ACK、repair 缓存、FEC 组或坏 lane。内层单 TCP 自身有序不等于隧道跨业务 HOL。
- 本文修订 Windows 旧临时参数/验收入口；旧文档中的256项/750ms/两次修复/旧MSS不再是施工目标。已验证成熟 FEC 数学、SIMD、Linux批处理不推倒重来。

## 1. 当前测试到底证明了什么

| 证据 | 真实范围 |
|---|---|
| 4977f12 / [40449519463](https://github.com/lly8666/wbd-next/actions/runs/40449519463) | 仓库收据记录七模式真实 Win/Linux 功能通过；Auto 只是启动档，不是自然调档或压力通过 |
| a0c8eeb / [40457048399](https://github.com/lly8666/wbd-next/actions/runs/40457048399) | 操作者请求 revision2 的范围通过，不替代自然 2s/8s 判断 |
| 9d2362d / [40476182202](https://github.com/lly8666/wbd-next/actions/runs/40476182202) | 已独立下载 artifact12721601306并核 SHA256；自然 Auto FAIL：控制 TX expected2744012027/got2744012455，相差428B；此前真实 UDP/TCP 可通，完整 Stop NOT_RUN |
| 6d35857 / [40483279229](https://github.com/lly8666/wbd-next/actions/runs/40483279229) | native kernel/FEC/normal/engine成功，receipt 7通过4失败；四项都在预期保留1项实际0项，需区分一次修复新契约与真正回归 |
| 6d35857 / 40483279286、40483279256 | 前者公开 CLI 原测试存在性/非skip门失败，组合构建步骤也失败。先给精确首错与替代测试映射，不能删门刷绿 |
| b305e29 / Governance、maintenance、G2 | 治理成功，不代表产品性能 |
| 6d35857 / [40483279255](https://github.com/lly8666/wbd-next/actions/runs/40483279255) | 本轮追到最终FAIL并核artifact12724129609/hash：Fixed和Auto启动模式PASS，Normal及四个Game模式FAIL。Normal在WL-N0中Rust seal拒绝后退出，NPF本地drop7333、最大交付间隔2102ms、pending885；不能凭885判断未有Arena/内部容量问题。Game最后样本为Windows发送器WinError10051网络不可达；产品/路由/包长导致与否待定，不误判为纯发生器容量 |

9d 资源采样28点覆盖27.172s：同一 Windows EXE（Go+Rust DLL）总CPU8.546875s，其中kernel6.78125s（79.34%）、user1.765625s，平均0.315核；峰值working set42.06MiB、private37.34MiB。包含启动/故障、非稳态性能资格。日志还记录本地Npcap ingress drop64、最大交付间隔493ms；不能把它当p99，也不能认定drop发生在稳态。

## 2. 与 Linux 的核心差异：薄适配还没真正做薄

Linux公开入口 `bridge_v4_embedded_linux.go::startRustOwnerLoop` 启动原生 Rust 长期循环；Windows `m0_native_v4_peer_windows.go::pulse` / `m0_native_v4_game_peer_windows.go::pulse` 则由 Go 逐包取 Wintun、调 Rust seal/open、发送 Npcap、处理 ACK、查询 outstanding、提交完成。**Go 仍在稳态热路径，Rust DLL CPU也记在Go EXE名下，不能按进程名归因语言。**

本批目标：共享协议/预算/时钟/状态机，平台层只做有界 I/O、句柄生命期和结果传递。无需重写建链、WFP/WAL、GUI；也不要求为了“全Rust”立即重写Npcap驱动接口。

## 3. 必须完成的施工项

### A. 先一次补齐正确性与状态事务

**A1｜自然Auto的TX序号断裂（实测FAIL，根因未定）**

定位 `m0_native_v4_peer_windows.go::{transmitOne,rustFeedbackOne,rustFixedParityOne}`、`v4_windows_owner.rs::m2_next_feedback_entry`、`v4_windows_fec2_owner.rs::{seal_symbol_entry,stage_fixed_source_entry,stage_fixed_parity_entry,fixed_change_revision_entry}`。同批处理最新Normal的seal拒绝：保留Rust具体返回码/阶段，查Arena、原owner队列、时间源和容量；不能把泛化的private-owner-refused当可忽略丢包。

源包、parity、控制共享一个Rust PN/SEQ分配和发送完成账本。消除多个调用者各自维护可写sendNext的权威；Go只核验Rust输出描述符和提交I/O结果。先记录有界最后64个事件：kind、PN、SEQ范围、revision、stage/commit/NotSent/Uncertain、caller、单调时间，不记录payload/密钥。428B只作为定位线索，不预先认定某一包或竞态。

所有可失败的大小/容量检查尽量在seal前；seal后失败必须结算已分配范围和不可变密文，禁止回滚nonce、偷偷跳过已seal记录、把post-seal错误改成“无包”。所有者内按实际发送顺序批量生成描述符；I/O后逐项或确定前缀结算，原PN重传不再分配SEQ。Busy/容量不足不是整体连接崩溃；真正状态不一致仍明确失败。统一单调时钟，审计热路径残留MonoNs(0)/人工tick对调度的影响。

**A2｜FEC状态被错误路径拿走（静态确定）**

`stage_fixed_source_entry` 在 `e.fec2_tx.take()` 后调用可能失败的 `e.arena.allocate()?`，失败会跳过 `e.fec2_tx=Some(stream)`。将可失败分配前置，或用作用域守卫保证所有返回路径归还；同类take后问号路径一起查。回归：强制Arena耗尽→返回有类型容量结果→释放空间→同generation继续处理合法新包、配置与Stop；不得只靠扩大Arena掩盖。

**A3｜外层序号半回绕导致误丢（静态确定，未测量触发）**

`m0_native_v4_rx_window_windows.go::Check` 先用 `int32(seq-cumulative)<0` 返回旧包；`IndependentAEADCandidate`也先拒绝负差。长期未补的旧缺口使cumulative停住，合法新业务推进超过2^31B后，authenticatedHigh附近的新包也进不了独立认证路径。500Mbps序列字节流约34.36s达到半空间、68.72s一圈；实际以包含控制/FEC后的SEQ字节率计算。

共享Rust已有64位展开/认证高水位逻辑；以近端已认证进度展开候选，cumulative仅做外观ACK账。不得跨缺口假ACK，也不得用未认证包推进可信高水位。历史80s故障**不据此宣布关闭**。定向构造2^31和2^32边界、丢首包、长缺口、新包/迟到/重放；无需反复跑几十秒才能复现。

**A4｜错误、完成和Game单lane隔离**

Windows Game `transmit/send` 顺序发送，任一lane失败立即返回；`receive`任一FIN/RST也退出整组，Rust每包检查所有成员均active。这与坏lane不拖住健康lane不等价。改成每lane typed结果和健康状态，真实局部失败只停止该lane、释放其票据，其他lane继续；组共同失效/全部不可用才走组级恢复。链路弱网本身不能伪装成本地发送成功。

Game/off当前adapter.drain回调true代表“复制到Go数组”，尚未完成NPF发送；审计哪些计数/状态把它当已发送，与FEC路径一样用真实I/O完成回执。RX FEC batch部分写入Wintun时用已写前缀/逐帧结果，避免一个失败让已交付帧再次提交。区分认证/畸形包正常拒绝、可选容量拒绝和内部owner错误，不能将所有Rust open错误静默累计为普通坏包。

### B. 去掉Windows适配引入的每包固定开销

**B1｜设备验证从每包OS查询改为受保护会话租约**

`CreatedWintun.VerifyCurrentNative` 每次重新Identity（NativeIdentity、ConvertInterfaceLuidToGuid等）并holder.Verify；Wintun读写/Fixed seal/parity和Game verifyLive重复进入。保留建立/绑定/重配置/恢复时完整OS核验，持有真实句柄与generation租约。热路径仅检查有效标记/epoch并借用已保护句柄；Stop撤销后等待在途调用清空再关闭，不能取消owned校验。真实设备错误触发失效和重新核验，周期审计只能作为补充，不能作为防止句柄复用的唯一措施。

DLL/Proc在会话建立时解析一次；去掉Fixed每包FindProc、CreatedWintun每包NewLazyDLL。不为此删除硬门或恢复脚本。

**B2｜批次跨FFI，复用缓冲和完成数组**

采用现有最大32包/约2ms工作预算，**有多少处理多少、不等凑批**；Go平台I/O可暂留，Rust一次消费一个描述符批次并返回发送/交付动作。输出缓冲、NPF序列化scratch、长度数组复用，按实际长度拷贝，避免每包清零16×2048B FEC返回结构、多次wire/frames.to_vec。协议状态留Rust，Go不另做重传/FEC调度。

NpCap/WinTun需要保留的内核拷贝不宣称零拷贝。缓存不可变密文引用直到真实I/O完成；Stop先收在途借用。每次所有权转移和分配路径有文档，避免重现旧ownership混血包。

**B3｜等待、ACK、锁与统计**

空闲优先复用Wintun read event、Npcap可用事件/已有接收通知及最近协议deadline，取消恒定1ms全栈轮询；没有事件能力时仅使用有界回退，不忙等。反馈/ACK遵循共享期限与批次合并，不能每个接收包额外强制一个sendACK而不记其CPU/线上开销。

`m0V4RxWindow.Check` 对最多256项map逐包扫描重叠，改复用共享有界区间/页索引，或有依据保持小窗口并O(1)常见路径；不为外观维护无界重排表。Game组/各lane有效性在租约边界核验，减少每个包遍历全部成员和嵌套锁。TX/RX不共持一个大锁执行FEC/系统调用。计数线程局部累加、1Hz快照；详细耗时按1/1024包采样或短期profiling，不全量逐包日志。

### C. 参数按实际极限推导，取消repair对fresh的背压

**C1｜1536 credit不是高带宽设计，且方向不对**

Go `transmitOne` 在outstanding>=1536时不读TUN；Rust `v3_seal_entry`同样把MAX_M2_FROZEN当首发准入。下面表是解释当前全量保留/等待反馈会遇到的限制，**不是要求分配整个BDP作待发送队列**。

| 边界/参考包型 | 计算 |
|---|---|
| 500Mbps外层、1500B IP包 | 约41667 packet/s；RTT400ms flight16667，RTT600ms25000 |
| 500Mbps UDP应用、1401B payload | 约44611包/s；1536项只覆盖34.43ms；若等RTT400ms退役，理想应用上限仅43.04Mbps |
| 500Mbps单TCP应用、1377B payload示例 | 约45389数据包/s；RTT400ms需25MB业务窗口；外层首发约544.66Mbps，不能放进500Mbps限速 |
| 双向TCP500 | 每向还叠加反向内层ACK/控制；70k PN/s只作规划示例，必须实测包型重算 |

执行现有v3约1/2候选抽样、全进程候选32768/s、一次机会式重传、65,536 repair槽、payload128MiB上限/endpoint总512MiB的共享按需方案。它们是上限，不启动全分配。不选中/过期/缓存满直接放弃**可选修复资格**，首发继续；并保证fresh的Arena预留不能被repair引用钉死。不得只将1536改65536而继续保留ACK闸门。

短fresh队列按PPS×服务间隙计算：45k PPS×2ms约91项，70k约140项，初值256描述符/明确字节与年龄界；不按600msRTT堆队列。允许批次<=32和CPU预算提前yield，I/O队列拥堵有可观测丢弃或上游自然背压，不能假造发送完成。

**C2｜Windows字节绝对帽与PPS/时间账同步**

`m2_arm_entry`还设每方向65,536B/s、process131,072B/s、grant32768B/50ms：开启v3比例没有取消这些帽。65,536B/s只有0.524Mbps；50Mbps线路的6%已需0.375MB/s；标准F=0.8C/1.1时9%信用为0.409MB/s（C50）或4.091MB/s（C500）。32KiB若每50ms只发一次最多0.655MB/s。检查实际grant刷新方式，不能机械认为周期即硬限。

方向/进程使用已实现共享v3批量预算，按实际首发字节累积，不另造Windows限速器；配置绝对上限需覆盖声明场景。grant按`rate×实际租期+8MTU burst`计算，实际按需发放。R/F<=10%、R/(F+R+control)、R/C三项分开；30%标准充分负载才检查R/C约6%以上，低负载/控制黑洞不强逼比例。0损无重排重传应接近0，不制造重传凑数。稀疏例外保持绝对有界，不能被这次移植抹掉。

**C3｜Auto质量清理不是免费，也不能持锁清空所有历史**

当前Windows `drain_original_auto_mature_due` 在Entry锁内loop到所有到期项处理完；`MatureFirstSend`用一个BTreeMap和两个BTreeSet，每源包维护2s/8s定时项，配置131072且构造硬限200000。即使8s及时清理，45.4k PPS仍需约363k live entries，按1.25余量约454k；131072只能承受约16384源包/s。

本批先保持观测语义，别同时发明Auto选档算法。只有Auto所需方向启用长期精确质量窗口；Fixed/OFF仅保留实际功能所需的有限确认，不为“Applied资格”永久维护整套8s质量树。把发送时间有序项改为按需分段FIFO/有界时间桶，保留PN查询，2s/8s批量分类；每轮最多256到期项或约200µs（二者先到），剩余工作在下一调度轮继续，让新业务先得到机会。阈值是实现初值，测服务率确保`到期处理率>2×源PPS`；不能只加上限又固定100ms才处理一次。

45.4k PPS的精确质量元数据初始上限524288/方向；若每向70k则按`nextpow2(1.25×70k×8)=1048576`重新核内存。这是metadata，不缓存8s payload；只在需要的会话按需长大，计入共享内存总额。若过预算可输出unknown/capacity，绝不阻塞DATA或把容量丢失当线路丢失。若已有共享Linux聚合/抽样能等价保留分母与置信区间，直接复用；不要临时做未经验证的无权重抽样。

保持unknown/有效/本机过载分开；故障解除后质量可恢复，不让累计一次capacity_censored永久污染后续窗口。修复不得伪造512样本或降低自然Auto阈值来过门。

**C4｜receipt/replay/池/回收要是一张账**

按每lane实际全PN/s（含parity/control）重算：2s receipt历史至少`ceil(1.25×PNps×2/256)+1`页；45.4k约445页，现有512勉强覆盖单向，70k约685页，取1024页。每报8页保持有界dirty调度；不能每轮扫描全部页。

当前共享replay已是100k PN/s、3s horizon、600ms RTT、256KiB元数据预算，不再按旧8192窗口宣称未修。读取实际有效位数和FEC保留期验证，不无故扩大。repair密文最长沿用v3按可信RTT推导的期限（最大单程300ms），确认/一次修复后及时释放；周期清理按到期桶，不全池扫描；低流量物理占用要回落，allocator保留块与活跃引用分别报告。

### D. Windows MTU和Game接线补齐共享语义

Windows Game仍在Go/Rust多处硬编码1200B输入、1536B输出、ClientLimit1400；scratch=1200且收到更大合法包会返回错误终止worker。Normal/Fixed也有2048B ABI上限与超限直接丢弃路径。共享`path_budget.rs`已支持动态预算，平台适配没完整消费。

统一一次冷预算：`W=min(outer/local/route允许的TCP载荷,真实peer MSS,双端record cap,实现能力)`；Normal/off TUN=W-31，Fixed/Auto=W-31-14，Game再扣16一次。无options、外层1500且peer允许1460时分别1429/1415/1413/1399；外层1400分别1329/1315/1313/1299；1280分别1209/1195/1193/1179。实际TCP options、对端MSS和record cap较小则收紧，不能为追数字忽视真实约束。

从同一快照生成TUN实际MTU、公开参数/GUI读回、FFI缓冲容量、NPF最大包；小路径用现有LINK兼容分片/必要ICMP或明确错误，不能大包杀连接或悄悄截断。大UDP低损可兼容；高损多片成功率按片数计算，不要求等同普通包。不强制本批支持9000 jumbo，无法支持的配置启动时清楚拒绝；不得声称跨平台支持了公式范围但实际ABI拒绝。

Game要复用Linux实际支持的错峰/即时配置与真实单调deadline，不能 `offer` 后必须一次返回全部lane副本：当前这一假设无法表达延后副本。共享逻辑payload/单次FEC，分别按lane加密/完成/取消；最早副本不等后续lane。先核固定策略的requested/effective，不另设计新时序算法。

Windows `ServerPort+i` 是现存多端口实现；**与用户最终单公共端口目标不符**，但属于上一轮旧功能恢复A批，与Linux服务端一起改，不能只改客户端。本文记录为功能缺口，不把它作为当前性能矩阵阻塞，也不宣称七模式PASS已证明单端口多客户端。认证简化、IP租约、GUI/DNS完整恢复仍按后续计划，不能夹在本次性能整改中扩大范围。

### E. 测试装配与监测一次写齐

- 修复当前夹具证据丢失：多模式脚本生成各mode-report和mode-batch.json，但workflow上传名单只留normal-report/report，其他模式报告未上传；资源和wl-n0应用日志跨mode覆盖。改为每SOURCE/mode/scenario独立目录并上传脱敏报告、应用日志与1Hz资源摘要；不要上传含密码的启动脚本/私钥。先让真实首错留得住。
- 当前functional mode循环还会在同一Action内分别跑Normal/Game的WL-N0，且生成器固定96/288/1060/1200B UDP payload；1200B应用包实际IPv4为1228B，已超过WindowsGame临时1200B输入上限。功能合批只留有限贯通，性能移到单场景Action；尺寸用生效TUN预算生成，超限兼容另设清楚用例。WinError10051须按产品退出、owned路由readback和首个Rust错误关联，不能自动归咎VM或掩盖产品超MTU路径。
- 对四个receipt FAIL逐项说明：如果测试仍要求一次修复后保留/重试，而当前契约允许终结回收，更新为新合法事件序列；保留同密文、真实发送计账、NotSent/Uncertain区别、跨方向共享额度等断言，不能直接删测试。
- 清理失效的公开CLI测试名/整文件skip扫描与重复手工装配列表，采用已有唯一装配helper、精确旧Go SHA和补丁hash。旧测试被替代必须指向同等真实入口证据；历史红灯原样留存。
- 启动输出effective参数账，1Hz产品进程user/kernel CPU-s、RSS/private、Go分配/GC摘要（低频）、本地NPF/TUN/socket drop、队列年龄/占用、F/R/control、FEC实际k/r和profile/revision。
- 一条代表失败/健康场景做短期CPU栈采样：Windows ETW/WPR可用时按Go exe、Rust DLL、Npcap/IP Helper/内核栈归类；Linux perf/pprof按实际可用性。未归因保留unknown。Go pprof本身看不到全部Rust/内核时间；不得拿Go进程CPU等于Go语言CPU或Rust库CPU。采样单独诊断，不把profile开销混入正式性能A/B。
- 首包到达/未到/迟到、10ms交付桶、最长跨业务空洞、TUN就绪到处理的抽样驻留必须能看到；1Hz日志不能证明细粒度无HOL。明细有界，不持久大pcap/业务正文。

## 4. 写完后统一测试：有限矩阵、先容量后极限

### 4.1 一次构建与功能合批

冻结精确Go+Rust+overlay+features+ISA SOURCE，构建Win amd64、Linux amd64和原生ARM64包，manifest/hash复用。先Actions执行编译/core/receipt/平台回归，过后一次全功能批次：Normal off、Fixed最高档、自然Auto、Game2/4 off及最高档；边界功能不需要各自再建一遍包。

定向反例：A1随机控制/parity/source交错及短缓冲/取消/NotSent；A2容量耗尽后恢复；A3半回绕/全回绕及永久缺口；Game坏一个lane不阻断其余；真实Wintun部分完成/Stop；稀疏与高PPS Auto到期债务可回落。自然Auto必须有真实线路质量驱动的revision变化与实际Applied，操作员强制revision只算独立功能证据。

### 4.2 性能单Action单场景，不在同VM并行施压

每个测量Action只一个配置/seed/预声明波形、一个测量job。同源码/旧新比较允许同job顺序A/B，必要时一条反序B/A；独立Action可并行，但共享物理机不能并行占用。复用现有Win→WSL2/Linux真实路径，禁止TCP代理替代raw链路。Linux→Linux是共享模块保护门，不替代Windows资格。

| 组 | 场景与目标 | 执行/停止 |
|---|---|---|
| 基线 | Normal/off双向10M、单程300ms、0%；Fixed最高档和Game4最高档各一个容量可行的代表 | 和同源低延迟校准区分；无损不得产品drop；先确认现有WL-N0不再失败 |
| 常用 | 30/100M近MTU大包为主，附小包；Normal off/最高FEC的实际线路预算分别计算 | 每模式先一个低点，余量足够才更高；不是每种配置跑满笛卡尔积 |
| E1 | 外层每方向500M、单程200ms、IID2%；Normal/off UDP大包为主 | 业务目标扣封装/控制/repair，首轮按现行80%预算；不把500M业务硬塞500M线路 |
| E2 | 单内层TCP应用500M、单程200ms、0损；先单方向、外层能力至少700M | 原有目标带>=475M且真实注入充分；窗口/scale/cwnd校准；不能以多流代替单流 |
| E3 | 外层50M、单程300ms、IID30%；Normal最高FEC | 业务按实际k/r、包型和占线预算算；满16:20 IID源残余参考约0.0228%，目标<1%仅限对应满组/健康主场景 |
| E4 | Game2/4、off/最高档，逻辑3M起步、单程300ms、独立30%与共同burst分开 | 无FEC独立副本p^L：2lane9%、4lane0.81%；不能拿它验共同黑洞，也不能宣称Game2/off<1% |
| 非单调保护 | off 1/5/15/30%代表损伤、0/5与5/0非对称、小包+TCP/UDP混跑、稀疏尾包、低→高→低Auto | 复用已有效样本；极限通过不能推导这些特性自动通过；保留一条故意缺口后其他流继续的反例 |
| MTU | 1280/1400/1500、非对称MSS/cap，边界-1/=/+1，2×MTU和最大合法UDP、长TCP | 低损兼容高损按分片模型；IPv6/DF/ICMP按现有策略，不扩大功能定义 |
| 寿命 | 当前已实现rotation、idle/keepalive/唤醒、单/双向黑洞、Stop | 功能可合批；尚未接线明确UNWIRED，交后续移植，不把它写PASS或无休止阻塞本批性能交付 |

每个高压场景先短校准，不合格则不跑更重同族；低PPS但高编码成本的模式独立判断。基准直连也达不到目标→环境受限；直连有余量而产品单线程满/队列堆积→产品容量问题，不能统称runner差。记录CPU型号、核/quota、Windows/WSL版本、ARM/x86实际ISA、host与注入器成本；WSL vmmem和Linux进程CPU不重复相加。

netem延迟存储按实际外层PPS×单程时间×1.25加control/repair核算。500M、1500B、200ms仅传播就8334包，建议至少10417再加实际额外包；300ms为12500/15625。小包用真实PPS重算，不要求500M纯64B也不使用默认1000队列。TCP500数据本身窗口BDP25MB，测试socket候选64MiB并读回有效窗口；产品fresh队列不能随它扩到25MB。

无损CPU与旧版比较同VM同业务/字节/PPS/MTU/ISA；旧版会崩的高点只能报旧版失败和新版绝对表现，不能拿少发/少收的旧版低CPU当高效率。报CPU-s/GiB offered和delivered、CPU-s/百万record、每端user/kernel、RSS峰值与回落。无损>5%回退是调查线，非噪声一次就定输赢。纯UDP/off有损相对同源无损争取<=15%、>20%定位，FEC/Game按实际处理量归一化，不要求和off同CPU。

off普通一包一record允许`q_app <= p_data + max(0.002,3sqrt(p(1-p)/N))`，无下限；0损必须单独审本地drop。FEC按源包加权实际(k,r_sent)及真实损伤类型算，不因full16参考值去误杀partial小流。p99必须同时报告未到与迟到；跨OS时钟未校准不算单向延迟；网络损伤造成的空洞与软件等待分开。

通过60s容量点后仅补一条约240s持续/回绕/回收代表；不要为每格做五分钟。0损半回绕反例必须覆盖，若VM不够500M则用确定性序号边界组件测试＋最高可行速率长流，不冒充500M实测。

## 5. 收口和后续

交付一个表：修复项/精确SOURCE/实际生效参数/功能与性能run/剩余缺口；源状态沿用M0 cursor，功能变化同步原feature卡和devlog，不新建任务系统。Go是否仍热路径、FFI/包、OS验证/包、分配/包和CPU归因unknown都明确写出。已达目标不为全Rust或零拷贝继续开大工程。

四个结果分别标：FUNCTIONAL_PASS、PERF_PASS_SCOPED、CAPACITY_LIMITED（environment/product分项）、NOT_RUN/UNWIRED/FAIL。修复完成并取得适用证据后再启动上一轮认证/单端口多客户端/生命周期产品补齐；历史80s、物理机和全局GUI/WFP/DNS资格不会被本批自动冲掉。

## 2026-10-28 用户更新：自然 Auto 升降档接受边界（覆盖旧时间门）

本整改包沿用同一个已认证原 Go TLS→Go 冷控制层 FecV2Step→Rust M2 Applied 的 Auto 接线。用户最新明确：**升档迅速即可，升档过渡期间出现业务丢包允许；在持续真实可判定的较好线路条件下，降档 2 分钟以内实际降低一档即可**。此项覆盖本文件/旧 FEC_V2_BALANCED §7 与旧矩阵内要求降档 20s/级、53s 内降档和过渡期极低丢包的冲突性验收硬时限；不把最小20s/级硬门追着产品设置，也不要求一次在2分钟内从 Strong 降到底。

- **升级**：可信真实业务丢包/成熟缺口触发后应尽快提升保护等级，评估周期沿用现行2s、现有升档参考范围4–30s；计量的是确已 **Applied** 的档位和修复包，而不是仅 requested。没有真实受损链路/有效上行压力证据时标 NOT_RUN，不能声称快速升级。升级期间有残余丢包不因此 FAIL；认证、序号、首次交付、非阻塞 fresh、每方向唯一revision、真实性及最终 Stop 仍为硬门。
- **降级**：从稳定可判定的健康、足量成熟 M2/actual-k 观察开始计时，**120秒以内至少实际降低1档并获得同generation有效 Applied 读回**；不是仅降低目标/启动档，更不强制降到底。若被真实 host 压力、数据源不足、未覆盖反馈、censored 等导致 VALID 样本不成立，记录 INVALID_INPUT/INCONCLUSIVE 与最早不足处，不能伪造0loss/512或删除旧 FAIL。原实现保守的10s+4096真实样本候选允许早于120s完成，无需为了“放宽验收”故意放慢。
- **验证**：同 SOURCE 自然业务及有效参数证据优先，先将 Windows 原生 Npcap/Wintun↔Linux WSL/TUN 自然降一级的真实动作和双方UDP/TCP/Stop分开记；升级需有独立真实线路劣化到档位 Applied 的正例。性能仍按一 Action 一场景、同job顺序AB/BA；不可把自然Auto功能回执算成极限容量或CPU通过。任何失败保留原 run/ SOURCE，改参数/夹具须精确留痕。
