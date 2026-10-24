# TLS 正文复用：理想化成本与真实外观验收

状态：计划，**NOT_RUN**。架构见[SELECTIVE_TLS_CRYPTO_EXPERIMENT](../architecture/SELECTIVE_TLS_CRYPTO_EXPERIMENT.md)。机器可读参数见[矩阵](selective-crypto-matrix.json)，它不是可直接投递到旧network-harness的请求。

## 0. 不扩散的执行顺序

1. S0：协议模型/功能向量 + 只编译一次的原生实验工具。
2. S1：同VM原语与完整record成本；并行一个小规模外观反例，不等满速调优后才看泄漏。
3. S2：只在有足够收益时，接入既有真实Go→Rust→raw/TUN，测Normal/FEC OFF整机成本。
4. S3：复用S2产物，独立有界抓包验证真实握手/稳态/结束及重复特征。S1外观反例若失败，最多补一份真实路径确认即可结算，不自动进入大矩阵。
5. 给出PERF与APPEARANCE分别的结果；实验无收益或外观退化是有效完成，不需要硬修成可发布功能。

每个性能Action只含一个架构/suite/负载/损伤场景、一个测量job。A/A-layout/B在该job顺序运行；不同场景可用独立Actions并行。建产物可用多平台job，但不能用它们跨VM比较CPU。

## 1. 冻结、复用和测试资源

- 原生ARM64优先，另一个x86_64代表；共同源码/依赖/LTO/优化级别。将SOURCE、Cargo.lock、rustc、Go、CPU型号/flags、内核、核数、内存/cgroup、实际native/scalar后端写入manifest。
- A/A-layout/B优先由同一个实验二进制选择，A直接调用未改的生产record实现。集成路径也固定同一公共源码，仅模式改变。原始父版本产物作为补充，不把非同源数据当算法收益。
- builder先产binary与manifest/hash；测量Action下载并逐项校验，不现场反复编译。原有ARM builder和`tools/arm64_public_go_rust_bundle.sh`复用，不另建通用部署系统。
- 新工具计划路径 `tools/selective_crypto/`、实验源码模块见架构；workflow可独立命名`selective-crypto-build.yml`/`selective-crypto-measure.yml`/`selective-crypto-capture.yml`，实现时才创建。逐场景请求位于`tests/network/selective-crypto-work/`，不覆盖上游request。
- workflow并发key始终含branch、SOURCE和request；不同提交不共用队列key。默认不取消正在运行的测量，不重复同一请求。手动指定target_arch，不能新分支误落amd64却下载ARM产物。
- 新分支复用network harness时必须显式接线其冻结产物下载/架构逻辑；旧实现有按分支名匹配的FEC特例，不能仅换分支就认为可用。下载故障与运行失败分开，不连续刷相同503。
- 上游已发现测试veth ARP/NUD被netem损伤会造成伪黑洞。沿用仅对owned namespace/veth预置邻居的测试修复，记录真实ARP/NUD，不改宿主网卡/全局网络。

## 2. S0：一批便宜且有意义的功能验证

覆盖AES-128-GCM、AES-256-GCM、ChaCha20-Poly1305；实际公开产品尚未接线的suite先限工具测量，不宣称CLI/GUI已经支持。

在Actions合批验证：

- FULL/SELECTIVE逐字节还原；0/1/512/近MTU/边界长度；H=40/52/最大TCP+IP选项及256边界；B小于阈值回FULL。
- 内层TLS真实记录跨TCP包、同包跨多记录、头部部分跨包、握手/alert/close、ACK-only、非TLS、IP分片/超MTU回FULL或现有兼容路径。不能把随机字节伪造为真实TLS证据。
- descriptor、PN、外头、B、C、tag每类篡改各一例；跨代/方向/suite错钥；失败不得交付或推进可信状态。
- 第N包损失/迟到，N+1马上可交付；不等待TLS记录完整；受保护小UDP/另一TCP持续交付。oracle缺失或容量不足直接FULL，不丢源包。
- 重传使用同一FrozenRecord全部原字节、PN/Seq/tag一致；禁止对同PN重seal。候选新包不复用内层TLS密钥做外层认证。
- 两端实验版本不匹配拒绝建实验数据通道；不会默默回落到错误解码器；生产default仍是原record。
- MTU1500/1400/1280的实际头长预算；恰好MTU、+1、原超MTU兼容测试。初版normal/FEC off，不能改变FEC2预算。
- Stop取消、缓冲回收、稀疏首包、未知模式与长度越界；复用已有检查，不造一套安全系统。

只有上述通过才生成可测产物。纯bench和模型不冒充原生收发通过。

## 3. S1：理想化成本测量

先跑主场景：ARM64、AES-128-GCM、近共同MTU、长TLS流、已知oracle，测seal和open分别及合计。ChaCha做第二场，x86/AES做第三场；AES256是便宜功能必测，性能按AES128结果有价值再补一个场景。

