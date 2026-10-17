# FEC v2：短块、低延迟、跨平台和可解释自动档

决策日期：2026-10-18。用户明确新 Rust 数据面不需要与旧 Go 数据面互通，并要求性能/真实首次交付优先，不能为节约带宽增加过多延迟或 CPU。本页是**待 M0 登记工作包后实施的新设计**，不是实现或产品 PASS。入口与分工见[工作包](../decisions/M0-fec-v2-workpacks-2026-10-18.md)，验证见[专项测试](FEC_V2_TEST_PLAN.md)。

## 1. 本轮决定与不变要求

采用**一种系统型短块 GF256 RS**，Normal/Game 共用 codec；源包立即发送，修复包在满组或期限到达后生成。保留已经验证的 ISA-L、缺 e 源只解 e 源、方向 owner、共享 Game 编码及有界生命周期。新矩阵/头部/档位不与旧 Go wire 对齐。不实现第二套 RLC、喷泉码、后台择优算法竞赛或默认长块模式。

选择短块而非滑动窗口的原因：RFC 8681 的滑动窗口确能提供更早修复机会，但需要维护跨窗口线性方程与淘汰关系；本轮短块将等待限制到个位毫秒，并限制每次求逆/编码规模，能复用现有 SIMD。没有证据说明额外状态成本值得。若以后仍有明确的 FEC 等待瓶颈，再单独提有界工作包，而不是让本次实现者重新选算法。

继续复用 Go 的 TLS/借站/认证、控制循环、配置/GUI和系统管理。原始包不等组、不等 ACK、不等缺口/其他 lane；同一修复 Seq 复用原密文；必要完整性、账号/地址、epoch/generation、MTU与资源上界不变。正常源包不因 FEC 内存不足而被同步阻塞。旧80秒中断、D10及原023未验门保留原状态。

解除：旧40×20矩阵、固定20源、旧六档、56B头、固定32ms、旧Go字节相等作为**新协议**门。保留：旧代码/向量作为已测参考与回归对象。V1的成功不能证明V2，V2也不必复现V1的字节。

## 2. 工程初值与数学边界

下表是本轮明确的实现初值，不是永远不准改的用户硬门。修改须先指出成本/正确性依据，并更新模型和测试允许带，不能为刷绿暗改。

| 项 | Normal | Game |
|---|---|---|
| 最大源符号 k | 16 | 16，共用内核 |
| 实际 k | 1..16，按满组/期限自然得到 | 同左，不等待各lane齐备 |
| 组关闭期限 T | clamp(SRTT/8, 2ms, 8ms) | clamp(SRTT/16, 1ms, 4ms) |
| 无可信 RTT | 4ms | 2ms |
| 固定档默认 | strong（100%） | strong（100%） |
| 自动档 | 支持，两个逻辑方向独立 | 不支持；明确拒绝而非静默套用 |
| 自动启动 | normal=strong；aggressive=maximum | 不适用 |
| 自动最低档/最高档 | light / maximum；本版不自动进off | 不适用 |

SRTT必须来自可信实际lane观测；不从业务RTT或跨机未校准单程时间猜。Game用可服务lane的最小可信SRTT，慢/失效lane不延长期限。控制快照至多每2s重算一次T；每个新block冻结T，后续源包/RTT变化不续期。计算最大值中的RTT用完整往返，300ms单程等于约600ms RTT。

例如 RTT=10/50/150/600ms，Normal T=2/6.25/8/8ms，Game T=1/3.125/4/4ms。**这是修复组形成期限，不是等待原包的期限，也不是端到端p99承诺**。还要计编码、调度、发送串行化、传输/重排、解码。

块形成时间：`T_fill ≈ (k-1)/lambda_class`，实际关闭 `min(T_fill,T)`。按每方向500Mbps、等长1200B源计算，lambda≈52,083/s，16源约0.288ms满组；10Mbps时lambda≈1,042/s，约14.4ms才能满组，所以会在T之前形成partial。使用**分类后的实际源包率**，不能拿包含parity/四lane副本的外层PPS代入。

用户常用50–100Mbps补充：每方向实际源业务、1200B且同一class时，50Mbps约2.88ms满组，100Mbps约1.44ms；大RTT下通常小于Normal8ms/Game4ms。按平均速率，1200B class需要约18Mbps才能在8ms收齐后续15包，4ms需要36Mbps；这是平均填组阈值，不是随机流保证。若服从Poisson到达，50Mbps在8ms前满组概率约99.99994%，4ms约92.36%；100Mbps在4ms约99.99994%。真实TCP突发/节奏不能假定Poisson，实际k直方图为准。

