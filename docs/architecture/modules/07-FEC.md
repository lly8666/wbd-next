# 07 FEC编码、缺源解码与生命周期

> **2026-10-18覆盖说明**：以下是已实现/已测V1的参考规格，不能再据此新开旧兼容任务。新工作包采用[FEC_V2_BALANCED](../FEC_V2_BALANCED.md)和[专项测试](../FEC_V2_TEST_PLAN.md)：k≤16、新Cauchy/10B源头/12B修复头、比例档、短期限与Go自动策略；旧矩阵/20源/56B/32ms/Go字节相等均不约束V2。ISA-L、缺e只解e、首到/有界/所有权经验保留。M0按[工作包](../../decisions/M0-fec-v2-workpacks-2026-10-18.md)统一分配，冻结016及历史证据不重写。

## 确定算法

GF(256)多项式0x11d；旧generator为Vandermonde行x=r+1，经前20行矩阵逆归一成systematic：`G = V × inverse(V[0..20])`，G尺寸40×20。**不能直接用ISA-L默认RS/Cauchy生成器替换**。R0从旧Go生成固定G/golden，Rust标量复算逐字节一致；其后ISA-L只做给定系数的矩阵乘。

TX每逻辑方向只有一套encoder，Normal一套、Game也是一套。固定20:4/8/10/12/16/20；20:20按原256/512/MTU三个size class，低档保持单组策略。一个class一个open block，各class共享方向BlockID分配器，BlockID在首次source到来分配，不能在flush时导致顺序倒置/冲突。

## TX状态机

`Empty → Open(first_at,profile,budget) → Closed(parity_pending) → Done`。

1. source到来先检查当前block的profile/budget兼容性，不兼容先关闭旧block，source入新block。
2. 留一份owned明文用于编码，立刻输出streaming systematic；设置原56B头flags=1，DataCount占位20、只本source长度有效、ShardSize为本source长度。
3. 第一包就设`deadline=first_at+32ms`，后到包不续期；满20立即关闭。系统性包不能因等待parity metadata而延迟。
4. 关闭时得到active k与真实最大L，r_sent=min(k,configured_r)，输出parity index=20..20+r_sent−1；**头部ParityCount仍是配置档r，不是r_sent**。final header的DataCount/lengths才具有全block权威。
5. 先让已ready systematic有一次发送机会，再处理ParityJob。parity封装完尽快发送，不为了“32ms延后”强行睡到32ms；32ms是稀疏block的最迟关闭基准，不是所有parity固定延迟。

长度从短到长时，只对每个active source `[original_len,L)`提供确定零字节；未使用的20−k列完全不读。短block也不得把池的旧数据当零。partial table按原G的前k列生成，tables缓存按(k,configured_r)有界。

首次parity不是08所限10%的外层重传。持续20:20时，同长满block的parity payload产出约等于source payload，不能只保证“偶尔给一次parity机会”；实际wire份额还须按最大shard长、partial k和头部计账。R3接入真实调度时核parity产出/实际首发/pressure及最老待发年龄，健康容量下不得持续积压。源包立即发送、32ms关闭上界与parity不饥饿须同时成立；过载则明确退化，不扩大队列掩盖。

## SIMD调用

wrapper唯一不安全边界：验证input/output长度、不可别名、pointer数组大小、k/r、scratch有效期；`ec_init_tables(k,r_sent,coeff,tables)`后`ec_encode_data(L,k,r_sent,...)`。len<64统一走简洁scalar参考，len≥64使用经目标测试的runtime dispatch；不要把各低级函数32/64要求混为一谈。SIMD tail按官方函数能力/已测wrapper处理，不把padding传到wire。

正常首次实现fused整行批次，不逐source×parity从Rust调用C几百次。若单call在目标机超过100µs服务预算，先按output rows分成最多4行/次的增量job，轮间归还调度机会；只有实测仍不足再用有界codec worker。禁止默认每block创建线程/async任务。