输入使用由本地真实TLS会话生成的已加密记录语料；oracle区分握手/密文/关闭。计时前准备工作区，定时区只包含实际record seal/open、HP、重排/复制与必要元数据读取。原语-only和完整record两种统计清楚分开，不把“少算了一项”叫提速。

每个leg独立密钥/nonce域；不能循环把同一PN和相同key用来seal。可以重复读有界输入语料测CPU，但这样的重复语料**不能用于外观验收**。校验输出使用抽样/测量外校验，避免计时器每包取时或完整hash主导测试；使用优化屏障防止消除。

同job顺序 `A → A-layout → B → B → A-layout → A`，每leg预热2秒、测量15秒，初始只做这一组；差异落在噪声区不反复刷seed。端到端另用A/B/B/A。记录各leg的线程/进程CPU ns、wall ns、payload/wire字节、seal/open失败、分配次数/字节及新增copy bytes。分配计数工具会扰动时，另开功能测量，不把instrumented数字和普通CPU直接比。

报告：cycles或CPU ns/packet、CPU ns/inner byte、AEAD-only与完整record比例、eligible bytes/packets、fallback原因、吞吐、CPU-s/GiB。CPU cycles不可用就标NOT_OBSERVED，不用CPU频率猜周期。

工作区与oracle/corpus/RSS分开。初始热语料16MiB，并有同场景一次较大语料64MiB敏感性检查，仅在结论依赖缓存时用；不大于机器合理可用内存，不把数据预生成算成生产分类器零成本证明。

## 4. S2：整机CPU必须以真实首次交付为分母

每端运行真实隧道产品，负载发生器是独立进程。A/A-layout/B沿同一underlay、端口策略、MTU预算、fq600/flow256、FEC OFF。默认隔离外层DATA repair=OFF，使修复行为不污染首轮加密对比；功能成立后补一个ON的正常代表，不能顺便重调V3算法。

先代表性100Mbps总应用负载：每方向50Mbps，30秒预热、60秒稳态、10秒drain，单程25ms/0损。应用按字节：TLS80%、普通TCP10%、UDP10%；短小UDP约1%总业务字节，独立统计交付间隔。近MTU为大流量主项，不把64B PPS压测当500M普通下载。

同VM A/B/B/A，所有leg严格相同随机种子、负载计划与内层包长，真实TLS密钥/记录内容各leg独立。产物核hash，state重置，host有足够恢复时间，禁止并行跑测量进程。generator CPU、product CPU、system/softirq、host busy/PSI/steal分别记。

通过后最多补：

- 单方向500Mbps应用、200ms单程/0损、700Mbps外层。沿原窗口/MTU/实际readback；第二方向仅ACK/控制。容量不足不再增加速率，不缩小有效业务来伪CPU下降。
- 10Mbps总、100ms单程、1%或5%真实损伤的混合业务，重点内层重传和无跨业务HOL；TCP因残余损失自身降速不要求满速，用相同业务交付分母且报告注入不足。
- 稀疏：1pps和20pps TCP/UDP混合。头尾FULL/no timer/no新增周期包，记录idle CPU、唤醒数、首包p99。

重度FEC测试、Game、多客户端大矩阵、Windows接线、真实分类器均不属于本实验首轮。只做一个x86整机代表确认可移植性，不复制所有ARM场景。

指标：产品两端分别及合计CPU-s/GiB唯一交付；RSS peak/steady、分配、copy bytes、TX/RX队列年龄、TUN/raw/socket/qdisc drops、AEAD错误、outer repair字节、app未到率、首次交付p50/p95/p99、每流10ms桶。丢失包单列，不能只对幸存包计算好看的p99。

## 5. S3：抓包验收，不能只看Wireshark标签

性能和抓包分开运行，避免pcap/分析本身拖高CPU。流量采用同一套真实本地TLS服务：长下载、短网页样式、两个TLS源切换、非TLS/UDP混合；不依赖公网上网站当测速源。复用现有外层真实TLS/bootstrap。测试证书和域名是fixture时明确标注，不能写成真实www.cisco.com证书资格；若复验借站流程，沿现有授权路径，不导出任何密钥或真实业务正文。

比较三个对象：A完整加密隧道、B候选隧道、普通HTTPS参考。普通HTTPS只帮助发现差异，不能要求本身有序的TCP与本项目高损无HOL行为完全一致。

抓包最低范围：外层建连、连续业务、内层握手/关闭、跨TLS记录边界、强制一次内层TCP重传和外层一次重传（分别归因）。用一个预声明波形完成每Action的一个外观场景，速率10Mbps、最长30秒即可；不抓500M长流。

在受控owned接口抓取，两端分别标明TX/RX、offload状态、截断与捕获丢包。最多32MiB原始pcap/端，合计64MiB，仅留临时目录；达到上限结束抓取并将coverage标PARTIAL。先解析并出摘要/hash，再在finally清理owned原始文件；成功失败都保留摘要、计数、时间窗口、工具版本、异常偏移的无正文说明，不上传大pcap、keylog或内层payload。