如果总50Mbps中大包class仅占10Mbps，它仍约14.4ms才满组，会按期限partial；每类按各自字节和包长计算，不能把三class都当50Mbps。Game3Mbps是逻辑业务，不能乘4lane/FEC倍数后声称更快成组。RTT增大最多将T放到既定8/4ms，不为凑满16继续等。50/100Mbps混合包作为常用速率资格，宿主撑不住就明确受限而非删除此工况。

同长满组的编码主项约 `k*r*L` GF乘加；每源字节约r次。相同100%冗余，16:16相对20:20的此主项约少20%，组数约多25%，因此总CPU收益必须实测；不能把它直接宣称为程序节省20%。64:64虽然统计更抗随机丢包，每源字节主项却是16:16的4倍，且形成时间更长，本轮不提供。

## 3. 固定档：明确定义比例，不再借旧名字猜行为

`fec.mode = off | fixed | auto`；`fec.profile`取以下稳定名称。固定档**不根据丢包自动变档**，但k按流量/期限自然变化，r确定性计算。配置、GUI显示“修复包比例”和实际k/r分布，不把比例当成可抵抗的丢包率。

| 名称 | UI | rho=r/k的名义比例 | k=16时 |
|---|---|---:|---:|
| light | 轻度 | 1/8=12.5% | 16:2 |
| mild | 较轻 | 1/4=25% | 16:4 |
| medium | 中度 | 3/8=37.5% | 16:6 |
| balanced | 均衡 | 1/2=50% | 16:8 |
| high | 较强 | 3/4=75% | 16:12 |
| strong | 强 | 1=100% | 16:16 |
| maximum | 很强 | 5/4=125% | 16:20 |

关闭时 `r=ceil(k*rho)`，1≤r≤20；不沿用旧 `min(k,configured_r)`。partial用真实k；全部r行是独立的合法修复行（k=1是明确的重复码特例）。初版不做跨block欠账以省一两个修复包，否则会让某些孤立包没有保护。

稀疏代价必须坦白：k=1时light..strong都会有1个修复包，maximum有2个，源/修复独立丢失时剩余率分别p²/p³；这时名义12.5%并不意味着实际只多12.5%流量。低频包没有凑够一组的机会，既要求快速保护又要求极低百分比冗余不可能同时满足。k=1直接重复受保护符号，不做矩阵求逆；复用明文引用，lane加密/PN仍独立。

不静默把旧`20:4`映射成某个新档：迁移工具可提示邻近比例及差异，用户保存时形成新显式值；导入旧配置需要可见的migration回执。旧`20:20`迁到strong是100%名义比例迁移，**不是相同恢复概率的承诺**。本轮没有旧网络互通需求，不搭一套双协议生产热路径。

## 4. 理论损失、延迟与内存的计算口径

系统型MDS、源/修复符号独立同分布丢失概率p、所有可用符号在期限内到达时，一个原始源符号未恢复概率：

`q(k,r,p) = p * P[Binomial(k+r-1,p) >= r]`。

这不是“整组失败率”，也不是`p-r/(k+r)`。它不包含外层重传、应用重传、相关突发、网络容量不足或碎片重组影响。实际partial分布按**源符号数量**加权：`q_mix = sum(k*N_k*q(k,r(k),p))/sum(k*N_k)`，不得平均各block百分比。

以满组16、纯IID为例（百分数）：

| 线路p | 最小满足q≤0.1%的固定档 | r | q |
|---:|---|---:|---:|
| 1% | light | 2 | 0.012309% |
| 3% | mild | 4 | 0.006560% |
| 5% | mild | 4 | 0.066180% |
| 10% | balanced | 8 | 0.012298% |
| 15% | high | 12 | 0.003682% |
| 20% | high | 12 | 0.069130% |
| 25% | strong | 16 | 0.032541% |
| 30% | maximum | 20 | 0.022826% |

这是**无安全余量/滞回的静态理论参考**，不是自动档必须逐秒照抄的曲线，更不是强制产品零丢包门。k=8、p=5%时mild约0.3561%，需medium约0.05752%；k=1、p=20%最高2修复仍约0.8%，此时报告`target_unattainable_at_latency_budget`，不延长T、不加到十几个副本、不阻塞新包。