## RX状态

`Absent → Heavy{streaming, final?} → Compact → Expired`。key=(tunnel_epoch,direction,BlockIdExt)，profile属key冲突检查，不允许同ID不同profile创建两份互不相认的状态。

收到合法streaming source后：验证本长度/索引/profile→与已知final核对→若首次则立即输出其业务frame→同时保留一个owned原始shard用于可能恢复。首到交付不等block完整。parity到来提供final metadata；所有已存source索引/长度须一致，否则Malformed，不能修正已交付的内容后继续装正常。

拥有final后将inactive columns k..19视作权威零；实际可恢复条件为`missing_active <= available_distinct_parity`。没有final的streaming长度不能自己猜k/零尾；暂不可恢复但不影响已到systematic交付。

## 只解缺的e个源包

取缺源列集合U（大小e），已知源K，选择e个可用parity行P（固定按index小到大，结果确定）。`M=G[P,U]`。由 `yP=G[P,K]xK + MxU` 得：

`xU = inverse(M)yP XOR inverse(M)G[P,K]xK`。

构造e×k直接输出系数D，输入数组为已知源+所选parity，调用一次fused核直接生成缺源，不先分配每行residual大buffer。求逆从固定20×20降为e×e；e=0立即结束，e=1仅GF逆与乘系数。所有输出与输入不别名，恢复后按原长度截取并首次交付。

最多64份decode table/owner，key包含active k、configured r、缺源mask、选中parity mask、generator版本。clock/近似LRU即可，不在每包做复杂LRU链表。每份表上限32×20×20=12,800B，64份约0.78MiB加metadata。任何非满秩反例明确失败并保留输入摘要，不能改用错误矩阵“凑结果”。

## Heavy/compact资源

初始3s绝对恢复horizon从first_seen计，收到重复包不续命。完成全部active originals或压力/到期即释放大payload，compact仅保留BlockID、profile、final lengths和delivered bitmap。迟到未交付systematic在compact有效期内仍首次交付；late parity不会重建heavy。已交付源永不因为pressure复活而重交。

heavy以字节预算为主，不固定64代/640块。compact初值10s保留并按实际block速率动态容量，受总内存限制；无法保留时推进明确retired floor，过旧ID拒绝，不当新block。wire32用最近可信extended ID解释，超过半空间不猜。profile切换保留原最多6个draining TX encoder的限制；满时先有界flush最旧，不阻塞新source等待peer。

退役只释放该block的引用；已经交下游、正在解码或被driver借用的buffer须按03独立存活，不能compact时把已首到输出的内存归池重用。切档只影响新TX block，RX按认证后的block metadata解释旧r/k，不拿当前发送档改写旧block；auto当前off仍接受合法旧FEC drain，fixed/off仍按协商模式分派。lane record、FEC源索引、LINK packet与Game logical ID分别去重，不能一层bitmap替代全部层级。

## 测试与指标

所有k1..20×配置档、L1/15/31/32/63/64/65/MTU、各种e、scalar/ISA/旧Go一致；已知零尾dirty poison、parity先到、source立刻交付、metadata冲突、同ID换profile、3s无ID前进、late systematic、全部duplicate。小k枚举全部丢包集合，k20抽样各e并固定seed；SIMD/ISA声明与实际运行target一致。

记录encode/decode cycles或CPU-ns/source-byte、e分布、matrix cache hit、job最大连续CPU、source首次发送延迟、flush lateness、partial(k,r)分布、heavy/compact bytes。FEC带宽/CPU改善必须在同机真实路径复验，micro速度不替代业务p99。

参考：[ISA-L给定系数接口](https://github.com/intel/isa-l/blob/v2.32.0/include/erasure_code.h)、旧 `fec/{fec,fastblock_encoder,block,size_class_encoder}.go`。e维求逆是本方案基于旧矩阵的代数化简，须用旧实现作为独立oracle。