分析项与判定：

|维度|实际检查|不能怎样判|
|---|---|---|
|握手|外层SNI/ALPN、TLS版本、suite及既有证书流程没有被候选改写；证书若不可见用端点收据|不把抓不到加密证书当失败，不把域名=真实服务端IP|
|记录结构|外头type/version/length、MTU、正常流连续记录解析、无明文mode/magic|不扫0x17寻找随机假边界；丢包缺口标不可重组|
|内部信息|预声明的内层SNI/DNS/HTTP canary、私网地址头组合不出现在外层可见正文|无命中只能证明样本，不保证所有网站不可识别|
|重传|同外层Seq范围重发内容一致；新PN不复用nonce|普通TCP重传/两端重复抓同包不算候选新增重复|
|重复正文|重组/去除同Seq重复后，在不同外层Seq区间搜索连续64/128B相同片段；用oracle内层seq映射确认|熵高、偶然匹配或少抓数据均不能抹掉确认反例|
|包长/时序|共同包型下A/B长度差应符合明确2B开销；方向、burst、固定周期、fallback切换的分布|不要求小样本统计完全相同，也不靠KS单一p值判隐身|
|无HOL|由应用每流收据证明后包及时交付，旁观TCP重组等待不算应用HOL|Wireshark重组延迟不是产品交付时延|

必须包含可检出性对照：人为放入一个应被检出的canary样本，离线扫描器能报；人为在两个新外层位置复用同一TLS密文，重复检测能报。对照只在测试构造器执行，不发布到公网。

若 B 的真实内层重传产生不同外层位置的大段相同正文，记录 `APPEARANCE_REGRESSION_REPEATED_INNER_CIPHERTEXT`。这是预期可能出现的设计失败，不能只把重传包改成FULL就假设解决：重分段/重复范围也要验证；首轮不自动扩展成一个重传识别缓存系统。

## 6. 有限验收与停止规则

以下是工程决策带，不是协议数学定理；发现不合理可给证据修改，但不能悄悄放宽硬门。

- 正确性：认证/身份/generation/MTU/逐字节还原/Stop失败为FAIL；受控无损额外缺包或新增跨业务阻塞为FAIL。
- CPU：先看B对A真实净收益。完整record CPU降幅<5%，或差异不超过同机A前后噪声，判NO_CLEAR_BENEFIT并停止扩大。5–10%可只做一次S2代表；>=10%也不是自动值得发布。不要假设端到端收益等于record收益。
- 推进参考：S2两端合计CPU/GiB改善约5%且每端无超过噪声的明显恶化，才值得讨论实际分类器；无收益可正常结束实验。
- 时延：同机同负载B相对A的p99增量初始允许 `max(1ms, A.p99*2%)`，单独保留未到率/10ms连续空洞；超出先定位，不用放慢注入来过门。稀疏首包不能因批处理等待，理想分类器无需等待时间。
- 内存：额外工作区目标<=256KiB/方向；端到端稳定RSS若超过A约4MiB/端须解释是否allocator/trace，不武断按RSS单点否决。退出后所有owned缓冲/资源归还，观察至少一个短重复连接循环；不跑数小时泄漏矩阵。
- 容量：host PSI some持续>20%、单核/产品线程饱和、实际注入不足、队列drop或发生器瓶颈均单列。产品饱和不能自动写成host原因。第一次明确容量受限停止更重负载，保留估算；不要因FEC在150M受限就预判Normal500不能测。
- 外观：可见内层敏感头/canary、确认的新增跨外层序号重复、破坏握手/MTU/同Seq密文一致性为回归。PERF_PASS不覆盖APPEARANCE_FAIL。不宣称“99%不可识别”。

完成一个有资格的结果即可结算：`NO_CLEAR_BENEFIT`、`PERF_BENEFIT_APPEARANCE_REGRESSION`、`IDEAL_BENEFIT_CLASSIFIER_NOT_IMPLEMENTED` 或有精确范围的 `SCOPED_EXPERIMENT_PASS`。生产默认、Windows/真实分类器资格仍单列。

## 7. 留痕契约

状态只写 `docs/evidence/selective-crypto-work/status.json`，日志 `docs/devlog/selective-crypto-work/`，最终报告同evidence目录。每个结果至少包含：SOURCE/父SHA/配置/产物hash、run/attempt、A与B口径、平台和实际后端、CPU/RSS/业务/队列/p99、oracle限制、完整性与外观各自结果、pcap摘要hash及清理状态。

新agent先查已完成Actions和未完成intent，补遗漏事实再动手。没有证据就NOT_RUN，不重新继承网络/FEC性能PASS；不因历史下载失败停止所有离线工作，也不反复重跑相同下载错误。禁止改上游岗位状态或要求其汇报。