Game n条独立同质lane复制**相同源/修复符号并联合接收**，理想有效符号丢失`p_eff=p^n`后代入q；不是先算每lane q再简单取q^n。共路径相关丢失必须用实际联合trace；完全相关时仍是p。丢失持续超过T的整组可能全失，不能用IID表要求50/200ms黑洞必恢复。

资源：每方向TX最多3个open class（256/512/MTU，按LINK输入含Game包络的长度分类，编码L取实际最大长度+2而非class容量）。每方向pending FEC源+parity初始2MiB；RX heavy初始16MiB/逻辑tunnel方向，server全局初始128MiB共享上限，不能给每client都实分配满额。计入正在codec/driver借用及输出拼接峰值，不只算表内引用。500Mbps源流单是保留0.5s就约31.25MB，因此16MiB必然可能先压力退役；这是有意有界，不宣称高压下仍有完整恢复窗口。

RX绝对horizon初值 `clamp(2*SRTT+4*T, 250ms, 2s)`，first_seen起算，不能由重复包续命；内存压力可更早退役。这只约束辅助恢复存储，不是交付等待时间。compact沿用按PPS/恢复寿命计算的有界位图/retired floor；迟到首次systematic仍可交付，迟到parity不复活heavy。不能用一个最高blockID跨三class强退其他仍合法短龄组。

## 5. 编码矩阵、短包、输出与缓存

协议标识`fec_v2_rs16`：GF(256)多项式0x11d；k=2..16，r=1..20；源行为单位阵，parity系数固定为：

`x_i=i (0..19), y_j=32+j (0..15), C[i,j]= y_j / (x_i XOR y_j)`，除法在GF256。

两集合不相交，这是Cauchy矩阵的非零列缩放；任意方形子矩阵非奇异，配系统行可恢复不超过r个总擦除。第0行系数全1，专门XOR快路；k取前k列，不依赖配置档r。k=1明确定义所有parity行系数1的重复码，保持同一包头/生命周期，不能套一般矩阵后错误地直接复制。无需每block重造Vandermonde或求归一矩阵。小k枚举、随机缺失以及跨后端golden必须验证实现。

解码继续只恢复缺的e源，用e×e逆与直接输出系数；没有新可解信息不重复求逆。e=0返回；首行可解e=1时用XOR。RX输出长度由受保护长度字段恢复后校验，不能依赖已丢失source的外部长度数组。

encoding tables按(k,first_row,row_count)有界缓存/预生成，复用ISA-L官方table格式；所有16×20系数表最大约`32*20*sum(1..16)=87,040B`，可每进程只读共享。decode表按(k,missing_mask,selected_parity_mask,scheme)缓存，初始每owner64项并计入内存；不同group实际L不改矩阵key。

输入pool预留2B受保护长度前缀和发送headroom；初始化/复用时仅将本次数学读取的尾部清零，不读dirty capacity。相等长度源直接借用，混合长度尽量一次写入owned FEC存储；不能每次4行计算都复制整组。编码直接写最终parity输出的body区，再填头，避免Vec<Vec>中间结果再封包。source输出与FEC持有引用的所有权分开，不能为省复制提前归池。

单次codec job初始最多4个输出行或64KiB GF输入遍历量（二者较小，最少1行）；每轮归还owner调度。这个上限不是要求每4行分配一次表/Vec。测到连续codec服务时间超过100us时定位实际调用/宿主抢占；不默认建线程池，不忙轮询。`L<64`首版scalar/XOR，≥64经验证后端；短尾与未对齐由wrapper按**该目标函数实际要求**处理，不能把一个架构的长度限制套全部。

1ms等期限是单调时钟上的目标；Windows/Linux均用现有可唤醒owner的有界timer能力并量实际lateness，不能假装OS永不调度延迟，也不能忙等烧CPU或无回滚地更改全系统timer设置。若目标平台粒度达不到，记录实际值与影响并修平台等待点，不能只在mock时钟证明低延迟。

## 6. 新wire：一次协商，无旧格式嗅探

继续原V4一次受TLS保护的admission；由M0分配`fec_v2_rs16`能力位（当前bit2空闲，可用bit2，合入前核实时表），纳入原认证/KDF上下文。不增加往返。新模式要求两端支持，旧端明确unsupported；不能fallback后UI仍显示V2。能力、认证模式fixed/off/auto、方向政策由原控制面绑定，多客户端独立。每次切档只改变新block的r，接收端按自描述block解码，不逐块请求确认。

record AEAD/HP/PN不在本轮更换。由M0在kind表分配`FEC2_SOURCE`和`FEC2_REPAIR`，禁止在LINK payload中靠WF前缀猜。普通off继续原DATA短路径，不创建FEC状态。新的FEC源也不需要为WF前缀escape；现有LINK分片格式与WBDLFRG1 escape仍保留，本轮不同时重写分片协议。

所有整数大端，逐字段编码，不dump struct。block_id使用u64，同tunnel_epoch/方向内跨size class唯一且单调，分配在首source到来；不复用、不回绕。Game各lane复制同一逻辑block/source/row，验证各自AEAD后联合处理。

| frame | 字段 | FEC专属长度 |
|---|---|---:|
| SOURCE | block_id:u64, source_index:u8, flags:u8=0, 原LINK frame | 10B + 原frame |
| REPAIR | block_id:u64, parity_row:u8, actual_k:u8, symbol_len:u16, parity body | 12B + symbol_len |

数学源符号是`original_len:u16 || original_frame || zero_tail`，L=max(original_len)+2。SOURCE长度从认证后的record payload长度减10推导，在本地构造受保护长度前缀；未发送补零。REPAIR body包含对长度前缀的编码。每份repair独立带actual_k/L；row∈0..19，不需要知道总r才恢复。source index∈0..15。source立即首次交付，不等待repair/k；之后repair宣布k/L时必须与已有source范围/长度一致，否则记malformed，不能修正已经交付的数据。

FEC开启时`max_original_frame = record_payload_budget - 14`，因为最大repair是12+2+N；source虽然只加10也预留这个4B差额。偏移/length检查完整，Game16B和LINK分片头仍各只扣一次。auto从off切on不改TUN/MSS包络；fixed/off可用更大预算。极小路径/MTU变化继续06的合法拒绝和兼容分片规则，不能把大包拆片成本藏进FEC收益。

相比V1，源头56→10B，最大parity固定额外56→14B（含受保护长度2B）。隔离头部差异、同为实际k=16/r=16/源1200B时，仅FEC层40,192→38,784B，少1,408B（约3.50%）；源64B时3,840→2,432B，少约36.67%。这不包含外层头、不等于CPU下降，更不包含更换k后的变化。比较报文大小用`sum(source_len+header)+r*(max_len+repair_header)`，再加真实record/IP/TCP与Game，而非只报头减少百分比。

## 7. 自动档：低频决策、按实际k、快速升档和克制降档

只有一个决策者：继续**Go冷控制层**，Rust提供事实快照并应用`SetTxFec(profile,revision)`；不要Go/Rust各自调档。Normal两方向各自控制，server不同client互不污染。fixed/off没有自动探针/控制器；原GUI被动质量显示和必要keepalive仍可工作，control/parity不刷新payload idle。

### 7.1 输入与不确定性（先冻结，再接线）

每方向复用现有receipt/quality与TX实际完成信息，低频提供：首次成功提交source数/字节、实际k直方图、缺源恢复/未恢复/晚到、修复首发及时率、outer repair demand、receipt覆盖/新鲜度、reorder、local/kernel drop与queue age。指标以source为单位而非原始IP大包或包含parity的PPS。分类/位图已有owner中更新，普通逐包不做map/日志/全局锁/IPC。

**真实物理首发丢包率不能从最终receipt或FEC恢复率精确反推**：相同密文重传、反馈自身丢失、预留未发PN、乱序和完整丢组都会造成偏差。控制输入命名为`loss_need_estimate`并带validity，而不是谎报wire_loss。使用成熟的已认证receipt缺口/实际first-send状态与RX pre-FEC缺源交叉估计；同PN只计一次，unsent/uncertain、反馈不覆盖、全组消失不可见不能算成功或零loss。outer repair demand是补充风险量，不能和FEC恢复简单相加重复计损失。

M0/M2冻结最小统计语义：有效样本须有成功first-send及成熟的观察覆盖；反馈仅丢失的窗口标UNKNOWN；已修复且无法判断首发的样本标censored，单列而非硬塞0/1。RX有最终k的可见组可估缺源，但必须报告可见组覆盖偏差。仅当覆盖足够、没有显著本机drop、能合理对照这些量时标VALID；其余保持档位，输出不确定原因，不能逼实现者用一个伪精确p驱动公式。

M0冻结时先采用可检查的观察门初值：成功提交源的成熟反馈覆盖≥90%，未知/删失占比≤20%，无未解释的分母跳变；达不到就只作辅助风险量，不输出精确线路p。有效比例过低持续不降档可能是**观测设计缺口**，不能无限挂UNKNOWN当完成；A01/A03正常容量下必须能形成有效估计并收敛。若既有机制只能稳定估“经过外层修复后的有效损失需求”，明确标该口径并按实际恢复时效校准，不能将其宣称真实物理丢包率。需要修改观察门时留误差/覆盖证据。

优先复用已有报告，不另建可靠控制流或逐包时间戳。若现有摘要无法消除“整组全失被忽略”的分母偏差，M0一次增加**低频累计已发送source计数/逻辑范围摘要**到既有质量TLV，并在专项中验证乱序/窗口/重传口径；不为每个block额外发送长度表。窗口不能配准就UNKNOWN。loss_need的有限偏差用同Actions已知损伤trace校准，注入真值只给分析器，不可喂给生产控制器。

### 7.2 决策规则（纯函数/可回放，不逐包算二项分布）

1. 活跃时至多每2s评价，复用当前合并/变化抑制的quality传输；本地2s GUI刷新不要求每2s固定wire包。休眠停报告，无业务不造样本。报告缺失不等于线路100%丢失。
2. 有效快窗2s、慢窗8s；升档至少512个有效源样本。样本不足保持启动/上次档；存在≥2个可信业务缺失/晚恢复事件时可每10s至多升一级，不能每个稀疏丢包一路顶满。
3. `p_design = min(1, max(p_fast,p_slow) + min(0.005,1.64*sqrt(p_slow*(1-p_slow)/N_slow)))`。0.005是绝对0.5个百分点的**工程余量上限**，不是统计置信区间保证；N/validity仍需足够。trace校准发现系统性偏差要修观测，不能不断加余量掩盖。
4. 以近8s实际source加权k分布计算每档q_mix，选择达到`epsilon=0.001`的最低档。状态只存7档、16个k桶和窗口累计量；二项结果可预计算小表/启动时生成，运行每2s至多7×16查表。只为观测到的k分布建模，不假装每组16。
5. 普通auto的期望档为上述档；aggressive在它上面加**一个固定档**，最多maximum，不同时再加一轮p或epsilon惩罚。初始strong/maximum；允许显式`fec.auto_start_profile`，aggressive在配置启动档上加一档；数据充分后按规则降。
6. 可信IID需求升高连续2个有效快窗可直接升到计算档，不逐级等待很久；可信突发指标（成熟缺口连续≥3个源，且窗口≥512样本）允许临时再高一档，aggressive与突发加档取max，不叠加。突发加档最多保持10s，未再出现则撤销；不能承诺遮住长黑洞。
7. 降档：候选低一级在p_design下q_mix≤epsilon/2，持续至少10s、累计≥4096有效源且没有新的突发/容量异常，每10s最多降一级。因此从初始strong到light通常几十秒，测试要有足够稳态，不以20s内必须最低档刷绿。aggressive降至其目标上一档时停止。
8. 报告过期`>max(6s,3*SRTT)`、censored占比高、local/kernel drop或明显queue增长：冻结上次可信档，不把host容量问题误判线路损失并加parity；可按既有容量策略丢过期辅助状态，不能损坏fresh。持续真实黑洞由原lifecycle处理，不靠FEC无限升档救。
9. 最高档仍无法达到epsilon，报告预计残余、实际partial和`target_unattainable`，维持上限和无HOL，允许业务/应用重传承担残余。不延长T去追统计门，不强制自动off，也不把125%改成无限冗余。

目标0.1%是选档参考而非全部网络硬性验收；高损/突发/稀疏/容量受限允许有解释的残余。为防“自动但长期过强”，有效平稳且可达的场景在收敛后普通档通常不超过理论最低+1，aggressive不超过普通目标+1；T/partial、余量、降档滞回导致差别必须输出，不能强求一条唯一时间曲线。

## 8. 调度、恢复与失败行为

source first-ready即交发送调度；pending parity按最老deadline公平轮转class，不一直fresh drain导致parity永远没机会。首发parity不占10%**外层重传**预算，但source+parity+Game副本+repair都占真实链路容量，必须统一计账。没有无限带宽的假设。

codec/发送拥塞时，过期parity明确丢弃并计expired/host_capacity；不堆长队列。初始parity queue有效年龄`max(2*T,10ms)`，超过后停止为这个block制造更多parity，放行fresh并标本组实际r_sent；它不是线上的传输超时。pending2MiB上限优先退最老辅助作业，持有driver loan的内存不得强回收。首次parity健康额外排队p99工程目标≤1ms，高于则定位容量/调度，不拉长T隐藏。

FEC保留内存不足时取消该组辅助编码/释放其可释放引用，原source仍按FEC2_SOURCE的合法标识尝试首发，记录本组实际r_sent=0/不足；不偷偷换回旧wire或让fixed模式接收端猜裸包。RX无heavy额度仍校验并首次交付合法source，保留有界去重；失败的是恢复机会，不是整条连接。若连正常业务arena/driver容量都不足，返回明确NoCapacity/计drop，不能承诺无条件吞下所有输入，更不能阻塞等待FEC空间。

outer重传仍最多两次/大流量约10%/稀疏绝对上限，不为本轮改变RACK或把FEC包全部禁止修复。已有repair预算对象和固定密文身份保持；测试分别报告FEC单独、组合恢复结果，不能把总丢包改善全部归给FEC。k=1的parity是FEC首发，不是“无限稀疏重传”。

## 9. 跨平台实施

首选复用已固定ISA-L v2.31.1 SOURCE `c387163fcbca62701d646149564c550c78a4f985`及现有safe FFI。该版上游包含AArch64 NEON和Windows nmake，不需要因为当前项目wrapper只开Linux x64就另造算法。构建支持存在不等于目标原生测试已通过。

| 目标 | 本轮要求 |
|---|---|
| Linux x86_64 | ISA-L runtime dispatch，功能与同机性能 |
| Linux aarch64 | 接上游NEON，原生runner执行功能；可用时同机性能 |
| Windows x86_64 | 上游Win64 ABI/汇编构建，原生runner执行codec与Go桥接加载；驱动可用性另记 |
| 无SIMD/未来平台 | 正确scalar/XOR fallback；显示后端，不能冒充加速已通过 |

M0掌握共享workflow/根依赖/FFI构建清单；M3掌握codec调用与等价向量；M4掌握目标打包/加载与配置接入。Native对象不使用构建VM的`-march=native`生成所谓portable包；不把Linux ELF静态对象拿到Windows。source/lock/compiler/target/features/hash齐全，QEMU或cross-build只证明对应范围。

## 10. 配置、开工与停止条件

新参数进入既有唯一参数目录，不另造第二份目录：`fec.mode`、`fec.profile`、`fec.auto_policy=normal|aggressive`、`fec.auto_start_profile`。k上限、T公式、cache/内存/后端是effective诊断值，首版不全部暴露GUI。server每client接受独立mode/profile/auto/cipher，上下行auto各自决定；fixed双向按客户端明确政策生效。Game拒绝auto。revision只在新block应用，旧block不用新r重解释。

GUI显示设置档、实际发送档、上下行估计与unknown/stale、后端、应用中/拒绝原因；不只加一个下拉框。有限startup padding、idle/keepalive/DNS/分流/IPv6等原配置语义不改。

实施不是先补完一切旧FEC全链路再开V2。已冻结M3-016及现有Normal/off基线足够保留参考；旧FEC可用同机codec/调度夹具对比，旧全链路没接好就诚实NOT_RUN，不为兼容基线新造生产双栈。M0先收尾当前安全批次，冻结新公共契约后M3/M1/M4并行；M2仅最小统计缺口需要时介入，不重做恢复算法。

达到工作包done_when即收口；没有新的证据不比较RLC/RaptorQ/64/128大块，不追求跨CPU通用“最快”。对任何性能阈值提出计算反例是正当工程工作，需留痕调整而非强行优化到错误指标。

## 原始参考

- [ISA-L v2.31.1 erasure_code API](https://github.com/intel/isa-l/blob/v2.31.1/include/erasure_code.h)：给定矩阵与table接口，复用计算内核。
- [同版 ARM64 dispatch](https://github.com/intel/isa-l/blob/v2.31.1/erasure_code/aarch64/ec_multibinary_arm.S)、[NEON内核](https://github.com/intel/isa-l/blob/v2.31.1/erasure_code/aarch64/gf_vect_dot_prod_neon.S)、[Windows构建入口](https://github.com/intel/isa-l/blob/v2.31.1/Makefile.nmake)。
- [RFC 8681](https://www.rfc-editor.org/rfc/rfc8681.html)：滑动窗口的时延机会与方程状态；本轮不实施该wire或算法。
- [klauspost/reedsolomon](https://github.com/klauspost/reedsolomon)：跨平台SIMD、缓存、短块实践参考，不因此引入Go逐包编码调用。

上述数学、参数选择和wire是本项目新设计；外部资料不证明本项目实现或性能。
